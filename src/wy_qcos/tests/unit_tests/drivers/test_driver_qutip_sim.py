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

# ruff: noqa: E402
# load driver venv
import sys

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path(
    "DriverQutipSim", Config.DEFAULT.VENV_DIR
)

import pytest


from wy_qcos.drivers.qutip.driver_qutip_sim import DriverQutipSim
from wy_qcos.common.cmss.gate_operation import RX
from wy_qcos.common.cmss.measure import Measure

driver_qutip_sim = DriverQutipSim()
job_id = "00000000-0000-4000-8000-000000000001"
num_qubits = 2
shots = 10
measure_result = {"00": 0.0, "01": 0.0, "10": 0.0, "11": 1.0}
final_result = {"11": 10}
transpile_result = [
    RX(targets=[0], arg_value=[3.141592653589793]),
    RX(targets=[1], arg_value=[3.141592653589793]),
    Measure(targets=[0], arg_value=[]),
    Measure(targets=[1], arg_value=[]),
]
data = {"index": 0, "source_code": None, "transpile_results": transpile_result}
data_type = DriverQutipSim.DATA_TYPE_GATE_SEQUENCE


@pytest.mark.driver
class TestDriverQutipSim:
    @classmethod
    def teardown_class(cls):
        sys.path = org_path

    def test_convert_result(self):
        result = driver_qutip_sim.convert_result(measure_result, shots)
        assert result == final_result

    def test_init_driver(self):
        assert driver_qutip_sim.init_driver() is None

    def test_validate_driver_configs(self):
        success, err_msg = driver_qutip_sim.validate_driver_configs(None)
        assert success is True
        assert err_msg is None

    def test_close_driver(self):
        assert driver_qutip_sim.close_driver() is None

    def test_fetch_configs(self):
        assert driver_qutip_sim.fetch_configs() is None

    def test_convert_gates(self):
        circuit = driver_qutip_sim.convert_gates(transpile_result, num_qubits)
        assert len(circuit.gates) == 2

    def test_run(self):
        assert (
            driver_qutip_sim.run(job_id, num_qubits, data, data_type) is None
        )

    def test_cancel(self):
        assert driver_qutip_sim.cancel(job_id) is None
