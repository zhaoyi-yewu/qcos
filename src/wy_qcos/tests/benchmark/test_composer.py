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

import time
from pathlib import Path

from wy_qcos.transpiler.cmss.decomposer.decomposer import Decomposer
from wy_qcos.transpiler.cmss.compiler.decomposer import decompose_gates
from wy_qcos.transpiler.cmss.compiler.parser import get_abs_tree, get_ir


class TestDecomposer:
    @staticmethod
    def run_equivalence_graph_decomposer(gates_list, target_basis: list):
        d = Decomposer()

        start = time.perf_counter()
        decomposed_gates = d.decompose(gates_list, target_basis)
        end = time.perf_counter()

        elapsed = end - start
        print(f"[Equivalence Graph Decomposer] time={elapsed:.6f}s\n")

        return decomposed_gates

    @staticmethod
    def run_base_decomposer(gates_list, target_basis: list):
        start = time.perf_counter()
        decomposed_gates = decompose_gates(gates_list, target_basis)
        end = time.perf_counter()

        elapsed = end - start
        print(f"[Base Decomposer] time={elapsed:.6f}s")

        return decomposed_gates

    @staticmethod
    def load_samples():
        base_dir = Path(__file__).resolve().parent.parents[3]
        qasm_dir = base_dir / "samples" / "qasm" / "2.0" / "benchpress"
        samples = {}
        for file in qasm_dir.glob("*.qasm"):
            samples[file.name] = file.read_text(encoding="utf-8")

        return samples


def main():
    target_basis = ["rx", "ry", "cz", "sync", "measure", "reset"]
    samples = TestDecomposer.load_samples()

    print(f"Found {len(samples)} QASM samples\n")

    for name, data in samples.items():
        print(f"[TEST] {name}")
        try:
            start = time.perf_counter()

            tree = get_abs_tree(data)
            cir = get_ir(tree)
            gates_list = cir.get_operations()

            end = time.perf_counter()
            elapsed = end - start
            print(f"[Parser] time={elapsed:.6f}s")

            TestDecomposer.run_base_decomposer(
                gates_list=gates_list,
                target_basis=target_basis,
            )
            TestDecomposer.run_equivalence_graph_decomposer(
                gates_list=gates_list,
                target_basis=target_basis,
            )
        except Exception:
            print("ERROR\n")
            raise


if __name__ == "__main__":
    main()
