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

from .subqubo import SubQUBOMultiSolution
from .tabu import QUBOSolution, TabuSearch
from .qubo_precision import (
    find_matrix_gcd,
    scale_to_integer_matrix,
    check_matrix,
    check_qubo_matrix_bit_width,
    qubo_matrix_to_ising_matrix,
    ising_matrix_to_qubo_matrix,
    get_spins_num,
    precision_reduction,
    process_qubo_solution,
)

subqubo = SubQUBOMultiSolution()
