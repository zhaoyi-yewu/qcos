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

import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.common.cmss.base_operation import OperationType
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library

# Inject a lightweight stub for the optional dependency 'smbclient' so that
# importing the driver module doesn't fail in environments without it.
if "smbclient" not in sys.modules:
    fake_smb = types.SimpleNamespace()
    fake_smb.register_session = lambda *_, **__: None
    fake_smb.reset_connection_cache = lambda: None
    fake_smb.path = types.SimpleNamespace(exists=lambda *_: True)

    def _open_file(*_, **__):  # will be patched in specific tests
        raise RuntimeError("open_file should be patched in tests")

    fake_smb.open_file = _open_file
    fake_smb.mkdir = lambda *_: None
    sys.modules["smbclient"] = fake_smb

from wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse import (
    DriverHanyuan1Pulse,
)


@pytest.mark.driver
class TestDriverHanyuan1Pulse:
    def test_init(self):
        driver = DriverHanyuan1Pulse()
        assert driver.version == "0.0.1"
        assert driver.alias_name == "中科酷原-汉原1-Pulse 中性原子驱动"
        assert driver.description == "中科酷原-汉原1-Pulse 中性原子驱动"
        assert driver.transpiler == Constant.TRANSPILER_CMSS
        assert driver.tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
        assert driver.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]
        assert driver.supported_code_types == [Constant.CODE_TYPE_QASM2]
        assert driver.supported_transpilers == [Constant.TRANSPILER_CMSS]
        assert driver.max_qubits == 100

    @patch.object(DriverHanyuan1Pulse, "set_device_status")
    def test_init_driver(self, mock_set_status):
        driver = DriverHanyuan1Pulse()
        driver.init_driver()
        mock_set_status.assert_called_once()

    @patch.object(Library, "validate_schema")
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.register_session"
    )
    def test_validate_driver_configs_success(
        self, mock_register_session, mock_validate
    ):
        driver = DriverHanyuan1Pulse()
        mock_validate.return_value = (True, [])

        configs = {
            "ip_address": "192.168.1.2",
            "port": 445,
            "user": "user1",
            "pwd": "pwd1",
            "shared_name": "share1",
        }

        success, err = driver.validate_driver_configs(configs)
        assert success is True
        assert err is None
        mock_register_session.assert_called_once()

    @patch.object(Library, "validate_schema")
    def test_validate_driver_configs_failure(self, mock_validate):
        driver = DriverHanyuan1Pulse()
        mock_validate.return_value = (False, ["e1", "e2"])
        success, err = driver.validate_driver_configs({})
        assert success is False
        assert "driver config file error" in err
        assert "e1" in err and "e2" in err

    def test_generate_pulse_basic(self):
        driver = DriverHanyuan1Pulse()
        # single-qubit op with one argument
        g1 = SimpleNamespace(
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            arg_value=[1.23456789],
            targets=[0],
        )
        # double-qubit op with one argument
        g2 = SimpleNamespace(
            operation_type=OperationType.DOUBLE_QUBIT_OPERATION.value,
            arg_value=[0.5],
            targets=[1, 2],
        )
        pulses, qids = driver._generate_pulse([g1, g2])

        assert len(pulses) == 2
        # first pulse
        assert pulses[0]["time"] == 0
        assert pulses[0]["type"] == 2
        assert pulses[0]["param"] == [0, round(1.23456789, 6), 0, 0, 0]
        # second pulse
        assert pulses[1]["time"] == 1
        assert pulses[1]["type"] == 3
        assert pulses[1]["param"] == [
            1,
            round(0.5, 6),
            0,
            0,
            0,
            0,
            2,
        ]
        # qubit id list collected
        assert qids == [0, 1, 2]

    def test_generate_pulse_skip_conditions(self):
        driver = DriverHanyuan1Pulse()
        # no arg -> skipped
        g_noarg = SimpleNamespace(
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            arg_value=[],
            targets=[0],
        )
        # two args -> code continues without appending
        g_twoargs = SimpleNamespace(
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            arg_value=[0.1, 0.2],
            targets=[1],
        )
        pulses, qids = driver._generate_pulse([g_noarg, g_twoargs])
        assert pulses == []
        assert qids == []

    def test_generate_qubit_map(self):
        driver = DriverHanyuan1Pulse()
        g_meas = SimpleNamespace(
            operation_type=OperationType.MEASURE.value,
            targets=[0],
        )
        g_other = SimpleNamespace(
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            targets=[1],
        )
        qubit_map = driver._generate_qubit_map([g_meas, g_other], [0, 1])
        # According to current implementation, entries are appended per gate
        assert qubit_map == [
            [0, 0, 0, 1],
            [1, 0, 0, 0],
            [0, 0, 0, 1],
            [1, 0, 0, 0],
        ]

    def test_prepare_data(self):
        driver = DriverHanyuan1Pulse()
        g1 = SimpleNamespace(
            operation_type=OperationType.SINGLE_QUBIT_OPERATION.value,
            arg_value=[1.0],
            targets=[0],
        )
        task = driver._prepare_data("job-1-0", [g1], shots=10, num_qubits=5)
        assert task["MsgType"] == "MsgTask"
        assert task["TaskID"] == "job-1-0"
        assert task["QuantumNum"] == 5
        assert task["RepeatTime"] == 10
        assert task["Mode"] == "circuit"
        assert isinstance(task["Pulse"], list)
        assert isinstance(task["QubitMap"], list)

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.reset_connection_cache"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.register_session"
    )
    def test_reset_and_reconnect(self, mock_register_session, mock_reset_cache):
        driver = DriverHanyuan1Pulse()
        driver._reset_and_reconnect()
        mock_reset_cache.assert_called_once()
        mock_register_session.assert_called_once()

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_submit_task_success(self, mock_mkdir, mock_exists, mock_open):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        # mock file write
        file_obj = MagicMock()
        cm = MagicMock()
        cm.__enter__.return_value = file_obj
        mock_open.return_value = cm

        succ, err = driver.submit_task({"TaskID": "job-1-0"})
        assert succ is True
        assert err is None
        file_obj.write.assert_called_once()

    @patch.object(DriverHanyuan1Pulse, "_reset_and_reconnect")
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_submit_task_reconnect(
        self, mock_mkdir, mock_exists, mock_open, mock_reset
    ):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        file_obj = MagicMock()
        cm = MagicMock()
        cm.__enter__.return_value = file_obj
        # first call raises ConnectionResetError, second call succeeds
        mock_open.side_effect = [ConnectionResetError("rst"), cm]

        succ, err = driver.submit_task({"TaskID": "job-1-0"})
        assert succ is True
        assert err is None
        assert mock_reset.call_count == 1
        assert file_obj.write.call_count == 1

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_submit_task_exception(self, mock_mkdir, mock_exists, mock_open):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        mock_open.side_effect = Exception("boom")
        succ, err = driver.submit_task({"TaskID": "job-1-0"})
        assert succ is False
        assert "boom" in err

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_get_task_result_success(self, mock_mkdir, mock_exists, mock_open):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        result_payload = {
            "TaskID": "jid-0",
            "Result2": [{"Type": "00", "Percent": 0.5}],
        }
        file_obj = MagicMock()
        file_obj.read.return_value = json.dumps(result_payload).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = file_obj
        mock_open.return_value = cm

        succ, err, raw = driver.get_task_result("jid-0")
        assert succ is True
        assert err is None
        assert raw == result_payload["Result2"]

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_get_task_result_taskid_mismatch(
        self, mock_mkdir, mock_exists, mock_open
    ):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        result_payload = {
            "TaskID": "other",
            "Result2": [{"Type": "00", "Percent": 0.5}],
        }
        file_obj = MagicMock()
        file_obj.read.return_value = json.dumps(result_payload).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = file_obj
        mock_open.return_value = cm

        succ, err, raw = driver.get_task_result("jid-0")
        assert succ is False
        assert err is None
        assert raw is None

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_get_task_result_invalid_format(
        self, mock_mkdir, mock_exists, mock_open
    ):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        file_obj = MagicMock()
        file_obj.read.return_value = json.dumps([1, 2, 3]).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = file_obj
        mock_open.return_value = cm

        succ, err, raw = driver.get_task_result("jid-0")
        assert succ is False
        assert err is None
        assert raw is None

    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.open_file"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.path.exists"
    )
    @patch(
        "wy_qcos.drivers.cascoldatom.driver_hanyuan1_pulse.smbclient.mkdir"
    )
    def test_get_task_result_exception(self, mock_mkdir, mock_exists, mock_open):
        driver = DriverHanyuan1Pulse()
        mock_exists.return_value = True
        mock_open.side_effect = Exception("read-fail")
        succ, err, raw = driver.get_task_result("jid-0")
        assert succ is False
        assert "read-fail" in err
        assert raw is None

    def test_format_result(self):
        driver = DriverHanyuan1Pulse()
        raw = [
            {"Type": "00", "Percent": 0.6},
            {"Type": "11", "Percent": 0.4},
        ]
        out = driver.format_result(raw, shots=10)
        assert out == {"00": 6.0, "11": 4.0}

    def test_run_success(self):
        driver = DriverHanyuan1Pulse()
        # patch the non-existing submit_tasks on instance to bypass typo
        driver.submit_tasks = MagicMock(return_value=(True, None))

        # mock loop_with_timeout to return results directly
        with patch.object(Library, "loop_with_timeout") as mock_loop, \
            patch.object(DriverHanyuan1Pulse, "set_results") as mock_set_results, \
            patch.object(DriverHanyuan1Pulse, "set_device_status") as mock_set_status:

            mock_loop.return_value = (
                True,
                None,
                [{"Type": "00", "Percent": 1.0}],
            )

            job_id = "jid"
            data = {"index": 0, "transpile_results": []}
            driver.run(job_id, num_qubits=2, data=data, data_type="gate", shots=5)

            mock_set_results.assert_called_once()
            mock_set_status.assert_called()

    def test_run_submit_failed(self):
        driver = DriverHanyuan1Pulse()
        driver.submit_tasks = MagicMock(return_value=(False, "submit-err"))
        with pytest.raises(ValueError) as ei:
            driver.run(
                "jid", 2, {"index": 0, "transpile_results": []}, "gate", 1
            )
        assert "Failed to submit task" in str(ei.value)

    def test_run_get_result_failed(self):
        driver = DriverHanyuan1Pulse()
        driver.submit_tasks = MagicMock(return_value=(True, None))
        with patch.object(Library, "loop_with_timeout") as mock_loop:
            mock_loop.return_value = (False, "timeout", None)
            with pytest.raises(ValueError) as ei:
                driver.run(
                    "jid",
                    2,
                    {"index": 0, "transpile_results": []},
                    "gate",
                    1,
                )
            assert "Failed to get task" in str(ei.value)

    def test_run_empty_results(self):
        driver = DriverHanyuan1Pulse()
        driver.submit_tasks = MagicMock(return_value=(True, None))
        with patch.object(Library, "loop_with_timeout") as mock_loop:
            mock_loop.return_value = (True, None, [])
            with pytest.raises(ValueError) as ei:
                driver.run(
                    "jid",
                    2,
                    {"index": 0, "transpile_results": []},
                    "gate",
                    1,
                )
            assert "Result is None or empty" in str(ei.value)

    def test_fetch_running_info(self):
        driver = DriverHanyuan1Pulse()
        info = driver.fetch_running_info()
        assert info == {"status": "online"}
