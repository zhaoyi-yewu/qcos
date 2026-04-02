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

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <iostream>
#include <vector>

#include "mapping/sabre_routing.h"
#include "utils/load_files.h"

using namespace qcos;
namespace fs = std::filesystem;

// ...WuYueOS/samples/
std::string data_dir = std::string(TEST_DATA_DIR);
// ...WuYueOS/etc/
std::string topo_dir = std::string(TEST_TOPOLOGY_DIR);

/**
 * @brief 友元函数，验证物理门序列是否正确实现逻辑电路的routing。
 * 模拟执行物理门序列，动态更新逻辑->物理映射。
 * @param logical_gates 逻辑电路双比特门列表
 * @param physical_gates 物理门序列，可能包含SWAP
 * @param initial_l2p 初始逻辑->物理映射
 * @return 如果物理门序列可行返回true，否则false
 */
bool qcos::validate_routing(const SABRE& sabre,
                            const std::vector<GateOperation>& logical_gates,
                            const std::vector<GateOperation>& physical_gates,
                            std::vector<int>& initial_l2p) {
  int logic_qubit_num = sabre.get_qubit_num_from_ir(logical_gates);
  // 若初始映射为空，生成顺序映射
  if (initial_l2p.empty()) {
    initial_l2p.resize(logic_qubit_num);
    for (int i = 0; i < logic_qubit_num; ++i) initial_l2p[i] = i;
  }

  // 构造DAG
  std::vector<std::shared_ptr<Node>> pre_nodes(logic_qubit_num, nullptr);
  std::vector<std::shared_ptr<Node>> front_layer;
  std::vector<std::shared_ptr<Node>> all_nodes;
  for (const auto& gate : logical_gates) {
    auto node = std::make_shared<Node>(gate);
    int pre_number = 0;

    if (node->bits.size() == 2) {
      for (int bit : node->bits) {
        auto pre = pre_nodes[bit];
        if (pre != nullptr) {
          auto it = std::find(pre->edges.begin(), pre->edges.end(), node);
          if (it == pre->edges.end()) {
            pre->edges.push_back(node);
            pre_number++;
          }
        }
      }
      for (int bit : node->bits) pre_nodes[bit] = node;
      node->pre_number = pre_number;
      if (pre_number == 0) front_layer.push_back(node);
    }
    all_nodes.push_back(node);
  }

  std::vector<int> l2p = initial_l2p;
  std::vector<int> p2l(sabre.phy_qubit_num_, -1);
  for (int l = 0; l < (int)l2p.size(); ++l) {
    if (l2p[l] >= 0 && l2p[l] < sabre.phy_qubit_num_) p2l[l2p[l]] = l;
  }

  // 模拟执行
  for (const auto& phy_gate : physical_gates) {
    if (phy_gate.targets.size() == 1) continue;

    // 物理比特
    int p0 = phy_gate.targets[0];
    int p1 = phy_gate.targets[1];

    // 更新映射关系
    if (phy_gate.name == "swap") {
      int l0 = p2l[p0];
      int l1 = p2l[p1];
      std::swap(p2l[p0], p2l[p1]);
      if (l0 != -1) l2p[l0] = p1;
      if (l1 != -1) l2p[l1] = p0;
      continue;
    }

    // 验证当前两个物理比特之间是否有耦合连接
    if (!sabre.adj_list_.at(p0).count(p1)) return false;

    bool matched = false;
    // 寻找并执行对应的逻辑门
    for (int i = 0; i < (int)front_layer.size(); ++i) {
      auto node = front_layer[i];
      int l0 = node->bits[0];
      int l1 = node->bits[1];

      if ((l2p[l0] == p0 && l2p[l1] == p1) ||
          (l2p[l0] == p1 && l2p[l1] == p0)) {
        for (auto& succ : node->edges) {
          succ->pre_number--;
          if (succ->pre_number == 0) front_layer.push_back(succ);
        }
        front_layer.erase(front_layer.begin() + i);
        matched = true;
        break;
      }
    }

    if (!matched) return false;
  }

  // 判断是否所有逻辑门均执行
  for (const auto& node : all_nodes) {
    if (node->pre_number > 0) return false;
  }

  return true;
}

/**
 * @brief 遍历文件夹内所有qasm文件，使用SABRE路由并验证结果
 * @param folder_path qasm文件夹路径
 * @param config_path 物理拓扑配置文件路径
 */
void routing_and_validate_qasmfiles(const std::string& folder_path,
                                    const std::string& config_path) {
  // 加载物理拓扑
  auto coupling_list = load_config_file(config_path);
  SABRE sabre(coupling_list);

  // 遍历文件夹，逐个处理并验证
  for (const auto& entry : fs::directory_iterator(folder_path)) {
    if (!entry.is_regular_file()) continue;
    if (entry.path().extension() != ".qasm") continue;

    std::string qasm_path = entry.path().string();
    std::cout << std::string(20, '=') << std::endl;
    std::cout << "Processing: " << qasm_path << std::endl;

    // 加载逻辑电路
    auto logical_gates = load_qasm_to_gate_list(qasm_path);

    auto t0 = std::chrono::high_resolution_clock::now();
    // 执行路由
    std::vector<int> initial_l2p;
    sabre.execute(logical_gates, initial_l2p);
    auto t1 = std::chrono::high_resolution_clock::now();
    double route_seconds = std::chrono::duration<double>(t1 - t0).count();

    const auto& physical_gates = sabre.get_physical_gates();
    // 验证结果
    bool valid =
        validate_routing(sabre, logical_gates, physical_gates, initial_l2p);
    if (valid) {
      std::cout << "Validation SUCCESS\n";
    } else {
      std::cout << "Validation FAILED\n";
    }
    std::cout << "Routing time: " << route_seconds << " ms\n";
  }
}

/**
 * 测试SABRE算法
 * 物理拓扑: 0 -- 1 -- 2 (线性)
 * 逻辑门: cx(q0, q2)
 */
TEST(SabreCoreTest, LinearTopologySwap) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<GateOperation> logical_circuit = {GateOperation(
      "cx", {0, 2}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};
  std::vector<int> initial_l2p = {0, 1, 2};

  SABRE sabre(coupling_list, 20, 0.5, 0.001);
  sabre.execute(logical_circuit, initial_l2p);
  const auto& physical_gates = sabre.get_physical_gates();

  EXPECT_GE(physical_gates.size(), 2);
  bool has_swap =
      std::any_of(physical_gates.begin(), physical_gates.end(),
                  [](const GateOperation& g) { return g.name == "swap"; });
  EXPECT_TRUE(has_swap)
      << "SABRE should insert a swap for non-adjacent qubits (0, 2)";
}

#ifdef TEST_BENCH
TEST(SabreCoreTest, Benchmark) {
  std::string config_path = topo_dir + "/topology/spinq_rpc_156.toml";
  std::string qasm_dir = data_dir + "/qasm/benchpress/qft";
  routing_and_validate_qasmfiles(qasm_dir, config_path);
}

TEST(SabreCoreTest, LoadAndRoute) {
  // topology
  std::string config_path = topo_dir + "/topology/spinq_rpc_156.toml";
  // qasm file
  std::string small_qasm_dir = data_dir + "/qasm/benchpress/qasmbench-small";
  std::string qasm_path =
      small_qasm_dir + "/adder_n4/adder_n4_transpiled.qasm";

  auto logical_circuit = load_qasm_to_gate_list(qasm_path);
  auto coupling_list = load_config_file(config_path);

  // 统计逻辑双比特门
  size_t logical_double_gates = 0;
  for (const auto& gate : logical_circuit) {
    if (gate.operation_type == OperationType::DOUBLE_QUBIT_OPERATION)
      logical_double_gates++;
  }

  SABRE sabre(coupling_list);
  std::cout << "开始对 " << logical_circuit.size() << " 个门进行路由映射..."
            << std::endl;
  auto start = std::chrono::high_resolution_clock::now();
  // routing
  sabre.execute(logical_circuit);
  auto end = std::chrono::high_resolution_clock::now();
  auto physical_circuit = sabre.get_physical_gates();
  std::chrono::duration<double> sec = end - start;
  std::chrono::duration<double, std::milli> ms = end - start;

  // 统计swap数量
  size_t physical_double_gates = 0;
  size_t swap_count = 0;
  for (const auto& gate : physical_circuit) {
    if (gate.name == "swap") swap_count++;
    if (gate.operation_type == OperationType::DOUBLE_QUBIT_OPERATION)
      physical_double_gates++;
  }

  // 输出报告
  std::cout << "\n" << std::string(50, '=') << std::endl;
  std::cout << "             SABRE 性能分析" << std::endl;
  std::cout << std::string(50, '-') << std::endl;
  std::cout << std::left << std::setw(25) << "总运行时间:" << std::fixed
            << std::setprecision(3) << ms.count() << " ms" << std::endl;
  std::cout << std::left << std::setw(25) << "处理速度:" << std::fixed
            << std::setprecision(0) << (logical_circuit.size() / sec.count())
            << " gates/sec" << std::endl;

  std::cout << std::string(50, '-') << std::endl;
  std::cout << std::left << std::setw(25)
            << "逻辑双比特门:" << logical_double_gates << std::endl;
  std::cout << std::left << std::setw(25)
            << "物理双比特门:" << physical_double_gates << std::endl;
  std::cout << std::left << std::setw(25) << "新增 swap 数量:"
            << "\033[1;32m" << swap_count << "\033[0m" << std::endl;
  std::cout << std::string(50, '=') << "\n" << std::endl;
}
#endif
