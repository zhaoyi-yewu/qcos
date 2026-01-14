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

from unittest.mock import patch

from wy_qcos.common.library import Library
from wy_qcos.drivers.spinq.driver_spinq_nmr import DriverSpinQNmr
from wy_qcos.transpiler.cmss.common.gate_operation import H

spinq_nmr = DriverSpinQNmr()

driver_config = {
    "remote_host": "127.0.0.1",
    "remote_port": 6060,
    "username": "admin",
    "signature": "",
    "transpiler": {
        "qpu_configs": {
            "qubits": 2,
            "coupler_map": {
                "CX1_2": ["Q1", "Q2"],
                "CX1_3": ["Q1", "Q3"],
                "CX2_1": ["Q2", "Q1"],
                "CX2_3": ["Q2", "Q3"],
                "CX3_1": ["Q3", "Q1"],
                "CX3_2": ["Q3", "Q2"],
            },
        }
    },
}
gate = H(targets=[1])
gates = [gate, gate]
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 2
data = {"index": 0, "source_code": "code", "transpile_results": []}
data_type = DriverSpinQNmr.DATA_TYPE_GATE_SEQUENCE
shots = 1024
result = [0.04928965, 0.08267435, 0.08869863, 0.77933737]
converted_result = {"01": 1, "10": 1, "11": 8}


class TestDriverSpinQNmr:
    def test_init_driver(self):
        assert spinq_nmr.init_driver() is None

    def test_validate_driver_configs(self):
        success, err_msg = spinq_nmr.validate_driver_configs(driver_config)
        assert success is True
        assert err_msg is None

    def test_convert_gate(self):
        gate_info = spinq_nmr.convert_gate(gate, 1)
        assert gate_info["timeSlot"] == 1
        assert gate_info["gate"]["gname"] == "H"
        assert gate_info["gate"]["gtag"] == "C1"
        assert gate_info["qubits"] == [2]

    def test_convert_gates(self):
        circuits = spinq_nmr.convert_gates(gates, num_qubits)
        assert len(circuits["operations"]) == 2

    @patch.object(DriverSpinQNmr, "user_auth")
    def test_fetch_configs(self, mock_user_auth):
        mock_user_auth.return_value = True, None, "S-260114-0005"
        assert spinq_nmr.fetch_configs() is None

    @patch.object(DriverSpinQNmr, "convert_results")
    @patch.object(Library, "loop_with_timeout")
    @patch.object(DriverSpinQNmr, "submit_task")
    @patch.object(DriverSpinQNmr, "convert_gates")
    def test_run(
        self,
        mock_convert_gates,
        mock_submit_task,
        mock_loop_with_timeout,
        mock_convert_results,
    ):
        mock_convert_gates.return_value = None
        mock_submit_task.return_value = True, None, "S-260114-0005"
        mock_loop_with_timeout.return_value = True, None, result
        mock_convert_results.return_value = converted_result
        assert (
            spinq_nmr.run(job_id, num_qubits, data, data_type, shots) is None
        )
