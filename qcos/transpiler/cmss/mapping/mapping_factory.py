#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from qcos.common.constant import Constant
from qcos.transpiler.cmss.mapping import NASingleRoute, NARoute
from qcos.transpiler.cmss.mapping import SCRoute
from qcos.transpiler.common.errors import MappingException


class MappingFactory:
    """Get Transpiler via Type."""

    def __init__(self):
        self._mapping = {
            Constant.TECH_TYPE_NEUTRAL_ATOM: NASingleRoute(),
            Constant.TECH_TYPE_SUPERCONDUCTING: SCRoute(),
        }

    def get_mapper_by_type(self, tech_type: str, na_support_move: bool):
        """Get mapper by type.

        Args:
          tech_type (str): tech type
          na_support_move(bool): Does NA support move and cz gate
        Returns:
            mapper
        """
        # support two-qubit_gate mapping for NA
        if tech_type == Constant.TECH_TYPE_NEUTRAL_ATOM and na_support_move:
            return NARoute()

        mapper = self._mapping.get(tech_type)
        if mapper:
            return mapper
        else:
            raise MappingException(f"tech_type: {tech_type} is invalid")
