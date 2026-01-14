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

import numpy as np

from fractions import Fraction
from functools import reduce
from loguru import logger
from math import gcd

from wy_qcos.engine.qubo.tabu import QUBOSolution


def find_matrix_gcd(matrix):
    """Find the greatest common divisor (GCD) of all non-zero elements.

    Args:
        matrix: a 2D numpy array
    Returns:
        the GCD of all non-zero elements in the matrix
    """
    flat_values = np.array(matrix).flatten().astype(int)
    flat_values = np.abs(flat_values[flat_values != 0])
    if len(flat_values) == 0:
        return 0
    return reduce(gcd, flat_values)


def scale_to_integer_matrix(matrix):
    """Scale matrix to interger matrix.

    Args:
        matrix: a 2D numpy array
    Returns:
        a scaled integer matrix.
    """
    arr = np.array(matrix, dtype=float)
    flat_arr = arr.flatten()
    # find the least common denominator of all non-zero elements
    denominators = []
    for val in flat_arr:
        if val != 0:
            # convert floating numbers to fractional form
            frac = Fraction(val).limit_denominator(1000000)
            denominators.append(frac.denominator)
    if not denominators:
        return arr.astype(int)

    # calculate the least common multiple (LCM) of all denominators
    def lcm(a, b):
        return a * b // gcd(a, b)

    scale_factor = reduce(lcm, denominators)
    # apply scaling and convert to integers
    scaled_matrix = (arr * scale_factor).round().astype(int)

    # find gcd of scaled matrix
    gcd_value = find_matrix_gcd(scaled_matrix)

    # scale back to original scale
    scaled_ising_matrix = scaled_matrix // gcd_value
    return scaled_ising_matrix


def check_matrix(matrix):
    """Check matrix is square array or not.

    Check if the input 2D list is a square array (i.e., the number
    of rows and columns are equal).

    Args:
        matrix: list(list())

    Returns:
        bool: True if valid, False otherwise
        error_msg: str
    """
    if not matrix:
        return False, "Input cannot be an empty list"
    try:
        matrix = np.array(matrix)
    except Exception as e:
        return False, f"Abnormal matrix: {str(e)}"
    matrix_shape = matrix.shape
    if matrix_shape[0] != matrix_shape[1]:
        return False, "Input matrix is not square"
    return True, None


def check_qubo_matrix_bit_width(qubo_matrix, param_bit):
    """Check qubo matrix bit width.

    Args:
        qubo_matrix(np.ndarray): qubo matrix to be checked
        param_bit(int): param bit width
    Returns:
        success of failed (bool), error message list.
    """
    success = True
    err_msgs = []

    try:
        # 1. change qubo matrix to ising matrix
        ising_matrix = qubo_matrix_to_ising_matrix(qubo_matrix)
        # 2. scale the ising matrix and check bit width
        bit_width = param_bit - 1
        if not np.any(ising_matrix):
            return np.inf, np.inf
        abs_matrix = np.abs(ising_matrix)
        threshold = 1e-10
        non_zero_elements = abs_matrix[
            np.where(np.abs(abs_matrix) > threshold)
        ]
        normalization_factor = np.min(non_zero_elements)
        normalized_matrix = ising_matrix / normalization_factor
        abs_normalized_matrix = np.abs(normalized_matrix)
        scaling_factor_upper_limit = (
            int(np.floor(2**bit_width / abs_normalized_matrix.max())) + 1
        )
        precision = np.inf
        for i in range(1, scaling_factor_upper_limit):
            scaled_normalized_matrix = ising_matrix * i / normalization_factor
            if np.array_equal(
                np.around(scaled_normalized_matrix, decimals=0),
                np.around(scaled_normalized_matrix, decimals=8),
            ):
                for j in range(1, bit_width + 1):
                    upper_bound = 2**j
                    if (
                        np.around(scaled_normalized_matrix.max())
                        == upper_bound
                    ):
                        continue
                    if (
                        i
                        < int(
                            np.floor(upper_bound / abs_normalized_matrix.max())
                        )
                        + 1
                    ):
                        precision = j + 1
        if precision > param_bit:
            success = False
            logger.warning(
                f"The element values in the QUBO matrix "
                f"does not meet {param_bit}-bit signed."
            )
    except Exception as e:
        success = False
        error = str(e)
        err_msg = f"Check qubo bit width fail: {error}"
        return success, [err_msg]
    return success, err_msgs


def qubo_matrix_to_ising_matrix(qubo_matrix):
    """Convert QUBO matrix to ising matrix.

    tip: Ising matrix is added a variable to the diagonal.

    Args:
        qubo_matrix (np.ndarray): qubo matrix

    Returns:
        np.ndarray: ising matrix
    """
    n = qubo_matrix.shape[0]
    ising_matrix = np.zeros((n + 1, n + 1))
    ising_h = np.zeros(n)
    for i in range(n):
        sum_row = qubo_matrix[i, i]
        for j in range(n):
            if j != i:
                sum_row += qubo_matrix[i][j]
        ising_h[i] = -0.25 * sum_row
        for j in range(i + 1, n):
            ising_matrix[i, j] = -0.25 * qubo_matrix[i][j]
            ising_matrix[j, i] = ising_matrix[i][j]
    ising_matrix[:n, n] = ising_h
    ising_matrix[n, :n] = ising_h
    return ising_matrix


def ising_matrix_to_qubo_matrix(ising_matrix):
    """Convert ising matrix to QUBO matrix.

    Args:
        ising_matrix (np.ndarray): ising matrix

    Returns:
        np.ndarray: QUBO matrix
    """
    n = ising_matrix.shape[0] - 1
    J_matrix = ising_matrix[:n, :n].copy()
    h_vector = ising_matrix[:n, n]
    # Building the QUBO matrix
    qubo_matrix = np.zeros((n, n))
    # Reconstructing the off-diagonal elements of the QUBO matrix
    for i in range(n):
        for j in range(i + 1, n):
            qubo_matrix[i, j] = -4 * J_matrix[i, j]
            qubo_matrix[j, i] = qubo_matrix[i, j]
    # Reconstruct the diagonal elements of the QUBO matrix
    for i in range(n):
        sum_off_diag = 0
        for j in range(n):
            if j != i:
                sum_off_diag += qubo_matrix[i, j]
        qubo_matrix[i, i] = -4 * h_vector[i] - sum_off_diag
    return qubo_matrix


def get_spins_num(mat, max_value):
    """Get the number of spin variables.

    Obtain the number of spin variables after the matrix
    is reduced in precision.

    Args:
        mat(np.ndarray): upper triangular matrix
        max_value (int): max value of the matrix

    Returns:
        list: spin variables list
    """
    n = mat.shape[0]
    spin_variables_list = [None] * n
    indices = []
    values = []
    # Traverse the upper triangular part (i < j)
    for i in range(n):
        for j in range(i + 1, n):
            indices.append((i, j))
            values.append(abs(mat[i, j]))
    # Sort the values and indices together
    # in descending order of absolute value
    indexed_values = list(zip(values, indices))
    indexed_values.sort(key=lambda item: abs(item[0]), reverse=True)
    # Process each element in descending order of absolute value
    for value, (i, j) in indexed_values:
        # Check if both index positions are empty
        if spin_variables_list[i] is None and spin_variables_list[j] is None:
            spin_variables_list[i] = max(
                int(np.ceil(np.sqrt(value / max_value))), 1
            )
            spin_variables_list[j] = max(
                int(np.ceil(np.sqrt(value / max_value))), 1
            )
        elif spin_variables_list[i] is None:
            spin_variables_list[i] = max(
                int(np.ceil(value / (spin_variables_list[j] * max_value))), 1
            )
        elif spin_variables_list[j] is None:
            spin_variables_list[j] = max(
                int(np.ceil(value / (spin_variables_list[i] * max_value))), 1
            )

    current_sum = 0
    last_idx = [0]
    for num in spin_variables_list:
        current_sum += num
        last_idx.append(current_sum)
    total_spins_num = sum(spin_variables_list)
    return spin_variables_list, last_idx, total_spins_num


def precision_reduction(ising_matrix, param_bit):
    """Precision reduction algorithm.

    Args:
        ising_matrix (np.ndarray): ising matrix
        param_bit (int): Parameters indicating matrix accuracy

    Returns:
        tuple:
            np.ndarray: new ising matrix
            list: last index
            int: total_spins_num
    """
    max_value = 2 ** (param_bit - 1) - 1
    # 1 scale to integer matrix
    scaled_ising_matrix = scale_to_integer_matrix(ising_matrix)
    # 2 get upper triangle matrix
    upper_triangular_matrix = np.triu(scaled_ising_matrix)
    # 3 determine the required number of spin variables
    spins_num_list, last_idx, total_spins_num = get_spins_num(
        scaled_ising_matrix, max_value
    )
    # 4 construct the new precision reduction matrix
    new_ising_matrix = np.zeros((total_spins_num, total_spins_num))
    n = len(upper_triangular_matrix)
    for i in range(n):
        for j in range(i, n):
            number = upper_triangular_matrix[i, j]
            average = 0
            if number >= 0:
                average = np.ceil(
                    number / (spins_num_list[i] * spins_num_list[j])
                )
            else:
                average = np.floor(
                    number / (spins_num_list[i] * spins_num_list[j])
                )
            for m in range(spins_num_list[i]):
                for k in range(spins_num_list[j]):
                    x = last_idx[i] + m
                    y = last_idx[j] + k
                    if i == j and y > x:
                        new_ising_matrix[x, y] = max_value
                        new_ising_matrix[y, x] = max_value
                    elif i != j:
                        sign = 1 if number >= 0 else -1
                        if sign * number <= sign * average:
                            new_ising_matrix[x, y] = number
                            new_ising_matrix[y, x] = number
                            number = 0
                        else:
                            new_ising_matrix[x, y] = average
                            new_ising_matrix[y, x] = average
                            number -= average
    return new_ising_matrix, last_idx[:-1], total_spins_num


def process_qubo_solution(job_results, last_idx, qubo_matrix):
    """Process qubo solution.

    Args:
        job_results (dict): job_results returned by the driver
        last_idx (list): last index returned by precsion reduction
        qubo_matrix (np.array): QUBO matrix

    Returns:
        dict: new job_results
    """
    new_job_results = job_results.copy()
    qubo_solution = job_results["results"]["out_data"]
    for i in range(len(qubo_solution)):
        solution = qubo_solution[i]
        solutionvector = solution["solutionVector"]
        flag = solutionvector[last_idx[-1]]
        solution_vector = [solutionvector[i] for i in last_idx[:-1]]
        solution_vector = np.array(solution_vector) ^ (1 - flag)
        qubo_value = QUBOSolution.calculate_energy(
            qubo=qubo_matrix, solution=solution_vector
        )
        new_job_results["results"]["out_data"][i]["quboValue"] = qubo_value
        new_job_results["results"]["out_data"][i]["solutionVector"] = (
            solution_vector.tolist()
        )
    new_job_results["results"]["out_data"] = sorted(
        new_job_results["results"]["out_data"], key=lambda x: x["quboValue"]
    )
    return new_job_results
