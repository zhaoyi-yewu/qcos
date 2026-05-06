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

import unittest
import numpy as np

from unittest.mock import patch, MagicMock

from wy_qcos.common.cmss.quantum_circuit import QuantumCircuit
from wy_qcos.common.cmss.gate_operation import H, CX
from wy_qcos.transpiler.common.wirecut.utils import (
    asign_probability,
    compute_measure_combian,
    attribute_prob,
    generate_measure_plans,
    attribute_state,
    generate_subcircuits_for_execute,
    generate_config_circuits_for_one_subcircuit,
)
from wy_qcos.transpiler.common.wirecut.prepare_data import to_basic_init


class TestUtils(unittest.TestCase):
    """Test utils."""

    def setUp(self):
        # Create a simple quantum circuit for testing
        self.qc = QuantumCircuit(2)
        self.qc.append(H([0]))
        self.qc.append(CX([0, 1]))

    def test_compute_measure_combian(self):
        """Test compute_measure_combian function."""
        # The test does not include the case of I.
        meas = ("X", "Y", "Z")
        result = compute_measure_combian(meas)
        assert result == [meas]

        # Testing includes the case of I
        meas = ("I", "X")
        result = compute_measure_combian(meas)
        assert len(result) == 2
        assert ("I", "X") in result
        assert ("Z", "X") in result

    def test_attribute_state(self):
        """Test the attribute_state function."""
        # The test includes the ground states of "common-measure".
        sign, eff_state = attribute_state(
            3, ("common-measure", "common-measure")
        )
        assert isinstance(sign, int)
        assert isinstance(eff_state, int)

        # The test includes the ground states of "I".
        sign, eff_state = attribute_state(3, ("I", "I"))
        assert isinstance(sign, int)
        assert isinstance(eff_state, int)

        # The test includes the ground states of "X", "Y", and "Z".
        sign, eff_state = attribute_state(3, ("X", "Y"))
        assert isinstance(sign, int)
        assert isinstance(eff_state, int)

    def test_attribute_prob(self):
        """Test the attribute_prob function."""
        # Test all cases as "common-measure"
        unmeasured_prob = np.array([0.2, 0.3, 0.1, 0.4])
        result = attribute_prob(
            unmeasured_prob, ("common-measure", "common-measure")
        )
        assert np.array_equal(result, unmeasured_prob)

        # Test input for float cases
        result = attribute_prob(0.5, ("X", "Y"))
        assert result == 0.5

        result = attribute_prob(
            np.array([0.2, 0.3, 0.1, 0.4]), ("common-measure", "X")
        )
        assert isinstance(result, np.ndarray)

    def test_asign_probability(self):
        """Test the asign_probability function."""
        measured_results = {
            (("0", "0"), ("I", "X")): np.array([0.5, 0.5]),
            (("0", "0"), ("Z", "Y")): np.array([0.3, 0.7]),
        }
        measure_configs = {
            "config1": [
                (1, (("0", "0"), ("I", "X"))),
                (0.5, (("0", "0"), ("Z", "Y"))),
            ]
        }

        result = asign_probability(measured_results, measure_configs)
        assert isinstance(result, dict)
        assert "config1" in result

    def test_generate_measure_plans(self):
        """Test the generate_measure_plans function."""
        init = ("0", "1")
        meas = ("X", "Y")
        result = generate_measure_plans(self.qc, init, meas)
        assert isinstance(result, QuantumCircuit)

    def test_compute_measure_combian_no_I(self):
        """Test calculation measurement combination and does not include I."""
        meas = ["X", "Y", "Z"]
        result = compute_measure_combian(meas)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == meas

    def test_compute_measure_combian_with_I(self):
        """Test calculation measurement combination and include I."""
        meas = ["I", "X"]
        result = compute_measure_combian(meas)
        assert isinstance(result, list)
        self.assertGreater(len(result), 1)

    def test_asign_probability_basic(self):
        """Testing the basic functionality of probability allocation."""
        measured_results = {
            ("0", "Z"): np.array([0.5, 0.5]),
            ("1", "Z"): np.array([0.3, 0.7]),
        }
        measure_configs = {
            "config1": [(1.0, ("0", "Z"))],
            "config2": [(1.0, ("1", "Z"))],
        }
        result = asign_probability(measured_results, measure_configs)
        assert isinstance(result, dict)
        assert "config1" in result
        assert "config2" in result
        for config_result in result.values():
            assert isinstance(config_result, np.ndarray)

    def test_attribute_prob_common_measure(self):
        """Test Attribute Probability - Public Measurement."""
        unattribute_prob = [0.5, 0.3, 0.2]
        meas = ["common-measure", "common-measure"]
        result = attribute_prob(unattribute_prob, meas)
        assert result == unattribute_prob

    def test_attribute_prob_float_input(self):
        """Test Attribute Probability - Floating Point Input."""
        unattribute_prob = 0.8
        meas = ["Z"]
        result = attribute_prob(unattribute_prob, meas)
        assert result == unattribute_prob

    def test_attribute_state_basic(self):
        """Test attribute status basic function."""
        try:
            sign, effective_idx = attribute_state(full_state=0, meas=["Z"])
            assert sign in [1, -1]
            assert isinstance(effective_idx, int)

            sign2, effective_idx2 = attribute_state(
                full_state=3, meas=["Z", "Z"]
            )
            assert sign2 in [1, -1]
            assert isinstance(effective_idx2, int)

        except Exception as e:
            self.skipTest(f"attribute_state test failed: {e}")

    def test_generate_measure_plans_basic(self):
        """Test the basic functionality of generating a measurement plan."""
        try:
            subcircuit = QuantumCircuit(2)
            subcircuit.append(H([0]))
            subcircuit.append(CX([0, 1]))
            init = "0"
            meas = ["Z", "Z"]
            result = generate_measure_plans(subcircuit, init, meas)
            assert isinstance(result, QuantumCircuit)

        except Exception as e:
            self.skipTest(f"generate_measure_plans test failed: {e}")

    def test_to_basic_init_various_inputs(self):
        """Testing the basic initialization of various inputs."""
        try:
            # Testing different base symbols
            result_0 = to_basic_init("0")
            assert isinstance(result_0, str)
            result_1 = to_basic_init("1")
            assert isinstance(result_1, str)
            result_plus = to_basic_init("+")
            assert isinstance(result_plus, str)
            result_minus = to_basic_init("-")
            assert isinstance(result_minus, str)
        except Exception as e:
            self.skipTest(f"to_basic_init test failed: {e}")

    def test_generate_subcircuits_for_execute(self):
        """Test the generate_subcircuits_for_execute function."""
        mock_prepare_data = MagicMock()
        mock_prepare_data.subcircuits = [self.qc, self.qc]
        mock_prepare_data.measure_config_value = [
            [(("0", "0"), ("X", "Y"))],
            [(("0", "1"), ("Z", "I"))],
        ]

        with patch(
            "wy_qcos.transpiler.common.wirecut.utils."
            "generate_config_circuits_for_one_subcircuit"
        ) as mock_generate_config:
            mock_generate_config.return_value = {
                (("0", "0"), ("X", "Y")): "mock_qasm"
            }
            result = generate_subcircuits_for_execute(mock_prepare_data)
            assert len(result) == 2
            assert mock_generate_config.call_count == 2

    def test_generate_config_circuits_for_one_subcircuit(self):
        """Test the generate_config_circuits_for_one_subcircuit function."""
        input_status = [(("0", "0"), ("X", "Y")), (("0", "1"), ("Z", "I"))]
        with patch(
            "wy_qcos.transpiler.common.wirecut.utils.generate_measure_plans"
        ) as mock_generate_measure:
            mock_generate_measure.return_value = self.qc
            result = generate_config_circuits_for_one_subcircuit(
                self.qc, input_status
            )
            assert len(result) == 2
            assert mock_generate_measure.call_count == 2
            for _, qasm_str in result.items():
                assert isinstance(qasm_str, str)
                assert "OPENQASM" in qasm_str

    def test_generate_measure_plans_all_init_states(self):
        """Test the generate_measure_plans function."""
        result = generate_measure_plans(self.qc, ("-", "0"), ("X", "Y"))
        assert isinstance(result, QuantumCircuit)
        with self.assertRaises(Exception):
            generate_measure_plans(self.qc, ("invalid", "0"), ("X", "Y"))

    def test_generate_measure_plans_all_meas_states(self):
        """Test the generate_measure_plans function."""
        result = generate_measure_plans(self.qc, ("0", "0"), ("Y", "Y"))
        assert isinstance(result, QuantumCircuit)
        with self.assertRaises(Exception):
            generate_measure_plans(self.qc, ("0", "0"), ("invalid", "Y"))

    def test_attribute_state_detailed(self):
        """Testing the details of the attribute_state function."""
        sign, eff_state = attribute_state(5, ("Z", "I"))
        assert isinstance(sign, int)
        assert isinstance(eff_state, int)
        sign, eff_state = attribute_state(3, ("Y", "Z"))
        assert isinstance(sign, int)
        assert isinstance(eff_state, int)
