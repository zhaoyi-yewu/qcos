/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <memory>
#include <string>
#include <vector>

#include "circuit/gate_operation.h"
#include "optimizer/gate_optimizer.h"

using namespace qcos;

// ======== optimize() 边界测试 ========

TEST(OptimizeBoundaryTest, EmptyCircuit) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, MeasureOnly) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<Measure>(std::vector<int>{1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, AllCancelWithMeasure) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {1}),
      std::make_shared<Measure>(std::vector<int>{0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, AllCancelNoMeasure) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),     create_gate("h", {0}),
      create_gate("x", {1}),     create_gate("x", {1}),
      create_gate("cx", {0, 1}), create_gate("cx", {0, 1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, SingleGate) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "h");
  }
}

TEST(OptimizeBoundaryTest, NonContiguousQubits) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("cx", {0, 3}), create_gate("cx", {0, 3}),
      std::make_shared<Measure>(std::vector<int>{0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, MixedCancelKeep) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    bool has_h = false, has_x = false;
    for (const auto& op : result) {
      if (op->name == "h") has_h = true;
      if (op->name == "x") has_x = true;
    }
    EXPECT_FALSE(has_h);
    EXPECT_TRUE(has_x);
  }
}

TEST(OptimizeBoundaryTest, MultiQubitAllCancel) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1}),
      create_gate("x", {1}), create_gate("y", {2}), create_gate("y", {2}),
      create_gate("z", {3}), create_gate("z", {3})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, OddCountSelfInverse) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {1}), create_gate("h", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "h");
  }
}

TEST(OptimizeBoundaryTest, DifferentQargsNoCancel) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("cx", {0, 1}),
                                                    create_gate("cx", {1, 0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 2u);
  }
}
