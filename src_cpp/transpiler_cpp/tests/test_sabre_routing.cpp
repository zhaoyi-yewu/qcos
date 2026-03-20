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
#include <vector>

#include "mapping/sabre_routing.h"
#include "utils/load_files.h"

using namespace qcos;

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
TEST(SabreCoreTest, LoadAndRoute) {
  // ...WuYueOS/samples/
  std::string data_dir = std::string(TEST_DATA_DIR);
  // ...WuYueOS/etc/
  std::string topo_dir = std::string(TEST_TOPOLOGY_DIR);

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
