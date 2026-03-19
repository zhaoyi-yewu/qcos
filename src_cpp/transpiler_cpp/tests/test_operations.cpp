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

#include "circuit/base_operation.h"

TEST(BaseOperationTest, test1) {
  qcos::BaseOperation op("h", {0});
  EXPECT_EQ(op.targets.size(), 1);
  EXPECT_EQ(op.name, "h");
}

TEST(BaseOperationTest, test2) {
  qcos::BaseOperation op("rx", {1}, 1.57);
  ASSERT_EQ(op.arg_value.size(), 1);
  EXPECT_DOUBLE_EQ(op.arg_value[0], 1.57);
}