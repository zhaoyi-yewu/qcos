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

#include "circuit/gate_operation.h"

using namespace qcos;

TEST(GateOperationTest, HGate) {
  GateOperation h("h", {0}, {});
  EXPECT_EQ(h.name, "h");
  EXPECT_EQ(h.targets.size(), 1);
  EXPECT_TRUE(h.arg_value.empty());
  EXPECT_EQ(h.operation_type, OperationType::SINGLE_QUBIT_OPERATION);
  EXPECT_TRUE(h.hermitian);
}

TEST(GateOperationTest, RXGate) {
  GateOperation rx("rx", {1}, {1.5707963});
  EXPECT_EQ(rx.name, "rx");
  EXPECT_EQ(rx.targets.size(), 1);
  EXPECT_EQ(rx.arg_value.size(), 1);
  EXPECT_DOUBLE_EQ(rx.arg_value[0], 1.5707963);
  EXPECT_TRUE(rx.hermitian);
}

TEST(GateOperationTest, CNOTGate) {
  GateOperation cnot("cx", {0, 1}, {}, OperationType::DOUBLE_QUBIT_OPERATION);
  EXPECT_EQ(cnot.name, "cx");
  EXPECT_EQ(cnot.targets.size(), 2);
  EXPECT_EQ(cnot.targets[0], 0);
  EXPECT_EQ(cnot.targets[1], 1);
  EXPECT_TRUE(cnot.arg_value.empty());
  EXPECT_EQ(cnot.operation_type, OperationType::DOUBLE_QUBIT_OPERATION);
}

TEST(GateOperationTest, InvalidTargetCount) {
  EXPECT_THROW(GateOperation("h", {0, 1}, {}), std::invalid_argument);
  EXPECT_THROW(
      GateOperation("cnot", {0}, {}, OperationType::DOUBLE_QUBIT_OPERATION),
      std::invalid_argument);
}
