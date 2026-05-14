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
import pytest

from unittest.mock import patch, MagicMock

from wy_qcos.common.constant import HttpCode
from wy_qcos.common.library import Library, _s

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.cascoldatom.driver_wuyue_hanyuan1_sim import (
    DriverWuyueHanyuan1Sim,
)


driver_wy_hanyuan1_sim = DriverWuyueHanyuan1Sim()

# ruff: noqa: S105
driver_wy_hanyuan1_sim.password_secret = _s("test_password_secret")
driver_wy_hanyuan1_sim.password_pri_key = _s(
    "MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAL+S1b9o7RbU0zhBdvV"
    "NijpIdCNMy3hx+G+H1rflVnhB0rE/4eNkTS5v3iDNMhhqBZKjAslyBcq6FQS55EgShH"
    "UeK4rXUPI8k0yfonxnemT/t7wI9nCgI9lb5HUffzj4B9RRlhmeqTuW8w9GEBoNQZxMD"
    "6sCn1zghWskrZrNhsjbAgMBAAECgYEAuWle0Mu3s8I1z5uki5QJdZFMPiIER8VeomtB"
    "SGiBgRCL35spgBBClvAUd4DBvFlYnWyBtQBTVLs2voU/yPWLFbZgKhRMBY1KbD8lgV6"
    "vVfMnZvLxsvt6HGAFNauOZ7JwnwaaLSNFSR+kApjSIh5rzrPufjQ5U+1TlQiebdXAFm"
    "kCQQDiWHedCvlrIAC7txgApzodRu6TjpnCk3+r+21FD75/uQDV3OcI6D8A+UkkP22Dm"
    "6ZR5FsHZgriN9s144H+omcHAkEA2KwhPBjh3C6mW/OPGhPLJwf7pCoJRT6Y+KME76kY"
    "bpBO99aEJqH8B3e7mEHGeZGyD3E0FODwbJvshqy4k68mjQJBAKlBfFiL700jBklYtfM"
    "vGa7w7tCajvJId+00O1asWkiKIEzMPluTyCFDSGV5pLwIdYvBViynKrZVDHA0q22tJZ"
    "sCQE98RezwC9tkWa8d2H9uh3ZYHV6J9UCryB5eX280DzxwQCf3UB+ECRsMN4uRhagPZ"
    "Mz5cGvAYTLWuJxnPIchF/kCQQDYtMa3+Yys8GjTe6gvkd6rQ7b6X3pTW2em8KfirlWe"
    "VAZtYs/MxYJZcuFy26lFA+DtO7Rg2GzhIKkUrzvqvgkQ"
)
driver_wy_hanyuan1_sim.password_pub_key = _s(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/aO0W1NM4QXb1TYo6SHQjTMt"
    "4cfhvh9a35VZ4QdKxP+HjZE0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJ"
    "NMn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMPRhAaDUGcTA+rAp9c4IVrJ"
    "K2azYbI2wIDAQAB"
)


@pytest.mark.driver
class TestDriverWuyuehanyuanSim:
    def test_init(self):
        assert driver_wy_hanyuan1_sim.submit_path == "task/WuYue/submit"
        assert driver_wy_hanyuan1_sim.query_task_path == "task/WuYue/query"
        assert driver_wy_hanyuan1_sim.version == "0.0.1"
        assert (
            driver_wy_hanyuan1_sim.alias_name
            == "WY-中科酷原-汉原1 中性原子驱动-Sim"
        )
        assert (
            driver_wy_hanyuan1_sim.description
            == "WY-中科酷原-汉原1 中性原子驱动-Sim"
        )
        assert (
            driver_wy_hanyuan1_sim.tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
        )
        assert driver_wy_hanyuan1_sim.supported_code_types == [
            Constant.CODE_TYPE_QASM2
        ]
        assert driver_wy_hanyuan1_sim.max_qubits == 25
        assert driver_wy_hanyuan1_sim.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]

    @patch.object(DriverWuyueHanyuan1Sim, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_check_task_status_success(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test check_task_status with successful status check."""
        mock_response = {
            "code": 1,
            "msg": "Success",
            "data": [
                {
                    "taskStatus": driver_wy_hanyuan1_sim.task_status_completed,
                    "outData": "test_result",
                }
            ],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, task_status = (
            driver_wy_hanyuan1_sim.check_task_status(
                "test_task_id",
                [driver_wy_hanyuan1_sim.task_status_completed],
            )
        )
        assert success is True
        assert err_msg == ""
        assert task_status == driver_wy_hanyuan1_sim.task_status_completed

    @patch.object(DriverWuyueHanyuan1Sim, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_check_task_status_failure(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test check_task_status with failed status check."""
        mock_response = {
            "code": 0,
            "msg": "Error",
            "data": [
                {"taskStatus": driver_wy_hanyuan1_sim.task_status_queuing}
            ],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, task_status = (
            driver_wy_hanyuan1_sim.check_task_status(
                "test_task_id",
                [driver_wy_hanyuan1_sim.task_status_completed],
            )
        )
        assert success is False
        assert err_msg is not None
        assert task_status == driver_wy_hanyuan1_sim.task_status_failed

    @patch.object(DriverWuyueHanyuan1Sim, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_task_results_success(
        self, mock_call_http_api, mock_decrypt_by_private_key
    ):
        """Test get_task_results with successful result retrieval."""
        test_result = {"00": 10, "01": 11, "10": 9, "11": 0}
        mock_response = {
            "code": 1,
            "msg": "Success",
            "data": [
                {
                    "taskStatus": driver_wy_hanyuan1_sim.task_status_completed,
                    "outData": test_result,
                    "execEndTime": 12345,
                    "execStartTime": 12333,
                    "timeConsume": "2.00",
                }
            ],
        }
        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )

        mock_decrypt_by_private_key.return_value = mock_response
        success, err_msg, results, machine_time_info = (
            driver_wy_hanyuan1_sim.get_task_results("test_task_id")
        )
        assert success is True
        assert err_msg == ""
        assert len(results) == 4
        assert results["00"] == 10
        assert results["01"] == 11
        assert results["10"] == 9
        assert machine_time_info["time_consume"] == "2.00"
        assert machine_time_info["exec_end_time"] == 12345
        assert machine_time_info["exec_start_time"] == 12333
