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

#include <gtest/gtest.h>

#include <algorithm>
#include <cmath>
#include <complex>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "optimizer/matrix_utils.h"
#include "test_optimizer_utils.h"

using namespace qcos;
using C = std::complex<double>;

// ========================================================================
// Matrix Utils Extended Tests
// ========================================================================

TEST(MatrixUtilsExtendedTest, Determinant2x2) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  C det = matrix_utils::det2(m);
  EXPECT_NEAR(det.real(), 0.0, 1e-10);
  EXPECT_NEAR(det.imag(), -16.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, Determinant2x2Identity) {
  auto id = matrix_utils::identity(2);
  C det = matrix_utils::det2(id);
  EXPECT_NEAR(det.real(), 1.0, 1e-10);
  EXPECT_NEAR(det.imag(), 0.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, Determinant4x4Identity) {
  auto id = matrix_utils::identity(4);
  C det = matrix_utils::det4(id);
  EXPECT_NEAR(det.real(), 1.0, 1e-10);
  EXPECT_NEAR(det.imag(), 0.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, Determinant4x4CX) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  C det = matrix_utils::det4(cx);
  EXPECT_NEAR(std::abs(det), 1.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, Transpose2x2) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  auto mt = matrix_utils::transpose(m);
  EXPECT_NEAR(mt[0][0].real(), 1.0, 1e-10);
  EXPECT_NEAR(mt[0][0].imag(), 2.0, 1e-10);
  EXPECT_NEAR(mt[0][1].real(), 5.0, 1e-10);
  EXPECT_NEAR(mt[0][1].imag(), 6.0, 1e-10);
  EXPECT_NEAR(mt[1][0].real(), 3.0, 1e-10);
  EXPECT_NEAR(mt[1][0].imag(), 4.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, ComplexTrace) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  C tr = matrix_utils::complex_trace(m);
  EXPECT_NEAR(tr.real(), 8.0, 1e-10);
  EXPECT_NEAR(tr.imag(), 10.0, 1e-10);
}

TEST(MatrixUtilsExtendedTest, IsUnitaryForAllGates) {
  std::vector<std::string> gates_1q = {
      "h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg"};
  for (const auto& g : gates_1q) {
    auto op = create_gate(g, {0});
    auto m = matrix_utils::gate_to_matrix(op);
    EXPECT_TRUE(matrix_utils::is_unitary(m, 1e-10))
        << "Gate " << g << " should be unitary";
  }
}

TEST(MatrixUtilsExtendedTest, IsUnitaryParameterizedGates) {
  std::vector<std::pair<std::string, std::vector<double>>> gates = {
      {"rx", {M_PI / 3}}, {"ry", {M_PI / 4}}, {"rz", {M_PI / 5}},
      {"u3", {1.0, 2.0, 3.0}}, {"p", {M_PI / 6}}};
  for (const auto& [name, params] : gates) {
    auto op = create_gate(name, {0}, params);
    auto m = matrix_utils::gate_to_matrix(op);
    EXPECT_TRUE(matrix_utils::is_unitary(m, 1e-10))
        << "Gate " << name << " should be unitary";
  }
}

// ========================================================================
// Basic Operations: multiply, tensor_product, conjugate_transpose, etc.
// ========================================================================

TEST(MatrixUtilsBasicOpsTest, Multiply2x2) {
  CMatrix a = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  CMatrix b = {{C(5, 0), C(6, 0)}, {C(7, 0), C(8, 0)}};
  auto c = matrix_utils::multiply(a, b);
  EXPECT_NEAR(c[0][0].real(), 19.0, 1e-12);
  EXPECT_NEAR(c[0][1].real(), 22.0, 1e-12);
  EXPECT_NEAR(c[1][0].real(), 43.0, 1e-12);
  EXPECT_NEAR(c[1][1].real(), 50.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, MultiplyComplex) {
  CMatrix a = {{C(0, 1), C(1, 0)}, {C(1, 0), C(0, -1)}};
  CMatrix b = {{C(1, 0), C(0, 0)}, {C(0, 0), C(1, 0)}};
  auto c = matrix_utils::multiply(a, b);
  EXPECT_NEAR(c[0][0].real(), 0.0, 1e-12);
  EXPECT_NEAR(c[0][0].imag(), 1.0, 1e-12);
  EXPECT_NEAR(c[1][1].real(), 0.0, 1e-12);
  EXPECT_NEAR(c[1][1].imag(), -1.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, MultiplyNonSquare) {
  // 2x3 times 3x2 -> 2x2
  CMatrix a = {{C(1, 0), C(2, 0), C(3, 0)}, {C(4, 0), C(5, 0), C(6, 0)}};
  CMatrix b = {{C(1, 0), C(0, 0)}, {C(0, 0), C(1, 0)}, {C(1, 0), C(1, 0)}};
  auto c = matrix_utils::multiply(a, b);
  ASSERT_EQ(c.size(), 2u);
  ASSERT_EQ(c[0].size(), 2u);
  EXPECT_NEAR(c[0][0].real(), 4.0, 1e-12);  // 1*1+2*0+3*1
  EXPECT_NEAR(c[0][1].real(), 5.0, 1e-12);  // 1*0+2*1+3*1
  EXPECT_NEAR(c[1][0].real(), 10.0, 1e-12); // 4*1+5*0+6*1
  EXPECT_NEAR(c[1][1].real(), 11.0, 1e-12); // 4*0+5*1+6*1
}

TEST(MatrixUtilsBasicOpsTest, MultiplyIdentityIsNoOp) {
  CMatrix a = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  auto id = matrix_utils::identity(2);
  EXPECT_TRUE(matrix_utils::is_close(matrix_utils::multiply(a, id), a, 1e-12));
  EXPECT_TRUE(matrix_utils::is_close(matrix_utils::multiply(id, a), a, 1e-12));
}

TEST(MatrixUtilsBasicOpsTest, TensorProduct2x2) {
  // kron([[1,2],[3,4]], [[0,1],[1,0]])
  CMatrix a = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  CMatrix x = {{C(0, 0), C(1, 0)}, {C(1, 0), C(0, 0)}};
  auto t = matrix_utils::tensor_product(a, x);
  ASSERT_EQ(t.size(), 4u);
  ASSERT_EQ(t[0].size(), 4u);
  // top-left block = 1 * X
  EXPECT_NEAR(t[0][0].real(), 0.0, 1e-12);
  EXPECT_NEAR(t[0][1].real(), 1.0, 1e-12);
  EXPECT_NEAR(t[1][0].real(), 1.0, 1e-12);
  EXPECT_NEAR(t[1][1].real(), 0.0, 1e-12);
  // block (0,1) = 2 * X
  EXPECT_NEAR(t[0][2].real(), 0.0, 1e-12);
  EXPECT_NEAR(t[0][3].real(), 2.0, 1e-12);
  // block (1,1) = 4 * X -> entry [3][3]
  EXPECT_NEAR(t[3][2].real(), 4.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, ConjugateTranspose) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  auto md = matrix_utils::conjugate_transpose(m);
  // m^dag[i][j] = conj(m[j][i])
  EXPECT_NEAR(md[0][0].real(), 1.0, 1e-12);
  EXPECT_NEAR(md[0][0].imag(), -2.0, 1e-12);
  EXPECT_NEAR(md[0][1].real(), 5.0, 1e-12);
  EXPECT_NEAR(md[0][1].imag(), -6.0, 1e-12);
  EXPECT_NEAR(md[1][0].real(), 3.0, 1e-12);
  EXPECT_NEAR(md[1][0].imag(), -4.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, ConjugateTransposeIsUnitaryInverse) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto hd = matrix_utils::conjugate_transpose(h);
  auto prod = matrix_utils::multiply(h, hd);
  EXPECT_TRUE(matrix_utils::is_identity(prod, 1e-12));
}

TEST(MatrixUtilsBasicOpsTest, ScalarMultiply) {
  CMatrix m = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  auto s = matrix_utils::scalar_multiply(C(0, 1), m);  // multiply by i
  EXPECT_NEAR(s[0][0].real(), 0.0, 1e-12);
  EXPECT_NEAR(s[0][0].imag(), 1.0, 1e-12);
  EXPECT_NEAR(s[1][1].real(), 0.0, 1e-12);
  EXPECT_NEAR(s[1][1].imag(), 4.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, Trace) {
  CMatrix m = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  EXPECT_NEAR(matrix_utils::trace(m), 5.0, 1e-12);
  // trace is real-valued (per API); imag part dropped
  CMatrix mc = {{C(0, 1), C(0, 0)}, {C(0, 0), C(0, 2)}};
  EXPECT_NEAR(matrix_utils::trace(mc), 0.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, AddSubtract) {
  CMatrix a = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  CMatrix b = {{C(5, 0), C(6, 0)}, {C(7, 0), C(8, 0)}};
  auto s = matrix_utils::add(a, b);
  EXPECT_NEAR(s[0][0].real(), 6.0, 1e-12);
  EXPECT_NEAR(s[1][1].real(), 12.0, 1e-12);
  auto d = matrix_utils::subtract(a, b);
  EXPECT_NEAR(d[0][0].real(), -4.0, 1e-12);
  EXPECT_NEAR(d[1][1].real(), -4.0, 1e-12);
}

TEST(MatrixUtilsBasicOpsTest, FrobeniusNorm) {
  // norm of identity_2 = sqrt(1^2 + 1^2) = sqrt(2)
  auto id = matrix_utils::identity(2);
  EXPECT_NEAR(matrix_utils::frobenius_norm(id), std::sqrt(2.0), 1e-12);
  // norm of [[3,4],[0,0]] = sqrt(9+16) = 5
  CMatrix m = {{C(3, 0), C(4, 0)}, {C(0, 0), C(0, 0)}};
  EXPECT_NEAR(matrix_utils::frobenius_norm(m), 5.0, 1e-12);
}

// ========================================================================
// Comparison predicates: is_identity, is_close, is_close_up_to_phase
// ========================================================================

TEST(MatrixUtilsCompareTest, IsIdentityTrueAndFalse) {
  EXPECT_TRUE(matrix_utils::is_identity(matrix_utils::identity(4), 1e-12));
  CMatrix m = matrix_utils::identity(4);
  m[1][1] = C(2, 0);
  EXPECT_FALSE(matrix_utils::is_identity(m, 1e-12));
  // non-square is not identity
  CMatrix ns = {{C(1, 0), C(0, 0)}, {C(0, 0), C(1, 0)}, {C(0, 0), C(0, 0)}};
  EXPECT_FALSE(matrix_utils::is_identity(ns, 1e-12));
}

TEST(MatrixUtilsCompareTest, IsClose) {
  CMatrix a = {{C(1, 0), C(2, 0)}, {C(3, 0), C(4, 0)}};
  EXPECT_TRUE(matrix_utils::is_close(a, a, 1e-12));
  CMatrix b = a;
  b[0][0] = C(1.0001, 0);
  EXPECT_FALSE(matrix_utils::is_close(a, b, 1e-6));
  EXPECT_TRUE(matrix_utils::is_close(a, b, 1e-3));
}

TEST(MatrixUtilsCompareTest, IsCloseUpToPhase) {
  CMatrix a = {{C(1, 0), C(0, 0)}, {C(0, 0), C(1, 0)}};
  // e^{i pi/2} * a = i * I — same structure, different global phase.
  CMatrix b = matrix_utils::scalar_multiply(C(0, 1), a);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(a, b, 1e-10));
  // exactly equal also satisfies
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(a, a, 1e-10));
  // Different structure (not a scalar multiple) -> not equal up to phase.
  CMatrix c = {{C(1, 0), C(1, 0)}, {C(0, 0), C(1, 0)}};
  EXPECT_FALSE(matrix_utils::is_close_up_to_phase(a, c, 1e-10));
}

TEST(MatrixUtilsCompareTest, IsCloseUpToPhasePhaseZeroInput) {
  // When b is all zeros, any phase matches (degenerate); should return true.
  CMatrix a = matrix_utils::identity(2);
  CMatrix z(2, std::vector<C>(2, C(0, 0)));
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(a, z, 1e-8));
}

// ========================================================================
// Real-symmetric 4x4 eigendecomposition (Jacobi)
// ========================================================================

TEST(MatrixUtilsEigenTest, EigRealSymmetric_NonDegenerate) {
  // Non-degenerate real symmetric matrix with well-separated eigenvalues.
  CMatrix M = {{C(4, 0), C(1, 0), C(1, 0), C(1, 0)},
               {C(1, 0), C(5, 0), C(1, 0), C(1, 0)},
               {C(1, 0), C(1, 0), C(6, 0), C(1, 0)},
               {C(1, 0), C(1, 0), C(1, 0), C(7, 0)}};
  std::vector<double> d;
  CMatrix V;
  matrix_utils::eig_real_symmetric_4x4(M, d, V);

  // Eigenvalue set must match LAPACK eigh (ascending), within tolerance.
  std::vector<double> expected = {3.296089645312, 4.392275290273,
                                   5.507748705364, 8.803886359051};
  std::vector<double> ds = d;
  std::sort(ds.begin(), ds.end());
  for (int i = 0; i < 4; ++i)
    EXPECT_NEAR(ds[i], expected[i], 1e-9) << "eigenvalue " << i;

  // V must be orthonormal: V^T V = I (V is real here).
  auto Vt = matrix_utils::transpose(V);
  auto VtV = matrix_utils::multiply(Vt, V);
  EXPECT_TRUE(matrix_utils::is_identity(VtV, 1e-9));

  // Eigendecomposition must hold: M V = V diag(d).
  CMatrix diag(4, std::vector<C>(4, C(0, 0)));
  for (int i = 0; i < 4; ++i) diag[i][i] = C(d[i], 0);
  auto MV = matrix_utils::multiply(M, V);
  auto VD = matrix_utils::multiply(V, diag);
  EXPECT_TRUE(matrix_utils::is_close(MV, VD, 1e-9));
}

TEST(MatrixUtilsEigenTest, EigRealSymmetric_Diagonal) {
  // Already-diagonal matrix: eigenvectors are identity, eigenvalues are diag.
  CMatrix M = {{C(1, 0), C(0, 0), C(0, 0), C(0, 0)},
               {C(0, 0), C(2, 0), C(0, 0), C(0, 0)},
               {C(0, 0), C(0, 0), C(3, 0), C(0, 0)},
               {C(0, 0), C(0, 0), C(0, 0), C(4, 0)}};
  std::vector<double> d;
  CMatrix V;
  matrix_utils::eig_real_symmetric_4x4(M, d, V);
  std::vector<double> ds = d;
  std::sort(ds.begin(), ds.end());
  for (int i = 0; i < 4; ++i)
    EXPECT_NEAR(ds[i], static_cast<double>(i + 1), 1e-9);
}

// ========================================================================
// Simultaneous diagonalization of complex-symmetric 4x4
// ========================================================================

TEST(MatrixUtilsSimDiagTest, DiagonalizesComplexSymmetric) {
  // Constructed non-degenerate complex-symmetric M = P0 diag(D) P0^T.
  CMatrix M = {
      {C(1.84288159679582, 0.826806138748035),
       C(-0.750462764667065, 1.03033470127567),
       C(0.627158632615319, -1.2508044117775),
       C(-0.0270944936161736, 0.0213642288430472)},
      {C(-0.750462764667065, 1.03033470127567),
       C(1.82459039931679, 0.862901191129164),
       C(-0.60517407991912, 1.23222333557268),
       C(-0.366053025667511, 0.56925206558828)},
      {C(0.627158632615319, -1.2508044117775),
       C(-0.60517407991912, 1.23222333557268),
       C(0.869590973696114, 3.25062021221259),
       C(0.0136607699244729, 0.0451009222605302)},
      {C(-0.0270944936161736, 0.0213642288430472),
       C(-0.366053025667511, 0.56925206558828),
       C(0.0136607699244729, 0.0451009222605302),
       C(1.96293703019127, 0.559672457910213)}};

  CMatrix P;
  std::vector<C> D;
  ASSERT_TRUE(matrix_utils::simultaneous_diag_4x4(M, P, D));

  // P must be orthogonal (real-transpose): P^T P = I.
  CMatrix Pt(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j) Pt[i][j] = P[j][i];
  CMatrix PtP = matrix_utils::multiply(Pt, P);
  EXPECT_TRUE(matrix_utils::is_identity(PtP, 1e-9));

  // P^T M P must be diagonal (off-diagonals ~0).
  CMatrix PtM = matrix_utils::multiply(Pt, M);
  CMatrix PtMP = matrix_utils::multiply(PtM, P);
  double off = 0.0;
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      if (i != j) off += std::norm(PtMP[i][j]);
  EXPECT_LT(off, 1e-12);

  // Reconstruct M = P diag(D) P^T and compare.
  CMatrix diag(4, std::vector<C>(4, C(0, 0)));
  for (int i = 0; i < 4; ++i) diag[i][i] = D[i];
  CMatrix PDPt = matrix_utils::multiply(
      matrix_utils::multiply(P, diag), Pt);
  EXPECT_TRUE(matrix_utils::is_close(M, PDPt, 1e-9));

  // Eigenvalue set (|D[i]| = 1 for unitary M2; here magnitudes vary, check set).
  // Expected eigenvalues: {1+2j, 3-1j, 0.5+4j, 2+0.5j}
  std::vector<C> expected = {C(1, 2), C(3, -1), C(0.5, 4), C(2, 0.5)};
  std::vector<C> Ds = D;
  std::sort(Ds.begin(), Ds.end(),
            [](const C& x, const C& y) {
              return std::abs(x - y) < 0 ? false : (x.real() < y.real());
            });
  // Match each expected eigenvalue to some returned eigenvalue.
  for (const auto& e : expected) {
    bool found = false;
    for (const auto& dval : D) {
      if (std::abs(dval - e) < 1e-7) { found = true; break; }
    }
    EXPECT_TRUE(found) << "expected eigenvalue " << e << " not in diagonal D";
  }
}

TEST(MatrixUtilsSimDiagTest, DiagonalMatrixIsTrivial) {
  // Already-diagonal complex-symmetric matrix: P = I (up to signs), D = diag.
  CMatrix M = {{C(1, 0), C(0, 0), C(0, 0), C(0, 0)},
               {C(0, 0), C(2, 0), C(0, 0), C(0, 0)},
               {C(0, 0), C(0, 0), C(3, 0), C(0, 0)},
               {C(0, 0), C(0, 0), C(0, 0), C(4, 0)}};
  CMatrix P;
  std::vector<C> D;
  ASSERT_TRUE(matrix_utils::simultaneous_diag_4x4(M, P, D));
  CMatrix Pt(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j) Pt[i][j] = P[j][i];
  CMatrix PtMP = matrix_utils::multiply(matrix_utils::multiply(Pt, M), P);
  double off = 0.0;
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      if (i != j) off += std::norm(PtMP[i][j]);
  EXPECT_LT(off, 1e-12);
}

// ========================================================================
// compute_block_unitary: compose a sequence of gates into one 4x4 unitary
// ========================================================================

TEST(MatrixUtilsBlockTest, SingleGateIdentity) {
  // An empty block composes to identity on the mapped qubits.
  std::vector<DAGOpNode*> block;
  std::unordered_map<int, int> mapping = {{0, 0}, {1, 1}};
  auto u = matrix_utils::compute_block_unitary(block, mapping);
  ASSERT_EQ(u.size(), 4u);
  EXPECT_TRUE(matrix_utils::is_identity(u, 1e-12));
}

TEST(MatrixUtilsBlockTest, TwoCXIsTheirProduct) {
  // Build a block of [cx] on qubits 0,1 and verify compute_block_unitary
  // returns the CX matrix.
  std::vector<DAGOpNode*> block;
  std::unordered_map<int, int> mapping = {{0, 0}, {1, 1}};
  DAGOpNode node(create_gate("cx", {0, 1}), {0, 1});
  block.push_back(&node);
  auto u = matrix_utils::compute_block_unitary(block, mapping);
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  EXPECT_TRUE(matrix_utils::is_close(u, cx, 1e-10));
}

