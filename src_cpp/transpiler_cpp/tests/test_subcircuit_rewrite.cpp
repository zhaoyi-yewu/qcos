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
#include "optimizer/subcircuit_rewrite.h"

using namespace qcos;

namespace {

std::shared_ptr<BaseOperation> make_gate(
    const std::string& name, const std::vector<int>& targets,
    const std::vector<double>& args = {}) {
  return std::shared_ptr<BaseOperation>(create_gate(name, targets, args));
}

std::vector<std::string> node_names(const std::vector<DAGOpNode*>& nodes) {
  std::vector<std::string> names;
  names.reserve(nodes.size());
  for (DAGOpNode* node : nodes) {
    names.push_back(node->name());
  }
  return names;
}

}  // namespace

TEST(EquivalencePassTest, RewritesFixedTemplates) {
  EquivalencePass optimizer;

  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        make_gate("h", {0}), make_gate("z", {0}), make_gate("h", {0})};
    DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

    EXPECT_EQ(optimizer.run(dag), 2);
    const auto counts = dag.count_ops();
    EXPECT_EQ(counts.size(), 1u);
    EXPECT_EQ(counts.at("x"), 1);
  }

  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        make_gate("h", {0}), make_gate("x", {0}), make_gate("h", {0})};
    DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

    EXPECT_EQ(optimizer.run(dag), 2);
    const auto counts = dag.count_ops();
    EXPECT_EQ(counts.size(), 1u);
    EXPECT_EQ(counts.at("z"), 1);
  }

  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        make_gate("x", {1}), make_gate("ry", {1}, {0.1}), make_gate("x", {1})};
    DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

    EXPECT_EQ(optimizer.run(dag), 2);
    const auto nodes = dag.topological_op_nodes();
    ASSERT_EQ(nodes.size(), 1u);
    EXPECT_EQ(nodes[0]->name(), "ry");
    ASSERT_EQ(nodes[0]->op->arg_value.size(), 1u);
    EXPECT_NEAR(nodes[0]->op->arg_value[0], -0.1, 1e-12);
  }
}

TEST(EquivalencePassTest, RewritesMultipleTemplatesInOnePass) {
  EquivalencePass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      make_gate("h", {0}), make_gate("x", {0}), make_gate("h", {0}),
      make_gate("h", {1}), make_gate("z", {1}), make_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag), 4);

  const auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 2u);
  EXPECT_EQ(node_names(nodes), (std::vector<std::string>{"z", "x"}));
  EXPECT_EQ(nodes[0]->op->targets, (std::vector<int>{0}));
  EXPECT_EQ(nodes[1]->op->targets, (std::vector<int>{1}));
}

TEST(EquivalencePassTest, HonorsBasisFilter) {
  EquivalencePass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      make_gate("h", {0}), make_gate("x", {0}),         make_gate("h", {0}),
      make_gate("x", {1}), make_gate("ry", {1}, {0.1}), make_gate("x", {1})};

  DAGCircuit dag_hxh = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(optimizer.run(dag_hxh, std::set<std::string>{"h", "x", "z"}), 2);
  auto nodes = dag_hxh.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 4u);
  EXPECT_EQ(node_names(nodes),
            (std::vector<std::string>{"z", "x", "ry", "x"}));

  DAGCircuit dag_xryx = DAGCircuit::ir_to_dag(ir);
  EXPECT_EQ(optimizer.run(dag_xryx, std::set<std::string>{"ry", "x"}), 2);
  nodes = dag_xryx.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 4u);
  EXPECT_EQ(node_names(nodes),
            (std::vector<std::string>{"h", "x", "h", "ry"}));
  ASSERT_EQ(nodes.back()->op->arg_value.size(), 1u);
  EXPECT_NEAR(nodes.back()->op->arg_value[0], -0.1, 1e-12);
}

TEST(EquivalencePassTest, DoesNotRewriteAcrossDifferentTargets) {
  EquivalencePass optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      make_gate("h", {0}), make_gate("z", {1}), make_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.run(dag), 0);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("h"), 2);
  EXPECT_EQ(counts.at("z"), 1);
}