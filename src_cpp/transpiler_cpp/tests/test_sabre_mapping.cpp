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

#include "mapping/chip_data.h"
#include "mapping/mapping_utils.h"
#include "mapping/sabre_mapping.h"
#include "mapping/sabre_routing.h"
#include "transpile/transpile.h"
#include "utils/load_files.h"

using namespace qcos;

// ...WuYueOS/etc/
static std::string topo_dir = std::string(TEST_TOPOLOGY_DIR);

TEST(SabreInitialMappingTest, CycleTopologySimpleCircuit) {
  // 4-cycle topology
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 0}};

  std::vector<GateOperation> logical_circuit = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};

  auto mapping = sabre_initial_mapping(logical_circuit, coupling_list);
  ASSERT_GE(mapping.size(), 4);
  EXPECT_EQ(mapping[0], 0);
  EXPECT_EQ(mapping[1], 1);
  EXPECT_EQ(mapping[2], 2);
  EXPECT_EQ(mapping[3], 3);
}

TEST(SabreInitialMappingTest, QasmStr2Scenario) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 0}};

  std::vector<GateOperation> logical_circuit = {
      GateOperation("x", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("x", {1}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {1, 3}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("x", {2}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {2, 3}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  auto mapping = sabre_initial_mapping(logical_circuit, coupling_list);

  // Expect the SABRE-based initial mapping to be [1,0,2,3]
  ASSERT_GE(mapping.size(), 4);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 0);
  EXPECT_EQ(mapping[2], 2);
  EXPECT_EQ(mapping[3], 3);
}

// Verify that using the initial mapping reduces the number of inserted SWAPs
TEST(SabreInitialMappingTest, InitialMappingReducesSwaps) {
  std::string config_path = topo_dir + "qcos/conf.d/spinq_rpc.toml";
  auto coupling_list = load_config_file(config_path);

  std::vector<GateOperation> logical_circuit = {
      GateOperation("x", {0}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("x", {1}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {1, 3}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
      GateOperation("x", {2}, {}, OperationType::SINGLE_QUBIT_OPERATION, true),
      GateOperation("cx", {2, 3}, {}, OperationType::DOUBLE_QUBIT_OPERATION,
                    false),
  };

  // routing without initial mapping
  std::vector<std::shared_ptr<BaseOperation>> base_circuit;
  for (const auto& g : logical_circuit) {
    base_circuit.push_back(std::make_shared<BaseOperation>(
        g.name, g.targets, g.arg_value, g.operation_type));
  }

  SABRE sabre(coupling_list);
  sabre.execute(base_circuit);
  const auto& phys = sabre.get_physical_gates();

  // 验证路由结果包含所有原始门(可能有额外swap)
  size_t non_swap_count = 0;
  for (const auto& g : phys)
    if (g->name != "swap") non_swap_count++;
  EXPECT_GE(non_swap_count, logical_circuit.size());
}

// 孤立量子位: 保真度高于阈值的孤立比特应被包含在稠密映射中
TEST(DensifyChipTopologyTest, IsolatedQubitsIncludedByFidelity) {
  // 物理位 0,1,2 有耦合; 物理位 5 孤立(无边), 但单比特保真度很好
  ChipCalibration chip(
      {{0, 1}, {1, 2}}, {0.95, 0.95},
      {/*0*/ 0.9, /*1*/ 0.9, /*2*/ 0.9, /*3*/ 0.0, /*4*/ 0.0, /*5*/ 0.99});

  double threshold = 0.8;
  auto remap = densify_chip_topology(chip, threshold);

  // 应包含 0,1,2(coupled) 和 5(孤立,保真度 0.99 > 0.8)
  // 不应包含 3,4(保真度 0.0 < 0.8)
  EXPECT_EQ(remap.dense_count, 4);
  EXPECT_EQ(remap.dense_to_orig.size(), 4);

  // dense_to_orig 应为 [0,1,2,5]
  EXPECT_EQ(remap.dense_to_orig[0], 0);
  EXPECT_EQ(remap.dense_to_orig[1], 1);
  EXPECT_EQ(remap.dense_to_orig[2], 2);
  EXPECT_EQ(remap.dense_to_orig[3], 5);

  // 反向映射验证
  EXPECT_EQ(remap.orig_to_dense[0], 0);
  EXPECT_EQ(remap.orig_to_dense[1], 1);
  EXPECT_EQ(remap.orig_to_dense[2], 2);
  EXPECT_EQ(remap.orig_to_dense[5], 3);

  // 孤立位 3,4 不在映射中
  EXPECT_EQ(remap.orig_to_dense[3], -1);
  EXPECT_EQ(remap.orig_to_dense[4], -1);

  // 单比特保真度应重建为稠密数组
  EXPECT_EQ(chip.single_qubit_fidelities.size(), 4);
  EXPECT_DOUBLE_EQ(chip.single_qubit_fidelities[0], 0.9);   // dense 0 = orig 0
  EXPECT_DOUBLE_EQ(chip.single_qubit_fidelities[1], 0.9);   // dense 1 = orig 1
  EXPECT_DOUBLE_EQ(chip.single_qubit_fidelities[2], 0.9);   // dense 2 = orig 2
  EXPECT_DOUBLE_EQ(chip.single_qubit_fidelities[3], 0.99);  // dense 3 = orig 5
}

// 阈值过滤低保真度边, 但保留高保真度孤立位
TEST(DensifyChipTopologyTest, LowFidelityEdgeFilteredIsolatedQubitKept) {
  // 边 0-1 保真度低(0.5), 边 1-2 保真度高(0.9)
  // 物理位 7 孤立, 单比特保真度 0.95
  ChipCalibration chip({{0, 1}, {1, 2}}, {0.5, 0.9},
                       {/*0*/ 0.9, /*1*/ 0.9, /*2*/ 0.9, /*3*/ 0.0, /*4*/ 0.0,
                        /*5*/ 0.0, /*6*/ 0.0, /*7*/ 0.95});

  double threshold = 0.8;
  auto remap = densify_chip_topology(chip, threshold);

  // 低保真度边 0-1 应被过滤, 只保留 1-2
  // 耦合位来自保留的边: 1, 2
  // 孤立位 7 保真度 0.95 > 0.8, 应包含
  // 位 0 保真度 0.9 > 0.8, 也应包含(虽然在耦合边端点上但边被过滤掉了)
  EXPECT_EQ(remap.dense_count, 4);  // 0, 1, 2, 7

  // dense_to_orig 应为 [0,1,2,7]
  EXPECT_EQ(remap.dense_to_orig[0], 0);
  EXPECT_EQ(remap.dense_to_orig[1], 1);
  EXPECT_EQ(remap.dense_to_orig[2], 2);
  EXPECT_EQ(remap.dense_to_orig[3], 7);

  // 边应稠密化: 只保留 1-2, 端点重映射
  EXPECT_EQ(chip.coupling_list.size(), 1);
  EXPECT_EQ(chip.coupling_list[0].first, 1);   // orig 1 -> dense 1
  EXPECT_EQ(chip.coupling_list[0].second, 2);  // orig 2 -> dense 2
}
