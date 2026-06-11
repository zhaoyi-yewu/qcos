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

#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "optimizer/inverse_cancellation.h"
using namespace qcos;

TEST(InverseCancellationTest, CancelsSelfInverseGates) {
  InverseCancellation optimizer(
      {InverseCancellation::InverseGateRule(H(std::vector<int>{0})),
       InverseCancellation::InverseGateRule(CX(std::vector<int>{0, 1})),
       InverseCancellation::InverseGateRule(Z(std::vector<int>{0}))});
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),     create_gate("h", {0}),
      create_gate("h", {1}),     create_gate("cx", {0, 1}),
      create_gate("cx", {0, 1}), create_gate("h", {1}),
      create_gate("z", {1}),     create_gate("z", {1}),
      create_gate("z", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  const int reduced = optimizer.run(dag);

  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("cx") == 0 ? 0 : counts.at("cx"), 0);
  EXPECT_TRUE(counts.count("h") == 0 || counts.at("h") == 0 ||
              counts.at("h") == 2);
  EXPECT_EQ(counts.at("z"), 1);
  EXPECT_GE(reduced, 6);
}

TEST(InverseCancellationTest, DoesNotCancelDifferentQargs) {
  InverseCancellation optimizer(
      {InverseCancellation::InverseGateRule(CX(std::vector<int>{0, 1})),
       InverseCancellation::InverseGateRule(CZ(std::vector<int>{0, 1}))});
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("cx", {0, 1}), create_gate("cx", {1, 0}),
      create_gate("cz", {0, 1}), create_gate("cz", {1, 0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag), 0);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("cx"), 2);
  EXPECT_EQ(counts.at("cz"), 2);
}

TEST(InverseCancellationTest, CancelsInversePairsAndHonorsBasis) {
  InverseCancellation optimizer(
      {InverseCancellation::InverseGateRule(S(std::vector<int>{0}),
                                            SDG(std::vector<int>{0})),
       InverseCancellation::InverseGateRule(T(std::vector<int>{0}),
                                            TDG(std::vector<int>{0}))});
  std::vector<std::shared_ptr<BaseOperation>> basis_filtered_ir = {
      create_gate("s", {0}), create_gate("sdg", {0}), create_gate("t", {1}),
      create_gate("tdg", {1})};

  DAGCircuit basis_filtered = DAGCircuit::ir_to_dag(basis_filtered_ir);
  EXPECT_EQ(optimizer.run(basis_filtered, std::set<std::string>{"s", "sdg"}),
            2);
  auto counts = basis_filtered.count_ops();
  EXPECT_EQ(counts.count("s") == 0 ? 0 : counts.at("s"), 0);
  EXPECT_EQ(counts.count("sdg") == 0 ? 0 : counts.at("sdg"), 0);
  EXPECT_EQ(counts.at("t"), 1);
  EXPECT_EQ(counts.at("tdg"), 1);

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("s", {0}), create_gate("sdg", {0}), create_gate("t", {1}),
      create_gate("tdg", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(optimizer.run(dag), 4);
  counts = dag.count_ops();
  EXPECT_EQ(counts.count("s"), 0u);
  EXPECT_EQ(counts.count("sdg"), 0u);
  EXPECT_EQ(counts.count("t"), 0u);
  EXPECT_EQ(counts.count("tdg"), 0u);
}

TEST(InverseCancellationTest, RejectsNonInverseGateRule) {
  EXPECT_THROW(InverseCancellation({InverseCancellation::InverseGateRule(
                   RX(std::vector<int>{0}, std::vector<double>{0.1}))}),
               std::invalid_argument);
}
