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

import logging
import numpy as np
import stim
import pytest

from wy_qcos.qec.qec_factory import QecFactory
from schema import Optional as SchemaOptional

from wy_qcos.qec.shor_code import ShorCode, ShorStimStrategy


logger = logging.getLogger(__name__)


class TestQecFactory:
    """Test QecFactory creation, registration, and code listing."""

    @pytest.mark.smoke
    def test_create_default_shor_code(self):
        factory = QecFactory(None)
        code = factory.create("shor")
        assert isinstance(code, ShorCode)
        assert code.get_logical_bit_num() == 0
        assert code.get_physical_bit_num() == 0
        assert code.get_distance() == 1

    @pytest.mark.smoke
    def test_create_with_custom_registry(self):
        factory = QecFactory({"custom_shor": ShorCode})
        code = factory.create("custom_shor")
        assert isinstance(code, ShorCode)

    def test_create_unknown_code_raises_error(self):
        factory = QecFactory(None)
        with pytest.raises(
            ValueError, match="Unknown quantum error correction code"
        ):
            factory.create("nonexistent_code")

    def test_register_new_code(self):
        factory = QecFactory(None)
        factory.register("shor_v2", ShorCode)
        code = factory.create("shor_v2")
        assert isinstance(code, ShorCode)

    def test_register_invalid_code_class_raises_error(self):
        factory = QecFactory(None)
        with pytest.raises(TypeError, match="Code class invalid"):
            factory.register("invalid", dict)

    def test_unregister_code(self):
        factory = QecFactory(None)
        factory.register("temp_code", ShorCode)
        assert "temp_code" in factory.list_codes()
        factory.unregister("temp_code")
        assert "temp_code" not in factory.list_codes()

    def test_unregister_nonexistent_code_raises_error(self):
        factory = QecFactory(None)
        with pytest.raises(KeyError, match="'nonexistent' is not registered"):
            factory.unregister("nonexistent")

    def test_list_codes(self):
        factory = QecFactory(None)
        codes = factory.list_codes()
        assert "shor" in codes
        assert len(codes) == 1

    def test_get_registry(self):
        factory = QecFactory(None)
        registry = factory.get_registry()
        assert "shor" in registry
        assert registry["shor"] == ShorCode
        # Verify it's a copy (not the original)
        registry["custom"] = ShorCode
        assert "custom" not in factory.list_codes()

    def test_set_distance_physical_logical_params(self):
        factory = QecFactory(None)
        code = factory.create("shor")
        code.set_distance(3)
        code.set_physical_bit_num(9)
        code.set_logical_bit_num(1)
        assert code.get_distance() == 3
        assert code.get_physical_bit_num() == 9
        assert code.get_logical_bit_num() == 1


class TestShorStimStrategyValidate:
    """Test ShorStimStrategy circuit validation."""

    @pytest.mark.smoke
    def test_validate_single_qubit_gates(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        circuit.append("Z", [0])
        circuit.append("Y", [0])
        circuit.append("H", [0])
        circuit.append("S", [0])
        formatted = strategy.validate_and_format_circuit(circuit)
        assert isinstance(formatted, stim.Circuit)

    def test_validate_multi_qubit_gate_raises_error(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("CX", [0, 1])
        with pytest.raises(
            ValueError, match="Unexpected multi-qubit gate input"
        ):
            strategy.validate_and_format_circuit(circuit)


class TestShorStimStrategyEncode:
    """Test ShorStimStrategy encoding."""

    @pytest.mark.smoke
    def test_encode_logical_x_gate(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        # Encoded circuit should be larger than input
        assert len(encoded) > len(circuit)
        # Verify it compiles without error
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)
        assert samples.shape == (10, 18)

    def test_encode_logical_z_gate(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("Z", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)
        assert samples.shape == (10, 18)

    def test_encode_logical_y_gate(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("Y", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)
        assert samples.shape == (10, 18)

    def test_encode_logical_s_gate(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("S", [0])
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)
        assert samples.shape == (10, 18)

    def test_encode_logical_h_gate_raises_error(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("H", [0])
        with pytest.raises(
            ValueError, match="Logical H gate requires non-transversal"
        ):
            strategy.encode(circuit)

    def test_encode_empty_circuit(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        encoded = strategy.encode(circuit)
        assert isinstance(encoded, stim.Circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)
        assert samples.shape == (10, 18)


class TestShorStimStrategyCorrection:
    """Test ShorStimStrategy syndrome computation, decoding, and correction."""

    def _run_shor_pipeline(self, logical_gate_name: str = "X"):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append(logical_gate_name, [0])
        encoded = strategy.encode(circuit)

        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=100)

        strategy.compute_samples(samples)
        err_pos = strategy.decode()
        corrected_bits = strategy.correct(err_pos=err_pos)
        return strategy.logical_measure(corrected_bits)

    @pytest.mark.smoke
    def test_decode_syndrome_dimensions(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)

        strategy.compute_samples(samples)
        err_pos = strategy.decode()

        # 9 physical qubits => err_pos length should be 9
        assert err_pos.shape == (10, 9) or (
            len(err_pos) == 9 and samples.shape[0] == 10
        )

    def test_correct_bits_invalidates_errors(self):
        strategy = ShorStimStrategy()
        strategy.raw_bits = [0, 1, 0, 0, 1, 0, 0, 0, 0]
        err_pos = [0, 1, 0, 0, 1, 0, 0, 0, 0]
        corrected = strategy.correct(err_pos=err_pos)
        assert corrected[1] == 0  # was 1, flipped to 0
        assert corrected[4] == 0  # was 1, flipped to 0

    def test_correct_with_no_error(self):
        strategy = ShorStimStrategy()
        raw = [1, 0, 1, 0, 0, 1, 0, 1, 0]
        strategy.raw_bits = raw
        err_pos = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        corrected = strategy.correct(err_pos=err_pos)
        assert list(corrected) == raw

    def test_logical_measure_x_gate(self):
        logical_result = self._run_shor_pipeline("X")
        # Due to noise, some shots may be 0, but majority should be 1
        if isinstance(logical_result, np.ndarray):
            ones = np.sum(logical_result)
        else:
            ones = logical_result
        assert ones > 40  # at least 40% correct after noise correction

    def test_logical_measure_no_gate(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        encoded = strategy.encode(circuit)

        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=100)

        strategy.compute_samples(samples)
        err_pos = strategy.decode()
        corrected_bits = strategy.correct(err_pos=err_pos)
        logical_result = strategy.logical_measure(corrected_bits)

        if isinstance(logical_result, np.ndarray):
            zeros = np.sum(logical_result == 0)
        else:
            zeros = 1 if logical_result == 0 else 0
        assert zeros > 40

    def test_compute_samples_syndrome_shape(self):
        strategy = ShorStimStrategy()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = strategy.encode(circuit)
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=10)

        strategy.compute_samples(samples)
        # Syndrome: 6 Z-stabilizer + 3 X-stabilizer = 9
        assert np.array(strategy.syndrome).shape[-1] == 9
        # Raw bits: 9 physical qubits
        assert np.array(strategy.raw_bits).shape[-1] == 9


class TestShorCode:
    """Test ShorCode wrapper class."""

    def test_shor_code_name(self):
        code = ShorCode()
        assert code.get_distance() == 1
        assert code.get_physical_bit_num() == 0
        assert code.get_logical_bit_num() == 0

    @pytest.mark.smoke
    def test_shor_code_validate_1_qubit(self):
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        validated = code.validate_and_format_circuit(circuit, num_qubits=1)
        assert isinstance(validated, stim.Circuit)

    def test_shor_code_validate_invalid_num_qubits(self):
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        with pytest.raises(ValueError, match="Shor does not support"):
            code.validate_and_format_circuit(circuit, num_qubits=2)

    @pytest.mark.smoke
    def test_shor_code_encode_stim_circuit(self):
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])
        encoded = code.encode(circuit)
        assert isinstance(encoded, stim.Circuit)

    @pytest.mark.smoke
    def test_shor_code_full_pipeline(self):
        code = ShorCode()
        circuit = stim.Circuit()
        circuit.append("X", [0])

        # validate
        validated = code.validate_and_format_circuit(circuit, num_qubits=1)

        # encode
        encoded = code.encode(validated)

        # sample
        sampler = encoded.compile_sampler()
        samples = sampler.sample(shots=50)

        # compute samples
        code.compute_samples(validated, samples)

        # decode
        err_pos = code.decode(validated)

        # correct
        corrected_bits = code.correct(validated, err_pos=err_pos)

        # logical measure
        logical = code.logical_measure(validated, corrected_bits)
        assert logical is not None


class TestQecEdgeCases:
    """Test QEC edge cases and error handling."""

    def test_empty_qec_options_in_driver(self):
        from wy_qcos.driver.stim.driver_stim import DriverStim

        driver = DriverStim()
        with pytest.raises(ValueError, match="Qec_options are needed"):
            # Directly call run without qec_options
            driver.run(
                job_id="test",
                num_qubits=1,
                data={},
                data_type="",
                shots=1,
                qec_options=None,
            )

    def test_qec_options_schema(self):
        from wy_qcos.driver.stim.driver_stim import DriverStim

        driver = DriverStim()
        schema = driver.get_qec_options_schema()
        assert "qec_code" in schema
        assert schema["qec_code"] is str
        # Optional fields - they are wrapped with schema.Optional
        assert "qec_code" in schema
        assert schema["qec_code"] is str
        # Verify optional fields exist in schema
        schema_keys = list(schema.keys())
        schema_key_names = set()
        for k in schema_keys:
            if isinstance(k, SchemaOptional):
                schema_key_names.add(k._schema)
            elif isinstance(k, str):
                schema_key_names.add(k)
        assert "distance" in schema_key_names
        assert "phy_bit_num" in schema_key_names
        assert "logical_bit_num" in schema_key_names

    def test_factory_init_with_none(self):
        factory = QecFactory(None)
        codes = factory.list_codes()
        assert codes == ["shor"]

    def test_factory_init_with_empty_dict(self):
        factory = QecFactory({})
        codes = factory.list_codes()
        assert codes == []

    def test_stim_strategy_unsupported_gate(self):
        strategy = ShorStimStrategy()
        # Use "I" (identity) gate which Stim supports as single-qubit
        # but ShorStimStrategy.encode does not handle
        circuit = stim.Circuit()
        circuit.append("I", [0])
        with pytest.raises(ValueError, match="Unsupported logical gate"):
            strategy.encode(circuit)
