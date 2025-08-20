#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.drivers.driver_passthrough import DriverPassthrough

obj = DriverPassthrough()


class TestDriverPassthrough:
    def test_close_driver(self):
        assert obj.close_driver() is None

    def test_run(self):
        qasm_str = {
            "source_code":
                '''
                OPENQASM 2.0;
                include "qelib1.inc";
                qreg q[5];
                creg c[5];
                h q[0];
                h q[0];
                x q[0];
                rx(1) q[0];
                measure q->c;
                ''',
            "index": "index"}
        assert obj.run("1", 5, qasm_str, "gate_sequence") is None

    def test_init_driver(self):
        assert obj.init_driver() is None

    def test_validate_driver_configs(self):
        success, err_msg = obj.validate_driver_configs()
        assert success is True
