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

from loguru import logger
from schema import Optional

from wy_qcos.common.constant import Constant, HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase

# Skip operations that have no hardware counterpart
_SKIP_OPS = {"sync", "barrier", "id", "i", "swap"}


class DriverCetcBase(DriverGateBase):
    """国基量子驱动基类.

    Submit / query / list tasks on https://www.tiangongqs.com
    via the REST API documented in samples/tiangong_quantum_api.py.
    """

    # API path segments (appended to the configured base URL)
    path_executetask = "/executetask"
    path_taskdetail = "/taskdetail"
    path_tasklist = "/tasklist"
    path_qdevicedetail = "/qdevicedetail"

    # Platform state codes
    state_running = 0
    state_failed = 1
    state_completed = 2
    state_queued = 3

    # Device state codes (from qdevicedetail API)
    device_state_offline = 0
    device_state_online = 1
    device_state_maintain = 2

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "国基量子 超导驱动"
        self.description = "国基量子 超导驱动"
        self.token = None
        self.base_url = ""
        self.computer_type = None  # set by subclass
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.TWO_QUBIT_GATE_RZZ,
        ]
        self.supported_transpilers = [
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        self.enable_circuit_aggregation = False
        self.max_qubits = 156
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE
        # Allow computer_type to be overridden via --driver-options
        self.driver_options_schema.update({
            Optional("computer_type"): int,
            Optional("url"): str,
            Optional("token"): str,
        })
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
            "token": str,
            "url": str,
            Optional("computer_type"): int,
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
        """Fetch configs from the toml file and set auth headers.

        driver_options can override url, token and computer_type
        from the config file, allowing system tests to redirect
        API calls to a mock server.
        """
        extra_configs = self.get_configs()
        self.token = self.driver_options.get(
            "token", extra_configs.get("token", "")
        )
        self.base_url = self.driver_options.get(
            "url", extra_configs.get("url", "")
        ).rstrip("/")
        self.computer_type = self.driver_options.get(
            "computer_type",
            extra_configs.get("computer_type", self.computer_type),
        )

        if not self.token:
            logger.warning(
                "CETC token is empty - set 'token' in cetc.toml "
                "to a valid Bearer token"
            )

        # Prepare auth headers for subsequent HTTP calls
        self.auth_headers["Authorization"] = f"Bearer {self.token}"

    def update_driver_params_from_options(self):
        """Sync instance attributes from driver_options.

        Note: fetch_configs() is called after this method in the
        job execution path and also checks driver_options, so the
        values set here are mainly for code paths that skip
        fetch_configs (e.g. when base_url is already set).
        """
        super().update_driver_params_from_options()
        if "computer_type" in self.driver_options:
            self.computer_type = self.driver_options["computer_type"]
        if "url" in self.driver_options:
            self.base_url = self.driver_options["url"].rstrip("/")
        if "token" in self.driver_options:
            self.token = self.driver_options["token"]
            self.auth_headers["Authorization"] = f"Bearer {self.token}"

    def fetch_running_info(self):
        """Fetch running info.

        Returns:
            remote device running info
        """
        # Lazy-load configs if not yet loaded (device monitor path
        # skips fetch_configs since no job_info is passed to init_driver)
        if not self.base_url:
            self.fetch_configs()

        success, err_msg, data = self.get_device_info()
        if not success:
            logger.debug(f"Failed to get device info: {err_msg}")
            return {
                "status": Device.DEVICE_STATUS_OFFLINE,
                "details": {},
            }

        device_data = data.get("data", data)
        state = device_data.get("state")
        if state == self.device_state_online:
            status = Device.DEVICE_STATUS_ONLINE
        elif state == self.device_state_maintain:
            status = Device.DEVICE_STATUS_MAINTAIN
        else:
            status = Device.DEVICE_STATUS_OFFLINE

        # Build qubit metrics from singleBitInfo
        qubit_metrics = []
        for bit in device_data.get("singleBitInfo", []):
            qb = bit.get("quantumBit", "")
            qubit_id = int(qb.replace("Q", "")) if qb else 0
            qubit_metrics.append({
                "qubit_id": qubit_id,
                "xeb_fidelity": bit.get("singleFidelity", 0.0),
                "t1": bit.get("T1", 0.0),
                "t2": bit.get("T2", 0.0),
                "readout_fidelity_0": bit.get("fidelity0", 0.0),
                "readout_fidelity_1": bit.get("fidelity1", 0.0),
            })

        # Build coupler metrics from doubleBitInfo
        coupler_metrics = []
        for bit in device_data.get("doubleBitInfo", []):
            coupling = bit.get("couplingQubits", "")
            if not coupling:
                continue
            parts = coupling.split("-")
            qubits = [int(p.replace("Q", "")) for p in parts]
            coupler_metrics.append({
                "qubits": qubits,
                "cz_fidelity": bit.get("czFidelity", 0.0),
            })

        device_running_info = {
            "status": status,
            "available_qubits": device_data.get("maxQubits", 0),
            "details": {
                "vendor_job_count": {
                    "total": device_data.get("jobNumber", 0),
                },
                "calibration": {
                    "last_updated_at": device_data.get("time", ""),
                    "qubit_metrics": qubit_metrics,
                    "coupler_metrics": coupler_metrics,
                },
            },
        }
        return device_running_info

    def get_device_info(self):
        """Get device info from the TianGong platform.

        Returns:
            (success, err_msg, data)
        """
        success = True
        err_msgs = []
        data = None

        url = f"{self.base_url}{self.path_qdevicedetail}"
        params = {"deviceid": self.computer_type}
        headers = {"Authorization": f"Bearer {self.token}"}

        logger.info(f"query device detail url: {url}")

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="get_device_info",
        )
        if status_code == HttpCode.SUCCESS_OK:
            if not text:
                success = False
                err_msgs.append("Empty response body")
            else:
                response = json.loads(text)
                code = response.get("code")
                msg = response.get("msg", "")
                if code == 200:
                    data = response
                else:
                    success = False
                    err_msgs.append(
                        f"Device detail failed (code={code}): {msg}"
                    )
        else:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}"
                f", response: {text[:500] if text else 'None'}"
            )

        return success, "\n".join(err_msgs), data

    # ------------------------------------------------------------------
    # Circuit conversion: transpile_results -> TianGong steps format
    # ------------------------------------------------------------------

    def convert_code(self, num_qubits, src_code, transpile_results):
        """Convert transpile results to the TianGong steps format.

        Args:
            num_qubits: number of qubits
            src_code: original source code (unused, kept for signature)
            transpile_results: list of BaseOperation / GateOperation

        Returns:
            (steps, actual_num_qubits) where steps is a list of step
            dicts and actual_num_qubits is the number of distinct qubit
            indices found in the transpiled circuit.  The remapping
            ensures physical qubit indices (which may be > num_qubits
            after SABRE mapping) are compacted to a 0-based range so
            they match quantum-num / classNumber / measure-position.
        """
        if not transpile_results:
            return [], num_qubits

        # First pass: collect all unique qubit indices so we can remap
        # them to a compact 0-based range.  After SABRE routing the
        # operation targets are *physical* qubit indices which may be
        # larger than the original logical qubit count.
        all_qubits = set()
        for op in transpile_results:
            name = self._get_op_name(op)
            if name is None:
                continue
            if name.lower() in _SKIP_OPS:
                continue
            targets = self._get_op_targets(op)
            all_qubits.update(targets)

        sorted_qubits = sorted(all_qubits)
        remap = {phys: compact for compact, phys in enumerate(sorted_qubits)}
        actual_num_qubits = len(sorted_qubits)

        # Second pass: build steps with remapped qubit indices.
        steps = []
        step_index = 0
        for op in transpile_results:
            name = self._get_op_name(op)
            if name is None:
                continue
            name = name.lower()

            if name in _SKIP_OPS:
                continue

            targets = self._get_op_targets(op)
            arg_value = self._get_op_arg_value(op)

            remapped_targets = [remap[t] for t in targets]
            gate = {"name": name, "targets": remapped_targets}

            if name == "measure":
                bit = remapped_targets[0]
                gate["bit"] = bit
                gate["cBit"] = bit
            elif arg_value and len(arg_value) > 0:
                gate["theta"] = arg_value[0]

            steps.append({"index": step_index, "gates": [gate]})
            step_index += 1

        return steps, actual_num_qubits

    @staticmethod
    def _get_op_name(op):
        """Extract gate name from either Python or C++ operation."""
        name = getattr(op, "name", None)
        if name is not None:
            return name
        return getattr(op, "gate_name", None)

    @staticmethod
    def _get_op_targets(op):
        """Extract target qubit list from either Python or C++ operation."""
        targets = getattr(op, "targets", None)
        if targets is not None:
            return list(targets)
        targets = getattr(op, "qubits", None)
        if targets is not None:
            return list(targets)
        return []

    @staticmethod
    def _get_op_arg_value(op):
        """Extract parameter values from either Python or C++ operation."""
        arg_value = getattr(op, "arg_value", None)
        if arg_value is not None:
            return list(arg_value)
        params = getattr(op, "params", None)
        if params is not None:
            return list(params)
        return []

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    def submit_task(self, job_id, num_qubits, steps, shots):
        """Submit a task to the TianGong platform.

        Args:
            job_id: job ID (used as project name)
            num_qubits: number of qubits
            steps: circuit steps in TianGong format
            shots: number of repetitions

        Returns:
            success, err_msg, instance_id
        """
        success = True
        err_msgs = []
        instance_id = None

        url = f"{self.base_url}{self.path_executetask}"
        body = {
            "version": "1.1",
            "circuit-type": "simple",
            "computerType": self.computer_type,
            "instanceId": str(job_id),
            "measure-position": list(range(num_qubits)),
            "projectName": str(job_id),
            "quantum-num": num_qubits,
            "classNumber": num_qubits,
            "repetitions": shots,
            "steps": steps,
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        logger.debug(f"submit_task URL: {url}")
        logger.debug(f"submit_task steps count: {len(steps)}")
        logger.debug(
            f"submit_task body: {json.dumps(body, ensure_ascii=False)[:1000]}"
        )

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.POST,
            json=body,
            headers=headers,
            func_name="submit_task",
            timeout=300,
        )
        if status_code in (HttpCode.SUCCESS_OK, 201):
            response = json.loads(text)
            code = response.get("code")
            msg = response.get("msg", "")
            if code == 200:
                instance_id = response["data"]["instanceId"]
            else:
                success = False
                err_msgs.append(f"Submit failed (code={code}): {msg}")
        else:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )

        return success, "\n".join(err_msgs), instance_id

    def check_task_status(self, instance_id, expect_task_status):
        """Check task status.

        Args:
            instance_id: task instance ID
            expect_task_status: list of expected state codes

        Returns:
            success, err_msg, status
        """
        success, err_msg, data = self._get_task_detail(instance_id)
        if not success:
            return False, err_msg, None

        state = data.get("state")
        if state in expect_task_status:
            return True, None, state

        if state == self.state_failed:
            return False, "Task failed", state

        err_msg = f"Task state is {state}, expected {expect_task_status}"
        return False, err_msg, None

    def _get_task_detail(self, instance_id):
        """Fetch raw task detail from the platform.

        Args:
            instance_id: task instance ID

        Returns:
            success, err_msg, data_dict
        """
        success = True
        err_msgs = []
        data = None

        url = f"{self.base_url}{self.path_taskdetail}"
        params = {"instanceId": instance_id}
        headers = {"Authorization": f"Bearer {self.token}"}

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="get_task_detail",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            code = response.get("code")
            msg = response.get("msg", "")
            if code == 200:
                data = response.get("data", {})
            else:
                success = False
                err_msgs.append(f"Task detail failed (code={code}): {msg}")
        else:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )

        return success, "\n".join(err_msgs), data

    def get_task_results(self, instance_id):
        """Get task results (frequency data) for a completed task.

        Args:
            instance_id: task instance ID

        Returns:
            success, err_msg, results_dict (sampling format)
        """
        success, err_msg, data = self._get_task_detail(instance_id)
        if not success:
            return False, err_msg, None

        results = self.convert_results(data)
        return True, None, results

    def get_task_list(self, page=1, page_size=12, project_name="", state=None):
        """List tasks on the platform.

        Args:
            page: page number (1-based)
            page_size: items per page
            project_name: filter by project name (empty = all)
            state: filter by state code (0-3), None for all

        Returns:
            success, err_msg, task_list_data
        """
        success = True
        err_msgs = []
        data = None

        url = f"{self.base_url}{self.path_tasklist}"
        params = {
            "index": page,
            "pagesize": page_size,
            "projectName": project_name,
        }
        if state is not None:
            params["state"] = state
        headers = {"Authorization": f"Bearer {self.token}"}

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="get_task_list",
        )
        if status_code == HttpCode.SUCCESS_OK:
            response = json.loads(text)
            code = response.get("code")
            msg = response.get("msg", "")
            if code == 200:
                data = response.get("data", {})
            else:
                success = False
                err_msgs.append(f"Task list failed (code={code}): {msg}")
        else:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )

        return success, "\n".join(err_msgs), data

    def convert_results(self, data):
        """Convert platform frequency results to sampling format.

        The platform returns frequencyResult as a list of
        {"qState": "00", "freq": 512} dicts. We normalize to
        {"00": 512, "11": 512} for the qcos sampling result type.

        Args:
            data: task detail data dict

        Returns:
            dict of {bitstring: count}
        """
        results = {}
        freq_list = data.get("frequencyResult", [])
        for item in freq_list:
            q_state = item.get("qState", "")
            freq = item.get("freq", 0)
            results[q_state] = freq
        return results

    # ------------------------------------------------------------------
    # Main run() entry point
    # ------------------------------------------------------------------

    def run(
        self, job_id, num_qubits, data, data_type, shots=1, qec_options=None
    ):
        """Run job on the CETC TianGong platform.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data dict containing source_code and transpile_results
            data_type: data type
            shots: number of shots
            qec_options: qec options (unused)
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )
        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Convert code
        logger.info("1. convert code")
        self.set_progress_by_task(self.TASK_STAGE_VALIDATING)
        transpile_results = data["transpile_results"]
        steps, actual_num_qubits = self.convert_code(
            num_qubits, None, transpile_results
        )
        logger.info(
            f"after converting, steps count: {len(steps)}, "
            f"actual qubits: {actual_num_qubits} (input: {num_qubits})"
        )

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg, instance_id = self.submit_task(
            job_id, actual_num_qubits, steps, shots
        )
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")
        logger.info(f"task submitted, instanceId: {instance_id}")

        # 3. Wait for task completion
        logger.info("3. wait for task completion")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_status,
            self.max_job_wait_time,
            self.job_query_interval,
            instance_id,
            expect_task_status=[self.state_completed],
        )
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 4. Get task results
        logger.info("4. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, results = self.get_task_results(instance_id)
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 5. Save results
        logger.info("5. save results")
        self.set_results(
            job_id,
            data_index,
            results=results,
            raw_results={"instanceId": instance_id},
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )

        # 6. Set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
        self.set_progress_by_task(self.TASK_STAGE_COMPLETE)
