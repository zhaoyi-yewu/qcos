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

import numpy as np
from unittest.mock import patch

from qcos.engine.qubo.qubo_precision import (
    find_matrix_gcd,
    scale_to_integer_matrix,
    is_int_matrix,
    check_qubo_matrix_bit_width,
    qubo_matrix_to_ising_matrix,
    ising_matrix_to_qubo_matrix,
    get_spins_num,
    precision_reduction,
    process_qubo_solution,
)


class TestQUBOPrecision:
    """Unit testing for qubo precision"""

    def test_find_matrix_gcd(self):
        """Test finding GCD of matrix elements"""
        # Test with positive integers
        matrix1 = np.array([[2, 4, 6], [8, 10, 12]])
        assert find_matrix_gcd(matrix1) == 2

        # Test with mixed values including zeros
        matrix2 = np.array([[0, 3, 0], [6, 9, 0]])
        assert find_matrix_gcd(matrix2) == 3

        # Test with all zeros
        matrix3 = np.array([[0, 0], [0, 0]])
        assert find_matrix_gcd(matrix3) == 0

        # Test with negative values
        matrix4 = np.array([[-4, 8], [12, -16]])
        assert find_matrix_gcd(matrix4) == 4

    def test_scale_to_integer_matrix(self):
        """Test scaling matrix to integer matrix"""
        # Test with integer matrix
        int_matrix = np.array([[1, 2], [3, 4]])
        scaled = scale_to_integer_matrix(int_matrix)
        assert np.array_equal(scaled, int_matrix)

        # Test with fractional matrix
        frac_matrix = np.array([[0.5, 0.25], [0.125, 1.0]])
        scaled = scale_to_integer_matrix(frac_matrix)
        expected = np.array([[4, 2], [1, 8]])  # After scaling by 8
        assert np.array_equal(scaled, expected)

        # Test with zero matrix
        zero_matrix = np.zeros((2, 2))
        scaled = scale_to_integer_matrix(zero_matrix)
        assert np.array_equal(scaled, zero_matrix)

    def test_is_int_matrix(self):
        """Test integer matrix validation"""
        # Valid int8 matrix
        valid_int8 = np.array([[1, 2], [-128, 127]])
        assert is_int_matrix(valid_int8, 8)

        # Value too large for int8
        invalid_int8 = np.array([[1, 200], [3, 4]])  # 200 > 127
        assert not is_int_matrix(invalid_int8, 8)

        # Non-integer matrix
        non_int = np.array([[1.5, 2], [3, 4]])
        assert not is_int_matrix(non_int, 8)

    def test_check_qubo_matrix_bit_width(self):
        """Test QUBO matrix bit width checking"""
        # Valid QUBO matrix
        valid_qubo = np.array([[1, 0.5], [0.5, 2]])
        success, errors = check_qubo_matrix_bit_width(valid_qubo, 8)
        assert success
        assert len(errors) == 0

        # Invalid QUBO matrix (values too large)
        large_qubo = np.array([[1000, 0], [0, 1001]])  # Too large for 8-bit
        success, errors = check_qubo_matrix_bit_width(large_qubo, 8)
        assert not success

        # Test exception handling
        with patch(
            "qcos.engine.qubo.qubo_precision.qubo_matrix_to_ising_matrix"
        ) as mock:
            mock.side_effect = Exception("Test error")
            success, errors = check_qubo_matrix_bit_width(valid_qubo, 8)
            assert not success
            assert "Test error" in errors[0]

    def test_qubo_ising_matrix_conversion(self):
        """Test conversion between QUBO and Ising matrices"""
        # Test QUBO to Ising conversion
        qubo_matrix = np.array([[1, 0.5], [0.5, 2]])
        ising_matrix = qubo_matrix_to_ising_matrix(qubo_matrix)

        # Verify Ising matrix dimensions
        expect_ising_matrix = np.array([
            [0, -0.125, -0.375],
            [-0.125, 0, -0.625],
            [-0.375, -0.625, 0],
        ])
        assert ising_matrix.shape == (3, 3)
        assert np.array_equal(expect_ising_matrix, ising_matrix)

        # Test round-trip conversion
        reconstructed_qubo = ising_matrix_to_qubo_matrix(ising_matrix)

        # Allow for small numerical differences
        assert np.array_equal(qubo_matrix, reconstructed_qubo)

    def test_qubo_ising_matrix_conversion_consistency(self):
        """Test consistency of QUBO-Ising conversions"""
        # Test with known values
        qubo_matrix = np.array([[2, -1], [-1, 3]])

        # Convert to Ising and back
        ising_matrix = qubo_matrix_to_ising_matrix(qubo_matrix)
        round_trip_qubo = ising_matrix_to_qubo_matrix(ising_matrix)

        # Should get original matrix back (within numerical precision)
        assert np.array_equal(qubo_matrix, round_trip_qubo)

    def test_get_spins_num(self):
        """Test spin variable calculation"""
        matrix = np.array([[0, 10, 0], [10, 0, 20], [0, 20, 0]])
        max_value = 15

        spins_list, last_idx, total_spins = get_spins_num(matrix, max_value)

        assert isinstance(spins_list, list)
        assert isinstance(last_idx, list)
        assert isinstance(total_spins, int)
        assert len(spins_list) == matrix.shape[0]
        assert len(last_idx) == matrix.shape[0] + 1
        assert total_spins >= matrix.shape[0]

    def test_precision_reduction(self):
        """Test precision reduction algorithm"""
        ising_matrix = np.array([[0, 10, 5], [10, 0, 15], [5, 15, 0]])
        # don't need precision reduction
        param_bit = 8

        new_ising, last_idx, total_spins = precision_reduction(
            ising_matrix, param_bit
        )

        assert isinstance(new_ising, np.ndarray)
        assert isinstance(last_idx, list)
        assert isinstance(total_spins, int)
        assert new_ising.shape == (total_spins, total_spins)
        assert total_spins == new_ising.shape[0]
        assert len(last_idx) == ising_matrix.shape[0]

        # need precision reduction
        ising_matrix = np.array([[0, 11, 5], [11, 0, 15], [5, 15, 0]])
        param_bit = 4

        new_ising, last_idx, total_spins = precision_reduction(
            ising_matrix, param_bit
        )
        expect_ising_matrix = np.array([
            [0, 6, 5, 3, 2],
            [6, 0, 7, 4, 4],
            [5, 7, 0, 4, 3],
            [3, 4, 4, 0, 7],
            [2, 4, 3, 7, 0],
        ])

        assert isinstance(new_ising, np.ndarray)
        assert isinstance(last_idx, list)
        assert isinstance(total_spins, int)
        assert new_ising.shape == (total_spins, total_spins)
        assert len(last_idx) == ising_matrix.shape[0]
        assert total_spins == new_ising.shape[0]
        assert np.array_equal(expect_ising_matrix, new_ising)

    def test_precision_reduction_edge_cases(self):
        """Test precision reduction with edge cases"""
        # Zero matrix
        zero_matrix = np.zeros((3, 3))
        new_ising, last_idx, total_spins = precision_reduction(zero_matrix, 8)
        assert total_spins >= 3
        assert np.array_equal(new_ising, zero_matrix)
        assert np.array_equal(last_idx, np.array([0, 1, 2]))

        # Diagonal matrix
        diag_matrix = np.diag([1, 2, 3])
        new_ising, last_idx, total_spins = precision_reduction(diag_matrix, 8)
        assert total_spins >= 3
        assert np.array_equal(last_idx, np.array([0, 1, 2]))

    def test_process_qubo_solution(self):
        """Test QUBO solution processing"""
        # Mock job results
        job_results = {
            "results": {
                "out_data": [
                    {"solutionVector": [1, 0, 1, 0, 1], "energy": -1.5}
                ]
            }
        }

        last_idx = [0, 2, 3, 4]
        qubo_matrix = np.array([[1, 0.5], [0.5, 2]])

        # Mock the QUBOSolution.calculate_energy method
        with patch(
            "qcos.engine.qubo.tabu.QUBOSolution.calculate_energy"
        ) as mock_energy:
            mock_energy.return_value = 2.5
            processed_results = process_qubo_solution(
                job_results, last_idx, qubo_matrix
            )

            # Verify the structure is maintained
            assert "results" in processed_results
            assert "out_data" in processed_results["results"]
            assert len(processed_results["results"]["out_data"]) == 1

            solution_data = processed_results["results"]["out_data"][0]
            assert "quboValue" in solution_data
            assert "solutionVector" in solution_data
            assert solution_data["quboValue"] == 2.5

    def test_process_qubo_solution_multiple_solutions(self):
        """Test processing multiple QUBO solutions"""
        job_results = {
            "results": {
                "out_data": [
                    {"solutionVector": [1, 0, 1], "energy": -1.0},
                    {"solutionVector": [0, 0, 0], "energy": -0.5},
                ]
            }
        }

        last_idx = [0, 1, 2]
        qubo_matrix = np.array([[1, 0], [0, 1]])

        with patch(
            "qcos.engine.qubo.tabu.QUBOSolution.calculate_energy"
        ) as mock_energy:
            mock_energy.side_effect = [
                1.0,
                0.5,
            ]  # Different energies for different solutions

            processed_results = process_qubo_solution(
                job_results, last_idx, qubo_matrix
            )

            assert len(processed_results["results"]["out_data"]) == 2
            assert (
                processed_results["results"]["out_data"][0]["quboValue"] == 1.0
            )
            assert (
                processed_results["results"]["out_data"][1]["quboValue"] == 0.5
            )

    def test_edge_cases(self):
        """Test various edge cases"""
        # Empty matrix
        empty_matrix = np.array([]).reshape(0, 0)
        scaled = scale_to_integer_matrix(empty_matrix)
        assert scaled.size == 0

        # Single element matrix
        single_matrix = np.array([[5]])
        gcd_val = find_matrix_gcd(single_matrix)
        assert gcd_val == 5

        # Very small values
        small_matrix = np.array([[0.0001, 0.0002]])
        scaled = scale_to_integer_matrix(small_matrix)
        assert np.all(scaled == [1, 2])
