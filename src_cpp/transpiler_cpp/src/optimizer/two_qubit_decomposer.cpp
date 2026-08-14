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

#include "optimizer/two_qubit_decomposer.h"

#include <algorithm>
#include <cassert>
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <numeric>

#include "circuit/gate_operation.h"
#include "optimizer/one_qubit_euler_decomposer.h"

namespace qcos {

namespace {

using C = std::complex<double>;
using CM = CMatrix;

// RZ(theta) matrix
CM rz_matrix(double theta) {
  return {{std::exp(C(0, -theta / 2.0)), C(0)},
          {C(0), std::exp(C(0, theta / 2.0))}};
}

C det4x4(const CM& m) {
  auto minor3 = [](const CM& m, int r0, int r1, int r2,
                   int c0, int c1, int c2) {
    return m[r0][c0] * (m[r1][c1] * m[r2][c2] - m[r1][c2] * m[r2][c1]) -
           m[r0][c1] * (m[r1][c0] * m[r2][c2] - m[r1][c2] * m[r2][c0]) +
           m[r0][c2] * (m[r1][c0] * m[r2][c1] - m[r1][c1] * m[r2][c0]);
  };

  return m[0][0] * minor3(m, 1, 2, 3, 1, 2, 3) -
         m[0][1] * minor3(m, 1, 2, 3, 0, 2, 3) +
         m[0][2] * minor3(m, 1, 2, 3, 0, 1, 3) -
         m[0][3] * minor3(m, 1, 2, 3, 0, 1, 2);
}

// Magic basis B (unnormalized storage, Qiskit convention)
// B_stored = sqrt(2) * B, B_inv_stored = B^dagger / sqrt(2)
// so B_stored * B_inv_stored = I exactly.
CM magic_basis() {
  return {
      {C(1), C(0, 1), C(0), C(0)},
      {C(0), C(0), C(0, 1), C(1)},
      {C(0), C(0), C(0, 1), C(-1)},
      {C(1), C(0, -1), C(0), C(0)}};
}

CM magic_basis_inv() {
  return {
      {C(0.5), C(0), C(0), C(0.5)},
      {C(0, -0.5), C(0), C(0), C(0, 0.5)},
      {C(0), C(0, -0.5), C(0, -0.5), C(0)},
      {C(0), C(0.5), C(-0.5), C(0)}};
}

// Transform to magic basis: B^dag @ U @ B  (reverse=true in Qiskit)
// With unnormalized storage: B_inv_stored @ U @ B_stored
CM to_magic_basis(const CM& u) {
  return matrix_utils::multiply(
      matrix_utils::multiply(magic_basis_inv(), u), magic_basis());
}

// Transform from magic basis: B @ U @ B^dag  (reverse=false in Qiskit)
CM from_magic_basis(const CM& u) {
  return matrix_utils::multiply(
      matrix_utils::multiply(magic_basis(), u), magic_basis_inv());
}

// Decompose K = Kl kron Kr where K in U(4), Kl,Kr in U(2).
// Returns {Kl, Kr, phase} such that K = e^{i*phase} * (Kl kron Kr).
// Follows Qiskit's decompose_two_qubit_product_gate.
struct ProductDecomp {
  CM Kl, Kr;
  double phase;
};

ProductDecomp decompose_product_gate(const CM& K) {
  // Extract right factor R from top-left 2x2 block
  CM R(2, std::vector<C>(2));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      R[i][j] = K[i][j];

  C detR = R[0][0] * R[1][1] - R[0][1] * R[1][0];
  if (std::abs(detR) < 0.1) {
    for (int i = 0; i < 2; ++i)
      for (int j = 0; j < 2; ++j)
        R[i][j] = K[i + 2][j];
    detR = R[0][0] * R[1][1] - R[0][1] * R[1][0];
  }
  if (std::abs(detR) < 0.1) {
    fprintf(stderr, "DECOMPOSE_PRODUCT_GATE FAILED! detR=%.10f\n", std::abs(detR));
    fprintf(stderr, "K:\n");
    for (int r = 0; r < 4; r++) { for (int c2 = 0; c2 < 4; c2++) fprintf(stderr, " (%.6f,%.6f)", K[r][c2].real(), K[r][c2].imag()); fprintf(stderr, "\n"); }
  }
  C sqrt_detR = std::sqrt(detR);
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      R[i][j] /= sqrt_detR;

  // Extract left factor: L = (I kron R^dag) @ K, take stride
  CM Rt_conj(2, std::vector<C>(2));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      Rt_conj[i][j] = std::conj(R[j][i]);

  CM kron_I_Rt = matrix_utils::tensor_product(
      matrix_utils::identity(2), Rt_conj);
  CM temp = matrix_utils::multiply(K, kron_I_Rt);

  CM L(2, std::vector<C>(2));
  L[0][0] = temp[0][0]; L[0][1] = temp[0][2];
  L[1][0] = temp[2][0]; L[1][1] = temp[2][2];

  C detL = L[0][0] * L[1][1] - L[0][1] * L[1][0];
  C sqrt_detL = std::sqrt(detL);
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      L[i][j] /= sqrt_detL;

  double phase = std::arg(detL) / 2.0;
  return {L, R, phase};
}

struct WeylResult {
  double a, b, c;
  double global_phase;
  CM K1l, K1r, K2l, K2r;  // Each 2x2 SU(2)
};

WeylResult compute_weyl_decomposition(const CM& u) {
  const double pi2 = M_PI / 2.0;
  const double pi4 = M_PI / 4.0;

  C det = det4x4(u);
  double global_phase = std::arg(det) / 4.0;
  C phase_factor = std::exp(C(0, -global_phase));
  CM su4 = matrix_utils::scalar_multiply(phase_factor, u);

  CM Up = to_magic_basis(su4);
  CM UpT = matrix_utils::transpose(Up);
  CM M2 = matrix_utils::multiply(UpT, Up);

  CM P;
  std::vector<C> D;
  if (!matrix_utils::simultaneous_diag_4x4(M2, P, D)) {
    throw std::runtime_error("Failed to diagonalize M2");
  }

  // Fix sign of P to be in SO(4)
  double det_P = std::real(matrix_utils::det4(P));
  if (det_P < 0) {
    for (int i = 0; i < 4; ++i) P[i][3] = -P[i][3];
  }

  std::vector<double> d(4);
  for (int i = 0; i < 4; ++i) d[i] = -std::arg(D[i]) / 2.0;
  d[3] = -d[0] - d[1] - d[2];

  fprintf(stderr, "=== Weyl Debug ===\n");
  fprintf(stderr, "D (diagonal): ");
  for (int i = 0; i < 4; ++i) fprintf(stderr, "(%.6f,%.6f) ", D[i].real(), D[i].imag());
  fprintf(stderr, "\n");
  fprintf(stderr, "d (before cs): %.6f %.6f %.6f %.6f\n", d[0], d[1], d[2], d[3]);

  std::vector<double> cs(3);
  for (int i = 0; i < 3; ++i)
    cs[i] = std::fmod((d[i] + d[3]) / 2.0, 2.0 * M_PI);
  if (cs[0] < 0) cs[0] += 2.0 * M_PI;
  if (cs[1] < 0) cs[1] += 2.0 * M_PI;
  if (cs[2] < 0) cs[2] += 2.0 * M_PI;

  // Reorder: argsort by min(cs mod pi/2, pi/2 - cs mod pi/2), take [1,2,0]
  std::vector<double> cstemp(3);
  for (int i = 0; i < 3; ++i) {
    cstemp[i] = std::fmod(cs[i], pi2);
    cstemp[i] = std::min(cstemp[i], pi2 - cstemp[i]);
  }
  std::vector<int> order = {0, 1, 2};
  std::sort(order.begin(), order.end(),
            [&cstemp](int a, int b) { return cstemp[a] < cstemp[b]; });
  // Qiskit: order = argsort(cstemp)[[1,2,0]]
  int qorder[3] = {order[1], order[2], order[0]};

  std::vector<double> cs_new(3), d_new(3);
  CM P_new(4, std::vector<C>(4));
  for (int i = 0; i < 3; ++i) {
    cs_new[i] = cs[qorder[i]];
    d_new[i] = d[qorder[i]];
    for (int r = 0; r < 4; ++r)
      P_new[r][i] = P[r][qorder[i]];
  }
  for (int r = 0; r < 4; ++r) P_new[r][3] = P[r][3];
  cs = cs_new;
  for (int i = 0; i < 3; ++i) d[i] = d_new[i];
  P = P_new;

  // Compute K1, K2 (4x4 in magic basis)
  std::vector<C> exp_id(4);
  for (int i = 0; i < 4; ++i) exp_id[i] = std::exp(C(0, d[i]));

  CM P_exp(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      P_exp[i][j] = P[i][j] * exp_id[j];

  CM K1_mb = from_magic_basis(matrix_utils::multiply(Up, P_exp));
  CM K2_mb = from_magic_basis(matrix_utils::transpose(P));

  auto pd1 = decompose_product_gate(K1_mb);
  auto pd2 = decompose_product_gate(K2_mb);
  fprintf(stderr, "K1_mb:\n");
  for (int r = 0; r < 4; r++) { for (int c2 = 0; c2 < 4; c2++) fprintf(stderr, " (%.6f,%.6f)", K1_mb[r][c2].real(), K1_mb[r][c2].imag()); fprintf(stderr, "\n"); }
  fprintf(stderr, "K2_mb:\n");
  for (int r = 0; r < 4; r++) { for (int c2 = 0; c2 < 4; c2++) fprintf(stderr, " (%.6f,%.6f)", K2_mb[r][c2].real(), K2_mb[r][c2].imag()); fprintf(stderr, "\n"); }
  fprintf(stderr, "K1l det=%.6f K1r det=%.6f\n",
    std::abs(pd1.Kl[0][0]*pd1.Kl[1][1]-pd1.Kl[0][1]*pd1.Kl[1][0]),
    std::abs(pd1.Kr[0][0]*pd1.Kr[1][1]-pd1.Kr[0][1]*pd1.Kr[1][0]));
  CM K1l = pd1.Kl, K1r = pd1.Kr;
  CM K2l = pd2.Kl, K2r = pd2.Kr;
  global_phase += pd1.phase + pd2.phase;

  // ipx, ipy, ipz (i*Pauli matrices)
  CM ipx = {{C(0), C(0, 1)}, {C(0, 1), C(0)}};
  CM ipy = {{C(0), C(1)}, {C(-1), C(0)}};
  CM ipz = {{C(0, 1), C(0)}, {C(0), C(0, -1)}};

  auto right_mul = [](CM& M, const CM& G) {
    M = matrix_utils::multiply(M, G);
  };
  auto left_mul = [](CM& M, const CM& G) {
    M = matrix_utils::multiply(G, M);
  };

  // Flip into Weyl chamber
  if (cs[0] > pi2) {
    cs[0] -= 3 * pi2;
    right_mul(K1l, ipy);
    right_mul(K1r, ipy);
    global_phase += pi2;
  }
  if (cs[1] > pi2) {
    cs[1] -= 3 * pi2;
    right_mul(K1l, ipx);
    right_mul(K1r, ipx);
    global_phase += pi2;
  }
  int conjs = 0;
  if (cs[0] > pi4) {
    cs[0] = pi2 - cs[0];
    right_mul(K1l, ipy);
    left_mul(K2r, ipy);
    conjs++;
    global_phase -= pi2;
  }
  if (cs[1] > pi4) {
    cs[1] = pi2 - cs[1];
    right_mul(K1l, ipx);
    left_mul(K2r, ipx);
    conjs++;
    global_phase += pi2;
    if (conjs == 1) global_phase -= M_PI;
  }
  if (cs[2] > pi2) {
    cs[2] -= 3 * pi2;
    right_mul(K1l, ipz);
    right_mul(K1r, ipz);
    global_phase += pi2;
    if (conjs == 1) global_phase -= M_PI;
  }
  if (conjs == 1) {
    cs[2] = pi2 - cs[2];
    right_mul(K1l, ipz);
    left_mul(K2r, ipz);
    global_phase += pi2;
  }
  if (cs[2] > pi4) {
    cs[2] -= pi2;
    right_mul(K1l, ipz);
    right_mul(K1r, ipz);
    global_phase -= pi2;
  }

  double a = cs[1], b = cs[0], c = cs[2];
  return {a, b, c, global_phase, K1l, K1r, K2l, K2r};
}

bool basis_has(const std::optional<std::set<std::string>>& basis,
               const std::string& g) {
  if (!basis.has_value()) return true;
  return basis->count(g) > 0;
}

void emit_1q_gates(const CM& mat, int qubit,
                    const std::optional<std::set<std::string>>& basis,
                    std::vector<std::shared_ptr<BaseOperation>>& result) {
  auto gates = single_qubit_unitary_to_basis(mat, qubit, basis);
  result.insert(result.end(), gates.begin(), gates.end());
}

void emit_entangling_gate(
    int q0, int q1,
    const std::optional<std::set<std::string>>& basis,
    std::vector<std::shared_ptr<BaseOperation>>& result) {
  if (basis_has(basis, "cx")) {
    result.push_back(create_gate("cx", {q0, q1}));
  } else if (basis_has(basis, "cz")) {
    // CX = (I ⊗ H) · CZ · (I ⊗ H) up to global phase
    // Decompose H using single_qubit_unitary_to_basis
    if (basis_has(basis, "h")) {
      result.push_back(create_gate("h", {q1}));
      result.push_back(create_gate("cz", {q0, q1}));
      result.push_back(create_gate("h", {q1}));
    } else {
      // Decompose H into available 1Q basis gates
      auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
      auto h_gates = single_qubit_unitary_to_basis(h_mat, q1, basis);
      result.insert(result.end(), h_gates.begin(), h_gates.end());
      result.push_back(create_gate("cz", {q0, q1}));
      result.insert(result.end(), h_gates.begin(), h_gates.end());
    }
  } else if (basis_has(basis, "iswap")) {
    result.push_back(create_gate("iswap", {q0, q1}));
  } else if (basis_has(basis, "ecr")) {
    result.push_back(create_gate("ecr", {q0, q1}));
  } else {
    result.push_back(create_gate("cx", {q0, q1}));
  }
}

bool try_direct_match(
    const CM& u, int q0, int q1,
    const std::optional<std::set<std::string>>& basis,
    std::vector<std::shared_ptr<BaseOperation>>& result) {
  struct GateInfo {
    const char* name;
  };
  GateInfo gates[] = {
      {"cx"}, {"cz"}, {"swap"},
      {"iswap"}, {"ecr"}};

  for (const auto& gi : gates) {
    if (!basis_has(basis, gi.name)) continue;
    auto gate_mat = matrix_utils::gate_to_matrix(
        create_gate(gi.name, {0, 1}));
    if (matrix_utils::is_close_up_to_phase(u, gate_mat, 1e-8)) {
      result.push_back(create_gate(gi.name, {q0, q1}));
      return true;
    }
  }
  return false;
}

// ========================================================================
// KAK Decomposition — Qiskit-compatible implementation
// ========================================================================

// Qiskit's ipx, ipy, ipz
const CM ipx_mat = {{C(0), C(0, 1)}, {C(0, 1), C(0)}};
const CM ipy_mat = {{C(0), C(1)}, {C(-1), C(0)}};
const CM ipz_mat = {{C(0, 1), C(0)}, {C(0), C(0, -1)}};
const CM id_mat = {{C(1), C(0)}, {C(0), C(1)}};

// Precomputed KAK matrices for CX-class basis (a=pi/4, c=0)
// Qiskit: b = basis.b, here CX has b=0
struct KakPrecomputed {
  CM k1ld, k1rd, k2ld, k2rd;  // daggers of basis K matrices

  // 3-part decomposition matrices
  CM u0l, u0r, u1l, u1ra, u1rb, u2la, u2lb, u2ra, u2rb, u3l, u3r;

  // 2-part decomposition matrices
  CM q0l, q0r, q1la, q1lb, q1ra, q1rb, q2l, q2r;
};

KakPrecomputed compute_kak_precomputed() {
  // For CX basis: a=pi/4, b=0, c=0
  // The Weyl decomposition of CX gives:
  // K1l, K1r, K2l, K2r from compute_weyl_decomposition
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto basis_wd = compute_weyl_decomposition(cx_mat);

  CM k1l = basis_wd.K1l, k1r = basis_wd.K1r;
  CM k2l = basis_wd.K2l, k2r = basis_wd.K2r;

  double b = basis_wd.b;

  // Qiskit precomputed matrices (lines 878-962 of two_qubit_decompose.py)
  C one_plus_i = C(1, 1);
  double sqrt2 = std::sqrt(2.0);

  CM K11l = matrix_utils::scalar_multiply(
      C(1) / one_plus_i,
      {{C(0, -1) * std::exp(C(0, -b)), std::exp(C(0, -b))},
       {C(0, -1) * std::exp(C(0, b)), -std::exp(C(0, b))}});

  CM K11r = matrix_utils::scalar_multiply(
      C(1, 0) / sqrt2,
      {{C(0, 1) * std::exp(C(0, -b)), -std::exp(C(0, -b))},
       {std::exp(C(0, b)), C(0, -1) * std::exp(C(0, b))}});

  CM K12l = matrix_utils::scalar_multiply(
      C(1) / one_plus_i,
      {{C(0, 1), C(0, 1)}, {C(-1), C(1)}});

  CM K12r = matrix_utils::scalar_multiply(
      C(1, 0) / sqrt2,
      {{C(0, 1), C(1)}, {C(-1), C(0, -1)}});

  CM K32lK21l = matrix_utils::scalar_multiply(
      C(1, 0) / sqrt2,
      {{C(1, 0) + C(0, std::cos(2 * b)), C(0, std::sin(2 * b))},
       {C(0, std::sin(2 * b)), C(1, 0) - C(0, std::cos(2 * b))}});

  CM K21r = matrix_utils::scalar_multiply(
      C(1) / C(1, -1),
      {{C(0, -1) * std::exp(C(0, -2 * b)), std::exp(C(0, -2 * b))},
       {C(0, 1) * std::exp(C(0, 2 * b)), std::exp(C(0, 2 * b))}});

  CM K22l = matrix_utils::scalar_multiply(
      C(1, 0) / sqrt2,
      {{C(1), C(-1)}, {C(1), C(1)}});

  CM K22r = {{C(0), C(1)}, {C(-1), C(0)}};

  CM K31l = matrix_utils::scalar_multiply(
      C(1, 0) / sqrt2,
      {{std::exp(C(0, -b)), std::exp(C(0, -b))},
       {-std::exp(C(0, b)), std::exp(C(0, b))}});

  CM K31r = matrix_utils::scalar_multiply(
      C(0, 1),
      {{std::exp(C(0, b)), C(0)}, {C(0), -std::exp(C(0, -b))}});

  CM K32r = matrix_utils::scalar_multiply(
      C(1) / C(1, -1),
      {{std::exp(C(0, b)), -std::exp(C(0, -b))},
       {C(0, -1) * std::exp(C(0, b)), C(0, -1) * std::exp(C(0, -b))}});

  // Dags
  CM k1ld = matrix_utils::conjugate_transpose(k1l);
  CM k1rd = matrix_utils::conjugate_transpose(k1r);
  CM k2ld = matrix_utils::conjugate_transpose(k2l);
  CM k2rd = matrix_utils::conjugate_transpose(k2r);

  KakPrecomputed kp;
  kp.k1ld = k1ld; kp.k1rd = k1rd;
  kp.k2ld = k2ld; kp.k2rd = k2rd;

  // 3-part precomputed
  kp.u0l = matrix_utils::multiply(K31l, k1ld);
  kp.u0r = matrix_utils::multiply(K31r, k1rd);
  kp.u1l = matrix_utils::multiply(k2ld,
      matrix_utils::multiply(K32lK21l, k1ld));
  kp.u1ra = matrix_utils::multiply(k2rd, K32r);
  kp.u1rb = matrix_utils::multiply(K21r, k1rd);
  kp.u2la = matrix_utils::multiply(k2ld, K22l);
  kp.u2lb = matrix_utils::multiply(K11l, k1ld);
  kp.u2ra = matrix_utils::multiply(k2rd, K22r);
  kp.u2rb = matrix_utils::multiply(K11r, k1rd);
  kp.u3l = matrix_utils::multiply(k2ld, K12l);
  kp.u3r = matrix_utils::multiply(k2rd, K12r);

  // 2-part precomputed
  kp.q0l = matrix_utils::multiply(
      matrix_utils::conjugate_transpose(K12l), k1ld);
  kp.q0r = matrix_utils::multiply(
      matrix_utils::multiply(
          matrix_utils::conjugate_transpose(K12r), ipz_mat), k1rd);
  kp.q1la = matrix_utils::multiply(k2ld,
      matrix_utils::conjugate_transpose(K11l));
  kp.q1lb = matrix_utils::multiply(K11l, k1ld);
  kp.q1ra = matrix_utils::multiply(k2rd,
      matrix_utils::multiply(ipz_mat,
          matrix_utils::conjugate_transpose(K11r)));
  kp.q1rb = matrix_utils::multiply(K11r, k1rd);
  kp.q2l = matrix_utils::multiply(k2ld, K12l);
  kp.q2r = matrix_utils::multiply(k2rd, K12r);

  return kp;
}

// Qiskit decomp0: K1l@K2l, K1r@K2r (tensor product)
std::vector<CM> decomp0(const WeylResult& target) {
  return {
      matrix_utils::multiply(target.K1r, target.K2r),
      matrix_utils::multiply(target.K1l, target.K2l)
  };
}

// Qiskit decomp1: 1 basis gate
std::vector<CM> decomp1(const WeylResult& target,
                         const KakPrecomputed& kp) {
  // Use precomputed basis K matrices directly
  CM U0l = matrix_utils::multiply(target.K1l, kp.k1ld);
  CM U0r = matrix_utils::multiply(target.K1r, kp.k1rd);
  CM U1l = matrix_utils::multiply(kp.k2ld, target.K2l);
  CM U1r = matrix_utils::multiply(kp.k2rd, target.K2r);
  return {U1r, U1l, U0r, U0l};
}

// Qiskit decomp2_supercontrolled: 2 basis gates
std::vector<CM> decomp2(const WeylResult& target,
                         const KakPrecomputed& kp) {
  CM U0l = matrix_utils::multiply(target.K1l, kp.q0l);
  CM U0r = matrix_utils::multiply(target.K1r, kp.q0r);
  CM U1l = matrix_utils::multiply(kp.q1la,
      matrix_utils::multiply(rz_matrix(-2 * target.a), kp.q1lb));
  CM U1r = matrix_utils::multiply(kp.q1ra,
      matrix_utils::multiply(rz_matrix(2 * target.b), kp.q1rb));
  CM U2l = matrix_utils::multiply(kp.q2l, target.K2l);
  CM U2r = matrix_utils::multiply(kp.q2r, target.K2r);
  return {U2r, U2l, U1r, U1l, U0r, U0l};
}

// Qiskit decomp3_supercontrolled: 3 basis gates
std::vector<CM> decomp3(const WeylResult& target,
                         const KakPrecomputed& kp) {
  CM U0l = matrix_utils::multiply(target.K1l, kp.u0l);
  CM U0r = matrix_utils::multiply(target.K1r, kp.u0r);
  CM U1l = kp.u1l;
  CM U1r = matrix_utils::multiply(kp.u1ra,
      matrix_utils::multiply(rz_matrix(-2 * target.c), kp.u1rb));
  CM U2l = matrix_utils::multiply(kp.u2la,
      matrix_utils::multiply(rz_matrix(-2 * target.a), kp.u2lb));
  CM U2r = matrix_utils::multiply(kp.u2ra,
      matrix_utils::multiply(rz_matrix(2 * target.b), kp.u2rb));
  CM U3l = matrix_utils::multiply(kp.u3l, target.K2l);
  CM U3r = matrix_utils::multiply(kp.u3r, target.K2r);
  return {U3r, U3l, U2r, U2l, U1r, U1l, U0r, U0l};
}

}  // namespace

TwoQubitDecomp decompose_two_qubit(const CMatrix& u) {
  if (u.size() != 4 || u[0].size() != 4) {
    throw std::invalid_argument(
        "Matrix must be 4x4 for two-qubit decomposition");
  }

  auto wd = compute_weyl_decomposition(u);

  TwoQubitDecomp result;
  result.cx = wd.a;
  result.cy = wd.b;
  result.cz = wd.c;

  double tol = 1e-8;
  if (std::abs(wd.a) < tol && std::abs(wd.b) < tol && std::abs(wd.c) < tol)
    result.num_cx = 0;
  else if (std::abs(wd.b) < tol && std::abs(wd.c) < tol)
    result.num_cx = 1;
  else if (std::abs(wd.c) < tol)
    result.num_cx = 2;
  else
    result.num_cx = 3;

  result.k1 = matrix_utils::tensor_product(wd.K1l, wd.K1r);
  result.k2 = matrix_utils::tensor_product(wd.K2l, wd.K2r);
  result.k3 = matrix_utils::identity(4);
  result.k4 = matrix_utils::identity(4);
  result.global_phase = wd.global_phase;

  return result;
}

// Select best number of basis gates using Qiskit's trace formula
int select_best_nbasis(double a, double b, double c, double b_basis = 0.0) {
  // Traces for supercontrolled basis (a_basis=π/4, c_basis=0)
  C trace_0 = 4.0 * C(std::cos(a)*std::cos(b)*std::cos(c),
                      std::sin(a)*std::sin(b)*std::sin(c));
  C trace_1 = 4.0 * C(std::cos(M_PI/4 - a)*std::cos(b_basis - b)*std::cos(c),
                      std::sin(M_PI/4 - a)*std::sin(b_basis - b)*std::sin(c));
  double trace_2 = 4.0 * std::cos(c);
  double trace_3 = 4.0;

  // Fidelity = (4 + |trace|^2) / 20
  double fid_0 = (4.0 + std::norm(trace_0)) / 20.0;
  double fid_1 = (4.0 + std::norm(trace_1)) / 20.0;
  double fid_2 = (4.0 + trace_2 * trace_2) / 20.0;
  double fid_3 = (4.0 + trace_3 * trace_3) / 20.0;

  // Select best fidelity (prefer more gates if fidelities are close)
  double fids[] = {fid_0, fid_1, fid_2, fid_3};
  int best = 0;
  for (int i = 1; i < 4; ++i) {
    if (fids[i] > fids[best] + 1e-12) {
      best = i;
    }
  }

  return best;
}

std::vector<std::shared_ptr<BaseOperation>> two_qubit_unitary_to_basis(
    const CMatrix& u, int qubit0, int qubit1,
    const std::optional<std::set<std::string>>& basis_gates) {

  std::vector<std::shared_ptr<BaseOperation>> result;

  if (matrix_utils::is_identity(u, 1e-10)) return result;

  if (try_direct_match(u, qubit0, qubit1, basis_gates, result))
    return result;

  auto wd = compute_weyl_decomposition(u);
  double a = wd.a, b = wd.b, c = wd.c;

  // Use trace-based selection to find optimal number of basis gates
  int best_nbasis = select_best_nbasis(a, b, c);

  // Tensor product: emit single-qubit gates only (decomp0)
  if (best_nbasis == 0) {
    auto decomp = decomp0(wd);
    emit_1q_gates(decomp[1], qubit0, basis_gates, result);  // U0l on qubit0 (MSB)
    emit_1q_gates(decomp[0], qubit1, basis_gates, result);  // U0r on qubit1 (LSB)
    return result;
  }

  // Use KAK decomposition
  auto kp = compute_kak_precomputed();
  std::vector<CM> decomposition;

  if (best_nbasis == 1) {
    decomposition = decomp1(wd, kp);
  } else if (best_nbasis == 2) {
    decomposition = decomp2(wd, kp);
    fprintf(stderr, "=== decomp2 DEBUG ===\n");
    fprintf(stderr, "Weyl: a=%.6f b=%.6f c=%.6f\n", a, b, c);
    fprintf(stderr, "wd.K1l:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", wd.K1l[r][c2].real(), wd.K1l[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "wd.K1r:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", wd.K1r[r][c2].real(), wd.K1r[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "wd.K2l:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", wd.K2l[r][c2].real(), wd.K2l[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "wd.K2r:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", wd.K2r[r][c2].real(), wd.K2r[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "kp.q0l:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", kp.q0l[r][c2].real(), kp.q0l[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "kp.q0r:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", kp.q0r[r][c2].real(), kp.q0r[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "kp.q2l:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", kp.q2l[r][c2].real(), kp.q2l[r][c2].imag()); fprintf(stderr, "\n"); }
    fprintf(stderr, "kp.q2r:\n");
    for (int r = 0; r < 2; r++) { for (int c2 = 0; c2 < 2; c2++) fprintf(stderr, " (%.6f,%.6f)", kp.q2r[r][c2].real(), kp.q2r[r][c2].imag()); fprintf(stderr, "\n"); }
    for (int k = 0; k < (int)decomposition.size(); k++) {
      fprintf(stderr, "decomp[%d]:\n", k);
      for (int r = 0; r < 2; r++) {
        for (int c2 = 0; c2 < 2; c2++)
          fprintf(stderr, " (%.6f,%.6f)", decomposition[k][r][c2].real(), decomposition[k][r][c2].imag());
        fprintf(stderr, "\n");
      }
    }
  } else {
    decomposition = decomp3(wd, kp);
  }

  // decomposition layout: [U_Nr, U_Nl, ..., U_1r, U_1l, U_0r, U_0l]
  // Qiskit: decomposition[2*i] = Ur (right factor, acts on q[0]=LSB)
  //         decomposition[2*i+1] = Ul (left factor, acts on q[1]=MSB)
  // Our convention: qubit0 = MSB, qubit1 = LSB
  // So: Ur → qubit1 (LSB), Ul → qubit0 (MSB)
  for (int i = 0; i < best_nbasis; ++i) {
    emit_1q_gates(decomposition[2 * i + 1], qubit0, basis_gates, result);  // Ul on qubit0 (MSB)
    emit_1q_gates(decomposition[2 * i], qubit1, basis_gates, result);      // Ur on qubit1 (LSB)
    emit_entangling_gate(qubit0, qubit1, basis_gates, result);
  }
  emit_1q_gates(decomposition[2 * best_nbasis + 1], qubit0, basis_gates, result);  // Ul on qubit0
  emit_1q_gates(decomposition[2 * best_nbasis], qubit1, basis_gates, result);      // Ur on qubit1

  return result;
}

}  // namespace qcos
