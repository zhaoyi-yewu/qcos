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

import pytest

from wy_qcos.transpiler.cmss.circuit.register import (
    QuantumRegister,
    ClassicalRegister,
)
from wy_qcos.transpiler.common.errors import CircuitException


class TestRegister:
    def test_qreg_init(self):
        qreg = QuantumRegister(size=4, name="q", init_pos=0)
        assert qreg.name == "q"
        assert qreg.size == 4

        assert qreg[2] == 2
        assert qreg.index(2) == 2

        qreg1 = QuantumRegister(size=4)
        assert qreg1.name == "q0"
        qreg2 = QuantumRegister(size=4)
        assert qreg2.name == "q1"
        assert qreg[:3] == [0, 1, 2]

    def test_creg_init(self):
        creg = ClassicalRegister(size=3, name="c", init_pos=1)
        assert creg.name == "c"
        assert creg.size == 3

        assert creg[2] == 3
        assert creg.index(3) == 2

        creg1 = ClassicalRegister(size=4)
        assert creg1.name == "c0"
        creg2 = ClassicalRegister(size=4)
        assert creg2.name == "c1"
        assert creg[1:3] == [2, 3]

    def test_qreg_bits_provided(self):
        bits = [2, 4, 6]
        qreg = QuantumRegister(size=None, name="q_custom", bits=bits)
        assert qreg.name == "q_custom"
        assert qreg.size == 3

    def test_creg_bits_provided(self):
        bits = [5, 7]
        creg = ClassicalRegister(size=None, name="c_custom", bits=bits)
        assert creg.name == "c_custom"
        assert creg.size == 2

    def test_qreg_eq(self):
        qreg1 = QuantumRegister(size=2, name="q1")
        qreg2 = QuantumRegister(size=2, name="q1")
        qreg3 = QuantumRegister(size=3, name="q2")
        qreg4 = QuantumRegister(size=None, name="q1", bits=[0, 1])

        assert qreg1 == qreg2
        assert qreg1 != qreg3
        assert qreg1 == qreg4

    def test_creg_eq(self):
        creg1 = ClassicalRegister(size=2, name="c1")
        creg2 = ClassicalRegister(size=2, name="c1")
        creg3 = ClassicalRegister(size=3, name="c2")
        creg4 = ClassicalRegister(size=None, name="c1", bits=[0, 1])

        assert creg1 == creg2
        assert creg1 != creg3
        assert creg1 == creg4

    def test_register_abnormal(self):
        with pytest.raises(CircuitException) as e1:
            _ = QuantumRegister(size=None, bits=None)

        msg = str(e1.value)
        assert "Exactly one" in msg

        with pytest.raises(CircuitException) as e2:
            _ = QuantumRegister(size=None, bits=["a", "b"])

        msg = str(e2.value)
        assert "Bits must be integers" in msg

        with pytest.raises(CircuitException) as e3:
            _ = QuantumRegister(size=-1)

        msg = str(e3.value)
        assert "Register size must be non-negative" in msg

        with pytest.raises(CircuitException) as e4:
            qreg = QuantumRegister(size=3)
            _ = qreg["a"]

        msg = str(e4.value)
        assert "expected integer" in msg

        with pytest.raises(CircuitException) as e5:
            qreg = QuantumRegister(size=3)
            _ = qreg[[0, 5]]

        msg = str(e5.value)
        assert "register index out of range" in msg

        with pytest.raises(CircuitException) as e6:
            qreg = QuantumRegister(size=3)
            _ = qreg.index(5)

        msg = str(e6.value)
        assert "not found" in msg

        with pytest.raises(CircuitException) as e7:
            _ = QuantumRegister(size=None, bits="6")

        msg = str(e7.value)
        assert "Bits must be list" in msg
