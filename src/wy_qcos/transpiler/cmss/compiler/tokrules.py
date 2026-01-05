#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

t_EQ = r"\=\="
t_ignore = " \t\r"
t_ARROW = r"->"


# 解析错误的时候直接抛出异常
def t_error(lex_error):
    raise SyntaxError(
        f"in line {lex_error.lineno}, "
        f"lex error at token : {lex_error.value[0]}"
    )


# 记录行号，方便出错定位
def t_newline(line_num):
    r"""\n+"""
    line_num.lexer.lineno += len(line_num.value)


# 支持c++风格的\\注释
def t_ignore_comment(comments):
    r"""\/\/[^\n]*"""


# 常数命令规则
def t_REAL(real):
    r"""([0-9]+\.[0-9]*|[0-9]*\.[0-9]+)([eE][-+]?[0-9]+)?"""
    real.value = float(real.value)
    return real


def t_NUMBER(number):
    r"""[1-9]+[0-9]*|0"""
    number.value = int(number.value)
    return number


def t_BOOL(boolean):
    r"""true|false"""
    if boolean.value == "true":
        boolean.value = bool(1)
    else:
        boolean.value = bool(0)
    return boolean


def t_STDFILE(t):
    r"""qelib1.inc|stdgates.inc"""
    return t


# 标识符的命令规则
def t_ID(t):
    r"""[a-zA-Z\_][a-zA-Z\_0-9]*"""
    t.type = reserved.get(t.value, "ID")  # Check for reserved words
    return t


reserved = {
    "OPENQASM": "OPENQASM",
    "include": "INCLUDE",
    "if": "IF",
    "qreg": "QREG",
    "creg": "CREG",
    "bit": "BIT",
    "qubit": "QUBIT",
    "gate": "GATE",
    "measure": "MEASURE",
    "pi": "PI",
    "sin": "SIN",
    "cos": "COS",
    "tan": "TAN",
    "exp": "EXP",
    "ln": "LN",
    "sqrt": "SQRT",
    "barrier": "BARRIER",
    "for": "FOR",
    "int": "INT",
    "in": "IN",
    "array": "ARRAY",
    "float": "FLOAT",
    "bool": "BOOL",
    "reset": "RESET",
}

# 输入中支持的符号头token，当然也支持t_PLUS = r'\+'的方式将加号定义为token
literals = [
    "+",
    "-",
    "*",
    "/",
    "%",
    "<",
    ">",
    "=",
    ",",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    ";",
    ":",
    '"',
]

tokens = ["EQ", "REAL", "NUMBER", "ID", "ARROW", "STDFILE"] + list(
    reserved.values()
)
