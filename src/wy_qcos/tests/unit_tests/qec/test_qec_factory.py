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

from wy_qcos.qec.qec_factory import QecFactory
from wy_qcos.qec.quantum_code_base import QuantumCodeBase
from wy_qcos.qec.shor_code import ShorCode


class MockCode(QuantumCodeBase):
    """Mock code for testing."""

    def __init__(self):
        super().__init__(name="MockCode")

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


class NotACode:
    """Class that does not inherit from QuantumCodeBase."""

    pass


class TestQecFactory:
    """Test QecFactory class."""

    def test_default_initialization(self):
        """Test factory initialization with default codes."""
        factory = QecFactory(code_dict=None)
        assert "shor" in factory.list_codes()
        assert factory.list_codes() == ["shor"]

    def test_custom_code_dict_initialization(self):
        """Test factory initialization with custom code dictionary."""
        code_dict = {"mock": MockCode, "shor": ShorCode}
        factory = QecFactory(code_dict=code_dict)
        codes = factory.list_codes()
        assert "mock" in codes
        assert "shor" in codes
        assert len(codes) == 2

    def test_custom_code_dict_independence(self):
        """Test that factory uses a copy of the code_dict."""
        code_dict = {"mock": MockCode}
        factory = QecFactory(code_dict=code_dict)
        code_dict["extra"] = ShorCode
        assert "extra" not in factory.list_codes()

    def test_default_initialization_shor_code(self):
        """Test that default factory can create ShorCode."""
        factory = QecFactory(code_dict=None)
        code = factory.create("shor")
        assert isinstance(code, ShorCode)
        assert code._name == "ShorCode"

    def test_create_with_custom_code(self):
        """Test creating a custom registered code."""
        factory = QecFactory(code_dict=None)
        factory.register("mock", MockCode)
        code = factory.create("mock")
        assert isinstance(code, MockCode)

    def test_create_unknown_code_raises_value_error(self):
        """Test that creating an unknown code raises ValueError."""
        factory = QecFactory(code_dict=None)
        with pytest.raises(ValueError) as exc_info:
            factory.create("unknown_code")
        assert "unknown_code" in str(exc_info.value)
        assert "Available codes" in str(exc_info.value)

    def test_create_unknown_code_lists_available_codes(self):
        """Test that error message lists available codes."""
        factory = QecFactory(code_dict=None)
        factory.register("mock", MockCode)
        with pytest.raises(ValueError) as exc_info:
            factory.create("nonexistent")
        assert "mock" in str(exc_info.value)

    def test_register_valid_code(self):
        """Test registering a valid code class."""
        factory = QecFactory(code_dict=None)
        factory.register("mock", MockCode)
        assert "mock" in factory.list_codes()

    def test_register_invalid_code_raises_type_error(self):
        """Test that registering a non-subclass raises TypeError."""
        factory = QecFactory(code_dict=None)
        with pytest.raises(TypeError) as exc_info:
            factory.register("invalid", NotACode)
        assert "Code class invalid" in str(exc_info.value)

    def test_register_overwrite_existing(self):
        """Test that registering overwrites an existing entry."""
        factory = QecFactory(code_dict=None)

        class MockCodeV1(MockCode):
            pass

        class MockCodeV2(MockCode):
            pass

        factory.register("mock", MockCodeV1)
        factory.register("mock", MockCodeV2)
        code = factory.create("mock")
        assert isinstance(code, MockCodeV2)

    def test_unregister_existing_code(self):
        """Test unregistering an existing code."""
        factory = QecFactory(code_dict=None)
        factory.register("mock", MockCode)
        assert "mock" in factory.list_codes()
        factory.unregister("mock")
        assert "mock" not in factory.list_codes()

    def test_unregister_nonexistent_code_raises_key_error(self):
        """Test that unregistering a non-registered code raises KeyError."""
        factory = QecFactory(code_dict=None)
        with pytest.raises(KeyError) as exc_info:
            factory.unregister("nonexistent")
        assert "nonexistent" in str(exc_info.value)

    def test_unregister_default_code(self):
        """Test unregistering a default code."""
        factory = QecFactory(code_dict=None)
        assert "shor" in factory.list_codes()
        factory.unregister("shor")
        assert "shor" not in factory.list_codes()

    def test_list_codes_returns_list(self):
        """Test that list_codes returns a list."""
        factory = QecFactory(code_dict=None)
        codes = factory.list_codes()
        assert isinstance(codes, list)

    def test_list_codes_multiple_codes(self):
        """Test listing multiple registered codes."""
        factory = QecFactory(code_dict=None)

        class CodeA(MockCode):
            pass

        class CodeB(MockCode):
            pass

        factory.register("code_a", CodeA)
        factory.register("code_b", CodeB)
        codes = factory.list_codes()
        assert len(codes) >= 2
        assert "shor" in codes
        assert "code_a" in codes
        assert "code_b" in codes

    def test_get_registry_returns_dict(self):
        """Test that get_registry returns a dictionary."""
        factory = QecFactory(code_dict=None)
        registry = factory.get_registry()
        assert isinstance(registry, dict)

    def test_get_registry_contains_correct_types(self):
        """Test that get_registry contains the correct types."""
        factory = QecFactory(code_dict=None)
        registry = factory.get_registry()
        assert "shor" in registry
        assert registry["shor"] == ShorCode

    def test_get_registry_is_copy(self):
        """Test that get_registry returns a copy (not a reference)."""
        factory = QecFactory(code_dict=None)
        registry = factory.get_registry()
        registry["mock"] = MockCode
        assert "mock" not in factory.list_codes()

    def test_create_returns_quantum_code_base_instance(self):
        """Test that create returns a QuantumCodeBase instance."""
        factory = QecFactory(code_dict=None)
        code = factory.create("shor")
        assert isinstance(code, QuantumCodeBase)

    def test_registry_after_multiple_unregister(self):
        """Test registry state after multiple operations."""
        factory = QecFactory(code_dict=None)

        class CodeA(MockCode):
            pass

        factory.register("code_a", CodeA)
        factory.unregister("shor")
        factory.register("code_b", MockCode)
        codes = factory.list_codes()
        assert "shor" not in codes
        assert "code_a" in codes
        assert "code_b" in codes

    def test_create_after_re_register(self):
        """Test creating after re-registering a code."""
        factory = QecFactory(code_dict=None)

        class CustomShor(ShorCode):
            pass

        factory.unregister("shor")
        factory.register("shor", CustomShor)
        code = factory.create("shor")
        assert isinstance(code, CustomShor)

    def test_empty_factory_initialization(self):
        """Test factory initialized with empty dict."""
        factory = QecFactory(code_dict={})
        assert factory.list_codes() == []

    def test_create_on_empty_factory_raises_error(self):
        """Test creating on empty factory raises ValueError."""
        factory = QecFactory(code_dict={})
        with pytest.raises(ValueError):
            factory.create("shor")