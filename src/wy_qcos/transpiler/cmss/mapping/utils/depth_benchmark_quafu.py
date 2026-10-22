#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from quark.circuit import Backend, QuantumCircuit, Transpiler
from wy_qcos.transpiler.high_performance import qasm_to_ir, transpile_from_qasm

BASIS = ["u", "cz"]
QUARK_OPT = 2  # max level
CMSS_OPT = 3
CHIPS = ["Shenglian"]


def _find_project_root() -> Path:
    """Walk up from this file to find the project root.

    The root must contain both pyproject.toml and the samples directory.
    """
    _SAMPLES_SUBPATH = (
        Path("samples") / "qasm" / "benchpress" / "qasmbench-small"
    )
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists() and (
            parent / _SAMPLES_SUBPATH
        ).is_dir():
            return parent
    raise FileNotFoundError(
        "Could not find project root "
        "(no pyproject.toml + samples/qasm/benchpress/qasmbench-small "
        "in parent directories)"
    )


CDIR = str(
    _find_project_root()
    / "samples"
    / "qasm"
    / "benchpress"
    / "qasmbench-small"
)
SKIP_OPS = {"measure", "barrier", "sync"}
SKIP_CIRCUITS = {
    "inverseqft_n4",
    "ipea_n2",
    "qec_sm_n5",
    "shor_n5",  # if statement
    "hhl_n7",
    "basis_trotter_n4",
    "vqe_uccsd_n6",
    "vqe_uccsd_n8",  # too large
    "bb84_n8",
    "hs4_n4",
    "lpn_n5",
    "qrng_n4",  # quark error
}


def _quark_transpile(qasm_string, transpiler):
    """Run quark Transpiler, return (depth, two_qubit_count)."""
    try:
        ops, num_qubits = qasm_to_ir(qasm_string)
        qc = QuantumCircuit(num_qubits, num_qubits)
        for op in ops:
            if op.name in SKIP_OPS:
                continue
            method = getattr(qc, op.name, None)
            if method:
                args = list(op.arg_value) if op.arg_value else []
                method(*args, *op.targets)
        with contextlib.redirect_stdout(io.StringIO()):
            fqc = transpiler.run(qc, optimize_level=QUARK_OPT)
        return fqc.depth, fqc.count_gate("cz")
    except Exception:
        return None, None


def _cmss_transpile(
    qasm_string: str,
    coupling_list: list[tuple[int, int]],
    edge_fidelities: list[float],
    single_qubit_fidelities: list[float],
) -> tuple[int | None, int | None]:
    """Run CMSS transpiler, return (depth, two_qubit_count)."""
    try:
        result = transpile_from_qasm(
            qasm_string,
            BASIS,
            CMSS_OPT,
            coupling_list=coupling_list,
            edge_fidelities=edge_fidelities,
            single_qubit_fidelities=single_qubit_fidelities,
            fidelity_threshold=0.1,
        )
        ops = result.basis_gate_list
        two_qubit = 0
        qubit_depths: dict[int, int] = {}
        for op in ops:
            if op.name in SKIP_OPS:
                continue
            targets = op.targets
            current = max((qubit_depths.get(q, 0) for q in targets), default=0)
            for q in targets:
                qubit_depths[q] = current + 1
            if len(targets) == 2:
                two_qubit += 1
        depth = max(qubit_depths.values(), default=0)
        return depth, two_qubit
    except Exception:
        return None, None


def main():
    paths = sorted(
        p
        for p in Path(CDIR).rglob("*.qasm")
        if "transpiled" not in p.name and p.stem not in SKIP_CIRCUITS
    )
    print(
        f"quark L{QUARK_OPT} vs CMSS L{CMSS_OPT}  basis={BASIS}  "
        f"circuits={len(paths)}"
    )
    print("=" * 65)

    for chip in CHIPS:
        with contextlib.redirect_stdout(io.StringIO()):
            backend = Backend(chip)
            transpiler = Transpiler(chip_backend=backend)

        chip_info = backend.chip_info
        coupling_list: list[tuple[int, int]] = []
        edge_fidelities: list[float] = []
        for coupler in chip_info["couplers_info"].values():
            fidelity = coupler.get("fidelity", 0.0)
            if fidelity <= 0:
                continue
            q = coupler["qubits_index"]
            coupling_list.append((q[0], q[1]))
            edge_fidelities.append(fidelity)
        num_qubits = max(max(a, b) for a, b in coupling_list) + 1
        single_qubit_fidelities = [0.0] * num_qubits
        for qi in chip_info["qubits_info"].values():
            if qi["index"] < num_qubits:
                single_qubit_fidelities[qi["index"]] = qi.get("fidelity", 0.0)

        print(f"\n[{chip}]")
        print(
            f"  {'circuit':<22} {'quark_depth':>11} "
            f"{'quark_2q':>8} {'cmss_depth':>10} {'cmss_2q':>7}"
        )
        print(f"  {'-' * 65}")

        quark_depths, quark_2q_counts = [], []
        cmss_depths, cmss_2q_counts = [], []

        for path in paths:
            name = path.stem
            qasm_string = path.read_text()

            q_depth, q_2q = _quark_transpile(qasm_string, transpiler)
            c_depth, c_2q = _cmss_transpile(
                qasm_string,
                coupling_list,
                edge_fidelities,
                single_qubit_fidelities,
            )

            if q_depth is not None:
                quark_depths.append(q_depth)
                quark_2q_counts.append(q_2q)
            if c_depth is not None:
                cmss_depths.append(c_depth)
                cmss_2q_counts.append(c_2q)

            qd = f"{q_depth:>11}" if q_depth is not None else f"{'ERR':>11}"
            qq = f"{q_2q:>8}" if q_2q is not None else f"{'ERR':>8}"
            cd = f"{c_depth:>10}" if c_depth is not None else f"{'ERR':>10}"
            cq = f"{c_2q:>7}" if c_2q is not None else f"{'ERR':>7}"
            print(f"  {name:<22} {qd} {qq} {cd} {cq}")

        q_avg_d = sum(quark_depths) / len(quark_depths) if quark_depths else 0
        q_avg_2q = (
            sum(quark_2q_counts) / len(quark_2q_counts)
            if quark_2q_counts
            else 0
        )
        c_avg_d = sum(cmss_depths) / len(cmss_depths) if cmss_depths else 0
        c_avg_2q = (
            sum(cmss_2q_counts) / len(cmss_2q_counts) if cmss_2q_counts else 0
        )
        print(f"  {'-' * 65}")
        print(
            f"  {'avg':<22} {q_avg_d:>11.0f} {q_avg_2q:>8.0f} "
            f"{c_avg_d:>10.0f} {c_avg_2q:>7.0f}"
            f"  (n: quark={len(quark_depths)}, "
            f"cmss={len(cmss_depths)})"
        )
        if q_avg_d and c_avg_d:
            pct_d = (c_avg_d - q_avg_d) / q_avg_d * 100
            print(
                f"  depth: cmss {c_avg_d:.0f} vs quark {q_avg_d:.0f}  "
                f"({pct_d:+.1f}%)"
            )
        if q_avg_2q and c_avg_2q:
            pct_2q = (c_avg_2q - q_avg_2q) / q_avg_2q * 100
            print(
                f"  2q:    cmss {c_avg_2q:.0f} vs quark "
                f"{q_avg_2q:.0f}  ({pct_2q:+.1f}%)"
            )


if __name__ == "__main__":
    main()
