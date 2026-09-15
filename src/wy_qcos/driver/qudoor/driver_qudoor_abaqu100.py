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

import json
import time

from loguru import logger
from schema import And, Optional, Schema

from wy_qcos.common.constant import Constant, HttpCode, HttpMethod
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.qudoor.driver_qudoor_base import (
    DriverQudoorBase,
    CODE_SUCCESS,
    ERROR_CODES,
    TASK_STATUS,
    TASK_STATUS_FAILURE,
    TASK_STATUS_SUCCESS,
    _CONTROLLED_GATES,
    _DOUBLE_CONTROLLED_GATES,
    _SKIP_OPS,
    _SYMMETRIC_TWO_QUBIT_GATES,
)


class DriverQudoorAbaQu100(DriverQudoorBase):
    """启科量子 AbaQu100 离子阱驱动."""

    # API paths (appended to base_url)
    path_device_query = "/api/cmccos/device/get"
    path_task_add = "/api/cmccos/task/add"
    path_task_result = "/api/cmccos/task/get/result"

    def __init__(self):
        super().__init__()
        self.alias_name = "启科量子 AbaQu100 离子阱驱动"
        self.description = "启科量子 AbaQu100 离子阱驱动"
        self.supported_basis_gates = [
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_U1,
            Constant.SINGLE_QUBIT_GATE_U2,
            Constant.SINGLE_QUBIT_GATE_U3,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_SWAP,
            Constant.TWO_QUBIT_GATE_CP,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.THREE_QUBIT_GATE_CCX,
        ]
        self.supported_transpilers = [
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        self.max_qubits = 20

        # QuDoor platform config
        self.eng_code = ""
        self.user_id = "demo_user"

        # Input constraints: shots must be a positive integer
        self.input_constrains["job_shots"] = Schema(And(int, lambda x: x >= 1))

        # Transpiler options
        self.transpiler_options_schema["enable_mapping"] = (
            Optional("enable_mapping", default=False),
            bool,
        )

        # Task stages
        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_VALIDATING: 20,
            self.TASK_STAGE_SUBMIT_TASK: 40,
            self.TASK_STAGE_WAIT_TASK: 60,
            self.TASK_STAGE_GET_RESULTS: 80,
            self.TASK_STAGE_COMPLETE: 100,
        }

        # Driver options overrides
        self.driver_options_schema.update({
            Optional("url"): str,
            Optional("client_id"): str,
            Optional("device_code"): str,
            Optional("eng_code"): str,
            Optional("user_id"): str,
        })

    def get_device_info(self):
        """Get device info via /api/cmccos/device/get (GET).

        Fetches real-time device status and trapped-ion hardware
        parameters from the QuDoor platform.

        Response fields: clientId, engCode, type (10=trapped ion),
        status (1=online), statusDesc, statusStartTime,
        statusEndTime, sign, and params containing paramUpdateTime
        and trappedIon (maxQubits, timing, singleQubit,
        doubleQubit, spamError).

        Returns:
            (success, err_msg, data) where *data* is the parsed
            device-info dict on success.
        """
        success = True
        err_msgs = []
        data = None

        url = f"{self.base_url}{self.path_device_query}"
        params = {
            "clientId": self.client_id,
            "engCode": self.eng_code,
        }
        params["sign"] = self.client_id
        headers = {
            "Content-Type": "application/json",
            **self.default_headers,
        }

        logger.info(f"get_device_info url: {url}")

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="get_device_info",
            timeout=30,
        )
        if status_code != HttpCode.SUCCESS_OK:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )
            return success, "\n".join(err_msgs), data

        if not text:
            success = False
            err_msgs.append("Empty response body")
            return success, "\n".join(err_msgs), data

        try:
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            success = False
            err_msgs.append("Failed to parse response")
            return success, "\n".join(err_msgs), data

        # Response is the device-info object directly (no code/data wrapper).
        if not isinstance(result, dict):
            success = False
            err_msgs.append("Invalid response format")
            return success, "\n".join(err_msgs), data

        data = result
        logger.info(
            f"device info: engCode={data.get('engCode', '')}, "
            f"status={data.get('status')}, "
            f"statusDesc={data.get('statusDesc', '')}"
        )
        return success, "\n".join(err_msgs), data

    # API camelCase -> schema snake_case key maps for trapped-ion params
    _TIMING_KEY_MAP = {
        "t1Min": "t1_min",
        "t2Min": "t2_min",
        "t1Avg": "t1_avg",
        "t2Avg": "t2_avg",
        "t1Opt": "t1_opt",
        "t2Opt": "t2_opt",
    }
    _FIDELITY_KEY_MAP = {
        "fidelityMin": "fidelity_min",
        "fidelityAvg": "fidelity_avg",
        "fidelityOpt": "fidelity_opt",
    }

    @staticmethod
    def _map_keys(source, key_map):
        """Rename dict keys using *key_map* (camelCase -> snake_case).

        Keys not in *key_map* are preserved as-is.
        """
        if not source:
            return {}
        return {key_map.get(k, k): v for k, v in source.items()}

    def fetch_running_info(self):
        """Fetch running info from the QuDoor platform.

        Calls :meth:`get_device_info` to obtain real-time device
        status and hardware parameters, then maps the QuDoor numeric
        status to the qcos ``Device`` status strings.

        Trapped-ion sub-field names returned by the API in camelCase
        (e.g. ``t1Min``, ``fidelityOpt``) are converted to the
        snake_case form used by ``DEVICE_INFO_SCHEMA`` (e.g.
        ``t1_min``, ``fidelity_opt``).

        Returns:
            device_running_info dict with keys:
                status          - Device status string (online/offline/...)
                available_qubits - Max supported qubits
                details         - Hardware parameters and calibration info
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

        # Map QuDoor numeric status to qcos Device status strings
        raw_status = data.get("status", 0)
        status_map = {
            0: Device.DEVICE_STATUS_OFFLINE,
            1: Device.DEVICE_STATUS_ONLINE,
            2: Device.DEVICE_STATUS_BUSY,
            3: Device.DEVICE_STATUS_MAINTAIN,
        }
        status = status_map.get(raw_status, Device.DEVICE_STATUS_UNKNOWN)

        # Extract hardware parameters
        hw_params = data.get("params", {}) or {}
        trapped_ion = hw_params.get("trappedIon", {}) or {}
        max_qubits = trapped_ion.get("maxQubits", 0)

        device_running_info = {
            "status": status,
            "available_qubits": max_qubits,
            "last_updated_at": hw_params.get("paramUpdateTime", ""),
            "details": {
                "calibration": {
                    "timing": self._map_keys(
                        trapped_ion.get("timing", {}),
                        self._TIMING_KEY_MAP,
                    ),
                    "single_qubit_fidelity": self._map_keys(
                        trapped_ion.get("singleQubit", {}),
                        self._FIDELITY_KEY_MAP,
                    ),
                    "double_qubit_fidelity": self._map_keys(
                        trapped_ion.get("doubleQubit", {}),
                        self._FIDELITY_KEY_MAP,
                    ),
                    "spam_error": trapped_ion.get("spamError", {}),
                },
            },
        }
        return device_running_info

    # ------------------------------------------------------------------
    # Circuit conversion: GateOperation -> circuits list
    # ------------------------------------------------------------------

    def _split_controls_targets(self, op):
        """Split operation qubits into controls and targets.

        For controlled gates (cx, cy, cz, cp), the first qubit in
        targets is the control and the rest are targets.
        For double-controlled gates (ccx, cswap, ccz), first two
        are controls.
        """
        name = self._get_op_name(op)
        all_qubits = self._get_op_targets(op)

        if name in _DOUBLE_CONTROLLED_GATES:
            return all_qubits[:2], all_qubits[2:]
        if name in _CONTROLLED_GATES:
            return all_qubits[:1], all_qubits[1:]
        if name in _SYMMETRIC_TWO_QUBIT_GATES:
            return [], all_qubits
        return [], all_qubits

    def _build_qasmdef(self, op):
        """Build QASM-like definition string for a gate operation.

        Examples: h q[0], cx q[0],q[1], rx(1.57) q[0]
        """
        name = self._get_op_name(op)
        controls, targets = self._split_controls_targets(op)
        args = self._get_op_arg_value(op)

        all_qubits = controls + targets
        qubits_str = ",".join(f"q[{q}]" for q in all_qubits)

        if args:
            params_str = ",".join(str(a) for a in args)
            return f"{name}({params_str}) {qubits_str}"
        return f"{name} {qubits_str}"

    def convert_code(self, num_qubits, transpile_results):
        """Convert transpile_results to circuit format.

        Transforms a list of GateOperation / Measure objects into the
        circuits list format expected by the /api/cmccos/task/add API.

        Args:
            num_qubits: number of qubits
            transpile_results: list of GateOperation / Measure objects

        Returns:
            tuple of (circuits_list, num_qubits)
        """
        if not transpile_results:
            return [], num_qubits

        for op in transpile_results:
            if not hasattr(op, "name"):
                return [], num_qubits

        circuits = []
        actual_qubits = num_qubits

        for op in transpile_results:
            name = self._get_op_name(op)

            if name in _SKIP_OPS:
                continue

            controls, targets = self._split_controls_targets(op)
            rotations = self._get_op_arg_value(op)
            qasmdef = self._build_qasmdef(op)

            circuits.append({
                "gate": name,
                "controls": controls,
                "targets": targets,
                "rotations": rotations,
                "qasmdef": qasmdef,
            })

            all_qubits = controls + targets
            if all_qubits:
                actual_qubits = max(actual_qubits, max(all_qubits) + 1)

        logger.info(
            f"convert_code: {len(circuits)} gates, "
            f"actual qubits: {actual_qubits}"
        )
        return circuits, actual_qubits

    # ------------------------------------------------------------------
    # Async task submission
    # ------------------------------------------------------------------

    def submit_task(self, job_id, circuits, num_qubits, shots):
        """Submit task via /api/cmccos/task/add.

        Sends a plain JSON request and returns the task ID + status.

        Args:
            job_id: job ID
            circuits: list of circuit gate dicts
            num_qubits: number of qubits
            shots: number of experiment shots

        Returns:
            tuple of (success, err_msg, job_id, task_status)
        """
        url = f"{self.base_url}{self.path_task_add}"
        create_time = time.strftime("%Y-%m-%d %H:%M:%S")

        in_data = {"circuits": circuits}

        params = {
            "clientId": self.client_id,
            "engCode": self.eng_code,
            "taskId": job_id,
            "userId": self.user_id,
            "examNum": shots,
            "createTime": create_time,
            "inDataType": 3,
            "inData": in_data,
            "quanNum": num_qubits,
            "engName": f"demo_{job_id[:8]}",
            "priorit": 3,
        }
        params["sign"] = self.client_id

        headers = {
            "Content-Type": "application/json",
            **self.default_headers,
        }

        logger.info(
            f"submit_task url: {url}, "
            f"taskId: {job_id}, qubits: {num_qubits}, "
            f"shots: {shots}, gates: {len(circuits)}"
        )
        logger.debug(
            f"submit_task params: {json.dumps(params, ensure_ascii=False)}"
        )

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.POST,
            data=json.dumps(params, ensure_ascii=False),
            headers=headers,
            func_name="submit_task",
            timeout=60,
        )
        if status_code != HttpCode.SUCCESS_OK:
            err_msg = (
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )
            return False, err_msg, None, None

        if not text:
            return False, "Empty response body", None, None

        try:
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return False, "Failed to parse response", None, None

        code = result.get("code")
        if code != CODE_SUCCESS:
            err_desc = ERROR_CODES.get(code, f"unknown code {code}")
            err_msg = (
                f"submit failed (code={code}): "
                f"{result.get('msg', '')}, desc={err_desc}"
            )
            return False, err_msg, None, None

        data = result.get("data", {})
        job_id = data.get("taskId", job_id)
        task_status = data.get("taskStatus", "unknown")

        logger.info(f"task submitted: taskId={job_id}, status={task_status} ")
        return True, None, job_id, task_status

    def check_task_status(self, task_id, expect_task_status):
        """Check task status.

        Called by ``loop_with_timeout`` for polling.  Returns
        ``(success, err_msg, status)`` per the loop contract.

        Args:
            task_id: task ID
            expect_task_status: expected status value or list of values

        Returns:
            (success, err_msg, status)
        """
        url = f"{self.base_url}{self.path_task_result}"
        params = {"taskId": task_id}
        headers = {
            "Content-Type": "application/json",
            **self.default_headers,
        }

        logger.debug(f"query task url: {url}, taskId: {task_id}")

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="check_task_status",
            timeout=30,
        )
        if status_code != HttpCode.SUCCESS_OK:
            return (
                False,
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}",
                None,
            )

        if not text:
            return False, "Empty response body", None

        try:
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return False, "Failed to parse response", None

        task_status = result.get("taskStatus", 0)
        status_name = TASK_STATUS.get(task_status, "unknown")
        logger.debug(
            f"task status: taskId={task_id}, "
            f"status={task_status} ({status_name})"
        )

        expected_statuses = (
            {expect_task_status}
            if isinstance(expect_task_status, int)
            else set(expect_task_status)
        )
        if task_status in expected_statuses:
            return True, None, task_status

        if task_status in TASK_STATUS_FAILURE:
            raise ValueError(
                f"task {task_id} failed with status "
                f"{task_status} ({status_name})"
            )

        err_msg = (
            f"Task status is not in {expected_statuses}, "
            f"current status: {task_status} ({status_name})"
        )
        return False, err_msg, task_status

    def get_task_results(self, task_id):
        """Get task results via /api/cmccos/task/get/result (GET).

        The response has no code/data envelope; taskStatus is at the top
        level and results are in the ``outData`` field.  When the task
        is not yet finished, ``outData`` is a plain string (e.g.
        "已提交."); when taskStatus == 5 (success), ``outData`` is a
        dict containing a ``probs`` list of
        ``{"qstate": "00000", "prob": 0.25}`` items.

        Args:
            task_id: task ID

        Returns:
            (success, err_msg, data) where *data* is the ``outData``
            dict on success.
        """
        success = True
        err_msgs = []
        data = None

        url = f"{self.base_url}{self.path_task_result}"
        params = {"taskId": task_id}
        headers = {
            "Content-Type": "application/json",
            **self.default_headers,
        }

        logger.info(f"get results url: {url}, taskId: {task_id}")

        status_code, reason, text, _ = Library.call_http_api(
            url,
            HttpMethod.GET,
            params=params,
            headers=headers,
            func_name="get_task_results",
            timeout=60,
        )
        if status_code != HttpCode.SUCCESS_OK:
            success = False
            err_msgs.append(
                f"HTTP {status_code}: {reason}, "
                f"response: {text[:500] if text else 'None'}"
            )
            return success, "\n".join(err_msgs), data

        if not text:
            success = False
            err_msgs.append("Empty response body")
            return success, "\n".join(err_msgs), data

        try:
            result = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            success = False
            err_msgs.append("Failed to parse response")
            return success, "\n".join(err_msgs), data

        task_status = result.get("taskStatus", 0)
        status_name = TASK_STATUS.get(task_status, "unknown")
        logger.info(
            f"task result: taskId={task_id}, "
            f"status={task_status} ({status_name})"
        )

        if task_status == TASK_STATUS_SUCCESS:
            out_data = result.get("outData")
            if isinstance(out_data, str):
                try:
                    out_data = json.loads(out_data)
                except (json.JSONDecodeError, ValueError):
                    out_data = None
            if isinstance(out_data, dict):
                data = out_data
            else:
                data = {}
            logger.info(
                f"outData type={type(result.get('outData'))}, "
                f"data keys={list(data.keys()) if data else 'empty'}"
            )
        else:
            success = False
            err_msgs.append(
                f"task not succeeded: status={task_status} "
                f"({status_name}), outData={result.get('outData', '')}"
            )

        return success, "\n".join(err_msgs), data

    # ------------------------------------------------------------------
    # Results conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _probs_to_counts(probs, shots):
        """Convert probability list to integer counts.

        Args:
            probs: list of {"qstate": "00000", "prob": 0.25}
            shots: number of shots

        Returns:
            dict of {bitstring: count}
        """
        results = {}
        total = 0
        for item in probs:
            state = item.get("qstate") or item.get("state", "")
            prob = float(item.get("prob", 0.0))
            count = round(prob * shots)
            results[state] = count
            total += count

        if results and total != shots:
            max_state = max(results, key=results.get)
            results[max_state] += shots - total

        return results

    def convert_results(self, results, shots=None):
        """Convert raw results to qcos sampling format.

        Args:
            results: raw results dict from the API
            shots: number of shots (needed for prob conversion)

        Returns:
            dict of {bitstring: count}
        """
        if results is None:
            return {}

        keys = list(results.keys()) if isinstance(results, dict) else "N/A"
        logger.info(
            f"convert_results: results={results}, shots={shots}, keys={keys}"
        )

        # QuDoor format: probs list
        if "probs" in results:
            probs = results.get("probs", [])
            if probs:
                return self._probs_to_counts(probs, shots or 1)

        # QuDoor format: counts dict
        if "counts" in results:
            counts = results.get("counts", {})
            if counts:
                return dict(counts)

        # Direct format: {bitstring: count}
        return {k: v for k, v in results.items() if k not in ("probs", "amps")}

    # ------------------------------------------------------------------
    # Main run() entry point
    # ------------------------------------------------------------------

    def run(
        self, job_id, num_qubits, data, data_type, shots=1, qec_options=None
    ):
        """Run job on the QuDoor platform.

        Follows the async driver pattern:
        1. Convert code -> circuits
        2. Submit task (/api/cmccos/task/add)
        3. Poll task status (loop_with_timeout)
        4. Get task results (/api/cmccos/task/get/result)
        5. Convert and save results

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
        circuits, actual_num_qubits = self.convert_code(
            num_qubits, transpile_results
        )
        logger.info(
            f"after converting, circuits count: {len(circuits)}, "
            f"actual qubits: {actual_num_qubits} (input: {num_qubits})"
        )

        # 2. Submit task
        logger.info("2. submit task")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        success, err_msg, task_id, task_status = self.submit_task(
            job_id, circuits, actual_num_qubits, shots
        )
        if not success:
            raise ValueError(f"Failed to submit task [{job_id}]: {err_msg}")

        # 3. Wait for task_status success
        logger.info("3. wait for task_status is success")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        success, _, _ = Library.loop_with_timeout(
            self.check_task_status,
            self.max_job_wait_time,
            self.job_query_interval,
            task_id,
            expect_task_status=[TASK_STATUS_SUCCESS],
        )
        if not success:
            raise ValueError(f"Failed to get task results [{job_id}]")

        # 4. Get task results
        logger.info("4. get task results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        success, err_msg, _results = self.get_task_results(task_id)
        if not success:
            raise ValueError(
                f"Failed to get task results [{job_id}]: {err_msg}"
            )

        # 5. Convert and save results
        logger.info("5. convert and save results")
        results = self.convert_results(_results, shots)
        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )

        # 6. Set driver status to ONLINE
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
