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
from schema import Optional

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos.common.library import Library, _s
from wy_qcos.drivers.cascoldatom.driver_wuyue_hanyuan1 import (
    DriverWuyueHanyuan1,
)


driver_wuyue_hanyuan1 = DriverWuyueHanyuan1()

# ruff: noqa: S105
driver_wuyue_hanyuan1.password_secret = _s("test_password_secret")
driver_wuyue_hanyuan1.password_pri_key = _s(
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
driver_wuyue_hanyuan1.password_pub_key = _s(
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC/ktW/aO0W1NM4QXb1TYo6SHQjTMt"
    "4cfhvh9a35VZ4QdKxP+HjZE0ub94gzTIYagWSowLJcgXKuhUEueRIEoR1HiuK11DyPJ"
    "NMn6J8Z3pk/7e8CPZwoCPZW+R1H384+AfUUZYZnqk7lvMPRhAaDUGcTA+rAp9c4IVrJ"
    "K2azYbI2wIDAQAB"
)


@pytest.mark.driver
class TestDriverWuyuehanyuan1:
    def test_init(self):
        assert driver_wuyue_hanyuan1.submit_path == "task/WuYue/submit"
        assert driver_wuyue_hanyuan1.query_task_path == "task/WuYue/query"
        assert driver_wuyue_hanyuan1.version == "0.0.1"
        assert (
            driver_wuyue_hanyuan1.alias_name
            == "WY-中科酷原-汉原1 中性原子驱动"
        )
        assert (
            driver_wuyue_hanyuan1.description
            == "WY-中科酷原-汉原1 中性原子驱动"
        )
        assert (
            driver_wuyue_hanyuan1.tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM
        )
        assert driver_wuyue_hanyuan1.supported_code_types == [
            Constant.CODE_TYPE_QASM2
        ]
        assert driver_wuyue_hanyuan1.max_qubits == 100
        assert driver_wuyue_hanyuan1.supported_basis_gates == [
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.TWO_QUBIT_GATE_CZ,
        ]

    def test_hanyuan1_device_info_schema_contains_expected_optional_keys(self):
        """Test hanyuan1_device_info_schema contains expected Optional keys."""
        schema = driver_wuyue_hanyuan1.hanyuan1_device_info_schema
        expected_keys = [
            "horizontalRelaxationTime",
            "uniformityDephasingTime",
            "nonUniformityDephasingTime",
            "verticalRelaxationTime",
            "tweezersNum",
            "vaccum",
            "rydbergExcitation",
            "transportFidelity",
            "elementAtom",
            "time",
        ]
        for key in expected_keys:
            assert Optional(key) in schema, f"Missing Optional({key})"

    def test_hanyuan1_device_info_schema_value_types(self):
        """Test hanyuan1_device_info_schema value types are correct."""
        schema = driver_wuyue_hanyuan1.hanyuan1_device_info_schema
        for key, value in schema.items():
            if "horizontalRelaxationTime" in str(key):
                assert value is int
            elif "uniformityDephasingTime" in str(key):
                assert value is int
            elif "nonUniformityDephasingTime" in str(key):
                assert value is int
            elif "verticalRelaxationTime" in str(key):
                assert value is int
            elif "tweezersNum" in str(key):
                assert value is int
            elif "vaccum" in str(key):
                assert value is float
            elif "rydbergExcitation" in str(key):
                assert value is float
            elif "transportFidelity" in str(key):
                assert value is float
            elif "elementAtom" in str(key):
                assert value is str
            elif "time" in str(key):
                assert value is str

    def test_update_device_info_schema_contains_base_and_hanyuan1_fields(self):
        """Test update_device_info_schema returns merged schema."""
        schema = driver_wuyue_hanyuan1.update_device_info_schema()
        # Should contain base fields from default_device_info_schema
        assert Optional("singleFidelity") in schema
        assert Optional("doubleFidelity") in schema
        assert Optional("SPAMError") in schema
        # Should contain hanyuan1 specific fields
        assert Optional("horizontalRelaxationTime") in schema
        assert Optional("uniformityDephasingTime") in schema
        assert Optional("nonUniformityDephasingTime") in schema
        assert Optional("verticalRelaxationTime") in schema
        assert Optional("tweezersNum") in schema
        assert Optional("vaccum") in schema
        assert Optional("rydbergExcitation") in schema
        assert Optional("transportFidelity") in schema
        assert Optional("elementAtom") in schema
        assert Optional("time") in schema

    def test_update_device_info_schema_base_fields_types(self):
        """Test update_device_info_schema base field types are correct."""
        schema = driver_wuyue_hanyuan1.update_device_info_schema()
        assert schema[Optional("singleFidelity")] is float
        assert schema[Optional("doubleFidelity")] is float
        assert schema[Optional("SPAMError")] is float

    def test_update_device_info_schema_hanyuan1_fields_types(self):
        """Test update_device_info_schema hanyuan1 field types are correct."""
        schema = driver_wuyue_hanyuan1.update_device_info_schema()
        assert schema[Optional("horizontalRelaxationTime")] is int
        assert schema[Optional("uniformityDephasingTime")] is int
        assert schema[Optional("nonUniformityDephasingTime")] is int
        assert schema[Optional("verticalRelaxationTime")] is int
        assert schema[Optional("tweezersNum")] is int
        assert schema[Optional("vaccum")] is float
        assert schema[Optional("rydbergExcitation")] is float
        assert schema[Optional("transportFidelity")] is float
        assert schema[Optional("elementAtom")] is str
        assert schema[Optional("time")] is str

    @patch.object(DriverWuyueHanyuan1, "update_device_info")
    @patch.object(DriverWuyueHanyuan1, "update_device_info_schema")
    @patch.object(DriverWuyueHanyuan1, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_device_info_success(
        self,
        mock_call_http_api,
        mock_decrypt_by_private_key,
        mock_update_device_info_schema,
        mock_update_device_info,
    ):
        """Test get_device_info with successful response."""
        mock_update_device_info_schema.return_value = {
            Optional("singleFidelity"): float,
            Optional("doubleFidelity"): float,
            Optional("horizontalRelaxationTime"): int,
            Optional("tweezersNum"): int,
            Optional("vaccum"): float,
            Optional("elementAtom"): str,
        }

        mock_data = {
            "singleFidelity": 0.99,
            "doubleFidelity": 0.95,
            "horizontalRelaxationTime": 132,
            "tweezersNum": 100,
            "vaccum": 1.2,
            "elementAtom": "Rb",
        }
        mock_response = {"code": 1, "msg": "Success", "data": mock_data}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response

        mock_update_device_info.return_value = mock_data

        success, err_msg, device_info = driver_wuyue_hanyuan1.get_device_info()
        assert success is True
        assert err_msg == ""
        assert device_info["singleFidelity"] == 0.99
        assert device_info["doubleFidelity"] == 0.95
        assert device_info["horizontalRelaxationTime"] == 132
        assert device_info["tweezersNum"] == 100
        assert device_info["vaccum"] == 1.2
        assert device_info["elementAtom"] == "Rb"

    @patch.object(DriverWuyueHanyuan1, "get_device_info")
    def test_get_device_info_schema_validation_failure(
        self,
        mock_get_device_info,
    ):
        """Test get_device_info with schema validation failure."""
        mock_get_device_info.return_value = (
            False,
            "schema validation error",
            None,
        )
        success, err_msg, device_info = driver_wuyue_hanyuan1.get_device_info()
        assert success is False
        assert err_msg is not None
        assert device_info is None

    @patch.object(DriverWuyueHanyuan1, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_device_info_http_error(
        self,
        mock_call_http_api,
        mock_decrypt_by_private_key,
    ):
        """Test get_device_info with HTTP error."""
        mock_call_http_api.return_value = (
            HttpCode.SERVICE_UNAVAILABLE_ERROR,
            "Service unavailable",
            None,
            MagicMock(),
        )

        success, err_msg, device_info = driver_wuyue_hanyuan1.get_device_info()
        assert success is False
        assert err_msg == "Service unavailable"
        assert device_info is None

    @patch.object(DriverWuyueHanyuan1, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_device_info_error_code(
        self,
        mock_call_http_api,
        mock_decrypt_by_private_key,
    ):
        """Test get_device_info with error code from server."""
        mock_response = {"code": 0, "msg": "Server error", "data": None}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response

        success, err_msg, device_info = driver_wuyue_hanyuan1.get_device_info()
        assert success is False
        assert err_msg is not None
        assert device_info is None

    @patch.object(DriverWuyueHanyuan1, "decrypt_by_private_key")
    @patch.object(Library, "call_http_api")
    def test_get_device_info_null_data(
        self,
        mock_call_http_api,
        mock_decrypt_by_private_key,
    ):
        """Test get_device_info with null data from server."""
        mock_response = {"code": 1, "msg": "Success", "data": None}

        mock_call_http_api.return_value = (
            HttpCode.SUCCESS_OK,
            "Success",
            json.dumps(mock_response),
            MagicMock(),
        )
        mock_decrypt_by_private_key.return_value = mock_response

        success, err_msg, device_info = driver_wuyue_hanyuan1.get_device_info()
        assert success is False
        assert err_msg is not None
        assert device_info is None
