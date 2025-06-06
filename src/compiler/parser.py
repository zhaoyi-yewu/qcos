from ply import (
    lex,
    yacc
)
from . import tokrules
from .tokrules import tokens
import time
from .qtypes import *
from .visitor import Visitor
from .decompose import transpiler, optimizer
from .gate_to_seq import gate_to_seq
from qcos.log.qcos_log import QCOSLogger

qcos_logger = QCOSLogger()

gate_params = []

# 根据具体的底层文法推断并记录openqasm版本，
# 然后对比推断的版本和源码中写的版本是否一致
# 目前只有[]和[3.0]两种可能。
openqasm_version = []


# 顶层文法

def p_mainprogram(mainprogram):
    """
    mainprogram : OPENQASM REAL ';' incfile ';' program
    """
    # '''program : programDef programBody'''

    if mainprogram[2] == 2.0 or mainprogram[2] == 3.0:
        if len(openqasm_version) == 0 or mainprogram[2] == openqasm_version[0]:
            pass
        else:
            raise TypeError(f"in line {mainprogram.lineno}: version error")
    else:
        raise TypeError(f"in line {mainprogram.lineno}: version error")
    mainprogram[0] = Node("top", mainprogram[6], None, mainprogram.lineno(6))
    openqasm_version.clear()


def p_arrayType(arrayType):
    """
    arrayType : ARRAY '[' scalarType ',' exp ']'
    """
    scalarType = arrayType[3]
    exp = arrayType[5]
    arrayType[0] = Node("arrayType", [scalarType, exp], None, arrayType.lineno(1))


def p_arrayLiteral(arrayLiteral):
    """
    arrayLiteral : '{' expOrArrayLiteral commaExpOrArrayLiteralList '}'
                 | '{' expOrArrayLiteral commaExpOrArrayLiteralList ',' '}'
                 | '{' empty '}'
    """
    if len(arrayLiteral) == 4:
        # 空数组情况
        arrayLiteral[0] = Node("arrayLiteral", [], None, arrayLiteral.lineno(1))
    else:
        expOrArrayLiteral = arrayLiteral[2]
        commaExpOrArrayLiteralList = arrayLiteral[3]
        arrayLiteral[0] = Node("arrayLiteral", [expOrArrayLiteral] + commaExpOrArrayLiteralList, None, arrayLiteral.lineno(2))


def p_expOrArrayLiteral(expOrArrayLiteral):
    """
    expOrArrayLiteral : exp
                      | arrayLiteral
    """
    expOrArrayLiteral[0] = expOrArrayLiteral[1]


def p_commaExpOrArrayLiteralList(commaExpOrArrayLiteralList):
    """
    commaExpOrArrayLiteralList : empty
                               | ',' expOrArrayLiteral
                               | commaExpOrArrayLiteralList ',' expOrArrayLiteral
    """
    if len(commaExpOrArrayLiteralList) == 2:
        # 当commaExpOrArrayLiteralList[1]是empty
        commaExpOrArrayLiteralList[0] = []
    elif len(commaExpOrArrayLiteralList) == 3:
        expOrArrayLiteral = commaExpOrArrayLiteralList[2]
        commaExpOrArrayLiteralList[0] = [expOrArrayLiteral]
    else:
        expOrArrayLiteral = commaExpOrArrayLiteralList[3]
        commaExpOrArrayLiteralList[0] = commaExpOrArrayLiteralList[1] + [expOrArrayLiteral]


def p_assignmentStatement(assignmentStatement):
    """
    assignmentStatement : indexedIdentifier '=' exp ';'
    """
    indexedIdentifier = assignmentStatement[1]
    equal = assignmentStatement[2]
    exp = assignmentStatement[3]
    assignmentStatement[0] = Node("assignmentStatement", [indexedIdentifier, equal, exp], None, indexedIdentifier.pos)


def p_indexedIdentifier(indexedIdentifier):
    """
    indexedIdentifier : ID
                      | indexedIdentifier indexOperator
    """
    if len(indexedIdentifier) == 2:
        ID = indexedIdentifier[1]
        indexedIdentifier[0] = Node("indexedIdentifier", [], ID, indexedIdentifier.lineno(1))
    else:
        indexedIdentifier[0] = Node("indexedIdentifier", indexedIdentifier[1].children + [indexedIdentifier[2]], indexedIdentifier[1].leaf, indexedIdentifier[1].pos)


def p_indexOperator(indexOperator):
    """
    indexOperator : '[' exp ']'
    """
    exp = indexOperator[2]
    indexOperator[0] = exp


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
              | gatedecl
              | qop
              | BARRIER qlist ';'
              | ifStatement
              | forStatement
              | classicalDeclarationStatement
              | assignmentStatement
    """
    if len(statement) == 2:
        statement[0] = statement[1]
    else:
        statement[0] = Node('barrier', statement[2], None, statement.lineno(1))


def p_forStatement(forStatement):
    """
    forStatement : FOR scalarType ID IN NUMBER '{' blockBody '}'
                 | FOR scalarType ID IN '[' rangeExpression ']' '{' blockBody '}'
                 | FOR scalarType ID IN ID '{' blockBody '}'
    """
    ID = forStatement[3]
    scalarType = forStatement[2]
    if len(forStatement) == 9:
        loopCondition = forStatement[5]
        if isinstance(loopCondition, str):
            forStatement[0] = Node('forStatement', [scalarType, ID, forStatement[4], forStatement[5], forStatement[7]], "inID", forStatement.lineno(1))
        else:
            forStatement[0] = Node('forStatement', [scalarType, ID, forStatement[4], forStatement[5], forStatement[7]], "inNumber", forStatement.lineno(1))
    elif len(forStatement) == 11:
        forStatement[0] = Node('forStatement', [scalarType, forStatement[3], forStatement[4], forStatement[6], forStatement[9]], "inRangeExpression", forStatement.lineno(1))


def p_rangeExpression(p):
    """
    rangeExpression : expression01 ':' expression01 ':' exp
                    | expression01 ':' expression01
    """
    if len(p) == 4:
        p[0] = Node("rangeExpression", [p[1], p[3]], None, p.lineno(1))
    elif len(p) == 6:
        p[0] = Node("rangeExpression", [p[1], p[3], p[5]], None, p.lineno(1))


def p_expression01(expression01):
    """
    expression01 : empty
                 | exp
    """
    emptyOrExp = expression01[1]
    expression01[0] = emptyOrExp


def p_classicalDeclarationStatement(p):
    """
    classicalDeclarationStatement : scalarType ID '=' exp ';'
                                  | scalarType ID '=' NUMBER ';'
                                  | arrayType ID '=' arrayLiteral ';'
                                  | scalarType ID '=' REAL ';'
                                  | scalarType ID '=' BooleanLiteral ';'
                                  | scalarType ID ';'
    """
    scalarType = p[1]
    ID = p[2]
    if len(p) == 6:
        expANDarrayLiteral = p[4]
        p[0] = Node("classicalDeclarationStatement", [scalarType, ID, expANDarrayLiteral], None, p.lineno(2))
    else:
        p[0] = Node("classicalDeclarationStatement", [scalarType, ID], None, p.lineno(2))


def p_scalarType(scalarType):
    """
    scalarType : INT designator01
               | FLOAT designator01
               | BOOL
    """
    # 这个节点表明openqasm应该使用3.0版本。
    if len(openqasm_version) == 0:
        openqasm_version.append(3.0)

    if scalarType[1] == 'int':
        scalarType[0] = Node('scalarType', None, 'int', scalarType.lineno(1))
    elif scalarType[1] == 'float':
        scalarType[0] = Node('scalarType', None, 'float', scalarType.lineno(1))
    elif scalarType[1] == 'bool':
        scalarType[0] = Node('scalarType', None, 'bool', scalarType.lineno(1))


def p_designator(designator):
    """
    designator : '[' exp ']'
    """
    exp = designator[2]
    designator[0] = exp


def p_designator01(designator01):
    """designator01 : empty
                    | designator """
    emptyOrDesignator = designator01[1]
    designator01[0] = emptyOrDesignator


def p_blockBody(blockBody):
    """ blockBody : empty
                  | statement
                  | blockBody statement """
    if len(blockBody) == 2:
        emptyOrStatement = blockBody[1]
        blockBody[0] = Node("blockBody", [emptyOrStatement], None, blockBody.lineno(1))
    elif len(blockBody) == 3:
        statement = blockBody[2]
        blockBody[1].children.append(statement)
        blockBody[0] = blockBody[1]
    else:
        raise SyntaxError(f'in line {blockBody.lineno(1)}, appears undefined tree')


def p_empty(empty):
    """
    empty :
    """
    empty[0] = Node('empty', None, None, empty.lineno(0))


def p_decl(decl):
    """
    decl : QREG ID '[' NUMBER ']' ';'
         | CREG ID '[' NUMBER ']' ';'
    """
    ID = decl[2]
    NUMBER = decl[4]
    QREGorCREG = decl[1]
    decl[0] = Node("defvar", [ID, NUMBER], QREGorCREG, decl.lineno(2))


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

    QUBITorBIT = decl3[1]
    if len(decl3) == 7:
        NUMBER = decl3[3]
        ID = decl3[5]
        decl3[0] = Node("defvar3", [NUMBER, ID], QUBITorBIT, decl3.lineno(0))
    else:
        ID = decl3[2]
        decl3[0] = Node("defvar3", [ID], QUBITorBIT, decl3.lineno(0))


def p_gatedecl(gatedecl):
    """
    gatedecl : GATE ID idlist '{' goplist '}'
             | GATE ID '(' idlist ')' idlist '{' goplist '}'
    """
    if len(gatedecl) == 7:
        goplist = gatedecl[5]
        ID = gatedecl[2]
        idlist = gatedecl[3]
        gatedecl[0] = Node('defgate', goplist, [ID, idlist, []], gatedecl.lineno(2))
    else:
        ID = gatedecl[2]
        goplist = gatedecl[8]
        idlist0 = gatedecl[6]
        idlist1 = gatedecl[4]
        gatedecl[0] = Node('defgate', goplist, [ID, idlist0, idlist1], gatedecl.lineno(2))


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
    goplist : uop
            | BARRIER idlist ';'
            | goplist uop
            | goplist BARRIER idlist ';'
    """
    if len(goplist) == 2:
        uop = goplist[1]
        goplist[0] = [uop]
    elif len(goplist) == 3:
        BARRIER = goplist[2]
        goplist[0] = goplist[1] + [BARRIER]
    elif len(goplist) == 4:
        idlist = goplist[2]
        goplist[0] = [Node('barrier', idlist, None, goplist.lineno(1))]
    else:
        idlist = goplist[2]
        goplist[0] = goplist[1] + [Node('barrier', idlist, None, goplist.lineno(2))]


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
        qop[0] = Node('measure', qubit, bit, qop.lineno(1))


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
        | BooleanLiteral
        | '(' exp ')'
        | exp '+' exp
        | exp '-' exp
        | exp '*' exp
        | exp '/' exp
        | '-' exp
        | unaryop '(' exp ')'
    """
    if len(exp) == 2:
        if exp[1] == 'pi':
            exp[0] = Node("exp", [], 'np.pi', exp.lineno(1))
        else:
            exp[0] = Node("exp", [], str(exp[1]), exp.lineno(1))
    elif len(exp) == 3:
        exp[0] = Node("exp", [exp[2]], '-', exp.lineno(1))
    elif len(exp) == 4:
        if exp[1] == '(':
            exp[0] = exp[2]
        else:
            # 加减乘除
            operator = exp[2]
            lval = exp[1]
            rval = exp[3]
            exp[0] = Node("exp", [lval, rval], f'{operator}', exp.lineno(1))
    else:
        mathFormula = exp[1]
        formulaInput = exp[3]
        if mathFormula == 'sin':
            exp[0] = Node("exp", [formulaInput], 'np.sin({})', exp.lineno(1))
        elif mathFormula == 'cos':
            exp[0] = Node("exp", [formulaInput], 'np.cos({})', exp.lineno(1))
        elif mathFormula == 'tan':
            exp[0] = Node("exp", [formulaInput], 'np.tan({})', exp.lineno(1))
        elif mathFormula == 'exp':
            exp[0] = Node("exp", [formulaInput], 'np.exp({})', exp.lineno(1))
        elif mathFormula == 'ln':
            exp[0] = Node("exp", [formulaInput], 'np.log({})', exp.lineno(1))
        elif mathFormula == 'sqrt':
            exp[0] = Node("exp", [formulaInput], 'np.sqrt({})', exp.lineno(1))
        else:
            raise SyntaxError(f"in line {exp.lineno}, {mathFormula} is not a legal operator")


def p_unaryop(unaryop):
    """
    unaryop : SIN
            | COS
            | TAN
            | EXP
            | LN
            | SQRT
    """
    mathFormula = unaryop[1]
    unaryop[0] = mathFormula


def p_ifStatement(ifStatement):
    """
    ifStatement : IF '(' ID EQ NUMBER ')' qop
    """
    ID = ifStatement[3]
    EQ = ifStatement[5]
    NUMBER = ifStatement[7]
    ifStatement[0] = Node("ifStatement", [ID, EQ], NUMBER, ifStatement.lineno(1))


def p_error(error):
    if isinstance(error, lex.LexToken):
        raise SyntaxError(f"in line {error.lineno}, can not parser the sentence at token: '{error.value}'")
    else:
        raise SyntaxError("lack ';' or '}' at the end of code")


def get_abs_tree(data):
    """
    解析OpenQASM，得到抽象语法树
    参数:
    data (_type_): OpenQASM
    返回:
    Node: 解析后的抽象语法树头节点
    """
    lexer = lex.lex(module=tokrules)
    lexer.input(data)
    parser = yacc.yacc(debug=False, write_tables=False)
    return parser.parse(data)


def get_ir(abs_tree):
    """
    解析抽象语法树，得到中间表示，其为Gate列表
    参数:
    abs_tree (_type_): 抽象语法树
    返回:
    Tuple (int, list): 量子比特总数、解析得到的量子门列表
    """
    vist = Visitor()
    return vist.visit_program(abs_tree)


def compile(data):
    """
    解析OpenQasm2.0，得到对应的脉冲序列
    参数:
    data (_type_): OpenQASM
    返回:
    Tuple (int, list, list): 量子比特总数、解析得到的量子门列表
    """
    lexer = lex.lex(module=tokrules)
    lexer.input(data)
    parser = yacc.yacc(debug=False, write_tables=False)
    ast_node = parser.parse(data)
    vist = Visitor()
    q_num, ir = vist.visit_program(ast_node)
    # 针对初始的ir进行一次优化，可以消去一些连续执行的酉门，如两个H门
    optimized_ir = optimizer(ir)
    transpiled_gates = transpiler(optimized_ir)
    # 针对分解后的ir进行优化，主要是针对分解后可能存在的连续两个相同的旋转门
    optimized_gates = optimizer(transpiled_gates)
    pulse_seqs, measure_qubits = gate_to_seq(optimized_gates)
    return q_num, pulse_seqs, measure_qubits
