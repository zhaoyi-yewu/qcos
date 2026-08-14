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

#include <cmath>
#include <complex>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "circuit/gate_operation.h"
#include "optimizer/matrix_utils.h"
#include "optimizer/two_qubit_decomposer.h"
#include "test_optimizer_utils.h"

using namespace qcos;
using C = std::complex<double>;

// ========================================================================
// Two-Qubit Weyl Decomposition Tests
// ========================================================================

TEST(TwoQubitWeylTest, DecomposeIdentity) {
  auto id = matrix_utils::identity(4);
  auto d = decompose_two_qubit(id);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeCX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeCZ) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeSWAP) {
  auto m = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 3);
}

TEST(TwoQubitWeylTest, DecomposeISWAP) {
  auto m = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 2);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeECR) {
  auto m = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeTensorProductHI) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeTensorProductIH) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(id, h);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeTensorProductRXRY) {
  auto rx = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI / 3}));
  auto ry = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {M_PI / 5}));
  auto tensor = matrix_utils::tensor_product(rx, ry);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeRXX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rxx", {0, 1}, {M_PI / 4}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 8, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, DecomposeRZZ) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rzz", {0, 1}, {M_PI / 5}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 10, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, InvalidMatrixSizeThrows) {
  CMatrix m3x3 = {{C(1), C(0), C(0)},
                  {C(0), C(1), C(0)},
                  {C(0), C(0), C(1)}};
  EXPECT_THROW(decompose_two_qubit(m3x3), std::invalid_argument);
}

// ========================================================================
// Two-Qubit Basis Translation Tests
// ========================================================================

TEST(TwoQubitToBasisExtTest, IdentityProducesNoGates) {
  auto id = matrix_utils::identity(4);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(id, 0, 1, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(TwoQubitToBasisExtTest, CXDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_cx = false;
  for (const auto& g : gates) {
    if (g->name == "cx") has_cx = true;
  }
  EXPECT_TRUE(has_cx);
}

TEST(TwoQubitToBasisExtTest, CZDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_cz = false;
  for (const auto& g : gates) {
    if (g->name == "cz") has_cz = true;
  }
  EXPECT_TRUE(has_cz);
}

TEST(TwoQubitToBasisExtTest, SWAPDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"swap", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_swap = false;
  for (const auto& g : gates) {
    if (g->name == "swap") has_swap = true;
  }
  EXPECT_TRUE(has_swap);
}

TEST(TwoQubitToBasisExtTest, ISWAPDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"iswap", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_iswap = false;
  for (const auto& g : gates) {
    if (g->name == "iswap") has_iswap = true;
  }
  EXPECT_TRUE(has_iswap);
}

TEST(TwoQubitToBasisExtTest, ECRDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  std::set<std::string> basis = {"ecr", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_ecr = false;
  for (const auto& g : gates) {
    if (g->name == "ecr") has_ecr = true;
  }
  EXPECT_TRUE(has_ecr);
}

TEST(TwoQubitToBasisExtTest, TensorProductNoEntanglingGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(tensor, 0, 1, basis);
  bool has_cx = false;
  for (const auto& g : gates) {
    if (g->name == "cx") has_cx = true;
  }
  EXPECT_FALSE(has_cx);
}

TEST(TwoQubitToBasisExtTest, QubitTargetsPreserved) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 0 || q == 1);
    }
  }
}

TEST(TwoQubitToBasisExtTest, CXToCZBasis) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry", "h"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  for (const auto& g : gates) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate " << g->name << " not in basis";
  }
}

// ========================================================================
// Helper: reconstruct 2Q unitary from gate sequence
// ========================================================================

static CMatrix reconstruct_2q(
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    int q0, int q1) {
  size_t n = 2, dim = 4;
  CMatrix result = matrix_utils::identity(dim);
  for (const auto& op : gates) {
    auto gate_mat = matrix_utils::gate_to_matrix(op);
    size_t nq = op->targets.size();
    CMatrix full = matrix_utils::identity(dim);
    if (nq == 1) {
      int q = op->targets[0];
      int pos = (q == q0) ? 0 : 1;
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
          size_t rq = (row >> (n - 1 - pos)) & 1;
          size_t cq = (col >> (n - 1 - pos)) & 1;
          size_t row_rest = row ^ (rq << (n - 1 - pos));
          size_t col_rest = col ^ (cq << (n - 1 - pos));
          full[row][col] = (row_rest == col_rest) ? gate_mat[rq][cq] : C(0);
        }
      }
    } else if (nq == 2) {
      int qa = op->targets[0], qb = op->targets[1];
      int pa = (qa == q0) ? 0 : 1;
      int pb = (qb == q0) ? 0 : 1;
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
          size_t ra = (row >> (n - 1 - pa)) & 1;
          size_t rb = (row >> (n - 1 - pb)) & 1;
          size_t ca = (col >> (n - 1 - pa)) & 1;
          size_t cb = (col >> (n - 1 - pb)) & 1;
          size_t row_rest = row ^ (ra << (n - 1 - pa)) ^ (rb << (n - 1 - pb));
          size_t col_rest = col ^ (ca << (n - 1 - pa)) ^ (cb << (n - 1 - pb));
          if (row_rest == col_rest) {
            full[row][col] = gate_mat[ra * 2 + rb][ca * 2 + cb];
          } else {
            full[row][col] = C(0);
          }
        }
      }
    }
    result = matrix_utils::multiply(full, result);
  }
  return result;
}

static void expect_all_in_basis(
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    const std::set<std::string>& basis) {
  for (const auto& g : gates) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }
}

// 4x4 matrix exponential via scaling-and-squaring + Taylor series.
// Accurate to ~1e-15 for the Hermitian exponents used here.
static CMatrix matrix_exp_4x4(const CMatrix& A0) {
  double norm = 0.0;
  for (size_t i = 0; i < A0.size(); ++i)
    for (size_t j = 0; j < A0[0].size(); ++j)
      norm = std::max(norm, std::abs(A0[i][j]));
  int s = 0;
  while (norm > 0.5) { norm /= 2.0; ++s; }
  CMatrix As = matrix_utils::scalar_multiply(
      std::pow(2.0, -s), A0);
  CMatrix E = matrix_utils::identity(4);
  CMatrix term = matrix_utils::identity(4);
  CMatrix An = As;
  double nfac = 1.0;
  for (int k = 1; k <= 30; ++k) {
    nfac /= k;
    term = matrix_utils::scalar_multiply(nfac, An);
    E = matrix_utils::add(E, term);
    An = matrix_utils::multiply(As, An);
  }
  for (int i = 0; i < s; ++i)
    E = matrix_utils::multiply(E, E);
  return E;
}

// Pauli matrices tensor-producted: XX = kron(X,X) etc.
static CMatrix pauli_xx() {
  return {{C(0), C(0), C(0), C(1)},
          {C(0), C(0), C(1), C(0)},
          {C(0), C(1), C(0), C(0)},
          {C(1), C(0), C(0), C(0)}};
}
static CMatrix pauli_yy() {
  return {{C(0), C(0), C(0), C(-1)},
          {C(0), C(0), C(1), C(0)},
          {C(0), C(1), C(0), C(0)},
          {C(-1), C(0), C(0), C(0)}};
}
static CMatrix pauli_zz() {
  return {{C(1), C(0), C(0), C(0)},
          {C(0), C(-1), C(0), C(0)},
          {C(0), C(0), C(-1), C(0)},
          {C(0), C(0), C(0), C(1)}};
}

// Rebuild U from a Weyl decomposition via the KAK identity:
//   U == exp(i*gp) * k1 * exp(i*(a*XX + b*YY + c*ZZ)) * k2
// where k1 = kron(K1l,K1r), k2 = kron(K2l,K2r) in the computational basis.
static CMatrix rebuild_from_weyl(const TwoQubitDecomp& wd) {
  CMatrix H = matrix_utils::scalar_multiply(wd.cx, pauli_xx());
  CMatrix tmp = matrix_utils::scalar_multiply(wd.cy, pauli_yy());
  H = matrix_utils::add(H, tmp);
  tmp = matrix_utils::scalar_multiply(wd.cz, pauli_zz());
  H = matrix_utils::add(H, tmp);
  CMatrix iH = matrix_utils::scalar_multiply(C(0, 1), H);
  CMatrix Ud = matrix_exp_4x4(iH);
  CMatrix mid = matrix_utils::multiply(
      matrix_utils::multiply(wd.k1, Ud), wd.k2);
  return matrix_utils::scalar_multiply(
      std::exp(C(0, wd.global_phase)), mid);
}

// ========================================================================
// Weyl Decomposition — Parameterized Gate Coordinates
// ========================================================================

TEST(TwoQubitWeylTest, RXX_VariousAngles) {
  for (double angle : {M_PI / 8, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("rxx", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "RXX(" << angle << ") should need 1 CX";
    EXPECT_NEAR(d.cx, angle / 2.0, 1e-8)
        << "RXX(" << angle << "): cx mismatch";
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylTest, RZZ_VariousAngles) {
  for (double angle : {M_PI / 8, M_PI / 5, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("rzz", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "RZZ(" << angle << ") should need 1 CX";
    EXPECT_NEAR(d.cx, angle / 2.0, 1e-8)
        << "RZZ(" << angle << "): cx mismatch";
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylTest, RYY_VariousAngles) {
  for (double angle : {M_PI / 8, M_PI / 4, M_PI / 3}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("ryy", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "RYY(" << angle << ") should need 1 CX";
  }
}

// ========================================================================
// Weyl Decomposition — Additional Standard Gates
// ========================================================================

TEST(TwoQubitWeylTest, DecomposeRZX) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("rzx", {0, 1}, {M_PI / 4}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DecomposeCP) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("cp", {0, 1}, {M_PI / 4}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DecomposeCRX) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("crx", {0, 1}, {M_PI / 3}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DecomposeCRY) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("cry", {0, 1}, {M_PI / 5}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DecomposeCRZ) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("crz", {0, 1}, {M_PI / 7}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DecomposeCU3) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("cu3", {0, 1}, {M_PI / 4, M_PI / 3, M_PI / 6}));
  auto d = decompose_two_qubit(m);
  EXPECT_GE(d.num_cx, 1);
}

// ========================================================================
// Weyl Decomposition — Gate Compositions
// ========================================================================

TEST(TwoQubitWeylTest, BellCircuit) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  CMatrix h_full(4, std::vector<C>(4, C(0)));
  for (size_t row = 0; row < 4; ++row)
    for (size_t col = 0; col < 4; ++col) {
      size_t rq = (row >> 1) & 1, cq = (col >> 1) & 1;
      h_full[row][col] = ((row ^ (rq << 1)) == (col ^ (cq << 1)))
                             ? h[rq][cq] : C(0);
    }
  auto bell = matrix_utils::multiply(cx, h_full);
  auto d = decompose_two_qubit(bell);
  EXPECT_EQ(d.num_cx, 1);
}

TEST(TwoQubitWeylTest, DoubleCX_IsIdentity) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto cx2 = matrix_utils::multiply(cx, cx);
  auto d = decompose_two_qubit(cx2);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, CXCX_IsIdentity_CoordCheck) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto cx2 = matrix_utils::multiply(cx, cx);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(
      matrix_utils::identity(4), cx2, 1e-8));
  auto d = decompose_two_qubit(cx2);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, TensorProductHxS) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto s = matrix_utils::gate_to_matrix(create_gate("s", {0}));
  auto tensor = matrix_utils::tensor_product(h, s);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
  EXPECT_NEAR(d.cx, 0.0, 1e-8);
}

TEST(TwoQubitWeylTest, TensorProductRxRy) {
  auto rx = matrix_utils::gate_to_matrix(
      create_gate("rx", {0}, {M_PI / 3}));
  auto ry = matrix_utils::gate_to_matrix(
      create_gate("ry", {0}, {M_PI / 5}));
  auto tensor = matrix_utils::tensor_product(rx, ry);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
}

// ========================================================================
// Basis Translation — Roundtrip Correctness
//
// 验证 two_qubit_unitary_to_basis 输出的门序列重建后
// 与输入矩阵在全局相位意义下等价。
// ========================================================================

TEST(TwoQubitBasisRoundtrip, CX_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CZ_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, SWAP_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, ISWAP_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, ECR_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, TensorProductHI_CxRzRy) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(tensor, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(tensor, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CX_CzRzRyH) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry", "h"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CZ_CzRzRy) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CP_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("cp", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CRX_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("crx", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, RXX_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("rxx", {0, 1}, {M_PI / 3}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, RZZ_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("rzz", {0, 1}, {M_PI / 5}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, RYY_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("ryy", {0, 1}, {M_PI / 3}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CU3_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("cu3", {0, 1}, {M_PI / 4, M_PI / 3, M_PI / 6}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, RZX_CxRzRy) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("rzx", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "h"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

// ========================================================================
// Basis Translation — Custom Qubit Targets
// ========================================================================

TEST(TwoQubitBasisRoundtrip, CustomQubits_3_7) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 3, 7, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 3 || q == 7) << "Unexpected target: " << q;
    }
  }
  auto reconstructed = reconstruct_2q(gates, 3, 7);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CustomQubits_0_5_SWAP) {
  auto u = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 5, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 0 || q == 5) << "Unexpected target: " << q;
    }
  }
  auto reconstructed = reconstruct_2q(gates, 0, 5);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CustomQubits_ISWAP) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 2, 9, basis);
  expect_all_in_basis(gates, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 2 || q == 9) << "Unexpected target: " << q;
    }
  }
  auto reconstructed = reconstruct_2q(gates, 2, 9);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

// ========================================================================
// Basis Translation — Gate Count Optimization
// ========================================================================

TEST(TwoQubitBasisGateCount, CX_DirectMatch_SingleGate) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") ++cx_count;
  }
  EXPECT_EQ(cx_count, 1);
}

TEST(TwoQubitBasisGateCount, CZ_DirectMatch_SingleGate) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int cz_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cz") ++cz_count;
  }
  EXPECT_EQ(cz_count, 1);
}

TEST(TwoQubitBasisGateCount, SWAP_DirectMatch_SingleGate) {
  auto u = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"swap", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int swap_count = 0;
  for (const auto& g : gates) {
    if (g->name == "swap") ++swap_count;
  }
  EXPECT_EQ(swap_count, 1);
}

TEST(TwoQubitBasisGateCount, ISWAP_DirectMatch_SingleGate) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"iswap", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int iswap_count = 0;
  for (const auto& g : gates) {
    if (g->name == "iswap") ++iswap_count;
  }
  EXPECT_EQ(iswap_count, 1);
}

TEST(TwoQubitBasisGateCount, ECR_DirectMatch_SingleGate) {
  auto u = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  std::set<std::string> basis = {"ecr", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int ecr_count = 0;
  for (const auto& g : gates) {
    if (g->name == "ecr") ++ecr_count;
  }
  EXPECT_EQ(ecr_count, 1);
}

TEST(TwoQubitBasisGateCount, Identity_ZeroGates) {
  auto u = matrix_utils::identity(4);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(TwoQubitBasisGateCount, TensorProduct_No2QGates) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto s = matrix_utils::gate_to_matrix(create_gate("s", {0}));
  auto tensor = matrix_utils::tensor_product(h, s);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(tensor, 0, 1, basis);
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") ++cx_count;
  }
  EXPECT_EQ(cx_count, 0);
}

// ========================================================================
// Basis Translation — Basis Combinations
// ========================================================================

TEST(TwoQubitBasisCombinations, AllSupportedBases_CX) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::vector<std::set<std::string>> bases = {
      {"cx", "rz", "ry"},
      {"cx", "rz", "ry", "u3"},
      {"cz", "rz", "ry", "h"},
      {"cx", "rz", "rx"},
  };
  for (size_t i = 0; i < bases.size(); ++i) {
    const auto& basis = bases[i];
    auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
    expect_all_in_basis(gates, basis);
  }
}

TEST(TwoQubitBasisCombinations, AllSupportedBases_ISWAP) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::vector<std::set<std::string>> bases = {
      {"cx", "rz", "ry", "u3"},
      {"iswap", "rz", "ry"},
      {"cx", "rz", "rx", "u3"},
  };
  for (size_t i = 0; i < bases.size(); ++i) {
    const auto& basis = bases[i];
    auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
    expect_all_in_basis(gates, basis);
  }
}

// ========================================================================
// Error Handling
// ========================================================================

TEST(TwoQubitDecomposerErrorTest, EmptyMatrixThrows) {
  CMatrix empty;
  EXPECT_THROW(decompose_two_qubit(empty), std::invalid_argument);
}

TEST(TwoQubitDecomposerErrorTest, Matrix3x3Throws) {
  CMatrix m3 = {{C(1), C(0), C(0)},
                {C(0), C(1), C(0)},
                {C(0), C(0), C(1)}};
  EXPECT_THROW(decompose_two_qubit(m3), std::invalid_argument);
}

TEST(TwoQubitDecomposerErrorTest, Matrix2x2Throws) {
  auto m2 = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  EXPECT_THROW(decompose_two_qubit(m2), std::invalid_argument);
}

TEST(TwoQubitDecomposerErrorTest, NonSquareMatrixThrows) {
  CMatrix m = {{C(1), C(0), C(0), C(0)},
               {C(0), C(1), C(0), C(0)}};
  EXPECT_THROW(decompose_two_qubit(m), std::invalid_argument);
}

// ========================================================================
// Weyl Decomposition — Additional Standard Gates (Weyl Coordinates)
//
// 对齐 qiskit 的 Weyl 坐标参考值，验证 decompose_two_qubit 给出的
// a/b/c 坐标与 qiskit TwoQubitWeylDecomposition 一致。
// ========================================================================

TEST(TwoQubitWeylCoordTest, DCX) {
  // DCX: a=b=pi/4, c=0  -> 2 CX
  auto m = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 2);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CY) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cy", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CH) {
  auto m = matrix_utils::gate_to_matrix(create_gate("ch", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 4, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CU1) {
  // CU1(lambda): a = lambda/4 (controlled-U1), b=c=0
  auto m = matrix_utils::gate_to_matrix(
      create_gate("cu1", {0, 1}, {M_PI / 4}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 16, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CS) {
  // CS (controlled-S): a = pi/4 / 2 = pi/8
  auto m = matrix_utils::gate_to_matrix(create_gate("cs", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 8, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CSDG) {
  auto m = matrix_utils::gate_to_matrix(create_gate("csdg", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 8, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CSX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("csx", {0, 1}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cx, M_PI / 8, 1e-8);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

TEST(TwoQubitWeylCoordTest, CU) {
  // CU(theta,phi,lambda,gamma): Weyl a depends on params; just check num_cx & b=c=0
  auto m = matrix_utils::gate_to_matrix(
      create_gate("cu", {0, 1}, {M_PI / 4, M_PI / 3, M_PI / 6, 0}));
  auto d = decompose_two_qubit(m);
  EXPECT_EQ(d.num_cx, 1);
  EXPECT_NEAR(d.cy, 0.0, 1e-8);
  EXPECT_NEAR(d.cz, 0.0, 1e-8);
}

// ========================================================================
// Basis Translation — Roundtrip for Additional Standard Gates
// ========================================================================

TEST(TwoQubitBasisRoundtrip, DCX_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CY_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cy", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CH_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("ch", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CS_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cs", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CSDG_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("csdg", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CSX_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(create_gate("csx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CU1_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("cu1", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtrip, CU_CxRzRyU3) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("cu", {0, 1}, {M_PI / 4, M_PI / 3, M_PI / 6, 0}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

// ========================================================================
// Basis Translation — Gate Count for Multi-CX Gates
//
// 验证需要 2~3 个 CX 的门在分解后确实产生对应数量的 CX。
// ========================================================================

TEST(TwoQubitBasisGateCount, DCX_NeedsTwoCX) {
  auto u = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") ++cx_count;
  }
  EXPECT_EQ(cx_count, 2);
}

TEST(TwoQubitBasisGateCount, ISWAP_NeedsTwoCX) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") ++cx_count;
  }
  EXPECT_EQ(cx_count, 2);
}

TEST(TwoQubitBasisGateCount, SWAP_NeedsThreeCX) {
  auto u = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") ++cx_count;
  }
  EXPECT_EQ(cx_count, 3);
}

// ========================================================================
// Weyl Decomposition — Parameterized Angle Scans
//
// 对带角度参数的门扫描多个角度，验证 Weyl 坐标与解析公式一致。
// ========================================================================

TEST(TwoQubitWeylParamTest, RZX_VariousAngles) {
  // RZX(theta): a = theta/2, b=c=0
  for (double angle : {M_PI / 8, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("rzx", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "RZX(" << angle << ") should need 1 CX";
    EXPECT_NEAR(d.cx, angle / 2.0, 1e-8)
        << "RZX(" << angle << "): cx mismatch";
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylParamTest, CRX_VariousAngles) {
  // CRX(theta): a = theta/4, b=c=0
  for (double angle : {M_PI / 7, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("crx", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "CRX(" << angle << ")";
    EXPECT_NEAR(d.cx, angle / 4.0, 1e-8);
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylParamTest, CRY_VariousAngles) {
  // CRY(theta): a = theta/4, b=c=0
  for (double angle : {M_PI / 8, M_PI / 5, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("cry", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "CRY(" << angle << ")";
    EXPECT_NEAR(d.cx, angle / 4.0, 1e-8);
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylParamTest, CRZ_VariousAngles) {
  // CRZ(theta): a = theta/4, b=c=0
  for (double angle : {M_PI / 9, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("crz", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "CRZ(" << angle << ")";
    EXPECT_NEAR(d.cx, angle / 4.0, 1e-8);
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylParamTest, CU1_VariousAngles) {
  // CU1(lambda): a = lambda/4, b=c=0
  for (double angle : {M_PI / 8, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("cu1", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "CU1(" << angle << ")";
    EXPECT_NEAR(d.cx, angle / 4.0, 1e-8);
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

TEST(TwoQubitWeylParamTest, CP_VariousAngles) {
  // CP(theta): a = theta/4, b=c=0
  for (double angle : {M_PI / 8, M_PI / 4, M_PI / 3, M_PI / 2}) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate("cp", {0, 1}, {angle}));
    auto d = decompose_two_qubit(m);
    EXPECT_EQ(d.num_cx, 1) << "CP(" << angle << ")";
    EXPECT_NEAR(d.cx, angle / 4.0, 1e-8);
    EXPECT_NEAR(d.cy, 0.0, 1e-8);
    EXPECT_NEAR(d.cz, 0.0, 1e-8);
  }
}

// ========================================================================
// Weyl Decomposition — num_cx Boundaries
//
// 验证 num_cx 在坐标边界处的正确性。
// ========================================================================

TEST(TwoQubitWeylNumCxTest, NumCxIdentityIsZero) {
  auto id = matrix_utils::identity(4);
  EXPECT_EQ(decompose_two_qubit(id).num_cx, 0);
}

TEST(TwoQubitWeylNumCxTest, NumCxSingleCXIsOne) {
  // a=pi/4, b=c=0
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  EXPECT_EQ(decompose_two_qubit(m).num_cx, 1);
}

TEST(TwoQubitWeylNumCxTest, NumCxISWAPIsTwo) {
  // a=b=pi/4, c=0
  auto m = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  EXPECT_EQ(decompose_two_qubit(m).num_cx, 2);
}

TEST(TwoQubitWeylNumCxTest, NumCxSWAPIsThree) {
  // a=b=c=pi/4
  auto m = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  EXPECT_EQ(decompose_two_qubit(m).num_cx, 3);
}

TEST(TwoQubitWeylNumCxTest, NumCxDCXIsTwo) {
  // DCX: a=b=pi/4, c=0
  auto m = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  EXPECT_EQ(decompose_two_qubit(m).num_cx, 2);
}

// ========================================================================
// Basis Translation — Global Phase Invariance
//
// 验证乘以任意全局相位后的酉矩阵，分解重建仍与原矩阵相位等价。
// ========================================================================

TEST(TwoQubitGlobalPhaseTest, CXWithGlobalPhase) {
  auto u0 = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  C phase = std::exp(C(0, 0.7));
  auto u = matrix_utils::scalar_multiply(phase, u0);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitGlobalPhaseTest, RXXWithGlobalPhase) {
  auto u0 = matrix_utils::gate_to_matrix(
      create_gate("rxx", {0, 1}, {M_PI / 3}));
  C phase = std::exp(C(0, -1.3));
  auto u = matrix_utils::scalar_multiply(phase, u0);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitGlobalPhaseTest, ISWAPWithGlobalPhase) {
  auto u0 = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  C phase = std::exp(C(0, 2.1));
  auto u = matrix_utils::scalar_multiply(phase, u0);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

// ========================================================================
// Basis Translation — Custom Qubit Targets Roundtrip
//
// 在非默认 qubit 索引上验证重建一致性。
// ========================================================================

TEST(TwoQubitBasisRoundtripTarget, DCX_CustomQubits) {
  auto u = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 4, 6, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 4 || q == 6) << "Unexpected target: " << q;
    }
  }
  auto reconstructed = reconstruct_2q(gates, 4, 6);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

TEST(TwoQubitBasisRoundtripTarget, CRX_CustomQubits) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("crx", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 1, 8, basis);
  for (const auto& g : gates) {
    for (int q : g->targets) {
      EXPECT_TRUE(q == 1 || q == 8) << "Unexpected target: " << q;
    }
  }
  auto reconstructed = reconstruct_2q(gates, 1, 8);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}

// ========================================================================
// Weyl Decomposition — SU(2) K-Matrix Sanity
//
// decompose_two_qubit 返回的 k1/k2 应是 4x4 酉矩阵（kron(K1l,K1r)，
// 其中 K1l,K1r ∈ SU(2)）。这里只验证它们是良态的（无 NaN/Inf），
// 对一般酉的精确自洽重建见 TwoQubitWeylGeneralUnitary 测试。
// ========================================================================

TEST(TwoQubitKMatrixTest, StandardGates_KMatricesWellConditioned) {
  struct G { const char* name; std::vector<double> args; };
  G gates[] = {
    {"cx", {}}, {"cz", {}}, {"swap", {}}, {"iswap", {}}, {"ecr", {}},
    {"dcx", {}}, {"rxx", {M_PI / 3}}, {"rzx", {M_PI / 4}},
  };
  for (const auto& g : gates) {
    auto m = matrix_utils::gate_to_matrix(
        create_gate(g.name, {0, 1}, g.args));
    auto d = decompose_two_qubit(m);
    for (size_t i = 0; i < d.k1.size(); ++i)
      for (size_t j = 0; j < d.k1[0].size(); ++j) {
        EXPECT_FALSE(std::isnan(d.k1[i][j].real()))
            << g.name << ": NaN in k1 real";
        EXPECT_FALSE(std::isnan(d.k1[i][j].imag()))
            << g.name << ": NaN in k1 imag";
        EXPECT_FALSE(std::isnan(d.k2[i][j].real()))
            << g.name << ": NaN in k2 real";
        EXPECT_FALSE(std::isnan(d.k2[i][j].imag()))
            << g.name << ": NaN in k2 imag";
      }
  }
}

// ========================================================================
// Weyl Decomposition — KAK Self-Consistency for Standard Gates
//
// 验证 U == exp(i*gp) * k1 * exp(i*(a*XX+b*YY+c*ZZ)) * k2。
// 这是 Weyl 分解的核心不变量：分解出的 k1/k2/坐标/global_phase 必须能
// 重建出原矩阵（相差全局相位）。
// ========================================================================

TEST(TwoQubitWeylSelfConsistency, CX_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, SWAP_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, ISWAP_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, DCX_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("dcx", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, RXX_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(
      create_gate("rxx", {0, 1}, {M_PI / 3}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, ECR_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

TEST(TwoQubitWeylSelfConsistency, CZ_RebuildsExactly) {
  auto u = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-8));
}

// ========================================================================
// Weyl Decomposition — KAK Self-Consistency for General Unitaries
//
// 以下用 Haar-随机酉矩阵验证 Weyl 分解的自洽性。这些矩阵的 Weyl 坐标
// a,b,c 均不为零，需要完整 3-CX 的 KAK 重建路径。
//
// 参考矩阵由 scipy.stats.unitary_group.rvs(seed=12345) 生成，与 qiskit
// TwoQubitWeylDecomposition 对照过坐标（a/b/c 一致）。
// ========================================================================

// Haar-random U0 (scipy seed 12345, t=0). qiskit: a=0.7668 b=0.4988 c=0.0991.
TEST(TwoQubitWeylSelfConsistency, GeneralUnitary_U0_Rebuilds) {
  CMatrix u = {
      {C(-0.4999576302408142, 0.2769924246427977),
       C(0.27468624198732094, -0.40774338166142177),
       C(0.21001075897441657, -0.07007369786464485),
       C(-0.6154977174921659, -0.06130322645001683)},
      {C(-0.02645582165157162, 0.4643077541058908),
       C(-0.2708045546378834, -0.07855295865994451),
       C(-0.5363576129011698, -0.021105748596082212),
       C(0.045109065777185126, -0.6434694674146533)},
      {C(0.1267808571702252, -0.055546100028193365),
       C(-0.49288706757206097, 0.13721291368564487),
       C(0.6187539564966393, -0.4261546451822942),
       C(-0.14271290952190152, -0.366394575737759)},
      {C(-0.26664892486064073, 0.6056199794672252),
       C(0.12673881314119922, 0.6332135163031564),
       C(0.27511752919612914, 0.15068616817759511),
       C(0.1933169938224454, 0.09660885623873945)}};
  auto d = decompose_two_qubit(u);
  EXPECT_NEAR(d.cx, 0.76682321, 1e-6);
  EXPECT_NEAR(d.cy, 0.49880360, 1e-6);
  EXPECT_NEAR(d.cz, 0.09910699, 1e-6);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-6));
}

// Haar-random U1 (scipy seed 12345, t=1).
TEST(TwoQubitWeylSelfConsistency, GeneralUnitary_U1_Rebuilds) {
  CMatrix u = {
      {C(-0.6837091740839236, 0.04359253133139244),
       C(-0.394413487801985, 0.05955281340509669),
       C(-0.23969210420766393, 0.498945016445847),
       C(-0.15369697242503952, -0.20374426606102217)},
      {C(0.5360939816669646, 0.3780425855084823),
       C(-0.31935986363116975, 0.13710332431877642),
       C(-0.6447982099310864, 0.13960193142959001),
       C(0.10912354006323657, -0.04168482308523961)},
      {C(0.22308363201859002, 0.21390658019561118),
       C(-0.07181398821574411, -0.6901187639643727),
       C(0.29528366452080984, 0.2549909660277428),
       C(0.04028306253455166, -0.5188650598946573)},
      {C(-0.04716216983073334, -0.05081240654990376),
       C(-0.4450989237392037, 0.2014179977675048),
       C(0.32317372816980255, -0.04115873039078684),
       C(0.80617937461062, -0.021238729361120295)}};
  auto d = decompose_two_qubit(u);
  EXPECT_TRUE(equal_up_to_global_phase(u, rebuild_from_weyl(d), 1e-6));
}

// General-unitary basis roundtrip (decomp3 path).
TEST(TwoQubitBasisRoundtrip, GeneralUnitary_U0_CxRzRyU3) {
  CMatrix u = {
      {C(-0.4999576302408142, 0.2769924246427977),
       C(0.27468624198732094, -0.40774338166142177),
       C(0.21001075897441657, -0.07007369786464485),
       C(-0.6154977174921659, -0.06130322645001683)},
      {C(-0.02645582165157162, 0.4643077541058908),
       C(-0.2708045546378834, -0.07855295865994451),
       C(-0.5363576129011698, -0.021105748596082212),
       C(0.045109065777185126, -0.6434694674146533)},
      {C(0.1267808571702252, -0.055546100028193365),
       C(-0.49288706757206097, 0.13721291368564487),
       C(0.6187539564966393, -0.4261546451822942),
       C(-0.14271290952190152, -0.366394575737759)},
      {C(-0.26664892486064073, 0.6056199794672252),
       C(0.12673881314119922, 0.6332135163031564),
       C(0.27511752919612914, 0.15068616817759511),
       C(0.1933169938224454, 0.09660885623873945)}};
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(u, 0, 1, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6));
}
