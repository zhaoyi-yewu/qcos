/*
 * ----------------------------------------------------------------------
 * Copyright(c) 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 *      EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 *      MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <complex>
#include <memory>
#include <unordered_map>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/dag_node.h"

namespace qcos {

using CMatrix = std::vector<std::vector<std::complex<double>>>;

namespace matrix_utils {

// ========================================================================
// Basic Matrix Operations
// ========================================================================

CMatrix identity(size_t n);
CMatrix multiply(const CMatrix& a, const CMatrix& b);
CMatrix tensor_product(const CMatrix& a, const CMatrix& b);
CMatrix conjugate_transpose(const CMatrix& m);
CMatrix scalar_multiply(std::complex<double> s, const CMatrix& m);
double trace(const CMatrix& m);
CMatrix subtract(const CMatrix& a, const CMatrix& b);
CMatrix add(const CMatrix& a, const CMatrix& b);
double frobenius_norm(const CMatrix& m);

// ========================================================================
// Eigenvalue Operations
// ========================================================================

std::vector<std::complex<double>> eigvals(const CMatrix& m);

// Real symmetric 4x4 eigendecomposition via Jacobi iteration.
// Returns eigenvalues in `d` and eigenvectors as columns of `V`.
void eig_real_symmetric_4x4(const CMatrix& M, std::vector<double>& d,
                            CMatrix& V);

// Simultaneous diagonalization of complex symmetric 4x4 matrix M.
// Finds P ∈ O(4) and diagonal D such that M = P diag(D) P^T.
// Returns true on success.
bool simultaneous_diag_4x4(const CMatrix& M, CMatrix& P,
                            std::vector<std::complex<double>>& D);

// ========================================================================
// Matrix Comparison
// ========================================================================

bool is_identity(const CMatrix& m, double tol = 1e-10);
bool is_close(const CMatrix& a, const CMatrix& b, double tol = 1e-10);
bool is_unitary(const CMatrix& m, double tol = 1e-10);

// Check if a ≈ e^{iφ} b for some global phase φ
bool is_close_up_to_phase(const CMatrix& a, const CMatrix& b,
                          double tol = 1e-8);

// ========================================================================
// Advanced Matrix Operations
// ========================================================================

std::complex<double> complex_trace(const CMatrix& m);
CMatrix transpose(const CMatrix& m);
std::complex<double> det2(const CMatrix& m);
std::complex<double> det4(const CMatrix& u);

// ========================================================================
// Gate Operations
// ========================================================================

CMatrix gate_to_matrix(const std::shared_ptr<BaseOperation>& op);

CMatrix compute_block_unitary(
    const std::vector<DAGOpNode*>& block,
    const std::unordered_map<int, int>& qubit_mapping);

}  // namespace matrix_utils

}  // namespace qcos
