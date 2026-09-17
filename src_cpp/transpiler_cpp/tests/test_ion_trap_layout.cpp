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

#include <chrono>
#include <set>
#include <vector>

#include "mapping/ion_trap_layout.h"

using namespace qcos;

namespace {

/**
 * 5 比特全连通离子阱。
 * 可靠性： (1,3)=(2,3)=(2,4)=0.99, (0,2)=(1,2)=(1,4)=0.98, 其余=0.97
 */
struct IonTrapFixture {
  std::vector<std::pair<int, int>> coupling_list;
  std::vector<double> edge_fidelities;
  std::vector<double> single_qubit_fidelities;

  IonTrapFixture() {
    double rel[5][5] = {{0, 0.97, 0.98, 0.97, 0.97},
                        {0.97, 0, 0.98, 0.99, 0.98},
                        {0.98, 0.98, 0, 0.99, 0.99},
                        {0.97, 0.99, 0.99, 0, 0.97},
                        {0.97, 0.98, 0.99, 0.97, 0}};
    for (int i = 0; i < 5; ++i)
      for (int j = 0; j < 5; ++j)
        if (i != j && rel[i][j] > 0) {
          coupling_list.emplace_back(i, j);
          edge_fidelities.push_back(rel[i][j]);
        }
    single_qubit_fidelities = {1.0, 1.0, 1.0, 1.0, 1.0};
  }
};

/**
 * 参数化全连通离子阱，用于不同规模的测试。
 * @param num_physical 物理比特数
 * @param best_a, best_b 保真度最高的物理对 (best_a, best_b)
 */
struct AllToAllFixture {
  int num_physical;
  int best_a, best_b;
  std::vector<std::pair<int, int>> coupling_list;
  std::vector<double> edge_fidelities;
  std::vector<double> single_qubit_fidelities;

  AllToAllFixture(int n, int a, int b)
      : num_physical(n), best_a(a), best_b(b) {
    for (int i = 0; i < n; ++i)
      for (int j = 0; j < n; ++j)
        if (i != j) {
          coupling_list.emplace_back(i, j);
          double f = 0.95 + 0.04 * ((i * 7 + j * 3) % 5) / 4.0;
          if ((i == a && j == b) || (i == b && j == a)) f = 0.999;
          edge_fidelities.push_back(f);
        }
    single_qubit_fidelities.assign(n, 1.0);
  }
};

bool has_duplicate(const std::vector<int>& mapping) {
  std::set<int> s(mapping.begin(), mapping.end());
  return s.size() != mapping.size();
}

}  // namespace

/**
 * 基础全连通离子阱测试（精确枚举路径）
 */
TEST(IonTrapLayout, BasicAllToAll) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 3);
}

/**
 * 最优对比特对选择：1 个 CNOT 应映射到 0.99 物理对
 */
TEST(IonTrapLayout, SelectsBestReliabilityPair) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 3);
}

/**
 * 频率加权：高频 CNOT(q0,q1)×10 应映射到 0.99 物理对
 */
TEST(IonTrapLayout, FrequencyWeighted) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list;
  for (int i = 0; i < 10; ++i)
    gates_list.emplace_back("cx", std::vector<int>{0, 1},
                            std::vector<double>{},
                            OperationType::DOUBLE_QUBIT_OPERATION, false);
  gates_list.emplace_back("cx", std::vector<int>{1, 2}, std::vector<double>{},
                          OperationType::DOUBLE_QUBIT_OPERATION, false);
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 3);
  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 3);
  EXPECT_EQ(mapping[2], 2);
}

/**
 * 无保真度数据返回恒等映射
 */
TEST(IonTrapLayout, NoFidelityIdentity) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list, {},
                                         fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_EQ(mapping[0], 0);
  EXPECT_EQ(mapping[1], 1);
}

/**
 * 单逻辑比特：无 CNOT，单比特保真度全 1.0，返回第一个物理比特
 */
TEST(IonTrapLayout, SingleLogicalQubit) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {GateOperation(
      "h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 1);
  ASSERT_EQ(mapping.size(), 1u);
  EXPECT_EQ(mapping[0], 0);
}

/**
 * 空电路
 */
TEST(IonTrapLayout, EmptyCircuit) {
  IonTrapFixture fix;
  auto mapping =
      ion_trap_layout_mapping({}, fix.coupling_list, fix.edge_fidelities,
                              fix.single_qubit_fidelities, 0);
  EXPECT_TRUE(mapping.empty());
}

/**
 * 无两比特门：单比特保真度全 1.0，返回前两个物理比特
 */
TEST(IonTrapLayout, NoTwoQubitGates) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {
      GateOperation("h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("x", {1}, {}, OperationType::SINGLE_QUBIT_OPERATION,
                    true)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_EQ(mapping[0], 0);
  EXPECT_EQ(mapping[1], 1);
}

/**
 * 三角交互：3 个 CNOT 形成完全图，应映射到 0.99/0.99/0.98 三角
 */
TEST(IonTrapLayout, ThreeQubitTriangle) {
  IonTrapFixture fix;
  std::vector<GateOperation> gates_list = {
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {1, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("cx", {0, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 3);
  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 2);
  EXPECT_EQ(mapping[2], 3);
}

/**
 * 对称可靠性：CX(0,1) 和 CX(1,0) 应映射到同一物理对
 */
TEST(IonTrapLayout, SymmetricReliability) {
  IonTrapFixture fix;
  auto mapping_fwd = ion_trap_layout_mapping(
      {GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                     false)},
      fix.coupling_list, fix.edge_fidelities, fix.single_qubit_fidelities, 2);
  auto mapping_rev = ion_trap_layout_mapping(
      {GateOperation("cx", {1, 0}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                     false)},
      fix.coupling_list, fix.edge_fidelities, fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping_fwd.size(), 2u);
  ASSERT_EQ(mapping_rev.size(), 2u);
  EXPECT_EQ(mapping_fwd[0], 1);
  EXPECT_EQ(mapping_fwd[1], 3);
  EXPECT_EQ(mapping_rev[0], 1);
  EXPECT_EQ(mapping_rev[1], 3);
}

/**
 * 大规模系统走贪心 + 局部搜索路径
 * 12 物理比特，P(12,4)>2000000，高频对映射到 (3,7)
 */
TEST(IonTrapLayout, LargeSystemGreedyLocalSearch) {
  AllToAllFixture fix(12, 3, 7);
  std::vector<GateOperation> gates_list;
  for (int i = 0; i < 10; ++i)
    gates_list.emplace_back("cx", std::vector<int>{0, 1},
                            std::vector<double>{},
                            OperationType::DOUBLE_QUBIT_OPERATION, false);
  gates_list.emplace_back("cx", std::vector<int>{1, 2}, std::vector<double>{},
                          OperationType::DOUBLE_QUBIT_OPERATION, false);
  gates_list.emplace_back("cx", std::vector<int>{2, 3}, std::vector<double>{},
                          OperationType::DOUBLE_QUBIT_OPERATION, false);
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 4);
  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_FALSE(has_duplicate(mapping));
  // 高频对应映射到保真度最高的物理对 (3,7) 或 (7,3)
  EXPECT_TRUE((mapping[0] == 3 && mapping[1] == 7) ||
              (mapping[0] == 7 && mapping[1] == 3));
}

/**
 * 大规模系统无两比特门
 */
TEST(IonTrapLayout, LargeSystemNoTwoQubitGates) {
  AllToAllFixture fix(12, 3, 7);
  std::vector<GateOperation> gates_list = {
      GateOperation("h", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("x", {1}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("h", {2}, {}, OperationType::SINGLE_QUBIT_OPERATION,
                    true)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 3);
  ASSERT_EQ(mapping.size(), 3u);
  EXPECT_FALSE(has_duplicate(mapping));
}

/**
 * 大规模系统无保真度数据返回恒等映射
 */
TEST(IonTrapLayout, LargeSystemNoFidelity) {
  AllToAllFixture fix(12, 3, 7);
  std::vector<GateOperation> gates_list = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list, {},
                                         fix.single_qubit_fidelities, 2);
  ASSERT_EQ(mapping.size(), 2u);
  EXPECT_EQ(mapping[0], 0);
  EXPECT_EQ(mapping[1], 1);
}

/**
 * 精确枚举上限测试：P(10,8)=1814400，测量耗时
 * 10 物理比特全连通，8 逻辑比特，高频对映射到 (4,9)
 */
TEST(IonTrapLayout, MaxBruteForcePerformance) {
  AllToAllFixture fix(10, 4, 9);
  std::vector<GateOperation> gates_list;
  for (int i = 0; i < 20; ++i)
    gates_list.emplace_back("cx", std::vector<int>{0, 1},
                            std::vector<double>{},
                            OperationType::DOUBLE_QUBIT_OPERATION, false);
  for (int i = 0; i < 5; ++i)
    gates_list.emplace_back("cx", std::vector<int>{1, 2},
                            std::vector<double>{},
                            OperationType::DOUBLE_QUBIT_OPERATION, false);
  gates_list.emplace_back("cx", std::vector<int>{2, 3}, std::vector<double>{},
                          OperationType::DOUBLE_QUBIT_OPERATION, false);

  auto start = std::chrono::high_resolution_clock::now();
  auto mapping = ion_trap_layout_mapping(gates_list, fix.coupling_list,
                                         fix.edge_fidelities,
                                         fix.single_qubit_fidelities, 8);
  auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::high_resolution_clock::now() - start);

  ASSERT_EQ(mapping.size(), 8u);
  EXPECT_FALSE(has_duplicate(mapping));
  // 高频对应映射到保真度最高的物理对 (4,9) 或 (9,4)
  EXPECT_TRUE((mapping[0] == 4 && mapping[1] == 9) ||
              (mapping[0] == 9 && mapping[1] == 4))
      << "Got (" << mapping[0] << "," << mapping[1] << ")";
  std::cout << "MaxBruteForce P(10,8)=1814400 elapsed: " << elapsed.count()
            << "ms" << std::endl;
}
