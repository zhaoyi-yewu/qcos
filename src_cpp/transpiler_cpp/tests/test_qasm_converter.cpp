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
 *     WITHOUT WARRANTIES OF ANY KIND,
 *     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 *     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <fstream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "circuit/gate_operation.h"
#include "circuit/qasm_converter.h"
#include "circuit/quantum_circuit.h"

using namespace qcos;

class QasmConverterTest : public ::testing::Test {
 protected:
  QuantumCircuit qc_{2, 2};
};

TEST_F(QasmConverterTest, EmptyCircuitToQasm2) {
  QuantumCircuit empty(3, 3);
  QasmConverter conv(empty);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("OPENQASM 2.0;"), std::string::npos);
  EXPECT_NE(result.find("qreg q[3];"), std::string::npos);
  EXPECT_NE(result.find("creg c[3];"), std::string::npos);
  EXPECT_NE(result.find("include \"qelib1.inc\";"), std::string::npos);
}

TEST_F(QasmConverterTest, EmptyCircuitToQasm3) {
  QuantumCircuit empty(3, 3);
  QasmConverter conv(empty);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("OPENQASM 3.0;"), std::string::npos);
  EXPECT_NE(result.find("qubit[3] q;"), std::string::npos);
  EXPECT_NE(result.find("bit[3] c;"), std::string::npos);
  EXPECT_NE(result.find("include \"stdgates.inc\";"), std::string::npos);
}

TEST_F(QasmConverterTest, SingleQubitGateToQasm2) {
  qc_.append(std::make_shared<H>(std::vector<int>{0}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("h q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, SingleQubitGateToQasm3) {
  qc_.append(std::make_shared<H>(std::vector<int>{0}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("h q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, TwoQubitGateToQasm2) {
  qc_.append(std::make_shared<CX>(std::vector<int>{0, 1}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("cx q[0], q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, TwoQubitGateToQasm3) {
  qc_.append(std::make_shared<CX>(std::vector<int>{0, 1}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("cx q[0], q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, ParamGateToQasm2) {
  qc_.append(std::make_shared<RX>(std::vector<int>{0}, std::vector<double>{3.14159265358979323846}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("rx(pi) q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, ParamGateToQasm3) {
  qc_.append(std::make_shared<RZ>(std::vector<int>{1}, std::vector<double>{1.57079632679489661923}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("rz(pi/2) q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, MeasureToQasm2) {
  qc_.append(std::make_shared<Measure>(std::vector<int>{0}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("measure q[0] -> c[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, MeasureToQasm3) {
  qc_.append(std::make_shared<Measure>(std::vector<int>{1}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("measure q[1] -> c[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, ResetToQasm2) {
  qc_.append(std::make_shared<Reset>(std::vector<int>{0}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("reset q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, ResetToQasm3) {
  qc_.append(std::make_shared<Reset>(std::vector<int>{1}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("reset q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, MeasureCaseInsensitive) {
  auto op = std::make_shared<Measure>(std::vector<int>{0});
  op->name = "Measure";
  qc_.append(op);
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("measure q[0] -> c[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, ResetCaseInsensitive) {
  auto op = std::make_shared<Reset>(std::vector<int>{0});
  op->name = "Reset";
  qc_.append(op);
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("reset q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, MixedOperationsToQasm2) {
  qc_.append(std::make_shared<H>(std::vector<int>{0}));
  qc_.append(std::make_shared<CX>(std::vector<int>{0, 1}));
  qc_.append(std::make_shared<Measure>(std::vector<int>{0}));
  qc_.append(std::make_shared<Measure>(std::vector<int>{1}));

  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("h q[0];"), std::string::npos);
  EXPECT_NE(result.find("cx q[0], q[1];"), std::string::npos);
  EXPECT_NE(result.find("measure q[0] -> c[0];"), std::string::npos);
  EXPECT_NE(result.find("measure q[1] -> c[1];"), std::string::npos);

  size_t h_pos = result.find("h q[0];");
  size_t cx_pos = result.find("cx q[0], q[1];");
  size_t m0_pos = result.find("measure q[0] -> c[0];");
  size_t m1_pos = result.find("measure q[1] -> c[1];");
  EXPECT_LT(h_pos, cx_pos);
  EXPECT_LT(cx_pos, m0_pos);
  EXPECT_LT(m0_pos, m1_pos);
}

TEST_F(QasmConverterTest, MixedOperationsToQasm3) {
  qc_.append(std::make_shared<X>(std::vector<int>{1}));
  qc_.append(std::make_shared<Reset>(std::vector<int>{0}));
  qc_.append(std::make_shared<Measure>(std::vector<int>{1}));

  QasmConverter conv(qc_);
  std::string result = conv.to_qasm3();

  EXPECT_NE(result.find("x q[1];"), std::string::npos);
  EXPECT_NE(result.find("reset q[0];"), std::string::npos);
  EXPECT_NE(result.find("measure q[1] -> c[1];"), std::string::npos);

  size_t x_pos = result.find("x q[1];");
  size_t reset_pos = result.find("reset q[0];");
  size_t m_pos = result.find("measure q[1] -> c[1];");
  EXPECT_LT(x_pos, reset_pos);
  EXPECT_LT(reset_pos, m_pos);
}

TEST_F(QasmConverterTest, InferQubitNumFromOperations) {
  QuantumCircuit qc;
  qc.append(std::make_shared<H>(std::vector<int>{5}));
  qc.append(std::make_shared<CX>(std::vector<int>{3, 7}));

  QasmConverter conv(qc);
  std::string qasm2 = conv.to_qasm2();
  std::string qasm3 = conv.to_qasm3();

  EXPECT_NE(qasm2.find("qreg q[8];"), std::string::npos);
  EXPECT_NE(qasm3.find("qubit[8] q;"), std::string::npos);
}

TEST_F(QasmConverterTest, SaveQasm2) {
  qc_.append(std::make_shared<H>(std::vector<int>{0}));
  QasmConverter conv(qc_);

  std::string path = std::string(TEST_DATA_DIR) + "test_save_qasm2.qasm";
  conv.save(path, "2.0");

  std::ifstream ifs(path);
  ASSERT_TRUE(ifs.is_open());
  std::string content((std::istreambuf_iterator<char>(ifs)),
                      std::istreambuf_iterator<char>());
  EXPECT_NE(content.find("OPENQASM 2.0;"), std::string::npos);
  EXPECT_NE(content.find("h q[0];"), std::string::npos);
}

TEST_F(QasmConverterTest, SaveQasm3) {
  qc_.append(std::make_shared<X>(std::vector<int>{1}));
  QasmConverter conv(qc_);

  std::string path = std::string(TEST_DATA_DIR) + "test_save_qasm3.qasm";
  conv.save(path, "3.0");

  std::ifstream ifs(path);
  ASSERT_TRUE(ifs.is_open());
  std::string content((std::istreambuf_iterator<char>(ifs)),
                      std::istreambuf_iterator<char>());
  EXPECT_NE(content.find("OPENQASM 3.0;"), std::string::npos);
  EXPECT_NE(content.find("x q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, SaveInvalidVersionThrows) {
  QasmConverter conv(qc_);
  EXPECT_THROW(conv.save("dummy.qasm", "4.0"), std::invalid_argument);
  EXPECT_THROW(conv.save("dummy.qasm", "x"), std::invalid_argument);
}

TEST_F(QasmConverterTest, SaveInvalidPathThrows) {
  QasmConverter conv(qc_);
  EXPECT_THROW(conv.save("/nonexistent_dir/subdir/out.qasm", "2.0"),
               std::runtime_error);
}

TEST_F(QasmConverterTest, ThreeQubitGateToQasm2) {
  QuantumCircuit qc(3, 3);
  qc.append(std::make_shared<CCX>(std::vector<int>{0, 1, 2}));
  QasmConverter conv(qc);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("ccx q[0], q[1], q[2];"), std::string::npos);
}

TEST_F(QasmConverterTest, SwapGateToQasm2) {
  qc_.append(std::make_shared<SWAP>(std::vector<int>{0, 1}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("swap q[0], q[1];"), std::string::npos);
}

TEST_F(QasmConverterTest, U3GateToQasm2) {
  qc_.append(std::make_shared<U3>(std::vector<int>{0}, std::vector<double>{1.0, 2.0, 3.0}));
  QasmConverter conv(qc_);
  std::string result = conv.to_qasm2();

  EXPECT_NE(result.find("u3("), std::string::npos);
  EXPECT_NE(result.find("q[0]"), std::string::npos);
}

TEST_F(QasmConverterTest, Qasm2HeaderFormat) {
  QuantumCircuit qc(2, 2);
  QasmConverter conv(qc);
  std::string result = conv.to_qasm2();

  EXPECT_TRUE(result.find("OPENQASM 2.0;\n") == 0);
  size_t header_end = result.find("\n\n");
  EXPECT_NE(header_end, std::string::npos);
}

TEST_F(QasmConverterTest, Qasm3HeaderFormat) {
  QuantumCircuit qc(2, 2);
  QasmConverter conv(qc);
  std::string result = conv.to_qasm3();

  EXPECT_TRUE(result.find("OPENQASM 3.0;\n") == 0);
}
