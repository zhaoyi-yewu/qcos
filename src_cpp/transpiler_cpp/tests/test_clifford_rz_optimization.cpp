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
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "optimizer/clifford_rz_optimization.h"

using namespace qcos;

namespace {

/**
 * @brief 收集 DAG 中所有 Rz 节点，按拓扑序返回
 * @param dag 目标 DAG
 * @return Rz 节点列表
 */
std::vector<DAGOpNode*> rz_nodes(DAGCircuit& dag) {
  std::vector<DAGOpNode*> nodes;
  for (DAGOpNode* node : dag.topological_op_nodes()) {
    if (node->name() == "rz") {
      nodes.push_back(node);
    }
  }
  return nodes;
}

}  // namespace

/*
 * get_next_node_on_specific_qubit 测试。
 * 验证 CX(0,1) 的控制位(0)后继是 X(0)，目标位(1)后继是 RZ(1,0.2)。
 *
 *      ┌─────────┐     ┌───┐
 * q_0: ┤ Rz(0.1) ├──■──┤ X ├───────────
 *      └─────────┘  │  └───┘
 *                 ┌─┴─┐┌─────────┐
 * q_1: ───────────┤ X ├┤ Rz(0.2) ├──────
 *                 └───┘└─────────┘
 */
TEST(CliffordRzOptimizationTest,
     GetNextNodeOnSpecificQubitUsesWireLocalOrder) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rz", {0}, {0.1}), create_gate("cx", {0, 1}),
      create_gate("rz", {1}, {0.2}), create_gate("x", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  const auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 4u);

  DAGOpNode* next_on_control =
      optimizer.get_next_node_on_specific_qubit(dag, nodes[1], 0);
  DAGOpNode* next_on_target =
      optimizer.get_next_node_on_specific_qubit(dag, nodes[1], 1);
  ASSERT_NE(next_on_control, nullptr);
  ASSERT_NE(next_on_target, nullptr);
  EXPECT_EQ(next_on_control->name(), "x");
  EXPECT_EQ(next_on_control->qargs, (std::vector<int>{0}));
  EXPECT_EQ(next_on_target->name(), "rz");
  EXPECT_EQ(next_on_target->qargs, (std::vector<int>{1}));
  EXPECT_THROW(optimizer.get_next_node_on_specific_qubit(dag, nodes[1], 2),
               std::invalid_argument);
}

/*
 * Rz 合并测试：相邻 Rz 直接合并 + H-CX-H 模板。
 * 前两个 Rz(0.1) 先合并为 Rz(0.2)，再跨过 H-CX-H 与最后的 Rz(0.1) 合并。
 *
 * q_0: ─────────────────────────────■──────────────────
 *      ┌─────────┐┌─────────┐┌───┐┌─┴─┐┌───┐┌─────────┐
 * q_1: ┤ Rz(0.1) ├┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ Rz(0.1) ├
 *      └─────────┘└─────────┘└───┘└───┘└───┘└─────────┘
 *
 * 优化后：
 * q_0: ─────────────■──────────
 *      ┌─────────┐┌─┴─┐
 * q_1: ┤ Rz(0.3) ├┤ X ├───────
 *      └─────────┘└───┘
 */
TEST(CliffordRzOptimizationTest, CancelSingleQubitGatesMergesAcrossTemplates) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rz", {1}, {0.1}), create_gate("rz", {1}, {0.1}),
      create_gate("h", {1}),         create_gate("cx", {0, 1}),
      create_gate("h", {1}),         create_gate("rz", {1}, {0.1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.cancel_single_qubit_gates(dag), 2);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("rz"), 1);
  EXPECT_EQ(counts.at("h"), 2);
  EXPECT_EQ(counts.at("cx"), 1);
  const auto nodes = rz_nodes(dag);
  ASSERT_EQ(nodes.size(), 1u);
  EXPECT_NEAR(nodes[0]->op->arg_value[0], 0.3, 1e-9);
}

/*
 * basis_gates 过滤测试：指定 {cx, rz} 时 H 不在 basis 中，
 * H-CX-H 模板被过滤掉，Rz 无法跨过 CX，优化效果为 0。
 *
 * q_0: ──────────────────■─────────■───────────────■─────────────
 *      ┌─────────┐┌───┐┌─┴─┐┌───┐┌─┴─┐┌─────────┐┌─┴─┐┌─────────┐
 * q_1: ┤ Rz(0.1) ├┤ H ├┤ X ├┤ H ├┤ X ├┤ Rz(0.2) ├┤ X ├┤ Rz(0.2) ├
 *      └─────────┘└───┘└───┘└───┘└───┘└─────────┘└───┘└─────────┘
 */
TEST(CliffordRzOptimizationTest, CancelSingleQubitGatesHonorsBasisFilter) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("rz", {1}, {0.1}), create_gate("h", {1}),
      create_gate("cx", {0, 1}),     create_gate("h", {1}),
      create_gate("cx", {0, 1}),     create_gate("rz", {1}, {0.2}),
      create_gate("cx", {0, 1}),     create_gate("rz", {1}, {0.2})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.cancel_single_qubit_gates(
                dag, std::set<std::string>{"cx", "rz"}),
            0);
  // 门数和参数均不变
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("rz"), 3);
  EXPECT_EQ(counts.at("h"), 2);
  EXPECT_EQ(counts.at("cx"), 3);
  const auto nodes = rz_nodes(dag);
  ASSERT_EQ(nodes.size(), 3u);
  EXPECT_NEAR(nodes[0]->op->arg_value[0], 0.1, 1e-9);
  EXPECT_NEAR(nodes[1]->op->arg_value[0], 0.2, 1e-9);
  EXPECT_NEAR(nodes[2]->op->arg_value[0], 0.2, 1e-9);
}

/*
 * CNOT 对消测试。
 *
 * test1 — 控制位模板，RZ(0,0.1) 在控制位线上被模板跨过，CX 对消。
 *              ┌─────────┐
 * q_0: ──■─────┤ Rz(0.1) ├────■──
 *      ┌─┴─┐   └─────────┘  ┌─┴─┐
 * q_1: ┤ X ├────────────────┤ X ├
 *      └───┘                └───┘
 *
 * test2 — 目标位模板跨过 H-CX-H，两端的 CX 对消。
 * q_0: ──■───────────────────■──
 *      ┌─┴─┐┌───┐     ┌───┐┌─┴─┐
 * q_1: ┤ X ├┤ H ├──■──┤ H ├┤ X ├
 *      └───┘└───┘┌─┴─┐└───┘└───┘
 * q_2: ──────────┤ X ├──────────
 *                └───┘
 */
TEST(CliffordRzOptimizationTest,
     CancelTwoQubitGatesCancelsControlAndTargetTemplates) {
  CliffordRzOptimization optimizer;

  // test1
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1}), create_gate("rz", {0}, {0.1}),
        create_gate("cx", {0, 1})};
    DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

    EXPECT_EQ(optimizer.cancel_two_qubit_gates(dag), 2);
    const auto counts = dag.count_ops();
    EXPECT_EQ(counts.at("rz"), 1);
    EXPECT_EQ(counts.count("cx"), 0u);
  }

  // test2
  {
    std::vector<std::shared_ptr<BaseOperation>> ir = {
        create_gate("cx", {0, 1}), create_gate("h", {1}),
        create_gate("cx", {1, 2}), create_gate("h", {1}),
        create_gate("cx", {0, 1})};
    DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

    EXPECT_EQ(optimizer.cancel_two_qubit_gates(dag), 2);
    const auto counts = dag.count_ops();
    EXPECT_EQ(counts.at("h"), 2);
    EXPECT_EQ(counts.at("cx"), 1);
  }
}

/*
 * run() 完整流程：两个 Z 门被 parameterize 转为 Rz(pi)，相邻合并为 2pi≈0，
 * deparameterize 阶段直接删除，最终只剩 CX。
 *
 *      ┌───┐     ┌───┐
 * q_0: ┤ Z ├──■──┤ Z ├           q_0: ──■──
 *      └───┘┌─┴─┐└───┘    →           ┌─┴─┐
 * q_1: ─────┤ X ├─────           q_1: ┤ X ├
 *           └───┘                     └───┘
 */
TEST(CliffordRzOptimizationTest,
     RunParameterizesAndDeparameterizesDiscretePhaseGates) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("z", {0}), create_gate("cx", {0, 1}), create_gate("z", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  optimizer.run(dag);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.size(), 1u);
  EXPECT_EQ(counts.at("cx"), 1);
}

// ===========================
// reduce_hadamard_gates 测试
// ===========================

/*
 * 模板 tpl[0]: H(0) S(0) H(0) → SDG(0) H(0) SDG(0), weight=1。
 *
 *      ┌───┐┌───┐┌───┐          ┌─────┐┌───┐┌─────┐
 * q_0: ┤ H ├┤ S ├┤ H ├  →  q_0: ┤ Sdg ├┤ H ├┤ Sdg ├
 *      └───┘└───┘└───┘          └─────┘└───┘└─────┘
 */
TEST(ReduceHadamardGatesTest, HSH_To_SdgHSdg) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 1);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("h"), 1);
  EXPECT_EQ(counts.at("sdg"), 2);
  EXPECT_EQ(counts.count("s"), 0u);
}

/*
 * 模板 tpl[1]: H(0) SDG(0) H(0) → S(0) H(0) S(0), weight=1。
 *
 *      ┌───┐┌─────┐┌───┐          ┌───┐┌───┐┌───┐
 * q_0: ┤ H ├┤ Sdg ├┤ H ├  →  q_0: ┤ S ├┤ H ├┤ S ├
 *      └───┘└─────┘└───┘          └───┘└───┘└───┘
 */
TEST(ReduceHadamardGatesTest, HSdgH_To_SHS) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("sdg", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 1);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("h"), 1);
  EXPECT_EQ(counts.at("s"), 2);
  EXPECT_EQ(counts.count("sdg"), 0u);
}

/*
 * 模板 tpl[2]: H(0) H(1) CX(0,1) H(0) H(1) → CX(1,0), weight=4。
 *
 *      ┌───┐     ┌───┐          ┌───┐
 * q_0: ┤ H ├──■──┤ H ├  →  q_0: ┤ X ├
 *      ├───┤┌─┴─┐├───┤          └─┬─┘
 * q_1: ┤ H ├┤ X ├┤ H ├  →  q_1:  ─■─
 *      └───┘└───┘└───┘
 */
TEST(ReduceHadamardGatesTest, HH_CX_HH_To_SwappedCX) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {1}), create_gate("cx", {0, 1}),
      create_gate("h", {0}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 4);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.count("h"), 0u);
  EXPECT_EQ(counts.at("cx"), 1);
  auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 1u);
  EXPECT_EQ(nodes[0]->name(), "cx");
  EXPECT_EQ(nodes[0]->qargs, (std::vector<int>{1, 0}));
}

/*
 * 模板 tpl[2] 在量子位 [1,2] 上，验证 CX 方向正确翻转。
 *
 *      ┌───┐     ┌───┐          ┌───┐
 * q_1: ┤ H ├──■──┤ H ├  →  q_1: ┤ X ├
 *      ├───┤┌─┴─┐├───┤          └─┬─┘
 * q_2: ┤ H ├┤ X ├┤ H ├  →  q_2:  ─■─
 *      └───┘└───┘└───┘
 */
TEST(ReduceHadamardGatesTest, HH_CX_HH_OnQubits12) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {2}), create_gate("cx", {1, 2}),
      create_gate("h", {1}), create_gate("h", {2})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 4);
  auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 1u);
  EXPECT_EQ(nodes[0]->name(), "cx");
  EXPECT_EQ(nodes[0]->qargs, (std::vector<int>{2, 1}));
}

/*
 * 模板 tpl[2]，电路 CX 方向为 (2,1)，验证结果翻转为 (1,2)。
 */
TEST(ReduceHadamardGatesTest, HH_CX21_HH_To_SwappedCX) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {2}), create_gate("cx", {2, 1}),
      create_gate("h", {1}), create_gate("h", {2})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 4);
  auto nodes = dag.topological_op_nodes();
  ASSERT_EQ(nodes.size(), 1u);
  EXPECT_EQ(nodes[0]->name(), "cx");
  EXPECT_EQ(nodes[0]->qargs, (std::vector<int>{1, 2}));
}

/*
 * 模板 tpl[3]: H(1) S(1) CX(0,1) SDG(1) H(1) → SDG(1) CX(0,1) S(1), weight=2。
 *
 * Before:                            After:
 * q_0: ────────────■────────────      q_0:  ────────■───────
 *      ┌───┐┌───┐┌─┴─┐┌────┐┌───┐          ┌─────┐┌─┴─┐┌───┐
 * q_1: ┤ H ├┤ S ├┤ X ├┤Sdg ├┤ H ├  →  q_1: ┤ Sdg ├┤ X ├┤ S ├
 *      └───┘└───┘└───┘└────┘└───┘          └─────┘└───┘└───┘
 */
TEST(ReduceHadamardGatesTest, H_S_CX_Sdg_H_To_Sdg_CX_S) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("s", {1}), create_gate("cx", {0, 1}),
      create_gate("sdg", {1}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 2);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("sdg"), 1);
  EXPECT_EQ(counts.at("cx"), 1);
  EXPECT_EQ(counts.at("s"), 1);
  EXPECT_EQ(counts.count("h"), 0u);
}

/*
 * 模板 tpl[4]: H(1) SDG(1) CX(0,1) S(1) H(1) → S(1) CX(0,1) SDG(1), weight=2。
 *
 * Before:                           After:
 * q_0: ─────────────■────────────     q_0: ───────■─────────
 *      ┌───┐┌────┐┌─┴─┐┌───┐┌───┐          ┌───┐┌─┴─┐┌─────┐
 * q_1: ┤ H ├┤Sdg ├┤ X ├┤ S ├┤ H ├  →  q_1: ┤ S ├┤ X ├┤ Sdg ├
 *      └───┘└────┘└───┘└───┘└───┘          └───┘└───┘└─────┘
 */
TEST(ReduceHadamardGatesTest, H_Sdg_CX_S_H_To_S_CX_Sdg) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("sdg", {1}),
      create_gate("cx", {0, 1}), create_gate("s", {1}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(dag), 2);
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("s"), 1);
  EXPECT_EQ(counts.at("cx"), 1);
  EXPECT_EQ(counts.at("sdg"), 1);
  EXPECT_EQ(counts.count("h"), 0u);
}

/*
 * 复合模板测试，一个电路同时匹配多个模板。
 *
 *      ┌───┐┌─────┐┌───┐
 * q_0: ┤ H ├┤ Sdg ├┤ H ├
 *      ├───┤└┬───┬┘├───┤
 * q_1: ┤ H ├─┤ X ├─┤ H ├
 *      ├───┤ └─┬─┘ ├───┤
 * q_2: ┤ H ├───■───┤ H ├
 *      └───┘       └───┘
 *
 * basis_gates = {h, sdg, s, cx} 时，所有模板可用：tpl[1] 匹配 qubit 0（减
 * 1）， tpl[2] 匹配 qubit 1,2（减 4），合计减 5。
 */
TEST(ReduceHadamardGatesTest, CombinedTemplatesWithBasisAllGates) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("sdg", {0}),
      create_gate("h", {0}), create_gate("h", {1}),
      create_gate("h", {2}), create_gate("cx", {2, 1}),
      create_gate("h", {1}), create_gate("h", {2})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(
                dag, std::set<std::string>{"h", "sdg", "s", "cx"}),
            5);
}

/*
 * basis_gates 不包含 h，所有模板都无法使用，应返回 0。
 */
TEST(ReduceHadamardGatesTest, BasisWithoutH_ReturnsZero) {
  CliffordRzOptimization optimizer;
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("sdg", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  EXPECT_EQ(optimizer.reduce_hadamard_gates(
                dag, std::set<std::string>{"sdg", "s", "cx"}),
            0);
  // 门数不变
  const auto counts = dag.count_ops();
  EXPECT_EQ(counts.at("h"), 2);
  EXPECT_EQ(counts.at("sdg"), 1);
}
