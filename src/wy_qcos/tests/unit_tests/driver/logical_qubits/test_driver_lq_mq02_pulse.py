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

from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import numpy as np
import pytest

from wy_qcos.common.config import Config
from wy_qcos.common.library import Library


org_path = Library.set_driver_venv_path(
    "logical_qubit", Config.DEFAULT.VENV_DIR
)

from wy_qcos.common.constant import Constant
from wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse import (
    DriverLqMQ02Pulse,
)


@pytest.mark.driver
class TestDriverLqMQ02Pulse:
    def test_supported_single_qubit_gates(self):
        driver = DriverLqMQ02Pulse()

        assert set(driver.supported_basis_gates) == {
            Constant.SINGLE_QUBIT_GATE_H,
            Constant.SINGLE_QUBIT_GATE_I,
            Constant.SINGLE_QUBIT_GATE_P,
            Constant.SINGLE_QUBIT_GATE_R,
            Constant.SINGLE_QUBIT_GATE_RX,
            Constant.SINGLE_QUBIT_GATE_RY,
            Constant.SINGLE_QUBIT_GATE_RZ,
            Constant.SINGLE_QUBIT_GATE_S,
            Constant.SINGLE_QUBIT_GATE_SDG,
            Constant.SINGLE_QUBIT_GATE_SX,
            Constant.SINGLE_QUBIT_GATE_SXDG,
            Constant.SINGLE_QUBIT_GATE_T,
            Constant.SINGLE_QUBIT_GATE_TDG,
            Constant.SINGLE_QUBIT_GATE_U,
            Constant.SINGLE_QUBIT_GATE_U1,
            Constant.SINGLE_QUBIT_GATE_U2,
            Constant.SINGLE_QUBIT_GATE_U3,
            Constant.SINGLE_QUBIT_GATE_X,
            Constant.SINGLE_QUBIT_GATE_Y,
            Constant.SINGLE_QUBIT_GATE_Z,
        }
        assert Constant.TWO_QUBIT_GATE_CZ not in (driver.supported_basis_gates)

    @patch(
        "wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse.gate.phased_x",
        return_value=28.0,
    )
    @patch("wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse.gate.virtual_z")
    def test_u3_uses_one_physical_pulse(self, virtual_z, phased_x):
        driver = DriverLqMQ02Pulse()
        seq = Mock()
        qubit = {"id": 3}

        end = driver.apply_gate(
            "u3",
            seq,
            qubit,
            8.0,
            parameters=(0.3, 0.4, 0.5),
        )

        assert end == 28.0
        assert virtual_z.call_args_list == [
            call(seq, qubit, phase=0.5),
            call(seq, qubit, phase=0.4),
        ]
        phased_x.assert_called_once_with(
            seq,
            qubit,
            start=8.0,
            theta=0.3,
            phi=np.pi / 2,
        )

    @pytest.mark.parametrize(
        ("gate_name", "parameters", "phase"),
        [
            ("rz", (0.2,), 0.2),
            ("p", (0.3,), 0.3),
            ("u1", (0.4,), 0.4),
            ("tdg", (), -np.pi / 4),
        ],
    )
    @patch("wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse.gate.virtual_z")
    def test_phase_gates_are_zero_duration(
        self, virtual_z, gate_name, parameters, phase
    ):
        driver = DriverLqMQ02Pulse()
        seq = Mock()
        qubit = {"id": 1}

        end = driver.apply_gate(
            gate_name, seq, qubit, 12.0, parameters=parameters
        )

        assert end == 12.0
        virtual_z.assert_called_once_with(seq, qubit, phase=phase)

    @patch(
        "wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse."
        "gate.measure_ring_flattop"
    )
    @patch("wy_qcos.driver.logical_qubit.driver_lq_mq02_pulse.Sequence")
    def test_convert_code_parallelizes_drives_and_readout(
        self, sequence_cls, measure
    ):
        driver = DriverLqMQ02Pulse()
        qpu_params = Mock()
        qpu_params.qubit.side_effect = lambda qid: {"id": qid}
        driver.backend = Mock()
        driver.backend.get_qpu_params.return_value = qpu_params
        operations = [
            SimpleNamespace(
                name="x", targets=[0], arg_value=[], operation_type=1
            ),
            SimpleNamespace(
                name="y", targets=[1], arg_value=[], operation_type=1
            ),
            SimpleNamespace(
                name="x", targets=[0], arg_value=[], operation_type=1
            ),
            SimpleNamespace(
                name="measure", targets=[0], arg_value=[], operation_type=4
            ),
            SimpleNamespace(
                name="measure", targets=[1], arg_value=[], operation_type=4
            ),
        ]

        with patch.object(
            driver,
            "apply_gate",
            side_effect=lambda name, seq, qubit, start, parameters: start
            + 20.0,
        ) as apply_gate:
            sequence = driver.convert_code(operations, {})

        assert sequence is sequence_cls.return_value
        assert [item.args[3] for item in apply_gate.call_args_list] == [
            0.0,
            0.0,
            20.0,
        ]
        assert measure.call_args_list == [
            call(sequence, {"id": 0}, start=40.0),
            call(sequence, {"id": 1}, start=40.0),
        ]
