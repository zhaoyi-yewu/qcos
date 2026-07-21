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

#include "mapping/mapping_utils.h"
#include "mapping/sabre_mapping.h"

using namespace qcos;

TEST(SabreInitialMapping, CycleTopology) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 0}};
  std::vector<GateOperation> logical_circuit = {GateOperation(
      "cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION, false)};

  auto mapping = sabre_initial_mapping(logical_circuit, coupling_list);

  ASSERT_GE(mapping.size(), 2);
  EXPECT_EQ(mapping[0], 0);
  EXPECT_EQ(mapping[1], 1);
}

TEST(SabreInitialMapping, MixedGateCircuit) {
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

  ASSERT_GE(mapping.size(), 4);
  EXPECT_EQ(mapping[0], 1);
  EXPECT_EQ(mapping[1], 0);
  EXPECT_EQ(mapping[2], 2);
  EXPECT_EQ(mapping[3], 3);
}

TEST(SabreMeasure, NoMeasure_AutoAppends) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      std::make_shared<BaseOperation>("h", std::vector<int>{0},
                                      std::vector<double>{},
                                      OperationType::SINGLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("cx", std::vector<int>{0, 1},
                                      std::vector<double>{},
                                      OperationType::DOUBLE_QUBIT_OPERATION),
  };

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  int measure_count = 0;
  for (const auto& g : phys) {
    if (g->name == "measure") measure_count++;
  }
  EXPECT_EQ(measure_count, 2);
}

TEST(SabreMeasure, FullMeasure_Preserved) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      std::make_shared<BaseOperation>("cx", std::vector<int>{0, 2},
                                      std::vector<double>{},
                                      OperationType::DOUBLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("measure", std::vector<int>{0},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
      std::make_shared<BaseOperation>("measure", std::vector<int>{1},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
      std::make_shared<BaseOperation>("measure", std::vector<int>{2},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
  };

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  int measure_count = 0;
  for (const auto& g : phys) {
    if (g->name == "measure") measure_count++;
  }
  EXPECT_EQ(measure_count, 3);
}

TEST(SabreMeasure, PartialMeasure_NoAutoAppend) {
  std::vector<std::pair<int, int>> coupling_list = {
      {0, 1}, {1, 2}, {2, 3}, {3, 4}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      std::make_shared<BaseOperation>("cx", std::vector<int>{0, 1},
                                      std::vector<double>{},
                                      OperationType::DOUBLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("cx", std::vector<int>{2, 3},
                                      std::vector<double>{},
                                      OperationType::DOUBLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("measure", std::vector<int>{0},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
      std::make_shared<BaseOperation>("measure", std::vector<int>{2},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
  };

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  int measure_count = 0;
  for (const auto& g : phys) {
    if (g->name == "measure") measure_count++;
  }
  EXPECT_EQ(measure_count, 2);
}

TEST(SabreMeasure, MeasureInMiddle_MovedToEnd) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}};
  std::vector<std::shared_ptr<BaseOperation>> circuit = {
      std::make_shared<BaseOperation>("h", std::vector<int>{0},
                                      std::vector<double>{},
                                      OperationType::SINGLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("measure", std::vector<int>{0},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
      std::make_shared<BaseOperation>("cx", std::vector<int>{0, 1},
                                      std::vector<double>{},
                                      OperationType::DOUBLE_QUBIT_OPERATION),
      std::make_shared<BaseOperation>("measure", std::vector<int>{1},
                                      std::vector<double>{},
                                      OperationType::MEASURE),
  };

  SABRE sabre(coupling_list);
  sabre.execute(circuit);
  const auto& phys = sabre.get_physical_gates();

  int last_non_measure_idx = -1;
  int first_measure_idx = -1;
  for (int i = 0; i < static_cast<int>(phys.size()); ++i) {
    if (phys[i]->name != "measure") {
      last_non_measure_idx = i;
    } else if (first_measure_idx == -1) {
      first_measure_idx = i;
    }
  }

  if (last_non_measure_idx >= 0 && first_measure_idx >= 0) {
    EXPECT_GT(first_measure_idx, last_non_measure_idx);
  }
}
