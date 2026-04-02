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

#include "mapping/sabre_mapping.h"
#include "mapping/sabre_routing.h"
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
  SABRE sabre_no_init(coupling_list);
  sabre_no_init.execute(logical_circuit);
  const auto& phys_no = sabre_no_init.get_physical_gates();
  size_t swaps_no = 0;
  for (const auto& g : phys_no)
    if (g.name == "swap") swaps_no++;

  // routing with initial mapping
  auto init_map = sabre_initial_mapping(logical_circuit, coupling_list);
  SABRE sabre_with_init(coupling_list);
  sabre_with_init.execute(logical_circuit, init_map);
  const auto& phys_with = sabre_with_init.get_physical_gates();
  size_t swaps_with = 0;
  for (const auto& g : phys_with)
    if (g.name == "swap") swaps_with++;

  // using initial mapping should reduce the number of swaps
  EXPECT_LT(swaps_with, swaps_no);
}
