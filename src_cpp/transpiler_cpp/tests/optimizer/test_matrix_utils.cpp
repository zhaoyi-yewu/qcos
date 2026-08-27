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
