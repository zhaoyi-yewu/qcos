#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Error Mitigation E2E Test — Multi-Chip Algorithm Comparison.

Runs the same circuit under different mitigation strategies across
one or more chips, and outputs a fidelity comparison report.

Usage:
  python test_em_e2e.py --driver quafu --chip Dongling
  python test_em_e2e.py --driver quafu --chip Dongling Baihua Yudu
  python test_em_e2e.py --driver quafu --chip all
  python test_em_e2e.py --driver dummy
  python test_em_e2e.py --driver quafu --circuit-dir samples/test/quick_5_circuits --shots 4096 --output my_report.md
"""

import argparse
import json
import os
import sys
import threading
import time
from collections import OrderedDict


class Tee:
    """Write to both stdout and a file simultaneously."""

    def __init__(self, filepath):
        self.file = open(filepath, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()


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
from wy_qcos.error_mitigation.mitigation_manager import MitigationManager

import numpy as np

BELL_CZ_QASM = """\
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cz q[0],q[1];
h q[1];
cz q[0],q[1];
measure q -> c;
"""

JOB_ID = "em-test-001"
IDEAL_PROBS = {"00": 0.5, "01": 0.0, "10": 0.0, "11": 0.5}

ALL_CHIPS = [
    "Dongling",
    "Baihua",
    "Yudu",
    "Honglu",
    "Baiwang",
    "Ling",
    "Shenglian",
]

# Default per-gate durations in microseconds for superconducting devices.
# Used by DD to detect idle windows and insert echo sequences. Override
# with --gate-times '{"h":0.02,"cz":0.04,"x":0.02,"y":0.02}'.
DEFAULT_GATE_TIMES = {
    "h": 0.02,
    "rx": 0.02,
    "ry": 0.02,
    "rz": 0.02,
    "x": 0.02,
    "y": 0.02,
    "cx": 0.04,
    "cz": 0.04,
    "measure": 0.0,
    "reset": 0.0,
    "default": 0.02,
}

MITIGATION_CONFIGS = OrderedDict(
    [
        ("Raw", {}),
        ("REM", {"rem": {"enabled": True}}),
        (
            "ZNE",
            {
                "zne": {
                    "enabled": True,
                    "scale_factors": [1, 2, 3],
                    "extrapolation_method": "polynomial",
                    "polynomial_degree": 1,
                    "enable_fallback": True,
                }
            },
        ),
        (
            "REM+ZNE",
            {
                "rem": {"enabled": True},
                "zne": {
                    "enabled": True,
                    "scale_factors": [1, 2, 3],
                    "extrapolation_method": "polynomial",
                    "polynomial_degree": 1,
                    "enable_fallback": True,
                },
            },
        ),
        (
            "DD",
            {
                "dd": {
                    "enabled": True,
                    "sequence": "XY4",
                    "gate_times": DEFAULT_GATE_TIMES,
                }
            },
        ),
        (
            "DD+REM",
            {
                "dd": {
                    "enabled": True,
                    "sequence": "XY4",
                    "gate_times": DEFAULT_GATE_TIMES,
                },
                "rem": {"enabled": True},
            },
        ),
        (
            "DD+ZNE",
            {
                "dd": {
                    "enabled": True,
                    "sequence": "XY4",
                    "gate_times": DEFAULT_GATE_TIMES,
                },
                "zne": {
                    "enabled": True,
                    "scale_factors": [1, 2, 3],
                    "extrapolation_method": "polynomial",
                    "polynomial_degree": 1,
                    "enable_fallback": True,
                },
            },
        ),
        (
            "DD+REM+ZNE",
            {
                "dd": {
                    "enabled": True,
                    "sequence": "XY4",
                    "gate_times": DEFAULT_GATE_TIMES,
                },
                "rem": {"enabled": True},
                "zne": {
                    "enabled": True,
                    "scale_factors": [1, 2, 3],
                    "extrapolation_method": "polynomial",
                    "polynomial_degree": 1,
                    "enable_fallback": True,
                },
            },
        ),
    ]
)


def build_mitigation_configs(gate_times):
    """Return MITIGATION_CONFIGS with DD gate_times overridden.

    Returns a shallow copy so the caller can inject a per-device gate_times
    without mutating the module-level defaults.
    """
    import copy as _copy

    cfgs = _copy.deepcopy(MITIGATION_CONFIGS)
    if not gate_times:
        return cfgs
    for _name, cfg in cfgs.items():
        if "dd" in cfg:
            cfg["dd"]["gate_times"] = gate_times
    return cfgs


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


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

    # Override the 7-day default wait so a failed/invalid quafu task
    # can't hang the script for days. update_driver_params_from_options
    # is never called in this script, so set the attribute directly.
    max_wait = kwargs.get("max_wait", 0)
    if max_wait and hasattr(driver, "max_job_wait_time"):
        driver.max_job_wait_time = max_wait

    if driver_name == "quafu":
        driver.chip_name = dc.get("chip_name", "Dongling")
        driver.token = dc.get("token", "")
        extra = dict(device_configs)
        extra["token"] = driver.token
        extra["chip_name"] = driver.chip_name
        driver.set_configs(extra)
        if not driver.token:
            raise RuntimeError(
                "Quafu token is empty. Set it via --token <YOUR_TOKEN> "
                "or fill the 'token' field in etc/qcos/conf.d/quafu.toml "
                "(obtain one from https://quafu-sqc.baqis.ac.cn/)."
            )
        driver.fetch_configs()
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


def parse_and_transpile(transpiler, driver, qasm_code):
    parsed = transpiler.parse(
        {f"{JOB_ID}-0": qasm_code}, Constant.CODE_TYPE_QASM
    )
    tr_result = transpiler.transpile(
        parsed, driver.get_supported_basis_gates()
    )
    if isinstance(tr_result, tuple) and len(tr_result) == 3:
        tr, md, _ = tr_result
    elif isinstance(tr_result, tuple) and len(tr_result) == 2:
        tr, md = tr_result
    else:
        tr = tr_result
        md = None
    return tr, transpiler.total_qubits, md


class _Heartbeat:
    """Print a dot every few seconds while a blocking call runs.

    quafu's driver.run() polls the task endpoint internally and blocks the
    main thread until the task finishes or times out. A background thread
    emits a dot so the user can tell the script is waiting, not frozen.
    """

    def __init__(self, interval=15, msg="."):
        self.interval = interval
        self.msg = msg
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        def _tick():
            while not self._stop.wait(self.interval):
                print(self.msg, end="", flush=True)
        self._thread = threading.Thread(target=_tick, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)
        if self._thread is not None:
            print("", flush=True)


def run_circuit(driver, job_id, num_qubits, qasm, ops, shots, label):
    hb = _Heartbeat()
    if hasattr(driver, "chip_name"):  # quafu driver — network call inside run
        hb.start()
    try:
        driver.run(
            job_id,
            num_qubits,
            {"index": label, "source_code": qasm, "transpile_results": ops},
            data_type=driver.get_default_data_type(),
            shots=shots,
        )
    except ValueError as exc:
        msg = str(exc)
        if "Failed to get task results" in msg:
            wait = getattr(driver, "max_job_wait_time", "?")
            raise RuntimeError(
                f"Task [{label}] did not finish within {wait}s. "
                "The task may have failed on the server, the token may be "
                "invalid, or the network may be down. Raise --max-wait if "
                "the task genuinely needs more time."
            ) from exc
        raise
    finally:
        hb.stop()
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


# ------------------------------------------------------------------
# Lightweight statevector simulator for ideal distribution
# ------------------------------------------------------------------


def _apply_single(state, qubit, nq, gate):
    """Apply a single-qubit gate to the state vector."""
    dim = 1 << nq
    step = 1 << (nq - 1 - qubit)
    for i in range(0, dim, 2 * step):
        for j in range(step):
            a, b = state[i + j], state[i + j + step]
            state[i + j] = gate[0, 0] * a + gate[0, 1] * b
            state[i + j + step] = gate[1, 0] * a + gate[1, 1] * b


def _apply_cx(state, ctrl, targ, nq):
    """Apply CNOT gate."""
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
    """Apply CZ gate."""
    dim = 1 << nq
    for idx in range(dim):
        bits = format(idx, f"0{nq}b")
        if bits[q1] == "1" and bits[q2] == "1":
            state[idx] *= -1


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


# ------------------------------------------------------------------
# Run one strategy
# ------------------------------------------------------------------


def _run_strategy(
    name,
    qem_cfg,
    driver,
    tr,
    nq,
    qasm,
    shots,
    cz,
    ideal=None,
    measured_phy=None,
):
    mgr = MitigationManager()
    mgr.configure(qem_cfg)

    # Find measured qubits (physical indices in transpiled circuit)
    if measured_phy is None:
        measured_phy = sorted(
            set(
                q
                for op in tr
                if op.name.lower() == "measure" and op.targets
                for q in op.targets
            )
        )
    # If no measure operations, assume all qubits are measured
    if not measured_phy:
        measured_phy = sorted(
            set(q for op in tr if op.targets for q in op.targets)
        )
    num_measured = len(measured_phy)

    # Calibration: build circuits for logical qubit positions [0, 1, ..., num_measured-1]
    if mgr.has_enabled() and "rem" in mgr.needs_calibration():
        cal_res = {}
        for log_q in range(num_measured):
            for prepared_state in ("0", "1"):
                # Build calibration circuit for logical qubit position
                cal_qc = QuantumCircuit(log_q + 1, 1)
                if prepared_state == "1":
                    from wy_qcos.common.cmss.gate_operation import (
                        GateOperation,
                    )
                    from wy_qcos.common.cmss.base_operation import (
                        OperationType,
                    )

                    cal_qc.append(
                        GateOperation(
                            "x",
                            targets=[log_q],
                            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
                        )
                    )
                from wy_qcos.common.cmss.measure import Measure

                cal_qc.append(Measure(targets=[log_q]))

                c = run_circuit(
                    driver,
                    JOB_ID,
                    cal_qc.num_qubits,
                    QasmConverter(cal_qc).to_qasm2(),
                    cal_qc.get_operations(),
                    shots,
                    f"cal_{log_q}_{prepared_state}",
                )
                if c:
                    cal_res.setdefault(log_q, {})[prepared_state] = c
        if cal_res:
            tech = mgr.get_technique("rem") or mgr.get_technique("readout")
            if tech:
                # Store calibration with logical indices
                logical_qubits = list(range(num_measured))
                mgr.store_calibration_data(
                    "readout",
                    tech.process_calibration_results(cal_res, logical_qubits),
                )

    # Generate and run all circuit variants (DD/ZNE folding) through the
    # manager so multi-point ZNE scale factors are exercised end-to-end.
    variants = {}
    for vdef in mgr.transform_circuit(QuantumCircuit.from_ir(tr, nq)):
        label = vdef["label"]
        vqc = vdef["circuit"]
        vops = vqc.get_operations()
        vqasm = QasmConverter(vqc).to_qasm2()
        counts = run_circuit(driver, JOB_ID, nq, vqasm, vops, shots, label)
        if counts:
            variants[label] = counts

    # Scale-1 counts are the baseline / fallback result.
    orig_processed = (
        variants.get("zne_s1")
        or variants.get("original")
        or (next(iter(variants.values())) if variants else {})
    )

    if mgr.has_enabled() and variants:
        # Hardware counts have length = num_measured, qubits are
        # contiguous [0, 1, ..., num_measured-1].
        out = mgr.postprocess_results(
            variants,
            num_qubits=num_measured,
            target_qubits=list(range(num_measured)),
        )
        mr = out.get("results", {})
        if isinstance(mr, dict) and mr:
            # Prefer the extrapolated/mitigated result if available.
            if "extrapolated" in mr:
                fc = mr["extrapolated"]
            else:
                fc = next(iter(mr.values()))
                if not isinstance(fc, dict):
                    fc = orig_processed
        else:
            fc = orig_processed
    else:
        fc = orig_processed

    total = sum(fc.values()) if fc else 0
    probs = counts_to_probs(fc, total)

    # Compute fidelity against ideal
    fid = round(fidelity(probs, ideal), 4) if ideal else 0.0

    return {"name": name, "fidelity": fid}


# ------------------------------------------------------------------
# Report
# ------------------------------------------------------------------


def generate_report(all_results, driver_name, shots, output_path):
    """Generate markdown report. all_results: {chip: {circuit: [results]}}"""
    # Infer strategy order from the first chip's first circuit results.
    strats = []
    for _circuits in all_results.values():
        for _results in _circuits.values():
            strats = [r["name"] for r in _results]
            break
        if strats:
            break
    lines = [
        "# Error Mitigation Fidelity Comparison\n",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Driver:** {driver_name}  ",
        f"**Shots:** {shots}\n",
    ]

    # Accumulate global stats: strategy -> list of (raw_fid, strat_fid, chip, circuit)
    global_stats = {s: [] for s in strats}

    for chip, circuits in all_results.items():
        lines.append(f"\n## {chip}\n")

        # ── Fidelity table ──
        header = "| Circuit | " + " | ".join(strats) + " | Best |"
        sep = "|---------|" + "|".join(["--------"] * len(strats)) + "|------|"
        lines.extend([header, sep])

        for circ_name, results in circuits.items():
            fids = {r["name"]: r["fidelity"] for r in results}
            best_name = max(results, key=lambda r: r["fidelity"])["name"]
            row = f"| {circ_name} |"
            for s in strats:
                fid = fids.get(s, 0)
                if s == best_name:
                    row += f" **{fid:.4f}** |"
                else:
                    row += f" {fid:.4f} |"
            row += f" {best_name} |"
            lines.append(row)

        # ── Per-strategy improvement table ──
        lines.append(f"\n### {chip} — Improvement over Raw\n")
        imp_header = "| Circuit | Raw |"
        imp_sep = "|---------|-----|"
        for s in strats:
            if s == "Raw":
                continue
            imp_header += f" {s} (delta / %) |"
            imp_sep += "------------------|"
        imp_header += " Best |"
        imp_sep += "------|"
        lines.extend([imp_header, imp_sep])

        for circ_name, results in circuits.items():
            fids = {r["name"]: r["fidelity"] for r in results}
            raw_fid = fids.get("Raw", 0)
            best_name = max(results, key=lambda r: r["fidelity"])["name"]
            row = f"| {circ_name} | {raw_fid:.4f} |"
            for s in strats:
                if s == "Raw":
                    continue
                fid = fids.get(s, 0)
                delta = fid - raw_fid
                if raw_fid > 0:
                    pct = delta / raw_fid * 100
                    cell = f"{delta:+.4f} / {pct:+.1f}%"
                else:
                    cell = f"{delta:+.4f} / N/A"
                row += f" {cell} |"

                if raw_fid > 0:
                    global_stats[s].append((raw_fid, fid, chip, circ_name))
            row += f" {best_name} |"
            lines.append(row)

        if "Raw" in strats:
            for circ_name, results in circuits.items():
                fids = {r["name"]: r["fidelity"] for r in results}
                raw_fid = fids.get("Raw", 0)
                if raw_fid > 0:
                    global_stats["Raw"].append(
                        (raw_fid, raw_fid, chip, circ_name)
                    )

    # ── Global summary across all chips & circuits ──
    lines.append("\n---\n")
    lines.append("## Overall Summary (All Chips & Circuits)\n")

    total_circuits = sum(len(circuits) for circuits in all_results.values())
    lines.append(
        f"**Total circuit-chip combinations tested:** {total_circuits}\n"
    )

    # Per-strategy average fidelity
    lines.append("### Average Fidelity by Strategy\n")
    lines.append("| Strategy | Samples | Avg Fidelity | Min | Max | Std Dev |")
    lines.append("|----------|---------|--------------|-----|-----|---------|")
    for s in strats:
        entries = global_stats[s]
        if entries:
            fids = [e[1] for e in entries]
            avg_f = sum(fids) / len(fids)
            std_f = (sum((f - avg_f) ** 2 for f in fids) / len(fids)) ** 0.5
            lines.append(
                f"| {s} | {len(fids)} | {avg_f:.4f} "
                f"| {min(fids):.4f} | {max(fids):.4f} | {std_f:.4f} |"
            )
        else:
            lines.append(f"| {s} | 0 | N/A | N/A | N/A | N/A |")

    # Per-strategy average improvement over Raw
    lines.append("\n### Average Improvement over Raw\n")
    lines.append(
        "| Strategy | Samples | Avg Delta | Avg % Improvement | Win Rate |"
    )
    lines.append(
        "|----------|---------|-----------|-------------------|----------|"
    )
    for s in strats:
        if s == "Raw":
            continue
        entries = global_stats[s]
        if entries:
            deltas = [e[1] - e[0] for e in entries]
            pcts = [(e[1] - e[0]) / e[0] * 100 for e in entries if e[0] > 0]
            wins = sum(1 for d in deltas if d > 0)
            avg_d = sum(deltas) / len(deltas)
            avg_p = sum(pcts) / len(pcts) if pcts else 0
            win_rate = wins / len(deltas) * 100
            lines.append(
                f"| {s} | {len(entries)} | {avg_d:+.4f} "
                f"| {avg_p:+.2f}% | {win_rate:.0f}% ({wins}/{len(deltas)}) |"
            )
        else:
            lines.append(f"| {s} | 0 | N/A | N/A | N/A |")

    # Per-circuit breakdown across chips
    if len(all_results) > 1:
        lines.append("\n### Per-Circuit Average Improvement (across chips)\n")
        circuit_names = set()
        for circuits in all_results.values():
            circuit_names.update(circuits.keys())
        circuit_names = sorted(circuit_names)

        c_header = "| Circuit |"
        c_sep = "|---------|"
        for s in strats:
            if s == "Raw":
                continue
            c_header += f" {s} |"
            c_sep += "--------|"
        lines.extend([c_header, c_sep])

        for cn in circuit_names:
            row = f"| {cn} |"
            for s in strats:
                if s == "Raw":
                    continue
                pcts = []
                for chip, circuits in all_results.items():
                    if cn not in circuits:
                        continue
                    fids = {r["name"]: r["fidelity"] for r in circuits[cn]}
                    raw_fid = fids.get("Raw", 0)
                    s_fid = fids.get(s, 0)
                    if raw_fid > 0:
                        pcts.append((s_fid - raw_fid) / raw_fid * 100)
                if pcts:
                    avg_p = sum(pcts) / len(pcts)
                    row += f" {avg_p:+.2f}% |"
                else:
                    row += " N/A |"
            lines.append(row)

    report = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    return report


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(
        description="Error Mitigation Multi-Chip Comparison"
    )
    ap.add_argument("--driver", default="dummy", choices=["dummy", "quafu"])
    ap.add_argument("--token", default="")
    ap.add_argument(
        "--chip",
        nargs="+",
        default=["Dongling"],
        help="Chip name(s). Use 'all' for all chips.",
    )
    ap.add_argument("--shots", type=int, default=1024)
    ap.add_argument(
        "--circuit-dir",
        default=None,
        help="Directory of .qasm files to test (tests all files)",
    )
    ap.add_argument("--output", default="em_comparison_report.md")
    ap.add_argument(
        "--gate-times",
        default=None,
        help='Gate durations (us) as JSON, e.g. '
        '\'{"h":0.02,"cz":0.04,"x":0.02,"y":0.02}\'. '
        "Used by DD; defaults to built-in superconducting timings.",
    )
    ap.add_argument(
        "--log",
        default="em_test.log",
        help="File to save console output (default: em_test.log)",
    )
    ap.add_argument(
        "--max-wait",
        type=int,
        default=600,
        help="Max seconds to wait for a single quafu task before giving up "
        "(default: 600). Quafu's built-in default is 604800s (7 days); "
        "without this override a failed/invalid task hangs the script "
        "for days with no output.",
    )
    args = ap.parse_args()

    # Parse gate_times for DD (JSON string -> dict)
    gate_times = DEFAULT_GATE_TIMES
    if args.gate_times:
        gate_times = json.loads(args.gate_times)
    mitigation_configs = build_mitigation_configs(gate_times)

    # Set up Tee to write to both stdout and log file
    tee = Tee(args.log)
    sys.stdout = tee

    chips = ALL_CHIPS if "all" in args.chip else args.chip

    # Load circuits
    if args.circuit_dir:
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
    else:
        circuits = OrderedDict([("bell_cz", BELL_CZ_QASM)])

    print(f"{'=' * 60}")
    print("  Error Mitigation Comparison")
    print(f"  Driver: {args.driver} | Chips: {', '.join(chips)}")
    print(f"  Circuits: {len(circuits)} | Shots: {args.shots}")
    print(f"{'=' * 60}")

    device_configs = load_device_config(args.driver)
    all_results = OrderedDict()  # chip -> circuit -> [results]

    for chip in chips:
        print(f"\n{'=' * 60}")
        print(f"  Chip: {chip}")
        print(f"{'=' * 60}")
        try:
            driver = create_driver(
                args.driver, device_configs, token=args.token, chip=chip,
                max_wait=args.max_wait,
            )
            transpiler = create_transpiler(device_configs, args.driver)
        except Exception as exc:
            print(f"  [SKIP] Driver init failed: {exc}")
            continue

        all_results[chip] = OrderedDict()

        for circ_name, qasm_code in circuits.items():
            try:
                parsed = transpiler.parse(
                    {f"{JOB_ID}-0": qasm_code}, Constant.CODE_TYPE_QASM
                )

                # Transpile
                supp = driver.get_supported_basis_gates()
                tr_result = transpiler.transpile(parsed, supp)
                if isinstance(tr_result, tuple) and len(tr_result) == 3:
                    tr, _, _ = tr_result
                elif isinstance(tr_result, tuple) and len(tr_result) == 2:
                    tr, _ = tr_result
                else:
                    tr = tr_result

                # Build ideal from TRANSPILED circuit mapped to contiguous qubits
                import copy

                active_phy = sorted(
                    set(q for op in tr if op.targets for q in op.targets)
                )
                phy_map = {q: i for i, q in enumerate(active_phy)}
                remapped = []
                for op in tr:
                    if op.targets:
                        new_op = copy.deepcopy(op)
                        new_op.targets = [phy_map[q] for q in op.targets]
                        remapped.append(new_op)

                # Extract measured qubits (physical indices)
                measured_phy = sorted(
                    set(
                        q
                        for op in tr
                        if op.name == "measure" and op.targets
                        for q in op.targets
                    )
                )

                # If no explicit measure gates, fall back to all active qubits
                if not measured_phy:
                    measured_phy = active_phy

                # Map measured qubits to contiguous indices
                measured_contiguous = [phy_map[q] for q in measured_phy]

                ideal = _ideal_probs_from_ops_with_measured(
                    remapped, len(active_phy), measured_contiguous
                )
                if ideal is None:
                    print(
                        f"  [SKIP] {circ_name}: too many qubits for simulator"
                    )
                    continue
            except Exception as exc:
                print(f"  [SKIP] {circ_name}: {exc}")
                continue

            cz = sum(1 for op in remapped if op.name == "cz")
            nq_remapped = len(active_phy)
            qc = QuantumCircuit(nq_remapped)
            qc.append_operations(remapped)
            qasm = QasmConverter(qc).to_qasm2()

            print(
                f"\n  --- {circ_name} (qubits={nq_remapped}, gates={len(remapped)}, cz={cz}, measured={len(measured_contiguous)}) ---"
            )

            circ_results = []
            for strat_name, qem_cfg in mitigation_configs.items():
                try:
                    r = _run_strategy(
                        strat_name,
                        qem_cfg,
                        driver,
                        remapped,
                        nq_remapped,
                        qasm,
                        shots=args.shots,
                        cz=cz,
                        ideal=ideal,
                        measured_phy=measured_contiguous,
                    )
                except Exception as exc:
                    print(f"    {strat_name:<10s}  FAILED: {exc}")
                    r = {"name": strat_name, "fidelity": 0.0,
                         "error": str(exc)}
                circ_results.append(r)
                if "error" not in r:
                    print(f"    {strat_name:<10s}  fidelity={r['fidelity']:.4f}")

            all_results[chip][circ_name] = circ_results

    if not all_results or not any(all_results.values()):
        print("\nNo results.")
        return 1

    # ── Console summary: per-circuit and per-algorithm stats ──
    strats = list(mitigation_configs.keys())
    global_stats = {s: [] for s in strats}  # strategy -> list of (raw, fid)
    for circuits in all_results.values():
        for results in circuits.values():
            fids = {r["name"]: r["fidelity"] for r in results}
            raw_fid = fids.get("Raw", 0)
            for s in strats:
                if s in fids:
                    global_stats[s].append((raw_fid, fids[s]))

    print(f"\n{'=' * 70}")
    print("  SUMMARY: Average Fidelity & Improvement over Raw")
    print(f"{'=' * 70}")
    print(
        f"  {'Strategy':<10} {'Samples':>7} {'AvgFid':>8} {'MinFid':>8} "
        f"{'MaxFid':>8} {'AvgDelta':>9} {'Avg%':>8} {'WinRate':>8}"
    )
    print(f"  {'-'*66}")
    for s in strats:
        entries = global_stats[s]
        if not entries:
            continue
        fids = [e[1] for e in entries]
        avg_f = sum(fids) / len(fids)
        deltas = [e[1] - e[0] for e in entries]
        pcts = [(e[1] - e[0]) / e[0] * 100 for e in entries if e[0] > 0]
        wins = sum(1 for d in deltas if d > 0)
        avg_d = sum(deltas) / len(deltas)
        avg_p = sum(pcts) / len(pcts) if pcts else 0
        win_r = wins / len(deltas) * 100
        print(
            f"  {s:<10} {len(entries):>7} {avg_f:>8.4f} {min(fids):>8.4f} "
            f"{max(fids):>8.4f} {avg_d:>+9.4f} {avg_p:>+7.2f}% "
            f"{win_r:>6.0f}%"
        )

    print(f"\n{'=' * 70}")
    print(f"  Report: {args.output}")
    print(f"{'=' * 70}")
    report = generate_report(all_results, args.driver, args.shots, args.output)
    print(report)
    print(f"\nSaved: {os.path.abspath(args.output)}")
    print(f"Log: {os.path.abspath(args.log)}")

    # Restore stdout and close tee
    sys.stdout = tee.stdout
    tee.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
