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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from qcos.transpiler.transpiler import transpiler


class TestTranspiler:
    @classmethod
    def setup_class(cls):
        cls.data = '''
            OPENQASM 2.0;
            include "qelib1.inc";
            qreg q[4];
            creg c[4];
            x q[0];
            x q[1];
            x q[2];
            x q[3];
            measure q->c;
        '''
        cls.job_info = {'source_code': [cls.data]}

    def test_transpiler(self):
        res = transpiler.fn(self.job_info)
        assert res == 8
