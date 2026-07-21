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

#include <filesystem>
#include <fstream>
#include <iostream>
#include <set>
#include <vector>

#include "compiler/qasm_to_ir.hpp"
#include "mapping/chip_data.h"
#include "mapping/dense_layout.h"

using namespace qcos;

namespace fs = std::filesystem;

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

}  // namespace

/**
 * @brief 基础连通性测试
 *
 * 4 节点环形拓扑（0-1-2-3-0），2 个逻辑比特 + 1 个 CX 门。
 * 验证映射结果长度正确、无重复物理比特、物理 ID
 * 在合法范围内、两个物理比特相邻。
 */
TEST(DenseLayout, BasicConnectivity) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}, {3, 0}, {0, 3}};
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 2);

  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_FALSE(has_duplicate(mapping));
  for (int phys_q : mapping) {
    EXPECT_GE(phys_q, 0);
    EXPECT_LE(phys_q, 3);
  }
  EXPECT_TRUE(are_adjacent(mapping[0], mapping[1], coupling_list));
}

/**
 * @brief 密度优先子图选择测试
 *
 * 5 节点线形拓扑（0-1-2-3-4），额外添加 1-3 边使中段 {1,2,3} 密度最高。
 * 验证算法选中密度最高的子图 {1,2,3} 而非端点区域。
 */
TEST(DenseLayout, DenseSubgraphSelection) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3},
      {3, 2}, {3, 4}, {4, 3}, {1, 3}, {3, 1}};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  std::set<int> phys_set(mapping.begin(), mapping.end());
  EXPECT_TRUE(phys_set.count(1) > 0);
  EXPECT_TRUE(phys_set.count(2) > 0);
  EXPECT_TRUE(phys_set.count(3) > 0);
}

/**
 * @brief 重复边去重测试
 *
 * coupling_list 包含重复边（如 (0,1) 出现两次）。
 * 验证 std::set 去重机制：映射结果正确且不崩溃。
 */
TEST(DenseLayout, DuplicateEdgesInCouplingList) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {0, 1}, {1, 0}, {1, 2}, {2, 1}, {1, 2}, {2, 1}};
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 2);

  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_FALSE(has_duplicate(mapping));
  EXPECT_TRUE(are_adjacent(mapping[0], mapping[1], coupling_list));
}

/**
 * @brief 单向边双向构建测试
 *
 * coupling_list 仅含单向边（只有 (u,v) 无 (v,u)）。
 * 验证 build_adj_list 正确构建双向邻接表，BFS 能双向遍历。
 */
TEST(DenseLayout, UnidirectionalCouplingList) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  std::set<int> phys_set(mapping.begin(), mapping.end());
  EXPECT_EQ(phys_set.size(), 3u);
}

/**
 * @brief 稀疏物理 ID 测试
 *
 * 物理 ID 非连续（10, 20, 30）。
 * 验证算法基于最大 ID 推断物理比特数，不因 ID 稀疏而出错。
 */
TEST(DenseLayout, SparsePhysicalQubitIds) {
  std::vector<std::pair<int, int>> coupling_list = {
      {10, 20}, {20, 10}, {20, 30}, {30, 20}};
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 2);

  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_FALSE(has_duplicate(mapping));
  for (int phys_q : mapping) {
    EXPECT_TRUE(phys_q == 10 || phys_q == 20 || phys_q == 30);
  }
  EXPECT_TRUE(are_adjacent(mapping[0], mapping[1], coupling_list));
}

/**
 * @brief 全物理比特使用测试
 *
 * num_logical == num_physical == 3，边界条件。
 * 验证算法在逻辑比特数等于物理比特数时正确映射全部节点。
 */
TEST(DenseLayout, AllPhysicalQubitsUsed) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
  std::set<int> phys_set(mapping.begin(), mapping.end());
  EXPECT_EQ(phys_set.size(), 3u);
  EXPECT_TRUE(phys_set.count(0) > 0);
  EXPECT_TRUE(phys_set.count(1) > 0);
  EXPECT_TRUE(phys_set.count(2) > 0);
}

/**
 * @brief 边保真度影响测试
 *
 * 提供边保真度数组（中段边 0.80 较低），分别用空保真度和带保真度调用。
 * 验证两种模式都不崩溃、无重复。
 */
TEST(DenseLayout, EdgeFidelityInfluence) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 0}, {1, 2},
                                                    {2, 1}, {2, 3}, {3, 2}};
  std::vector<double> edge_fidelities = {0.99, 0.99, 0.80, 0.80, 0.99, 0.99};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping_no_fid = dense_layout_mapping(gates_list, coupling_list, {}, 3);
  auto mapping_with_fid =
      dense_layout_mapping(gates_list, coupling_list, edge_fidelities, 3);

  ASSERT_EQ(mapping_no_fid.size(), 3u);
  ASSERT_EQ(mapping_with_fid.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping_no_fid));
  EXPECT_FALSE(has_duplicate(mapping_with_fid));
}

/**
 * @brief 单逻辑比特测试
 *
 * 仅 1 个逻辑比特 + 单比特 H 门。
 * 验证返回长度为 1 的映射，物理 ID 在合法范围内。
 */
TEST(DenseLayout, SingleLogicalQubit) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}};
  std::vector<GateOperation> gates_list = {GateOperation(
      "h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true)};

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 1);

  ASSERT_EQ(mapping.size(), 1u);
  EXPECT_GE(mapping[0], 0);
  EXPECT_LE(mapping[0], 2);
}

/**
 * @brief 空门列表测试
 *
 * 空门列表 + num_logical=0。
 * 验证返回空映射。
 */
TEST(DenseLayout, EmptyGates) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}};
  std::vector<GateOperation> gates_list = {};

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 0);

  EXPECT_TRUE(mapping.empty());
}

/**
 * @brief 逻辑比特超限异常测试
 *
 * 逻辑比特数（4）超过物理比特数（3）。
 * 验证抛出 std::invalid_argument。
 */
TEST(DenseLayout, TooManyLogicalQubits) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {1, 2}, {2, 1}};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {2, 3}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  EXPECT_THROW(dense_layout_mapping(gates_list, coupling_list, {}, 4),
               std::invalid_argument);
}

/**
 * @brief 空耦合图异常测试
 *
 * 空耦合图。
 * 验证抛出 std::invalid_argument。
 */
TEST(DenseLayout, EmptyCouplingList) {
  std::vector<std::pair<int, int>> coupling_list = {};
  std::vector<GateOperation> gates_list = {GateOperation(
      "h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true)};

  EXPECT_THROW(dense_layout_mapping(gates_list, coupling_list, {}, 1),
               std::invalid_argument);
}

/**
 * @brief 不连通图测试
 *
 * 不连通图：0-1 和 3-4 两个连通分量，中间缺节点 2。
 * 3 个逻辑比特需要 3 个连通节点，验证不崩溃（算法可能回退到 identity 映射）。
 */
TEST(DenseLayout, DisconnectedGraph) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 0}, {3, 4}, {4, 3}};
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping = dense_layout_mapping(gates_list, coupling_list, {}, 3);

  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
}
