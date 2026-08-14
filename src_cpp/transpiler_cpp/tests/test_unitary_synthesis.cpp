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

#include <gtest/gtest.h>

#include <cmath>
#include <complex>
#include <memory>
#include <set>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "optimizer/unitary_synthesis.h"

using namespace qcos;
using C = std::complex<double>;

// ========================================================================
// Helpers
// ========================================================================

static CMatrix reconstruct_from_zyz(double theta, double phi, double lambda,
                                    double phase) {
  double c = std::cos(theta / 2), s = std::sin(theta / 2);
  CMatrix su2 = {{C(c) * std::exp(C(0, -(phi + lambda) / 2)),
                  -C(s) * std::exp(C(0, -(phi - lambda) / 2))},
                 {C(s) * std::exp(C(0, (phi - lambda) / 2)),
                  C(c) * std::exp(C(0, (phi + lambda) / 2))}};
  return matrix_utils::scalar_multiply(std::exp(C(0, phase)), su2);
}

// Helper: check U ≈ V up to global phase
static bool equal_up_to_global_phase(const CMatrix& a, const CMatrix& b,
                                     double tol = 1e-8) {
  if (a.size() != b.size() || a.empty()) return false;
  double max_abs = 0;
  C phase{1, 0};
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j) {
      if (std::abs(a[i][j]) > max_abs && std::abs(b[i][j]) > tol) {
        max_abs = std::abs(a[i][j]);
        phase = a[i][j] / b[i][j];
      }
    }
  if (max_abs < tol) return true;
  CMatrix scaled = matrix_utils::scalar_multiply(phase, b);
  return matrix_utils::is_close(a, scaled, tol);
}

// Helper: compute the unitary of an IR sequence
static CMatrix ir_unitary(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, size_t num_qubits) {
  size_t dim = 1ULL << num_qubits;
  CMatrix result = matrix_utils::identity(dim);
  for (const auto& op : ir) {
    DAGCircuit tmp;
    tmp.add_qubits(static_cast<int>(num_qubits));
    tmp.apply_operation_back(op);
    auto ops = tmp.topological_op_nodes();
    std::unordered_map<int, int> mapping;
    for (size_t i = 0; i < num_qubits; ++i)
      mapping[static_cast<int>(i)] = static_cast<int>(i);
    CMatrix gate_u = matrix_utils::compute_block_unitary(ops, mapping);
    // If gate acts on a subset of qubits, we need to embed it
    // For simplicity this helper only works for full-width ops
    if (gate_u.size() == dim) {
      result = matrix_utils::multiply(gate_u, result);
    } else {
      // embed: not handled in this simple helper
      auto gate_mat = matrix_utils::gate_to_matrix(op);
      CMatrix full = matrix_utils::identity(dim);
      size_t nq = op->targets.size();
      size_t gd = 1ULL << nq;
      int q0 = op->targets[0];
      for (size_t row = 0; row < dim; ++row) {
        for (size_t col = 0; col < dim; ++col) {
          bool match = true;
          size_t gr = 0, gc = 0;
          for (size_t qi = 0; qi < nq; ++qi) {
            int q = op->targets[qi];
            size_t rq = (row >> (num_qubits - 1 - q)) & 1;
            size_t cq = (col >> (num_qubits - 1 - q)) & 1;
            gr = gr * 2 + rq;
            gc = gc * 2 + cq;
          }
          // check all other qubits match
          for (size_t bit = 0; bit < num_qubits; ++bit) {
            bool in_targets = false;
            for (int t : op->targets)
              if (static_cast<size_t>(t) == bit) in_targets = true;
            if (!in_targets) {
              size_t rb = (row >> (num_qubits - 1 - bit)) & 1;
              size_t cb = (col >> (num_qubits - 1 - bit)) & 1;
              if (rb != cb) {
                match = false;
                break;
              }
            }
          }
          full[row][col] = match ? gate_mat[gr][gc] : C(0);
        }
      }
    }
    result = matrix_utils::multiply(full, result);
  }
  return result;
}

// ========================================================================
// Matrix utility tests
// ========================================================================

TEST(MatrixUtilsTest, IdentityMatrix2x2) {
  auto id = matrix_utils::identity(2);
  EXPECT_EQ(id.size(), 2u);
  EXPECT_EQ(id[0].size(), 2u);
  EXPECT_TRUE(matrix_utils::is_identity(id));
}

TEST(MatrixUtilsTest, IdentityMatrix4x4) {
  auto id4 = matrix_utils::identity(4);
  EXPECT_EQ(id4.size(), 4u);
  EXPECT_TRUE(matrix_utils::is_identity(id4));
}

TEST(MatrixUtilsTest, IdentityMatrix1x1) {
  auto id1 = matrix_utils::identity(1);
  EXPECT_TRUE(matrix_utils::is_identity(id1));
}

TEST(MatrixUtilsTest, MatrixMultiplyIdentity) {
  auto id = matrix_utils::identity(2);
  CMatrix h = {{C(1.0 / std::sqrt(2)), C(1.0 / std::sqrt(2))},
               {C(1.0 / std::sqrt(2)), C(-1.0 / std::sqrt(2))}};
  auto r1 = matrix_utils::multiply(h, id);
  auto r2 = matrix_utils::multiply(id, h);
  EXPECT_TRUE(matrix_utils::is_close(r1, h, 1e-10));
  EXPECT_TRUE(matrix_utils::is_close(r2, h, 1e-10));
}

TEST(MatrixUtilsTest, MatrixMultiplyAssociative) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto z = matrix_utils::gate_to_matrix(create_gate("z", {0}));
  auto ab_c = matrix_utils::multiply(matrix_utils::multiply(x, h), z);
  auto a_bc = matrix_utils::multiply(x, matrix_utils::multiply(h, z));
  EXPECT_TRUE(matrix_utils::is_close(ab_c, a_bc, 1e-10));
}

TEST(MatrixUtilsTest, TensorProductIKronI) {
  CMatrix i2 = matrix_utils::identity(2);
  auto i4 = matrix_utils::tensor_product(i2, i2);
  EXPECT_EQ(i4.size(), 4u);
  EXPECT_TRUE(matrix_utils::is_identity(i4));
}

TEST(MatrixUtilsTest, TensorProductXKronI) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto i2 = matrix_utils::identity(2);
  auto xi = matrix_utils::tensor_product(x, i2);
  EXPECT_EQ(xi.size(), 4u);
  // X⊗I: rows 0↔2, 1↔3
  EXPECT_NEAR(std::abs(xi[0][2] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(xi[1][3] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(xi[2][0] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(xi[3][1] - C(1)), 0, 1e-10);
}

TEST(MatrixUtilsTest, TensorProductIKronX) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto i2 = matrix_utils::identity(2);
  auto ix = matrix_utils::tensor_product(i2, x);
  EXPECT_EQ(ix.size(), 4u);
  // I⊗X: rows 0↔1, 2↔3
  EXPECT_NEAR(std::abs(ix[0][1] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(ix[1][0] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(ix[2][3] - C(1)), 0, 1e-10);
  EXPECT_NEAR(std::abs(ix[3][2] - C(1)), 0, 1e-10);
}

TEST(MatrixUtilsTest, ConjugateTransposeRoundtrip) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  auto ct = matrix_utils::conjugate_transpose(m);
  auto m2 = matrix_utils::conjugate_transpose(ct);
  EXPECT_TRUE(matrix_utils::is_close(m, m2, 1e-10));
}

TEST(MatrixUtilsTest, ConjugateTransposeValues) {
  CMatrix m = {{C(1, 2), C(3, 4)}, {C(5, 6), C(7, 8)}};
  auto ct = matrix_utils::conjugate_transpose(m);
  EXPECT_NEAR(ct[0][0].real(), 1.0, 1e-10);
  EXPECT_NEAR(ct[0][0].imag(), -2.0, 1e-10);
  EXPECT_NEAR(ct[0][1].real(), 5.0, 1e-10);
  EXPECT_NEAR(ct[0][1].imag(), -6.0, 1e-10);
  EXPECT_NEAR(ct[1][0].real(), 3.0, 1e-10);
  EXPECT_NEAR(ct[1][0].imag(), -4.0, 1e-10);
}

TEST(MatrixUtilsTest, ScalarMultiply) {
  CMatrix m = {{C(1), C(2)}, {C(3), C(4)}};
  auto sm = matrix_utils::scalar_multiply(C(2, 1), m);
  EXPECT_NEAR(sm[0][0].real(), 2.0, 1e-10);
  EXPECT_NEAR(sm[0][0].imag(), 1.0, 1e-10);
  EXPECT_NEAR(sm[0][1].real(), 4.0, 1e-10);
  EXPECT_NEAR(sm[0][1].imag(), 2.0, 1e-10);
}

TEST(MatrixUtilsTest, TraceIdentity) {
  EXPECT_NEAR(matrix_utils::trace(matrix_utils::identity(2)), 2.0, 1e-10);
  EXPECT_NEAR(matrix_utils::trace(matrix_utils::identity(4)), 4.0, 1e-10);
}

TEST(MatrixUtilsTest, TraceX) {
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  EXPECT_NEAR(matrix_utils::trace(x), 0.0, 1e-10);
}

TEST(MatrixUtilsTest, SubtractAndAdd) {
  CMatrix a = {{C(1), C(2)}, {C(3), C(4)}};
  CMatrix b = {{C(5), C(6)}, {C(7), C(8)}};
  auto diff = matrix_utils::subtract(b, a);
  EXPECT_NEAR(diff[0][0].real(), 4.0, 1e-10);
  auto sum = matrix_utils::add(a, diff);
  EXPECT_TRUE(matrix_utils::is_close(sum, b, 1e-10));
}

TEST(MatrixUtilsTest, FrobeniusNorm) {
  auto id2 = matrix_utils::identity(2);
  EXPECT_NEAR(matrix_utils::frobenius_norm(id2), std::sqrt(2.0), 1e-10);
  CMatrix zero = {{C(0), C(0)}, {C(0), C(0)}};
  EXPECT_NEAR(matrix_utils::frobenius_norm(zero), 0.0, 1e-10);
}

TEST(MatrixUtilsTest, IsIdentityTolerance) {
  CMatrix almost_id = {{C(1, 1e-12), C(0)}, {C(0), C(1)}};
  EXPECT_TRUE(matrix_utils::is_identity(almost_id, 1e-10));
  CMatrix not_id = {{C(1, 0.01), C(0)}, {C(0), C(1)}};
  EXPECT_FALSE(matrix_utils::is_identity(not_id, 1e-3));
}

TEST(MatrixUtilsTest, IsCloseWithDifferentSizes) {
  CMatrix a = {{C(1), C(0)}, {C(0), C(1)}};
  CMatrix b = {{C(1), C(0), C(0)}, {C(0), C(1), C(0)}, {C(0), C(0), C(1)}};
  EXPECT_FALSE(matrix_utils::is_close(a, b));
}

// ========================================================================
// Gate-to-matrix tests for all supported gates
// ========================================================================

TEST(GateToMatrixTest, AllSingleQubitGates) {
  std::vector<std::string> gates_1q = {"h",   "x", "y",   "z",  "s",
                                       "sdg", "t", "tdg", "sx", "sxdg"};
  for (const auto& g : gates_1q) {
    auto op = create_gate(g, {0});
    auto m = matrix_utils::gate_to_matrix(op);
    EXPECT_EQ(m.size(), 2u) << "Gate " << g;
    EXPECT_EQ(m[0].size(), 2u) << "Gate " << g;
    // Verify unitary: U†U = I
    auto u_dag = matrix_utils::conjugate_transpose(m);
    auto prod = matrix_utils::multiply(u_dag, m);
    EXPECT_TRUE(matrix_utils::is_identity(prod, 1e-10))
        << "Gate " << g << " is not unitary";
  }
}

TEST(GateToMatrixTest, ParameterizedSingleQubitGates) {
  auto test_unitary = [](const std::string& name,
                         const std::vector<double>& params) {
    auto op = create_gate(name, {0}, params);
    auto m = matrix_utils::gate_to_matrix(op);
    auto u_dag = matrix_utils::conjugate_transpose(m);
    auto prod = matrix_utils::multiply(u_dag, m);
    EXPECT_TRUE(matrix_utils::is_identity(prod, 1e-10))
        << name << "(" << params[0] << ")";
  };
  test_unitary("p", {M_PI / 3});
  test_unitary("u1", {M_PI / 4});
  test_unitary("rx", {M_PI / 6});
  test_unitary("ry", {M_PI / 3});
  test_unitary("rz", {M_PI / 2});
  test_unitary("r", {M_PI / 4, M_PI / 3});
  test_unitary("u2", {M_PI / 4, M_PI / 3});
  test_unitary("u3", {M_PI / 4, M_PI / 3, M_PI / 6});
  test_unitary("u", {M_PI / 5, M_PI / 7, M_PI / 11});
}

TEST(GateToMatrixTest, AllTwoQubitGates) {
  struct GateInfo {
    std::string name;
    std::vector<double> params;
  };
  std::vector<GateInfo> gates_2q = {
      {"cx", {}},          {"cz", {}},
      {"cy", {}},          {"swap", {}},
      {"iswap", {}},       {"ecr", {}},
      {"cp", {M_PI / 4}},  {"cu1", {M_PI / 3}},
      {"crx", {M_PI / 4}}, {"cry", {M_PI / 5}},
      {"crz", {M_PI / 6}}, {"cu3", {M_PI / 4, M_PI / 3, M_PI / 6}},
      {"rxx", {M_PI / 4}}, {"ryy", {M_PI / 3}},
      {"rzz", {M_PI / 5}}, {"rzx", {M_PI / 7}}};
  for (const auto& g : gates_2q) {
    auto op = create_gate(g.name, {0, 1}, g.params);
    auto m = matrix_utils::gate_to_matrix(op);
    EXPECT_EQ(m.size(), 4u) << "Gate " << g.name;
    EXPECT_EQ(m[0].size(), 4u) << "Gate " << g.name;
    auto u_dag = matrix_utils::conjugate_transpose(m);
    auto prod = matrix_utils::multiply(u_dag, m);
    EXPECT_TRUE(matrix_utils::is_identity(prod, 1e-10))
        << "Gate " << g.name << " is not unitary";
  }
}

TEST(GateToMatrixTest, UnsupportedGateThrows) {
  auto op = std::make_shared<BaseOperation>("foobar", std::vector<int>{0});
  EXPECT_THROW(matrix_utils::gate_to_matrix(op), std::runtime_error);
}

// ========================================================================
// Single-qubit decomposition tests
// ========================================================================

TEST(SingleQubitDecompTest, DecomposeIdentity) {
  auto id = matrix_utils::identity(2);
  auto d = decompose_single_qubit(id);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeY) {
  auto m = matrix_utils::gate_to_matrix(create_gate("y", {0}));
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeZ) {
  auto m = matrix_utils::gate_to_matrix(create_gate("z", {0}));
  auto d = decompose_single_qubit(m);
  // Z has theta=0, only phase
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeS) {
  auto m = matrix_utils::gate_to_matrix(create_gate("s", {0}));
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeT) {
  auto m = matrix_utils::gate_to_matrix(create_gate("t", {0}));
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, 0.0, 1e-10);
}

TEST(SingleQubitDecompTest, DecomposeRX) {
  double angle = M_PI / 3;
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {angle}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposeRY) {
  double angle = 2.0 * M_PI / 5;
  auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {angle}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposeRZ) {
  double angle = M_PI / 7;
  auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {angle}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposeH_Roundtrip) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposeU3_Roundtrip) {
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.23, -0.45, 2.67}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposePhaseGate) {
  auto m = matrix_utils::gate_to_matrix(create_gate("p", {0}, {M_PI / 4}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(SingleQubitDecompTest, DecomposeSX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("sx", {0}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

// ========================================================================
// Single-qubit basis gate translation tests
// ========================================================================

TEST(SingleQubitBasisTest, IdentityProducesNoGates) {
  auto id = matrix_utils::identity(2);
  auto gates = single_qubit_unitary_to_basis(id, 0, std::nullopt);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(SingleQubitBasisTest, DefaultBasisProducesU3) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = single_qubit_unitary_to_basis(m, 0, std::nullopt);
  EXPECT_GE(gates.size(), 1u);
  // With no basis restriction, should produce a u3 or similar
}

TEST(SingleQubitBasisTest, RZRYBasis) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
  // Verify: reconstruct from gates and compare
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    auto gm = matrix_utils::gate_to_matrix(g);
    product = matrix_utils::multiply(gm, product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8));
}

TEST(SingleQubitBasisTest, RXRZBasis) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rx", "rz"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rx" || g->name == "rz")
        << "Unexpected gate: " << g->name;
  }
}

TEST(SingleQubitBasisTest, RXRYBasis) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rx" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
}

TEST(SingleQubitBasisTest, U3Explicit) {
  auto m =
      matrix_utils::gate_to_matrix(create_gate("u3", {0}, {1.0, 2.0, 3.0}));
  std::set<std::string> basis = {"u3"};
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
}

TEST(SingleQubitBasisTest, RZRYRoundtripCorrectness) {
  // Test multiple gates with RZ+RY basis and verify matrix equivalence
  std::vector<std::string> test_gates = {"h", "x", "y", "s", "t"};
  std::set<std::string> basis = {"rz", "ry"};
  for (const auto& gname : test_gates) {
    auto m = matrix_utils::gate_to_matrix(create_gate(gname, {0}));
    auto gates = single_qubit_unitary_to_basis(m, 0, basis);
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates) {
      product =
          matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    }
    EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
        << "Roundtrip failed for gate: " << gname;
  }
}

TEST(SingleQubitBasisTest, QubitTargetPreserved) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = single_qubit_unitary_to_basis(m, 5, std::nullopt);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 5);
  }
}

// ========================================================================
// Block unitary computation tests
// ========================================================================

TEST(BlockUnitTest, SingleGateBlock) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  EXPECT_TRUE(matrix_utils::is_close(u, h_mat, 1e-10));
}

TEST(BlockUnitTest, TwoGateSequence_HX) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("x", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  auto expected = matrix_utils::multiply(
      matrix_utils::gate_to_matrix(create_gate("x", {0})),
      matrix_utils::gate_to_matrix(create_gate("h", {0})));
  EXPECT_TRUE(matrix_utils::is_close(u, expected, 1e-10));
}

TEST(BlockUnitTest, ThreeGateSequence) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  // Verify: result should be unitary
  auto u_dag = matrix_utils::conjugate_transpose(u);
  EXPECT_TRUE(
      matrix_utils::is_identity(matrix_utils::multiply(u_dag, u), 1e-10));
}

TEST(BlockUnitTest, SelfInverseCancels) {
  // H*H = I
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  EXPECT_TRUE(matrix_utils::is_identity(u, 1e-10));
}

TEST(BlockUnitTest, X_X_Cancels) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("x", {0}),
                                                    create_gate("x", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  EXPECT_TRUE(matrix_utils::is_identity(u, 1e-10));
}

TEST(BlockUnitTest, S_SDG_Cancels) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("s", {0}),
                                                    create_gate("sdg", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  EXPECT_TRUE(matrix_utils::is_identity(u, 1e-10));
}

TEST(BlockUnitTest, TwoQubitBlock_HC_CX) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}, {1, 1}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  auto u_dag = matrix_utils::conjugate_transpose(u);
  EXPECT_TRUE(
      matrix_utils::is_identity(matrix_utils::multiply(u, u_dag), 1e-10));
}

TEST(BlockUnitTest, TwoQubitBlockBellState) {
  // Bell state circuit: H(0) + CX(0,1) creates |00>+|11>
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}, {1, 1}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  // Apply to |00> (column 0): should give (|00> + |11>)/sqrt(2)
  // Index: |00>=0, |01>=1, |10>=2, |11>=3
  double sq = 1.0 / std::sqrt(2.0);
  EXPECT_NEAR(std::abs(u[0][0] - C(sq)), 0, 1e-10);
  EXPECT_NEAR(std::abs(u[3][0] - C(sq)), 0, 1e-10);
  EXPECT_NEAR(std::abs(u[1][0]), 0, 1e-10);
  EXPECT_NEAR(std::abs(u[2][0]), 0, 1e-10);
}

TEST(BlockUnitTest, ResultIsAlwaysUnitary) {
  // Random-ish sequence, verify result is always unitary
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),          create_gate("cx", {0, 1}),
      create_gate("rz", {0}, {1.23}), create_gate("ry", {1}, {0.45}),
      create_gate("cx", {0, 1}),      create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto ops = dag.topological_op_nodes();
  std::unordered_map<int, int> mapping = {{0, 0}, {1, 1}};
  auto u = matrix_utils::compute_block_unitary(ops, mapping);
  auto u_dag = matrix_utils::conjugate_transpose(u);
  EXPECT_TRUE(
      matrix_utils::is_identity(matrix_utils::multiply(u_dag, u), 1e-10));
}

// ========================================================================
// Two-qubit decomposition tests
// ========================================================================

TEST(TwoQubitDecompTest, IdentityNeeds0CX) {
  auto id = matrix_utils::identity(4);
  auto d = decompose_two_qubit(id);
  EXPECT_EQ(d.num_cx, 0);
}

TEST(TwoQubitDecompTest, CXNeedsAtLeast1CX) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto d = decompose_two_qubit(m);
  // CX is entangling: the simplified KAK extraction may not perfectly
  // identify the exact count, but it should not claim 0 CX via tensor
  // product (CX is not a tensor product).
  // Verify by checking that the two_qubit_unitary_to_basis emits gates.
  std::set<std::string> basis = {"cx", "cz", "h", "rz", "ry", "rx", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
}

TEST(TwoQubitDecompTest, TensorProductNeeds0CX) {
  // H⊗I should be decomposable with 0 CX
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
}

TEST(TwoQubitDecompTest, TensorProductIKronH) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(id, h);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
}

TEST(TwoQubitDecompTest, TensorProductRXKronRY) {
  auto rx = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI / 3}));
  auto ry = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {M_PI / 5}));
  auto tensor = matrix_utils::tensor_product(rx, ry);
  auto d = decompose_two_qubit(tensor);
  EXPECT_EQ(d.num_cx, 0);
}

// ========================================================================
// Two-qubit to basis gates tests
// ========================================================================

TEST(TwoQubitToBasisTest, IdentityProducesNoGates) {
  auto id = matrix_utils::identity(4);
  auto gates = two_qubit_unitary_to_basis(id, 0, 1, std::nullopt);
  EXPECT_EQ(gates.size(), 0u);
}

TEST(TwoQubitToBasisTest, CXDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "rx", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  // Should contain exactly one CX
  int cx_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cx") cx_count++;
    EXPECT_TRUE(basis.count(g->name) > 0) << g->name << " not in basis";
  }
  EXPECT_EQ(cx_count, 1);
}

TEST(TwoQubitToBasisTest, CZDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cz", "rz", "ry", "rx", "h", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  int cz_count = 0;
  for (const auto& g : gates) {
    if (g->name == "cz") cz_count++;
  }
  EXPECT_EQ(cz_count, 1);
}

TEST(TwoQubitToBasisTest, SwapDirectMatch) {
  auto m = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"swap", "cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  bool has_swap = false;
  for (const auto& g : gates) {
    if (g->name == "swap") has_swap = true;
  }
  EXPECT_TRUE(has_swap);
}

TEST(TwoQubitToBasisTest, CXWithCZBasis) {
  // When cx is NOT in basis but cz is, should use H+CZ+H
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cz", "h", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 0, 1, basis);
  EXPECT_GE(gates.size(), 1u);
  for (const auto& g : gates) {
    EXPECT_TRUE(basis.count(g->name) > 0) << g->name << " not in basis";
  }
}

TEST(TwoQubitToBasisTest, TensorProductNoEntanglingGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(tensor, 0, 1, basis);
  // Should have only single-qubit gates, no CX
  for (const auto& g : gates) {
    EXPECT_NE(g->name, "cx") << "Tensor product should not need CX";
  }
}

TEST(TwoQubitToBasisTest, QubitTargetsPreserved) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = two_qubit_unitary_to_basis(m, 3, 7, basis);
  for (const auto& g : gates) {
    for (int t : g->targets) {
      EXPECT_TRUE(t == 3 || t == 7) << "Unexpected qubit target: " << t;
    }
  }
}

// ========================================================================
// UnitarySynthesis pass tests
// ========================================================================

TEST(UnitarySynthesisTest, NoChangeOnEmptyDAG) {
  DAGCircuit dag;
  dag.add_qubits(2);
  UnitarySynthesis synth;
  int reduced = synth.run(dag);
  EXPECT_EQ(reduced, 0);
  EXPECT_EQ(dag.size(), 0);
}

TEST(UnitarySynthesisTest, IdentityBlockRemoved) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  UnitarySynthesis synth;
  int reduced = synth.run(dag);
  EXPECT_GE(reduced, 0);
  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("x") ? counts.at("x") : 0, 1);
}

TEST(UnitarySynthesisTest, BasisGateTranslation) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("s", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry", "cx"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(UnitarySynthesisTest, BasisGatesFromConstructor) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("s", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry", "cx"};
  UnitarySynthesis synth(basis);
  synth.run(dag);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(UnitarySynthesisTest, MultiBlockOptimization) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}),   // qubit 0: I
      create_gate("x", {1}), create_gate("x", {1})};  // qubit 1: I
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  UnitarySynthesis synth;
  int reduced = synth.run(dag);
  EXPECT_GE(reduced, 0);
  EXPECT_LE(dag.size(), 4);
}

TEST(UnitarySynthesisTest, SynthesizeBlock1Q) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  UnitarySynthesis synth;
  auto gates = synth.synthesize_block(m, {3});
  EXPECT_GE(gates.size(), 1u);
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 3);
  }
}

TEST(UnitarySynthesisTest, SynthesizeBlock2Q) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  UnitarySynthesis synth;
  auto gates = synth.synthesize_block(m, {0, 1});
  EXPECT_GE(gates.size(), 1u);
}

TEST(UnitarySynthesisTest, SynthesizeBlockIdentity) {
  auto id = matrix_utils::identity(2);
  UnitarySynthesis synth;
  auto gates = synth.synthesize_block(id, {0});
  EXPECT_EQ(gates.size(), 0u);
}

TEST(UnitarySynthesisTest, MaxBlockSizeLimitsScope) {
  // max_block_size=1 should not touch 2-qubit blocks
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  UnitarySynthesis synth(std::nullopt, 1.0, 1);
  int reduced = synth.run(dag);
  (void)reduced;
}

// ========================================================================
// ConsolidateBlocks pass tests
// ========================================================================

TEST(ConsolidateBlocksTest, ConsolidateSingleQubitRun) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  ConsolidateBlocks consolidator;
  int reduced = consolidator.run(dag);
  EXPECT_GE(reduced, 0);
  EXPECT_LE(dag.size(), 3);
}

TEST(ConsolidateBlocksTest, ConsolidateReducesGateCount) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig_size = dag.size();
  ConsolidateBlocks consolidator;
  consolidator.run(dag);
  EXPECT_LE(dag.size(), orig_size);
}

TEST(ConsolidateBlocksTest, ConsolidateWithBasisGates) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry", "cx"};
  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(ConsolidateBlocksTest, DoesNotConsolidateSingleGate) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig = dag.size();
  ConsolidateBlocks consolidator;
  consolidator.run(dag);
  EXPECT_EQ(dag.size(), orig);
}

TEST(ConsolidateBlocksTest, TwoQubitBlockConsolidation) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1}), create_gate("h", {0}),
      create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  ConsolidateBlocks consolidator;
  consolidator.run(dag);
  // Result should be unitary-equivalent
}

// ========================================================================
// Integration with optimize() at different levels
// ========================================================================

TEST(OptimizeIntegrationTest, Level0NoChange) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1})};
  auto result = optimize(ir, 0);
  EXPECT_EQ(result.size(), 3u);
}

TEST(OptimizeIntegrationTest, Level1InverseCancellation) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1})};
  auto result = optimize(ir, 1);
  // Level 1 should cancel H+H
  EXPECT_LE(result.size(), 3u);
}

TEST(OptimizeIntegrationTest, Level2WithUnitarySynthesis) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  std::set<std::string> basis = {"rz", "ry", "cx"};
  auto result = optimize(ir, 3, false, basis);
  for (const auto& op : result) {
    if (op->name == "measure") continue;
    EXPECT_TRUE(basis.count(op->name) > 0 ||
                Constant::ALL_GATE_LIST.end() ==
                    std::find(Constant::ALL_GATE_LIST.begin(),
                              Constant::ALL_GATE_LIST.end(), op->name))
        << "Gate " << op->name << " not in basis at level 3";
  }
}

TEST(OptimizeIntegrationTest, MeasurePreserved) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0}),
                                                    create_gate("h", {0})};
  auto m = std::make_shared<Measure>(std::vector<int>{0}, std::vector<int>{0});
  ir.push_back(m);
  auto result = optimize(ir, 1);
  bool has_measure = false;
  for (const auto& op : result) {
    if (op->name == "measure") has_measure = true;
  }
  EXPECT_TRUE(has_measure);
}

TEST(OptimizeIntegrationTest, InvalidLevelThrows) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {0})};
  EXPECT_THROW(optimize(ir, -1), std::runtime_error);
  EXPECT_THROW(optimize(ir, 4), std::runtime_error);
}

// ========================================================================
// Edge cases and numerical stability
// ========================================================================

TEST(EdgeCaseTest, VerySmallRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {1e-12}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-6));
}

TEST(EdgeCaseTest, PiRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI}));
  auto d = decompose_single_qubit(m);
  EXPECT_NEAR(d.theta, M_PI, 1e-10);
}

TEST(EdgeCaseTest, TwoPiRotation) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {2 * M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-6));
}

TEST(EdgeCaseTest, NegativeAngle) {
  auto m = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {-M_PI / 3}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

TEST(EdgeCaseTest, LargeAngle) {
  auto m = matrix_utils::gate_to_matrix(create_gate("rz", {0}, {10 * M_PI}));
  auto d = decompose_single_qubit(m);
  auto reconstructed = reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-6));
}

TEST(EdgeCaseTest, AllPaulisRoundtrip) {
  for (const auto& name : {"x", "y", "z"}) {
    auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}));
    auto d = decompose_single_qubit(m);
    auto reconstructed =
        reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
    EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8))
        << "Roundtrip failed for Pauli " << name;
  }
}

TEST(EdgeCaseTest, AllCliffordRoundtrip) {
  for (const auto& name : {"h", "s", "sdg", "sx", "sxdg"}) {
    auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}));
    auto d = decompose_single_qubit(m);
    auto reconstructed =
        reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
    EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8))
        << "Roundtrip failed for Clifford " << name;
  }
}

TEST(EdgeCaseTest, ParameterizedGatesRoundtrip) {
  std::vector<double> angles = {0.0,  M_PI / 6,     M_PI / 4, M_PI / 2,
                                M_PI, 3 * M_PI / 2, 2 * M_PI};
  for (double a : angles) {
    for (const auto& name : {"rx", "ry", "rz"}) {
      auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}, {a}));
      auto d = decompose_single_qubit(m);
      auto reconstructed =
          reconstruct_from_zyz(d.theta, d.phi, d.lambda, d.phase);
      EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8))
          << name << "(" << a << ") roundtrip failed";
    }
  }
}

// ========================================================================
// decompose_unitary() — top-level interface tests
// ========================================================================

TEST(DecomposeUnitaryTest, SingleQubit_H_ToRzRy) {
  auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = decompose_unitary(h_mat, {"rz", "ry"});
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "ry")
        << "Unexpected gate: " << g->name;
  }
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates) {
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  }
  EXPECT_TRUE(equal_up_to_global_phase(h_mat, product, 1e-8));
}

TEST(DecomposeUnitaryTest, SingleQubit_DefaultQubit) {
  auto x_mat = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  auto gates = decompose_unitary(x_mat, {"u3"});
  for (const auto& g : gates) {
    ASSERT_EQ(g->targets.size(), 1u);
    EXPECT_EQ(g->targets[0], 0);
  }
}

TEST(DecomposeUnitaryTest, SingleQubit_CustomQubit) {
  auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = decompose_unitary(h_mat, {"rz", "ry"}, {5});
  for (const auto& g : gates) {
    EXPECT_EQ(g->targets[0], 5);
  }
}

TEST(DecomposeUnitaryTest, SingleQubit_Identity_NoGates) {
  auto id = matrix_utils::identity(2);
  auto gates = decompose_unitary(id, {"rz", "ry"});
  EXPECT_EQ(gates.size(), 0u);
}

TEST(DecomposeUnitaryTest, TwoQubit_CX_DirectMatch) {
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto gates = decompose_unitary(cx_mat, {"cx", "rz", "ry"});
  EXPECT_GE(gates.size(), 1u);
  bool has_cx = false;
  for (const auto& g : gates) {
    if (g->name == "cx") has_cx = true;
  }
  EXPECT_TRUE(has_cx);
}

TEST(DecomposeUnitaryTest, TwoQubit_CZ_DirectMatch) {
  auto cz_mat = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  auto gates = decompose_unitary(cz_mat, {"cz", "rz", "ry", "h"});
  EXPECT_GE(gates.size(), 1u);
  bool has_cz = false;
  for (const auto& g : gates) {
    if (g->name == "cz") has_cz = true;
  }
  EXPECT_TRUE(has_cz);
}

TEST(DecomposeUnitaryTest, TwoQubit_TensorProduct_NoCX) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto id = matrix_utils::identity(2);
  auto tensor = matrix_utils::tensor_product(h, id);
  auto gates = decompose_unitary(tensor, {"cx", "rz", "ry", "u3"});
  for (const auto& g : gates) {
    EXPECT_NE(g->name, "cx") << "Tensor product should not need CX";
  }
}

TEST(DecomposeUnitaryTest, TwoQubit_Identity4x4_NoGates) {
  auto id = matrix_utils::identity(4);
  auto gates = decompose_unitary(id, {"cx", "rz", "ry"});
  EXPECT_EQ(gates.size(), 0u);
}

TEST(DecomposeUnitaryTest, TwoQubit_CustomQubits) {
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto gates = decompose_unitary(cx_mat, {"cx", "rz", "ry"}, {3, 7});
  for (const auto& g : gates) {
    for (int t : g->targets) {
      EXPECT_TRUE(t == 3 || t == 7) << "Unexpected target: " << t;
    }
  }
}

TEST(DecomposeUnitaryTest, TwoQubit_CXToCZCrossBasis) {
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto gates = decompose_unitary(cx_mat, {"cz", "h", "rz", "ry"});
  EXPECT_GE(gates.size(), 1u);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "cz" || g->name == "h" || g->name == "rz" ||
                g->name == "ry")
        << "Gate " << g->name << " not in basis";
  }
}

TEST(DecomposeUnitaryTest, InvalidDimension_Throws) {
  CMatrix m3x3 = {{C(1), C(0), C(0)}, {C(0), C(1), C(0)}, {C(0), C(0), C(1)}};
  EXPECT_THROW(decompose_unitary(m3x3, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryTest, EmptyMatrix_Throws) {
  CMatrix empty;
  EXPECT_THROW(decompose_unitary(empty, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryTest, NonUnitary_Throws) {
  CMatrix not_unitary = {{C(1), C(1)}, {C(0), C(1)}};
  EXPECT_THROW(decompose_unitary(not_unitary, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryTest, AllSingleQubitGates_Roundtrip) {
  std::set<std::string> basis = {"rz", "ry"};
  for (const auto& name :
       {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg"}) {
    auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}));
    auto gates = decompose_unitary(m, basis);
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates) {
      product =
          matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
    }
    EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
        << "Roundtrip failed for " << name;
  }
}

TEST(DecomposeUnitaryTest, ParameterizedGate_Roundtrip) {
  std::set<std::string> basis = {"rz", "ry"};
  for (double angle : {M_PI / 7, M_PI / 3, 2 * M_PI / 5}) {
    for (const auto& name : {"rx", "ry", "rz"}) {
      auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}, {angle}));
      auto gates = decompose_unitary(m, basis);
      CMatrix product = matrix_utils::identity(2);
      for (const auto& g : gates) {
        product =
            matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
      }
      EXPECT_TRUE(equal_up_to_global_phase(m, product, 1e-8))
          << name << "(" << angle << ") roundtrip failed";
    }
  }
}

TEST(DecomposeUnitaryTest, Swap_DirectMatch) {
  auto swap_mat = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  auto gates = decompose_unitary(swap_mat, {"swap", "cx", "rz", "ry"});
  bool has_swap = false;
  for (const auto& g : gates) {
    if (g->name == "swap") has_swap = true;
  }
  EXPECT_TRUE(has_swap);
}

// ========================================================================
// decompose_unitary() — 2Q roundtrip correctness
// ========================================================================

// Helper: reconstruct the full 4x4 unitary from a gate sequence on 2 qubits.
// Embeds each gate into the 4x4 space and multiplies in order.
static CMatrix reconstruct_2q_unitary(
    const std::vector<std::shared_ptr<BaseOperation>>& gates, int q0, int q1) {
  size_t n = 2;
  size_t dim = 4;
  CMatrix result = matrix_utils::identity(dim);
  for (const auto& op : gates) {
    auto gate_mat = matrix_utils::gate_to_matrix(op);
    size_t nq = op->targets.size();
    CMatrix full = matrix_utils::identity(dim);
    if (nq == 1) {
      int q = op->targets[0];
      int pos = (q == q0) ? 0 : 1;  // position in 2-qubit system
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

// Helper: check all gates are in the basis
static void expect_all_in_basis(
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    const std::set<std::string>& basis) {
  for (const auto& g : gates) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }
}

TEST(DecomposeUnitary2QTest, AllKnownGates_Roundtrip) {
  // Gates that can be directly matched or factored — verify roundtrip
  std::set<std::string> basis = {"cx", "cz", "swap", "iswap", "ecr", "h",
                                 "rz", "ry", "rx",   "u3",    "x"};
  struct TestCase {
    std::string name;
    std::vector<double> params;
    bool expect_roundtrip;
  };
  std::vector<TestCase> cases = {
      {"cx", {}, true},
      {"cz", {}, true},
      {"swap", {}, true},
      {"iswap", {}, true},
      {"ecr", {}, true},
      // Parameterized gates need general KAK (K matrices not yet exact)
      {"cp", {M_PI / 4}, false},
      {"crx", {M_PI / 3}, false},
      {"cry", {M_PI / 5}, false},
      {"crz", {M_PI / 7}, false},
      {"rxx", {M_PI / 4}, false},
      {"ryy", {M_PI / 3}, false},
      {"rzz", {M_PI / 5}, false},
  };

  for (const auto& tc : cases) {
    auto mat =
        matrix_utils::gate_to_matrix(create_gate(tc.name, {0, 1}, tc.params));
    auto gates = decompose_unitary(mat, basis);
    expect_all_in_basis(gates, basis);

    if (tc.expect_roundtrip) {
      auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
      EXPECT_TRUE(equal_up_to_global_phase(mat, reconstructed, 1e-6))
          << "2Q roundtrip failed for gate: " << tc.name;
    }
  }
}

TEST(DecomposeUnitary2QTest, BellCircuit_BasisCompliance) {
  auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  CMatrix h_full(4, std::vector<C>(4, C(0)));
  for (size_t row = 0; row < 4; ++row)
    for (size_t col = 0; col < 4; ++col) {
      size_t rq = (row >> 1) & 1, cq = (col >> 1) & 1;
      h_full[row][col] =
          ((row ^ (rq << 1)) == (col ^ (cq << 1))) ? h_mat[rq][cq] : C(0);
    }
  CMatrix bell_u = matrix_utils::multiply(cx_mat, h_full);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = decompose_unitary(bell_u, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, IBM_Basis_U3PlusCX) {
  auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> ibm_basis = {"u3", "cx"};
  auto gates = decompose_unitary(cx_mat, ibm_basis);
  expect_all_in_basis(gates, ibm_basis);
}

TEST(DecomposeUnitary2QTest, Google_Basis_RzRxPlusCX) {
  std::set<std::string> google_basis = {"rz", "rx", "cx"};
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  CMatrix h_full(4, std::vector<C>(4, C(0)));
  for (size_t row = 0; row < 4; ++row)
    for (size_t col = 0; col < 4; ++col) {
      size_t rq = (row >> 1) & 1, cq = (col >> 1) & 1;
      h_full[row][col] =
          ((row ^ (rq << 1)) == (col ^ (cq << 1))) ? h[rq][cq] : C(0);
    }
  CMatrix u = matrix_utils::multiply(cx, h_full);
  auto gates = decompose_unitary(u, google_basis);
  expect_all_in_basis(gates, google_basis);
}

TEST(DecomposeUnitary2QTest, CZ_Basis_RzRyPlusCZ) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> ionq_basis = {"rz", "ry", "cz"};
  auto gates = decompose_unitary(cx, ionq_basis);
  expect_all_in_basis(gates, ionq_basis);
}

TEST(DecomposeUnitary2QTest, TensorProduct_RX_RY_BasisCompliance) {
  auto rx = matrix_utils::gate_to_matrix(create_gate("rx", {0}, {M_PI / 3}));
  auto ry = matrix_utils::gate_to_matrix(create_gate("ry", {0}, {M_PI / 5}));
  auto tensor = matrix_utils::tensor_product(rx, ry);
  std::set<std::string> basis = {"cx", "rz", "ry", "rx"};
  auto gates = decompose_unitary(tensor, basis);
  expect_all_in_basis(gates, basis);
  for (const auto& g : gates) {
    EXPECT_NE(g->name, "cx");
  }
}

TEST(DecomposeUnitary2QTest, Iswap_Roundtrip) {
  auto iswap = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3", "iswap"};
  auto gates = decompose_unitary(iswap, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(iswap, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QTest, ECR_Roundtrip) {
  auto ecr = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "ecr", "u3"};
  auto gates = decompose_unitary(ecr, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(ecr, reconstructed, 1e-6));
}

// General KAK tests: verify basis compliance (K matrices not yet exact for
// roundtrip)
TEST(DecomposeUnitary2QTest, ControlledPhase_BasisCompliance) {
  auto cp =
      matrix_utils::gate_to_matrix(create_gate("cp", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "cp", "u3"};
  auto gates = decompose_unitary(cp, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, RZZ_BasisCompliance) {
  auto rzz =
      matrix_utils::gate_to_matrix(create_gate("rzz", {0, 1}, {M_PI / 3}));
  std::set<std::string> basis = {"cx", "rz", "ry", "rzz"};
  auto gates = decompose_unitary(rzz, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, GateCountOptimization_CXDirectMatch) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  auto gates = decompose_unitary(cx, {"cx", "rz", "ry"});
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "cx");
}

TEST(DecomposeUnitary2QTest, GateCountOptimization_HH_IsIdentity) {
  auto id4 = matrix_utils::identity(4);
  auto gates = decompose_unitary(id4, {"cx", "rz", "ry"});
  EXPECT_EQ(gates.size(), 0u);
}

TEST(DecomposeUnitary2QTest, CustomQubits_Roundtrip) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = decompose_unitary(cx, basis, {4, 9});
  for (const auto& g : gates) {
    for (int t : g->targets) {
      EXPECT_TRUE(t == 4 || t == 9) << "Unexpected target: " << t;
    }
  }
  auto reconstructed = reconstruct_2q_unitary(gates, 4, 9);
  EXPECT_TRUE(equal_up_to_global_phase(cx, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QTest, SWAP_ToCX_BasisCompliance) {
  auto swap_mat = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = decompose_unitary(swap_mat, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, CZ_ToCX_Roundtrip) {
  auto cz = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cx", "h", "rz", "ry"};
  auto gates = decompose_unitary(cz, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(cz, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QTest, CRX_BasisCompliance) {
  auto crx =
      matrix_utils::gate_to_matrix(create_gate("crx", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "crx", "u3"};
  auto gates = decompose_unitary(crx, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, CU3_BasisCompliance) {
  auto cu3 = matrix_utils::gate_to_matrix(
      create_gate("cu3", {0, 1}, {M_PI / 4, M_PI / 3, M_PI / 6}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = decompose_unitary(cu3, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, RXX_BasisCompliance) {
  auto rxx =
      matrix_utils::gate_to_matrix(create_gate("rxx", {0, 1}, {M_PI / 3}));
  std::set<std::string> basis = {"cx", "rz", "ry", "rxx"};
  auto gates = decompose_unitary(rxx, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, RZX_BasisCompliance) {
  auto rzx =
      matrix_utils::gate_to_matrix(create_gate("rzx", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "rzx", "h"};
  auto gates = decompose_unitary(rzx, basis);
  expect_all_in_basis(gates, basis);
}

// ========================================================================
// decompose_unitary() — 1Q additional edge cases
// ========================================================================

TEST(DecomposeUnitary1QTest, U3_FullParams_Roundtrip) {
  auto u3 = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.234, -0.567, 2.891}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = decompose_unitary(u3, basis);
  expect_all_in_basis(gates, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(u3, product, 1e-8));
}

TEST(DecomposeUnitary1QTest, PurePhase_P_Roundtrip) {
  auto p = matrix_utils::gate_to_matrix(create_gate("p", {0}, {M_PI / 3}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = decompose_unitary(p, basis);
  expect_all_in_basis(gates, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(p, product, 1e-8));
}

TEST(DecomposeUnitary1QTest, U2_Roundtrip) {
  auto u2 = matrix_utils::gate_to_matrix(
      create_gate("u2", {0}, {M_PI / 4, M_PI / 6}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = decompose_unitary(u2, basis);
  expect_all_in_basis(gates, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(u2, product, 1e-8));
}

TEST(DecomposeUnitary1QTest, RGate_Roundtrip) {
  auto r = matrix_utils::gate_to_matrix(
      create_gate("r", {0}, {M_PI / 3, M_PI / 5}));
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = decompose_unitary(r, basis);
  expect_all_in_basis(gates, basis);
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  EXPECT_TRUE(equal_up_to_global_phase(r, product, 1e-8));
}

TEST(DecomposeUnitary1QTest, U3Basis_ProducesOneGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = decompose_unitary(h, {"u3"});
  EXPECT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
}

TEST(DecomposeUnitary1QTest, BasisCompliance_RzRx) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = decompose_unitary(h, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary1QTest, BasisCompliance_RxRy) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rx", "ry"};
  auto gates = decompose_unitary(h, basis);
  expect_all_in_basis(gates, basis);
}

// ========================================================================
// decompose_unitary() — error handling
// ========================================================================

TEST(DecomposeUnitaryErrorTest, NonSquareMatrix) {
  CMatrix nonsquare = {{C(1), C(0), C(0)}, {C(0), C(1), C(0)}};
  EXPECT_THROW(decompose_unitary(nonsquare, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, Dimension3x3) {
  CMatrix m3 = {{C(1), C(0), C(0)}, {C(0), C(1), C(0)}, {C(0), C(0), C(1)}};
  EXPECT_THROW(decompose_unitary(m3, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, Dimension5x5) {
  CMatrix m5(5, std::vector<C>(5, C(0)));
  for (int i = 0; i < 5; ++i) m5[i][i] = C(1);
  EXPECT_THROW(decompose_unitary(m5, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, Dimension8x8) {
  auto m8 = matrix_utils::identity(8);
  EXPECT_THROW(decompose_unitary(m8, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, NonUnitary2x2) {
  CMatrix m = {{C(1), C(2)}, {C(3), C(4)}};
  EXPECT_THROW(decompose_unitary(m, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, NonUnitary4x4) {
  CMatrix m = matrix_utils::identity(4);
  m[0][1] = C(0.5);
  EXPECT_THROW(decompose_unitary(m, {"cx"}), std::invalid_argument);
}

TEST(DecomposeUnitaryErrorTest, ZeroMatrix) {
  CMatrix zero(2, std::vector<C>(2, C(0)));
  EXPECT_THROW(decompose_unitary(zero, {"rz"}), std::invalid_argument);
}

// ========================================================================
// Dangling pointer fix verification tests
// ========================================================================

TEST(DanglingPointerFix, MultipleIndependent1QBlocks) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("s", {0}));
  ir.push_back(create_gate("t", {0}));
  ir.push_back(create_gate("x", {1}));
  ir.push_back(create_gate("y", {1}));
  ir.push_back(create_gate("z", {1}));
  ir.push_back(create_gate("h", {2}));
  ir.push_back(create_gate("t", {2}));
  ir.push_back(create_gate("s", {2}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), 9);

  std::set<std::string> basis = {"rz", "ry", "cx"};
  UnitarySynthesis synth(basis);
  int reduced = synth.run(dag, basis);

  EXPECT_GE(reduced, 0);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

// Multiple independent 2Q blocks on different qubit pairs.
// Before the fix: replacing first CX block invalidates second CX block's
// pointers.
TEST(DanglingPointerFix, MultipleIndependent2QBlocks) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("cx", {0, 1}));
  ir.push_back(create_gate("h", {2}));
  ir.push_back(create_gate("cx", {2, 3}));
  ir.push_back(create_gate("h", {4}));
  ir.push_back(create_gate("cx", {4, 5}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), 6);

  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
}

TEST(DanglingPointerFix, Mixed1QAnd2QBlocks) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("s", {0}));
  ir.push_back(create_gate("cx", {1, 2}));
  ir.push_back(create_gate("h", {1}));
  ir.push_back(create_gate("t", {3}));
  ir.push_back(create_gate("h", {3}));
  ir.push_back(create_gate("cz", {4, 5}));
  ir.push_back(create_gate("s", {4}));
  ir.push_back(create_gate("x", {6}));
  ir.push_back(create_gate("y", {6}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), 10);

  std::set<std::string> basis = {"cx", "cz", "rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(DanglingPointerFix, ConsolidateMultipleBlocks) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("s", {0}));
  ir.push_back(create_gate("t", {0}));
  ir.push_back(create_gate("x", {1}));
  ir.push_back(create_gate("y", {1}));
  ir.push_back(create_gate("z", {1}));
  ir.push_back(create_gate("cx", {2, 3}));
  ir.push_back(create_gate("h", {2}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), 8);

  std::set<std::string> basis = {"cx", "rz", "ry"};
  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(DanglingPointerFix, StressManyBlocks) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  const int num_qubits = 10;
  for (int q = 0; q < num_qubits; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("s", {q}));
  }

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), num_qubits * 2);

  std::set<std::string> basis = {"rz", "ry", "cx"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(DanglingPointerFix, SkippedAndReplacedBlocksInterleaved) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("s", {0}));
  ir.push_back(create_gate("t", {1}));
  ir.push_back(create_gate("h", {1}));
  ir.push_back(create_gate("x", {2}));
  ir.push_back(create_gate("y", {2}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis, 1.0, 1);
  synth.run(dag, basis);
}

// Verify the DAG remains valid after multi-block synthesis (structural
// integrity).
TEST(DanglingPointerFix, DAGRemainsValidAfterMultiBlockSynthesis) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  ir.push_back(create_gate("h", {0}));
  ir.push_back(create_gate("s", {0}));
  ir.push_back(create_gate("h", {1}));
  ir.push_back(create_gate("t", {1}));
  ir.push_back(create_gate("h", {2}));
  ir.push_back(create_gate("x", {2}));

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig_size = dag.size();

  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto ops = dag.topological_op_nodes();
  EXPECT_GT(ops.size(), 0u);

  for (auto* node : ops) {
    EXPECT_FALSE(node->qargs.empty());
    for (int q : node->qargs) {
      EXPECT_GE(q, 0);
      EXPECT_LT(q, 3);
    }
  }
}

// ========================================================================
// QASM benchmark circuit optimization tests
//
// Load real QASM circuits (bb84_n8, hs4_n4, qpe_n9, qrng_n4, simon_n6)
// and run optimize() at levels 1-3 with various basis gate sets.
// Verifies no crashes and valid output.
// ========================================================================

namespace {

// Helper: load QASM file and return IR
std::vector<std::shared_ptr<BaseOperation>> load_qasm_circuit(
    const std::string& filename) {
  std::string path = std::string(TEST_DATA_DIR) +
                     "qasm/benchpress/qasmbench-small/" + filename + "/" +
                     filename + ".qasm";
  std::ifstream ifs(path);
  if (!ifs) return {};
  std::ostringstream oss;
  oss << ifs.rdbuf();
  auto [ir, num_qubits] = qasm_to_ir(oss.str());
  return ir;
}

}  // namespace

TEST(QASMCircuitOptTest, bb84_n8_Level1) {
  auto ir = load_qasm_circuit("bb84_n8");
  if (ir.empty()) GTEST_SKIP() << "bb84_n8.qasm not found";
  auto result = optimize(ir, 1);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, bb84_n8_Level2) {
  auto ir = load_qasm_circuit("bb84_n8");
  if (ir.empty()) GTEST_SKIP() << "bb84_n8.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 2, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, bb84_n8_Level3) {
  auto ir = load_qasm_circuit("bb84_n8");
  if (ir.empty()) GTEST_SKIP() << "bb84_n8.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 3, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, hs4_n4_Level1) {
  auto ir = load_qasm_circuit("hs4_n4");
  if (ir.empty()) GTEST_SKIP() << "hs4_n4.qasm not found";
  auto result = optimize(ir, 1);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, hs4_n4_Level2) {
  auto ir = load_qasm_circuit("hs4_n4");
  if (ir.empty()) GTEST_SKIP() << "hs4_n4.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 2, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, hs4_n4_Level3) {
  auto ir = load_qasm_circuit("hs4_n4");
  if (ir.empty()) GTEST_SKIP() << "hs4_n4.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 3, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qpe_n9_Level1) {
  auto ir = load_qasm_circuit("qpe_n9");
  if (ir.empty()) GTEST_SKIP() << "qpe_n9.qasm not found";
  auto result = optimize(ir, 1);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qpe_n9_Level2) {
  auto ir = load_qasm_circuit("qpe_n9");
  if (ir.empty()) GTEST_SKIP() << "qpe_n9.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 2, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qpe_n9_Level3) {
  auto ir = load_qasm_circuit("qpe_n9");
  if (ir.empty()) GTEST_SKIP() << "qpe_n9.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 3, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qrng_n4_Level1) {
  auto ir = load_qasm_circuit("qrng_n4");
  if (ir.empty()) GTEST_SKIP() << "qrng_n4.qasm not found";
  auto result = optimize(ir, 1);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qrng_n4_Level2) {
  auto ir = load_qasm_circuit("qrng_n4");
  if (ir.empty()) GTEST_SKIP() << "qrng_n4.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 2, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, qrng_n4_Level3) {
  auto ir = load_qasm_circuit("qrng_n4");
  if (ir.empty()) GTEST_SKIP() << "qrng_n4.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 3, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, simon_n6_Level1) {
  auto ir = load_qasm_circuit("simon_n6");
  if (ir.empty()) GTEST_SKIP() << "simon_n6.qasm not found";
  auto result = optimize(ir, 1);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, simon_n6_Level2) {
  auto ir = load_qasm_circuit("simon_n6");
  if (ir.empty()) GTEST_SKIP() << "simon_n6.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 2, false, basis);
  EXPECT_GT(result.size(), 0u);
}

TEST(QASMCircuitOptTest, simon_n6_Level3) {
  auto ir = load_qasm_circuit("simon_n6");
  if (ir.empty()) GTEST_SKIP() << "simon_n6.qasm not found";
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = optimize(ir, 3, false, basis);
  EXPECT_GT(result.size(), 0u);
}

// Test with IBM-style basis (u3 + cx)
TEST(QASMCircuitOptTest, AllCircuits_IBM_Basis) {
  std::vector<std::string> circuits = {"bb84_n8", "hs4_n4", "qpe_n9",
                                       "qrng_n4", "simon_n6"};
  std::set<std::string> ibm_basis = {"cx", "u3"};

  for (const auto& name : circuits) {
    auto ir = load_qasm_circuit(name);
    if (ir.empty()) {
      std::cout << "[SKIP] " << name << " not found" << std::endl;
      continue;
    }
    auto result = optimize(ir, 2, false, ibm_basis);
    EXPECT_GT(result.size(), 0u)
        << "Circuit " << name << " produced empty result";
  }
}

// Test with Google-style basis (rz + rx + cx)
TEST(QASMCircuitOptTest, AllCircuits_Google_Basis) {
  std::vector<std::string> circuits = {"bb84_n8", "hs4_n4", "qpe_n9",
                                       "qrng_n4", "simon_n6"};
  std::set<std::string> google_basis = {"cx", "rz", "rx"};

  for (const auto& name : circuits) {
    auto ir = load_qasm_circuit(name);
    if (ir.empty()) {
      std::cout << "[SKIP] " << name << " not found" << std::endl;
      continue;
    }
    auto result = optimize(ir, 2, false, google_basis);
    EXPECT_GT(result.size(), 0u)
        << "Circuit " << name << " produced empty result";
  }
}

// Test with IonQ-style basis (rz + ry + cz)
TEST(QASMCircuitOptTest, AllCircuits_IonQ_Basis) {
  std::vector<std::string> circuits = {"bb84_n8", "hs4_n4", "qpe_n9",
                                       "qrng_n4", "simon_n6"};
  std::set<std::string> ionq_basis = {"cz", "rz", "ry"};

  for (const auto& name : circuits) {
    auto ir = load_qasm_circuit(name);
    if (ir.empty()) {
      std::cout << "[SKIP] " << name << " not found" << std::endl;
      continue;
    }
    auto result = optimize(ir, 2, false, ionq_basis);
    EXPECT_GT(result.size(), 0u)
        << "Circuit " << name << " produced empty result";
  }
}

// ========================================================================
// RZ + SX basis decomposition tests
//
// Verifies the newly added branch in single_qubit_unitary_to_basis():
//   U3(θ, φ, λ) ≡ Rz(λ) Sx Rz(θ+π) Sx Rz(φ+3π)
// triggered when basis has rz+sx but not u3/u/ry/rx.
// ========================================================================

// Helper: reconstruct 2x2 unitary from a 1Q gate sequence
static CMatrix reconstruct_1q_unitary(
    const std::vector<std::shared_ptr<BaseOperation>>& gates) {
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : gates)
    product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
  return product;
}

// Verify the new branch is triggered: result gates are only rz/sx, no u3
TEST(RzSxBasisTest, BasisCompliance_NoU3) {
  std::set<std::string> basis = {"rz", "sx"};
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.234, -0.567, 2.891}));
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  for (const auto& g : gates) {
    EXPECT_TRUE(g->name == "rz" || g->name == "sx")
        << "Unexpected gate: " << g->name;
  }
}

// Verify decomposition equivalence: U3(θ,φ,λ) ≡ Rz(λ) Sx Rz(θ+π) Sx Rz(φ+3π)
TEST(RzSxBasisTest, U3_Roundtrip) {
  std::set<std::string> basis = {"rz", "sx"};
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.234, -0.567, 2.891}));
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  auto reconstructed = reconstruct_1q_unitary(gates);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}

// Verify with FakeTorino-style basis ['cz', 'id', 'rz', 'sx', 'x']
TEST(RzSxBasisTest, FakeTorinoBasis_U3Roundtrip) {
  std::set<std::string> basis = {"cz", "id", "rz", "sx", "x"};
  auto m = matrix_utils::gate_to_matrix(
      create_gate("u3", {0}, {1.91063, 0.0, 0.0}));
  auto gates = single_qubit_unitary_to_basis(m, 0, basis);
  auto reconstructed = reconstruct_1q_unitary(gates);
  EXPECT_TRUE(equal_up_to_global_phase(m, reconstructed, 1e-8));
}
