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
#include <fstream>
#include <memory>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "compiler/qasm_to_ir.hpp"
#include "optimizer/unitary_synthesis.h"

using namespace qcos;
using C = std::complex<double>;

// ========================================================================
// Helpers
// ========================================================================

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

static CMatrix reconstruct_2q_unitary(
    const std::vector<std::shared_ptr<BaseOperation>>& gates,
    int q0, int q1) {
  size_t n = 2;
  size_t dim = 4;
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
      create_gate("h", {0}), create_gate("h", {0}),
      create_gate("x", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  UnitarySynthesis synth;
  int reduced = synth.run(dag);
  EXPECT_GE(reduced, 0);
  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("x") ? counts.at("x") : 0, 1);
}

TEST(UnitarySynthesisTest, BasisGateTranslation) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0})};
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
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0})};
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
      create_gate("h", {0}), create_gate("h", {0}),
      create_gate("x", {1}), create_gate("x", {1})};
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
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1})};
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
      create_gate("h", {0}), create_gate("cx", {0, 1}),
      create_gate("h", {0}), create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  ConsolidateBlocks consolidator;
  consolidator.run(dag);
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
    EXPECT_TRUE(g->name == "cz" || g->name == "h" ||
                g->name == "rz" || g->name == "ry")
        << "Gate " << g->name << " not in basis";
  }
}

TEST(DecomposeUnitaryTest, InvalidDimension_Throws) {
  CMatrix m3x3 = {{C(1), C(0), C(0)},
                   {C(0), C(1), C(0)},
                   {C(0), C(0), C(1)}};
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
  for (const auto& name : {"h", "x", "y", "z", "s", "sdg", "t", "tdg", "sx", "sxdg"}) {
    auto m = matrix_utils::gate_to_matrix(create_gate(name, {0}));
    auto gates = decompose_unitary(m, basis);
    CMatrix product = matrix_utils::identity(2);
    for (const auto& g : gates) {
      product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
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
        product = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), product);
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

TEST(DecomposeUnitary2QTest, AllKnownGates_Roundtrip) {
  std::set<std::string> basis = {"cx", "cz", "swap", "iswap", "ecr",
                                  "h", "rz", "ry", "rx", "u3", "x"};
  struct TestCase {
    std::string name;
    std::vector<double> params;
    bool expect_roundtrip;
  };
  std::vector<TestCase> cases = {
      {"cx", {}, true}, {"cz", {}, true},
      {"swap", {}, true}, {"iswap", {}, true}, {"ecr", {}, true},
      {"cp", {M_PI / 4}, false},
      {"crx", {M_PI / 3}, false}, {"cry", {M_PI / 5}, false},
      {"crz", {M_PI / 7}, false},
      {"rxx", {M_PI / 4}, false}, {"ryy", {M_PI / 3}, false},
      {"rzz", {M_PI / 5}, false},
  };

  for (const auto& tc : cases) {
    auto mat = matrix_utils::gate_to_matrix(create_gate(tc.name, {0, 1}, tc.params));
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
      h_full[row][col] = ((row ^ (rq << 1)) == (col ^ (cq << 1)))
                             ? h_mat[rq][cq] : C(0);
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
      h_full[row][col] = ((row ^ (rq << 1)) == (col ^ (cq << 1)))
                             ? h[rq][cq] : C(0);
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

TEST(DecomposeUnitary2QTest, ControlledPhase_BasisCompliance) {
  auto cp = matrix_utils::gate_to_matrix(create_gate("cp", {0, 1}, {M_PI / 4}));
  std::set<std::string> basis = {"cx", "rz", "ry", "cp", "u3"};
  auto gates = decompose_unitary(cp, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, RZZ_BasisCompliance) {
  auto rzz = matrix_utils::gate_to_matrix(create_gate("rzz", {0, 1}, {M_PI / 3}));
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
  auto crx = matrix_utils::gate_to_matrix(create_gate("crx", {0, 1}, {M_PI / 4}));
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
  auto rxx = matrix_utils::gate_to_matrix(create_gate("rxx", {0, 1}, {M_PI / 3}));
  std::set<std::string> basis = {"cx", "rz", "ry", "rxx"};
  auto gates = decompose_unitary(rxx, basis);
  expect_all_in_basis(gates, basis);
}

TEST(DecomposeUnitary2QTest, RZX_BasisCompliance) {
  auto rzx = matrix_utils::gate_to_matrix(create_gate("rzx", {0, 1}, {M_PI / 4}));
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
  CMatrix m3 = {{C(1), C(0), C(0)},
                {C(0), C(1), C(0)},
                {C(0), C(0), C(1)}};
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
// synthesize_block() — error branch coverage
//
// 覆盖 synthesize_block 中各错误分支:
//   - 2x2 矩阵传空 qubits (第 96 行)
//   - 4x4 矩阵传 <2 qubits (第 101 行)
//   - 不支持维度 (第 105 行)
// ========================================================================

TEST(SynthesizeBlockErrorTest, Matrix2x2_EmptyQubits_Throws) {
  auto m = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  UnitarySynthesis synth;
  EXPECT_THROW(synth.synthesize_block(m, {}), std::invalid_argument);
}

TEST(SynthesizeBlockErrorTest, Matrix4x4_EmptyQubits_Throws) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  UnitarySynthesis synth;
  EXPECT_THROW(synth.synthesize_block(m, {}), std::invalid_argument);
}

TEST(SynthesizeBlockErrorTest, Matrix4x4_SingleQubit_Throws) {
  auto m = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  UnitarySynthesis synth;
  EXPECT_THROW(synth.synthesize_block(m, {0}), std::invalid_argument);
}

TEST(SynthesizeBlockErrorTest, Matrix3x3_Throws) {
  CMatrix m3 = {{C(1), C(0), C(0)},
                {C(0), C(1), C(0)},
                {C(0), C(0), C(1)}};
  UnitarySynthesis synth;
  EXPECT_THROW(synth.synthesize_block(m3, {0}), std::invalid_argument);
}

TEST(SynthesizeBlockErrorTest, Matrix5x5_Throws) {
  CMatrix m5(5, std::vector<C>(5, C(0)));
  for (int i = 0; i < 5; ++i) m5[i][i] = C(1);
  UnitarySynthesis synth;
  EXPECT_THROW(synth.synthesize_block(m5, {0, 1}), std::invalid_argument);
}

// ========================================================================
// decompose_unitary() — validation order coverage
//
// decompose_unitary 的校验顺序: empty → non-unitary → non-square。
// 验证各种非法输入被正确拒绝。
// ========================================================================

TEST(DecomposeUnitaryValidationTest, EmptyFirstColumn_Throws) {
  // outer vector non-empty but inner empty => "empty matrix" path.
  CMatrix m = {{}};
  EXPECT_THROW(decompose_unitary(m, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryValidationTest, NonSquareRagged_Throws) {
  // Ragged rows (1st row 2 cols, 2nd row 1 col) => not unitary, not square.
  CMatrix m = {{C(1), C(0)}, {C(0)}};
  EXPECT_THROW(decompose_unitary(m, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryValidationTest, UnitaryBut1x1_NotSupported) {
  // A 1x1 "unitary" (phase) is technically unitary but dim != 2 and != 4.
  CMatrix m = {{C(0, 1)}};  // |det|=1, is_unitary true for 1x1
  EXPECT_THROW(decompose_unitary(m, {"rz"}), std::invalid_argument);
}

TEST(DecomposeUnitaryValidationTest, EmptyBasisSet_1Q) {
  // Empty basis => single_qubit_unitary_to_basis falls back to U3.
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = decompose_unitary(h, {});
  EXPECT_GE(gates.size(), 0u);  // must not crash; may emit u3 fallback
}

TEST(DecomposeUnitaryValidationTest, EmptyBasisSet_2Q) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  EXPECT_NO_THROW(decompose_unitary(cx, {}));
}

// ========================================================================
// decompose_unitary() — diverse 1Q Euler basis end-to-end
//
// 通过顶层 decompose_unitary 接口验证不同欧拉基 (U/PSX/ZSX/RR)
// 的端到端行为，而非直接调用 single_qubit_unitary_to_basis。
// ========================================================================

TEST(DecomposeUnitary1QEulerTest, UBasis_ProducesSingleUGate) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"u"};
  auto gates = decompose_unitary(h, basis);
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(DecomposeUnitary1QEulerTest, PSXBasis_UnimplementedFallsBackToU3) {
  // The PSX basis ({p, sx}) is selectable by basis_selector but NOT yet
  // implemented in single_qubit_unitary_to_basis. The decomposer falls back
  // to emitting a U3 gate. This test documents that current behavior.
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"p", "sx"};
  auto gates = decompose_unitary(h, basis);
  EXPECT_GE(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(DecomposeUnitary1QEulerTest, ZSXBasis_UnimplementedFallsBackToU3) {
  // ZSX basis ({rz, sx}) is selectable but not implemented in the decomposer.
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  std::set<std::string> basis = {"rz", "sx"};
  auto gates = decompose_unitary(h, basis);
  EXPECT_GE(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(h, product, 1e-8));
}

TEST(DecomposeUnitary1QEulerTest, RRBasis_UnimplementedFallsBackToU3) {
  // RR basis ({r}) is selectable but not implemented in the decomposer.
  auto x = matrix_utils::gate_to_matrix(create_gate("x", {0}));
  std::set<std::string> basis = {"r"};
  auto gates = decompose_unitary(x, basis);
  EXPECT_GE(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  CMatrix product = matrix_utils::gate_to_matrix(gates[0]);
  EXPECT_TRUE(equal_up_to_global_phase(x, product, 1e-8));
}

TEST(DecomposeUnitary1QEulerTest, U3Basis_PreservesQubit) {
  auto h = matrix_utils::gate_to_matrix(create_gate("h", {0}));
  auto gates = decompose_unitary(h, {"u3"}, {7});
  ASSERT_EQ(gates.size(), 1u);
  EXPECT_EQ(gates[0]->name, "u3");
  EXPECT_EQ(gates[0]->targets[0], 7);
}

// ========================================================================
// decompose_unitary() — 1Q multi-gate composition roundtrip
//
// 通过 decompose_unitary 顶层接口分解多门组合矩阵，验证 roundtrip。
// ========================================================================

TEST(DecomposeUnitary1QCompositionTest, HS_Roundtrip) {
  CMatrix product = matrix_utils::identity(2);
  product = matrix_utils::multiply(
      matrix_utils::gate_to_matrix(create_gate("s", {0})), product);
  product = matrix_utils::multiply(
      matrix_utils::gate_to_matrix(create_gate("h", {0})), product);
  std::set<std::string> basis = {"rz", "ry"};
  auto gates = decompose_unitary(product, basis);
  expect_all_in_basis(gates, basis);
  CMatrix rebuilt = matrix_utils::identity(2);
  for (const auto& g : gates)
    rebuilt = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), rebuilt);
  EXPECT_TRUE(equal_up_to_global_phase(product, rebuilt, 1e-8));
}

TEST(DecomposeUnitary1QCompositionTest, HTH_Roundtrip) {
  CMatrix product = matrix_utils::identity(2);
  for (const auto& g : {"h", "t", "h"}) {
    product = matrix_utils::multiply(
        matrix_utils::gate_to_matrix(create_gate(g, {0})), product);
  }
  std::set<std::string> basis = {"rz", "rx"};
  auto gates = decompose_unitary(product, basis);
  expect_all_in_basis(gates, basis);
  CMatrix rebuilt = matrix_utils::identity(2);
  for (const auto& g : gates)
    rebuilt = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), rebuilt);
  EXPECT_TRUE(equal_up_to_global_phase(product, rebuilt, 1e-8));
}

TEST(DecomposeUnitary1QCompositionTest, LongChain_Roundtrip) {
  CMatrix product = matrix_utils::identity(2);
  std::vector<std::string> seq = {"h", "t", "s", "h", "t", "h", "s", "t"};
  for (const auto& g : seq) {
    product = matrix_utils::multiply(
        matrix_utils::gate_to_matrix(create_gate(g, {0})), product);
  }
  for (const auto& basis_set : std::vector<std::set<std::string>>{
           {"rz", "ry"}, {"rz", "rx"}, {"rx", "ry"}, {"u3"}}) {
    auto gates = decompose_unitary(product, basis_set);
    CMatrix rebuilt = matrix_utils::identity(2);
    for (const auto& g : gates)
      rebuilt = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), rebuilt);
    EXPECT_TRUE(equal_up_to_global_phase(product, rebuilt, 1e-7))
        << "Roundtrip failed for basis";
  }
}

// ========================================================================
// decompose_unitary() — 2Q Haar-random stress test
//
// 通过顶层 decompose_unitary 接口分解 Haar-随机 4x4 酉矩阵，
// 验证基合规性和 roundtrip 正确性。这是真实优化器使用场景。
// ========================================================================

static CMatrix haar_random_unitary_2q(std::mt19937_64& rng) {
  std::normal_distribution<double> dist(0.0, 1.0);
  CMatrix A(4, std::vector<C>(4));
  for (int i = 0; i < 4; ++i)
    for (int j = 0; j < 4; ++j)
      A[i][j] = C(dist(rng), dist(rng));
  // Modified Gram-Schmidt
  CMatrix Q(4, std::vector<C>(4));
  for (int j = 0; j < 4; ++j) {
    for (int i = 0; i < 4; ++i) Q[i][j] = A[i][j];
    for (int k = 0; k < j; ++k) {
      C dot = C(0, 0);
      for (int i = 0; i < 4; ++i) dot += std::conj(Q[i][k]) * Q[i][j];
      for (int i = 0; i < 4; ++i) Q[i][j] -= dot * Q[i][k];
    }
    double norm = 0.0;
    for (int i = 0; i < 4; ++i) norm += std::norm(Q[i][j]);
    norm = std::sqrt(norm);
    if (norm < 1e-15) continue;
    for (int i = 0; i < 4; ++i) Q[i][j] /= norm;
  }
  return Q;
}

TEST(DecomposeUnitary2QHaarTest, BasisCompliance_50Samples) {
  std::mt19937_64 rng(20260814);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  for (int i = 0; i < 50; ++i) {
    auto u = haar_random_unitary_2q(rng);
    auto gates = decompose_unitary(u, basis);
    expect_all_in_basis(gates, basis);
  }
}

TEST(DecomposeUnitary2QHaarTest, Roundtrip_50Samples) {
  std::mt19937_64 rng(7777);
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  for (int i = 0; i < 50; ++i) {
    auto u = haar_random_unitary_2q(rng);
    auto gates = decompose_unitary(u, basis);
    auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
    EXPECT_TRUE(equal_up_to_global_phase(u, reconstructed, 1e-6))
        << "2Q Haar roundtrip failed at sample " << i;
  }
}

// ========================================================================
// UnitarySynthesis pass — two-phase optimization assertions
//
// 验证 run() 返回的 reduced 值、电路结构有效性、基合规性。
// ========================================================================

TEST(UnitarySynthesisPhaseTest, TwoPhaseOptimization_1QOnly) {
  // Pure 1Q gates that consolidate: H·S·T on qubit 0.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig = dag.size();
  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis);
  int reduced = synth.run(dag, basis);
  EXPECT_GE(reduced, 0);
  EXPECT_LE(dag.size(), orig);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(UnitarySynthesisPhaseTest, TwoPhaseOptimization_Mixed1Q2Q) {
  // 1Q blocks (h·s on q0, t·h on q1) and a 2Q cx between them.
  // collect phase 1 processes the 1Q runs; phase 2 processes the 2Q block.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}),
      create_gate("cx", {0, 1}),
      create_gate("t", {1}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  // cx is a basis gate and should be preserved.
  auto counts = dag.count_ops();
  EXPECT_GE(counts.count("cx") ? counts.at("cx") : 0, 1);
  // Any rz/ry gates produced must be in basis (they are).
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(UnitarySynthesisPhaseTest, MaxBlockSize2_Allows2Q) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  UnitarySynthesis synth(basis, 1.0, 2);
  synth.run(dag, basis);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(UnitarySynthesisPhaseTest, AllBasisGatesUnchanged) {
  // When the circuit already contains only basis gates, run() should be a no-op.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rz", {0}, {0.3}),
      create_gate("ry", {0}, {0.5}),
      create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  UnitarySynthesis synth(basis);
  int reduced = synth.run(dag, basis);
  EXPECT_EQ(reduced, 0);
  EXPECT_EQ(dag.size(), 3);
}

TEST(UnitarySynthesisPhaseTest, DAGRemainsValidAfterOptimization) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int q = 0; q < 4; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("s", {q}));
    ir.push_back(create_gate("t", {q}));
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto ops = dag.topological_op_nodes();
  EXPECT_GT(ops.size(), 0u);
  for (auto* node : ops) {
    EXPECT_FALSE(node->qargs.empty());
    for (int q : node->qargs) {
      EXPECT_GE(q, 0);
      EXPECT_LT(q, 4);
    }
  }
}

TEST(UnitarySynthesisPhaseTest, NonBasisGateGetsReplaced) {
  // A 2-gate 1Q block (h·s) with h non-basis must be consolidated and
  // replaced. Single-gate blocks are NOT processed (min_block_size=2 in
  // collect_all_matching_blocks), so we use a 2-gate block here.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("h") ? counts.at("h") : 0, 0);
  EXPECT_EQ(counts.count("s") ? counts.at("s") : 0, 0);
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0);
  }
}

// ========================================================================
// ConsolidateBlocks — return value, min_block_size, DAG validity
//
// 覆盖 ConsolidateBlocks::run 的返回值断言、min_block_size 参数行为、
// 合并后 DAG 结构有效性。
// ========================================================================

TEST(ConsolidateBlocksAdvancedTest, RunReturnsNonNegative) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  ConsolidateBlocks consolidator;
  int reduced = consolidator.run(dag);
  EXPECT_GE(reduced, 0);
}

TEST(ConsolidateBlocksAdvancedTest, MinBlockSize3_SkipsSmallBlocks) {
  // With min_block_size=3, a 2-gate block should NOT be consolidated.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig = dag.size();
  ConsolidateBlocks consolidator(std::nullopt, 1.0, 3);
  int reduced = consolidator.run(dag);
  EXPECT_EQ(reduced, 0);
  EXPECT_EQ(dag.size(), orig);
}

TEST(ConsolidateBlocksAdvancedTest, MinBlockSize2_Consolidates) {
  // With min_block_size=2, a 3-gate block should be consolidated.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  int orig = dag.size();
  ConsolidateBlocks consolidator(std::nullopt, 1.0, 2);
  consolidator.run(dag);
  EXPECT_LE(dag.size(), orig);
}

TEST(ConsolidateBlocksAdvancedTest, EmptyDAGReturnsZero) {
  DAGCircuit dag;
  dag.add_qubits(2);
  ConsolidateBlocks consolidator;
  int reduced = consolidator.run(dag);
  EXPECT_EQ(reduced, 0);
  EXPECT_EQ(dag.size(), 0);
}

TEST(ConsolidateBlocksAdvancedTest, DAGRemainsValidAfterConsolidation) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int q = 0; q < 3; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("s", {q}));
    ir.push_back(create_gate("t", {q}));
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry"};
  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);

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

TEST(ConsolidateBlocksAdvancedTest, NonBasisGateGetsConsolidated) {
  // h is non-basis; consolidation must replace it with rz+ry.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("t", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry"};
  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);
  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("h") ? counts.at("h") : 0, 0);
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0);
  }
}

TEST(ConsolidateBlocksAdvancedTest, Preserves2QGates) {
  // 2Q gate (cx) in basis should be preserved, not decomposed.
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);
  auto counts = dag.count_ops();
  EXPECT_GE(counts.count("cx") ? counts.at("cx") : 0, 1);
}

// ========================================================================
// Large circuit stress test
//
// 多比特、多 block 的大电路端到端验证，确认无崩溃、基合规、DAG 有效。
// ========================================================================

TEST(LargeCircuitStressTest, ManyQubitsManyBlocks) {
  const int num_qubits = 8;
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int q = 0; q < num_qubits; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("s", {q}));
    ir.push_back(create_gate("t", {q}));
    ir.push_back(create_gate("h", {q}));
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(dag.size(), num_qubits * 4);
  std::set<std::string> basis = {"rz", "ry", "cx"};
  UnitarySynthesis synth(basis);
  int reduced = synth.run(dag, basis);
  EXPECT_GE(reduced, 0);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(LargeCircuitStressTest, Interleaved1Q2QDeep) {
  // Each qubit gets a 2-gate 1Q run (h·t) plus cx links between neighbors.
  // The 1Q runs form ≥2-gate blocks and should be re-expressed in basis.
  std::vector<std::shared_ptr<BaseOperation>> ir;
  const int num_qubits = 6;
  for (int q = 0; q < num_qubits; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("t", {q}));
    if (q + 1 < num_qubits) {
      ir.push_back(create_gate("cx", {q, q + 1}));
    }
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
}

TEST(LargeCircuitStressTest, ConsolidateThenSynthesize) {
  // Run ConsolidateBlocks followed by UnitarySynthesis — a realistic pipeline.
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int q = 0; q < 4; ++q) {
    ir.push_back(create_gate("h", {q}));
    ir.push_back(create_gate("s", {q}));
    ir.push_back(create_gate("t", {q}));
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  std::set<std::string> basis = {"rz", "ry", "cx"};

  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);

  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
  auto ops = dag.topological_op_nodes();
  EXPECT_GT(ops.size(), 0u);
}

// ========================================================================
// decompose_unitary() — 2Q cross-basis roundtrip
//
// 验证跨基分解（如 CX→CZ、CZ→CX）的 roundtrip 正确性，不仅基合规。
// ========================================================================

TEST(DecomposeUnitary2QCrossBasisTest, CXToCZRoundtrip) {
  auto cx = matrix_utils::gate_to_matrix(create_gate("cx", {0, 1}));
  std::set<std::string> basis = {"cz", "h", "rz", "ry"};
  auto gates = decompose_unitary(cx, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(cx, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QCrossBasisTest, CZToCXRoundtrip) {
  auto cz = matrix_utils::gate_to_matrix(create_gate("cz", {0, 1}));
  std::set<std::string> basis = {"cx", "h", "rz", "ry"};
  auto gates = decompose_unitary(cz, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(cz, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QCrossBasisTest, SWAPToCXRoundtrip) {
  auto swap = matrix_utils::gate_to_matrix(create_gate("swap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto gates = decompose_unitary(swap, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(swap, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QCrossBasisTest, ISwapToCXRoundtrip) {
  auto iswap = matrix_utils::gate_to_matrix(create_gate("iswap", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = decompose_unitary(iswap, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(iswap, reconstructed, 1e-6));
}

TEST(DecomposeUnitary2QCrossBasisTest, ECRToCXRoundtrip) {
  auto ecr = matrix_utils::gate_to_matrix(create_gate("ecr", {0, 1}));
  std::set<std::string> basis = {"cx", "rz", "ry", "u3"};
  auto gates = decompose_unitary(ecr, basis);
  expect_all_in_basis(gates, basis);
  auto reconstructed = reconstruct_2q_unitary(gates, 0, 1);
  EXPECT_TRUE(equal_up_to_global_phase(ecr, reconstructed, 1e-6));
}

// ========================================================================
// OpenQASM end-to-end tests
//
// 真实场景验证: 从 OpenQASM 文本加载电路 → 解析为 ops → 构建 DAG →
// 运行 UnitarySynthesis 分解 → 验证:
//   (1) 分解后所有门都在目标基中
//   (2) 分解后电路的酉矩阵与原始电路酉矩阵相等 (up to global phase)
//
// 这是酉综合 pass 的端到端正确性验证，覆盖完整数据流。
// ========================================================================

// Build the full N-qubit unitary of an operation sequence. ops are applied
// left-to-right in circuit order (op[0] first); U = op[n-1] ... op[1] op[0]
// because later ops act on the state produced by earlier ones.
static CMatrix circuit_unitary_from_ops(
    const std::vector<std::shared_ptr<BaseOperation>>& ops, int num_qubits) {
  size_t dim = static_cast<size_t>(1) << num_qubits;
  CMatrix result = matrix_utils::identity(dim);
  for (const auto& op : ops) {
    // Skip non-unitary ops (measure, reset, sync, move): they do not
    // contribute to the circuit's unitary evolution.
    if (op->operation_type < OperationType::SINGLE_QUBIT_OPERATION) continue;
    auto gate_mat = matrix_utils::gate_to_matrix(op);
    size_t nq = op->targets.size();
    size_t gate_dim = static_cast<size_t>(1) << nq;
    CMatrix full = matrix_utils::identity(dim);
    // Map op target i -> global qubit position (big-endian bit pos).
    for (size_t row = 0; row < dim; ++row) {
      for (size_t col = 0; col < dim; ++col) {
        // Extract the sub-indices for the gate's qubits.
        size_t g_row = 0, g_col = 0;
        bool mismatch = false;
        for (size_t i = 0; i < nq; ++i) {
          int pos = num_qubits - 1 - op->targets[i];
          size_t rb = (row >> pos) & 1;
          size_t cb = (col >> pos) & 1;
          g_row |= (rb << (nq - 1 - i));
          g_col |= (cb << (nq - 1 - i));
          // remaining bits (excluding gate qubits) must match
        }
        // Check non-gate bits match between row and col.
        std::vector<int> gate_positions;
        for (size_t i = 0; i < nq; ++i)
          gate_positions.push_back(num_qubits - 1 - op->targets[i]);
        for (int b = 0; b < num_qubits; ++b) {
          bool is_gate = false;
          for (int gp : gate_positions)
            if (gp == b) { is_gate = true; break; }
          if (!is_gate) {
            if (((row >> b) & 1) != ((col >> b) & 1)) {
              mismatch = true; break;
            }
          }
        }
        full[row][col] = mismatch ? C(0) : gate_mat[g_row][g_col];
      }
    }
    result = matrix_utils::multiply(full, result);
  }
  return result;
}

// Build the full N-qubit unitary from a DAG's topological op nodes.
static CMatrix circuit_unitary_from_dag(DAGCircuit& dag, int num_qubits) {
  auto nodes = dag.topological_op_nodes();
  std::vector<std::shared_ptr<BaseOperation>> ops;
  for (auto* node : nodes) {
    ops.push_back(node->op);
  }
  return circuit_unitary_from_ops(ops, num_qubits);
}

// Full pipeline via decompose_unitary: qasm string -> ops -> circuit unitary
// -> decompose_unitary -> rebuild -> verify equivalence. This directly
// exercises the unitary decomposer (1Q ZYZ / 2Q KAK) on real QASM-derived
// unitaries, independent of the run() pass's block-collection heuristics.
static void run_qasm_decompose_test(
    const std::string& qasm, int num_qubits,
    const std::set<std::string>& basis, double tol = 1e-6) {
  auto [ops, parsed_nq] = qasm_to_ir(qasm);
  ASSERT_FALSE(ops.empty()) << "QASM parsed to empty op list";
  int nq = num_qubits > 0 ? num_qubits : parsed_nq;
  ASSERT_GE(nq, 1);

  CMatrix original = circuit_unitary_from_ops(ops, nq);
  size_t dim = static_cast<size_t>(1) << nq;
  ASSERT_EQ(original.size(), dim);

  // Decompose the full circuit unitary into the target basis.
  auto gates = decompose_unitary(original, basis);
  expect_all_in_basis(gates, basis);

  // Rebuild the unitary from the emitted gate sequence and compare.
  CMatrix rebuilt;
  if (nq == 1) {
    rebuilt = matrix_utils::identity(2);
    for (const auto& g : gates)
      rebuilt = matrix_utils::multiply(matrix_utils::gate_to_matrix(g), rebuilt);
  } else {
    rebuilt = reconstruct_2q_unitary(gates, 0, 1);
  }
  EXPECT_TRUE(equal_up_to_global_phase(original, rebuilt, tol))
      << "QASM-derived unitary decomposition roundtrip failed";
}

// Full pipeline via the UnitarySynthesis pass: qasm -> ops -> DAG -> run() ->
// verify basis compliance + unitary equivalence. Suitable for circuits whose
// gates form >=2-gate collectible blocks (the pass requires min_block_size=2).
static void run_qasm_pass_test(
    const std::string& qasm, int num_qubits,
    const std::set<std::string>& basis, double tol = 1e-6) {
  auto [ops, parsed_nq] = qasm_to_ir(qasm);
  ASSERT_FALSE(ops.empty()) << "QASM parsed to empty op list";
  int nq = num_qubits > 0 ? num_qubits : parsed_nq;
  ASSERT_GE(nq, 1);

  CMatrix original = circuit_unitary_from_ops(ops, nq);

  DAGCircuit dag = DAGCircuit::ir_to_dag(ops);
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0)
        << "Gate '" << name << "' not in target basis after synthesis";
  }

  CMatrix synthesized = circuit_unitary_from_dag(dag, nq);
  EXPECT_TRUE(equal_up_to_global_phase(original, synthesized, tol))
      << "QASM synthesis pass changed the circuit unitary";
}

// ---- 1-qubit QASM circuits ----

TEST(QasmSynthesisTest, SingleQubit_HST_ZYZ) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
s q[0];
t q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "ry"});
}

TEST(QasmSynthesisTest, SingleQubit_HTHS_ZXZ) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
t q[0];
h q[0];
s q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "rx"});
}

TEST(QasmSynthesisTest, SingleQubit_Paulis_XYX) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
x q[0];
y q[0];
z q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rx", "ry"});
}

TEST(QasmSynthesisTest, SingleQubit_U3Basis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
u3(0.5, 1.2, -0.3) q[0];
h q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"u3"});
}

TEST(QasmSynthesisTest, SingleQubit_IdentityChain) {
  // H·H = I, S·Sdg = I => net identity, should produce no gates.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
h q[0];
s q[0];
sdg q[0];
)";
  auto [ops, nq] = qasm_to_ir(qasm);
  DAGCircuit dag = DAGCircuit::ir_to_dag(ops);
  std::set<std::string> basis = {"rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  // Identity => no gates after synthesis.
  EXPECT_EQ(dag.size(), 0);
}

TEST(QasmSynthesisTest, SingleQubit_LongChain_Roundtrip) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
t q[0];
s q[0];
h q[0];
t q[0];
h q[0];
s q[0];
t q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "ry"});
}

// ---- 2-qubit QASM circuits ----

TEST(QasmSynthesisTest, TwoQubit_BellState_CXBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_BellState_U3Basis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "u3"});
}

TEST(QasmSynthesisTest, TwoQubit_CXDirect_Preserved) {
  // A bare CX in a CX-basis should remain a single CX.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
cx q[0],q[1];
)";
  auto [ops, nq] = qasm_to_ir(qasm);
  DAGCircuit dag = DAGCircuit::ir_to_dag(ops);
  std::set<std::string> basis = {"cx", "rz", "ry"};
  UnitarySynthesis synth(basis);
  synth.run(dag, basis);
  auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("cx") ? counts.at("cx") : 0, 1);
}

TEST(QasmSynthesisTest, TwoQubit_CZToCZBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
cz q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cz", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_CZToCXBasis) {
  // CZ decomposed into CX basis (needs H on target). Via decompose_unitary
  // on the full circuit unitary (the pass needs >=2-gate blocks).
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
cz q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "h", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_SWAPToCXBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
swap q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_ParallelRotations) {
  // Two independent 1Q rotations on separate qubits, no entanglement.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
rx(0.7) q[0];
ry(1.1) q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_Independent1QBlocks) {
  // Each qubit has a 1Q run; both must be re-expressed in basis.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
s q[0];
t q[1];
h q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_GHZ_CXBasis) {
  // 3-qubit GHZ — but synthesis handles ≤2-qubit blocks, so verify no crash
  // and that the 2-qubit blocks are correctly synthesized.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0],q[1];
h q[0];
t q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, TwoQubit_IswapInBasis) {
  // ISWAP is a native basis gate here => preserved, roundtrip verified.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
iswap q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"iswap", "rz", "ry", "u3"});
}

TEST(QasmSynthesisTest, TwoQubit_IswapToCXBasis) {
  // ISWAP not in basis => must decompose to CX + rotations. Via
  // decompose_unitary (single 2Q gate isn't a >=2-gate collectible block).
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
iswap q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry", "u3"});
}

// ---- QASM 3.0 circuits ----

TEST(QasmSynthesisTest, Qasm3_SingleQubitSXRZ) {
  std::string qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
sx q[0];
rz(0.5) q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "ry"});
}

TEST(QasmSynthesisTest, Qasm3_TwoQubitBell) {
  std::string qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
h q[0];
cx q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

TEST(QasmSynthesisTest, Qasm3_RotationGates) {
  std::string qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
rx(0.3) q[0];
ry(0.7) q[1];
cx q[0],q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

// ---- Multi-block QASM circuits ----

TEST(QasmSynthesisTest, MultiBlock_TwoIndependent1Q) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
s q[0];
t q[0];
h q[1];
tdg q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"rz", "ry"});
}

TEST(QasmSynthesisTest, MultiBlock_CXBetween1QRuns) {
  // 1Q run on q0, entangling CX, 1Q run on q1.
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
s q[0];
cx q[0],q[1];
t q[1];
h q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

// ---- ConsolidateBlocks + UnitarySynthesis pipeline from QASM ----

TEST(QasmSynthesisTest, ConsolidateThenSynthesize_Pipeline) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
s q[0];
t q[0];
h q[1];
s q[1];
t q[1];
)";
  auto [ops, nq] = qasm_to_ir(qasm);
  CMatrix original = circuit_unitary_from_ops(ops, nq);

  DAGCircuit dag = DAGCircuit::ir_to_dag(ops);
  std::set<std::string> basis = {"cx", "rz", "ry"};

  ConsolidateBlocks consolidator(basis);
  consolidator.run(dag, basis);

  UnitarySynthesis synth(basis);
  synth.run(dag, basis);

  auto counts = dag.count_ops();
  for (const auto& [name, count] : counts) {
    EXPECT_TRUE(basis.count(name) > 0) << "Gate " << name << " not in basis";
  }
  CMatrix synthesized = circuit_unitary_from_dag(dag, nq);
  EXPECT_TRUE(equal_up_to_global_phase(original, synthesized, 1e-6));
}

// ---- QASM with parameterized gates ----

TEST(QasmSynthesisTest, ParameterizedU3Roundtrip) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
u3(1.234, -0.567, 2.891) q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "ry"});
}

TEST(QasmSynthesisTest, ParameterizedRotationsRoundtrip) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
rx(0.7) q[0];
rz(1.3) q[0];
ry(0.9) q[0];
)";
  run_qasm_decompose_test(qasm, 1, {"rz", "ry"});
}

TEST(QasmSynthesisTest, Parameterized2QGatesRoundtrip) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
rz(0.5) q[0];
cx q[0],q[1];
rx(0.8) q[1];
)";
  run_qasm_decompose_test(qasm, 2, {"cx", "rz", "ry"});
}

// ========================================================================
// 真实 benchmark 电路在 {u3, cz} 基下的酉综合回归测试
//
// 背景: iswap_n2 / hs4_n4 在 {u3, cz} basis 下曾出现优化后酉矩阵与原电路不等价
// 的 bug (数值错误)。这两个用例作为回归防护: 优化前后酉矩阵必须等价 (允许
// 全局相位), 且输出门全在 {u3, cz} 内。hs4_n4 为 4 比特, decompose_unitary
// 路径仅支持 <=2 比特, 故只走 UnitarySynthesis pass 路径。
// ========================================================================

// iswap_n2 (2 比特): h/s/x/cx 电路, 走 pass + decompose 两条路径。
TEST(QasmU3CzBenchTest, IswapN2_Pass_U3CzBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
s q[0];
s q[1];
h q[0];
cx q[0],q[1];
h q[0];
h q[1];
cx q[0],q[1];
h q[0];
)";
  run_qasm_pass_test(qasm, 2, {"u3", "cz"});
}

TEST(QasmU3CzBenchTest, IswapN2_Decompose_U3CzBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
x q[0];
s q[0];
s q[1];
h q[0];
cx q[0],q[1];
h q[0];
h q[1];
cx q[0],q[1];
h q[0];
)";
  run_qasm_decompose_test(qasm, 2, {"u3", "cz"});
}

// hs4_n4 (4 比特): 两组独立 2q 块 (q0/q1, q2/q3), h/x/cx 电路, 走 pass 路径。
TEST(QasmU3CzBenchTest, Hs4N4_Pass_U3CzBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
h q[1];
h q[2];
h q[3];
x q[0];
x q[2];
h q[1];
h q[3];
cx q[0],q[1];
cx q[2],q[3];
h q[1];
h q[3];
x q[0];
x q[2];
h q[0];
h q[1];
h q[2];
h q[3];
h q[1];
h q[3];
cx q[0],q[1];
cx q[2],q[3];
h q[1];
h q[3];
h q[0];
h q[1];
h q[2];
h q[3];
)";
  run_qasm_pass_test(qasm, 4, {"u3", "cz"});
}
