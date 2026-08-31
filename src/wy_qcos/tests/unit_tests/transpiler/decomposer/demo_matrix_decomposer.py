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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""矩阵分解模块交互式演示脚本 (需求 4.1.1.12).

菜单驱动, 用户无需输入复杂矩阵, 从预设矩阵库选择序号即可完成
"目标矩阵 -> 基础门序列 -> 等价性验证" 的完整演示流程.

运行方式 (二选一)::

    cd src && python -m wy_qcos.tests.unit_tests.transpiler.decomposer.demo_matrix_decomposer
    cd src && PYTHONPATH=. python wy_qcos/tests/unit_tests/transpiler/decomposer/demo_matrix_decomposer.py
"""

from __future__ import annotations

import numpy as np

from wy_qcos.common.cmss.gate_operation import (
    CH,
    CX,
    CY,
    CZ,
    H,
    SWAP,
    X,
    Y,
    Z,
)
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.circuit.operators.operator import Operator
from wy_qcos.transpiler.cmss.decomposer.matrix_to_circuit import (
    matrix_to_circuit,
)

# matrix_to_circuit 固定输出到的基础门集合 (见 matrix_to_circuit.py:
# 单比特分解用 rz/ry, 多比特 CSD 用 cx, 受控相位用 p, 受控态翻转用 x).
BASIS_GATES = ["rz", "ry", "cx", "p", "x"]

# 校验输出门合法性时允许的门集合 (BASIS_GATES + 非门操作透传).
ALLOWED_OUTPUT_GATES = set(BASIS_GATES) | {
    "measure",
    "move",
    "sync",
    "reset",
    "barrier",
}


# ----------------------------------------------------------------------
# 预设矩阵库
# ----------------------------------------------------------------------


def _random_unitary(size: int, seed: int | None = None) -> np.ndarray:
    """生成随机酉矩阵.

    Args:
        size: 矩阵维度 (2 的幂).
        seed: 随机种子. 为 None 时使用系统熵, 每次结果不同;
            为整数时结果可复现.

    Returns:
        酉矩阵.
    """
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((size, size)) + 1j * rng.standard_normal((
        size,
        size,
    ))
    q, _ = np.linalg.qr(z)
    return q


def _bell_matrix() -> np.ndarray:
    """Bell 态制备电路的酉矩阵."""
    return CX().to_matrix() @ np.kron(H().to_matrix(), np.eye(2))


# 预设矩阵库: (显示名, 维度说明, 工厂函数 -> (matrix, qubits))
MATRIX_LIBRARY: list[tuple[str, str]] = [
    ("H 门 (单比特)", "1 qubit, 2x2"),
    ("X 门 (单比特)", "1 qubit, 2x2"),
    ("Y 门 (单比特)", "1 qubit, 2x2"),
    ("Z 门 (单比特)", "1 qubit, 2x2"),
    ("CZ 门 (双比特)", "2 qubit, 4x4"),
    ("CX 门 (双比特)", "2 qubit, 4x4"),
    ("CY 门 (双比特)", "2 qubit, 4x4"),
    ("SWAP 门 (双比特)", "2 qubit, 4x4"),
    ("CH 门 (双比特)", "2 qubit, 4x4"),
    ("Bell 态制备电路 (双比特)", "2 qubit, 4x4"),
    ("随机酉矩阵 3 比特 (8x8, 固定种子)", "3 qubit, 8x8"),
    ("随机酉矩阵 4 比特 (16x16, 固定种子)", "4 qubit, 16x16"),
    ("随机酉矩阵 5 比特 (32x32, 固定种子)", "5 qubit, 32x32"),
    ("真随机酉矩阵 (每次不同, 自选比特数)", "1-8 qubit"),
]


def build_matrix(choice: int) -> tuple[np.ndarray, list[int]]:
    """根据菜单序号构造目标矩阵和比特列表."""
    # 单比特门
    if choice == 1:
        return H().to_matrix(), [0]
    if choice == 2:
        return X().to_matrix(), [0]
    if choice == 3:
        return Y().to_matrix(), [0]
    if choice == 4:
        return Z().to_matrix(), [0]
    # 双比特门
    if choice == 5:
        return CZ().to_matrix(), [0, 1]
    if choice == 6:
        return CX().to_matrix(), [0, 1]
    if choice == 7:
        return CY().to_matrix(), [0, 1]
    if choice == 8:
        return SWAP().to_matrix(), [0, 1]
    if choice == 9:
        return CH().to_matrix(), [0, 1]
    if choice == 10:
        return _bell_matrix(), [0, 1]
    # 随机酉矩阵 (固定种子, 可复现)
    if choice == 11:
        return _random_unitary(8, seed=7), [0, 1, 2]
    if choice == 12:
        return _random_unitary(16, seed=7), [0, 1, 2, 3]
    if choice == 13:
        return _random_unitary(32, seed=999), [0, 1, 2, 3, 4]
    # 真随机酉矩阵 (每次不同, 比特数交互输入)
    if choice == 14:
        n = _prompt_qubit_count()
        return _random_unitary(2**n, seed=None), list(range(n))
    raise ValueError(f"未知选项: {choice}")


def _prompt_qubit_count() -> int:
    """交互式询问比特数 (1-8), 校验后返回."""
    while True:
        raw = input("请输入比特数 (1-8, 8 对应 256x256): ").strip()
        if not raw.isdigit():
            print("无效输入, 请输入 1-8 的整数。")
            continue
        n = int(raw)
        if not (1 <= n <= 8):
            print("比特数超出范围, 请输入 1-8。")
            continue
        return n


# ----------------------------------------------------------------------
# 分解与验证
# ----------------------------------------------------------------------


def _equiv_matrix(matrix: np.ndarray, gates: list, n: int) -> bool:
    """校验门序列实现的酉矩阵与目标矩阵等价 (忽略全局相位)."""
    circuit = QuantumCircuit.from_ir(gates, n)
    return Operator(circuit).equiv(Operator(matrix))


def _equiv_distance(matrix: np.ndarray, gates: list, n: int) -> float:
    """计算门序列矩阵与目标矩阵的最大幅值差 (用于展示误差量级)."""
    circuit = QuantumCircuit.from_ir(gates, n)
    actual = Operator(circuit).data
    # 对齐全局相位: 取最能使两者接近的相位
    denom = np.abs(actual) * np.abs(matrix)
    mask = denom > 1e-15
    if not np.any(mask):
        return float(np.max(np.abs(actual - matrix)))
    phase = actual[mask] / matrix[mask]
    common = phase[0]
    return float(np.max(np.abs(actual / common - matrix)))


def _illegal_gates(gates: list) -> list[str]:
    """返回不在合法集合内的门名."""
    return sorted({
        str(g.name) for g in gates if str(g.name) not in ALLOWED_OUTPUT_GATES
    })


# ----------------------------------------------------------------------
# 展示
# ----------------------------------------------------------------------


def _print_matrix(matrix: np.ndarray, max_rows: int = 4) -> None:
    """打印矩阵 (超过 max_rows 行则截断展示)."""
    n = matrix.shape[0]
    show = min(n, max_rows)
    for i in range(show):
        row = "  ".join(f"{matrix[i, j]:7.3f}" for j in range(show))
        print(f"    {row}")
    if n > max_rows:
        print(f"    ... (共 {n}x{matrix.shape[1]}, 仅展示前 {show} 行)")


def _print_gates(gates: list, max_gates: int = 12) -> None:
    """打印门序列 (超过 max_gates 则截断)."""
    show = min(len(gates), max_gates)
    for i in range(show):
        print(f"    [{i:>3}] {gates[i]!r}")
    if len(gates) > max_gates:
        print(f"    ... (共 {len(gates)} 个门, 仅展示前 {show} 个)")


def decompose_and_verify(matrix: np.ndarray, qubits: list[int]) -> None:
    """执行分解、展示结果并验证等价性."""
    n = len(qubits)
    dim = matrix.shape[0]

    print()
    print("-" * 60)
    print(f"目标矩阵: {dim}x{dim} ({n} qubit)")
    print(f"基础门集合: {BASIS_GATES}")
    print("-" * 60)
    _print_matrix(matrix)
    print()

    import time

    # 大矩阵 (n>=7) 分解与等价校验各需数分钟, 提前提示避免误判卡死
    if n >= 7:
        print(f"正在分解... (大矩阵 {dim}x{dim}, 预计数分钟, 请耐心等待)")
    else:
        print("正在分解...")
    start = time.perf_counter()
    gates, phase = matrix_to_circuit(matrix, qubits)
    elapsed = time.perf_counter() - start

    print()
    print(f"分解完成: {len(gates)} 个基础门, 耗时 {elapsed * 1000:.1f} ms")
    print(f"全局相位: {phase:.6f} rad")
    print()
    print("门序列:")
    _print_gates(gates)
    print()

    # 合法性校验
    illegal = _illegal_gates(gates)
    if illegal:
        print(f"[警告] 输出含非法门: {illegal}")
    else:
        print(f"[校验] 输出门均在基础门集合 {BASIS_GATES} 内  ->  通过")

    # 等价性校验
    if n >= 7:
        print()
        print(
            "[校验] 重建电路做等价校验, 大矩阵下耗时与分解同量级, 请耐心等待..."
        )
    equiv = _equiv_matrix(matrix, gates, n)
    dist = _equiv_distance(matrix, gates, n)
    print()
    if equiv:
        print(f"[校验] 门序列矩阵与目标矩阵等价 (忽略全局相位)  ->  通过")
        print(f"        最大幅值误差: {dist:.2e}")
    else:
        print(f"[校验] 门序列矩阵与目标矩阵不等价  ->  失败")
        print(f"        最大幅值误差: {dist:.2e}")
    print("-" * 60)


# ----------------------------------------------------------------------
# 交互循环
# ----------------------------------------------------------------------


def _print_menu() -> None:
    print()
    print("=" * 60)
    print("矩阵分解模块交互式演示 (需求 4.1.1.12)")
    print("=" * 60)
    print(f"分解使用的基础门集合: {BASIS_GATES}")
    print("-" * 60)
    print("请选择目标量子矩阵 (输入序号, q 退出):")
    for idx, (name, desc) in enumerate(MATRIX_LIBRARY, start=1):
        print(f"  {idx:>2}. {name}  [{desc}]")
    print("   q. 退出")


def main() -> int:
    while True:
        _print_menu()
        try:
            choice = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("再见。")
            return 0

        if choice.lower() in ("q", "quit", "exit"):
            print("再见。")
            return 0

        if not choice.isdigit():
            print("无效输入, 请输入序号或 q。")
            continue

        idx = int(choice)
        if not (1 <= idx <= len(MATRIX_LIBRARY)):
            print(f"序号超出范围 (1-{len(MATRIX_LIBRARY)})。")
            continue

        name, desc = MATRIX_LIBRARY[idx - 1]
        print(f"\n已选择: {name}  [{desc}]")
        try:
            matrix, qubits = build_matrix(idx)
            decompose_and_verify(matrix, qubits)
        except KeyboardInterrupt:
            print("\n[中断] 已取消本次分解。")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[错误] 分解失败: {type(exc).__name__}: {exc}")

        print()
        try:
            input("按回车键继续...")
        except (EOFError, KeyboardInterrupt):
            print("再见。")
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
