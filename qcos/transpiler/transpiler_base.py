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


class TranspilerBase:
    """Transpiler Base Class.

    All Transpiler classes are inherited from this class.
    """

    def __init__(self):
        # name
        self.name = None
        # alias name
        self.alias_name = None
        # version
        self.version = None
        # module name
        self._module_name = None
        # class name
        self._class_name = None
        # enable this transpiler or not
        self.enable = True
        # total num of qubits
        self.total_qubits = -1
        # supported code types
        self.supported_code_types = []
        # transpiler_options
        self.transpiler_options = {}
        # transpiler_options schema
        self.transpiler_options_schema = None
        # qpu_config
        self.qpu_config = None

    def init_transpiler(self):
        """Init transpiler."""
        raise NotImplementedError(
            f"Transpiler: {self.__class__.__name__} "
            f"must implement method: init_transpiler"
        )

    def get_transpiler_options_schema(self):
        """Get transpiler options schema.

        Returns:
            transpiler options schema
        """
        return self.transpiler_options_schema

    def update_transpiler_options(self, transpiler_options):
        """Update transpiler options.

        Args:
            transpiler_options: new transpiler options
        """
        self.transpiler_options.update(transpiler_options)

    def get_transpiler_options(self):
        """Get transpiler options.

        Returns:
            transpiler options
        """
        return self.transpiler_options

    def get_transpiler_info(self):
        """Get transpiler info."""
        show_list = [
            f"[{self.__class__.__name__}]",
            f"transpiler_name: {self.name}",
            f"enable: {self.enable}",
            f"transpiler_options: {self.transpiler_options}",
            # f"qpu_configs: {self.qpu_configs}",
            # f"decomposition_rule: {self.decomposition_rule}",
        ]
        return "\n".join(show_list)

    def set_name(self, name):
        """Set transpiler name.

        Args:
            name: transpiler_name
        """
        self.name = name

    def get_name(self):
        """Get transpiler name.

        Returns:
            transpiler name
        """
        return self.name

    def get_alias_name(self):
        """Get transpiler alias name.

        Returns:
            transpiler alias name
        """
        return self.alias_name

    def get_version(self):
        """Get version.

        Returns:
            version
        """
        return self.version

    def set_module_name(self, module_name):
        """Set module name.

        Args:
            module_name: module name
        """
        self._module_name = module_name

    def get_module_name(self):
        """Get module name.

        Returns:
            module name
        """
        return self._module_name

    def set_class_name(self, class_name):
        """Set class name.

        Args:
            class_name: class name
        """
        self._class_name = class_name

    def get_class_name(self):
        """Get class name.

        Returns:
            class name
        """
        return self._class_name

    def get_supported_code_types(self):
        """Get supported code types.

        Returns:
            supported code types
        """
        return self.supported_code_types

    def parse(self, src_code_dict):
        """Parse src code dict.

        Args:
            src_code_dict: src code dict

        Returns:
            parse result
        """
        raise NotImplementedError(
            f"Transpiler: {self.__class__.__name__} "
            f"must implement method: parse"
        )

    def transpile(self, parse_result, supp_basis_gates: list):
        """Transpile codes.

        Args:
            parse_result: parse result
            supp_basis_gates: supported basis gates

        Returns:
            basis gate list
        """
        raise NotImplementedError(
            f"Transpiler: {self.__class__.__name__} "
            "must implement method: transpile"
        )
