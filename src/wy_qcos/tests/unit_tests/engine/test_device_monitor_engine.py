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

import pytest
from loguru import logger

from wy_qcos.common.args_schema import DEVICE_INFO_SCHEMA
from wy_qcos.common.library import Library
from wy_qcos.engine.device_monitor_engine import validate_device_info


# A fully populated device_info dict that matches DEVICE_INFO_SCHEMA.
# Used as the base for valid-case tests and mutated for invalid cases.
FULL_DEVICE_INFO = {
    "status": "online",
    "details": {
        "calibration": {
            "last_updated": "2026-08-04T14:24:43.870115",
            "qubit_metrics": [
                {
                    "qubit_id": 0,
                    "xeb_fidelity": 0.9995854181305239,
                    "t1": 77.86509849407439,
                    "t2": 22.052429329266976,
                    "readout_fidelity_0": 0.9743115942028986,
                    "readout_fidelity_1": 0.9700000000000001,
                },
                {
                    "qubit_id": 1,
                    "xeb_fidelity": 0.9995979780385145,
                    "t1": 48.86245293912624,
                    "t2": 7.6102444925724559,
                    "readout_fidelity_0": 0.9527878787878787,
                    "readout_fidelity_1": 0.969777777777778,
                },
            ],
            "coupler_metrics": [
                {"qubits": [0, 1], "cz_fidelity": 0.9939434524556052},
                {"qubits": [1, 2], "cz_fidelity": 0.996273989700184},
            ],
        }
    },
    "last_updated_at": "2026-08-04T14:24:43.870115",
}


class TestDeviceInfoSchema:
    """Tests for DEVICE_INFO_SCHEMA validation via Library.validate_schema."""

    def test_full_valid_device_info(self):
        success, err_msgs = Library.validate_schema(
            FULL_DEVICE_INFO, DEVICE_INFO_SCHEMA
        )
        assert success is True
        # On success validate_schema returns [None].
        assert err_msgs == [None]

    def test_minimal_valid_device_info(self):
        # Only the required "status" field is present.
        device_info = {"status": "offline"}
        success, err_msgs = Library.validate_schema(
            device_info, DEVICE_INFO_SCHEMA
        )
        assert success is True
        assert err_msgs == [None]

    def test_none_allowed(self):
        # allow_none=True should pass None values.
        success, _ = Library.validate_schema(
            None, DEVICE_INFO_SCHEMA, allow_none=True
        )
        assert success is True

    def test_none_not_allowed(self):
        # Without allow_none, None should fail validation.
        success, _ = Library.validate_schema(
            None, DEVICE_INFO_SCHEMA, allow_none=False
        )
        assert success is False

    def test_missing_status_is_invalid(self):
        device_info = {"details": {}}
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_status_wrong_type_is_invalid(self):
        device_info = {"status": 123}
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_last_updated_at_accepts_string(self):
        # DEVICE_INFO_SCHEMA defines last_updated_at as str (ISO
        # timestamp), matching device_monitor_engine which sets it
        # via Library.to_iso(...).
        device_info = {
            "status": "online",
            "last_updated_at": "2026-08-04T14:24:43.870115",
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True

    def test_last_updated_at_rejects_int(self):
        # Numeric timestamps are rejected because the schema requires
        # a string value.
        device_info = {"status": "online", "last_updated_at": 1722867883}
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_empty_details_is_valid(self):
        device_info = {"status": "online", "details": {}}
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True

    def test_details_wrong_type_is_invalid(self):
        device_info = {"status": "online", "details": "not a dict"}
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_calibration_partial_is_valid(self):
        # calibration with only last_updated (no metrics lists)
        device_info = {
            "status": "online",
            "details": {
                "calibration": {"last_updated": "2026-08-04"},
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True

    def test_calibration_empty_qubit_metrics_is_valid(self):
        device_info = {
            "status": "online",
            "details": {"calibration": {"qubit_metrics": []}},
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True

    def test_qubit_metrics_missing_qubit_id_is_invalid(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "qubit_metrics": [{"xeb_fidelity": 0.99}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_qubit_metrics_qubit_id_wrong_type_is_invalid(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "qubit_metrics": [{"qubit_id": "0", "xeb_fidelity": 0.99}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_qubit_metrics_fidelity_accepts_int(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "qubit_metrics": [{"qubit_id": 0, "xeb_fidelity": 1}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True

    def test_qubit_metrics_fidelity_rejects_string(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "qubit_metrics": [{"qubit_id": 0, "xeb_fidelity": "0.99"}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_coupler_metrics_missing_qubits_is_invalid(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "coupler_metrics": [{"cz_fidelity": 0.99}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_coupler_metrics_qubits_wrong_element_type_is_invalid(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "coupler_metrics": [
                        {"qubits": ["0", 1], "cz_fidelity": 0.99}
                    ],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is False

    def test_coupler_metrics_cz_fidelity_accepts_int(self):
        device_info = {
            "status": "online",
            "details": {
                "calibration": {
                    "coupler_metrics": [{"qubits": [0, 1], "cz_fidelity": 1}],
                }
            },
        }
        success, _ = Library.validate_schema(device_info, DEVICE_INFO_SCHEMA)
        assert success is True


class TestValidateDeviceInfo:
    """Tests for the validate_device_info wrapper function."""

    def test_valid_device_info_logs_no_warning(self):
        with logger.catch():
            with pytest.MonkeyPatch().context() as ctx:
                called = []

                def fake_warn(msg, *args, **kwargs):
                    called.append(msg)

                ctx.setattr(
                    "wy_qcos.engine.device_monitor_engine.logger.warning",
                    fake_warn,
                )
                validate_device_info(FULL_DEVICE_INFO)
                assert called == []

    def test_none_device_info_logs_no_warning(self):
        # allow_none=True means None should pass without warning.
        with pytest.MonkeyPatch().context() as ctx:
            called = []

            def fake_warn(msg, *args, **kwargs):
                called.append(msg)

            ctx.setattr(
                "wy_qcos.engine.device_monitor_engine.logger.warning",
                fake_warn,
            )
            validate_device_info(None)
            assert called == []

    def test_invalid_device_info_logs_warning(self):
        # Missing required "status" field should trigger a warning.
        with pytest.MonkeyPatch().context() as ctx:
            called = []

            def fake_warn(msg, *args, **kwargs):
                called.append(msg)

            ctx.setattr(
                "wy_qcos.engine.device_monitor_engine.logger.warning",
                fake_warn,
            )
            validate_device_info({"details": {}})
            assert len(called) == 1
            assert "Invalid device info" in called[0]

    def test_invalid_status_type_logs_warning(self):
        with pytest.MonkeyPatch().context() as ctx:
            called = []

            def fake_warn(msg, *args, **kwargs):
                called.append(msg)

            ctx.setattr(
                "wy_qcos.engine.device_monitor_engine.logger.warning",
                fake_warn,
            )
            validate_device_info({"status": 123})
            assert len(called) == 1
            assert "Invalid device info" in called[0]

    def test_minimal_valid_device_info_logs_no_warning(self):
        with pytest.MonkeyPatch().context() as ctx:
            called = []

            def fake_warn(msg, *args, **kwargs):
                called.append(msg)

            ctx.setattr(
                "wy_qcos.engine.device_monitor_engine.logger.warning",
                fake_warn,
            )
            validate_device_info({"status": "online"})
            assert called == []
