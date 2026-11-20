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

import re
from pathlib import Path

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedInput
from lark.exceptions import UnexpectedToken

from wy_qcos.transpiler.cmss.compiler.qtypes import Node
from wy_qcos.transpiler.cmss.compiler.visitor import Visitor
from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit

_GRAMMAR_PATH = Path(__file__).parent / "qasm_grammar.lark"

_lark_parser = Lark(
    _GRAMMAR_PATH.read_text(encoding="utf-8"),
    parser="lalr",
    propagate_positions=True,
    maybe_placeholders=False,
    regex=True,
)

_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z_0-9]*$")

_FUNC_TEMPLATES = {
    "sin": "np.sin({})",
    "cos": "np.cos({})",
    "tan": "np.tan({})",
    "exp": "np.exp({})",
    "ln": "np.log({})",
    "sqrt": "np.sqrt({})",
}


def _token_line(node_or_token):
    """Extract line number from a Token or Node."""
    if isinstance(node_or_token, Token):
        return node_or_token.line
    if isinstance(node_or_token, Node):
        return node_or_token.pos
    return 0


class QasmTransformer(Transformer):
    """Transform lark parse tree into Node-based AST.

    Each method corresponds to a grammar rule alias, mirroring the
    semantic actions of the original PLY p_* functions.
    """

    def __init__(self) -> None:
        super().__init__()
        self._openqasm_version: list = []

    # ── top-level ──────────────────────────────────────

    @v_args(meta=True)
    def main_program(self, meta, children):
        real_token = children[0]
        incfile_result = children[1]
        program_result = children[2]
        del incfile_result
        version = float(real_token.value)
        if version in (2.0, 3.0):
            if (
                len(self._openqasm_version) > 0
                and version != self._openqasm_version[0]
            ):
                raise TypeError(f"in line {meta.line}: version error")
        else:
            raise TypeError(f"in line {meta.line}: version error")
        self._openqasm_version.clear()
        return Node("top", program_result, None, meta.line)

    def incfile(self, children):
        return children[0].value

    def program(self, children):
        return list(children)

    def start(self, children):
        return children[0]

    # ── declarations ───────────────────────────────────

    @v_args(meta=True)
    def decl(self, meta, children):
        keyword = children[0].value
        id_val = children[1].value
        number = int(children[2].value)
        return Node("def_var", [id_val, number], keyword, meta.line)

    @v_args(meta=True)
    def decl3(self, meta, children):
        del meta
        keyword = children[0].value
        if len(children) == 3:
            number = int(children[1].value)
            id_val = children[2].value
            return Node("def_var3", [number, id_val], keyword, 0)
        else:
            id_val = children[1].value
            return Node("def_var3", [id_val], keyword, 0)

    @v_args(meta=True)
    def classical_decl_init(self, meta, children):
        scalar_type = children[0]
        id_val = children[1].value
        exp_result = children[2]
        return Node(
            "classical_declare_statement",
            [scalar_type, id_val, exp_result],
            None,
            meta.line,
        )

    @v_args(meta=True)
    def classical_decl_array(self, meta, children):
        array_type = children[0]
        id_val = children[1].value
        array_literal = children[2]
        return Node(
            "classical_declare_statement",
            [array_type, id_val, array_literal],
            None,
            meta.line,
        )

    @v_args(meta=True)
    def classical_decl_only(self, meta, children):
        scalar_type = children[0]
        id_val = children[1].value
        return Node(
            "classical_declare_statement",
            [scalar_type, id_val],
            None,
            meta.line,
        )

    # ── scalar types ───────────────────────────────────

    @v_args(meta=True)
    def scalar_type_int(self, meta, children):
        if len(self._openqasm_version) == 0:
            self._openqasm_version.append(3.0)
        return Node("scalar_type", None, "int", meta.line)

    @v_args(meta=True)
    def scalar_type_float(self, meta, children):
        if len(self._openqasm_version) == 0:
            self._openqasm_version.append(3.0)
        return Node("scalar_type", None, "float", meta.line)

    @v_args(meta=True)
    def scalar_type_bool(self, meta, children):
        if len(self._openqasm_version) == 0:
            self._openqasm_version.append(3.0)
        return Node("scalar_type", None, "bool", meta.line)

    def designator01(self, children):
        if children:
            return children[0]
        return None

    # ── array types ────────────────────────────────────

    @v_args(meta=True)
    def array_type(self, meta, children):
        return Node("array_type", list(children), None, meta.line)

    @v_args(meta=True)
    def array_literal_empty(self, meta, children):
        return Node("array_literal", [], None, meta.line)

    @v_args(meta=True)
    def array_literal_items(self, meta, children):
        return Node("array_literal", list(children), None, meta.line)

    # ── assignment ─────────────────────────────────────

    @v_args(meta=True)
    def assign_statement(self, meta, children):
        del meta
        indexed_identifier = children[0]
        exp_result = children[1]
        return Node(
            "assign_statement",
            [indexed_identifier, "=", exp_result],
            None,
            indexed_identifier.pos,
        )

    def indexed_identifier(self, children):
        id_token = children[0]
        if len(children) == 1:
            return Node(
                "indexed_identifier",
                [],
                id_token.value,
                id_token.line,
            )
        else:
            indices = list(children[1:])
            return Node(
                "indexed_identifier",
                indices,
                id_token.value,
                id_token.line,
            )

    # ── gate declarations ──────────────────────────────

    @v_args(meta=True)
    def gate_decl_no_params(self, meta, children):
        id_val = children[0].value
        idlist_qubits = children[1]
        goplist_result = children[2]
        return Node(
            "def_gate",
            goplist_result,
            [id_val, idlist_qubits, []],
            meta.line,
        )

    @v_args(meta=True)
    def gate_decl_with_params(self, meta, children):
        id_val = children[0].value
        idlist_params = children[1]
        idlist_qubits = children[2]
        goplist_result = children[3]
        return Node(
            "def_gate",
            goplist_result,
            [id_val, idlist_qubits, idlist_params],
            meta.line,
        )

    def idlist(self, children):
        return [child.value for child in children]

    def goplist(self, children):
        return list(children)

    def goplist_uop(self, children):
        return children[0]

    @v_args(meta=True)
    def goplist_barrier(self, meta, children):
        idlist = children[1]
        return Node("barrier", idlist, None, meta.line)

    @v_args(meta=True)
    def goplist_reset(self, meta, children):
        idlist = children[1]
        return Node("reset", idlist, None, meta.line)

    # ── quantum operations ─────────────────────────────

    @v_args(meta=True)
    def measure_qop(self, meta, children):
        qubit = children[0]
        bit = children[2]
        return Node("measure", qubit, bit, meta.line)

    def argument(self, children):
        id_val = children[0].value
        if len(children) == 1:
            return [id_val]
        exp_result = children[1]
        if isinstance(exp_result, Node) and not exp_result.children:
            leaf = exp_result.leaf
            if leaf.isdigit():
                return [id_val, int(leaf)]
            if _ID_PATTERN.match(leaf) and leaf not in (
                "True",
                "False",
                "np.pi",
            ):
                return [id_val, leaf]
        return [id_val, exp_result]

    def qlist(self, children):
        return list(children)

    @v_args(meta=True)
    def uop_no_params(self, meta, children):
        id_val = children[0].value
        qlist_result = children[1]
        return Node("uop", [id_val, []], qlist_result, meta.line)

    @v_args(meta=True)
    def uop_with_params(self, meta, children):
        id_val = children[0].value
        explist_result = children[1]
        qlist_result = children[2]
        return Node(
            "uop",
            [id_val, explist_result],
            qlist_result,
            meta.line,
        )

    def explist(self, children):
        return list(children)

    # ── control flow ───────────────────────────────────

    @v_args(meta=True)
    def if_statement(self, meta, children):
        # PLY index quirk: p[5] is NUMBER (not EQ), p[7] is qop (not NUMBER)
        # so Node children=[id, number], leaf=qop
        id_val = children[0].value
        number = int(children[2].value)
        qop_result = children[3]
        return Node("if_statement", [id_val, number], qop_result, meta.line)

    @v_args(meta=True)
    def for_statement(self, meta, children):
        scalar_type = children[0]
        id_val = children[1].value
        for_source_result = children[2]
        block_body_result = children[3]
        leaf_type, value = for_source_result
        return Node(
            "for_statement",
            [scalar_type, id_val, "in", value, block_body_result],
            leaf_type,
            meta.line,
        )

    def for_source_number(self, children):
        return ("in_number", int(children[0].value))

    def for_source_range(self, children):
        return ("in_range_exp", children[0])

    def for_source_id(self, children):
        return ("in_id", children[0].value)

    def for_source_array(self, children):
        return ("in_array", children[0])

    @v_args(meta=True)
    def range_exp(self, meta, children):
        return Node("range_exp", list(children), None, meta.line)

    def expression01_exp(self, children):
        return children[0]

    def expression01_empty(self, children):
        del children
        return Node("empty", None, None, 0)

    def block_body(self, children):
        if children:
            pos = _token_line(children[0])
        else:
            pos = 0
        return Node("block_body", list(children), None, pos)

    @v_args(meta=True)
    def barrier_statement(self, meta, children):
        qlist = children[1]
        return Node("barrier", qlist, None, meta.line)

    @v_args(meta=True)
    def reset_statement(self, meta, children):
        qlist = children[1]
        return Node("reset", qlist, None, meta.line)

    # ── expression hierarchy ───────────────────────────

    def add_exp(self, children):
        result = children[0]
        i = 1
        while i < len(children):
            op = children[i].value
            rval = children[i + 1]
            result = Node("exp", [result, rval], op, _token_line(result))
            i += 2
        return result

    def mul_exp(self, children):
        result = children[0]
        i = 1
        while i < len(children):
            op = children[i].value
            rval = children[i + 1]
            result = Node("exp", [result, rval], op, _token_line(result))
            i += 2
        return result

    @v_args(meta=True)
    def neg_exp(self, meta, children):
        return Node("exp", [children[1]], "-", meta.line)

    def exp_real(self, children):
        token = children[0]
        return Node("exp", [], str(float(token.value)), token.line)

    def exp_number(self, children):
        token = children[0]
        return Node("exp", [], str(int(token.value)), token.line)

    def exp_pi(self, children):
        token = children[0]
        return Node("exp", [], "np.pi", token.line)

    def exp_id(self, children):
        token = children[0]
        return Node("exp", [], token.value, token.line)

    def exp_bool(self, children):
        token = children[0]
        if token.value == "true":
            return Node("exp", [], "True", token.line)
        return Node("exp", [], "False", token.line)

    def exp_paren(self, children):
        return children[0]

    @v_args(meta=True)
    def exp_func(self, meta, children):
        func_name = children[0]
        formula_input = children[1]
        template = _FUNC_TEMPLATES.get(func_name)
        if template is None:
            raise SyntaxError(
                f"in line {meta.line}, {func_name} is not a legal operator"
            )
        return Node("exp", [formula_input], template, meta.line)

    def unaryop(self, children):
        return children[0].value


# ── Public API (signatures unchanged) ──────────────────────


def get_abs_tree(data):
    """Parse OpenQASM source and return the AST root Node.

    Args:
        data: OpenQASM source string

    Returns:
        Node: the root node of the abstract syntax tree
    """
    try:
        tree = _lark_parser.parse(data)
    except UnexpectedInput as e:
        if isinstance(e, UnexpectedToken):
            raise SyntaxError(
                f"in line {e.line}, "
                f"can not parser the sentence at token: "
                f"'{e.token}'"
            ) from e
        raise SyntaxError(f"in line {e.line}, {e}") from e
    transformer = QasmTransformer()
    node = transformer.transform(tree)
    return node


def get_ir(abs_tree):
    """Convert AST to intermediate representation.

    Args:
        abs_tree: abstract syntax tree root node

    Returns:
        QuantumCircuit: the quantum circuit intermediate representation
    """
    vist = Visitor()
    return vist.visit_program(abs_tree)


def compile(data):
    """Compile OpenQASM source into quantum operations.

    Args:
        data: OpenQASM source string

    Returns:
        tuple: (num_qubits, operations list)
    """
    abs_tree = get_abs_tree(data)
    circuit = get_ir(abs_tree)
    return circuit.num_qubits, circuit.get_operations()


class Parser:
    """Parser class.

    The Parser class is used to parse quantum circuit files or directly
    provided quantum circuit objects.

    It can convert quantum circuits into circuits containing only single-qubit
    and two-qubit gates, and provides methods to export the circuit as a
    string in OpenQASM 2 format.
    """

    def __init__(self, src_code):
        """Initialize the Parser class.

        Args:
            src_code (str): Represent qasm.
        """
        self.basis_gates = [
            "h",
            "x",
            "y",
            "z",
            "cx",
            "cz",
            "rx",
            "ry",
            "rz",
            "u3",
            "s",
            "sdg",
            "t",
            "tdg",
        ]
        if not src_code:
            raise ValueError("The qasm parameter must be provided")

        # Parsing OpenQASM
        self.nqubits, self.ir = compile(src_code)
        self.quantum_circuit = QuantumCircuit()
        self.quantum_circuit.append_operations(self.ir)

        # TODO: need transpile to basis gates
        self.opt_circuit = self.ir
