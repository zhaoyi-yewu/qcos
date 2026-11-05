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

import os
import numpy as _np

from loguru import logger
from schema import Optional, Or

# spinqit is an optional dependency (pyproject.toml: driver-spinq-cloud).
# We use lazy imports so the module can be imported without spinqit
# installed.  This allows Prefect to load the deployment's flow function
# (which imports the driver module) even when spinqit is absent.
# The actual spinqit calls happen inside methods that do local imports.

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.device.device import Device
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.driver.driver_gate_base import DriverGateBase

# spinqit gate mapping (lazy-loaded; rebuilt when spinqit is available)
_spinqit_gates = None


def _get_spinqit_gates():
    """Lazily build the qcos-gate-name -> spinqit-gate-object mapping."""
    global _spinqit_gates
    if _spinqit_gates is None:
        from spinqit import (
            I,
            H,
            X,
            Y,
            Z,
            Rx,
            Ry,
            Rz,
            P,
            T,
            Td,
            S,
            Sd,
            CX,
            CY,
            CZ,
            SWAP,
            CCX,
            U,
        )

        _spinqit_gates = {
            "i": I,
            "id": I,
            "h": H,
            "x": X,
            "y": Y,
            "z": Z,
            "rx": Rx,
            "ry": Ry,
            "rz": Rz,
            "p": P,
            "t": T,
            "tdg": Td,
            "s": S,
            "sdg": Sd,
            "cx": CX,
            "cnot": CX,
            "cy": CY,
            "cz": CZ,
            "swap": SWAP,
            "ccx": CCX,
            "u": U,
        }
    return _spinqit_gates


class DriverSpinqBase(DriverGateBase):
    """量旋云平台驱动基类.

    Submits quantum circuits to SpinQ Cloud via the spinqit SDK and
    retrieves sampling results.
    """

    default_host = "https://cloud.spinq.com/api"
    default_shots = 1024

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.alias_name = "量旋科技 云平台驱动"
        self.description = "量旋科技 云平台驱动"
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NONE
        self.supported_basis_gates = []
        self.supported_transpilers = [
            Constant.TRANSPILER_CMSS,
            Constant.TRANSPILER_HIGH_PERFORMANCE_CMSS,
        ]
        self.enable_circuit_aggregation = True
        self.max_qubits = 0
        self.default_data_type = DriverBase.DATA_TYPE_GATE_SEQUENCE

        self.task_stages = {
            self.TASK_STAGE_START: 0,
            self.TASK_STAGE_USER_AUTHENTICATION: 10,
            self.TASK_STAGE_SUBMIT_TASK: 20,
            self.TASK_STAGE_WAIT_TASK: 30,
            self.TASK_STAGE_GET_RESULTS: 95,
            self.TASK_STAGE_COMPLETE: 100,
        }

        # private variables
        self._username = None
        self._keyfile = None
        self._host = None
        self._platform = None
        self._cloud_backend = None
        self.enable_device_monitor = True

    def init_driver(self):
        """Init driver."""
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)

    def close_driver(self):
        """Close driver."""
        # SpinQCloudBackend holds an HTTP client; nothing explicit to close.
        self._cloud_backend = None

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
            "username": str,
            "keyfile": str,
            "host": str,
            Optional("platform"): str,
            Optional("machine_code"): str,
            Optional("transpiler"): {
                "qpu_configs": {
                    "qubits": int,
                    Optional("storage_area"): [str],
                    Optional("operate_area"): [str],
                    Optional("coupler_map"): {str: [str]},
                    Optional("readout_error"): {str: Or(float, int)},
                    Optional("coupler_error"): {str: Or(float, int)},
                    Optional("closest"): {str: str},
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
        """Fetch configs.

        Connects to SpinQ Cloud, authenticates, and retrieves platform
        information to build transpiler configs.

        Returns:
            remote transpiler configs
        """
        extra_configs = self.get_configs()
        self._username = extra_configs.get("username", "")
        self._keyfile = os.path.expanduser(extra_configs.get("keyfile", ""))
        self._host = extra_configs.get("host", self.default_host)
        self._platform = extra_configs.get("platform", self._platform)
        self._machine_code = extra_configs.get("machine_code", self._platform)

        if self._platform is None:
            raise ValueError(
                "No platform specified. Subclasses must set self._platform "
                "or the config file must provide a 'platform' value."
            )

        # authenticate and create cloud backend
        logger.info("1. user authentication (SpinQ Cloud)")
        self.set_progress_by_task(self.TASK_STAGE_USER_AUTHENTICATION)
        try:
            # numpy >= 2.0 removed msort
            from spinqit.backend.client.spinq_session import SpinQSession

            # numpy >= 2.0 removed msort
            if not hasattr(_np, "msort"):
                _np.msort = lambda a: _np.sort(a, axis=0)

            # Patch SpinQSession *before* creating the backend so that
            # the HTTP calls made inside SpinQCloudBackend.__init__()
            # (login + refresh_remote_platforms) also have a timeout.
            # The SDK's SpinQSession extends requests.Session but sets no
            # default timeout, so an unreachable host hangs forever.
            _default_timeout = 30
            try:
                if not getattr(SpinQSession, "_qcos_timeout_patched", False):
                    _orig_init = SpinQSession.__init__
                    _log_http = extra_configs.get("debug", False)

                    def _patched_session_init(self):
                        _orig_init(self)
                        _og = self.get
                        _op = self.post

                        def _wrapped_get(*a, **kw):
                            _url = a[0] if a else kw.get("url", "?")
                            logger.info(f"HTTP GET {_url}")
                            _resp = _og(
                                *a,
                                timeout=kw.pop("timeout", _default_timeout),
                                **kw,
                            )
                            if _log_http:
                                logger.info(
                                    f"HTTP GET {_url} -> "
                                    f"{_resp.status_code} "
                                    f"{_resp.text[:500]}"
                                )
                            return _resp

                        def _wrapped_post(*a, **kw):
                            _url = a[0] if a else kw.get("url", "?")
                            logger.info(f"HTTP POST {_url}")
                            _resp = _op(
                                *a,
                                timeout=kw.pop("timeout", _default_timeout),
                                **kw,
                            )
                            if _log_http:
                                logger.info(
                                    f"HTTP POST {_url} -> "
                                    f"{_resp.status_code} "
                                    f"{_resp.text[:500]}"
                                )
                            return _resp

                        self.get = _wrapped_get
                        self.post = _wrapped_post

                    SpinQSession.__init__ = _patched_session_init
                    SpinQSession._qcos_timeout_patched = True
                    logger.info(
                        f"patched SpinQSession with "
                        f"{_default_timeout}s timeout"
                    )
            except ImportError:
                logger.warning(
                    "   SpinQSession not found; timeout patch skipped"
                )

            # Monkey-patch spinqit SDK's hardcoded HOST constant.
            # Some SDK versions (e.g. production Python 3.11 builds)
            # have a spinq_client.py module with a module-level HOST
            # constant (default: https://cloud.spinq.com) that is
            # used instead of the host parameter.  We must override it
            # before authentication.  If spinq_client.py does not exist
            # (e.g. the local Python 3.10 dev env), we inject a mock
            # into sys.modules so that any `from spinqit.backend.client
            # import spinq_client` inside the SDK resolves instead of
            # raising ImportError.
            _patched_host = self._host.rstrip("/")
            try:
                from spinqit.backend.client import spinq_client as _sc

                _sc.HOST = _patched_host
                logger.info(f"   patched SDK HOST -> {_patched_host}")
            except ImportError:
                import sys as _sys
                import types as _types

                _mock = _types.ModuleType(
                    "spinqit.backend.client.spinq_client"
                )
                _mock.HOST = _patched_host
                _sys.modules["spinqit.backend.client.spinq_client"] = _mock
                try:
                    import spinqit.backend.client as _client_pkg

                    _client_pkg.spinq_client = _mock
                except Exception:
                    logger.debug(
                        "Could not attach spinq_client mock to package"
                    )
                logger.info(
                    f"   spinq_client not found; injected mock "
                    f"with HOST={_patched_host}"
                )

            from spinqit.backend import get_spinq_cloud

            self._cloud_backend = get_spinq_cloud(
                self._username, self._keyfile, host=self._host
            )

        except Exception as e:
            raise ValueError(f"SpinQ Cloud authentication failed: {e}") from e

        # retrieve platform info for transpiler configs
        platform = None
        for p in self._cloud_backend.platforms:
            if p.code == self._platform:
                platform = p
                break
        if platform is None:
            available = [p.code for p in self._cloud_backend.platforms]
            raise ValueError(
                f"Platform '{self._platform}' not found. "
                f"Available: {available}"
            )

        self.available_num_qubits = platform.max_bitnum

        # build coupler_map in qcos format: {"0": ["1"], "1": ["0","2"], ...}
        coupler_map = {}
        for src, dst in platform.coupling_map:
            coupler_map.setdefault(str(src), []).append(str(dst))
            coupler_map.setdefault(str(dst), []).append(str(src))

        transpiler_configs = {
            "qpu_configs": {
                "qubits": platform.max_bitnum,
                "coupler_map": coupler_map,
            }
        }
        return transpiler_configs

    def convert_to_spinqit_circuit(self, transpile_results, num_qubits):
        """Convert qcos transpile_results to a spinqit Circuit.

        Args:
            transpile_results: list of GateOperation / Measure objects
            num_qubits: number of logical qubits

        Returns:
            spinqit Circuit
        """
        from spinqit.model import Circuit

        circ = Circuit()
        circ.allocateQubits(num_qubits)

        gate_map = _get_spinqit_gates()

        # Non-gate operations silently skipped. SpinQ Cloud auto-measures
        # all qubits at the end, so explicit MEASURE instructions are not
        # needed.
        _skip_ops = {"measure", "sync", "move", "reset", "barrier"}

        for obj in transpile_results:
            # Use duck-typing instead of isinstance() so that both Python
            # GateOperation objects (from the cmss transpiler) and C++
            # BaseOperation objects (from the high_performance_cmss
            # transpiler, bound via nanobind) are handled correctly. The
            # isinstance check against Python GateOperation/Measure would
            # reject all C++ BaseOperation objects, producing an empty
            # circuit ("Cannot submit a task with empty circuit").
            name = obj.name
            if name in _skip_ops:
                continue

            spinqit_gate = gate_map.get(name, None)
            if spinqit_gate is None:
                raise ValueError(
                    f"Gate '{name}' is not supported "
                    f"by {self.__class__.__name__}"
                )

            targets = obj.targets
            params = obj.arg_value

            if params and len(params) > 0:
                circ << (spinqit_gate, targets, params[0])
            else:
                circ << (spinqit_gate, targets)

        return circ

    def convert_results(self, result):
        """Convert SpinQCloudResult to qcos sampling results.

        Args:
            result: SpinQCloudResult object

        Returns:
            dict of binary-string -> count
        """
        if result is None:
            raise ValueError(
                "SpinQ Cloud returned no result (task may have failed)"
            )

        counts = result.counts
        if counts:
            return dict(counts)

        probs = result.probabilities
        if probs:
            shots = result._shots or self.default_shots
            return {k: int(round(v * shots)) for k, v in probs.items()}

        raise ValueError("SpinQ Cloud returned no counts or probabilities")

    def cancel(self, job_id):
        """Cancel running job in driver.

        Args:
            job_id: job ID
        """
        logger.info(f"Cancel job: job_id: {job_id}")

    def run(
        self,
        job_id,
        num_qubits,
        data,
        data_type,
        shots=1,
        qec_options=None,
    ):
        """Run job.

        Args:
            job_id: job ID
            num_qubits: number of qubits
            data: data
            data_type: data type
            shots: shots (Default value = 1)
            qec_options: qec options
        """
        # pylint: disable=duplicate-code
        data_index = data["index"]
        logger.info(
            f"job_id: {job_id}, shots: {shots}, num_qubits: {num_qubits}, "
            f"data_type: {data_type}, data: {data}"
        )

        self.set_progress_by_task(self.TASK_STAGE_START)
        self.set_device_status(Device.DEVICE_STATUS_BUSY)

        # 1. Convert transpile_results to spinqit Circuit and compile to IR
        logger.info("1. convert transpile_results to spinqit circuit")
        transpile_results = data["transpile_results"]
        circ = self.convert_to_spinqit_circuit(transpile_results, num_qubits)

        from spinqit import get_compiler
        from spinqit.backend import SpinQCloudConfig

        comp = get_compiler("native")
        ir = comp.compile(circ, 0)

        # 2. Configure and submit task
        logger.info("2. submit task to SpinQ Cloud")
        self.set_progress_by_task(self.TASK_STAGE_SUBMIT_TASK)
        task_name = f"{job_id}_{data_index}"
        task_desc = f"qcos: {task_name}"

        config = SpinQCloudConfig()
        config.configure_platform(self._platform)
        config.configure_task(task_name, task_desc)
        config.configure_shots(shots)

        # 3. Wait for task and get results (execute handles both)
        logger.info("3. wait for task and get results")
        self.set_progress_by_task(self.TASK_STAGE_WAIT_TASK)
        result = self._cloud_backend.execute(ir, config)

        # 4. Convert results
        logger.info("4. convert results")
        self.set_progress_by_task(self.TASK_STAGE_GET_RESULTS)
        results = self.convert_results(result)

        # 5. Save results and set driver status to ONLINE
        self.set_results(
            job_id,
            data_index,
            results=results,
            result_type=Constant.RESULT_TYPE_SAMPLING,
        )
        self.set_device_status(Device.DEVICE_STATUS_ONLINE)
