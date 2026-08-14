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

#include "optimizer/matrix_utils.h"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>
#include <stdexcept>

#include "circuit/gate_operation.h"

namespace qcos {

namespace matrix_utils {

using C = std::complex<double>;
using CM = CMatrix;

// ========================================================================
// Basic Matrix Operations
// ========================================================================

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

// ========================================================================
// Eigenvalue Operations
// ========================================================================

namespace {

void jacobi_4x4(double A[4][4], double d[4], double V[4][4], int max_iter = 200) {
  for (int i = 0; i < 4; ++i) {
    for (int j = 0; j < 4; ++j) V[i][j] = (i == j) ? 1.0 : 0.0;
  }

  for (int iter = 0; iter < max_iter; ++iter) {
    // Find largest off-diagonal element
    double max_val = 0.0;
    int p = 0, q = 1;
    for (int i = 0; i < 4; ++i)
      for (int j = i + 1; j < 4; ++j)
        if (std::abs(A[i][j]) > max_val) {
          max_val = std::abs(A[i][j]);
          p = i; q = j;
        }

    if (max_val < 1e-15) break;

    double App = A[p][p], Aqq = A[q][q], Apq = A[p][q];
    double theta, t, c, s;

    if (std::abs(App - Aqq) < 1e-15) {
      // Degenerate diagonal: rotate by pi/4
      c = s = 1.0 / std::sqrt(2.0);
    } else {
      theta = (Aqq - App) / (2.0 * Apq);
      if (theta >= 0)
        t = 1.0 / (theta + std::sqrt(1.0 + theta * theta));
      else
        t = 1.0 / (theta - std::sqrt(1.0 + theta * theta));
      c = 1.0 / std::sqrt(1.0 + t * t);
      s = t * c;
    }

    // Update rows p, q
    for (int i = 0; i < 4; ++i) {
      double Aip = A[i][p], Aiq = A[i][q];
      A[i][p] = c * Aip - s * Aiq;
      A[i][q] = s * Aip + c * Aiq;
    }
    // Update cols p, q
    for (int j = 0; j < 4; ++j) {
      double Apj = A[p][j], Aqj = A[q][j];
      A[p][j] = c * Apj - s * Aqj;
      A[q][j] = s * Apj + c * Aqj;
    }
    // Update eigenvectors
    for (int i = 0; i < 4; ++i) {
      double Vip = V[i][p], Viq = V[i][q];
      V[i][p] = c * Vip - s * Viq;
      V[i][q] = s * Vip + c * Viq;
    }
  }
  for (int i = 0; i < 4; ++i) d[i] = A[i][i];
}

}  // namespace

void eig_real_symmetric_4x4(const CMatrix& M, std::vector<double>& d,
                            CMatrix& V) {
  double A[4][4];
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      A[i][j] = M[i][j].real();

  double d_arr[4], V_arr[4][4];
  jacobi_4x4(A, d_arr, V_arr);

  d.resize(4);
  V.assign(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i) {
    d[i] = d_arr[i];
    for (int j = 0; j < 4; ++j)
      V[i][j] = C(V_arr[i][j], 0);
  }
}

bool simultaneous_diag_4x4(const CMatrix& M, CMatrix& P,
                            std::vector<std::complex<double>>& D) {
  std::mt19937 rng(2020);
  std::normal_distribution<double> dist(0.0, 1.0);

  for (int attempt = 0; attempt < 100; ++attempt) {
    double a = dist(rng), b = dist(rng);
    CM H(4, std::vector<C>(4));
    for (int i = 0; i < 4; ++i)
      for (int j = 0; j < 4; ++j)
        H[i][j] = C(a * M[i][j].real() + b * M[i][j].imag(), 0);

    std::vector<double> eigvals;
    CM eigvecs;
    eig_real_symmetric_4x4(H, eigvals, eigvecs);

    // Verify P^T @ M @ P is diagonal (real transpose, NOT conjugate transpose)
    CM PT(4, std::vector<C>(4));
    for (int i = 0; i < 4; ++i)
      for (int j = 0; j < 4; ++j)
        PT[i][j] = eigvecs[j][i];
    CM PTM = multiply(PT, M);
    CM PTMP = multiply(PTM, eigvecs);

    double off_diag = 0.0;
    for (int i = 0; i < 4; ++i)
      for (int j = 0; j < 4; ++j)
        if (i != j) off_diag += std::norm(PTMP[i][j]);

    if (off_diag < 1e-20) {
      // Sort eigenpairs by the eigenvalue of H (ascending) to match the
      // behavior of LAPACK's symmetric eigensolver (np.linalg.eigh), which
      // qiskit's Weyl decomposition relies on: degenerate eigenvalues must be
      // clustered so that the downstream product-gate decomposition stays
      // well-conditioned.
      int order[4] = {0, 1, 2, 3};
      std::sort(order, order + 4,
                [&](int x, int y) { return eigvals[x] < eigvals[y]; });
      P.assign(4, std::vector<C>(4));
      for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
          P[i][j] = eigvecs[i][order[j]];
      D.resize(4);
      for (int i = 0; i < 4; ++i) D[i] = PTMP[order[i]][order[i]];
      return true;
    }
  }
  return false;
}

std::vector<std::complex<double>> eigvals(const CMatrix& m) {
  using C = std::complex<double>;
  size_t n = m.size();

  if (n == 0 || m[0].size() != n) {
    throw std::invalid_argument("eigvals: matrix must be square");
  }

  if (n == 1) {
    return {m[0][0]};
  }

  if (n == 2) {
    C trace = m[0][0] + m[1][1];
    C det = m[0][0] * m[1][1] - m[0][1] * m[1][0];
    C disc = std::sqrt(trace * trace - 4.0 * det);
    return {(trace + disc) / 2.0, (trace - disc) / 2.0};
  }

  if (n == 4) {
    const double tol = 1e-10;

    // First, reduce to upper Hessenberg form using Householder reflections
    CMatrix A = m;
    std::vector<std::vector<C>> Q_hess = identity(4);

    // Hessenberg reduction: A = P_{n-2} ... P_1 A P_1 ... P_{n-2}
    for (size_t k = 0; k < n - 2; ++k) {
      // Construct Householder vector for column k, starting from row k+1
      std::vector<C> v(n - k - 1);
      C sigma = C(0);
      for (size_t i = 1; i < v.size() + 1; ++i) {
        v[i - 1] = A[k + i][k];
        sigma += std::norm(A[k + i][k]);
      }

      if (std::abs(sigma) < tol) continue;

      C alpha = std::sqrt(sigma);
      if (std::real(v[0]) < 0) alpha = -alpha;

      v[0] += alpha;
      C tau = std::conj(alpha) * v[0];

      // Apply P * A from the left
      for (size_t j = k; j < n; ++j) {
        C dot = C(0);
        for (size_t i = 0; i < v.size(); ++i) {
          dot += std::conj(v[i]) * A[k + 1 + i][j];
        }
        dot /= tau;
        for (size_t i = 0; i < v.size(); ++i) {
          A[k + 1 + i][j] -= dot * v[i];
        }
      }

      // Apply A * P from the right
      for (size_t i = 0; i < n; ++i) {
        C dot = C(0);
        for (size_t j = 0; j < v.size(); ++j) {
          dot += A[i][k + 1 + j] * v[j];
        }
        dot /= tau;
        for (size_t j = 0; j < v.size(); ++j) {
          A[i][k + 1 + j] -= dot * std::conj(v[j]);
        }
      }
    }

    // Now perform QR iteration on the Hessenberg matrix
    const int max_iter = 500;

    for (int iter = 0; iter < max_iter; ++iter) {
      // Wilkinson shift: use eigenvalue of bottom-right 2x2 closer to A[3][3]
      C a = A[2][2], b = A[2][3];
      C c = A[3][2], d = A[3][3];
      C trace = a + d;
      C det = a * d - b * c;
      C disc = std::sqrt(trace * trace - 4.0 * det);
      C s1 = (trace + disc) / 2.0;
      C s2 = (trace - disc) / 2.0;
      C shift = (std::abs(s1 - d) < std::abs(s2 - d)) ? s1 : s2;

      // Shift
      for (size_t i = 0; i < n; ++i) {
        A[i][i] -= shift;
      }

      // QR decomposition using Givens rotations (more stable for Hessenberg)
      std::vector<std::pair<C, C>> givens; // (c, s) for each rotation
      std::vector<std::vector<C>> R = A;

      for (size_t i = 0; i < n - 1; ++i) {
        C x = R[i][i];
        C y = R[i + 1][i];
        C norm = std::sqrt(std::norm(x) + std::norm(y));

        if (std::abs(norm) < tol) {
          givens.push_back({C(1), C(0)});
          continue;
        }

        C c = std::conj(x) / norm;
        C s = std::conj(y) / norm;
        givens.push_back({c, s});

        // Apply Givens rotation to rows i and i+1
        for (size_t j = i; j < n; ++j) {
          C temp1 = c * R[i][j] + s * R[i + 1][j];
          C temp2 = -std::conj(s) * R[i][j] + std::conj(c) * R[i + 1][j];
          R[i][j] = temp1;
          R[i + 1][j] = temp2;
        }
      }

      // Apply Givens rotations from the right: A = R * Q
      for (size_t i = 0; i < givens.size(); ++i) {
        C c = givens[i].first;
        C s = givens[i].second;

        // Apply rotation to columns i and i+1
        for (size_t k = 0; k < n; ++k) {
          C temp1 = R[k][i] * c - R[k][i + 1] * std::conj(s);
          C temp2 = R[k][i] * s + R[k][i + 1] * std::conj(c);
          R[k][i] = temp1;
          R[k][i + 1] = temp2;
        }
      }

      A = R;

      // Unshift
      for (size_t i = 0; i < n; ++i) {
        A[i][i] += shift;
      }

      // Check convergence
      double off_diag = 0.0;
      for (size_t i = 1; i < n; ++i) {
        off_diag += std::norm(A[i][i - 1]);
      }

      if (std::sqrt(off_diag) < tol) {
        break;
      }
    }

    // Extract eigenvalues (for Hessenberg, may have 2x2 blocks)
    std::vector<C> eigenvalues;
    size_t i = 0;
    while (i < n) {
      if (i + 1 < n && std::abs(A[i + 1][i]) > tol) {
        // 2x2 block, compute its eigenvalues
        C a = A[i][i], b = A[i][i + 1];
        C c = A[i + 1][i], d = A[i + 1][i + 1];
        C trace = a + d;
        C det = a * d - b * c;
        C disc = std::sqrt(trace * trace - 4.0 * det);
        eigenvalues.push_back((trace + disc) / 2.0);
        eigenvalues.push_back((trace - disc) / 2.0);
        i += 2;
      } else {
        eigenvalues.push_back(A[i][i]);
        i += 1;
      }
    }

    return eigenvalues;
  }

  throw std::runtime_error("eigvals: only supports 1x1, 2x2, and 4x4 matrices");
}

// ========================================================================
// Matrix Comparison
// ========================================================================

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

bool is_unitary(const CMatrix& m, double tol) {
  if (m.size() != m[0].size()) return false;
  CMatrix m_dag = conjugate_transpose(m);
  CMatrix product = multiply(m, m_dag);
  return is_identity(product, tol);
}

bool is_close_up_to_phase(const CMatrix& a, const CMatrix& b, double tol) {
  if (a.size() != b.size() || a.empty() || a[0].size() != b[0].size())
    return false;
  if (is_close(a, b, tol)) return true;
  std::complex<double> phase{0, 0};
  double max_abs = 0.0;
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j) {
      double mag = std::abs(b[i][j]);
      if (mag > max_abs && std::abs(a[i][j]) > tol) {
        max_abs = mag;
        phase = a[i][j] / b[i][j];
      }
    }
  if (max_abs < tol) return true;
  CMatrix scaled = scalar_multiply(phase, b);
  return is_close(a, scaled, tol);
}

// ========================================================================
// Advanced Matrix Operations
// ========================================================================

std::complex<double> complex_trace(const CMatrix& m) {
  std::complex<double> t{0.0, 0.0};
  for (size_t i = 0; i < m.size(); ++i) t += m[i][i];
  return t;
}

CMatrix transpose(const CMatrix& m) {
  size_t n = m.size(), cols = m[0].size();
  CMatrix result(cols, std::vector<std::complex<double>>(n));
  for (size_t i = 0; i < n; ++i)
    for (size_t j = 0; j < cols; ++j)
      result[j][i] = m[i][j];
  return result;
}

std::complex<double> det2(const CMatrix& m) {
  return m[0][0] * m[1][1] - m[0][1] * m[1][0];
}

std::complex<double> det4(const CMatrix& u) {
  using C = std::complex<double>;
  auto minor3 = [&](int r0, int r1, int r2, int c0, int c1, int c2) -> C {
    return u[r0][c0] * (u[r1][c1] * u[r2][c2] - u[r1][c2] * u[r2][c1]) -
           u[r0][c1] * (u[r1][c0] * u[r2][c2] - u[r1][c2] * u[r2][c0]) +
           u[r0][c2] * (u[r1][c0] * u[r2][c1] - u[r1][c1] * u[r2][c0]);
  };
  return u[0][0] * minor3(1, 2, 3, 1, 2, 3) -
         u[0][1] * minor3(1, 2, 3, 0, 2, 3) +
         u[0][2] * minor3(1, 2, 3, 0, 1, 3) -
         u[0][3] * minor3(1, 2, 3, 0, 1, 2);
}

// ========================================================================
// Gate Operations
// ========================================================================

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

  try {
    auto typed_op = create_gate(op->name, op->targets, op->arg_value);
    return gate_to_matrix(typed_op);
  } catch (...) {
    throw std::runtime_error("Unsupported gate for matrix conversion: " +
                             op->name);
  }
}

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

    const auto& effective_qargs =
        (gate_qubits > 0 && !node->qargs.empty()) ? node->qargs
                                                   : node->op->targets;
    std::vector<size_t> positions(effective_qargs.size());
    for (size_t i = 0; i < effective_qargs.size(); ++i) {
      auto it = qubit_mapping.find(effective_qargs[i]);
      if (it == qubit_mapping.end()) {
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

    CMatrix full_mat = identity(dim);

    if (gate_qubits == 1) {
      size_t q = positions[0];
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
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

}  // namespace qcos
