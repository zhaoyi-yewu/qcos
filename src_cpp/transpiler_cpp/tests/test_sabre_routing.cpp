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
  SABRE sabre(coupling_list, edge_fidelities, single_qubit_fidelities, 0.8);
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
