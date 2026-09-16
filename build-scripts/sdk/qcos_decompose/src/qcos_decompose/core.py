# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from wy_qcos.transpiler.cmss.compiler.parser import compile as qasm_compile
from wy_qcos.transpiler.cmss.decomposer.decomposer import Decomposer
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.qasm_converter import QasmConverter


def decompose_qasm(qasm_str, basis_gates):
    """Parse and decompose an OpenQASM circuit into the target basis gates.

    Args:
        qasm_str (str): OpenQASM 2.0 source string.
        basis_gates (list[str]): Target basis gate name list, e.g.
            ``["rx", "ry", "rz", "cx"]``.

    Returns:
        str: OpenQASM 2.0 source string containing only the basis gates.
    """
    num_qubits, ir_ops = qasm_compile(qasm_str)

    decomposer = Decomposer()
    gate_names = list({op.name for op in ir_ops})
    table, _ = decomposer.get_decompose_rules(gate_names, basis_gates)
    decomposed_ops = decomposer.apply_decompose_rules(ir_ops, table)

    circuit = QuantumCircuit.from_ir(decomposed_ops, num_qubits)
    return QasmConverter(circuit).to_qasm2()
