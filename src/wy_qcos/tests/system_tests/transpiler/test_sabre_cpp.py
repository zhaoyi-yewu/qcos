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

from wy_qcos.transpiler.high_performance import (
    SABRE as SABRE_cpp,
    load_config_file,
)
from wy_qcos.tests.system_tests.transpiler.utils import (
    load_qasm_to_ir,
    convert_ir_cpp2py,
)


class TestSabreCpp:
    def test_sabre_cpp(self):
        coupling_list = load_config_file(
            "../../../etc/topology/spinq_rpc_156.toml"
        )
        file_path = "../../../samples/qasm/benchpress/qft/qft_N010.qasm"
        ir_cpp = load_qasm_to_ir(file_path, code_type="cpp")

        sabre = SABRE_cpp(coupling_list)
        sabre.execute(ir_cpp)
        res_cpp = sabre.get_physical_gates()
        res_py = convert_ir_cpp2py(res_cpp)
        assert res_py is not None
