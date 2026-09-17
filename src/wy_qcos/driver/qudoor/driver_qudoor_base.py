#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You may use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------


from loguru import logger
from schema import Optional

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase


# ------------------------------------------------------------------ #
# QuDoor task response codes
# ------------------------------------------------------------------ #
CODE_SUCCESS = 1
ERROR_CODES = {
    1: "success",
    1001: "encrypt/decrypt failed",
    1006: "no permission",
    1008: "missing params",
    1009: "too frequent",
    1011: "invalid params / data parse failed",
    1031: "signature verification failed",
    500: "server exception",
}
TASK_STATUS = {
    1: "submitted",
    2: "queuing",
    3: "calculating",
    4: "waiting",
    5: "success",
    6: "failed",
}
TASK_STATUS_SUCCESS = 5
TASK_STATUS_FAILURE = frozenset({6})

# Operations with no hardware counterpart on the QuDoor simulator
_SKIP_OPS = {"sync", "barrier", "id", "i", "reset"}

# Two-qubit gates that are symmetric (no control qubit)
_SYMMETRIC_TWO_QUBIT_GATES = {
    "swap",
    "iswap",
    "rxx",
    "ryy",
    "rzz",
    "rzx",
    "ecr",
    "dcx",
    "ashn",
}

# Three-qubit gates with two control qubits (ccx, cswap, ccz)
_DOUBLE_CONTROLLED_GATES = {"ccx", "cswap", "ccz"}

# Controlled two-qubit gates (first qubit is control, rest are targets)
_CONTROLLED_GATES = {
    "cx",
    "cnot",
    "cy",
    "cz",
    "cp",
    "ch",
    "crx",
    "cry",
    "crz",
    "cu1",
    "cu3",
    "cu",
    "cs",
    "csdg",
    "csx",
}


class DriverQudoorBase(DriverGateBase):
    """启科量子离子阱驱动基类.

    Provides base infrastructure: lifecycle, config management,
    and duck-typed operation helpers.  Concrete device drivers
    should subclass and implement the platform-specific methods
    (submit_task, check_task_status, get_task_results,
    convert_code, convert_results, run, etc.).
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "启科量子离子阱驱动"
        self.description = "启科量子离子阱驱动"
        self.base_url = ""
        self.client_id = "cmccos"
        self.device_code = ""
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_ION_TRAP
        self.enable_circuit_aggregation = False
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
        self.enable_device_monitor = True

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""

    def cancel(self, job_id):
        """Cancel running job in driver.

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    # ------------------------------------------------------------------
    # Config validation / fetching
    # ------------------------------------------------------------------

    def validate_driver_configs(self, configs):
        """Validate driver configs.

        Args:
            configs: configs dictionary

        Returns:
            success or fail, err_msg
        """
        success = True
        err_msg = None

        driver_config_schema = {
            "url": str,
            Optional("client_id"): str,
            Optional("device_code"): str,
            Optional("eng_code"): str,
            Optional("user_id"): str,
            Optional("transpiler"): {
                Optional("qpu_configs"): {
                    Optional("qubits"): int,
                    Optional("coupler_map"): {str: [str]},
                }
            },
        }
        _success, err_msgs = Library.validate_schema(
            configs, driver_config_schema, ignore_extra_keys=True
        )
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False

        return success, err_msg

    def fetch_configs(self):
        """Fetch configs from the config file / driver_options."""
        extra_configs = self.get_configs()
        self.base_url = self.driver_options.get(
            "url", extra_configs.get("url", "")
        ).rstrip("/")
        self.client_id = self.driver_options.get(
            "client_id", extra_configs.get("client_id", "cmccos")
        )
        self.device_code = self.driver_options.get(
            "device_code", extra_configs.get("device_code", "")
        )
        self.eng_code = self.driver_options.get(
            "eng_code", extra_configs.get("eng_code", "")
        )
        self.user_id = self.driver_options.get(
            "user_id", extra_configs.get("user_id", "demo_user")
        )

    def update_driver_params_from_options(self):
        """Sync instance attributes from driver_options."""
        super().update_driver_params_from_options()
        if "url" in self.driver_options:
            self.base_url = self.driver_options["url"].rstrip("/")
        if "client_id" in self.driver_options:
            self.client_id = self.driver_options["client_id"]
        if "device_code" in self.driver_options:
            self.device_code = self.driver_options["device_code"]
        if "eng_code" in self.driver_options:
            self.eng_code = self.driver_options["eng_code"]
        if "user_id" in self.driver_options:
            self.user_id = self.driver_options["user_id"]

    # ------------------------------------------------------------------
    # Duck-typed operation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_op_name(op):
        """Get operation gate name (duck-typed)."""
        return getattr(op, "name", None)

    @staticmethod
    def _get_op_targets(op):
        """Get operation target qubits (duck-typed)."""
        return list(getattr(op, "targets", []) or [])

    @staticmethod
    def _get_op_arg_value(op):
        """Get operation parameter values (duck-typed)."""
        return list(getattr(op, "arg_value", []) or [])
