/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include "optimizer/unitary_synthesis.h"

#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <complex>
#include <numeric>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "optimizer/collect_block.h"

namespace qcos {

// ========================================================================
// Matrix Utilities
// ========================================================================

namespace matrix_utils {

CMatrix identity(size_t n) {
  CMatrix m(n, std::vector<std::complex<double>>(n, {0.0, 0.0}));
  for (size_t i = 0; i < n; ++i) m[i][i] = {1.0, 0.0};
  return m;
}

CMatrix multiply(const CMatrix& a, const CMatrix& b) {
  size_t n = a.size();
  size_t p = b.size();
  size_t m = b[0].size();
  CMatrix c(n, std::vector<std::complex<double>>(m, {0.0, 0.0}));
  for (size_t i = 0; i < n; ++i) {
    for (size_t k = 0; k < p; ++k) {
      if (std::abs(a[i][k]) < 1e-15) continue;
      for (size_t j = 0; j < m; ++j) {
        c[i][j] += a[i][k] * b[k][j];
      }
    }
  }
  return c;
}

CMatrix tensor_product(const CMatrix& a, const CMatrix& b) {
  size_t ra = a.size(), ca = a[0].size();
  size_t rb = b.size(), cb = b[0].size();
  CMatrix c(ra * rb, std::vector<std::complex<double>>(ca * cb, {0.0, 0.0}));
  for (size_t i = 0; i < ra; ++i) {
    for (size_t j = 0; j < ca; ++j) {
      for (size_t k = 0; k < rb; ++k) {
        for (size_t l = 0; l < cb; ++l) {
          c[i * rb + k][j * cb + l] = a[i][j] * b[k][l];
        }
      }
    }
  }
  return c;
}

CMatrix conjugate_transpose(const CMatrix& m) {
  size_t n = m.size(), cols = m[0].size();
  CMatrix result(cols, std::vector<std::complex<double>>(n));
  for (size_t i = 0; i < n; ++i)
    for (size_t j = 0; j < cols; ++j)
      result[j][i] = std::conj(m[i][j]);
  return result;
}

CMatrix scalar_multiply(std::complex<double> s, const CMatrix& m) {
  CMatrix result = m;
  for (auto& row : result)
    for (auto& val : row) val *= s;
  return result;
}

double trace(const CMatrix& m) {
  std::complex<double> t{0.0, 0.0};
  for (size_t i = 0; i < m.size(); ++i) t += m[i][i];
  return t.real();
}

CMatrix subtract(const CMatrix& a, const CMatrix& b) {
  CMatrix c(a.size(), std::vector<std::complex<double>>(a[0].size()));
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j)
      c[i][j] = a[i][j] - b[i][j];
  return c;
}

CMatrix add(const CMatrix& a, const CMatrix& b) {
  CMatrix c(a.size(), std::vector<std::complex<double>>(a[0].size()));
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j)
      c[i][j] = a[i][j] + b[i][j];
  return c;
}

double frobenius_norm(const CMatrix& m) {
  double s = 0.0;
  for (const auto& row : m)
    for (const auto& v : row) s += std::norm(v);
  return std::sqrt(s);
}

bool is_identity(const CMatrix& m, double tol) {
  if (m.size() != m[0].size()) return false;
  for (size_t i = 0; i < m.size(); ++i)
    for (size_t j = 0; j < m.size(); ++j) {
      double expected = (i == j) ? 1.0 : 0.0;
      if (std::abs(m[i][j] - std::complex<double>(expected, 0.0)) > tol)
        return false;
    }
  return true;
}

bool is_close(const CMatrix& a, const CMatrix& b, double tol) {
  if (a.size() != b.size() || a[0].size() != b[0].size()) return false;
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j)
      if (std::abs(a[i][j] - b[i][j]) > tol) return false;
  return true;
}

// Convert a gate operation to its unitary matrix by calling the
// existing to_matrix() on each gate subclass via dynamic_cast.
CMatrix gate_to_matrix(const std::shared_ptr<BaseOperation>& op) {
  using C = std::complex<double>;

  auto to_mat = [](const auto& arr, size_t dim) -> CMatrix {
    CMatrix m(dim, std::vector<C>(dim));
    for (size_t i = 0; i < dim; ++i)
      for (size_t j = 0; j < dim; ++j) m[i][j] = arr[i * dim + j];
    return m;
  };

  // Single-qubit gates (2x2)
  if (auto* g = dynamic_cast<const H*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const X*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const Y*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const Z*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const S*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const SDG*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const T*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const TDG*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const P*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const R*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const RX*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const RY*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const RZ*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const SX*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const SXDG*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const U1*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const U2*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const U3*>(op.get())) return to_mat(g->to_matrix(), 2);
  if (auto* g = dynamic_cast<const U*>(op.get())) return to_mat(g->to_matrix(), 2);

  // Two-qubit gates (4x4)
  if (auto* g = dynamic_cast<const CZ*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CX*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CY*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const SWAP*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const ISWAP*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CH*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CS*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CSDG*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CRX*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CRY*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CRZ*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CU1*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CP*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CU3*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CSX*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const CU*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const ECR*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const DCX*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const RXX*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const RYY*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const RZZ*>(op.get())) return to_mat(g->to_matrix(), 4);
  if (auto* g = dynamic_cast<const RZX*>(op.get())) return to_mat(g->to_matrix(), 4);

  // Three-qubit gates (8x8)
  if (auto* g = dynamic_cast<const CCX*>(op.get())) return to_mat(g->to_matrix(), 8);
  if (auto* g = dynamic_cast<const CSWAP*>(op.get())) return to_mat(g->to_matrix(), 8);
  if (auto* g = dynamic_cast<const RCCX*>(op.get())) return to_mat(g->to_matrix(), 8);

  // Four-qubit gates (16x16)
  if (auto* g = dynamic_cast<const RC3X*>(op.get())) return to_mat(g->to_matrix(), 16);
  if (auto* g = dynamic_cast<const C3X*>(op.get())) return to_mat(g->to_matrix(), 16);
  if (auto* g = dynamic_cast<const C3SQRTX*>(op.get())) return to_mat(g->to_matrix(), 16);

  // Five-qubit gates (32x32)
  if (auto* g = dynamic_cast<const C4X*>(op.get())) return to_mat(g->to_matrix(), 32);

  // Fallback: recreate via create_gate to get a properly-typed subclass.
  // This handles cases where gates were created as plain GateOperation
  // (e.g., by the Decomposer with allow_undefined=true).
  try {
    auto typed_op = create_gate(op->name, op->targets, op->arg_value);
    return gate_to_matrix(typed_op);
  } catch (...) {
    throw std::runtime_error("Unsupported gate for matrix conversion: " +
                             op->name);
  }
}

// Compute the block's unitary matrix with given qubit mapping
// qubit_mapping: block-local qubit index -> position in the unitary
CMatrix compute_block_unitary(
    const std::vector<DAGOpNode*>& block,
    const std::unordered_map<int, int>& qubit_mapping) {
  using C = std::complex<double>;
  size_t num_qubits = qubit_mapping.size();
  size_t dim = 1ULL << num_qubits;
  CMatrix result = identity(dim);

  for (DAGOpNode* node : block) {
    CMatrix gate_mat = gate_to_matrix(node->op);
    size_t gate_qubits = node->qargs.size();

    // Map block qubits to positions.
    // Use op->targets as fallback when node->qargs has been invalidated
    // (e.g. after a DAG modification by replace_block_with_dag).
    const auto& effective_qargs =
        (gate_qubits > 0 && !node->qargs.empty()) ? node->qargs
                                                   : node->op->targets;
    std::vector<size_t> positions(effective_qargs.size());
    for (size_t i = 0; i < effective_qargs.size(); ++i) {
      auto it = qubit_mapping.find(effective_qargs[i]);
      if (it == qubit_mapping.end()) {
        // Fallback: try op->targets if qargs lookup failed
        if (i < node->op->targets.size()) {
          it = qubit_mapping.find(node->op->targets[i]);
        }
        if (it == qubit_mapping.end()) {
          throw std::runtime_error(
              "compute_block_unitary: qubit " +
              std::to_string(effective_qargs[i]) +
              " not found in qubit_mapping for gate " + node->name());
        }
      }
      positions[i] = it->second;
    }
    gate_qubits = effective_qargs.size();

    // Build the full-dimension gate matrix via tensor product embedding
    CMatrix full_mat = identity(dim);

    if (gate_qubits == 1) {
      // Embed single-qubit gate
      size_t q = positions[0];
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
          // Check if row and col differ only at bit q
          size_t row_q = (row >> (num_qubits - 1 - q)) & 1;
          size_t col_q = (col >> (num_qubits - 1 - q)) & 1;
          size_t row_rest = row ^ (row_q << (num_qubits - 1 - q));
          size_t col_rest = col ^ (col_q << (num_qubits - 1 - q));
          if (row_rest == col_rest) {
            full_mat[row][col] = gate_mat[row_q][col_q];
          } else {
            full_mat[row][col] = C(0);
          }
        }
      }
    } else if (gate_qubits == 2) {
      size_t q0 = positions[0];
      size_t q1 = positions[1];
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
          size_t r0 = (row >> (num_qubits - 1 - q0)) & 1;
          size_t r1 = (row >> (num_qubits - 1 - q1)) & 1;
          size_t c0 = (col >> (num_qubits - 1 - q0)) & 1;
          size_t c1 = (col >> (num_qubits - 1 - q1)) & 1;

          size_t row_rest = row ^ (r0 << (num_qubits - 1 - q0)) ^
                            (r1 << (num_qubits - 1 - q1));
          size_t col_rest = col ^ (c0 << (num_qubits - 1 - q0)) ^
                            (c1 << (num_qubits - 1 - q1));

          if (row_rest == col_rest) {
            size_t gr = r0 * 2 + r1;
            size_t gc = c0 * 2 + c1;
            full_mat[row][col] = gate_mat[gr][gc];
          } else {
            full_mat[row][col] = C(0);
          }
        }
      }
    }

    result = multiply(full_mat, result);
  }

  return result;
}

}  // namespace matrix_utils

// ========================================================================
// Single-Qubit Unitary Decomposition (ZYZ Euler angles)
// ========================================================================

SingleQubitDecomp decompose_single_qubit(const CMatrix& u) {
  using C = std::complex<double>;
  assert(u.size() == 2 && u[0].size() == 2);

  // Extract global phase from determinant
  C det = u[0][0] * u[1][1] - u[0][1] * u[1][0];
  double phase = std::arg(det) / 2.0;

  // Remove global phase to get SU(2) matrix
  C e_neg_i_alpha = std::exp(C(0, -phase));
  C a = u[0][0] * e_neg_i_alpha;
  C b = u[1][0] * e_neg_i_alpha;

  double abs_a = std::abs(a);
  double abs_b = std::abs(b);

  // Clamp for numerical safety
  abs_a = std::min(1.0, std::max(0.0, abs_a));

  double theta = 2.0 * std::acos(abs_a);
  double phi, lambda;

  constexpr double eps = 1e-12;

  if (abs_a > 1.0 - eps && abs_b < eps) {
    // theta ≈ 0: only phi+lambda is determined
    phi = -std::arg(a);
    lambda = -std::arg(a);
  } else if (abs_b > 1.0 - eps && abs_a < eps) {
    // theta ≈ pi: only phi-lambda is determined
    phi = std::arg(b);
    lambda = -std::arg(b);
  } else {
    // General case
    // a = cos(theta/2) * exp(-i(phi+lambda)/2)
    // b = sin(theta/2) * exp(i(phi-lambda)/2)
    double arg_a = std::arg(a);
    double arg_b = std::arg(b);
    phi = arg_b - arg_a;
    lambda = -arg_b - arg_a;
  }

  return {theta, phi, lambda, phase};
}

// Translate single-qubit decomposition to target basis gates
std::vector<std::shared_ptr<BaseOperation>>
single_qubit_unitary_to_basis(
    const CMatrix& u, int qubit,
    const std::optional<std::set<std::string>>& basis_gates) {

  auto decomp = decompose_single_qubit(u);
  double theta = decomp.theta;
  double phi = decomp.phi;
  double lambda = decomp.lambda;

  std::vector<std::shared_ptr<BaseOperation>> result;
  auto targets = std::vector<int>{qubit};

  auto has_gate = [&](const std::string& g) -> bool {
    if (!basis_gates.has_value()) return true;
    return basis_gates->count(g) > 0;
  };

  // Check if identity (theta≈0 and phi+lambda≈0)
  constexpr double eps = 1e-10;
  double total_phase = phi + lambda;
  // Normalize total_phase to [-π, π] for robust near-zero check
  double tp_norm = std::fmod(total_phase + M_PI, 2 * M_PI);
  if (tp_norm < 0) tp_norm += 2 * M_PI;
  tp_norm -= M_PI;
  if (std::abs(theta) < eps && std::abs(tp_norm) < eps) {
    return result;  // Identity, no gates needed
  }

  // Preferred decomposition: U3(θ, φ, λ) or U(θ, φ, λ)
  if (has_gate("u3")) {
    if (std::abs(theta) > eps || std::abs(phi) > eps || std::abs(lambda) > eps) {
      result.push_back(std::make_shared<U3>(targets, std::vector<double>{theta, phi, lambda}));
    }
    return result;
  }
  if (has_gate("u")) {
    if (std::abs(theta) > eps || std::abs(phi) > eps || std::abs(lambda) > eps) {
      result.push_back(std::make_shared<U>(targets, std::vector<double>{theta, phi, lambda}));
    }
    return result;
  }

  // RZ-RY-RZ decomposition: Rz(φ) Ry(θ) Rz(λ)
  bool has_rz = has_gate("rz");
  bool has_ry = has_gate("ry");
  bool has_rx = has_gate("rx");

  if (has_rz && has_ry) {
    // U = Rz(φ) Ry(θ) Rz(λ)
    if (std::abs(lambda) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{lambda}));
    if (std::abs(theta) > eps)
      result.push_back(std::make_shared<RY>(targets, std::vector<double>{theta}));
    if (std::abs(phi) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{phi}));
    return result;
  }

  if (has_rx && has_rz) {
    // U = Rz(φ) Rx(-π/2) Rz(θ) Rx(π/2) Rz(λ)
    if (std::abs(lambda) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{lambda}));
    result.push_back(std::make_shared<RX>(targets, std::vector<double>{M_PI / 2}));
    if (std::abs(theta) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{theta}));
    result.push_back(std::make_shared<RX>(targets, std::vector<double>{-M_PI / 2}));
    if (std::abs(phi) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{phi}));
    return result;
  }

  if (has_rx && has_ry) {
    // U = Ry(π/2) Rz(φ) Ry(θ) Rx(λ) Ry(-π/2) ... approximate
    // Actually use: Ry(π/2) Rx(φ) Ry(θ) Rx(λ) Ry(-π/2) via Rx≈Ry rotation
    // Fallback: just use Rz as Rx with π/2 Ry rotations
    if (std::abs(lambda) > eps)
      result.push_back(std::make_shared<RX>(targets, std::vector<double>{lambda}));
    if (std::abs(theta) > eps)
      result.push_back(std::make_shared<RY>(targets, std::vector<double>{theta}));
    if (std::abs(phi) > eps)
      result.push_back(std::make_shared<RX>(targets, std::vector<double>{phi}));
    return result;
  }

  if (has_rz && has_gate("sx")) {
    // U3(θ, φ, λ) ≡ Rz(λ) Sx Rz(θ+π) Sx Rz(φ+3π)
    if (std::abs(lambda) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{lambda}));
    result.push_back(std::make_shared<SX>(targets));
    if (std::abs(theta + M_PI) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{theta + M_PI}));
    result.push_back(std::make_shared<SX>(targets));
    if (std::abs(phi + 3 * M_PI) > eps)
      result.push_back(std::make_shared<RZ>(targets, std::vector<double>{phi + 3 * M_PI}));
    return result;
  }

  // Fallback: U3 is universally understood in this codebase
  result.push_back(std::make_shared<U3>(targets, std::vector<double>{theta, phi, lambda}));
  return result;
}

// ========================================================================
// Two-Qubit Unitary Decomposition (KAK / Weyl Chamber Decomposition)
//
// Algorithm from:
//   Cross et al. arXiv:1811.12926 (Appendix B)
//   Zhang et al. Phys Rev A 67, 042313 (2003)
//   Kraus & Cirac arXiv:0011050
// ========================================================================

namespace {

using C = std::complex<double>;

// Check if a 4x4 unitary is a tensor product A⊗B of two 2x2 unitaries.
bool try_factor_tensor_product(const CMatrix& u, CMatrix& a, CMatrix& b,
                                double tol = 1e-8) {
  a = CMatrix(2, std::vector<C>(2));
  b = CMatrix(2, std::vector<C>(2));

  CMatrix block00(2, std::vector<C>(2));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      block00[i][j] = u[i][j];

  double b_norm = matrix_utils::frobenius_norm(block00);
  if (b_norm < tol) return false;

  CMatrix b_dag = matrix_utils::conjugate_transpose(block00);

  // Complex trace of b_dag * block00
  CMatrix prod00 = matrix_utils::multiply(b_dag, block00);
  C b_sq_c(0, 0);
  for (int i = 0; i < 2; ++i) b_sq_c += prod00[i][i];
  if (std::abs(b_sq_c) < tol) return false;

  for (int i = 0; i < 2; ++i) {
    for (int j = 0; j < 2; ++j) {
      CMatrix block(2, std::vector<C>(2));
      for (int k = 0; k < 2; ++k)
        for (int l = 0; l < 2; ++l)
          block[k][l] = u[i * 2 + k][j * 2 + l];
      CMatrix prod = matrix_utils::multiply(b_dag, block);
      C tr_val(0, 0);
      for (int k = 0; k < 2; ++k) tr_val += prod[k][k];
      a[i][j] = tr_val / b_sq_c;
    }
  }

  if (std::abs(a[0][0]) < tol) return false;
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      b[i][j] = block00[i][j] / a[0][0];

  CMatrix reconstructed = matrix_utils::tensor_product(a, b);
  // Find phase from largest element
  C phase{0, 0};
  double max_abs = 0;
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      if (std::abs(reconstructed[i][j]) > max_abs) {
        max_abs = std::abs(reconstructed[i][j]);
        phase = u[i][j] / reconstructed[i][j];
      }
  if (max_abs < tol) return false;
  CMatrix phased = matrix_utils::scalar_multiply(phase, reconstructed);
  if (!matrix_utils::is_close(u, phased, tol)) return false;

  a = matrix_utils::scalar_multiply(phase, a);
  return true;
}

// Factor a 4x4 matrix W = A⊗B where A, B ∈ U(2).
// Uses the realignment + SVD approach.
bool factor_su2_su2(const CMatrix& w, CMatrix& a, CMatrix& b,
                     double tol = 1e-8) {
  // Realignment: R[2i+j][2k+l] = W[2i+k][2j+l]
  // For W = A⊗B: W[2i+k][2j+l] = A[i][j]·B[k][l]
  // So R[2i+j][2k+l] = A[i][j]·B[k][l] = vec(A)·vec(B)^T
  CMatrix R(4, std::vector<C>(4, C(0)));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      for (int k = 0; k < 2; ++k)
        for (int l = 0; l < 2; ++l)
          R[2 * i + j][2 * k + l] = w[2 * i + k][2 * j + l];

  // Compute R†R (4x4 Hermitian)
  CMatrix Rdag = matrix_utils::conjugate_transpose(R);
  CMatrix RdagR = matrix_utils::multiply(Rdag, R);

  // Find the dominant eigenvector of RdagR using power iteration
  std::vector<C> v = {C(1), C(0), C(0), C(0)};
  // Initialize with the column of largest norm
  double max_col_norm = 0;
  int best_col = 0;
  for (int j = 0; j < 4; ++j) {
    double cn = 0;
    for (int i = 0; i < 4; ++i) cn += std::norm(RdagR[i][j]);
    if (cn > max_col_norm) { max_col_norm = cn; best_col = j; }
  }
  for (int i = 0; i < 4; ++i) v[i] = RdagR[i][best_col];

  for (int iter = 0; iter < 100; ++iter) {
    std::vector<C> w_vec(4, C(0));
    for (int i = 0; i < 4; ++i)
      for (int j = 0; j < 4; ++j)
        w_vec[i] += RdagR[i][j] * v[j];
    double norm = 0;
    for (int i = 0; i < 4; ++i) norm += std::norm(w_vec[i]);
    norm = std::sqrt(norm);
    if (norm < 1e-15) return false;
    for (int i = 0; i < 4; ++i) v[i] = w_vec[i] / norm;
  }

  // v is the dominant eigenvector (= right singular vector of R)
  // Singular value σ = ||R·v||
  std::vector<C> Rv(4, C(0));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      Rv[i] += R[i][j] * v[j];
  double sigma = 0;
  for (int i = 0; i < 4; ++i) sigma += std::norm(Rv[i]);
  sigma = std::sqrt(sigma);

  if (sigma < tol) return false;

  // Left singular vector: u = R·v / σ
  std::vector<C> u_vec(4);
  for (int i = 0; i < 4; ++i) u_vec[i] = Rv[i] / sigma;

  // B = reshape(v) into 2x2, scaled by √σ
  // A = reshape(u) into 2x2, scaled by √σ
  double sqrt_sigma = std::sqrt(sigma);
  a = CMatrix(2, std::vector<C>(2));
  b = CMatrix(2, std::vector<C>(2));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j) {
      a[i][j] = u_vec[2 * i + j] * sqrt_sigma;
      b[i][j] = v[2 * i + j] * sqrt_sigma;
    }

  // Verify: A⊗B ≈ W (up to global phase)
  CMatrix ab = matrix_utils::tensor_product(a, b);
  // Find phase factor
  C pf{0, 0};
  double max_abs = 0;
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      if (std::abs(w[i][j]) > max_abs) {
        max_abs = std::abs(w[i][j]);
        pf = w[i][j] / ab[i][j];
      }
  if (max_abs < tol) return false;

  CMatrix phased = matrix_utils::scalar_multiply(pf, ab);
  if (!matrix_utils::is_close(w, phased, tol * 100)) {
    // Try absorbing phase into A
    a = matrix_utils::scalar_multiply(pf, a);
    ab = matrix_utils::tensor_product(a, b);
    if (!matrix_utils::is_close(w, ab, tol * 100)) return false;
  } else {
    a = matrix_utils::scalar_multiply(pf, a);
  }

  return true;
}

// Solve cubic equation t³ + p·t² + q·t + r = 0
// Returns three real roots (for our case, roots are always real and in [0,1])
std::array<double, 3> solve_cubic(double p, double q, double r) {
  // Depressed cubic: t = x - p/3
  // x³ + ax + b = 0 where a = q - p²/3, b = r - pq/3 + 2p³/27
  double a = q - p * p / 3.0;
  double b = r - p * q / 3.0 + 2.0 * p * p * p / 27.0;

  double disc = b * b / 4.0 + a * a * a / 27.0;

  std::array<double, 3> roots;
  if (disc > 1e-12) {
    // One real root (shouldn't happen for our case)
    double sq = std::sqrt(disc);
    double u = std::cbrt(-b / 2.0 + sq);
    double v = std::cbrt(-b / 2.0 - sq);
    roots[0] = u + v - p / 3.0;
    roots[1] = roots[0];
    roots[2] = roots[0];
  } else {
    // Three real roots (casus irreducibilis)
    double m = 2.0 * std::sqrt(-a / 3.0);
    double theta = std::acos(3.0 * b / (a * m)) / 3.0;
    roots[0] = m * std::cos(theta) - p / 3.0;
    roots[1] = m * std::cos(theta - 2.0 * M_PI / 3.0) - p / 3.0;
    roots[2] = m * std::cos(theta - 4.0 * M_PI / 3.0) - p / 3.0;
  }

  // Sort descending
  std::sort(roots.begin(), roots.end(), std::greater<double>());
  return roots;
}

}  // namespace

TwoQubitDecomp decompose_two_qubit(const CMatrix& u) {
  using C = std::complex<double>;
  assert(u.size() == 4 && u[0].size() == 4);

  TwoQubitDecomp result;
  result.k1 = matrix_utils::identity(2);
  result.k2 = matrix_utils::identity(2);
  result.k3 = matrix_utils::identity(2);
  result.k4 = matrix_utils::identity(2);
  result.cx = result.cy = result.cz = 0;
  result.num_cx = 0;

  constexpr double eps = 1e-10;

  // Step 0: Check if U is a tensor product A⊗B (0 entangling gates)
  CMatrix a_mat, b_mat;
  if (try_factor_tensor_product(u, a_mat, b_mat)) {
    result.k1 = a_mat;
    result.k2 = b_mat;
    result.num_cx = 0;
    return result;
  }

  // Step 1: Remove global phase to get SU(4)
  // det via cofactor expansion
  auto minor3 = [&](int r0, int r1, int r2, int c0, int c1, int c2) -> C {
    return u[r0][c0] * (u[r1][c1] * u[r2][c2] - u[r1][c2] * u[r2][c1]) -
           u[r0][c1] * (u[r1][c0] * u[r2][c2] - u[r1][c2] * u[r2][c0]) +
           u[r0][c2] * (u[r1][c0] * u[r2][c1] - u[r1][c1] * u[r2][c0]);
  };
  C det_val = u[0][0] * minor3(1, 2, 3, 1, 2, 3) -
              u[0][1] * minor3(1, 2, 3, 0, 2, 3) +
              u[0][2] * minor3(1, 2, 3, 0, 1, 3) -
              u[0][3] * minor3(1, 2, 3, 0, 1, 2);

  double global_phase = std::arg(det_val) / 4.0;
  CMatrix su4 = matrix_utils::scalar_multiply(
      std::exp(C(0, -global_phase)), u);

  // Step 2: Magic basis transform
  // Mb from Cross et al. arXiv:1811.12926
  const double sq = 1.0 / std::sqrt(2.0);
  CMatrix mb = {{C(sq), C(0), C(0), C(0, sq)},
                {C(0), C(0, sq), C(sq), C(0)},
                {C(0), C(0, sq), C(-sq), C(0)},
                {C(sq), C(0), C(0), C(0, -sq)}};
  CMatrix mb_dag = matrix_utils::conjugate_transpose(mb);
  CMatrix u_mb = matrix_utils::multiply(
      matrix_utils::multiply(mb_dag, su4), mb);

  // Step 3: Compute Γ = U_mb^T · U_mb (plain transpose, NOT conjugate)
  CMatrix u_mb_t(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      u_mb_t[i][j] = u_mb[j][i];
  CMatrix gamma = matrix_utils::multiply(u_mb_t, u_mb);

  // Step 4: Extract Weyl coordinates from trace invariants
  //
  // From Zhang et al. PRA 67, 042313 (2003):
  //   tr(Γ) = 4(cos(2a)cos(2b)cos(2c) - i·sin(2a)sin(2b)sin(2c))
  //   tr(Γ²) = 4(cos(4a)cos(4b)cos(4c) - i·sin(4a)sin(4b)sin(4c))
  //   G₂ = cos(4a) + cos(4b) + cos(4c)
  //
  // Let u=cos²(2a), v=cos²(2b), w=cos²(2c):
  //   u + v + w = (G₂ + 3) / 2
  //   u·v·w = (Re(tr(Γ))/4)²
  //   uv + uw + vw = x² + y² + S - 1
  //   where x = Re(tr(Γ))/4, y = -Im(tr(Γ))/4, S = (G₂+3)/2

  C tr_gamma(0, 0);
  for (int i = 0; i < 4; ++i) tr_gamma += gamma[i][i];

  CMatrix gamma2 = matrix_utils::multiply(gamma, gamma);
  C tr_gamma2(0, 0);
  for (int i = 0; i < 4; ++i) tr_gamma2 += gamma2[i][i];

  double x = tr_gamma.real() / 4.0;   // cos(2a)cos(2b)cos(2c)
  double y = -tr_gamma.imag() / 4.0;  // sin(2a)sin(2b)sin(2c)

  // G₂ = (tr(Γ)² - tr(Γ²)) / 4
  C tr_gamma_sq = tr_gamma * tr_gamma;
  C G2 = (tr_gamma_sq - tr_gamma2) / C(4.0);
  double g2_real = G2.real();  // cos(4a) + cos(4b) + cos(4c)

  double S = (g2_real + 3.0) / 2.0;  // u + v + w
  double x2y2 = x * x + y * y;       // u·v·w + ...
  double P = x2y2 + S - 1.0;          // uv + uw + vw
  double Q = x * x;                   // u·v·w

  // Solve cubic: t³ - S·t² + P·t - Q = 0
  auto roots = solve_cubic(-S, P, -Q);

  // Clamp roots to [0, 1] (cos² values)
  for (auto& r : roots) r = std::min(1.0, std::max(0.0, r));

  // Extract Weyl coordinates: cos²(2a) ≥ cos²(2b) ≥ cos²(2c)
  // Since π/4 ≥ a ≥ b ≥ |c|:
  //   cos(2a) ≤ cos(2b) ≤ cos(2c) (for angles in [0, π/2])
  //   So cos²(2a) ≤ cos²(2b) ≤ cos²(2c)
  // roots are sorted descending, so:
  //   cos²(2c) = roots[0] (largest)
  //   cos²(2b) = roots[1]
  //   cos²(2a) = roots[2] (smallest)
  double cos2_2a = roots[2];
  double cos2_2b = roots[1];
  double cos2_2c = roots[0];

  // Recover 2a, 2b, 2c from cos² values
  // 2a ∈ [0, π/2], 2b ∈ [0, π/2], 2c ∈ [-π/2, π/2]
  double two_a = std::acos(std::sqrt(cos2_2a));
  double two_b = std::acos(std::sqrt(cos2_2b));
  double two_c = std::acos(std::sqrt(cos2_2c));

  // Determine signs using the product constraint
  // cos(2a)cos(2b)cos(2c) = x, sin(2a)sin(2b)sin(2c) = y
  double cos2a = std::sqrt(cos2_2a);
  double cos2b = std::sqrt(cos2_2b);
  double cos2c = std::sqrt(cos2_2c);

  // If the product cos(2a)cos(2b)cos(2c) has the wrong sign, negate one
  double prod_cos = cos2a * cos2b * cos2c;
  if (std::abs(prod_cos) > eps) {
    if ((prod_cos > 0 && x < 0) || (prod_cos < 0 && x > 0)) {
      // Flip sign of 2c (the smallest coordinate)
      two_c = -two_c;
      cos2c = -cos2c;
    }
  }

  double sin2a = std::sin(two_a);
  double sin2b = std::sin(two_b);
  double sin2c = std::sin(std::abs(two_c));
  double prod_sin = sin2a * sin2b * sin2c;

  // Check sin product sign; adjust c sign if needed
  if (std::abs(sin2a * sin2b) > eps && std::abs(y) > eps) {
    if ((prod_sin > 0 && y < 0) || (prod_sin < 0 && y > 0)) {
      two_c = -two_c;
    }
  }

  result.cx = two_a / 2.0;
  result.cy = two_b / 2.0;
  result.cz = two_c / 2.0;

  // Ensure Weyl chamber: π/4 ≥ a ≥ b ≥ |c|
  if (result.cx < result.cy) std::swap(result.cx, result.cy);
  if (result.cy < std::abs(result.cz)) {
    if (result.cx < std::abs(result.cz)) {
      std::swap(result.cx, result.cz);
    } else {
      std::swap(result.cy, result.cz);
    }
  }

  // Step 5: Determine number of CX gates needed
  // Based on the Weyl chamber position
  if (result.cx < eps && result.cy < eps && std::abs(result.cz) < eps) {
    result.num_cx = 0;
  } else if (result.cy < eps && std::abs(result.cz) < eps) {
    result.num_cx = 1;
  } else if (std::abs(result.cz) < eps) {
    result.num_cx = 2;
  } else {
    result.num_cx = 3;
  }

  // Step 6: Extract K matrices from eigenvectors of Γ
  // K2_B = eigenvector matrix of Γ (in magic basis)
  // K2_full = Mb · K2_B · Mb† = K2l ⊗ K2r
  // K1_full = U · K2_full† · Ud†

  // For now, use a numerical approach:
  // Compute Ud from (a,b,c) and solve for K matrices
  // Ud = exp(i(a·XX + b·YY + c·ZZ))
  CMatrix xx = {{C(0), C(0), C(0), C(1)},
                {C(0), C(0), C(1), C(0)},
                {C(0), C(1), C(0), C(0)},
                {C(1), C(0), C(0), C(0)}};
  CMatrix yy = {{C(0), C(0), C(0), C(-1)},
                {C(0), C(0), C(1), C(0)},
                {C(0), C(1), C(0), C(0)},
                {C(-1), C(0), C(0), C(0)}};
  CMatrix zz = {{C(1), C(0), C(0), C(0)},
                {C(0), C(-1), C(0), C(0)},
                {C(0), C(0), C(-1), C(0)},
                {C(0), C(0), C(0), C(1)}};

  // H = i(a·XX + b·YY + c·ZZ)
  CMatrix h_mat = matrix_utils::add(
      matrix_utils::add(
          matrix_utils::scalar_multiply(C(0, result.cx), xx),
          matrix_utils::scalar_multiply(C(0, result.cy), yy)),
      matrix_utils::scalar_multiply(C(0, result.cz), zz));

  // exp(H) via Taylor series
  CMatrix ud = matrix_utils::identity(4);
  CMatrix term = matrix_utils::identity(4);
  for (int k = 1; k <= 20; ++k) {
    term = matrix_utils::multiply(term, h_mat);
    double scale = 1.0;
    for (int j = 1; j <= k; ++j) scale /= j;
    ud = matrix_utils::add(ud, matrix_utils::scalar_multiply(C(scale), term));
    if (scale < 1e-16) break;
  }

  // Compute K_combined = U · Ud†
  // K_combined = (K1l⊗K1r) · (K2l⊗K2r) if Ud were between them
  // Actually: U = (K1l⊗K1r) · Ud · (K2l⊗K2r)
  // So: U · (K2l⊗K2r)† = (K1l⊗K1r) · Ud
  // And: Ud† · (K2l⊗K2r) · U† = (K1l⊗K1r)†
  //
  // Simplified: compute K_pre = U · Ud† and try to factor
  CMatrix ud_dag = matrix_utils::conjugate_transpose(ud);
  CMatrix k_combined = matrix_utils::multiply(su4, ud_dag);

  // Try to factor k_combined = K1l ⊗ K1r
  CMatrix k1l, k1r;

  // Fast path: if k_combined ≈ I (up to global phase), K matrices are identity
  C kc_phase{1, 0};
  bool kc_is_identity = false;
  for (int i = 0; i < 4 && !kc_is_identity; ++i) {
    for (int j = 0; j < 4; ++j) {
      if (i == j && std::abs(k_combined[i][j]) > 1e-8) {
        kc_phase = k_combined[i][j];
        CMatrix phased = matrix_utils::scalar_multiply(C(1.0) / kc_phase, k_combined);
        kc_is_identity = matrix_utils::is_identity(phased, 1e-6);
        break;
      }
    }
  }

  if (kc_is_identity) {
    // K matrices are identity — no single-qubit correction needed
    result.k1 = matrix_utils::identity(2);
    result.k2 = matrix_utils::identity(2);
  } else if (factor_su2_su2(k_combined, k1l, k1r)) {
    result.k1 = k1l;
    result.k2 = k1r;
  }

  return result;
}

// Decompose 2Q unitary into basis gates
std::vector<std::shared_ptr<BaseOperation>>
two_qubit_unitary_to_basis(
    const CMatrix& u, int qubit0, int qubit1,
    const std::optional<std::set<std::string>>& basis_gates) {

  std::vector<std::shared_ptr<BaseOperation>> result;

  auto has_gate = [&](const std::string& g) -> bool {
    if (!basis_gates.has_value()) return true;
    return basis_gates->count(g) > 0;
  };

  // Check if the matrix is close to identity (up to global phase)
  constexpr double eps = 1e-8;
  using C = std::complex<double>;

  // Check for identity up to global phase
  C phase_factor{1, 0};
  bool is_phased_identity = false;
  for (int i = 0; i < 4 && !is_phased_identity; ++i) {
    for (int j = 0; j < 4; ++j) {
      if (i == j) {
        if (std::abs(u[i][j]) > eps) {
          phase_factor = u[i][j];
          CMatrix phased_id = matrix_utils::scalar_multiply(
              C(1.0) / phase_factor, u);
          if (matrix_utils::is_identity(phased_id, eps)) {
            is_phased_identity = true;
          }
        }
      }
    }
  }
  if (is_phased_identity) return result;

  // Direct match for known 2Q gates
  auto try_known_gate = [&](const std::string& gate_name,
                             const CMatrix& known_mat) -> bool {
    // Check if u ≈ known_mat up to global phase
    if (std::abs(u[0][0]) < eps && std::abs(known_mat[0][0]) < eps) {
      // Find a non-zero element to determine phase
      for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
          if (std::abs(known_mat[i][j]) > eps && std::abs(u[i][j]) > eps) {
            C pf = u[i][j] / known_mat[i][j];
            CMatrix phased = matrix_utils::scalar_multiply(C(1.0) / pf, u);
            if (matrix_utils::is_close(phased, known_mat, eps)) {
              if (has_gate(gate_name)) {
                result.push_back(create_gate(gate_name, {qubit0, qubit1}));
                return true;
              }
            }
          }
        }
      }
    } else if (std::abs(known_mat[0][0]) > eps) {
      C pf = u[0][0] / known_mat[0][0];
      CMatrix phased = matrix_utils::scalar_multiply(C(1.0) / pf, u);
      if (matrix_utils::is_close(phased, known_mat, eps)) {
        if (has_gate(gate_name)) {
          result.push_back(create_gate(gate_name, {qubit0, qubit1}));
          return true;
        }
      }
    }
    return false;
  };

  // Try known 2Q gates in order of preference
  if (has_gate("cx") && try_known_gate("cx", matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}))))
    return result;
  if (has_gate("cz") && try_known_gate("cz", matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}))))
    return result;
  if (has_gate("swap") && try_known_gate("swap", matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}))))
    return result;
  if (has_gate("iswap") && try_known_gate("iswap", matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}))))
    return result;
  if (has_gate("ecr") && try_known_gate("ecr", matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}))))
    return result;

  auto t0 = std::vector<int>{qubit0};
  auto t1 = std::vector<int>{qubit1};
  auto t01 = std::vector<int>{qubit0, qubit1};

  // Cross-translation: CX ↔ CZ via H on target qubit
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto cz_mat = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));

  auto is_close_phased = [&](const CMatrix& target) -> bool {
    for (int i = 0; i < 4; ++i)
      for (int j = 0; j < 4; ++j)
        if (std::abs(target[i][j]) > eps && std::abs(u[i][j]) > eps) {
          C pf = u[i][j] / target[i][j];
          CMatrix phased = matrix_utils::scalar_multiply(C(1.0) / pf, u);
          if (matrix_utils::is_close(phased, target, eps)) return true;
        }
    return false;
  };

  // CX matched but cx not in basis → translate via CZ
  if (!has_gate("cx") && has_gate("cz") && is_close_phased(cx_mat)) {
    // H = Rz(π/2)·Ry(π/2)·Rz(π/2) (up to global phase)
    auto h_gates = single_qubit_unitary_to_basis(
        matrix_utils::gate_to_matrix(create_gate("h", {qubit1})),
        qubit1, basis_gates);
    result.insert(result.end(), h_gates.begin(), h_gates.end());
    result.push_back(std::make_shared<CZ>(t01));
    result.insert(result.end(), h_gates.begin(), h_gates.end());
    return result;
  }
  // CZ matched but cz not in basis → translate via CX
  if (!has_gate("cz") && has_gate("cx") && is_close_phased(cz_mat)) {
    auto h_gates = single_qubit_unitary_to_basis(
        matrix_utils::gate_to_matrix(create_gate("h", {qubit1})),
        qubit1, basis_gates);
    result.insert(result.end(), h_gates.begin(), h_gates.end());
    result.push_back(std::make_shared<CX>(t01));
    result.insert(result.end(), h_gates.begin(), h_gates.end());
    return result;
  }

  // Try tensor product factorization: U = A⊗B
  CMatrix a_mat, b_mat;
  if (try_factor_tensor_product(u, a_mat, b_mat)) {
    auto k0_gates = single_qubit_unitary_to_basis(a_mat, qubit0, basis_gates);
    auto k1_gates = single_qubit_unitary_to_basis(b_mat, qubit1, basis_gates);
    result.insert(result.end(), k0_gates.begin(), k0_gates.end());
    result.insert(result.end(), k1_gates.begin(), k1_gates.end());
    return result;
  }

  // General case: use KAK decomposition
  auto decomp = decompose_two_qubit(u);

  // Emit pre-rotation (K3, K4)
  auto k3_gates = single_qubit_unitary_to_basis(decomp.k3, qubit0, basis_gates);
  result.insert(result.end(), k3_gates.begin(), k3_gates.end());
  auto k4_gates = single_qubit_unitary_to_basis(decomp.k4, qubit1, basis_gates);
  result.insert(result.end(), k4_gates.begin(), k4_gates.end());

  // Helper: emit H gate decomposed into basis
  auto emit_h = [&](int qubit) {
    auto h_mat = matrix_utils::gate_to_matrix(
        create_gate("h", std::vector<int>{qubit}));
    return single_qubit_unitary_to_basis(h_mat, qubit, basis_gates);
  };

  // Emit entangling gates
  if (decomp.num_cx >= 1) {
    if (has_gate("cx")) {
      result.push_back(std::make_shared<CX>(t01));
    } else if (has_gate("cz")) {
      auto h1 = emit_h(qubit1);
      result.insert(result.end(), h1.begin(), h1.end());
      result.push_back(std::make_shared<CZ>(t01));
      result.insert(result.end(), h1.begin(), h1.end());
    }
  }
  if (decomp.num_cx >= 2) {
    if (std::abs(decomp.cy) > eps) {
      // Decompose RY into basis gates
      auto ry0 = single_qubit_unitary_to_basis(
          matrix_utils::gate_to_matrix(create_gate("ry", {qubit0}, {decomp.cy})),
          qubit0, basis_gates);
      auto ry1 = single_qubit_unitary_to_basis(
          matrix_utils::gate_to_matrix(create_gate("ry", {qubit1}, {-decomp.cy})),
          qubit1, basis_gates);
      result.insert(result.end(), ry0.begin(), ry0.end());
      result.insert(result.end(), ry1.begin(), ry1.end());
    }
    if (has_gate("cx")) {
      result.push_back(std::make_shared<CX>(t01));
    } else if (has_gate("cz")) {
      auto h1 = emit_h(qubit1);
      result.insert(result.end(), h1.begin(), h1.end());
      result.push_back(std::make_shared<CZ>(t01));
      result.insert(result.end(), h1.begin(), h1.end());
    }
  }
  if (decomp.num_cx >= 3) {
    if (std::abs(decomp.cz) > eps) {
      auto rz0 = single_qubit_unitary_to_basis(
          matrix_utils::gate_to_matrix(create_gate("rz", {qubit0}, {decomp.cz})),
          qubit0, basis_gates);
      auto rz1 = single_qubit_unitary_to_basis(
          matrix_utils::gate_to_matrix(create_gate("rz", {qubit1}, {-decomp.cz})),
          qubit1, basis_gates);
      result.insert(result.end(), rz0.begin(), rz0.end());
      result.insert(result.end(), rz1.begin(), rz1.end());
    }
    if (has_gate("cx")) {
      result.push_back(std::make_shared<CX>(t01));
    } else if (has_gate("cz")) {
      auto h1 = emit_h(qubit1);
      result.insert(result.end(), h1.begin(), h1.end());
      result.push_back(std::make_shared<CZ>(t01));
      result.insert(result.end(), h1.begin(), h1.end());
    }
  }

  // Emit post-rotation (K1, K2)
  auto k1_gates = single_qubit_unitary_to_basis(decomp.k1, qubit0, basis_gates);
  result.insert(result.end(), k1_gates.begin(), k1_gates.end());
  auto k2_gates = single_qubit_unitary_to_basis(decomp.k2, qubit1, basis_gates);
  result.insert(result.end(), k2_gates.begin(), k2_gates.end());

  return result;
}

// ========================================================================
// decompose_unitary — 核心接口
// ========================================================================

std::vector<std::shared_ptr<BaseOperation>> decompose_unitary(
    const CMatrix& unitary,
    const std::set<std::string>& basis_gates,
    const std::vector<int>& qubits) {
  if (unitary.empty() || unitary[0].empty()) {
    throw std::invalid_argument("decompose_unitary: empty matrix");
  }

  size_t dim = unitary.size();
  if (dim != unitary[0].size()) {
    throw std::invalid_argument("decompose_unitary: matrix is not square");
  }

  // Verify unitarity: U†U ≈ I
  auto u_dag = matrix_utils::conjugate_transpose(unitary);
  auto product = matrix_utils::multiply(u_dag, unitary);
  if (!matrix_utils::is_identity(product, 1e-8)) {
    throw std::invalid_argument("decompose_unitary: input is not unitary");
  }

  std::optional<std::set<std::string>> bg = basis_gates;

  if (dim == 2) {
    // Single-qubit decomposition
    int q = qubits.empty() ? 0 : qubits[0];
    return single_qubit_unitary_to_basis(unitary, q, bg);
  }

  if (dim == 4) {
    // Two-qubit decomposition
    int q0 = qubits.size() > 0 ? qubits[0] : 0;
    int q1 = qubits.size() > 1 ? qubits[1] : 1;
    return two_qubit_unitary_to_basis(unitary, q0, q1, bg);
  }

  throw std::invalid_argument(
      "decompose_unitary: unsupported matrix dimension " +
      std::to_string(dim) + " (only 2x2 and 4x4 are supported)");
}

// ========================================================================
// UnitarySynthesis Pass
// ========================================================================

UnitarySynthesis::UnitarySynthesis(
    const std::optional<std::set<std::string>>& basis_gates,
    double approximation_degree,
    size_t max_block_size)
    : basis_gates_(basis_gates),
      approximation_degree_(approximation_degree),
      max_block_size_(max_block_size) {}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_1q(
    const CMatrix& u, int qubit) {
  return single_qubit_unitary_to_basis(u, qubit, basis_gates_);
}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_2q(
    const CMatrix& u, int q0, int q1) {
  return two_qubit_unitary_to_basis(u, q0, q1, basis_gates_);
}

UnitarySynthesis::OpList UnitarySynthesis::synthesize_block(
    const CMatrix& unitary, const std::vector<int>& qubits) {
  if (qubits.size() == 1) {
    return synthesize_1q(unitary, qubits[0]);
  } else if (qubits.size() == 2) {
    return synthesize_2q(unitary, qubits[0], qubits[1]);
  }
  // For >2 qubit blocks, decompose recursively (not implemented yet)
  return {};
}

int UnitarySynthesis::run(
    DAGCircuit& dag,
    const std::optional<std::set<std::string>>& basis_gates) {
  const auto& bg = basis_gates.has_value() ? basis_gates : basis_gates_;

  int total_replaced = 0;

  // Phase 1: Optimize 1Q gate runs.
  // Use only single-qubit gates as collect_gates so that 2Q gates act as
  // separators. This prevents the entire circuit from becoming one giant
  // block that exceeds max_block_size.
  std::set<std::string> collect_1q;
  for (const auto& g : Constant::SINGLE_QUBIT_GATE_LIST) {
    collect_1q.insert(g);
  }

  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_1q, 2);
    if (blocks.empty()) break;

    bool any_replaced = false;

    for (const auto& block : blocks) {
      std::vector<int> qubits;
      std::unordered_map<int, int> qubit_mapping;
      for (DAGOpNode* node : block) {
        for (int q : node->qargs) {
          if (qubit_mapping.find(q) == qubit_mapping.end()) {
            qubit_mapping[q] = static_cast<int>(qubits.size());
            qubits.push_back(q);
          }
        }
      }

      // 1Q runs should only involve 1 qubit, but guard anyway
      if (qubits.size() > max_block_size_) continue;

      CMatrix unitary = matrix_utils::compute_block_unitary(block, qubit_mapping);

      OpList replacement;
      if (qubits.size() == 1) {
        replacement = synthesize_1q(unitary, qubits[0]);
      } else if (qubits.size() == 2) {
        replacement = synthesize_2q(unitary, qubits[0], qubits[1]);
      }

      bool has_non_basis_gate = false;
      if (bg.has_value()) {
        for (DAGOpNode* node : block) {
          if (bg->count(node->name()) == 0) {
            has_non_basis_gate = true;
            break;
          }
        }
      }

      bool should_replace = false;
      if (has_non_basis_gate) {
        should_replace = true;
      } else if (!replacement.empty() && replacement.size() < block.size()) {
        should_replace = true;
      } else if (replacement.empty() && block.size() > 0) {
        should_replace = (block.size() > 1);
      }

      if (should_replace) {
        DAGCircuit replacement_dag;
        replacement_dag.add_qubits(static_cast<int>(qubits.size()));
        for (const auto& op : replacement) {
          auto local_op = op->clone();
          std::vector<int> local_targets;
          for (int t : op->targets) {
            local_targets.push_back(qubit_mapping[t]);
          }
          local_op->setTargets(local_targets);
          replacement_dag.apply_operation_back(local_op);
        }

        std::unordered_map<int, int> local_to_global;
        for (const auto& [global_q, local_idx] : qubit_mapping) {
          local_to_global[local_idx] = global_q;
        }

        dag.replace_block_with_dag(block, replacement_dag, local_to_global);
        total_replaced += static_cast<int>(block.size()) -
                          static_cast<int>(replacement.size());
        any_replaced = true;
        break;  // re-collect after DAG modification
      }
    }

    if (!any_replaced) break;
  }

  // Phase 2: Optimize 2Q blocks.
  // Use all gates as collect_gates. Since 1Q runs have been consolidated
  // in Phase 1, blocks tend to be smaller (centered around 2Q gates).
  std::set<std::string> collect_all;
  for (const auto& g : Constant::ALL_GATE_LIST) {
    collect_all.insert(g);
  }

  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_all, 2);
    if (blocks.empty()) break;

    bool any_replaced = false;

    for (const auto& block : blocks) {
      std::vector<int> qubits;
      std::unordered_map<int, int> qubit_mapping;
      for (DAGOpNode* node : block) {
        for (int q : node->qargs) {
          if (qubit_mapping.find(q) == qubit_mapping.end()) {
            qubit_mapping[q] = static_cast<int>(qubits.size());
            qubits.push_back(q);
          }
        }
      }

      if (qubits.size() > max_block_size_) continue;

      CMatrix unitary = matrix_utils::compute_block_unitary(block, qubit_mapping);

      OpList replacement;
      if (qubits.size() == 1) {
        replacement = synthesize_1q(unitary, qubits[0]);
      } else if (qubits.size() == 2) {
        replacement = synthesize_2q(unitary, qubits[0], qubits[1]);
      }

      bool has_non_basis_gate = false;
      if (bg.has_value()) {
        for (DAGOpNode* node : block) {
          if (bg->count(node->name()) == 0) {
            has_non_basis_gate = true;
            break;
          }
        }
      }

      bool should_replace = false;
      if (has_non_basis_gate) {
        should_replace = true;
      } else if (!replacement.empty() && replacement.size() < block.size()) {
        should_replace = true;
      } else if (replacement.empty() && block.size() > 1) {
        should_replace = true;
      }

      if (should_replace) {
        DAGCircuit replacement_dag;
        replacement_dag.add_qubits(static_cast<int>(qubits.size()));
        for (const auto& op : replacement) {
          auto local_op = op->clone();
          std::vector<int> local_targets;
          for (int t : op->targets) {
            local_targets.push_back(qubit_mapping[t]);
          }
          local_op->setTargets(local_targets);
          replacement_dag.apply_operation_back(local_op);
        }

        std::unordered_map<int, int> local_to_global;
        for (const auto& [global_q, local_idx] : qubit_mapping) {
          local_to_global[local_idx] = global_q;
        }

        dag.replace_block_with_dag(block, replacement_dag, local_to_global);
        total_replaced += static_cast<int>(block.size()) -
                          static_cast<int>(replacement.size());
        any_replaced = true;
        break;  // re-collect after DAG modification
      }
    }

    if (!any_replaced) break;
  }

  return total_replaced;
}

// ========================================================================
// ConsolidateBlocks Pass
// ========================================================================

ConsolidateBlocks::ConsolidateBlocks(
    const std::optional<std::set<std::string>>& basis_gates,
    double approximation_degree,
    size_t min_block_size)
    : basis_gates_(basis_gates),
      approximation_degree_(approximation_degree),
      min_block_size_(min_block_size) {}

int ConsolidateBlocks::run(
    DAGCircuit& dag,
    const std::optional<std::set<std::string>>& basis_gates) {
  const auto& bg = basis_gates.has_value() ? basis_gates : basis_gates_;

  std::set<std::string> collect_gates;
  for (const auto& g : Constant::ALL_GATE_LIST) {
    collect_gates.insert(g);
  }

  int total_replaced = 0;

  // Re-collect blocks after each replacement to avoid dangling pointers.
  while (true) {
    auto blocks = collect_all_matching_blocks(dag, collect_gates, min_block_size_);
    if (blocks.empty()) break;

    bool any_replaced = false;

    for (const auto& block : blocks) {
      std::vector<int> qubits;
      std::unordered_map<int, int> qubit_mapping;
      for (DAGOpNode* node : block) {
        for (int q : node->qargs) {
          if (qubit_mapping.find(q) == qubit_mapping.end()) {
            qubit_mapping[q] = static_cast<int>(qubits.size());
            qubits.push_back(q);
          }
        }
      }

      if (qubits.size() > 2) continue;

      CMatrix unitary = matrix_utils::compute_block_unitary(block, qubit_mapping);

      UnitarySynthesis synthesizer(bg, approximation_degree_);
      auto replacement = synthesizer.synthesize_block(unitary, qubits);

      bool consolidate_has_non_basis = false;
      if (bg.has_value()) {
        for (DAGOpNode* node : block) {
          if (bg->count(node->name()) == 0) {
            consolidate_has_non_basis = true;
            break;
          }
        }
      }

      bool consolidate_should_replace = false;
      if (consolidate_has_non_basis) {
        consolidate_should_replace = true;
      } else if (!replacement.empty() && replacement.size() < block.size()) {
        consolidate_should_replace = true;
      }

      if (consolidate_should_replace) {
        DAGCircuit replacement_dag;
        replacement_dag.add_qubits(static_cast<int>(qubits.size()));
        for (const auto& op : replacement) {
          auto local_op = op->clone();
          std::vector<int> local_targets;
          for (int t : op->targets) {
            local_targets.push_back(qubit_mapping[t]);
          }
          local_op->setTargets(local_targets);
          replacement_dag.apply_operation_back(local_op);
        }

        // replace_block_with_dag expects local→global mapping
        std::unordered_map<int, int> local_to_global;
        for (const auto& [global_q, local_idx] : qubit_mapping) {
          local_to_global[local_idx] = global_q;
        }

        dag.replace_block_with_dag(block, replacement_dag, local_to_global);
        total_replaced += static_cast<int>(block.size()) -
                          static_cast<int>(replacement.size());
        any_replaced = true;
        // Break and re-collect: DAG modified, remaining pointers invalid.
        break;
      }
    }

    if (!any_replaced) break;
  }

  return total_replaced;
}

}  // namespace qcos
