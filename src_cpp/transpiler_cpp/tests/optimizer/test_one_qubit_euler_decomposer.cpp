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
#include <random>
#include <set>
#include <string>
#include <vector>

#include "circuit/gate_operation.h"
#include "optimizer/matrix_utils.h"
#include "optimizer/one_qubit_euler_decomposer.h"
#include "test_optimizer_utils.h"

using namespace qcos;
using C = std::complex<double>;

// ========================================================================
// Single-Qubit Euler Decomposition Tests (ZYZ basis)
// ========================================================================

TEST(OneQubitEulerTest, ZYZDecomposeIdentity) {
  auto id = matrix_utils::identity(2);
  auto d = decompose_single_qubit(id);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(id, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeX) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto d = decompose_single_qubit(x);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(x, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeY) {
  auto y = matrix_utils::gate_to_matrix(create_gate("y", {0}));
  auto d = decompose_single_qubit(y);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(y, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeZ) {
  auto z = matrix_utils::gate_to_matrix(create_gate("z", {0}));
  auto d = decompose_single_qubit(z);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(z, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeH) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto d = decompose_single_qubit(h);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(h, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeS) {
  auto s = matrix_utils::gate_to_matrix(create_gate("s", {0}));
  auto d = decompose_single_qubit(s);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(s, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeT) {
  auto t = matrix_utils::gate_to_matrix(create_gate("t", {0}));
  auto d = decompose_single_qubit(t);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(t, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeRX) {
  double angle = M_PI / 3;
  auto rx = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {angle}));
  auto d = decompose_single_qubit(rx);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(rx, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeRY) {
  double angle = 2.0 * M_PI / 5;
  auto ry = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {angle}));
  auto d = decompose_single_qubit(ry);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(ry, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeRZ) {
  double angle = M_PI / 7;
  auto rz = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {angle}));
  auto d = decompose_single_qubit(rz);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(rz, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeU3) {
  auto u3 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.23, -0.45, 2.67}));
  auto d = decompose_single_qubit(u3);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(u3, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposePhaseGate) {
  auto p = matrix_utils::gate_to_matrix(create_gate("p", {0}, {M_PI / 4}));
  auto d = decompose_single_qubit(p);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(p, reconstructed, 1e-8));
}

TEST(OneQubitEulerTest, ZYZDecomposeSX) {
  auto sx = matrix_utils::gate_to_matrix(create_gate("sx", {0}));
  auto d = decompose_single_qubit(sx);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(sx, reconstructed, 1e-8));
}

// ========================================================================
// Single-Qubit Basis Translation Tests
// ========================================================================

TEST(OneQubitBasisTest, RZRyBasisHGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(h, 0, basis);

  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }

  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(OneQubitBasisTest, RZRyBasisXGate) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(x, 0, basis);

  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry");
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(x, product, 1e-8));
}

TEST(OneQubitBasisTest, RZRxBasisHGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(h, 0, basis);

  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "rx")
        << "Unexpected gate: " << g->name;
  }

  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(OneQubitBasisTest, RxRyBasisHGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(h, 0, basis);

  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rx" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }

  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(OneQubitBasisTest, U3BasisProducesSingleGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"u3"};
  auto gates = single_qubit_unitary_to_basis(h, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
}

TEST(OneQubitBasisTest, IdentityProducesNoGates) {
  auto id = matrix_utils::identity(2);
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(id, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(OneQubitBasisTest, QubitTargetPreserved) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(h, 5, basis);
  ASSERT_GT(gates.size(), 0u);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 5);
  }
}

TEST(OneQubitBasisTest, ParameterizedGatesRoundtrip) {
  std::set<std::string> basis = {"rz", "ry"};
  std::vector<std::string> test_gates = {"rx", "ry", "rz"};
  std::vector<double> test_angles = {0.0, M_PI / 6, M_PI / 4, M_PI / 2, M_PI};

  for (const auto& g : test_gates) {
    for (double angle : test_angles) {
      auto op = create_gate(g, {0}, {angle});
      auto m = matrix_utils::gate_to_matrix(op);
      auto gates = single_qubit_unitary_to_basis(m, 0, basis);
      CMatrix product = matrix_utils::identity(2);
      for (const auto& gate : gates) {
        product = matrix_utils::multiply(matrix_utils::gate_to_matrix(gate), product);
      }
      EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
          << "Failed for " << g << "(" << angle << ")";
    }
  }
}

// ========================================================================
// Numerical Stability Tests
// ========================================================================

TEST(NumericalStabilityTest, VerySmallRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {1e-12}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(NumericalStabilityTest, TwoPiRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {2 * M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(NumericalStabilityTest, NegativeAngle) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {-M_PI / 3}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(NumericalStabilityTest, LargeAngle) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {10 * M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(NumericalStabilityTest, AllPaulisRoundtrip) {
  std::vector<std::string> paulis = {"x", "y", "z"};
  for (const auto& p : paulis) {
    auto m = matrix_utils::gate_to_matrix(create_gate(p, {0}));
    auto d = decompose_single_qubit(m);
    auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
    EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8))
        << "Failed for Pauli " << p;
  }
}

TEST(NumericalStabilityTest, AllCliffordsRoundtrip) {
  std::vector<std::string> cliffords = {"h", "s", "sdg", "t", "tdg", "sx", "sxdg"};
  for (const auto& c : cliffords) {
    auto m = matrix_utils::gate_to_matrix(create_gate(c, {0}));
    auto d = decompose_single_qubit(m);
    auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
    EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8))
        << "Failed for Clifford " << c;
  }
}

// ========================================================================
// Multi-Gate Composition Decomposition Tests
//
// 将多个1Q门的矩阵乘积传入分解器，验证分解结果的roundtrip正确性。
// 这是真实使用场景：优化器将一段量子门序列合并为单一酉矩阵后，
// 需要用分解器将其重新分解为目标基门集。
// ========================================================================

static CMatrix compose_gates(
    const std::vector<std::shared_ptr<BaseOperation>>& gates) {
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  return product;
}

TEST(MultiGateCompositionTest, HS) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, SH) {
  auto m = compose_gates({create_gate("s", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HT) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HTH) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HSH) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, THT) {
  auto m = compose_gates({
      create_gate("t", {0}), create_gate("h", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, SHS) {
  auto m = compose_gates({
      create_gate("s", {0}), create_gate("h", {0}), create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HST) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, TSH) {
  auto m = compose_gates({
      create_gate("t", {0}), create_gate("s", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HSTS) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}),
      create_gate("t", {0}), create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HSTHT) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0}),
      create_gate("h", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, XYZ) {
  auto m = compose_gates({
      create_gate("x", {0}), create_gate("y", {0}), create_gate("z", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, ZYX) {
  auto m = compose_gates({
      create_gate("z", {0}), create_gate("y", {0}), create_gate("x", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, XZY) {
  auto m = compose_gates({
      create_gate("x", {0}), create_gate("z", {0}), create_gate("y", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, YXZ) {
  auto m = compose_gates({
      create_gate("y", {0}), create_gate("x", {0}), create_gate("z", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, XX_IsIdentity) {
  auto m = compose_gates({create_gate("x", {0}), create_gate("x", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, HH_IsIdentity) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, SS_IsZ) {
  auto m = compose_gates({create_gate("s", {0}), create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, SdgS_IsIdentity) {
  auto m = compose_gates({
      create_gate("sdg", {0}), create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, TdgT_IsIdentity) {
  auto m = compose_gates({
      create_gate("tdg", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, SxdgSX_IsIdentity) {
  auto m = compose_gates({
      create_gate("sxdg", {0}), create_gate("sx", {0})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RxPi4_RyPi3_RzPi6) {
  auto m = compose_gates({
      create_gate("rx", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 3}),
      create_gate("rz", {0}, {M_PI / 6})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RzPi3_RxPi5_RzPi7) {
  auto m = compose_gates({
      create_gate("rz", {0}, {M_PI / 3}),
      create_gate("rx", {0}, {M_PI / 5}),
      create_gate("rz", {0}, {M_PI / 7})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RyPi2_RzPi4_RyPi2) {
  auto m = compose_gates({
      create_gate("ry", {0}, {M_PI / 2}),
      create_gate("rz", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 2})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RxPi2_RyPi3_RxPi4) {
  auto m = compose_gates({
      create_gate("rx", {0}, {M_PI / 2}),
      create_gate("ry", {0}, {M_PI / 3}),
      create_gate("rx", {0}, {M_PI / 4})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RzPi_RyPi2_RzPi) {
  auto m = compose_gates({
      create_gate("rz", {0}, {M_PI}),
      create_gate("ry", {0}, {M_PI / 2}),
      create_gate("rz", {0}, {M_PI})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, U3_Rz_Ry_Mixed) {
  auto m = compose_gates({
      create_gate("u3", {0}, {0.5, 1.2, -0.3}),
      create_gate("rz", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 6})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, H_SX_T_Mixed) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("sx", {0}),
      create_gate("t", {0}), create_gate("h", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, LongChain_8Gates) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}),
      create_gate("h", {0}), create_gate("s", {0}),
      create_gate("t", {0}), create_gate("h", {0}),
      create_gate("s", {0}), create_gate("t", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, LongChain_16Gates) {
  std::vector<std::shared_ptr<BaseOperation>> chain;
  for (int i = 0; i < 16; ++i) {
    double angle = (i + 1) * M_PI / 17;
    chain.push_back(create_gate("rz", {0}, {angle}));
    chain.push_back(create_gate("ry", {0}, {angle * 0.7}));
  }
  auto m = compose_gates(chain);
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-7));
}

TEST(MultiGateCompositionTest, LongChain_MixedAngles) {
  std::vector<std::shared_ptr<BaseOperation>> chain;
  double angles[] = {0.1234, -0.5678, 1.9876, -2.3456, 3.1415};
  for (double a : angles) {
    chain.push_back(create_gate("rz", {0}, {a}));
    chain.push_back(create_gate("ry", {0}, {a * 0.5}));
    chain.push_back(create_gate("rz", {0}, {-a * 0.3}));
  }
  auto m = compose_gates(chain);
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, RPi_IsX) {
  auto m = compose_gates({create_gate("r", {0}, {M_PI, 0.0})});
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  EXPECT_TRUE(equal_up_to_global_phase(m, x, 1e-8));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, P_Pi4_S) {
  auto m = compose_gates({
      create_gate("p", {0}, {M_PI / 4}),
      create_gate("s", {0})});
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(MultiGateCompositionTest, P_MultiPhase) {
  auto m = compose_gates({
      create_gate("p", {0}, {M_PI / 3}),
      create_gate("p", {0}, {M_PI / 5}),
      create_gate("p", {0}, {M_PI / 7})});
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-8);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

// ========================================================================
// Multi-Gate Composition — Basis Translation Tests
//
// 验证多门组合矩阵通过 single_qubit_unitary_to_basis 后，
// 输出门全部在目标基中且 roundtrip 正确。
// ========================================================================

TEST(MultiGateBasisTest, HS_RzRyBasis) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("s", {0})});
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(MultiGateBasisTest, HTH_RzRxBasis) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}), create_gate("h", {0})});
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "rx")
        << "Unexpected gate: " << g->name;
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(MultiGateBasisTest, XYZ_RxRyBasis) {
  auto m = compose_gates({
      create_gate("x", {0}), create_gate("y", {0}), create_gate("z", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rx" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(MultiGateBasisTest, LongChain_U3Basis) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}),
      create_gate("s", {0}), create_gate("h", {0})});
  std::set<std::string> basis = {"u3"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(MultiGateBasisTest, RxRyRz_RzRyBasis) {
  auto m = compose_gates({
      create_gate("rx", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 3}),
      create_gate("rz", {0}, {M_PI / 6})});
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(MultiGateBasisTest, IdentityChain_ProducesNoGates) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("h", {0}),
      create_gate("s", {0}), create_gate("sdg", {0})});
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(MultiGateBasisTest, LongChain_QubitTargetPreserved) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}), create_gate("s", {0})});
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 7, basis);
  ASSERT_GT(gates.size(), 0u);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 7);
  }
}

TEST(MultiGateBasisTest, AllBasisCombinations) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})});
  std::vector<std::set<std::string>> bases = {
      {"rz", "ry"}, {"rz", "rx"}, {"rx", "ry"}, {"u3"},
      {"rz", "ry", "cx"}, {"rz", "rx", "cx"}, {"rx", "ry", "cx"}};
  for (size_t i = 0; i < bases.size(); ++i) {
    const auto& basis = bases[i];
    auto gates = single_qubit_unitary_to_basis(m, 0, basis);
    for (const auto& g : gates) {
      EXPECT_TRUE(basis.count(g->name) > 0)
          << "Gate '" << g->name << "' not in basis [index " << i << "]";
    }
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates)
      product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
        << "Roundtrip failed for basis index " << i;
  }
}

// ========================================================================
// XYX Basis (rx + ry) — Single Gate Decomposition Tests
//
// 修复了 single_qubit_unitary_to_basis 中 {rx, ry} 分支后，
// 验证各标准门经 Hadamard 共轭 → ZYZ 分解 → XYX 角度调整后
// roundtrip 正确且输出门全部在 {rx, ry} 基中。
// ========================================================================

static void expect_xyx_basis(const CMatrix& u, const std::string& label,
                              double tol = 1e-8) {
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(u, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rx" || g->name == "ry")
        << label << ": unexpected gate '" << g->name << "'";
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(u, product, tol))
      << label << ": roundtrip failed (got " << gates.size() << " gates)";
}

TEST(XYXBasisTest, Identity_NoGates) {
  auto id = matrix_utils::identity(2);
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(id, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(XYXBasisTest, XGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("x", {0})), "X");
}

TEST(XYXBasisTest, YGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("y", {0})), "Y");
}

TEST(XYXBasisTest, ZGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("z", {0})), "Z");
}

TEST(XYXBasisTest, HGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("h", {0})), "H");
}

TEST(XYXBasisTest, SGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("s", {0})), "S");
}

TEST(XYXBasisTest, SdgGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("sdg", {0})), "Sdg");
}

TEST(XYXBasisTest, TGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("t", {0})), "T");
}

TEST(XYXBasisTest, TdgGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("tdg", {0})), "Tdg");
}

TEST(XYXBasisTest, SXGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("sx", {0})), "SX");
}

TEST(XYXBasisTest, SXdgGate_Roundtrip) {
  expect_xyx_basis(matrix_utils::gate_to_matrix(create_gate("sxdg", {0})), "SXdg");
}

TEST(XYXBasisTest, U3Gate_Roundtrip) {
  auto u3 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.23, -0.45, 2.67}));
  expect_xyx_basis(u3, "U3(1.23,-0.45,2.67)");
}

TEST(XYXBasisTest, U3Gate_FullParams) {
  auto u3 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 3, M_PI / 5, M_PI / 7}));
  expect_xyx_basis(u3, "U3(pi/3,pi/5,pi/7)");
}

// ========================================================================
// XYX Basis — Parameterized Gate Roundtrip
// ========================================================================

TEST(XYXBasisTest, RX_VariousAngles) {
  for (double angle : {M_PI / 7, M_PI / 4, M_PI / 3, M_PI / 2, M_PI, 2.5}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {angle}));
    expect_xyx_basis(m, "RX(" + std::to_string(angle) + ")");
  }
}

TEST(XYXBasisTest, RY_VariousAngles) {
  for (double angle : {M_PI / 7, M_PI / 4, M_PI / 3, M_PI / 2, M_PI, 2.5}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {angle}));
    expect_xyx_basis(m, "RY(" + std::to_string(angle) + ")");
  }
}

TEST(XYXBasisTest, RZ_VariousAngles) {
  for (double angle : {M_PI / 7, M_PI / 4, M_PI / 3, M_PI / 2, M_PI, 2.5}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {angle}));
    expect_xyx_basis(m, "RZ(" + std::to_string(angle) + ")");
  }
}

TEST(XYXBasisTest, PhaseGate_VariousAngles) {
  for (double angle : {M_PI / 6, M_PI / 4, M_PI / 3, M_PI / 2, M_PI}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("p", {0}, {angle}));
    expect_xyx_basis(m, "P(" + std::to_string(angle) + ")");
  }
}

// ========================================================================
// XYX Basis — Inverse Pair Identity (theta=0 special case)
// ========================================================================

TEST(XYXBasisTest, XX_IsIdentity_NoGates) {
  auto m = compose_gates({create_gate("x", {0}), create_gate("x", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(XYXBasisTest, HH_IsIdentity_NoGates) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("h", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(XYXBasisTest, SdgS_IsIdentity_NoGates) {
  auto m = compose_gates({create_gate("sdg", {0}), create_gate("s", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(XYXBasisTest, TdgT_IsIdentity_NoGates) {
  auto m = compose_gates({create_gate("tdg", {0}), create_gate("t", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(XYXBasisTest, SXdgSX_IsIdentity_NoGates) {
  auto m = compose_gates({create_gate("sxdg", {0}), create_gate("sx", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

// ========================================================================
// XYX Basis — Multi-Gate Composition Roundtrip
// ========================================================================

TEST(XYXBasisTest, HS_Roundtrip) {
  auto m = compose_gates({create_gate("h", {0}), create_gate("s", {0})});
  expect_xyx_basis(m, "H·S");
}

TEST(XYXBasisTest, SH_Roundtrip) {
  auto m = compose_gates({create_gate("s", {0}), create_gate("h", {0})});
  expect_xyx_basis(m, "S·H");
}

TEST(XYXBasisTest, HTH_Roundtrip) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}), create_gate("h", {0})});
  expect_xyx_basis(m, "H·T·H");
}

TEST(XYXBasisTest, HSH_Roundtrip) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("h", {0})});
  expect_xyx_basis(m, "H·S·H");
}

TEST(XYXBasisTest, THT_Roundtrip) {
  auto m = compose_gates({
      create_gate("t", {0}), create_gate("h", {0}), create_gate("t", {0})});
  expect_xyx_basis(m, "T·H·T");
}

TEST(XYXBasisTest, HST_Roundtrip) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})});
  expect_xyx_basis(m, "H·S·T");
}

TEST(XYXBasisTest, TSH_Roundtrip) {
  auto m = compose_gates({
      create_gate("t", {0}), create_gate("s", {0}), create_gate("h", {0})});
  expect_xyx_basis(m, "T·S·H");
}

TEST(XYXBasisTest, HSTHT_Roundtrip) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0}),
      create_gate("h", {0}), create_gate("t", {0})});
  expect_xyx_basis(m, "H·S·T·H·T");
}

TEST(XYXBasisTest, XYZ_Roundtrip) {
  auto m = compose_gates({
      create_gate("x", {0}), create_gate("y", {0}), create_gate("z", {0})});
  expect_xyx_basis(m, "X·Y·Z");
}

TEST(XYXBasisTest, ZYX_Roundtrip) {
  auto m = compose_gates({
      create_gate("z", {0}), create_gate("y", {0}), create_gate("x", {0})});
  expect_xyx_basis(m, "Z·Y·X");
}

TEST(XYXBasisTest, XZY_Roundtrip) {
  auto m = compose_gates({
      create_gate("x", {0}), create_gate("z", {0}), create_gate("y", {0})});
  expect_xyx_basis(m, "X·Z·Y");
}

TEST(XYXBasisTest, YXZ_Roundtrip) {
  auto m = compose_gates({
      create_gate("y", {0}), create_gate("x", {0}), create_gate("z", {0})});
  expect_xyx_basis(m, "Y·X·Z");
}

TEST(XYXBasisTest, RxRyRz_Roundtrip) {
  auto m = compose_gates({
      create_gate("rx", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 3}),
      create_gate("rz", {0}, {M_PI / 6})});
  expect_xyx_basis(m, "RX·RY·RZ");
}

TEST(XYXBasisTest, RzRxRz_Roundtrip) {
  auto m = compose_gates({
      create_gate("rz", {0}, {M_PI / 3}),
      create_gate("rx", {0}, {M_PI / 5}),
      create_gate("rz", {0}, {M_PI / 7})});
  expect_xyx_basis(m, "RZ·RX·RZ");
}

TEST(XYXBasisTest, U3_Rz_Ry_Mixed_Roundtrip) {
  auto m = compose_gates({
      create_gate("u3", {0}, {0.5, 1.2, -0.3}),
      create_gate("rz", {0}, {M_PI / 4}),
      create_gate("ry", {0}, {M_PI / 6})});
  expect_xyx_basis(m, "U3·RZ·RY");
}

TEST(XYXBasisTest, LongChain_8Gates_Roundtrip) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}),
      create_gate("h", {0}), create_gate("s", {0}),
      create_gate("t", {0}), create_gate("h", {0}),
      create_gate("s", {0}), create_gate("t", {0})});
  expect_xyx_basis(m, "8-gate chain");
}

TEST(XYXBasisTest, LongChain_16Gates_Roundtrip) {
  std::vector<std::shared_ptr<BaseOperation>> chain;
  for (int i = 0; i < 16; ++i) {
    double angle = (i + 1) * M_PI / 17;
    chain.push_back(create_gate("rz", {0}, {angle}));
    chain.push_back(create_gate("ry", {0}, {angle * 0.7}));
  }
  auto m = compose_gates(chain);
  expect_xyx_basis(m, "16-gate chain", 1e-7);
}

TEST(XYXBasisTest, LongChain_MixedAngles_Roundtrip) {
  std::vector<std::shared_ptr<BaseOperation>> chain;
  double angles[] = {0.1234, -0.5678, 1.9876, -2.3456, 3.1415};
  for (double a : angles) {
    chain.push_back(create_gate("rz", {0}, {a}));
    chain.push_back(create_gate("ry", {0}, {a * 0.5}));
    chain.push_back(create_gate("rz", {0}, {-a * 0.3}));
  }
  auto m = compose_gates(chain);
  expect_xyx_basis(m, "mixed-angle chain");
}

// ========================================================================
// XYX Basis — Qubit Target & Edge Cases
// ========================================================================

TEST(XYXBasisTest, QubitTargetPreserved) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})});
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 7, basis);
  ASSERT_GT(gates.size(), 0u);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 7);
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(XYXBasisTest, SmallRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {1e-10}));
  expect_xyx_basis(m, "small RX", 1e-6);
}

TEST(XYXBasisTest, NegativeAngles) {
  for (double angle : {-M_PI / 7, -M_PI / 3, -2.5}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {angle}));
    expect_xyx_basis(m, "RY(" + std::to_string(angle) + ")");
  }
}

TEST(XYXBasisTest, LargeAngles) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {10 * M_PI}));
  expect_xyx_basis(m, "RX(10pi)");
}

TEST(XYXBasisTest, TwoPiRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {2 * M_PI}));
  expect_xyx_basis(m, "RY(2pi)");
}

// ========================================================================
// XYX Basis — Gate Count Optimization
// ========================================================================

TEST(XYXBasisTest, XGate_OptimalGateCount) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(x, 0, basis);
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "rx");
}

TEST(XYXBasisTest, YGate_OptimalGateCount) {
  auto y = matrix_utils::gate_to_matrix(create_gate("y", {0}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(y, 0, basis);
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "ry");
}

TEST(XYXBasisTest, PurePhaseGate_ThetaZero) {
  // P(θ) = diag(1, e^{iθ}), after Hadamard conjugation theta may be non-zero
  // so the gate count is not necessarily 1 (unlike ZYZ basis)
  auto m = matrix_utils::gate_to_matrix(create_gate("p", {0}, {M_PI / 4}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_LE(gates.size(), 3u);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(XYXBasisTest, PureRY_NoOuterRX) {
  // Pure RY gate should produce a single RY gate
  auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {M_PI / 3}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "ry");
}

TEST(XYXBasisTest, PureRX_NoOuterRY) {
  // Pure RX gate should produce a single RX gate
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI / 5}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "rx");
}

// ========================================================================
// ZXZ Basis ({rz, rx}) — Dedicated Branch Coverage
//
// 覆盖 single_qubit_unitary_to_basis 中 {rz, rx} 分支的各子路径:
//   theta≈0 合并外层 RZ、一般 ZZX→ZXZ 角度映射、
//   以及 lam/phi ≡ -π (mod 2π) 的 theta 取反特殊路径。
// ========================================================================

static void expect_zxz_basis(const CMatrix& u, const std::string& label,
                              double tol = 1e-8) {
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(u, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "rx")
        << label << ": unexpected gate '" << g->name << "'";
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(u, product, tol))
      << label << ": roundtrip failed (got " << gates.size() << " gates)";
}

TEST(ZXZBasisTest, Identity_NoGates) {
  auto id = matrix_utils::identity(2);
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(id, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(ZXZBasisTest, PureRZ_ThetaZeroMerged) {
  // theta=0 => the two outer RZ gates collapse into a single RZ.
  auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {M_PI / 4}));
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "rz");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(ZXZBasisTest, PureRX_SingleGate) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI / 3}));
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "rx");
}

TEST(ZXZBasisTest, PureRY_Roundtrip) {
  // RY is not a native gate in {rz,rx}; must decompose to a 3-gate sequence.
  auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {M_PI / 3}));
  expect_zxz_basis(m, "RY(pi/3)");
}

TEST(ZXZBasisTest, HGate_Roundtrip) {
  expect_zxz_basis(matrix_utils::gate_to_matrix(create_gate("h", {0})), "H");
}

TEST(ZXZBasisTest, StandardGatesRoundtrip) {
  std::vector<std::string> gates = {"h", "s", "sdg", "t", "tdg", "sx", "sxdg"};
  for (const auto& g : gates) {
    auto m = matrix_utils::gate_to_matrix(create_gate(g, {0}));
    expect_zxz_basis(m, g);
  }
}

TEST(ZXZBasisTest, ParameterizedGatesRoundtrip) {
  std::vector<std::string> test_gates = {"rx", "ry", "rz"};
  std::vector<double> test_angles = {0.0, M_PI / 6, M_PI / 4, M_PI / 2, M_PI};
  for (const auto& g : test_gates) {
    for (double angle : test_angles) {
      auto m = matrix_utils::gate_to_matrix(create_gate(g, {0}, {angle}));
      expect_zxz_basis(m, g + "(" + std::to_string(angle) + ")");
    }
  }
}

TEST(ZXZBasisTest, U3_Roundtrip) {
  auto u3 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.23, -0.45, 2.67}));
  expect_zxz_basis(u3, "U3(1.23,-0.45,2.67)");
}

TEST(ZXZBasisTest, MultiGateComposition) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("t", {0}),
      create_gate("h", {0}), create_gate("s", {0})});
  expect_zxz_basis(m, "H·T·H·S");
}

TEST(ZXZBasisTest, QubitTargetPreserved) {
  auto m = compose_gates({
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})});
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = single_qubit_unitary_to_basis(m, 9, basis);
  ASSERT_GT(gates.size(), 0u);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 9);
  }
}

// ========================================================================
// U-Gate Basis ({u}) and Fallback Coverage
//
// 覆盖 has_gate("u") 分支 (第 94-98 行)、无 basis_gates (nullopt) 默认路径、
// 以及不匹配任何基时的 U3 fallback (第 218-220 行)。
// ========================================================================

TEST(UBasisTest, UGateBasisProducesSingleUGate) {
  // basis = {"u"} => should emit a single U gate (not U3).
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"u"};
  auto gates = single_qubit_unitary_to_basis(h, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(UBasisTest, UGateBasisParameterized) {
  for (double th : {M_PI / 5, M_PI / 2, M_PI}) {
    auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {th}));
    std::set<std::string> basis = {"u"};
    auto gates = single_qubit_unitary_to_basis(m, 0, basis);
    ASSERT_EQ(gates.size(), 1u);
    EXPECT_EQ(gates[0]->name, "u");
    CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
    EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
        << "Failed for RX(" << th << ")";
  }
}

TEST(UBasisTest, UGateBasisIdentity) {
  auto id = matrix_utils::identity(2);
  std::set<std::string> basis = {"u"};
  auto gates = single_qubit_unitary_to_basis(id, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(UBasisTest, UPreferredOverRotationsWhenBothPresent) {
  // When basis contains both "u" and rotation gates, "u" takes priority
  // (has_gate("u") is checked before the rz/ry/rx branches).
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"u", "rz", "ry", "rx"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u");
}

TEST(U3PriorityTest, U3PreferredOverUWhenBothPresent) {
  // has_gate("u3") is checked first; "u" is only reached if u3 is absent.
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"u3", "u"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
}

TEST(FallbackBasisTest, NoBasisGatesNullopt_ProducesU3) {
  // std::nullopt => has_gate returns true for everything; u3 is matched first.
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = single_qubit_unitary_to_basis(h, 0, std::nullopt);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(FallbackBasisTest, UnrecognizedBasis_ProducesU3Fallback) {
  // A basis set that matches no supported branch falls through to the
  // U3 fallback at the end of single_qubit_unitary_to_basis.
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"p", "swap"};  // none of these are recognized
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(FallbackBasisTest, EmptyBasisSet_ProducesU3Fallback) {
  // Empty basis set => has_gate always false => U3 fallback.
  auto m = matrix_utils::gate_to_matrix(create_gate("u3", {0}, {0.5, 1.2, -0.3}));
  std::set<std::string> basis = {};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
}

TEST(FallbackBasisTest, IdentityWithUnrecognizedBasis_NoGates) {
  auto id = matrix_utils::identity(2);
  std::set<std::string> basis = {"p", "swap"};
  auto gates = single_qubit_unitary_to_basis(id, 0, basis);
  EXPECT_EQ(gates.size(), 0u);
}

// ========================================================================
// Decomposer Angle Branch Coverage
//
// 直接验证 decompose_single_qubit 对 theta=π (X/Y 门) 和 theta=0 (Z/S/T 门)
// 的特殊角度返回值，以及 ZYZ/ZXZ/XYX 基在 theta=π 时的门合并行为。
// ========================================================================

TEST(DecomposerBranchTest, XGate_ThetaIsPi) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto d = decompose_single_qubit(x);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
}

TEST(DecomposerBranchTest, YGate_ThetaIsPi) {
  auto y = matrix_utils::gate_to_matrix(create_gate("y", {0}));
  auto d = decompose_single_qubit(y);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
}

TEST(DecomposerBranchTest, ZGate_ThetaIsZero) {
  auto z = matrix_utils::gate_to_matrix(create_gate("z", {0}));
  auto d = decompose_single_qubit(z);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(DecomposerBranchTest, SGate_ThetaIsZero) {
  auto s = matrix_utils::gate_to_matrix(create_gate("s", {0}));
  auto d = decompose_single_qubit(s);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(DecomposerBranchTest, ZYZ_ThetaPiBranch_XGate) {
  // X gate: theta=pi => ZYZ theta-pi branch.
  // decompose_single_qubit(X) gives phi=-pi, lambda=0, so lam2=lambda-phi=pi
  // is non-zero => emits RZ(pi).RY(pi) (2 gates, not 1).
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(x, 0, basis);
  EXPECT_LE(gates.size(), 2u);
  // Must contain an RY(pi).
  bool has_ry_pi = false;
  for (const auto& g : gates) {
    if (g->name == "ry" && std::abs(std::abs(g->arg_value[0]) - M_PI) < 1e-10)
      has_ry_pi = true;
  }
  EXPECT_TRUE(has_ry_pi);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(x, product, 1e-8));
}

TEST(DecomposerBranchTest, ZYZ_ThetaPiBranch_YGate) {
  // Y gate: theta=pi => ZYZ emits RZ.RY(pi) (two gates).
  auto y = matrix_utils::gate_to_matrix(create_gate("y", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(y, 0, basis);
  EXPECT_LE(gates.size(), 2u);
  // Must contain an RY(pi).
  bool has_ry_pi = false;
  for (const auto& g : gates) {
    if (g->name == "ry" && std::abs(std::abs(g->arg_value[0]) - M_PI) < 1e-10)
      has_ry_pi = true;
  }
  EXPECT_TRUE(has_ry_pi);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(y, product, 1e-8));
}

TEST(DecomposerBranchTest, ThetaFlipBranch_LambdaNearMinusPi) {
  // Construct a U3 whose ZYZ lambda ≡ -π (mod 2π) to trigger the
  // is_zero_angle(lambda+pi) theta-flip branch (line 123-127).
  // U3(theta, phi, lambda) with lambda = pi: lambda+pi ≡ 0 (mod 2pi).
  double theta = M_PI / 3;
  double phi = 0.0;
  double lambda = M_PI;  // triggers lam+pi ≡ 0
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {theta, phi, lambda}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(DecomposerBranchTest, ThetaFlipBranch_PhiNearMinusPi) {
  // Construct a U3 whose ZYZ phi ≡ -π (mod 2π) to trigger the
  // is_zero_angle(phi+pi) theta-flip branch.
  double theta = M_PI / 4;
  double phi = M_PI;  // phi+pi ≡ 0 (mod 2pi)
  double lambda = 0.0;
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {theta, phi, lambda}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(DecomposerBranchTest, ZXZ_ThetaFlipBranch) {
  // Same theta-flip coverage but in the ZXZ ({rz,rx}) branch.
  double theta = M_PI / 5;
  double phi = 0.0;
  double lambda = M_PI;
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {theta, phi, lambda}));
  expect_zxz_basis(m, "ZXZ theta-flip");
}

TEST(DecomposerBranchTest, XYX_ThetaFlipBranch) {
  // Theta-flip coverage in the XYX ({rx,ry}) branch.
  double theta = M_PI / 6;
  double phi = M_PI;
  double lambda = 0.0;
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {theta, phi, lambda}));
  expect_xyx_basis(m, "XYX theta-flip");
}

// ========================================================================
// mod_2pi Boundary & Angle Wrapping Tests
//
// 验证分解器对超出 [−π, π] 范围的角度、以及边界值 ±π 的处理。
// ========================================================================

TEST(AngleWrappingTest, LargeAnglesRoundtrip) {
  // U3 with angles outside [-pi, pi] — mod_2pi should wrap them.
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {7.0, -5.0, 11.0}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(AngleWrappingTest, ExactlyPiAngles) {
  // Boundary: theta = pi, phi = pi, lambda = pi.
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI, M_PI, M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(AngleWrappingTest, NegativePiAngles) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {-M_PI, -M_PI, -M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(AngleWrappingTest, TwoPiEquivalentToZero) {
  // U3(theta, 2pi, 2pi) ≡ U3(theta, 0, 0) up to global phase.
  auto m1 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 3, 2 * M_PI, 2 * M_PI}));
  auto m2 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 3, 0.0, 0.0}));
  EXPECT_TRUE(equal_up_to_global_phase(m1, m2, 1e-8));
}

TEST(AngleWrappingTest, ZYZBasisWrappedAnglesRoundtrip) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 3, 3 * M_PI, -3 * M_PI}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry");
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

// ========================================================================
// Global Phase Extraction
//
// 验证 decompose_single_qubit 提取的 phase 能正确重建带任意全局相位
// 的酉矩阵。
// ========================================================================

TEST(GlobalPhaseTest, ArbitraryGlobalPhasePreserved) {
  // U3 * e^{i*alpha} should decompose to the same ZYZ angles but with
  // phase shifted by alpha.
  double alpha = 0.7;
  auto base = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 3, 0.5, -0.3}));
  auto phased = matrix_utils::scalar_multiply(std::exp(C(0, alpha)), base);
  auto d = decompose_single_qubit(phased);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(phased, reconstructed, 1e-8));
}

TEST(GlobalPhaseTest, NegativeGlobalPhase) {
  double alpha = -1.23;
  auto base = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {M_PI / 4, 1.0, -0.7}));
  auto phased = matrix_utils::scalar_multiply(std::exp(C(0, alpha)), base);
  auto d = decompose_single_qubit(phased);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(phased, reconstructed, 1e-8));
}

TEST(GlobalPhaseTest, IdentityWithGlobalPhase) {
  // e^{i*alpha} * I should give theta=0 and a non-zero phase.
  double alpha = 0.5;
  auto phased = matrix_utils::scalar_multiply(std::exp(C(0, alpha)),
                                               matrix_utils::identity(2));
  auto d = decompose_single_qubit(phased);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(phased, reconstructed, 1e-8));
}

// ========================================================================
// Haar-Random 1Q Unitary Stress Test
//
// 生成大量随机 2x2 酉矩阵，验证 ZYZ 分解 + 三种基的 roundtrip。
// 这是真实优化器场景的端到端覆盖。
// ========================================================================

static CMatrix haar_random_unitary_1q(std::mt19937_64& rng) {
  std::normal_distribution<double> dist(0.0, 1.0);
  CMatrix A(2, std::vector<C>(2));
  for (int i = 0; i < 2; ++i)
    for (int j = 0; j < 2; ++j)
      A[i][j] = C(dist(rng), dist(rng));
  // Modified Gram-Schmidt
  CMatrix Q(2, std::vector<C>(2));
  for (int j = 0; j < 2; ++j) {
    for (int i = 0; i < 2; ++i) Q[i][j] = A[i][j];
    for (int k = 0; k < j; ++k) {
      C dot = C(0, 0);
      for (int i = 0; i < 2; ++i) dot += std::conj(Q[i][k]) * Q[i][j];
      for (int i = 0; i < 2; ++i) Q[i][j] -= dot * Q[i][k];
    }
    double norm = 0.0;
    for (int i = 0; i < 2; ++i) norm += std::norm(Q[i][j]);
    norm = std::sqrt(norm);
    if (norm < 1e-15) continue;
    for (int i = 0; i < 2; ++i) Q[i][j] /= norm;
  }
  return Q;
}

TEST(OneQubitHaarStressTest, ZYZDecomposition_200Samples) {
  std::mt19937_64 rng(20260814);
  for (int i = 0; i < 200; ++i) {
    auto u = haar_random_unitary_1q(rng);
    auto d = decompose_single_qubit(u);
    auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
    EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-7))
        << "ZYZ roundtrip failed at sample " << i;
  }
}

TEST(OneQubitHaarStressTest, RzRyBasis_200Samples) {
  std::mt19937_64 rng(777);
  std::set<std::string> basis = {"rz", "ry"};
  for (int i = 0; i < 200; ++i) {
    auto u = haar_random_unitary_1q(rng);
    auto gates = single_qubit_unitary_to_basis(u, 0, basis);
    for (const auto& g : gates) {
      EXPECT_TRUE(g->name == "rz" || g->name == "ry")
          << "sample " << i << ": unexpected gate " << g->name;
    }
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates)
      product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    EXPECT_TRUE(equal_up_to_global_phase(u, product, 1e-7))
        << "RzRy basis roundtrip failed at sample " << i;
  }
}

TEST(OneQubitHaarStressTest, RzRxBasis_200Samples) {
  std::mt19937_64 rng(88888);
  std::set<std::string> basis = {"rz", "rx"};
  for (int i = 0; i < 200; ++i) {
    auto u = haar_random_unitary_1q(rng);
    auto gates = single_qubit_unitary_to_basis(u, 0, basis);
    for (const auto& g : gates) {
      EXPECT_TRUE(g->name == "rz" || g->name == "rx")
          << "sample " << i << ": unexpected gate " << g->name;
    }
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates)
      product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    EXPECT_TRUE(equal_up_to_global_phase(u, product, 1e-7))
        << "RzRx basis roundtrip failed at sample " << i;
  }
}

TEST(OneQubitHaarStressTest, RxRyBasis_200Samples) {
  std::mt19937_64 rng(42);
  std::set<std::string> basis = {"rx", "ry"};
  for (int i = 0; i < 200; ++i) {
    auto u = haar_random_unitary_1q(rng);
    auto gates = single_qubit_unitary_to_basis(u, 0, basis);
    for (const auto& g : gates) {
      EXPECT_TRUE(g->name == "rx" || g->name == "ry")
          << "sample " << i << ": unexpected gate " << g->name;
    }
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates)
      product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    EXPECT_TRUE(equal_up_to_global_phase(u, product, 1e-7))
        << "RxRy basis roundtrip failed at sample " << i;
  }
}

TEST(OneQubitHaarStressTest, U3Basis_200Samples) {
  std::mt19937_64 rng(1314);
  std::set<std::string> basis = {"u3"};
  for (int i = 0; i < 200; ++i) {
    auto u = haar_random_unitary_1q(rng);
    auto gates = single_qubit_unitary_to_basis(u, 0, basis);
    ASSERT_EQ(gates.size(), 1u);
    EXPECT_EQ(gates[0]->name, "u3");
    CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
    EXPECT_TRUE(equal_up_to_global_phase(u, product, 1e-7))
        << "U3 basis roundtrip failed at sample " << i;
  }
}
