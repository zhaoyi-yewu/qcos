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
#include <memory>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "optimizer/adjacent_optimization.h"

using namespace qcos;

TEST(AdjacentPhaseOptPassTest, MergesAdjacentParameterizedPhaseGates) {
  AdjacentPhaseOptPass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rx", {0}, {M_PI / 2.0}),
      create_gate("rx", {0}, {M_PI / 4.0}),
      create_gate("ry", {0}, {M_PI / 3.0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag), 1);

  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("rx"), 1);
  EXPECT_EQ(counts.at("ry"), 1);

  const auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 2u);
  EXPECT_EQ(nodes[0]->name(), "rx");
  ASSERT_FALSE(nodes[0]->op->arg_value.empty());
  EXPECT_NEAR(nodes[0]->op->arg_value[0], 3.0 * M_PI / 4.0, 1e-9);
}

TEST(AdjacentPhaseOptPassTest, HonorsBasisFilterForParameterizedPhaseGates) {
  AdjacentPhaseOptPass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rx", {0}, {M_PI / 2.0}),
      create_gate("rx", {0}, {M_PI / 4.0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag, std::set<std::string>{"ry"}), 0);

  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("rx"), 2);
}

TEST(AdjacentPhaseOptPassTest,
     ParameterizesAndDeparameterizesDiscreteRzPhaseGates) {
  AdjacentPhaseOptPass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("s", {0}),
                                                    create_gate("s", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag), 1);

  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("s"), 0u);
  EXPECT_EQ(counts.at("z"), 1);
  EXPECT_EQ(counts.count("rz"), 0u);
}