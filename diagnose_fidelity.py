#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostic script: run circuits and compute raw fidelity only.

No mitigation algorithms - just transpile, run, and compare hardware results
against ideal simulation. Outputs detailed diagnostic info for each circuit.

Supports multi-round testing: each round runs all circuits, raw results are
appended to a JSON file (--data), and the markdown report (--output) is
regenerated from all accumulated rounds so chip drift over time is easy to
compare.

Usage:
  # Single round (backward-compatible detailed report)
  python diagnose_fidelity.py --driver quafu --circuit-dir samples/test

  # Multiple rounds in one run, 60s apart
  python diagnose_fidelity.py --driver quafu --circuit-dir samples/test --rounds 3 --interval 60

  # Append a round on a later day, then compare against history
  python diagnose_fidelity.py --driver quafu --circuit-dir samples/test --rounds 1

  # Rebuild the report from saved data without running hardware
  python diagnose_fidelity.py --driver quafu --circuit-dir samples/test --rounds 0
"""

import argparse
import json
import os
import sys
import time
from collections import OrderedDict
from datetime import datetime

for _k in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_k, None)
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from wy_qcos.common.library import Library
from wy_qcos.common.constant import Constant
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.qasm_converter import QasmConverter
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
import numpy as np


def load_device_config(driver_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    toml_path = os.path.join(
        base_dir, "etc", "qcos", "conf.d", f"{driver_name}.toml"
    )
    success, _, config = Library.read_toml_file(toml_path)
    if not success:
        raise RuntimeError(f"Failed to load {toml_path}")
    return json.loads(json.dumps(config.get(driver_name, config)))


def create_driver(driver_name, device_configs, **kwargs):
    if driver_name == "quafu":
        from wy_qcos.driver.quafu.driver_quafu import DriverQuafu

        driver = DriverQuafu()
    elif driver_name == "dummy":
        from wy_qcos.driver.dummy.driver_dummy import DriverDummy

        driver = DriverDummy()
    else:
        raise ValueError(f"Unknown driver: {driver_name}")

    skip_keys = {
        "alias_name",
        "description",
        "driver",
        "debug",
        "device_log_file",
        "monitor_log_file",
        "mgr_log_file",
        "enable_device_monitor",
        "log_format",
        "log_rotate_max_size_mb",
        "log_rotate_backup_count",
        "log_rotate_compression",
        "max_queued_jobs",
    }
    dc = {k: v for k, v in device_configs.items() if k not in skip_keys}
    if driver_name == "quafu":
        if kwargs.get("chip"):
            dc["chip_name"] = kwargs["chip"]
        else:
            dc.setdefault("chip_name", "Dongling")
        dc.setdefault(
            "token", kwargs.get("token", "") or device_configs.get("token", "")
        )
        dc.setdefault("url", device_configs.get("url", ""))

    ok, err = driver.validate_driver_configs(dc)
    if not ok:
        raise RuntimeError(f"Driver config validation failed: {err}")

    driver.set_configs(device_configs)
    driver.init_driver()

    if driver_name == "quafu":
        driver.chip_name = dc.get("chip_name", "Dongling")
        driver.token = dc.get("token", "")
        extra = dict(device_configs)
        extra["token"] = driver.token
        extra["chip_name"] = driver.chip_name
        driver.set_configs(extra)
        if driver.token:
            try:
                driver.fetch_configs()
            except Exception:
                pass
    return driver


def create_transpiler(device_configs, driver_name):
    from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss

    tp = TranspilerCmss()
    cfgs = (
        device_configs.get("transpiler", {})
        if driver_name != "dummy"
        else load_device_config("quafu").get("transpiler", {})
    )
    trans_cfg_inst.set_max_qubits(84)
    trans_cfg_inst.set_tech_type(Constant.TECH_TYPE_SUPERCONDUCTING)
    trans_cfg_inst.set_driver_name("quafu")
    if cfgs.get("qpu_configs"):
        trans_cfg_inst.set_qpu_cfg(cfgs["qpu_configs"])
    if cfgs.get("decomposition_rule"):
        trans_cfg_inst.set_decompose_rule(cfgs["decomposition_rule"])
    return tp


def run_circuit(driver, job_id, num_qubits, qasm, ops, shots, label):
    driver.run(
        job_id,
        num_qubits,
        {"index": label, "source_code": qasm, "transpile_results": ops},
        data_type=driver.get_default_data_type(),
        shots=shots,
    )
    counts = driver.get_results(job_id, label)

    # Quafu returns little-endian (q2q1q0), convert to big-endian (q0q1q2)
    if counts and hasattr(driver, "chip_name"):  # Quafu driver has chip_name
        counts = {bs[::-1]: c for bs, c in counts.items()}

    return counts


def counts_to_probs(counts, total):
    return (
        {k: v / total for k, v in counts.items()} if counts and total else {}
    )


def fidelity(probs, ideal):
    return sum(
        min(probs.get(k, 0), ideal.get(k, 0)) for k in set(probs) | set(ideal)
    )


# Statevector simulator (same as test_em_e2e.py)
def _apply_single(state, qubit, nq, gate):
    dim = 1 << nq
    step = 1 << (nq - 1 - qubit)
    for i in range(0, dim, 2 * step):
        for j in range(step):
            a, b = state[i + j], state[i + j + step]
            state[i + j] = gate[0, 0] * a + gate[0, 1] * b
            state[i + j + step] = gate[1, 0] * a + gate[1, 1] * b


def _apply_cx(state, ctrl, targ, nq):
    dim = 1 << nq
    swapped = set()
    for idx in range(dim):
        if idx in swapped:
            continue
        bits = list(format(idx, f"0{nq}b"))
        if bits[ctrl] == "1":
            bits[targ] = "0" if bits[targ] == "1" else "1"
            new_idx = int("".join(bits), 2)
            if new_idx != idx:
                state[idx], state[new_idx] = state[new_idx], state[idx]
                swapped.add(new_idx)


def _apply_cz(state, q1, q2, nq):
    dim = 1 << nq
    for idx in range(dim):
        bits = format(idx, f"0{nq}b")
        if bits[q1] == "1" and bits[q2] == "1":
            state[idx] *= -1


def _ideal_probs_from_ops(ops, nq):
    max_q = 0
    for op in ops:
        if op.targets:
            max_q = max(max_q, max(op.targets))
    actual_nq = max(max_q + 1, nq)

    if actual_nq > 16:
        return None

    dim = 1 << actual_nq
    state = np.zeros(dim, dtype=complex)
    state[0] = 1.0

    measured = []

    for op in ops:
        name = op.name.lower()
        tg = op.targets if op.targets else []
        av = op.arg_value if op.arg_value else []

        if name == "measure":
            for q in tg:
                if q not in measured:
                    measured.append(q)
            continue

        if name == "barrier" or name == "delay":
            continue

        if name == "h" and len(tg) == 1:
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array([[1, 1], [1, -1]]) / np.sqrt(2),
            )
        elif name == "x" and len(tg) == 1:
            _apply_single(state, tg[0], actual_nq, np.array([[0, 1], [1, 0]]))
        elif name == "y" and len(tg) == 1:
            _apply_single(
                state, tg[0], actual_nq, np.array([[0, -1j], [1j, 0]])
            )
        elif name == "z" and len(tg) == 1:
            _apply_single(state, tg[0], actual_nq, np.array([[1, 0], [0, -1]]))
        elif name == "s" and len(tg) == 1:
            _apply_single(state, tg[0], actual_nq, np.array([[1, 0], [0, 1j]]))
        elif name == "t" and len(tg) == 1:
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]),
            )
        elif name == "rx" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array(
                    [
                        [np.cos(th / 2), -1j * np.sin(th / 2)],
                        [-1j * np.sin(th / 2), np.cos(th / 2)],
                    ]
                ),
            )
        elif name == "ry" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array(
                    [
                        [np.cos(th / 2), -np.sin(th / 2)],
                        [np.sin(th / 2), np.cos(th / 2)],
                    ]
                ),
            )
        elif name == "rz" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array(
                    [[np.exp(-1j * th / 2), 0], [0, np.exp(1j * th / 2)]]
                ),
            )
        elif name in ("u3", "u") and len(tg) == 1 and len(av) >= 3:
            th, ph, la = float(av[0]), float(av[1]), float(av[2])
            _apply_single(
                state,
                tg[0],
                actual_nq,
                np.array(
                    [
                        [np.cos(th / 2), -np.exp(1j * la) * np.sin(th / 2)],
                        [
                            np.exp(1j * ph) * np.sin(th / 2),
                            np.exp(1j * (ph + la)) * np.cos(th / 2),
                        ],
                    ]
                ),
            )
        elif name == "cx" and len(tg) == 2:
            _apply_cx(state, tg[0], tg[1], actual_nq)
        elif name == "cz" and len(tg) == 2:
            _apply_cz(state, tg[0], tg[1], actual_nq)
        elif name == "swap" and len(tg) == 2:
            _apply_cx(state, tg[0], tg[1], actual_nq)
            _apply_cx(state, tg[1], tg[0], actual_nq)
            _apply_cx(state, tg[0], tg[1], actual_nq)

    if not measured:
        measured = list(range(actual_nq))

    measured = sorted(measured)

    probs = np.abs(state) ** 2
    meas_probs = {}
    for idx in range(dim):
        bits = format(idx, f"0{actual_nq}b")
        meas_bits = "".join(bits[q] for q in measured)
        meas_probs[meas_bits] = meas_probs.get(meas_bits, 0) + probs[idx]

    return {k: v for k, v in meas_probs.items() if v > 1e-10}


def _ideal_probs_from_ops_with_measured(ops, nq, measured):
    """Simulate full circuit on nq qubits, project onto measured qubits.

    Args:
        ops: Operations on contiguous qubits [0, 1, ..., nq-1]
        nq: Total number of qubits in circuit
        measured: List of qubit indices to measure (contiguous indices)

    Returns:
        dict: {bitstring: probability} for measured qubits
    """
    if nq > 16:
        return None

    dim = 1 << nq
    state = np.zeros(dim, dtype=complex)
    state[0] = 1.0

    # Apply all operations (excluding measure)
    for op in ops:
        name = op.name.lower()
        tg = op.targets if op.targets else []
        av = op.arg_value if op.arg_value else []

        if name == "measure" or name == "barrier" or name == "delay":
            continue

        if name == "h" and len(tg) == 1:
            _apply_single(
                state, tg[0], nq, np.array([[1, 1], [1, -1]]) / np.sqrt(2)
            )
        elif name == "x" and len(tg) == 1:
            _apply_single(state, tg[0], nq, np.array([[0, 1], [1, 0]]))
        elif name == "y" and len(tg) == 1:
            _apply_single(state, tg[0], nq, np.array([[0, -1j], [1j, 0]]))
        elif name == "z" and len(tg) == 1:
            _apply_single(state, tg[0], nq, np.array([[1, 0], [0, -1]]))
        elif name == "s" and len(tg) == 1:
            _apply_single(state, tg[0], nq, np.array([[1, 0], [0, 1j]]))
        elif name == "t" and len(tg) == 1:
            _apply_single(
                state,
                tg[0],
                nq,
                np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]]),
            )
        elif name == "rx" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                nq,
                np.array(
                    [
                        [np.cos(th / 2), -1j * np.sin(th / 2)],
                        [-1j * np.sin(th / 2), np.cos(th / 2)],
                    ]
                ),
            )
        elif name == "ry" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                nq,
                np.array(
                    [
                        [np.cos(th / 2), -np.sin(th / 2)],
                        [np.sin(th / 2), np.cos(th / 2)],
                    ]
                ),
            )
        elif name == "rz" and len(tg) == 1 and len(av) >= 1:
            th = float(av[0])
            _apply_single(
                state,
                tg[0],
                nq,
                np.array(
                    [[np.exp(-1j * th / 2), 0], [0, np.exp(1j * th / 2)]]
                ),
            )
        elif name in ("u3", "u") and len(tg) == 1 and len(av) >= 3:
            th, ph, la = float(av[0]), float(av[1]), float(av[2])
            _apply_single(
                state,
                tg[0],
                nq,
                np.array(
                    [
                        [np.cos(th / 2), -np.exp(1j * la) * np.sin(th / 2)],
                        [
                            np.exp(1j * ph) * np.sin(th / 2),
                            np.exp(1j * (ph + la)) * np.cos(th / 2),
                        ],
                    ]
                ),
            )
        elif name == "cx" and len(tg) == 2:
            _apply_cx(state, tg[0], tg[1], nq)
        elif name == "cz" and len(tg) == 2:
            _apply_cz(state, tg[0], tg[1], nq)
        elif name == "swap" and len(tg) == 2:
            _apply_cx(state, tg[0], tg[1], nq)
            _apply_cx(state, tg[1], tg[0], nq)
            _apply_cx(state, tg[0], tg[1], nq)

    # Project onto measured qubits
    measured = sorted(measured)
    probs = np.abs(state) ** 2
    meas_probs = {}
    for idx in range(dim):
        bits = format(idx, f"0{nq}b")
        meas_bits = "".join(bits[q] for q in measured)
        meas_probs[meas_bits] = meas_probs.get(meas_bits, 0) + probs[idx]

    return {k: v for k, v in meas_probs.items() if v > 1e-10}


def _sanitize_label(name):
    """Make a circuit name safe for use as a driver job label."""
    return name.replace("/", "_").replace("\\", "_").replace(" ", "_")


def run_circuit_diagnosis(
    driver, transpiler, circ_name, qasm_code, shots, round_idx
):
    """Transpile, simulate, and execute one circuit.

    Args:
        driver: Initialized driver instance.
        transpiler: Initialized transpiler instance.
        circ_name: Circuit identifier.
        qasm_code: QASM source string.
        shots: Number of shots.
        round_idx: Round index (used for unique job labels).

    Returns:
        Diagnostic dict. On failure nq is -1 and an "error" key is set.
    """
    import copy

    parsed = transpiler.parse(
        {f"diag-{round_idx}": qasm_code}, Constant.CODE_TYPE_QASM
    )
    tr_result = transpiler.transpile(
        parsed, driver.get_supported_basis_gates()
    )
    if isinstance(tr_result, tuple) and len(tr_result) == 3:
        tr, _, _ = tr_result
    elif isinstance(tr_result, tuple) and len(tr_result) == 2:
        tr, _ = tr_result
    else:
        tr = tr_result

    nq = transpiler.total_qubits

    measured_qubits = sorted(
        set(
            q
            for op in tr
            if op.name.lower() == "measure" and op.targets
            for q in op.targets
        )
    )
    active_qubits = sorted(
        set(q for op in tr if op.targets for q in op.targets)
    )
    if not measured_qubits:
        measured_qubits = active_qubits

    num_measured = len(measured_qubits)
    num_active = len(active_qubits)

    gate_count = sum(
        1 for op in tr if op.name.lower() not in ("measure", "barrier")
    )
    cz_count = sum(1 for op in tr if op.name == "cz")

    phy_map = {q: i for i, q in enumerate(active_qubits)}
    remapped_ops = []
    for op in tr:
        if op.targets:
            new_op = copy.deepcopy(op)
            new_op.targets = [phy_map[q] for q in op.targets]
            remapped_ops.append(new_op)

    measured_contiguous = [phy_map[q] for q in measured_qubits]

    ideal = _ideal_probs_from_ops_with_measured(
        remapped_ops, num_active, measured_contiguous
    )
    if ideal is None:
        raise RuntimeError("too many qubits for simulator")

    ideal_sorted = [
        (bs, float(p))
        for bs, p in sorted(ideal.items(), key=lambda x: -x[1])[:5]
    ]

    qc = QuantumCircuit(nq)
    qc.append_operations(tr)
    qasm_final = QasmConverter(qc).to_qasm2()

    label = f"diag-r{round_idx}-{_sanitize_label(circ_name)}"
    counts = run_circuit(
        driver, label, nq, qasm_final, tr, shots, label
    )
    if not counts:
        raise RuntimeError("no counts returned from hardware")

    bitstring_len = len(next(iter(counts.keys())))
    counts_sorted = sorted(counts.items(), key=lambda x: -x[1])[:10]

    total = sum(counts.values())
    probs = counts_to_probs(counts, total)
    final_fid = float(fidelity(probs, ideal))

    return {
        "circuit": circ_name,
        "nq": nq,
        "num_measured": num_measured,
        "num_active": num_active,
        "active_qubits": active_qubits,
        "measured_qubits": measured_qubits,
        "gate_count": gate_count,
        "cz_count": cz_count,
        "bitstring_len": bitstring_len,
        "fidelity": final_fid,
        "ideal_sorted": ideal_sorted,
        "counts_sorted": counts_sorted,
    }


def run_round(
    driver, transpiler, circuits, shots, round_idx, chip, driver_name
):
    """Run one diagnosis round over all circuits.

    Args:
        driver: Initialized driver instance.
        transpiler: Initialized transpiler instance.
        circuits: Ordered dict of {name: qasm_code}.
        shots: Number of shots.
        round_idx: Round index.
        chip: Chip name.
        driver_name: Driver name.

    Returns:
        Round result dict with metadata and per-circuit results.
    """
    round_started = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []

    for circ_name, qasm_code in circuits.items():
        print(f"\n{'-' * 70}")
        print(f"  [Round {round_idx}] Circuit: {circ_name}")
        try:
            diag = run_circuit_diagnosis(
                driver,
                transpiler,
                circ_name,
                qasm_code,
                shots,
                round_idx,
            )
            print(
                f"    qubits={diag['nq']} cz={diag['cz_count']} "
                f"fid={diag['fidelity']:.4f}"
            )
        except Exception as exc:
            import traceback

            traceback.print_exc()
            diag = {
                "circuit": circ_name,
                "nq": -1,
                "num_measured": -1,
                "num_active": -1,
                "active_qubits": [],
                "measured_qubits": [],
                "gate_count": -1,
                "cz_count": -1,
                "bitstring_len": -1,
                "fidelity": 0.0,
                "ideal_sorted": [],
                "counts_sorted": [],
                "error": str(exc),
            }
            print(f"    [ERROR] {exc}")
        results.append(diag)

    elapsed = time.time() - round_started
    valid = [r for r in results if r.get("nq", -1) > 0]
    fids = [r["fidelity"] for r in valid]
    return {
        "round": round_idx,
        "timestamp": timestamp,
        "elapsed_s": round(elapsed, 1),
        "shots": shots,
        "chip": chip,
        "driver": driver_name,
        "num_circuits": len(results),
        "num_succeeded": len(valid),
        "avg_fidelity": (sum(fids) / len(fids)) if fids else 0.0,
        "min_fidelity": min(fids) if fids else 0.0,
        "max_fidelity": max(fids) if fids else 0.0,
        "results": results,
    }


def load_rounds(data_path):
    """Load previously-saved rounds from JSON, if any."""
    if not data_path or not os.path.exists(data_path):
        return []
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(data, dict):
        return data.get("rounds", [])
    if isinstance(data, list):
        return data
    return []


def save_rounds(data_path, rounds, meta):
    """Persist all rounds + metadata to JSON (crash-safe write)."""
    payload = {"meta": meta, "rounds": rounds}
    tmp = data_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, data_path)


def _round_stats(rd):
    """Return (avg, min, max) fidelity for a round, computed from results."""
    valid = [r for r in rd.get("results", []) if r.get("nq", -1) > 0]
    fids = [r["fidelity"] for r in valid]
    if not fids:
        return 0.0, 0.0, 0.0
    return sum(fids) / len(fids), min(fids), max(fids)


def _circuit_series(rounds, circ_name):
    """Return list of fidelity-or-None for a circuit across rounds."""
    series = []
    for rd in rounds:
        match = next(
            (r for r in rd["results"] if r["circuit"] == circ_name), None
        )
        if match and match.get("nq", -1) > 0 and "error" not in match:
            series.append(match["fidelity"])
        else:
            series.append(None)
    return series


def _emit_round_summary(lines, rounds):
    """Emit per-round aggregate fidelity table."""
    lines.append("## Round Summary\n")
    lines.append(
        "| Round | Timestamp | Shots | Circuits | Succeeded | "
        "Avg Fidelity | Min | Max |"
    )
    lines.append(
        "|-------|-----------|-------|----------|-----------|"
        "--------------|-----|-----|"
    )
    for rd in rounds:
        avg, mn, mx = _round_stats(rd)
        valid = sum(1 for r in rd["results"] if r.get("nq", -1) > 0)
        lines.append(
            f"| {rd['round']} | {rd.get('timestamp', '')} | "
            f"{rd.get('shots', '')} | {len(rd['results'])} | "
            f"{valid} | {avg:.4f} | {mn:.4f} | {mx:.4f} |"
        )
    lines.append("")

    if len(rounds) >= 2:
        first, _, _ = _round_stats(rounds[0])
        last, _, _ = _round_stats(rounds[-1])
        delta = last - first
        arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
        lines.append(
            f"**Avg fidelity drift (last \u2212 first):** "
            f"{delta:+.4f} {arrow}\n"
        )


def _emit_circuit_comparison(lines, rounds, change_threshold):
    """Emit per-circuit fidelity across rounds with stats and trend."""
    lines.append("## Per-Circuit Fidelity Across Rounds\n")
    n = len(rounds)
    header = "| Circuit | Nq | CZ |" + "".join(
        f" R{rd['round']} |" for rd in rounds
    )
    header += " Mean | Std | \u0394(last\u2212first) | Trend |"
    sep = (
        "|---------|----|----|"
        + "------|" * n
        + "------|------|----------------|-------|"
    )
    lines.append(header)
    lines.append(sep)

    seen = set()
    ordered = []
    for rd in rounds:
        for r in rd["results"]:
            if r["circuit"] not in seen:
                seen.add(r["circuit"])
                ordered.append(r["circuit"])

    for nm in ordered:
        series = _circuit_series(rounds, nm)
        vals = [v for v in series if v is not None]
        nq = cz = ""
        for rd in rounds:
            m = next(
                (r for r in rd["results"] if r["circuit"] == nm), None
            )
            if m and m.get("nq", -1) > 0:
                nq = m["nq"]
                cz = m["cz_count"]
                break
        mean = (sum(vals) / len(vals)) if vals else 0.0
        if len(vals) > 1:
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            std = var ** 0.5
        else:
            std = 0.0
        delta = ""
        trend = "\u2192"
        if (
            len(rounds) >= 2
            and series[0] is not None
            and series[-1] is not None
        ):
            d = series[-1] - series[0]
            delta = f"{d:+.4f}"
            if abs(d) > change_threshold:
                trend = "\u2191" if d > 0 else "\u2193"
            else:
                trend = "\u2192"
        cells = "".join(
            (f" {v:.4f} |" if v is not None else " ERR |") for v in series
        )
        lines.append(
            f"| {nm} | {nq} | {cz} |{cells} {mean:.4f} | {std:.4f} | "
            f"{delta} | {trend} |"
        )
    lines.append("")

    if len(rounds) >= 2:
        movers = []
        for nm in ordered:
            series = _circuit_series(rounds, nm)
            if series[0] is not None and series[-1] is not None:
                movers.append((nm, series[-1] - series[0]))
        if movers:
            movers.sort(key=lambda x: abs(x[1]), reverse=True)
            lines.append("### Top Movers (|\u0394| largest)\n")
            lines.append("| Circuit | \u0394(last\u2212first) | Direction |")
            lines.append("|---------|---------------|-----------|")
            for nm, d in movers[:10]:
                direction = (
                    "\u2191 improved" if d > 0 else "\u2193 degraded"
                )
                lines.append(f"| {nm} | {d:+.4f} | {direction} |")
            lines.append("")


def _emit_single_round_detail(lines, rd):
    """Emit the original detailed per-circuit report for one round."""
    for r in rd["results"]:
        if "error" in r:
            lines.append(f"\n## {r['circuit']}\n")
            lines.append(f"**ERROR:** {r['error']}\n")
            lines.append("---\n")
            continue
        lines.append(f"\n## {r['circuit']}\n")
        lines.append(f"- **Logical qubits:** {r['nq']}")
        lines.append(
            f"- **Active physical qubits:** {r['num_active']} -> "
            f"{r['active_qubits']}"
        )
        lines.append(
            f"- **Measured physical qubits:** {r['num_measured']} -> "
            f"{r['measured_qubits']}"
        )
        lines.append(
            f"- **Gate count:** {r['gate_count']}, "
            f"**CZ gates:** {r['cz_count']}"
        )
        lines.append(f"- **Hardware bitstring length:** {r['bitstring_len']}\n")

        lines.append("**Ideal distribution (top 5):**\n")
        lines.append("| Bitstring | Probability |")
        lines.append("|-----------|-------------|")
        for pair in r.get("ideal_sorted", []):
            lines.append(f"| {pair[0]} | {pair[1]:.4f} |")

        lines.append("\n**Hardware counts (top 10):**\n")
        lines.append("| Bitstring | Count |")
        lines.append("|-----------|-------|")
        for pair in r.get("counts_sorted", []):
            lines.append(f"| {pair[0]} | {pair[1]} |")

        lines.append(f"\n**Fidelity:** {r['fidelity']:.4f}\n")
        lines.append("---\n")


def _emit_summary_section(lines, rounds):
    """Emit aggregate summary over the latest round."""
    rd = rounds[-1]
    all_results = rd["results"]
    valid = [r for r in all_results if r.get("nq", -1) > 0]
    errored = [r for r in all_results if "error" in r]

    lines.append("\n---\n")
    lines.append("## Summary\n")
    lines.append(f"**Total circuits:** {len(all_results)}  ")
    lines.append(f"**Succeeded:** {len(valid)}  ")
    lines.append(f"**Errors:** {len(errored)}\n")

    if valid:
        fids = [r["fidelity"] for r in valid]
        avg_fid = sum(fids) / len(fids)
        min_fid = min(fids)
        max_fid = max(fids)
        lines.append(f"**Average fidelity:** {avg_fid:.4f}  ")
        lines.append(f"**Min fidelity:** {min_fid:.4f}  ")
        lines.append(f"**Max fidelity:** {max_fid:.4f}\n")

        lines.append(
            "| # | Circuit | Qubits | Measured | Gates | CZ | "
            "BS Len | Fidelity |"
        )
        lines.append(
            "|---|---------|--------|----------|-------|----|"
            "--------|----------|"
        )
        for i, r in enumerate(valid, 1):
            lines.append(
                f"| {i} | {r['circuit']} | {r['nq']} | "
                f"{r['num_measured']} | {r['gate_count']} | {r['cz_count']} "
                f"| {r['bitstring_len']} | **{r['fidelity']:.4f}** |"
            )

        if errored:
            lines.append("\n### Errors\n")
            for r in errored:
                lines.append(f"- **{r['circuit']}**: {r['error']}")


def generate_report(rounds, args):
    """Build the markdown report.

    Single round   -> original detailed per-circuit report.
    Multiple rounds -> comparison-focused report (tables first).
    """
    lines = []
    lines.append("# Fidelity Diagnosis Report\n")
    lines.append(f"**Driver:** {args.driver}  ")
    lines.append(f"**Chip:** {args.chip}  ")
    lines.append(f"**Shots:** {args.shots}  ")
    lines.append(f"**Rounds:** {len(rounds)}\n")

    if len(rounds) == 1:
        _emit_single_round_detail(lines, rounds[0])
        _emit_summary_section(lines, rounds)
        return "\n".join(lines)

    _emit_round_summary(lines, rounds)
    _emit_circuit_comparison(lines, rounds, args.change_threshold)
    _emit_summary_section(lines, rounds)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Diagnostic: run circuits and compute raw fidelity, "
        "with multi-round support for tracking chip drift"
    )
    ap.add_argument("--driver", default="quafu", choices=["dummy", "quafu"])
    ap.add_argument("--token", default="")
    ap.add_argument("--chip", default="Dongling")
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument(
        "--circuit-dir", default=None, help="Directory of .qasm files"
    )
    ap.add_argument("--output", default="fidelity_diagnosis.md")
    ap.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Number of rounds to run (each round runs all circuits)",
    )
    ap.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help="Seconds to sleep between rounds",
    )
    ap.add_argument(
        "--change-threshold",
        type=float,
        default=0.02,
        help="Fidelity |delta| above this is flagged as a change",
    )
    ap.add_argument(
        "--data",
        default="fidelity_data.json",
        help="JSON file storing per-round raw data (append mode)",
    )
    ap.add_argument(
        "--reset",
        action="store_true",
        help="Ignore existing --data and start a fresh rounds list",
    )
    args = ap.parse_args()

    # Report-only mode: rebuild the markdown report from saved JSON data
    # without needing circuit files or a live driver connection.
    if args.rounds == 0:
        rounds = load_rounds(args.data)
        if not rounds:
            print(f"No saved rounds found in {args.data}")
            return 1
        last = rounds[-1]
        args.driver = last.get("driver", args.driver)
        args.chip = last.get("chip", args.chip)
        print(
            f"Report-only mode: loaded {len(rounds)} round(s) from "
            f"{args.data}"
        )
        report = generate_report(rounds, args)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n  Report: {os.path.abspath(args.output)}")
        print(f"  Data:   {os.path.abspath(args.data)}")
        return 0

    if not args.circuit_dir:
        print("--circuit-dir is required when --rounds >= 1")
        return 1

    circuit_dir = os.path.abspath(args.circuit_dir)
    qasm_files = []
    for root, dirs, files in os.walk(circuit_dir):
        for f in files:
            if f.endswith(".qasm"):
                qasm_files.append(os.path.join(root, f))
    qasm_files.sort()

    if not qasm_files:
        print(f"No .qasm files found in {circuit_dir}")
        return 1

    circuits = OrderedDict()
    for qf in qasm_files:
        rel = os.path.relpath(qf, circuit_dir)
        name = os.path.splitext(rel)[0].replace(os.sep, "/")
        with open(qf, "r", encoding="utf-8") as fh:
            circuits[name] = fh.read()

    print(f"Loaded {len(circuits)} circuits from {circuit_dir}")
    print(f"Driver: {args.driver} | Chip: {args.chip} | Shots: {args.shots}")
    print(f"Rounds to run: {args.rounds} | Interval: {args.interval}s")

    device_configs = load_device_config(args.driver)
    driver = create_driver(args.driver, device_configs, chip=args.chip)
    transpiler = create_transpiler(device_configs, args.driver)

    rounds = [] if args.reset else load_rounds(args.data)
    if rounds:
        print(f"Loaded {len(rounds)} existing round(s) from {args.data}")
        for rd in rounds:
            if rd.get("chip") != args.chip or rd.get("driver") != args.driver:
                print(
                    f"  [WARN] existing round {rd['round']} used "
                    f"{rd.get('driver')}/{rd.get('chip')} != "
                    f"{args.driver}/{args.chip}"
                )
                break

    start_round = max([r.get("round", 0) for r in rounds] + [0]) + 1

    meta = {
        "driver": args.driver,
        "chip": args.chip,
        "circuit_dir": circuit_dir,
        "change_threshold": args.change_threshold,
    }

    for i in range(args.rounds):
        round_idx = start_round + i
        print(f"\n{'=' * 90}")
        print(f"  ROUND {round_idx} / {start_round + args.rounds - 1}")
        print(f"{'=' * 90}")
        rd = run_round(
            driver,
            transpiler,
            circuits,
            args.shots,
            round_idx,
            args.chip,
            args.driver,
        )
        rounds.append(rd)
        save_rounds(args.data, rounds, meta)
        avg, mn, mx = _round_stats(rd)
        print(
            f"  Round {round_idx} done: avg_fid={avg:.4f} "
            f"({rd['num_succeeded']}/{rd['num_circuits']}) in "
            f"{rd['elapsed_s']}s  ->  saved {args.data}"
        )
        if i < args.rounds - 1 and args.interval > 0:
            print(f"  Sleeping {args.interval}s before next round...")
            time.sleep(args.interval)

    if not rounds:
        print("No rounds to report (use --rounds N with N>=1).")
        return 1

    report = generate_report(rounds, args)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n{'=' * 90}")
    print("  COMPARISON SUMMARY")
    print(f"{'=' * 90}")
    print(
        f"  {'Round':<6} {'Timestamp':<20} {'AvgFid':>8} {'Min':>8} "
        f"{'Max':>8} {'OK':>5}"
    )
    print(f"  {'-' * 60}")
    for rd in rounds:
        avg, mn, mx = _round_stats(rd)
        ok = sum(1 for r in rd["results"] if r.get("nq", -1) > 0)
        print(
            f"  {rd['round']:<6} {rd.get('timestamp', ''):<20} "
            f"{avg:>8.4f} {mn:>8.4f} {mx:>8.4f} {ok:>5}"
        )
    if len(rounds) >= 2:
        first, _, _ = _round_stats(rounds[0])
        last, _, _ = _round_stats(rounds[-1])
        delta = last - first
        arrow = "\u2191" if delta > 0 else ("\u2193" if delta < 0 else "\u2192")
        print(
            f"\n  Avg fidelity drift (R{rounds[-1]['round']} \u2212 "
            f"R{rounds[0]['round']}): {delta:+.4f} {arrow}"
        )

    print(f"\n  Report: {os.path.abspath(args.output)}")
    print(f"  Data:   {os.path.abspath(args.data)}")
    print(f"{'=' * 90}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
