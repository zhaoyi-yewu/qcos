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

#include "mapping/chip_data.h"
#include "mapping/mapping_utils.h"

using namespace qcos;

TEST(ChipCalibration, ConstructorSizeMismatch) {
  EXPECT_THROW(ChipCalibration({{0, 1}, {1, 2}}, {0.99}, {}),
               std::invalid_argument);
}

TEST(ChipCalibration, ValidConstruction) {
  EXPECT_NO_THROW(
      ChipCalibration({{0, 1}, {1, 2}}, {0.99, 0.98}, {0.999, 0.998, 0.997}));
}

TEST(FilterLowFidelity, RemovesBelowThreshold) {
  ChipCalibration chip({{0, 1}, {1, 2}, {2, 3}}, {0.5, 0.95, 0.99},
                       {0.99, 0.99, 0.99, 0.99});

  filter_low_fidelity(chip, 0.8);

  EXPECT_EQ(chip.coupling_list.size(), 2u);
  EXPECT_DOUBLE_EQ(chip.edge_fidelities[0], 0.95);
  EXPECT_DOUBLE_EQ(chip.edge_fidelities[1], 0.99);
}

TEST(FilterLowFidelity, ZeroThresholdNoFilter) {
  ChipCalibration chip({{0, 1}, {1, 2}}, {0.1, 0.2}, {0.1, 0.2, 0.3});

  filter_low_fidelity(chip, 0.0);

  EXPECT_EQ(chip.coupling_list.size(), 2u);
  EXPECT_DOUBLE_EQ(chip.edge_fidelities[0], 0.1);
  EXPECT_DOUBLE_EQ(chip.edge_fidelities[1], 0.2);
}

TEST(SelectLargestComponent, SingleComponent_NoOp) {
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {2, 3}};
  std::vector<double> edge_fidelities = {0.99, 0.98, 0.97};

  select_largest_component(coupling_list, edge_fidelities);

  EXPECT_EQ(coupling_list.size(), 3u);
  EXPECT_EQ(edge_fidelities.size(), 3u);
  EXPECT_DOUBLE_EQ(edge_fidelities[0], 0.99);
  EXPECT_DOUBLE_EQ(edge_fidelities[1], 0.98);
  EXPECT_DOUBLE_EQ(edge_fidelities[2], 0.97);
}

TEST(SelectLargestComponent, MultipleComponents_KeepsLargest) {
  // 两个分量: {0,1} (1 条边) 和 {5,6,7} (2 条边)
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {5, 6}, {6, 7}};
  std::vector<double> edge_fidelities = {0.9, 0.99, 0.98};

  select_largest_component(coupling_list, edge_fidelities);

  // 保留最大分量 {5,6,7} 的两条边
  EXPECT_EQ(coupling_list.size(), 2u);
  EXPECT_EQ(coupling_list[0].first, 5);
  EXPECT_EQ(coupling_list[0].second, 6);
  EXPECT_EQ(coupling_list[1].first, 6);
  EXPECT_EQ(coupling_list[1].second, 7);
}

TEST(SelectLargestComponent, EdgeFidelitiesSynced) {
  // 分量 {0,1,2} (2 条边) 和 {10,11} (1 条边)
  std::vector<std::pair<int, int>> coupling_list = {{0, 1}, {1, 2}, {10, 11}};
  std::vector<double> edge_fidelities = {0.5, 0.6, 0.99};

  select_largest_component(coupling_list, edge_fidelities);

  ASSERT_EQ(coupling_list.size(), 2u);
  ASSERT_EQ(edge_fidelities.size(), 2u);
  // 保真度与边同步过滤: 0.5/0.6 保留, 0.99 (边 10-11) 丢弃
  EXPECT_DOUBLE_EQ(edge_fidelities[0], 0.5);
  EXPECT_DOUBLE_EQ(edge_fidelities[1], 0.6);
}