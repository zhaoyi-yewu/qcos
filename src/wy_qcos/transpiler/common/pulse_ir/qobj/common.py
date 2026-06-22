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

"""Module providing definitions of common Qobj classes."""

from types import SimpleNamespace

from wy_qcos.transpiler.common.pulse_ir.utils import deprecate_func


QOBJ_DEPRECATION_MSG = (
    "The `Qobj` class and related functionality are part of the deprecated "
    "`BackendV1` workflow, and no longer necessary for `BackendV2`. If a "
    "user workflow requires `Qobj` it likely relies on deprecated "
    "functionality and should be updated to use `BackendV2`."
)


class QobjDictField(SimpleNamespace):
    """A class used to represent a dictionary field in Qobj.

    Exists as a backwards compatibility shim around a dictionary for Qobjs
    previously constructed using marshmallow.
    """

    @deprecate_func(
        since="1.2",
        removal_timeline="in the 2.0 release",
        additional_msg=QOBJ_DEPRECATION_MSG,
    )
    def __init__(self, **kwargs):
        """Instantiate a new Qobj dict field object.

        Args:
            kwargs: arbitrary keyword arguments that can be accessed as
                attributes of the object.
        """
        self.__dict__.update(kwargs)

    def to_dict(self):
        """Return a dictionary format representation of the OpenQASM 2 Qobj.

        Returns:
            dict: The dictionary form of the QobjHeader.
        """
        return self.__dict__

    @classmethod
    def from_dict(cls, data):
        """Create a new QobjHeader object from a dictionary.

        Args:
            data (dict): A dictionary representing the QobjHeader to create. It
                will be in the same format as output by :func:`to_dict`.

        Returns:
            QobjDictFieldr: The QobjDictField from the input dictionary.
        """
        return cls(**data)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            if self.__dict__ == other.__dict__:
                return True
        return False


class QobjHeader(QobjDictField):
    """A class used to represent a dictionary header in Qobj objects."""

    pass


class QobjExperimentHeader(QobjHeader):
    """A class representing a header dictionary for a Qobj Experiment."""

    pass
