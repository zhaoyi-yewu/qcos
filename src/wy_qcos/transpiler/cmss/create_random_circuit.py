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

import argparse
import sys
from pathlib import Path

from wy_qcos.transpiler.cmss.circuit.utils import RandomCircuitGen
from wy_qcos.transpiler.high_performance import qasm_to_ir, QuantumCircuit


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate random quantum circuit."
    )
    parser.add_argument(
        "-q", "--num-qubits", type=int, default=None, help="Number of qubits."
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=None,
        help="Depth of circuit (mutually exclusive with -g).",
    )
    parser.add_argument(
        "-g",
        "--num-gates",
        type=int,
        default=None,
        help="Number of gates (mutually exclusive with -d).",
    )
    parser.add_argument(
        "-n",
        "--density",
        type=float,
        default=None,
        help="Density of gates in circuit.",
    )
    parser.add_argument(
        "-b",
        "--basis-gates",
        type=str,
        default=None,
        help="Comma-separated basis gate names.",
    )
    parser.add_argument(
        "-t",
        "--gate-type",
        type=int,
        default=None,
        help="Type of gates: 0/1/2. gate_type=2 with -b for custom gates.",
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None, help="Random seed."
    )
    parser.add_argument(
        "-f",
        "--outfile",
        type=str,
        default=None,
        help="Output file path (.qasm).",
    )
    parser.add_argument(
        "-v",
        "--view",
        type=str,
        default=None,
        metavar="QASM_FILE",
        help="View QASM file info: filename, num_qubits, depth, num_gates.",
    )
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace):
    if args.num_qubits is None:
        print(
            "Error: -q/--num-qubits is required.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.depth is not None and args.num_gates is not None:
        print(
            "Error: -d/--depth and -g/--num-gates are mutually exclusive. "
            "Please provide only one of them.",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.depth is None and args.num_gates is None:
        print(
            "Error: either -d/--depth or -g/--num-gates must be provided.",
            file=sys.stderr,
        )
        sys.exit(1)


def validate_depth_mode(args: argparse.Namespace):
    if args.basis_gates is not None and args.gate_type != 2:
        print(
            "Error: -b/--basis-gates is only allowed with gate_type=2 "
            "in depth mode.",
            file=sys.stderr,
        )
        sys.exit(1)


def validate_gates_mode(args: argparse.Namespace):
    if args.density is not None:
        print(
            "Error: -n/--density is not allowed in gates mode "
            "(use with -d/--depth instead).",
            file=sys.stderr,
        )
        sys.exit(1)
    if args.gate_type is not None:
        print(
            "Error: -t/--gate-type is not allowed in gates mode "
            "(use with -d/--depth instead).",
            file=sys.stderr,
        )
        sys.exit(1)


def parse_basis_gates(basis_gates_str: str | None):
    if basis_gates_str is None:
        return None
    return tuple(g.strip() for g in basis_gates_str.split(","))


def view_qasm(filepath: str):
    path = Path(filepath)
    qasm_str = path.read_text()
    ir, num_qubits = qasm_to_ir(qasm_str)
    qc = QuantumCircuit.from_ir(ir, num_qubits)
    print(
        f"filename: {path.name}\n"
        f"num_qubits: {num_qubits}\n"
        f"depth: {qc.depth()}\n"
        f"num_gates: {qc.size()}"
    )


def main(argv=None):
    args = parse_args(argv)
    if args.view is not None:
        view_qasm(args.view)
        return
    validate_args(args)

    rcg = RandomCircuitGen()

    if args.depth is not None:
        validate_depth_mode(args)
        kwargs = {
            "num_qubits": args.num_qubits,
            "depth": args.depth,
            "gate_type": args.gate_type if args.gate_type is not None else 0,
            "density": args.density if args.density is not None else 0.05,
            "seed": args.seed,
            "outfile": args.outfile,
        }
        if args.basis_gates is not None:
            kwargs["custom_gates"] = parse_basis_gates(args.basis_gates)
        rcg.random_circuit_with_depth(**kwargs)
    else:
        validate_gates_mode(args)
        basis_gates = parse_basis_gates(args.basis_gates)
        kwargs = {
            "num_qubits": args.num_qubits,
            "num_gates": args.num_gates,
            "seed": args.seed,
            "outfile": args.outfile,
        }
        if basis_gates is not None:
            kwargs["basis_gates"] = basis_gates
        rcg.random_circuit_with_gates(**kwargs)

    print(
        f"Random circuit generated: num_qubits={rcg.num_qubits}, "
        f"depth={rcg.depth}, size={rcg.size}"
    )


if __name__ == "__main__":
    main()
