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

from loguru import logger

from wy_qcos.common.constant import Constant
from wy_qcos.device.device import Device
from wy_qcos.driver.spinq.driver_spinq_base import (
    DriverSpinqBase,
)


class DriverSpinqSqc25(DriverSpinqBase):
    """量旋科技 SQC-25 云平台超导驱动.

    Driver for the SQC-25 platform on SpinQ Cloud.
    """

    def __init__(self):
        super().__init__()
        self._platform = "sqc_25_vp"
        self.max_qubits = 25
        self.alias_name = "量旋科技 SQC-25 云平台超导驱动"
        self.description = "量旋科技 SQC-25 云平台超导驱动"
        self.supported_basis_gates = [
            # Gates: I, H, X, Y, Z, S, T, RX, RY, RZ, U, CX, CZ, SWAP
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_U,
            Constant.TWO_QUBIT_GATE_CX,
            Constant.TWO_QUBIT_GATE_CZ,
            Constant.TWO_QUBIT_GATE_SWAP,
        ]
        self.tech_type = Constant.TECH_TYPE_SUPERCONDUCTING

    def fetch_running_info(self):
        """Fetch running info via the spinqit SDK.

        Uses ``refresh_remote_platforms()`` to determine online status,
        then calls the machine-spec API
        ``GET /machine/getLatestMachineSpec?machineCode={machine_code}``
        directly through the SDK's HTTP client to retrieve full calibration
        data (T1/T2/f_ro/f_sq/f_cz and topology).  The raw REST call is
        made through ``SpinQSession`` so authentication headers are
        automatically included.

        Returns:
            remote device running info matching DEVICE_INFO_SCHEMA
        """
        # Lazy-load configs if not yet loaded (device monitor path
        # skips fetch_configs since no job_info is passed to init_driver)
        if self._cloud_backend is None:
            try:
                self.fetch_configs()
            except Exception as e:
                logger.warning(
                    f"Failed to fetch configs for running info: {e}"
                )
                return {
                    "status": Device.DEVICE_STATUS_OFFLINE,
                    "details": {},
                }

        # 1. Refresh platform list to get the latest online machine count
        try:
            self._cloud_backend.refresh_remote_platforms()
        except Exception as e:
            logger.warning(f"Failed to refresh platforms: {e}")
            return {
                "status": Device.DEVICE_STATUS_OFFLINE,
                "details": {},
            }

        try:
            platform = self._cloud_backend.get_platform(self._platform)
        except Exception as e:
            logger.warning(f"Platform '{self._platform}' not found: {e}")
            return {
                "status": Device.DEVICE_STATUS_OFFLINE,
                "details": {},
            }

        # 2. Determine status from online machine count
        status = (
            Device.DEVICE_STATUS_ONLINE
            if platform.available()
            else Device.DEVICE_STATUS_OFFLINE
        )

        # 3. Call the machine-spec API to get full calibration data
        #    API: GET /machine/getLatestMachineSpec?machineCode={machine_code}
        #    The SDK's SpinQSession carries valid auth headers, so we reuse it.
        #    machine_code defaults to self._platform when not set in config.
        machine_code = getattr(self, "_machine_code", self._platform)
        session = self._cloud_backend._api_client._session
        spec_url = (
            f"{self._host}/machine/getLatestMachineSpec?"
            f"machineCode={machine_code}"
        )
        try:
            resp = session.get(spec_url)
            resp.raise_for_status()
            spec_data = resp.json()
            if spec_data.get("status") != 200:
                raise ValueError(
                    f"Machine spec API error: "
                    f"status={spec_data.get('status')}, "
                    f"msg={spec_data.get('msg')}"
                )
            machine = spec_data.get("item", {})
        except Exception as e:
            logger.warning(f"Failed to fetch machine spec: {e}")
            # Fall back to platform-level info (no fidelity data)
            qubit_metrics = []
            if platform.active_qubits:
                for qid in sorted(platform.active_qubits):
                    qubit_metrics.append({"qubit_id": qid})

            coupler_metrics = []
            seen_pairs = set()
            if platform.coupling_map:
                for src, dst in platform.coupling_map:
                    pair = (min(src, dst), max(src, dst))
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        coupler_metrics.append({"qubits": [pair[0], pair[1]]})
            coupler_metrics.sort(
                key=lambda x: (x["qubits"][0], x["qubits"][1])
            )

            return {
                "status": status,
                "available_qubits": platform.max_bitnum,
                "details": {
                    "calibration": {
                        "qubit_metrics": qubit_metrics,
                        "coupler_metrics": coupler_metrics,
                    },
                },
            }

        # 4.Parse single-qubit specs: {qubit_id: {t1, t2, t2_echo, f_ro, f_sq}}
        #    Keys are 1-based strings e.g. "1", "2", ... from the API
        single_spec = machine.get("singleQubitSpec", {}) or {}
        qubit_metrics = []
        for qid_str, spec in single_spec.items():
            qid = int(qid_str) - 1  # API uses 1-based, qcos uses 0-based
            metric = {"qubit_id": qid}
            t1 = spec.get("t1")
            if t1 is not None:
                metric["t1"] = t1
            t2 = spec.get("t2")
            if t2 is not None:
                metric["t2"] = t2
            f_ro = spec.get("f_ro")
            if f_ro is not None:
                metric["readout_fidelity_0"] = f_ro
                metric["readout_fidelity_1"] = f_ro
            qubit_metrics.append(metric)
        qubit_metrics.sort(key=lambda x: x["qubit_id"])

        # 5. Parse two-qubit specs: fidelity map {coupler_key: {f_cz}}
        #    Keys are like "10_5" (1-based)
        dual_spec = machine.get("dualQubitsSpec", {}) or {}
        fidelity_map = {}  # (0-based pair) -> f_cz
        for key, spec in dual_spec.items():
            parts = key.split("_")
            if len(parts) != 2:
                continue
            a, b = int(parts[0]) - 1, int(parts[1]) - 1  # 1-based -> 0-based
            pair = (min(a, b), max(a, b))
            fidelity_map[pair] = spec.get("f_cz")

        # 6.Build coupler_metrics from curCouplingMap (actual running topology)
        #   Falls back to designedCouplingMap if curCouplingMap is absent.
        #   Finally merge f_cz from dualQubitsSpec.
        cur_map_raw = (
            machine.get("curCouplingMap")
            or machine.get("designedCouplingMap")
            or {}
        )
        coupler_metrics = []
        seen_pairs = set()
        for qid_str, neighbors in cur_map_raw.items():
            qid = int(qid_str) - 1  # 1-based -> 0-based
            for nb in neighbors:
                nb_adj = int(nb) - 1
                pair = (min(qid, nb_adj), max(qid, nb_adj))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                metric = {"qubits": [pair[0], pair[1]]}
                cz_fidelity = fidelity_map.get(pair)
                if cz_fidelity is not None:
                    metric["cz_fidelity"] = cz_fidelity
                coupler_metrics.append(metric)
        coupler_metrics.sort(key=lambda x: (x["qubits"][0], x["qubits"][1]))

        # 7. If curCouplingMap is empty, fall back to platform.coupling_map
        if not coupler_metrics and platform.coupling_map:
            for src, dst in platform.coupling_map:
                pair = (min(src, dst), max(src, dst))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    coupler_metrics.append({
                        "qubits": [pair[0], pair[1]],
                        "cz_fidelity": fidelity_map.get(pair),
                    })
            coupler_metrics.sort(
                key=lambda x: (x["qubits"][0], x["qubits"][1])
            )

        device_running_info = {
            "status": status,
            "available_qubits": machine.get("maxBitNum", platform.max_bitnum),
            "details": {
                "calibration": {
                    "last_updated_at": machine.get("latestReviseTime"),
                    "qubit_metrics": qubit_metrics,
                    "coupler_metrics": coupler_metrics,
                },
            },
        }
        return device_running_info
