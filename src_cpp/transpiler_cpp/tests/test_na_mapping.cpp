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

#include <memory>
#include <vector>

#include "circuit/gate_operation.h"
#include "mapping/na_mapping.h"

using namespace qcos;

namespace {

NAQpuConfig make_test_qpu_config() {
  // 与 Python 侧 test_transpiler_na_mapping.py 配置保持一致：
  // 8 个操作区位置（4 条边）+ 36 个存储区位置
  NAQpuConfig cfg;
  cfg.storage_area = {"P144", "P145", "P146", "P147", "P148", "P149",
                      "P150", "P151", "P152", "P153", "P154", "P155",
                      "P164", "P165", "P166", "P167", "P168", "P169",
                      "P170", "P171", "P172", "P173", "P174", "P175",
                      "P184", "P185", "P186", "P187", "P188", "P189",
                      "P190", "P191", "P192", "P193", "P194", "P195"};
  cfg.operate_area = {"P100", "P101", "P106", "P107", "P112", "P113",
                      "P118", "P119"};
  cfg.coupler_map = {
      {"R_G0", {"P100", "P101"}}, {"R_G1", {"P106", "P107"}},
      {"R_G2", {"P112", "P113"}}, {"R_G3", {"P118", "P119"}},
  };
  cfg.readout_error = {
      {"P144", 1.0}, {"P145", 2.0}, {"P146", 3.0}, {"P147", 4.0},
      {"P148", 5.0}, {"P149", 5.0}, {"P150", 6.0}, {"P151", 7.0},
      {"P152", 6.0}, {"P153", 5.0}, {"P154", 4.0}, {"P155", 3.0},
      {"P164", 1.0}, {"P165", 2.0}, {"P166", 2.0}, {"P167", 3.0},
      {"P168", 4.0}, {"P169", 5.0}, {"P170", 6.0}, {"P171", 7.0},
      {"P172", 1.0}, {"P173", 3.0}, {"P174", 2.0}, {"P175", 4.0},
      {"P184", 5.0}, {"P185", 6.0}, {"P186", 7.0}, {"P187", 8.0},
      {"P188", 5.0}, {"P189", 3.0}, {"P190", 4.0}, {"P191", 3.0},
      {"P192", 4.0}, {"P193", 5.0}, {"P194", 3.0}, {"P195", 2.0},
  };
  return cfg;
}

std::vector<std::shared_ptr<BaseOperation>> make_simple_gates() {
  // 对应 Python simple_data 经 optimize_gate(opt_level=1) 后的结果：
  // h; h; x; rx(1) -> x; rx(1)
  return {
      std::make_shared<X>(std::vector<int>{0}),
      std::make_shared<RX>(std::vector<int>{0}, std::vector<double>{1.0}),
      std::make_shared<Measure>(std::vector<int>{0}),
  };
}

std::vector<std::shared_ptr<BaseOperation>> make_task2_gates() {
  // qreg q[5]; x q[0]; cx q[0], q[1]; cz q[0], q[2]; cz q[0], q[3]; measure;
  return {
      std::make_shared<X>(std::vector<int>{0}),
      std::make_shared<CX>(std::vector<int>{0, 1}),
      std::make_shared<CZ>(std::vector<int>{0, 2}),
      std::make_shared<CZ>(std::vector<int>{0, 3}),
      std::make_shared<Measure>(std::vector<int>{0}),
  };
}

}  // namespace

TEST(NaMappingTest, PrepareDataBuildsGraph) {
  auto cfg = make_test_qpu_config();
  NARoute na;
  na.prepare_data(5, make_simple_gates(), cfg);
  // prepare_data 不构建 logical_to_storage（与 Python 实现一致，
  // 该映射在 get_init_mapping 中构建）
  EXPECT_TRUE(na.logical_to_storage.empty());
}

TEST(NaMappingTest, ExecuteWithOrderSimple) {
  auto cfg = make_test_qpu_config();
  NARoute na;
  na.prepare_data(1, make_simple_gates(), cfg);
  auto [res, layout] = na.execute_with_order();
  EXPECT_FALSE(res.empty());
  EXPECT_EQ(res.front()->name, "x");
  EXPECT_EQ(res.back()->name, "measure");
  EXPECT_TRUE(layout.empty());
}

TEST(NaMappingTest, ExecuteWithOrderTwoQubit) {
  auto cfg = make_test_qpu_config();
  NARoute na;
  na.prepare_data(4, make_task2_gates(), cfg);
  auto [res, layout] = na.execute_with_order();
  EXPECT_FALSE(res.empty());
  EXPECT_EQ(res.front()->name, "x");
  EXPECT_EQ(res.back()->name, "measure");
  EXPECT_EQ(static_cast<int>(na.logical_to_storage.size()), 4);
}

TEST(NaMappingTest, ExecuteWithOptSimple) {
  auto cfg = make_test_qpu_config();
  NARoute na;
  na.prepare_data(1, make_simple_gates(), cfg);
  auto res = na.execute_with_opt();
  EXPECT_FALSE(res.empty());
  EXPECT_EQ(res.front()->name, "x");
  EXPECT_EQ(res.back()->name, "measure");
}

TEST(NaMappingTest, ExecuteWithOptTwoQubit) {
  auto cfg = make_test_qpu_config();
  NARoute na;
  na.prepare_data(4, make_task2_gates(), cfg);
  auto res = na.execute_with_opt();
  EXPECT_FALSE(res.empty());
  EXPECT_EQ(res.front()->name, "x");
  EXPECT_EQ(res.back()->name, "measure");
}

TEST(NaMappingTest, SingleRouteExecute) {
  auto cfg = make_test_qpu_config();
  NASingleRoute na;
  std::vector<std::shared_ptr<BaseOperation>> gates = {
      std::make_shared<X>(std::vector<int>{0}),
      std::make_shared<H>(std::vector<int>{1}),
      std::make_shared<Measure>(std::vector<int>{0}),
      std::make_shared<Measure>(std::vector<int>{1}),
  };
  na.prepare_data(2, gates, cfg);
  auto [res, layout] = na.execute_with_order();
  EXPECT_EQ(res.size(), 4u);
  EXPECT_TRUE(layout.empty());
}
