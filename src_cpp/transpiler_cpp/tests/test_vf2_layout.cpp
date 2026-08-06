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
 *      WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <set>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"
#include "mapping/vf2_layout.h"

using namespace qcos;

namespace {

bool are_adjacent(int phys_a, int phys_b,
                  const std::vector<std::pair<int, int>>& coupling_list) {
  for (const auto& edge : coupling_list) {
    if ((edge.first == phys_a && edge.second == phys_b) ||
        (edge.first == phys_b && edge.second == phys_a)) {
      return true;
    }
  }
  return false;
}

bool has_duplicate(const std::vector<int>& mapping) {
  std::set<int> unique_set(mapping.begin(), mapping.end());
  return unique_set.size() != mapping.size();
}

// 验证映射中所有两比特门的两端在耦合图上相邻
bool all_gates_adjacent(
    const std::vector<GateOperation>& gates, const std::vector<int>& mapping,
    const std::vector<std::pair<int, int>>& coupling_list) {
  for (const auto& gate : gates) {
    if (gate.operation_type != OperationType::DOUBLE_QUBIT_OPERATION) continue;
    int p0 = mapping[gate.targets[0]];
    int p1 = mapping[gate.targets[1]];
    if (!are_adjacent(p0, p1, coupling_list)) return false;
  }
  return true;
}

GateOperation cx(int q0, int q1) {
  return GateOperation("cx", {q0, q1}, {},
                       OperationType::DOUBLE_QUBIT_OPERATION, false);
}

}  // namespace

/**
 * @brief 链式电路完美嵌入测试
 *
 * 3 比特链式电路 (q0-q1-q2)，物理拓扑为 5 节点线形 (0-1-2-3-4)。
 * VF2 应找到完美嵌入，所有门直接可执行，无需 SWAP。
 */
TEST(Vf2Layout, ChainCircuitPerfectEmbedding) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(1, 2)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
}

/**
 * @brief 星形电路完美嵌入测试
 *
 * 星形电路 (q0 连 q1,q2,q3)，物理拓扑含星形子结构。
 */
TEST(Vf2Layout, StarCircuitPerfectEmbedding) {
  // 物理拓扑: 0 是中心，连接 1,2,3,4；额外有 1-2 边
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {0, 2}, {0, 3}, {0, 4}, {1, 2}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(0, 2), cx(0, 3)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 4);

  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
  // q0 应映射到度数为 4 的中心节点 0
  EXPECT_EQ(mapping[0], 0);
}

/**
 * @brief 无解场景测试
 *
 * 电路需要三角形 (q0-q1, q1-q2, q0-q2)，
 * 但物理拓扑是纯线形，无三角形子图 -> VF2 应返回空。
 */
TEST(Vf2Layout, NoSolutionTriangleOnLine) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(1, 2), cx(0, 2)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 3);

  EXPECT_TRUE(mapping.empty());
}

/**
 * @brief 无两比特门时返回空
 */
TEST(Vf2Layout, NoTwoQubitGates) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}};
  std::vector<GateOperation> gates = {
      GateOperation("h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("h", {1}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
  };

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 2);
  EXPECT_TRUE(mapping.empty());
}

/**
 * @brief 保真度评分测试
 *
 * 两条等价的链式嵌入路径，验证 VF2 选择错误率更低的那条。
 * 路径 A: 0-1-2 (边 0-1 错误率 0.1, 边 1-2 错误率 0.1)
 * 路径 B: 3-4-5 (边 3-4 错误率 0.01, 边 4-5 错误率 0.01)
 * 电路 q0-q1-q2 链式，应选 B (3,4,5)。
 */
TEST(Vf2Layout, FidelityScoring) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {3, 4}, {4, 5}};
  std::vector<double> edge_fidelities = {0.9, 0.9,     // 路径 A: error=0.1
                                         0.99, 0.99};  // 路径 B: error=0.01
  std::vector<GateOperation> gates = {cx(0, 1), cx(1, 2)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, edge_fidelities, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));

  std::set<int> phys_set(mapping.begin(), mapping.end());
  // 应选低错误率路径 {3,4,5}
  EXPECT_TRUE(phys_set.count(3) > 0);
  EXPECT_TRUE(phys_set.count(4) > 0);
  EXPECT_TRUE(phys_set.count(5) > 0);
}

/**
 * @brief 多门共享同一边的重复交互
 *
 * 同一对逻辑比特有多个两比特门，交互图只有一条边但权重高。
 */
TEST(Vf2Layout, MultipleGatesSamePair) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(0, 1), cx(1, 2)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
}

/**
 * @brief 含孤立逻辑比特的映射
 *
 * 电路有 4 个逻辑比特，但 q3 只参与单比特门。
 * VF2 只匹配耦合的 q0-q1-q2，q3 应被分配到空闲物理比特。
 */
TEST(Vf2Layout, IsolatedLogicalQubit) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}};
  std::vector<GateOperation> gates = {
      cx(0, 1),
      cx(1, 2),
      GateOperation("h", {3}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
  };

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 4);

  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
  for (int phys : mapping) {
    EXPECT_GE(phys, 0);
    EXPECT_LE(phys, 4);
  }
}

/**
 * @brief 大规模链式电路
 *
 * 10 比特链式电路嵌入 20 节点线形拓扑。
 */
TEST(Vf2Layout, LongChainCircuit) {
  std::vector<std::pair<int, int>> coupling_list;
  for (int i = 0; i < 19; ++i) {
    coupling_list.push_back({i, i + 1});
  }
  std::vector<GateOperation> gates;
  for (int i = 0; i < 9; ++i) {
    gates.push_back(cx(i, i + 1));
  }

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 10);

  ASSERT_EQ(mapping.size(), 10u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
}

/**
 * @brief 环形电路嵌入含环子图的拓扑
 *
 * 4 比特环形电路 (q0-q1-q2-q3-q0)，
 * 物理拓扑含 4 节点环 (0-1-2-3-0) 加额外链 3-4-5。
 */
TEST(Vf2Layout, RingCircuitOnRingTopology) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3},
                                                    {3, 0}, {3, 4}, {4, 5}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(1, 2), cx(2, 3), cx(3, 0)};

  auto mapping = vf2_layout_mapping(gates, coupling_list, {}, 4);

  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(all_gates_adjacent(gates, mapping, coupling_list));
}

/**
 * @brief 空耦合图报错
 */
TEST(Vf2Layout, EmptyCouplingList) {
  std::vector<std::pair<int, int>> coupling_list;
  std::vector<GateOperation> gates = {cx(0, 1)};

  EXPECT_THROW(vf2_layout_mapping(gates, coupling_list, {}, 2),
               std::invalid_argument);
}

/**
 * @brief 逻辑比特数 > 物理比特数报错
 */
TEST(Vf2Layout, LogicalExceedsPhysical) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}};
  std::vector<GateOperation> gates = {cx(0, 1), cx(1, 2)};

  EXPECT_THROW(vf2_layout_mapping(gates, coupling_list, {}, 3),
               std::invalid_argument);
}
