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

"""Unit tests for MitigationBase default method behaviour."""

import pytest

from wy_qcos.error_mitigation.mitigation_base import MitigationBase


class _ConcreteMitigation(MitigationBase):
    """Minimal concrete subclass for testing default behaviours."""

    def postprocess(self, results, calibration=None, **kwargs):
        return {"results": results, "metadata": {}}


class TestMitigationBaseDefaults:
    """Cover the default method implementations."""

    def test_init_defaults(self):
        m = _ConcreteMitigation("test")
        assert m.name == "test"
        assert m.enabled is False
        assert m._config == {}

    def test_set_config_enables(self):
        m = _ConcreteMitigation("test")
        m.set_config({"enabled": True, "foo": "bar"})
        assert m.enabled is True
        assert m._config["foo"] == "bar"

    def test_set_config_disabled_by_default(self):
        m = _ConcreteMitigation("test")
        m.set_config({"foo": "bar"})  # no "enabled" key
        assert m.enabled is False

    def test_get_config_returns_copy(self):
        m = _ConcreteMitigation("test")
        m.set_config({"enabled": True, "key": 1})
        cfg = m.get_config()
        cfg["key"] = 999  # mutate the copy
        assert m._config["key"] == 1  # original untouched

    def test_needs_calibration_default_false(self):
        m = _ConcreteMitigation("test")
        assert m.needs_calibration() is False

    def test_calibrate_returns_empty_dict(self):
        m = _ConcreteMitigation("test")
        result = m.calibrate(None, "device-0", [0, 1])
        assert result == {}

    def test_transform_circuit_default_returns_original(self):
        m = _ConcreteMitigation("test")
        sentinel = object()
        variants = m.transform_circuit(sentinel)
        assert len(variants) == 1
        assert variants[0]["label"] == "original"
        assert variants[0]["circuit"] is sentinel
        assert variants[0]["scale_factor"] == 1

    def test_validate_device_default_valid(self):
        m = _ConcreteMitigation("test")
        valid, msg = m.validate_device({"basis_gates": ["cz"]})
        assert valid is True
        assert msg is None

    def test_postprocess_not_implemented_on_abstract(self):
        # MitigationBase is abstract (postprocess is abstractmethod): a
        # subclass that doesn't override it cannot be instantiated.
        class Incomplete(MitigationBase):
            pass

        with pytest.raises(TypeError):
            Incomplete("test")  # can't instantiate abstract class

    def test_postprocess_raises_not_implemented_via_super(self):
        # Calling the abstract postprocess directly (via __init_subclass__
        # bypass) is not possible since the class is abstract; instead verify
        # that the base raise statement exists by checking the method body is
        # the documented behaviour via a near-complete subclass.
        class Almost(MitigationBase):
            def postprocess(self, results, calibration=None, **kwargs):
                # invoke the parent's NotImplementedError path
                return super().postprocess(results, calibration, **kwargs)

        m = Almost("test")
        with pytest.raises(NotImplementedError, match="must be implemented"):
            m.postprocess({"original": {"0": 1}})
