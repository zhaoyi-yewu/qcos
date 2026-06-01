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
#include <unordered_map>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "optimizer/template.h"
using namespace qcos;

/*
 * compare 方法的核心行为：
 *   从 start_node 出发，沿模板的量子比特线路在 circuit DAG 中 BFS 遍历，
 *   逐节点校验门名称和量子比特映射的一致性。若整个模板子图都能在 circuit
 *   DAG 中匹配到同构子图，返回模板节点到 circuit 节点的映射；否则返回空映射。
 */

/*
 * 单量子比特模板，完整匹配。
 * 模板 H(0) S(0) H(0) 在电路 H(0) S(0) H(0) 上应从第一个 H 开始匹配全部 3
 * 个节点。
 */
TEST(CompareTest, SingleQubitTemplateFullMatch) {
  auto tpls = generate_single_qubit_gate_templates();
  /*
   * tpls[4]: H(0) X(0) H(0), anchor=0
   * 将模板 DAG 当作匹配目标来测试 compare，不涉及 replacement。
   */
  ASSERT_GE(tpls.size(), 5u);
  auto& tpl = tpls[4];

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("x", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * Rz 对消模板，从 CX 节点开始 BFS 双向扩展匹配。
 * 模板 CX(0,1) RZ(1) CX(0,1)，anchor=1。
 * anchor=1 表示从模板 qubit 1 上的第一个门（CX）出发，
 * 后继方向找到 RZ(1) 和 CX(0,1)，前驱方向无更多门。
 */
TEST(CompareTest, RzCancelTemplateBidirectionalMatch) {
  auto tpls = generate_single_qubit_gate_templates();
  /*
   * tpls[1]: CX(0,1) RZ(1) CX(0,1), anchor=1
   */
  ASSERT_GE(tpls.size(), 2u);
  auto& tpl = tpls[1];

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("cx", {0, 1}), create_gate("rz", {1}, {0.1}),
      create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /*
   * 从第一个 CX(0,1) 开始匹配，电路 anchor_qubit=1 对应模板 anchor=1。
   * CX 作用在 [0,1]，所以 qargs[1]=1。
   */
  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[1]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * Rz 对消模板 H(1) CX(0,1) H(1)，anchor=1。
 * 用于检测 Rz 门可以跨过 H-CX-H 模式交换到另一侧。
 */
TEST(CompareTest, HcxhTemplateForRzCommutation) {
  auto tpls = generate_single_qubit_gate_templates();
  /*
   * tpls[0]: H(1) CX(0,1) H(1), anchor=1
   */
  ASSERT_GE(tpls.size(), 1u);
  auto& tpl = tpls[0];

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("cx", {0, 1}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * 多量子比特模板，从 CX 节点开始匹配（非首节点）。
 * H(1) S(1) CX(0,1) SDG(1) H(1)，anchor=0。
 * anchor=0 意味着从 qubit 0 的第一个门 CX(0,1) 出发，
 * BFS 向前驱方向找到 H(1) S(1)，向后继方向找到 SDG(1) H(1)。
 */
TEST(CompareTest, MultiQubitTemplateMatchFromMiddle) {
  std::vector<std::shared_ptr<BaseOperation>> tpl_ir = {
      create_gate("h", {1}), create_gate("s", {1}), create_gate("cx", {0, 1}),
      create_gate("sdg", {1}), create_gate("h", {1})};
  DAGCircuit tpl_dag = DAGCircuit::ir_to_dag(tpl_ir);
  OptimizingTemplate tpl(std::move(tpl_dag), std::nullopt, 0, 0);

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("s", {1}), create_gate("cx", {0, 1}),
      create_gate("sdg", {1}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /* 从 CX (topo[2]) 开始，qargs[0]=0 对应模板 anchor=0 */
  auto mapping = tpl.compare(dag, topo[2], topo[2]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 5u);
}

/*
 * CNOT 控制位对消模板。
 * generate_cnot_ctrl_templates 包含 CX(0,1) (anchor=0) 和 RZ(0) (anchor=0)。
 */
TEST(CompareTest, CnotCtrlTemplateMatch) {
  auto tpls = generate_cnot_ctrl_templates();
  ASSERT_GE(tpls.size(), 1u);
  auto& tpl = tpls[0]; /* CX(0,1), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 1u);
}

/*
 * CNOT 目标位对消模板。
 * generate_cnot_targ_templates 包含 CX(0,1) (anchor=1) 和 H(0) CX(0,1) H(0)
 * (anchor=0)。
 */
TEST(CompareTest, CnotTargTemplateMatch) {
  auto tpls = generate_cnot_targ_templates();
  ASSERT_GE(tpls.size(), 1u);
  auto& tpl = tpls[0]; /* CX(0,1), anchor=1 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("cx", {0, 1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[1]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 1u);
}

/*
 * 两量子比特 Hadamard 模板 H(0) H(1) CX(0,1) H(0) H(1)，anchor=0。
 */
TEST(CompareTest, TwoQubitHadamardTemplateMatch) {
  std::vector<std::shared_ptr<BaseOperation>> tpl_ir = {
      create_gate("h", {0}), create_gate("h", {1}), create_gate("cx", {0, 1}),
      create_gate("h", {0}), create_gate("h", {1})};
  DAGCircuit tpl_dag = DAGCircuit::ir_to_dag(tpl_ir);
  DAGCircuit rpl_dag = DAGCircuit::ir_to_dag({create_gate("cx", {1, 0})});
  OptimizingTemplate tpl(std::move(tpl_dag), std::move(rpl_dag), 0, 4);

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {1}), create_gate("cx", {0, 1}),
      create_gate("h", {0}), create_gate("h", {1})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 5u);
}

/*
 * 首节点门名称不一致，应返回空映射。
 */
TEST(CompareTest, NameMismatchReturnsEmpty) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* 期望 H(0) */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("x", {0}), create_gate("x", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  EXPECT_TRUE(mapping.empty());
}

/*
 * 模板嵌入在更大电路中，模板左侧有额外的量子门。
 * 电路: X(0), H(0), X(0), H(0)。模板 H(0) X(0) H(0) 从第二个节点开始匹配，
 * 左侧的 X(0) 不属于模板子图，不应影响匹配结果。
 */
TEST(CompareTest, TemplateWithExtraGatesOnLeft) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("x", {0}), create_gate("h", {0}), create_gate("x", {0}),
      create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /*
   * topo 顺序为 X(0), H(0), X(0), H(0)。
   * 从 topo[1]=H(0) 开始比较，只有 H,X,H 三个节点属于模板子图，
   * 左侧的 X(0) 不在模板匹配范围内。
   */
  auto mapping = tpl.compare(dag, topo[1], topo[1]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * 模板嵌入在更大电路中，模板右侧有额外的量子门。
 * 电路: H(0), X(0), H(0), Z(0)。模板 H(0) X(0) H(0) 从第一个节点开始匹配，
 * 右侧的 Z(0) 不属于模板子图，不应影响匹配结果。
 */
TEST(CompareTest, TemplateWithExtraGatesOnRight) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("x", {0}), create_gate("h", {0}),
      create_gate("z", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /*
   * topo 顺序为 H(0), X(0), H(0), Z(0)。
   * 从 topo[0]=H(0) 开始，BFS 沿后继方向找到 X(0), H(0) 后，
   * H(0) 的后继是 Z(0) 和 output，但模板中 H 是末端节点（后继只有 output），
   * 因此 Z(0) 不会被纳入 mapping。
   */
  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * 模板嵌入在更大电路中，模板左右两侧都有额外的量子门。
 * 电路: Z(0), H(0), X(0), H(0), Z(0)。模板 H(0) X(0) H(0)
 * 从第二个节点 (H) 开始匹配，仅中间三个节点匹配。
 */
TEST(CompareTest, TemplateWithExtraGatesOnBothSides) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("z", {0}), create_gate("h", {0}), create_gate("x", {0}),
      create_gate("h", {0}), create_gate("z", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /* 从 topo[1]=H(0) 开始，匹配中间的 H,X,H */
  auto mapping = tpl.compare(dag, topo[1], topo[1]->qargs[0]);
  ASSERT_FALSE(mapping.empty());
  EXPECT_EQ(mapping.size(), 3u);
}

/*
 * 模板门在同一量子比特，电路门分散在不同量子比特，后继查询不到对应邻居节点。
 */
TEST(CompareTest, DifferentQubitsNoMatch) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0) */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("x", {1}), create_gate("h", {2})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  EXPECT_TRUE(mapping.empty());
}

/*
 * start_node 为 nullptr 应直接返回空映射。
 */
TEST(CompareTest, NullStartNode) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[0];
  DAGCircuit dag;
  dag.add_qubits(2);

  auto mapping = tpl.compare(dag, nullptr, 0);
  EXPECT_TRUE(mapping.empty());
}

/*
 * anchor_qubit 越界导致 qubit_mapping 冲突。
 */
TEST(CompareTest, AnchorQubitOutOfRange) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("x", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  /*
   * anchor_qubit=5 但电路只有 qubit 0。
   * qubit_mapping={0:5}，H(0) 的 qargs[0]=0 应为 5 但电路 H(0) 的 qargs[0]=0。
   */
  auto mapping = tpl.compare(dag, topo[0], 5);
  EXPECT_TRUE(mapping.empty());
}

/*
 * 验证 mapping 中每个映射的电路节点都是有效指针且在正确的量子比特上。
 */
TEST(CompareTest, MappingContentsValid) {
  auto tpls = generate_single_qubit_gate_templates();
  auto& tpl = tpls[4]; /* H(0) X(0) H(0), anchor=0 */

  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("x", {0}), create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  ASSERT_EQ(mapping.size(), 3u);

  for (const auto& kv : mapping) {
    DAGOpNode* node = kv.second;
    ASSERT_NE(node, nullptr);
    EXPECT_EQ(node->qargs.size(), 1u);
    EXPECT_EQ(node->qargs[0], 0);
  }
}

/*
 * 两量子比特模板部分缺失后继节点，匹配失败。
 */
TEST(CompareTest, TwoQubitTemplatePartialMatchFails) {
  std::vector<std::shared_ptr<BaseOperation>> tpl_ir = {
      create_gate("h", {0}), create_gate("h", {1}), create_gate("cx", {0, 1}),
      create_gate("h", {0}), create_gate("h", {1})};
  DAGCircuit tpl_dag = DAGCircuit::ir_to_dag(tpl_ir);
  OptimizingTemplate tpl(std::move(tpl_dag), std::nullopt, 0, 0);

  /*
   * 电路缺少最后的 H(1)，qubit 1 上后继查询返回 nullptr。
   */
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {1}), create_gate("cx", {0, 1}),
      create_gate("h", {0})};
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);
  auto topo = dag.topological_op_nodes();

  auto mapping = tpl.compare(dag, topo[0], topo[0]->qargs[0]);
  EXPECT_TRUE(mapping.empty());
}
