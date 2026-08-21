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
using namespace qcos;

TEST(BaseOperationTest, SingleQubitNoParam) {
  BaseOperation op("h", {0});
  EXPECT_EQ(op.name, "h");
  EXPECT_EQ(op.targets.size(), 1);
  EXPECT_EQ(op.targets[0], 0);
  EXPECT_TRUE(op.arg_value.empty());
  EXPECT_EQ(op.operation_type, OperationType::SINGLE_QUBIT_OPERATION);
}

TEST(BaseOperationTest, SingleQubitWithParam) {
  BaseOperation op("rx", {1}, {3.1415926});
  EXPECT_EQ(op.name, "rx");
  EXPECT_EQ(op.targets.size(), 1);
  EXPECT_EQ(op.arg_value.size(), 1);
  EXPECT_DOUBLE_EQ(op.arg_value[0], 3.1415926);
}

TEST(BaseOperationTest, ToOpenQasmSingleQubitNoParam) {
  BaseOperation op("h", {0});
  EXPECT_EQ(op.to_openqasm(), "h q[0];");
}

TEST(BaseOperationTest, ToOpenQasmSingleQubitWithParam) {
  BaseOperation op("rx", {1}, {M_PI / 2});
  EXPECT_EQ(op.to_openqasm(), "rx(pi/2) q[1];");
}

TEST(BaseOperationTest, ToOpenQasmMultiQubitNoSpaceAfterComma) {
  BaseOperation op("cx", {0, 1});
  EXPECT_EQ(op.to_openqasm(), "cx q[0],q[1];");
}

TEST(BaseOperationTest, ToOpenQasmMultiParamNoSpaceAfterComma) {
  BaseOperation op("u3", {0}, {M_PI / 2, M_PI / 4, 0.5});
  EXPECT_EQ(op.to_openqasm(), "u3(pi/2,pi/4,0.50000000) q[0];");
}

TEST(BaseOperationTest, ToOpenQasmTargetsEmptyThrows) {
  BaseOperation op("h", {});
  EXPECT_THROW(op.to_openqasm(), std::runtime_error);
}

TEST(BaseOperationTest, ToOpenQasmTripleQubitNoSpace) {
  BaseOperation op("ccx", {0, 1, 2});
  EXPECT_EQ(op.to_openqasm(), "ccx q[0],q[1],q[2];");
}

TEST(BaseOperationTest, ToOpenQasmMultiQubitAndParamNoSpace) {
  BaseOperation op("u3", {0, 1}, {M_PI, 0.5, 0.25});
  EXPECT_EQ(op.to_openqasm(), "u3(pi,0.50000000,0.25000000) q[0],q[1];");
}

TEST(BaseOperationTest, ToOpenQasmSyncNoSpace) {
  BaseOperation op("sync", {0, 1, 2, 3});
  EXPECT_EQ(op.to_openqasm(), "barrier q[0],q[1],q[2],q[3];");
}

TEST(BaseOperationTest, ToOpenQasmMeasureNoSpace) {
  BaseOperation op("measure", {0, 1});
  EXPECT_EQ(op.to_openqasm(), "measure q[0],q[1];");
}

TEST(BaseOperationTest, ToOpenQasmResetNoSpace) {
  BaseOperation op("reset", {0});
  EXPECT_EQ(op.to_openqasm(), "reset q[0];");
}

TEST(BaseOperationTest, ToOpenQasmNoSpaceInArgStr) {
  BaseOperation op("rzz", {0, 1}, {0.1, 0.2, 0.3, 0.4});
  std::string qasm = op.to_openqasm();
  EXPECT_EQ(qasm.find(", "), std::string::npos);
}

TEST(BaseOperationTest, ToOpenQasmNoSpaceInTargetsStr) {
  BaseOperation op("h", {0, 1, 2, 3, 4});
  std::string qasm = op.to_openqasm();
  EXPECT_EQ(qasm.find(", "), std::string::npos);
}
