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

#include <set>
#include <vector>

#include "mapping/sabre_routing.h"

using namespace qcos;

namespace {

std::shared_ptr<BaseOperation> make_2q_gate(const std::string& name, int q0,
                                            int q1) {
  return std::make_shared<BaseOperation>(
      name, std::vector<int>{q0, q1}, std::vector<double>{},
      OperationType::DOUBLE_QUBIT_OPERATION);
}

std::shared_ptr<BaseOperation> make_1q_gate(const std::string& name, int q0) {
  return std::make_shared<BaseOperation>(
      name, std::vector<int>{q0}, std::vector<double>{},
      OperationType::SINGLE_QUBIT_OPERATION);
}

}  // namespace

TEST(SabreRouting, LinearTopology) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_2q_gate("cx", 0, 2)};

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  EXPECT_GE(phys.size(), 1u);
}

TEST(SabreRouting, DisconnectedTopology) {
  // 非连通拓扑：{0,1} 和 {5,6,7} 两个分量
  // SABRE 应选择最大连通分量 {5,6,7} 进行路由
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {5, 6}, {6, 7}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_2q_gate("cx", 0, 1)};

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  std::set<int> used_qubits;
  for (const auto& gate : phys) {
    for (int target : gate->targets) {
      used_qubits.insert(target);
    }
  }
  for (int qubit : used_qubits) {
    EXPECT_TRUE(qubit == 5 || qubit == 6 || qubit == 7)
        << "物理位 " << qubit << " 不在最大连通分量 {5,6,7} 中";
  }
}

TEST(SabreRouting, FidelityAwareRouting) {
  // 线性拓扑 0-1-2-3，边 0-1 保真度低 (0.5)，其他边高 (0.99)
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<double> edge_fidelities = {0.5, 0.99, 0.99};
  std::vector<double> single_qubit_fidelities = {0.99, 0.99, 0.99, 0.99};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_2q_gate("cx", 0, 1),
      make_2q_gate("cx", 1, 2),
  };

  // 阈值 0.8 应过滤掉边 0-1
  SABRE sabre(coupling_list, edge_fidelities, single_qubit_fidelities,
              "vf2_layout", {}, 0.8);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  EXPECT_GE(phys.size(), 2u);

  // 所有 cx 门不应使用被过滤的低保真度边 (0,1)
  for (const auto& gate : phys) {
    if (gate->name == "cx" && gate->targets.size() == 2) {
      int q0 = gate->targets[0], q1 = gate->targets[1];
      bool uses_filtered_edge = (q0 == 0 && q1 == 1) || (q0 == 1 && q1 == 0);
      EXPECT_FALSE(uses_filtered_edge) << "门使用了被过滤的低保真度边 (0,1)";
    }
  }
}
// 多比特门 + target_bits + 编号空缺: cx q[0],q[3], target_bits=[1,2]
// 稠密化前 SABRE 需 4 个物理位(编号空间), 诱导子图仅 2 节点 -> 失败
// 稠密化后 logic_qubit_num_=2, 诱导子图 2 节点, 路由成功
TEST(SabreRouting, MultiQubitTargetBitsWithHoles) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 5}, {5, 6}, {6, 7}};
  std::vector<double> edge_fidelities(7, 0.99);
  std::vector<double> single_fids = {0.90, 0.92, 0.99, 0.95,
                                     0.88, 0.97, 0.91, 0.89};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_2q_gate("cx", 0, 3),
      make_1q_gate("h", 0),
  };

  SABRE sabre(coupling_list, edge_fidelities, single_fids, "vf2_layout",
              {1, 2});
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  // cx + h + 2 measures
  ASSERT_EQ(phys.size(), 4u);
  for (const auto& gate : phys) {
    for (int target : gate->targets) {
      EXPECT_TRUE(target == 1 || target == 2)
          << "物理位 " << target << " 不在 target_bits {1,2} 中";
    }
  }

  const auto& mapping = sabre.get_final_mapping();
  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], -1);
  EXPECT_EQ(mapping[2], -1);
  EXPECT_EQ(mapping[3], 2);
}

// 全单比特门 + 编号空缺 + 无 target_bits + 保真度: 自动选 top-N 保真度位
TEST(SabreRouting, SingleQubitHolesAutoFidelity) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 5}, {5, 6}, {6, 7}};
  std::vector<double> edge_fidelities(7, 0.99);
  std::vector<double> single_fids = {0.90, 0.92, 0.99, 0.95,
                                     0.88, 0.97, 0.91, 0.89};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_1q_gate("h", 0),
      make_1q_gate("h", 3),
  };

  SABRE sabre(coupling_list, edge_fidelities, single_fids);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  std::set<int> used_phys;
  for (const auto& gate : phys) {
    for (int target : gate->targets) {
      used_phys.insert(target);
    }
  }
  EXPECT_EQ(used_phys.count(2), 1u);
  EXPECT_EQ(used_phys.count(5), 1u);
  EXPECT_EQ(used_phys.size(), 2u);

  const auto& mapping = sabre.get_final_mapping();
  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_EQ(mapping[0], 2);
  EXPECT_EQ(mapping[1], -1);
  EXPECT_EQ(mapping[2], -1);
  EXPECT_EQ(mapping[3], 5);
}

// 全单比特门 + 编号空缺 + target_bits: 映射到指定物理位
TEST(SabreRouting, SingleQubitHolesWithTargetBits) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}, {4, 5}, {5, 6}, {6, 7}};
  std::vector<double> edge_fidelities(7, 0.99);
  std::vector<double> single_fids = {0.90, 0.92, 0.99, 0.95,
                                     0.88, 0.97, 0.91, 0.89};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_1q_gate("h", 0),
      make_1q_gate("h", 3),
  };

  SABRE sabre(coupling_list, edge_fidelities, single_fids, "vf2_layout",
              {5, 7});
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  std::set<int> used_phys;
  for (const auto& gate : phys) {
    for (int target : gate->targets) {
      used_phys.insert(target);
    }
  }
  EXPECT_EQ(used_phys.count(5), 1u);
  EXPECT_EQ(used_phys.count(7), 1u);
  EXPECT_EQ(used_phys.size(), 2u);

  const auto& mapping = sabre.get_final_mapping();
  ASSERT_EQ(mapping.size(), 4u);
  EXPECT_EQ(mapping[0], 5);
  EXPECT_EQ(mapping[1], -1);
  EXPECT_EQ(mapping[2], -1);
  EXPECT_EQ(mapping[3], 7);
}

// 无编号空缺的回归测试: 确保稠密化不影响正常电路
TEST(SabreRouting, NoHolesRegression) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<double> edge_fidelities = {0.99, 0.99};
  std::vector<double> single_fids = {0.99, 0.99, 0.99};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_2q_gate("cx", 0, 1),
      make_1q_gate("h", 0),
  };

  SABRE sabre(coupling_list, edge_fidelities, single_fids);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();
  EXPECT_GE(phys.size(), 1u);

  const auto& mapping = sabre.get_final_mapping();
  ASSERT_EQ(mapping.size(), 2u);
  for (int val : mapping) {
    EXPECT_GE(val, 0) << "无空缺电路不应有 -1 映射";
  }
}

// 全单比特门, 逻辑比特数超过耦合图比特数, 但有保真度数据覆盖全部芯片比特
// 芯片有 8 比特 (single_fids 8 个), 耦合图只有 3 比特 {0,1,2}
// 电路用 5 比特 -> identity 回退, single_fids.size()=8 >= 5 -> 通过
TEST(SabreRouting, SingleQubitExceedsCouplingWithFidelity) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<double> edge_fidelities = {0.99, 0.99};
  std::vector<double> single_fids = {0.99, 0.99, 0.99, 0.99,
                                     0.99, 0.99, 0.99, 0.99};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_1q_gate("h", 0), make_1q_gate("h", 1), make_1q_gate("h", 2),
      make_1q_gate("h", 3), make_1q_gate("h", 4),
  };

  SABRE sabre(coupling_list, edge_fidelities, single_fids);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  // 5 个 h 门 + 5 个自动 measure = 10 个输出门
  EXPECT_EQ(phys.size(), 10u);

  // identity 映射: 逻辑 i -> 物理 i
  const auto& mapping = sabre.get_final_mapping();
  ASSERT_EQ(mapping.size(), 5u);
  for (int i = 0; i < 5; ++i) {
    EXPECT_EQ(mapping[i], i) << "逻辑 " << i << " 应映射到物理 " << i;
  }
}

// 全单比特门, 逻辑比特数超过芯片比特数 (无保真度数据)
// 耦合图只有 3 比特 {0,1,2}, max_chip_qubit_ = 2, 电路用 5 比特
// 无保真度数据: available_phys = max_chip_qubit_+1 = 3 < 5 -> 抛异常
TEST(SabreRouting, SingleQubitExceedsChipNoFidelity) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<double> edge_fidelities = {0.99, 0.99};

  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      make_1q_gate("h", 0), make_1q_gate("h", 1), make_1q_gate("h", 2),
      make_1q_gate("h", 3), make_1q_gate("h", 4),
  };

  SABRE sabre(coupling_list, edge_fidelities);
  EXPECT_THROW(sabre.execute(circuit), std::invalid_argument);
}
