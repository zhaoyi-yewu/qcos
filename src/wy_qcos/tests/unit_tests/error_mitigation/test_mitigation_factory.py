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

from wy_qcos.error_mitigation.mitigation_factory import MitigationFactory
from wy_qcos.error_mitigation.mitigation_base import MitigationBase
from wy_qcos.error_mitigation.readout_mitigation import ReadoutMitigation
from wy_qcos.error_mitigation.zne_mitigation import ZNEMitigation


class NotAMitigation:
    """Class that does not inherit from MitigationBase."""

    pass


class TestMitigationFactory:
    """Test MitigationFactory class."""

    def test_default_registry(self):
        factory = MitigationFactory()
        available = factory.list_available()
        assert "readout" in available
        assert "rem" in available
        assert "zne" in available

    def test_create_readout(self):
        factory = MitigationFactory()
        rem = factory.create("readout")
        assert isinstance(rem, ReadoutMitigation)

    def test_create_rem_alias(self):
        factory = MitigationFactory()
        rem = factory.create("rem")
        assert isinstance(rem, ReadoutMitigation)

    def test_create_zne(self):
        factory = MitigationFactory()
        zne = factory.create("zne")
        assert isinstance(zne, ZNEMitigation)

    def test_create_unknown_raises(self):
        factory = MitigationFactory()
        with pytest.raises(ValueError, match="Unknown mitigation"):
            factory.create("nonexistent")

    def test_create_with_kwargs(self):
        factory = MitigationFactory()
        rem = factory.create("readout", calibration_shots=4096)
        assert rem._calibration_shots == 4096

    def test_register_custom(self):
        factory = MitigationFactory()

        class CustomMitigation(MitigationBase):
            def __init__(self):
                super().__init__("custom")

            def postprocess(self, results, calibration=None, **kwargs):
                return {"results": results, "metadata": {}}

        factory.register("custom", CustomMitigation)
        assert "custom" in factory.list_available()
        instance = factory.create("custom")
        assert isinstance(instance, CustomMitigation)

    def test_register_invalid_raises(self):
        factory = MitigationFactory()
        with pytest.raises(TypeError, match="Invalid mitigation class"):
            factory.register("bad", NotAMitigation)
