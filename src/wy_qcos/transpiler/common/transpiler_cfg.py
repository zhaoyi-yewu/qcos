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


class TranspilerCfg:
    """Transpiler Config Class."""

    def __init__(
        self,
        decomp_rule=None,
        qpu_cfg=None,
        max_qubits=0,
        tech_type=None,
        driver_name=None,
    ) -> None:
        self.decompose_rule = decomp_rule
        self.qpu_cfg = qpu_cfg
        self.max_qubits = max_qubits
        self.tech_type = tech_type
        self.driver_name = driver_name

    def get_decompose_rule(self):
        """Get decompose rule."""
        return self.decompose_rule

    def set_decompose_rule(self, decomp_rule):
        """Set decompose rule.

        Args:
          decomp_rule: decomposition rule
        """
        self.decompose_rule = decomp_rule

    def get_qpu_cfg(self):
        """Get qpu cfg."""
        return self.qpu_cfg

    def set_qpu_cfg(self, qpu_cfg):
        """Set qpu cfg.

        Args:
          qpu_cfg: qpu config
        """
        self.qpu_cfg = qpu_cfg

    def get_max_qubits(self):
        """Get max qubits.

        Returns:
            max qubits
        """
        return self.max_qubits

    def set_max_qubits(self, max_qubits):
        """Set qpu cfg.

        Args:
          max_qubits: max qubits
        """
        self.max_qubits = max_qubits

    def get_tech_type(self):
        """Get tech type.

        Returns:
            tech type
        """
        return self.tech_type

    def set_tech_type(self, tech_type):
        """Set tech type.

        Args:
          tech_type: tech type
        """
        self.tech_type = tech_type

    def get_driver_name(self):
        """Get driver name.

        Returns:
            driver name
        """
        return self.driver_name

    def set_driver_name(self, driver_name):
        """Set driver name.

        Args:
          driver_name: driver name
        """
        self.driver_name = driver_name


trans_cfg_inst = TranspilerCfg()
