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

import numpy as np
import re
from typing import Any
from loguru import logger

from wy_qcos.transpiler.cmss.compiler.qtypes import Node, RegType
from wy_qcos.transpiler.cmss.common.gate_operation import create_gate
from wy_qcos.transpiler.cmss.circuit.quantum_circuit import QuantumCircuit
from wy_qcos.transpiler.cmss.compiler.linked_list import LinkedList, LinkedNode


class Visitor:
    """抽象语法树遍历类"""

    def __init__(self, allow_undefined=False) -> None:
        """
        初始化抽象语法树遍历类，设置其中的参数信息:

        :ivar q_var 量子变量字典，记录每个变量对应的数组长度
        :ivar q_map: 量子变量字典，记录每个变量对应物理比特的起始下标
        :ivar c_var: 经典变量字典，记录每个变量对应的数组长度
        :ivar c_map: 经典变量字典，记录每个变量对应物理比特的起始下标
        :ivar c_cnt: 经典变量总数
        :ivar built_in_gate: 内置门字典
        :ivar gate: 所有可用门字典，记录门作用比特数和所需参数个数
        :ivar defined_gate: 用户自定义门字典
        :ivar symbol_table: 符号表, openqasm3.0专用
        :ivar circuit: 量子电路中间表示(ir)
        """
        self.q_var = {}
        self.q_map = {}
        self.c_var = {}
        self.c_map = {}
        self.c_cnt = 0
        self.built_in_gates = {
            "h",
            "x",
            "y",
            "z",
            "s",
            "p",
            "sdg",
            "t",
            "tdg",
            "r",
            "rx",
            "ry",
            "rz",
            "sx",
            "sxdg",
            "cx",
            "CX",
            "cy",
            "cz",
            "ch",
            "swap",
            "crx",
            "cry",
            "crz",
            "cu1",
            "cp",
            "cu3",
            "csx",
            "cu",
            "rxx",
            "rzz",
            "ccx",
            "cswap",
            "rccx",
            "rc3x",
            "c3x",
            "c3sqrtx",
            "c4x",
            "u1",
            "u2",
            "u3",
            "u",
            "U",
        }
        self.gate = {
            "h": (1, 0),
            "x": (1, 0),
            "y": (1, 0),
            "z": (1, 0),
            "s": (1, 0),
            "p": (1, 1),
            "sdg": (1, 0),
            "t": (1, 0),
            "tdg": (1, 0),
            "r": (1, 2),
            "rx": (1, 1),
            "ry": (1, 1),
            "rz": (1, 1),
            "sx": (1, 0),
            "sxdg": (1, 0),
            "cx": (2, 0),
            "CX": (2, 0),
            "cy": (2, 0),
            "cz": (2, 0),
            "ch": (2, 0),
            "swap": (2, 0),
            "crx": (2, 1),
            "cry": (2, 1),
            "crz": (2, 1),
            "cu1": (2, 1),
            "cp": (2, 1),
            "cu3": (2, 3),
            "csx": (2, 0),
            "cu": (2, 4),
            "rxx": (2, 1),
            "rzz": (2, 1),
            "ccx": (3, 0),
            "cswap": (3, 0),
            "rccx": (3, 0),
            "rc3x": (4, 0),
            "c3x": (4, 0),
            "c3sqrtx": (4, 0),
            "c4x": (5, 0),
            "u1": (1, 1),
            "u2": (1, 2),
            "u3": (1, 3),
            "u": (1, 3),
            "U": (1, 3),
        }
        self.defined_gate = {}
        self.now_gate = ""
        self.in_gate = False
        self.measure_qubits = []
        self.allow_undefined = allow_undefined
        self.symbol_table = LinkedList()
        self._circuit = QuantumCircuit()

    def add_reg(self, reg_id, reg_size, reg_type, pos):
        """添加变量到相关字典中

        Args:
          reg_id: 变量名
          reg_size: 变量的长度
          reg_type: 变量类型
          pos: 所在位置

        Returns:

        """
        reg_dict = self.q_var
        if reg_type in ("creg", "bit"):
            reg_dict = self.c_var
        if reg_id in reg_dict:
            raise SyntaxError(f"in line {pos}, {reg_type} redefined")

        reg_dict[reg_id] = reg_size

        if reg_type in ("qreg", "qubit"):
            self.q_map[reg_id] = self._circuit.num_qubits
            new_num_qubits = self._circuit.num_qubits + reg_size
            self._circuit.set_num_qubits(new_num_qubits)
        else:
            self.c_map[reg_id] = self.c_cnt
            new_num_clbits = self._circuit.num_clbits + reg_size
            self._circuit.set_num_clbits(new_num_clbits)

    def check_reg(self, reg, reg_type: RegType, pos):
        """检查量子寄存器变量或者经典寄存器变量是否越界，若没有越界则返回其对应的物理比特下标
        否则报错。

        Args:
          reg: 寄存器变量
          reg_type: 寄存器变量类型
          pos: 所在位置
        :return List: 寄存器变量对应下标
          reg_type: RegType:

        Returns:

        """
        reg_id = reg[0]
        if reg_type == RegType.QREG:
            reg_dict = self.q_var
            reg_map = self.q_map
        else:
            reg_dict = self.c_var
            reg_map = self.c_map

        if reg_id not in reg_dict:
            raise NameError(f"in line {pos}, qreg {reg_id} is not defined")

        if len(reg) == 2:
            idx = reg[1]
            if idx >= reg_dict[reg_id]:
                raise IndexError(f"in line {pos}, creg {reg_id} out of bound")
            return list([reg_map[reg_id] + idx])
        else:
            return list(
                range(reg_map[reg_id], reg_map[reg_id] + reg_dict[reg_id])
            )

    def check_in_gate_qubit(self, qubit, pos):
        """检查门作用的量子比特是否已经定义

        Args:
          qubit: 门作用的量子比特
          pos: 所在位置

        Returns:

        """
        if len(qubit) != 1:
            raise NameError(f"in line {pos}, qubit is not defined")
        if qubit[0] not in self.defined_gate[self.now_gate]["gate_q"]:
            raise NameError(f"in line {pos}, qubit {qubit[0]} is not defined")

    def check_qlist(self, qids, pos):
        """检查量子比特是否重复使用在同一操作中

        Args:
          qids: 量子比特
          pos: 所在位置

        Returns:

        """
        if len(set(qids)) != len(qids):
            raise RuntimeError(f"in line {pos}, qubit reused")

    def visit_program(self, s: Node):
        """遍历抽象语法树的入口函数，通过dfs方法遍历根节点的所有子节点来完成遍历

        Args:
          s: mainprogram节点

        Returns:
            circuit(QuantumCircuit): 量子电路的中间表示
        """
        if s.type != "top":
            raise RuntimeError("OpenQASM version not specified")
        self.symbol_table.add_tail(LinkedNode({}), s)
        for state in s.children:
            self.visit_state(state)
        self.symbol_table.remove_tail()
        return self._circuit

    def visit_state(self, s: Node):
        """遍历所有语句，语句主要包括
            变量定义: 更新相关成员变量，将其添加至相关字典中
            门定义: 更新相关成员变量，将其添加至相关字典中
            量子操作: 递归遍历

        Args:
          s: 抽象语法树节点
          s: Node:

        Returns:

        """
        if s.type == "def_var":
            reg_type = s.leaf
            reg_id, reg_size = s.children
            self.check_var_name(reg_id, s.pos)
            self.add_reg(reg_id, reg_size, reg_type, s.pos)
        elif s.type == "def_var3":
            bit_type = s.leaf
            if len(s.children) == 1:
                bit_id = s.children[0]
                self.check_var_name(bit_id, s.pos)
                self.add_reg(bit_id, 1, bit_type, s.pos)
            else:
                bit_num, bit_id = s.children
                self.check_var_name(bit_id, s.pos)
                self.add_reg(bit_id, bit_num, bit_type, s.pos)
        elif s.type == "def_gate":
            gate_id = s.leaf[0]
            if gate_id in self.gate:
                # allow redefinition of built-in gates
                if gate_id in self.built_in_gates:
                    logger.warning(
                        f"in line {s.pos}, {gate_id} is a built-in gate"
                    )
                else:
                    raise SyntaxError(f"in line {s.pos}, {gate_id} redefined")
            self.gate[gate_id] = (len(s.leaf[1]), len(s.leaf[2]))
            self.defined_gate[gate_id] = {
                "gate_q": s.leaf[1],
                "gate_param": s.leaf[2],
                "base_gate": [],
            }
            self.in_gate = True
            self.now_gate = gate_id
            for gop in s.children:
                self.visit_qop(gop)
            self.in_gate = False
        elif s.type == "barrier":
            self.visit_barrier(s)
        elif s.type == "reset":
            self.visit_reset(s)
        elif s.type == "for_statement":
            self.visit_for_statement(s)
        elif s.type == "classical_declare_statement":
            self.visit_classical_declaration_statement(s)
        elif s.type == "assign_statement":
            self.visit_assignment_statement(s)
        else:
            self.visit_qop(s)

    def visit_barrier(self, s: Node):
        """检查量子比特已定义且无重复，若在自定义门中则添加相关元组以便后续解析
        否则直接添加同步操作的中间表示到结果列表中。

        Args:
          s: barrier节点
          s: Node:

        Returns:

        """
        self.check_node_type(s, "barrier")

        qids = []
        for qubit in s.children:
            if self.in_gate:
                self.check_in_gate_qubit(qubit, s.pos)
                qids.append(qubit[0])
            else:
                qlist = self.check_reg(qubit, RegType.QREG, s.pos)
                qids += qlist

        self.check_qlist(qids, s.pos)
        if self.in_gate:
            self.defined_gate[self.now_gate]["base_gate"].append(
                ("sync", [], qids)
            )
        else:
            self._circuit.append(create_gate("sync", qids))

    def visit_reset(self, s: Node):
        """检查量子比特已定义且无重复，若在自定义门中则添加相关元组以便后续解析
        否则直接添加Reset操作的中间表示到结果列表中。

        Args:
          s: reset 节点
          s: Node:

        Returns:

        """
        self.check_node_type(s, "reset")

        qids = []
        for qubit in s.children:
            if self.in_gate:
                self.check_in_gate_qubit(qubit, s.pos)
                qids.append(qubit[0])
            else:
                qlist = self.check_reg(qubit, RegType.QREG, s.pos)
                qids += qlist

        self.check_qlist(qids, s.pos)
        if self.in_gate:
            self.defined_gate[self.now_gate]["base_gate"].append(
                ("reset", [], qids)
            )
        else:
            self._circuit.append(create_gate("reset", qids))

    def visit_qop(self, s: Node):
        """量子操作分为三种

        - 同步：递归遍历
        - 测量：测量操作首先判断量子变量和经典变量是否可用，且比特没有重复测量
          在结果中添加测量的中间表示。
        - 门操作：递归遍历

        Args:
          s: qop节点
          s: Node:

        Returns:

        """
        if s.type == "measure":
            qids, cids = s.children, s.leaf
            qlist = self.check_reg(qids, RegType.QREG, s.pos)
            clist = self.check_reg(cids, RegType.CREG, s.pos)
            if len(qlist) != len(clist):
                raise RuntimeError(
                    f"in line {s.pos},"
                    f"the len of qregs and cregs is different"
                )
            for qubit in qlist:
                if qubit in self.measure_qubits:
                    raise RuntimeError(
                        f"in line {s.pos}," f"multiple measurements"
                    )
                self.measure_qubits.append(qubit)
                self._circuit.append(create_gate("measure", [qubit]))
        elif s.type == "barrier":
            self.visit_barrier(s)
        elif s.type == "reset":
            self.visit_reset(s)
        elif s.type == "if_statement":
            reg = s.children[0]
            val = s.children[1]
            # 判断id是否为定义的creg
            if reg not in self.c_var:
                raise NameError(f"in line {s.pos}, creg {reg} is not defined")
            bit_length = self.c_var[reg]
            if val > int("1" * bit_length, 2):
                raise RuntimeError(
                    f"in line {s.pos}, value {val} "
                    f"if always larger than creg {reg}"
                )
        elif s.type == "empty":
            return
        else:
            # self.visitUop(s)
            self.visit_uop_v3(s)

    def eval_gate(self, uid, args, qids, pos, func_dict=None):
        """解析自定义门中的子语句
        如果是全局的量子操作，则直接添加对应的中间表示,
        否则生成参数对应字典，该字典的键值对为自定义门的参数以及调用时实际使用值，
        用该字典以及eval函数来实现内联操作，将自定义门中的子语句转换为中间表示。

        Args:
          uid: 量子门类型
          args: 量子门参数
          qids: 量子门作用的量子比特
          pos: 所在位置
          func_dict: 函数字典 (Default value = None)

        Returns:

        """
        real_args = []

        # 为3.0特性做的改动
        for arg in args:
            # real_args.append(eval(arg, dic))
            value = self.get_call_param_value(arg, func_dict, pos)
            real_args.append(value)

        real_qids = []
        for qid in qids:
            if func_dict is not None and qid in func_dict:
                real_qids.append(func_dict[qid])
            else:
                real_qids.append(qid)

        if uid not in self.defined_gate:
            args = real_args
            if len(real_args) == 1:
                args = real_args[0]
            self._circuit.append(
                create_gate(uid, real_qids, args, self.allow_undefined)
            )
        else:
            for _uid, _args, _qids in self.defined_gate[uid]["base_gate"]:
                _dic = {}
                for param, val in zip(
                    self.defined_gate[uid]["gate_param"], real_args
                ):
                    _dic[param] = val
                for qreg, val in zip(
                    self.defined_gate[uid]["gate_q"], real_qids
                ):
                    _dic[qreg] = val
                self.eval_gate(_uid, _args, _qids, pos, _dic)

    def visit_for_statement(self, s: Node):
        """for 循环条件处理，创建for作用域符号表

        Args:
          s: for_statement 节点
          s: Node:

        Returns:

        """
        self.check_node_type(s, "for_statement")

        if s.leaf == "in_number":
            loop_count = s.children[3]

            # 检查loop_count是否为整数
            if not isinstance(loop_count, int):
                raise TypeError(f"in line {s.pos}, loop count should be int")

            iterator_var_type = s.children[0].leaf
            iterator_var_name = s.children[1]
            block_body = s.children[4]
            for i in range(loop_count):
                self.visit_for_block_body(
                    block_body, iterator_var_type, iterator_var_name, i
                )

        elif s.leaf == "in_id":
            id_name = s.children[3]
            id_dict = self.find_in_symbol_table(id_name, True)
            value = self.find_val_in_var_dict(id_dict, id_name, s.pos)
            id_type = self.find_type_in_var_dict(id_dict, id_name, s.pos)

            iterator_var_type = s.children[0].leaf
            iterator_var_name = s.children[1]

            # 检测类型是否为int
            if iterator_var_type != id_type != "int":
                raise TypeError(
                    f"in line {s.pos}, var {iterator_var_name} "
                    f"and var {id_name} should both be int type"
                )

            block_body = s.children[4]
            if isinstance(value, list):
                # in 后是数组变量的情况
                for i in value:
                    self.visit_for_block_body(
                        block_body, iterator_var_type, iterator_var_name, i
                    )
            else:
                # in 后是普通变量的情况
                for i in range(value):
                    self.visit_for_block_body(
                        block_body, iterator_var_type, iterator_var_name, i
                    )

        elif s.leaf == "in_range_exp":
            range_exp = s.children[3]
            iterator_var_name = s.children[1]
            iterator_var_type = s.children[0].leaf
            start, step, end = self.visit_range_expression(range_exp)
            while start < end:
                self.visit_for_block_body(
                    s.children[4], iterator_var_type, iterator_var_name, start
                )
                start = start + step

        elif s.leaf == "in_array":
            array_exp = s.children[3]
            iterator_var_name = s.children[1]
            iterator_var_type = s.children[0].leaf
            arr = self.visit_array_literal(array_exp)
            for i in arr:
                self.visit_for_block_body(
                    s.children[4], iterator_var_type, iterator_var_name, i
                )

    def visit_range_expression(self, s: Node):
        """处理 range_exp 节点, 用在for语句中

        Args:
          s: range_exp 节点
          s: Node:

        Returns:
          Tuple (int, int, int): 循环起点、步长、循环终点

        """
        self.check_node_type(s, "range_exp")

        start = 0
        step = 1
        end = 0
        if len(s.children) == 2:
            if s.children[0].type == "exp":
                start = self.visit_exp(s.children[0], True, s.pos)
            if s.children[1].type == "exp":
                end = self.visit_exp(s.children[1], True, s.pos)
        if len(s.children) == 3:
            if s.children[0].type == "exp":
                start = self.visit_exp(s.children[0], True, s.pos)
            if s.children[1].type == "exp":
                step = self.visit_exp(s.children[1], True, s.pos)
            end = self.visit_exp(s.children[2], True, s.pos)
        return start, step, end

    def visit_for_block_body(
        self, s: Node, iterator_type, iterator_name, cur_loop_count
    ):
        """处理for循环体中的每条语句

        Args:
          s: block_body 节点
          iterator_type: for循环体索引类型
          iterator_name: for循环体索引名
          cur_loop_count: 当前索引值
          s: Node:

        Returns:

        """
        self.check_node_type(s, "block_body")

        self.symbol_table.add_tail(LinkedNode({}), s)
        curr_symbol_table = self.symbol_table.get_tail()
        curr_symbol_table.data[iterator_name] = {
            "type": iterator_type,
            "val": cur_loop_count,
        }
        if isinstance(s.children, list):
            for child in s.children:
                if child.type == "empty":
                    continue
                self.visit_state(child)
        self.symbol_table.remove_tail()

    def visit_uop_v3(self, s: Node):
        """为支持openqasm 3.0特性而写，
        基于visitUop方法，新增对exp节点的处理

        Args:
          s: uop节点
          s: Node:

        Returns:

        """
        self.check_node_type(s, "uop")

        uid = s.children[0]
        if not self.allow_undefined:
            if uid not in self.gate:
                raise NameError(f"in line {s.pos}, gate {uid} is not defined")

        if uid in self.gate:
            qnum, pnum = self.gate[uid]
            if pnum != len(s.children[1]):
                raise RuntimeError(
                    f"in line {s.pos}, parameter error, "
                    f"need {pnum} but {len(s.children[1])}"
                )

            if qnum != len(s.leaf):
                raise RuntimeError(
                    f"in line {s.pos}, qubit error, "
                    f"need {qnum} but {len(s.leaf)}"
                )
        qids = []
        if self.in_gate:
            for qubit in s.leaf:
                self.check_in_gate_qubit(qubit, s.pos)
                qids.append(qubit[0])
            self.check_qlist(qids, s.pos)
            self.defined_gate[self.now_gate]["base_gate"].append(
                (uid, s.children[1], qids)
            )
        else:
            qreg_num = -1
            for qubit in s.leaf:
                if len(qubit) == 1:
                    id_list = self.check_reg(qubit, RegType.QREG, s.pos)
                    if qreg_num != -1 and len(id_list) != qreg_num:
                        raise RuntimeError(
                            f"in line {s.pos}, qreg length should be the same"
                        )
                    qreg_num = len(id_list)
                    for item in id_list:
                        qids.append(item)
                elif len(qubit) == 2:
                    temp = qubit[1]
                    qubit[1] = self.var_to_number(qubit, s.pos)
                    qids.append(self.check_reg(qubit, RegType.QREG, s.pos)[0])
                    qubit[1] = temp
                else:
                    raise RuntimeError(
                        f"in line {s.pos}, need to specific qubits"
                    )

            if qreg_num == -1:
                self.check_qlist(qids, s.pos)
                self.eval_gate(uid, s.children[1], qids, s.pos)
            else:
                for qubits in qids:
                    self.check_qlist([qubits], s.pos)
                    self.eval_gate(uid, s.children[1], [qubits], s.pos)

    def var_to_number(self, in_var, pos):
        """如果in_var[1]是整数返回值，
        如果in_var[1]是表达式节点，遍历处理表达式节点，
        如果in_var[1]是字符串，从符号表中取值

        Args:
          in_var: 变量
          pos: 所在位置
        :return Any: 变量对应的值

        Returns:

        """
        idx = in_var[1]
        if isinstance(idx, int):
            return idx
        if isinstance(idx, Node):
            return self.visit_exp(idx, False, pos)
        else:
            # 从符号表中找到
            value = self.find_val_in_symbol_table(idx, pos, False)
            return value

    def visit_classical_declaration_statement(self, s):
        """遍历经典变量声明语句，把变量的值放到符号表中。
        对于 scalar_type 类型变量，语法树支持声明和定义分开，但是变量使用时必须定义
        对于arrayType类型变量，声明时必须定义

        Args:
          s: Node): classical_declare_statement 节点

        Returns:

        """
        self.check_node_type(s, "classical_declare_statement")
        decl_name = s.children[1]
        self.check_var_name(decl_name, s.pos)
        if s.children[0].type == "scalar_type":
            if len(s.children) == 2:
                decl_val = None
            else:
                decl_val = s.children[2]
            if isinstance(decl_val, Node) and decl_val.type == "exp":
                decl_val = self.visit_exp(decl_val, True, s.pos)
            decl_type = s.children[0].leaf
            self.add_to_symbol_table(decl_type, decl_name, decl_val, s.pos)

        elif s.children[0].type == "array_type":
            scalar_type, length = self.visit_array_type(s.children[0])
            array_literal = s.children[2]

            if len(array_literal.children) != length:
                raise SyntaxError(
                    f"length in arrayType: {length}"
                    f"should be equal to the length in array_literal: "
                    f"{len(array_literal.children)}"
                )

            # 处理等号右边
            elements = self.visit_array_literal(array_literal)
            self.add_array_to_symbol_table(
                scalar_type, decl_name, length, elements, s.pos
            )
        else:
            # 当前不会执行的分支，预防后续开发带来的未察觉到的影响
            logger.warning(
                f"in line {s.pos} undefined scene: {s.children[0].type} "
                f"in classical_declare_statement"
            )
            raise SyntaxError(
                f"in line {s.pos} undefined scene: " f"{s.children[0].type}"
            )

    def visit_array_literal(self, s: Node) -> list:
        """处理数组字面值。
        如果元素是bool，int，float等基本类型，保存值。
        其他类型目前不考虑。

        Args:
          s: array_literal 节点
        :return List: 数组类型
          s: Node:

        Returns:

        """
        self.check_node_type(s, "array_literal")

        arr = []
        for child in s.children:
            val = self.visit_exp(child, True, s.pos)
            arr.append(val)
        return arr

    def visit_array_type(self, s: Node):
        """获取数组的类型与长度

        Args:
          s: array_type 节点
        :return Tuple (str, int): 数组类型、长度
          s: Node:

        Returns:

        """
        self.check_node_type(s, "array_type")

        scalar_type = s.children[0].leaf
        length = self.visit_exp(s.children[1], True, s.pos)
        if not isinstance(length, int):
            raise TypeError("array length should be int")

        return scalar_type, length

    def visit_assignment_statement(self, s: Node):
        """处理赋值语句

        Args:
          s: assign_statement 节点
          s: Node:

        Returns:

        """
        self.check_node_type(s, "assign_statement")

        indexed_identifier = s.children[0]
        val_name = indexed_identifier.leaf

        # 找到等号左侧变量所在的符号表
        symbol_table = self.find_symbol_table(val_name)

        if symbol_table is None:
            raise NameError(f"in line {s.pos}, variable a is not declared")

        # 如果indexed_identifier的children为空，说明不是数组变量赋值
        if not indexed_identifier.children:
            # 普通变量赋值
            assign_val = self.visit_exp(s.children[2], True, s.pos)
            self.modify_in_symbol_table(val_name, assign_val, s.pos, True)
        elif len(indexed_identifier.children) == 1:

            # 检查变量类型是否是数组
            var_dict = symbol_table.data[val_name]
            if "category" not in var_dict or var_dict["category"] != "array":
                raise TypeError(
                    f"in line {s.pos}, var {val_name} is not array"
                )

            # 一维数组变量赋值情况
            index_node = indexed_identifier.children[0]
            # 获取数组索引
            idx = self.visit_exp(index_node, True, s.pos)

            # 检查索引是否为整数
            if not isinstance(idx, int):
                raise TypeError(
                    f"in line {s.pos}, array index {idx} is not int"
                )

            # 检查数组索引是否越界
            if var_dict["length"] <= idx or idx < 0:
                raise IndexError(
                    f"in line {s.pos}, array index {idx} is out of bound"
                )

            # 获取等号右边的值
            rvalue = self.visit_exp(s.children[2], True, s.pos)

            # 赋值
            symbol_table.data[val_name][idx] = rvalue
        else:
            raise TypeError("目前只支持普通变量和一维数组赋值")

    def find_symbol_table(self, var_name: str):
        """获取变量名所在的符号表

        Args:
          var_name: 变量名
        :return LinkedNode: 变量所在作用域
          var_name: str:

        Returns:

        """
        symbol_table = self.symbol_table.get_tail()
        while symbol_table != self.symbol_table.get_head():
            if var_name in symbol_table.data:
                return symbol_table
            else:
                symbol_table = symbol_table.previous
        return None

    def add_to_symbol_table(self, var_type, var_name, value, pos):
        """把变量名和变量值作为键值对放到符号表中
        对于普通变量a，在字典中的存储格式是：
        {a:{"val":1,"type":"int","category":"default"}}

        Args:
          var_type: 变量类型
          var_name: 变量名
          value: 变量值
          pos: 所在位置

        Returns:

        """
        curr_symbol_table = self.symbol_table.get_tail().data
        if var_name in curr_symbol_table:
            raise SyntaxError(
                f"in line {pos}, variable {var_name} has been defined"
            )

        if value is None:
            curr_symbol_table[var_name] = {
                "val": None,
                "type": var_type,
                "category": "default",
            }
        else:
            if var_type == "int":
                val = int(value)
            elif var_type == "float":
                val = float(value)
            elif var_type == "bool":
                if value == "True":
                    val = 1
                else:
                    val = 0
            else:
                # 其他未定义类型，不会执行的分支。
                raise TypeError(f"undefined type in line {pos}")
            curr_symbol_table[var_name] = {
                "val": val,
                "type": var_type,
                "category": "default",
            }

    def add_array_to_symbol_table(
        self, var_type, var_name, length, elements, pos
    ):
        """把数组变量和它的元素放入符号表中，
        对于int数组变量arr，存储结构为：
        {"arr":{"type":"int","category":"array","length":1,"val":[1,2,3]}}
        目前数组在声明时必须定义。

        Args:
          var_type: 数组类型
          var_name: 数组名
          length: 数组长度
          elements: 数组元素
          pos: 所在位置

        Returns:

        """
        curr_symbol_table = self.symbol_table.get_tail().data

        # 检查变量名是否重复
        if var_name in curr_symbol_table:
            raise SyntaxError(
                f"in line {pos}, variable {var_name} has been defined"
            )

        # 检查elements中的每个元素类型是否正确。
        if var_type in ("int", "bool"):
            for idx, element in enumerate(elements):
                if not isinstance(element, int):
                    raise TypeError(f"{var_name}[{idx}] is not {var_type}")
        elif var_type == "float":
            for idx, element in enumerate(elements):
                if not isinstance(element, float):
                    raise TypeError(f"{var_name}[{idx}] is not {var_type}")
        else:
            raise TypeError(f"type: {var_type} is invalid")

        var_dict = {
            "type": var_type,
            "length": length,
            "val": elements,
            "category": "array",
        }
        curr_symbol_table[var_name] = var_dict

    def visit_exp(self, exp_node, is_recursion, pos):
        """遍历处理表达式节点，用于获取表达式具体的值，
        具体情况参考parser.py p_exp方法中exp节点的定义
        is_recursion 表示是否查询外层作用域的符号表

        Args:
          exp_node: 表达式节点
          is_recursion: 是否在当前作用域外查找
          pos: 所在位置
        :return Any: 表达式计算结果

        Returns:

        """
        self.check_node_type(exp_node, "exp")

        if len(exp_node.children) == 0:
            if exp_node.leaf.isdigit():
                return int(exp_node.leaf)
            elif self.is_float_regex(exp_node.leaf):
                return float(exp_node.leaf)
            elif exp_node.leaf == "np.pi":
                # return eval("np.pi")
                return 3.141592653589793
            elif exp_node.leaf == "True":
                return 1
            elif exp_node.leaf == "False":
                return 0
            else:
                value = self.find_val_in_symbol_table(
                    exp_node.leaf, pos, is_recursion
                )
                if value is None:
                    logger.error(f"in line {pos}, rVal not defined")
                    raise NameError(
                        f"in line {pos}, variable {exp_node.leaf} "
                        f"is only declared but not defined"
                    )
                return value

        if len(exp_node.children) == 2:
            l_val = self.visit_exp(exp_node.children[0], is_recursion, pos)
            r_val = self.visit_exp(exp_node.children[1], is_recursion, pos)
            if exp_node.leaf == "-":
                return l_val - r_val
            elif exp_node.leaf == "+":
                return l_val + r_val
            elif exp_node.leaf == "*":
                return l_val * r_val
            elif exp_node.leaf == "/":
                if not r_val:
                    raise ZeroDivisionError(
                        f"in line {pos}, divide by zero error"
                    )
                return l_val / r_val

        if len(exp_node.children) == 1:
            if exp_node.leaf == "-":
                val = self.visit_exp(exp_node.children[0], is_recursion, pos)
                return -val

        raise RuntimeError(f"in line {pos}, unexpected scene in visit exp")

    def modify_in_symbol_table(
        self, var_name: str, value: Any, pos: int, is_recursion: bool = True
    ):
        """在符号表中修改变量的值

        Args:
          var_name: 变量名
          value: 变量值
          pos: 所在位置
          is_recursion: 是否在当前作用域外查找
          var_name: str:
          value: Any:
          pos: int:
          is_recursion: bool:  (Default value = True)

        Returns:

        """
        is_var = False
        curr_symbol_table = self.symbol_table.get_tail()
        while curr_symbol_table != self.symbol_table.get_head():
            if var_name in curr_symbol_table.data:
                if value is None:
                    logger.error(f"in line {pos}, rVal not defined")
                    raise NameError(f"var {var_name} is not defined")
                val_type = curr_symbol_table.data[var_name]["type"]
                if val_type == "bool":
                    # 因为bool变量在符号表中的存储格式为
                    # b:{"val":1, "val_type":bool, "category":default}
                    # 我们保存0，1来表示true，false.所以value的值可能为0和1
                    if value in (1, 0):
                        curr_symbol_table.data[var_name]["val"] = value
                    else:
                        raise ValueError(f"invalid bool value in line {pos}")
                elif val_type == "int":
                    curr_symbol_table.data[var_name]["val"] = int(value)
                elif val_type == "float":
                    curr_symbol_table.data[var_name]["val"] = float(value)
                else:
                    raise TypeError(
                        f"unsupported type {val_type}, in line {pos}"
                    )
                # 在当前符号表中找到变量，跳出循环
                is_var = True
                break
            if not is_recursion:
                break
            curr_symbol_table = curr_symbol_table.previous
        if not is_var:
            raise NameError(
                f"in line {pos}, variable {var_name} is not declared"
            )

    def find_val_in_symbol_table(
        self, var_name: str, pos: int, is_recursion: bool = True
    ):
        """在符号表中找到变量的值

        Args:
          var_name: 变量名
          pos: 所在位置
          is_recursion: 是否在当前作用域外查找
        :return Any: 变量的值
          var_name: str:
          pos: int:
          is_recursion: bool:  (Default value = True)

        Returns:

        """
        var_dict = self.find_in_symbol_table(var_name, is_recursion)
        if var_dict is None:
            raise NameError(
                f"in line {pos}, variable {var_name} is not declared"
            )
        return var_dict["val"]

    def find_type_in_var_dict(self, var_dict: dict, var_name: str, pos: int):
        """在变量字典中找到变量类型type,如果type为None，报错

        Args:
          var_dict: 变量字典
          var_name: 变量名
          pos: 所在位置
        :return Any: 变量的类型
          var_dict: dict:
          var_name: str:
          pos: int:

        Returns:

        """
        if var_dict is None:
            raise NameError(
                f"in line {pos}, variable {var_name} is not be declared"
            )

        if "type" not in var_dict:
            raise AttributeError(
                f"in line {pos}, variable {var_name} has no type"
            )

        if var_dict["type"] is None:
            raise ValueError(
                f"in line {pos}, variable {var_name} type should not be None"
            )

        return var_dict["type"]

    def find_val_in_var_dict(self, var_dict: dict, var_name: str, pos: int):
        """在变量字典中找到变量值val, 如果val为None，报错

        Args:
          var_dict: 变量字典
          var_name: 变量名
          pos: 所在位置
        :return Any: 变量的值
          var_dict: dict:
          var_name: str:
          pos: int:

        Returns:

        """
        if var_dict is None:
            raise NameError(
                f"in line {pos}, variable {var_name} is not be declared"
            )

        if "val" not in var_dict:
            raise TypeError(
                f"in line {pos}, variable {var_name} has no val property"
            )

        if var_dict["val"] is None:
            raise NameError(
                f"in line {pos}, variable {var_name} is not defined"
            )

        return var_dict["val"]

    def find_in_symbol_table(self, var_name: str, is_recursion):
        """在符号表中找到变量

        Args:
          var_name: 变量名
          is_recursion: 是否在当前作用域外查找
        :return Any: 变量的值
          var_name: str:

        Returns:

        """
        curr_symbol_table = self.symbol_table.get_tail()
        while curr_symbol_table != self.symbol_table.get_head():
            if var_name in curr_symbol_table.data:
                value = curr_symbol_table.data[var_name]
                return value
            if not is_recursion:
                break
            curr_symbol_table = curr_symbol_table.previous
        return None

    def is_float_regex(self, s):
        """判断字符串是否是浮点数

        Args:
          s: 字符串
        :return bool: 是否为浮点数

        Returns:

        """
        pattern = r"^[+-]?(\d+(\.\d*)?|\.\d+)?$"
        return bool(re.match(pattern, s))

    def is_id(self, s):
        """判断字符串是否是变量名

        Args:
          s: 字符串
        :return bool: 是否为变量名

        Returns:

        """
        pattern = r"[a-zA-Z_][a-zA-Z_0-9]*"
        return bool(re.match(pattern, s))

    def get_call_param_value(self, arg, func_dict, pos):
        """获取自定义门入参的值

        Args:
          arg: 自定义门入参
          func_dict: 函数字典
          pos: 所在位置
        :return Any: 自定义门入参的值

        Returns:

        """
        if len(arg.children) == 0:
            # 先从函数字典中查，再从符号表中查
            if self.is_id(arg.leaf):
                if func_dict is not None and arg.leaf in func_dict:
                    value = func_dict[arg.leaf]
                elif arg.leaf == "np.pi":
                    value = np.pi
                else:
                    value = self.find_val_in_symbol_table(arg.leaf, pos)
            else:
                try:
                    value = int(arg.leaf)
                except ValueError:
                    try:
                        value = float(arg.leaf)
                    except ValueError:
                        value = None
            if value is None:
                raise NameError(
                    f"in line {pos}, variable {value} "
                    f"is only declared but not defined"
                )
            return value
        else:
            # 当入参是表达式的情况
            if arg.leaf == "+":
                l_val = self.get_call_param_value(
                    arg.children[0], func_dict, pos
                )
                r_val = self.get_call_param_value(
                    arg.children[1], func_dict, pos
                )
                value = l_val + r_val
            elif arg.leaf == "-":
                if len(arg.children) == 1:
                    l_val = 0
                    r_val = self.get_call_param_value(
                        arg.children[0], func_dict, pos
                    )
                    value = l_val - r_val
                else:
                    l_val = self.get_call_param_value(
                        arg.children[0], func_dict, pos
                    )
                    r_val = self.get_call_param_value(
                        arg.children[1], func_dict, pos
                    )
                    value = l_val - r_val
            elif arg.leaf == "*":
                l_val = self.get_call_param_value(
                    arg.children[0], func_dict, pos
                )
                r_val = self.get_call_param_value(
                    arg.children[1], func_dict, pos
                )
                value = l_val * r_val
            elif arg.leaf == "/":
                r_val = self.get_call_param_value(
                    arg.children[1], func_dict, pos
                )
                if not r_val:
                    raise ZeroDivisionError(
                        f"in line {pos}, divide by zero error"
                    )
                l_val = self.get_call_param_value(
                    arg.children[0], func_dict, pos
                )
                value = l_val / r_val
            elif arg.leaf.startswith("np."):
                # 场景 np.sin , np.cos, np.tan
                # np.exp, np.log, np.sqrt
                n = self.get_call_param_value(arg.children[0], func_dict, pos)
                # pylint: disable=eval-used
                value = eval(arg.leaf.format(n), func_dict)  # noqa: S307
            else:
                value = None
        return value

    def check_node_type(self, node: Node, expect_type: str):
        """检测节点类型是否复合预期, 用于visit语法树节点方法中，防止对节点进行了错误的遍历

        Args:
          node: 抽象语法树节点
          expect_type: 期望的节点类型
          node: Node:
          expect_type: str:

        Returns:

        """
        if node.type != expect_type:
            raise TypeError(
                f"in line {node.pos}, node type expect {expect_type}"
            )

    def check_var_name(self, var_name: str, pos):
        """检测变量命名是否重复

        Args:
          var_name: 变量名
          pos: 所在位置
          var_name: str:

        Returns:

        """
        # 变量名是否出现在经典变量符号表中
        classical_dict = self.find_in_symbol_table(var_name, True)
        if classical_dict is not None:
            raise NameError(f"in line {pos}, var {var_name} is existed")

        # 变量名是否已经存在于经典比特和量子比特中
        if var_name in self.q_var or var_name in self.c_var:
            raise NameError(f"in line {pos}, var {var_name} is existed")
