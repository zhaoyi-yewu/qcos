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

from ply import lex, yacc

from wy_qcos.transpiler.cmss.compiler import tokrules
from wy_qcos.transpiler.cmss.compiler.tokrules import tokens
from wy_qcos.transpiler.cmss.compiler.qtypes import Node
from wy_qcos.transpiler.cmss.compiler.visitor import Visitor
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit


gate_params = []

# 根据具体的底层文法推断并记录openqasm版本，
# 然后对比推断的版本和源码中写的版本是否一致
# 目前只有[2.0]和[3.0]两种可能。
openqasm_version = []


# 顶层文法


def p_main_program(main_program):
    """
    main_program : OPENQASM REAL ';' incfile ';' program
    """
    if main_program[2] == 2.0 or main_program[2] == 3.0:
        if (
            len(openqasm_version) == 0
            or main_program[2] == openqasm_version[0]
        ):
            pass
        else:
            raise TypeError(f"in line {main_program.lineno}: version error")
    else:
        raise TypeError(f"in line {main_program.lineno}: version error")
    main_program[0] = Node(
        "top", main_program[6], None, main_program.lineno(6)
    )
    openqasm_version.clear()


def p_array_type(array_type):
    """
    array_type : ARRAY '[' scalar_type ',' exp ']'
    """
    scalar_type = array_type[3]
    exp = array_type[5]
    array_type[0] = Node(
        "array_type", [scalar_type, exp], None, array_type.lineno(1)
    )


def p_array_literal(array_literal):
    # pylint: disable=line-too-long
    """
    array_literal : '{' exp_or_array_literal comma_or_array_literal_list '}'
                  | '{' exp_or_array_literal comma_or_array_literal_list ',' '}'
                  | '{' empty '}'
    """
    # pylint: enable=line-too-long
    if len(array_literal) == 4:
        # 空数组情况
        array_literal[0] = Node(
            "array_literal", [], None, array_literal.lineno(1)
        )
    else:
        exp_or_array_literal = array_literal[2]
        comma_or_array_literal_list = array_literal[3]
        array_literal[0] = Node(
            "array_literal",
            [exp_or_array_literal] + comma_or_array_literal_list,
            None,
            array_literal.lineno(2),
        )


def p_exp_or_array_literal(exp_or_array_literal):
    """
    exp_or_array_literal : exp
                         | array_literal
    """
    exp_or_array_literal[0] = exp_or_array_literal[1]


def p_comma_or_array_literal_list(comma_or_array_literal_list):
    # pylint: disable=line-too-long
    """
    comma_or_array_literal_list : empty
                                | ',' exp_or_array_literal
                                | comma_or_array_literal_list ',' exp_or_array_literal
    """
    # pylint: enable=line-too-long
    if len(comma_or_array_literal_list) == 2:
        # comma_or_array_literal_list[1]是empty
        comma_or_array_literal_list[0] = []
    elif len(comma_or_array_literal_list) == 3:
        exp_or_array_literal = comma_or_array_literal_list[2]
        comma_or_array_literal_list[0] = [exp_or_array_literal]
    else:
        exp_or_array_literal = comma_or_array_literal_list[3]
        comma_or_array_literal_list[0] = comma_or_array_literal_list[1] + [
            exp_or_array_literal
        ]


def p_assign_statement(assign_statement):
    """
    assign_statement : indexed_identifier '=' exp ';'
    """
    indexed_identifier = assign_statement[1]
    equal = assign_statement[2]
    exp = assign_statement[3]
    assign_statement[0] = Node(
        "assign_statement",
        [indexed_identifier, equal, exp],
        None,
        indexed_identifier.pos,
    )


def p_indexed_identifier(indexed_identifier):
    """
    indexed_identifier : ID
                       | indexed_identifier index_operator
    """
    if len(indexed_identifier) == 2:
        ID = indexed_identifier[1]
        indexed_identifier[0] = Node(
            "indexed_identifier", [], ID, indexed_identifier.lineno(1)
        )
    else:
        indexed_identifier[0] = Node(
            "indexed_identifier",
            indexed_identifier[1].children + [indexed_identifier[2]],
            indexed_identifier[1].leaf,
            indexed_identifier[1].pos,
        )


def p_index_operator(index_operator):
    """
    index_operator : '[' exp ']'
    """
    exp = index_operator[2]
    index_operator[0] = exp


def p_incfile(incfile):
    """
    incfile : INCLUDE '"' STDFILE '"'
    """
    STDFILE = incfile[3]
    incfile[0] = STDFILE


def p_program(program):
    """
    program : statement
            | program statement
    """
    if len(program) == 2:
        statement = program[1]
        program[0] = [statement]
    else:
        statement = program[2]
        program[0] = program[1] + [statement]


def p_statement(statement):
    """
    statement : decl
              | decl3
              | gate_decl
              | qop
              | BARRIER qlist ';'
              | if_statement
              | for_statement
              | classical_declare_statement
              | assign_statement
              | RESET qlist ';'
    """
    if len(statement) == 2:
        statement[0] = statement[1]
    else:
        # reset or barrier
        node_type = statement[1]
        id_list = statement[2]
        statement[0] = Node(node_type, id_list, None, statement.lineno(1))


def p_for_statement(for_stmt):
    """
    for_statement : FOR scalar_type ID IN NUMBER '{' block_body '}'
                  | FOR scalar_type ID IN '[' range_exp ']' '{' block_body '}'
                  | FOR scalar_type ID IN ID '{' block_body '}'
                  | FOR scalar_type ID IN array_literal '{' block_body '}'
    """
    id = for_stmt[3]
    scalar_type = for_stmt[2]
    if len(for_stmt) == 9:
        loop_condition = for_stmt[5]
        if isinstance(loop_condition, str):
            for_stmt[0] = Node(
                "for_statement",
                [scalar_type, id, for_stmt[4], for_stmt[5], for_stmt[7]],
                "in_id",
                for_stmt.lineno(1),
            )
        elif isinstance(loop_condition, int):
            for_stmt[0] = Node(
                "for_statement",
                [scalar_type, id, for_stmt[4], for_stmt[5], for_stmt[7]],
                "in_number",
                for_stmt.lineno(1),
            )
        else:
            for_stmt[0] = Node(
                "for_statement",
                [scalar_type, id, for_stmt[4], for_stmt[5], for_stmt[7]],
                "in_array",
                for_stmt.lineno(1),
            )
    elif len(for_stmt) == 11:
        for_stmt[0] = Node(
            "for_statement",
            [scalar_type, for_stmt[3], for_stmt[4], for_stmt[6], for_stmt[9]],
            "in_range_exp",
            for_stmt.lineno(1),
        )
    # pylint: enable=line-too-long


def p_range_exp(range):
    """
    range_exp : expression01 ':' expression01 ':' exp
              | expression01 ':' expression01
    """
    if len(range) == 4:
        range[0] = Node(
            "range_exp", [range[1], range[3]], None, range.lineno(1)
        )
    elif len(range) == 6:
        range[0] = Node(
            "range_exp", [range[1], range[3], range[5]], None, range.lineno(1)
        )


def p_expression01(expression01):
    """
    expression01 : empty
                 | exp
    """
    empty_or_exp = expression01[1]
    expression01[0] = empty_or_exp


def p_classical_declare_statement(p):
    """
    classical_declare_statement : scalar_type ID '=' exp ';'
                                | scalar_type ID '=' NUMBER ';'
                                | array_type ID '=' array_literal ';'
                                | scalar_type ID '=' REAL ';'
                                | scalar_type ID '=' BOOL ';'
                                | scalar_type ID ';'
    """
    scalar_type = p[1]
    id = p[2]
    if len(p) == 6:
        exp_and_array_literal = p[4]
        p[0] = Node(
            "classical_declare_statement",
            [scalar_type, id, exp_and_array_literal],
            None,
            p.lineno(2),
        )
    else:
        p[0] = Node(
            "classical_declare_statement", [scalar_type, id], None, p.lineno(2)
        )


def p_scalar_type(scalar_type):
    """
    scalar_type : INT designator01
               | FLOAT designator01
               | BOOL
    """
    # 这个节点表明openqasm应该使用3.0版本。
    if len(openqasm_version) == 0:
        openqasm_version.append(3.0)

    if scalar_type[1] == "int":
        scalar_type[0] = Node(
            "scalar_type", None, "int", scalar_type.lineno(1)
        )
    elif scalar_type[1] == "float":
        scalar_type[0] = Node(
            "scalar_type", None, "float", scalar_type.lineno(1)
        )
    elif scalar_type[1] == "bool":
        scalar_type[0] = Node(
            "scalar_type", None, "bool", scalar_type.lineno(1)
        )


def p_designator(designator):
    """
    designator : '[' exp ']'
    """
    exp = designator[2]
    designator[0] = exp


def p_designator01(designator01):
    """designator01 : empty
    | designator"""
    empty_or_designator = designator01[1]
    designator01[0] = empty_or_designator


def p_block_body(block_body):
    """block_body : empty
    | statement
    | block_body statement"""
    if len(block_body) == 2:
        empty_or_statement = block_body[1]
        block_body[0] = Node(
            "block_body", [empty_or_statement], None, block_body.lineno(1)
        )
    elif len(block_body) == 3:
        statement = block_body[2]
        block_body[1].children.append(statement)
        block_body[0] = block_body[1]
    else:
        raise SyntaxError(
            f"in line {block_body.lineno(1)}, " f"appears undefined tree"
        )


def p_empty(empty):
    """
    empty :
    """
    empty[0] = Node("empty", None, None, empty.lineno(0))


def p_decl(decl):
    """
    decl : QREG ID '[' NUMBER ']' ';'
         | CREG ID '[' NUMBER ']' ';'
    """
    id = decl[2]
    number = decl[4]
    qreg_or_creg = decl[1]
    decl[0] = Node("def_var", [id, number], qreg_or_creg, decl.lineno(2))


def p_decl3(decl3):
    """
    decl3 : QUBIT '[' NUMBER ']' ID ';'
          | QUBIT ID ';'
          | BIT '[' NUMBER ']' ID ';'
          | BIT ID ';'
    """
    # 表明仅OpenQASM3支持
    if len(openqasm_version) == 0:
        openqasm_version.append(3.0)

    qbit_or_bit = decl3[1]
    if len(decl3) == 7:
        number = decl3[3]
        id = decl3[5]
        decl3[0] = Node("def_var3", [number, id], qbit_or_bit, decl3.lineno(0))
    else:
        id = decl3[2]
        decl3[0] = Node("def_var3", [id], qbit_or_bit, decl3.lineno(0))


def p_gatedecl(gate_decl):
    """
    gate_decl : GATE ID idlist '{' goplist '}'
              | GATE ID '(' idlist ')' idlist '{' goplist '}'
    """
    if len(gate_decl) == 7:
        goplist = gate_decl[5]
        id = gate_decl[2]
        idlist = gate_decl[3]
        gate_decl[0] = Node(
            "def_gate", goplist, [id, idlist, []], gate_decl.lineno(2)
        )
    else:
        id = gate_decl[2]
        goplist = gate_decl[8]
        idlist0 = gate_decl[6]
        idlist1 = gate_decl[4]
        gate_decl[0] = Node(
            "def_gate", goplist, [id, idlist0, idlist1], gate_decl.lineno(2)
        )


def p_idlist(idlist):
    """
    idlist : ID
           | idlist ',' ID
    """
    if len(idlist) == 2:
        ID = idlist[1]
        idlist[0] = [ID]
    else:
        ID = idlist[3]
        idlist[0] = idlist[1] + [ID]


def p_goplist(goplist):
    """
    goplist : empty
            | uop
            | BARRIER idlist ';'
            | goplist uop
            | goplist BARRIER idlist ';'
            | RESET idlist ';'
            | goplist RESET idlist ';'

    """
    if len(goplist) == 2:
        uop = goplist[1]
        goplist[0] = [uop]
    elif len(goplist) == 3:
        uop = goplist[2]
        goplist[0] = goplist[1] + [uop]
    elif len(goplist) == 4:
        node_type = goplist[1]  # barrier or reset
        idlist = goplist[2]
        goplist[0] = [Node(node_type, idlist, None, goplist.lineno(1))]
    else:
        node_type = goplist[2]  # barrier or reset
        idlist = goplist[3]
        goplist[0] = goplist[1] + [
            Node(node_type, idlist, None, goplist.lineno(2))
        ]


def p_qop(qop):
    """
    qop : uop
        | MEASURE argument ARROW argument ';'
    """
    if len(qop) == 2:
        uop = qop[1]
        qop[0] = uop
    else:
        qubit = qop[2]
        bit = qop[4]
        qop[0] = Node("measure", qubit, bit, qop.lineno(1))


def p_argument(argument):
    """
    argument : ID
             | ID '[' NUMBER ']'
             | ID '[' ID ']'
             | ID '[' exp ']'
    """
    ID = argument[1]
    if len(argument) == 2:
        argument[0] = [ID]
    else:
        expOrIDorNumber = argument[3]
        argument[0] = [ID, expOrIDorNumber]


def p_qlist(qlist):
    """
    qlist : argument
          | qlist ',' argument
    """
    if len(qlist) == 2:
        argument = qlist[1]
        qlist[0] = [argument]
    else:
        argument = qlist[3]
        qlist[0] = qlist[1] + [argument]


def p_uop(uop):
    """
    uop : ID qlist ';'
        | ID '(' explist ')' qlist ';'
    """
    ID = uop[1]
    if len(uop) == 4:
        qlist = uop[2]
        uop[0] = Node("uop", [ID, []], qlist, uop.lineno(1))
    else:
        explist = uop[3]
        qlist = uop[5]
        uop[0] = Node("uop", [ID, explist], qlist, uop.lineno(1))


def p_explist(explist):
    """
    explist : exp
            | explist ',' exp
    """
    if len(explist) == 2:
        exp = explist[1]
        explist[0] = [exp]
    else:
        exp = explist[3]
        explist[0] = explist[1] + [exp]


def p_exp(exp):
    """
    exp : REAL
        | NUMBER
        | PI
        | ID
        | BOOL
        | '(' exp ')'
        | exp '+' exp
        | exp '-' exp
        | exp '*' exp
        | exp '/' exp
        | '-' exp
        | unaryop '(' exp ')'
    """
    if len(exp) == 2:
        if exp[1] == "pi":
            exp[0] = Node("exp", [], "np.pi", exp.lineno(1))
        else:
            exp[0] = Node("exp", [], str(exp[1]), exp.lineno(1))
    elif len(exp) == 3:
        exp[0] = Node("exp", [exp[2]], "-", exp.lineno(1))
    elif len(exp) == 4:
        if exp[1] == "(":
            exp[0] = exp[2]
        else:
            # 加减乘除
            operator = exp[2]
            lval = exp[1]
            rval = exp[3]
            exp[0] = Node("exp", [lval, rval], f"{operator}", exp.lineno(1))
    else:
        math_formula = exp[1]
        formula_input = exp[3]
        if math_formula == "sin":
            exp[0] = Node("exp", [formula_input], "np.sin({})", exp.lineno(1))
        elif math_formula == "cos":
            exp[0] = Node("exp", [formula_input], "np.cos({})", exp.lineno(1))
        elif math_formula == "tan":
            exp[0] = Node("exp", [formula_input], "np.tan({})", exp.lineno(1))
        elif math_formula == "exp":
            exp[0] = Node("exp", [formula_input], "np.exp({})", exp.lineno(1))
        elif math_formula == "ln":
            exp[0] = Node("exp", [formula_input], "np.log({})", exp.lineno(1))
        elif math_formula == "sqrt":
            exp[0] = Node("exp", [formula_input], "np.sqrt({})", exp.lineno(1))
        else:
            raise SyntaxError(
                f"in line {exp.lineno}, "
                f"{math_formula} is not a legal operator"
            )


def p_unaryop(unaryop):
    """
    unaryop : SIN
            | COS
            | TAN
            | EXP
            | LN
            | SQRT
    """
    math_formula = unaryop[1]
    unaryop[0] = math_formula


def p_if_statement(if_statement):
    """
    if_statement : IF '(' ID EQ NUMBER ')' qop
    """
    id = if_statement[3]
    eq = if_statement[5]
    number = if_statement[7]
    if_statement[0] = Node(
        "if_statement", [id, eq], number, if_statement.lineno(1)
    )


def p_error(error):
    if isinstance(error, lex.LexToken):
        raise SyntaxError(
            f"in line {error.lineno}, "
            f"can not parser the sentence at token: "
            f"'{error.value}'"
        )
    raise SyntaxError("lack ';' or '}' at the end of code")


def get_abs_tree(data):
    """解析OpenQASM，得到抽象语法树

    Args:
        data: OpenQASM 语句

    Returns:
        解析后的抽象语法树头节点
    """
    lexer = lex.lex(module=tokrules)
    lexer.input(data)
    parser = yacc.yacc(debug=False, write_tables=False)
    try:
        node = parser.parse(data)
    except Exception as e:
        raise SyntaxError(e) from e
    return node


def get_ir(abs_tree):
    """解析抽象语法树，得到中间表示，其为Gate列表

    Args:
        abs_tree: 抽象语法树

    Returns:
        circuit(QuantumCircuit): 量子电路中间表示
    """
    vist = Visitor()
    return vist.visit_program(abs_tree)


def compile(data):
    """解析OpenQASM，得到抽象语法树

    Args:
        data: OpenQASM 语句

    Returns:
        num_qubits(int): 量子比特总数
        operations(list[BaseOperation]): 解析得到的量子门列表
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
        """Initialize the Parser class

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
