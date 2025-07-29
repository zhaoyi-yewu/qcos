#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
    """
    Transpiler Base Class.
    All Transpiler classes are inherited from this class.
    """

    def __init__(self):
        # name
        self.name = None
        # module name
        self._module_name = None
        # class name
        self._class_name = None
        # enable this transpiler or not
        self.enable = True
        # num qubits
        self.num_qubits = -1
        # supported code types
        self.supported_code_types = []
        # transpiler_options
        self.transpiler_options = {}
        # transpiler_options schema
        self.transpiler_options_schema = None
        # qpu_config
        self.qpu_config = None

    def init_transpiler(self):
        """
        Init transpiler
        """
        raise NotImplementedError(f"Transpiler: {self.__class__.__name__} "
                                  f"must implement method: init_transpiler")

    def update_transpiler_options(self, transpiler_options):
        """
        Update transpiler options

        :param transpiler_options: new transpiler options
        """
        self.transpiler_options.update(transpiler_options)

    def get_transpiler_options(self):
        """
        Show transpiler options
        """
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
        """
        Set transpiler name

        :param name: transpiler_name
        """
        self.name = name

    def get_name(self):
        """
        Get transpiler name

        :return: transpiler name
        """
        return self.name

    def set_module_name(self, module_name):
        """
        Set module name

        :param module_name: module name
        """
        self._module_name = module_name

    def get_module_name(self):
        """
        Get module name

        :return: module name
        """
        return self._module_name

    def set_class_name(self, class_name):
        """
        Set class name

        :param class_name: class name
        """
        self._class_name = class_name

    def get_class_name(self):
        """
        Get class name

        :return: class name
        """
        return self._class_name

    def get_supported_code_types(self):
        """
        Get supported code types

        :return: supported code types
        """
        return self.supported_code_types

    def parse(self, codes: str):
        """
        parse source codes

        :param codes: source codes
        :return parse result
        """
        raise NotImplementedError(f"Transpiler: {self.__class__.__name__} "
                                  f"must implement method: parse")

    def transpile(self, parse_result, supp_basis_gates: list):
        """
        Transpile codes

        :param parse_result: parse result
        :param supp_basis_gates: supported basis gates
        :return basis gate list
        """
        raise NotImplementedError(f"Transpiler: {self.__class__.__name__} "
                                  f"must implement method: transpile")
