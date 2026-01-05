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

import random

from schema import Optional

from wy_qcos.common.constant import Constant
from wy_qcos.drivers.driver_base import DriverBase


class DriverQuboBase(DriverBase):
    """QUBO驱动基类.

    QUBO Base driver
    """

    def __init__(self):
        super().__init__()
        self.enable_transpiler = False
        self.tech_type = Constant.TECH_TYPE_PHOTON
        self.default_data_type = DriverBase.DATA_TYPE_QUBO
        self.supported_code_types = [Constant.CODE_TYPE_QUBO]
        self.driver_options = {
            "enable_subqubo": False,
            "enable_prec_reduce": False,
        }
        self.driver_options_schema = {
            Optional("enable_subqubo"): bool,
            Optional("enable_prec_reduce"): bool,
        }

    def get_fake_results(self, num_qubits, shots, data):
        """Get fake results.

        Args:
            num_qubits: number of qubits
            shots: number of shots
            data: source data
        """
        results = []
        for i in range(10):  # return 10 best solutions is enough
            code_length = len(data.get("source_code", [])[0])
            result = {
                "result": i + 1,
                "quboValue": -112,
                "maxcutValue": 28.0,
                "solutionVector": [
                    random.randint(0, 1) for _ in range(code_length)
                ],
            }
            results.append(result)
        return results

    def get_enable_subqubo(self):
        """Get enable subqubo.

        Returns:
            bool: enable subqubo
        """
        return self.driver_options["enable_subqubo"]

    def get_enable_prec_reduce(self):
        """Get enable precision reduction.

        Returns:
            bool: enable precision reduction
        """
        return self.driver_options["enable_prec_reduce"]
