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

from wy_qcos.transpiler.cmss.common.move import Move as MOV

from collections import defaultdict


class NAEstimate:
    """中性原子映射结果评估.

    Args:
        single_gate_duration (int, optional): 单比特门时间. Defaults to 6.
        multi_gate_duration (int, optional): 两比特门时间. Defaults to 2.
        move_duration (int, optional): 移动时间. Defaults to 1000.
        single_gate_fidelity (float, optional): 单比特门保真度. 0.995.
        multi_gate_fidelity (float, optional): 两比特门保真度. 0.98.
        mov_fidelity (float, optional): 移动保真度. Defaults to 0.97.
    """

    def __init__(
        self,
        single_gate_duration=6,
        multi_gate_duration=2,
        move_duration=1000,
        single_gate_fidelity=0.995,
        multi_gate_fidelity=0.98,
        mov_fidelity=0.97,
    ) -> None:
        self.single_gate_duration = single_gate_duration
        self.multi_gate_duration = multi_gate_duration
        self.move_duration = move_duration
        self.single_gate_fidelity = single_gate_fidelity
        self.multi_gate_fidelity = multi_gate_fidelity
        self.mov_fidelity = mov_fidelity

    def set_circuit(self, circuit):
        self.circuit = circuit

    def estimate_time(self):
        """估计运行时间."""
        t = 0
        multi_gate_qubits = set()
        for opt in self.circuit:
            if not isinstance(opt, MOV):
                if opt.type == 1:
                    t += self.single_gate_duration
                if opt.type == 2:
                    for q in opt.targets:
                        if not multi_gate_qubits or q in multi_gate_qubits:
                            multi_gate_qubits = set(opt.targets)
                            t += self.multi_gate_duration
                            break
                        multi_gate_qubits.add(q)
            else:
                multi_gate_qubits = set()
                t += self.move_duration
        return t

    def estimate_fidelity(self):
        """估计保真度."""
        f = 1.0
        for opt in self.circuit:
            if not isinstance(opt, MOV):
                if opt.type == 1:
                    for q in opt.targets:
                        f *= self.single_gate_fidelity
                if opt.type == 2:
                    f *= self.multi_gate_fidelity
            else:
                f *= self.mov_fidelity
        return f


class SCEstimate:
    """基于swap的映射结果评估.

    Args:
        single_gate_duration (float, optional): 单比特门时间. Defaults to 10.0.
        multi_gate_duration (float, optional): 两比特门时间. Defaults to 50.0.
        single_gate_fidelity (float, optional): 单比特门保真度. 0.995.
        multi_gate_fidelity (float, optional): 两比特门保真度. 0.98.
    """

    def __init__(
        self,
        single_gate_duration=10.0,
        multi_gate_duration=50.0,
        single_gate_fidelity=0.995,
        multi_gate_fidelity=0.98,
    ) -> None:
        self.single_gate_duration = single_gate_duration
        self.multi_gate_duration = multi_gate_duration
        self.single_gate_fidelity = single_gate_fidelity
        self.multi_gate_fidelity = multi_gate_fidelity

    def set_circuit(self, circuit):
        self.circuit = circuit

    def estimate_time(self):
        """估计运行时间."""
        node_time = defaultdict(int)
        # time_opt = defaultdict(lambda : {'gate': [], 'time': 0})
        for opt in self.circuit:
            t = max(node_time[q] for q in opt.targets)
            duration = 0
            if opt.type == 1:
                duration = self.single_gate_duration
            elif opt.type == 2:
                duration = self.multi_gate_duration
            elif opt.type == -1:
                duration = 0
            else:
                continue
            for q in opt.targets:
                node_time[q] = t + duration

        estimate_time = max(node_time.values())
        return estimate_time

    def estimate_fidelity(self):
        """估计保真度."""
        f = 1.0
        for opt in self.circuit:
            if opt.type == 1:
                f *= self.single_gate_fidelity
            elif opt.type == 2:
                f *= self.multi_gate_fidelity
            else:
                continue
        return f
