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


import copy


class EmptyRoute:
    def __init__(self):
        self.enable_mapping = False


def aggregate_empty_route_results(opt_result_dict):
    """Aggregate circuits for backends that do not need physical routing."""
    mapping_res = []
    mapping_dict = {}
    qubit_offset = 0

    for key, value in opt_result_dict.items():
        num_qubits, operations = value
        mapping_dict[key] = num_qubits
        for operation in operations:
            shifted_operation = copy.deepcopy(operation)
            if shifted_operation.targets is not None:
                shifted_operation.targets = [
                    target + qubit_offset
                    for target in shifted_operation.targets
                ]
            mapping_res.append(shifted_operation)
        qubit_offset += num_qubits

    return mapping_res, mapping_dict
