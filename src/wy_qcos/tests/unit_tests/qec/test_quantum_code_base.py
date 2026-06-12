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

from wy_qcos.qec.quantum_code_base import QuantumCodeBase


class ConcreteQuantumCode(QuantumCodeBase):
    """Concrete implementation of QuantumCodeBase for testing."""

    def __init__(self):
        super().__init__(name="TestCode")

    def encode(self, circuit):
        return circuit

    def decode(self, circuit, **kwargs):
        return kwargs

    def correct(self, circuit, **kwargs):
        return kwargs

    def validate_and_format_circuit(self, circuit, num_qubits: int):
        return circuit

    def compute_samples(self, circuit, samples: list):
        return samples


class TestQuantumCodeBase:
    """Test QuantumCodeBase abstract base class."""

    def test_cannot_instantiate_abstract_class_directly(self):
        """Test that QuantumCodeBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            QuantumCodeBase()

    def test_concrete_subclass_instantiation(self):
        """Test that a concrete subclass can be instantiated."""
        code = ConcreteQuantumCode()
        assert isinstance(code, QuantumCodeBase)

    def test_encode_abstract_method(self):
        """Test that encode is abstract and must be implemented."""
        with pytest.raises(TypeError):

            class MissingEncode(QuantumCodeBase):
                def decode(self, circuit, **kwargs):
                    pass

                def correct(self, circuit, **kwargs):
                    pass

                def validate_and_format_circuit(
                    self, circuit, num_qubits: int
                ):
                    pass

                def compute_samples(self, circuit, samples: list):
                    pass

            MissingEncode()

    def test_decode_abstract_method(self):
        """Test that decode is abstract and must be implemented."""
        with pytest.raises(TypeError):

            class MissingDecode(QuantumCodeBase):
                def encode(self, circuit):
                    pass

                def correct(self, circuit, **kwargs):
                    pass

                def validate_and_format_circuit(
                    self, circuit, num_qubits: int
                ):
                    pass

                def compute_samples(self, circuit, samples: list):
                    pass

            MissingDecode()

    def test_correct_abstract_method(self):
        """Test that correct is abstract and must be implemented."""
        with pytest.raises(TypeError):

            class MissingCorrect(QuantumCodeBase):
                def encode(self, circuit):
                    pass

                def decode(self, circuit, **kwargs):
                    pass

                def validate_and_format_circuit(
                    self, circuit, num_qubits: int
                ):
                    pass

                def compute_samples(self, circuit, samples: list):
                    pass

            MissingCorrect()

    def test_validate_and_format_circuit_abstract_method(self):
        """Test that validate_and_format_circuit is abstract."""
        with pytest.raises(TypeError):

            class MissingValidate(QuantumCodeBase):
                def encode(self, circuit):
                    pass

                def decode(self, circuit, **kwargs):
                    pass

                def correct(self, circuit, **kwargs):
                    pass

                def compute_samples(self, circuit, samples: list):
                    pass

            MissingValidate()

    def test_compute_samples_abstract_method(self):
        """Test that compute_samples is abstract."""
        with pytest.raises(TypeError):

            class MissingCompute(QuantumCodeBase):
                def encode(self, circuit):
                    pass

                def decode(self, circuit, **kwargs):
                    pass

                def correct(self, circuit, **kwargs):
                    pass

                def validate_and_format_circuit(
                    self, circuit, num_qubits: int
                ):
                    pass

            MissingCompute()

    def test_encode_concrete(self):
        """Test encode in concrete class."""
        code = ConcreteQuantumCode()
        result = code.encode("test_circuit")
        assert result == "test_circuit"

    def test_decode_concrete(self):
        """Test decode in concrete class."""
        code = ConcreteQuantumCode()
        result = code.decode("test_circuit", extra_param="value")
        assert result == {"extra_param": "value"}

    def test_correct_concrete(self):
        """Test correct in concrete class."""
        code = ConcreteQuantumCode()
        result = code.correct("test_circuit", err_pos=[1])
        assert result == {"err_pos": [1]}

    def test_validate_and_format_circuit_concrete(self):
        """Test validate_and_format_circuit in concrete class."""
        code = ConcreteQuantumCode()
        circuit = code.validate_and_format_circuit("raw_circuit", num_qubits=1)
        assert circuit == "raw_circuit"

    def test_compute_samples_concrete(self):
        """Test compute_samples in concrete class."""
        code = ConcreteQuantumCode()
        samples = code.compute_samples("circuit", [0, 1, 0])
        assert samples == [0, 1, 0]
