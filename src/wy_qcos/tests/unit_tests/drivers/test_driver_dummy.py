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

from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.drivers.driver_base import DriverBase
from wy_qcos.drivers.dummy.driver_dummy import DriverDummy

driver_dummy = DriverDummy()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 5
data_type = DriverDummy.DATA_TYPE_GATE_SEQUENCE
data_qasm = {
    "source_code": """
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[5];
        creg c[5];
        h q[0];
        h q[0];
        x q[0];
        rx(1) q[0];
        measure q->c;
        """,
    "index": "index",
    "transpile_results": [],
}


class TestDriverDummy:
    def test_init_driver(self):
        assert driver_dummy.init_driver() is None

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs(self, mock_validate_schema):
        configs = {}
        mock_validate_schema.return_value = iter([True, ""])
        success, err_msg = driver_dummy.validate_driver_configs(configs)
        assert success is True

        mock_validate_schema.return_value = iter([False, ""])
        success, err_msg = driver_dummy.validate_driver_configs(configs)
        assert success is False

    def test_close_driver(self):
        assert driver_dummy.close_driver() is None

    @patch.object(DriverBase, "get_fake_results")
    def test_run(self, mock_get_fake_results):
        mock_get_fake_results.return_value = {"00": 45, "11": 55}
        assert (
            driver_dummy.run(job_id, num_qubits, data_qasm, data_type) is None
        )

    def test_cancel(self):
        assert driver_dummy.cancel(job_id) is None
