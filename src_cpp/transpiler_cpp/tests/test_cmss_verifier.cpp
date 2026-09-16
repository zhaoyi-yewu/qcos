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

#include "test_verify_utils.h"
#include "verify/cmss_verifier.h"

using namespace qcos;

// ============ 语法校验（MQ02 拓扑，与拓扑结构无关） ============

TEST(CMSSVerifier, CheckQasmSyntax_ValidQasm_ReturnsTrue) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "creg c[2];\n"
      "h q[0];\n"
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.check_qasm_syntax2(qasm));
}

TEST(CMSSVerifier, CheckQasmSyntax_MissingOpenQASM_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm = "qreg q[2];\nh q[0];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "QASM syntax error: OPENQASM declaration not found");
}

TEST(CMSSVerifier, CheckQasmSyntax_Qasm3Header_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 3.0;\n"
      "include \"stdgates.inc\";\n"
      "qubit[2] q;\n"
      "h q[0];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "QASM syntax error: only OPENQASM 2.0 is supported");
}

TEST(CMSSVerifier, CheckQasmSyntax_InvalidGate_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "foobar q[0];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "QASM syntax error: failed to parse circuit");
}

TEST(CMSSVerifier, Measure_GateAfterMeasure_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "creg c[2];\n"
      "h q[0];\n"
      "measure q[0] -> c[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "QASM syntax error: Measure gates must be at the end of the circuit");
}

TEST(CMSSVerifier, Measure_DuplicateMeasure_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "creg c[2];\n"
      "h q[0];\n"
      "measure q[0] -> c[0];\n"
      "measure q[0] -> c[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "QASM syntax error: qubit 0 is measured more than once");
}

// ============ 数量/去重校验（MQ02 拓扑，与拓扑结构无关） ============

TEST(CMSSVerifier, TargetBitsCountMatch_ReturnsTrue) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TargetBitsCountMoreThan_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1, 2};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, TargetBitsCountLessThan_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, TargetBitsDuplicate_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 0, 1, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, TargetBitsDuplicateMiddle_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1, 0};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

// ============ 深度/门数量校验（MQ02 拓扑，与拓扑结构无关） ============

TEST(CMSSVerifier, Depth_200SequentialGates_Passes) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[1];\n";
  for (int i = 0; i < 200; ++i) qasm += "h q[0];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Depth_201SequentialGates_Fails) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[1];\n";
  for (int i = 0; i < 201; ++i) qasm += "h q[0];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Depth error: circuit depth 201 exceeds limit 200");
}

TEST(CMSSVerifier, TwoQubitGateCount_200Cz_ReturnsTrue) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n";
  for (int i = 0; i < 200; ++i) qasm += "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TwoQubitGateCount_201Cz_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n";
  for (int i = 0; i < 201; ++i) qasm += "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Gate count error: 201 multi-qubit gates exceed limit 200");
}

TEST(CMSSVerifier, TwoQubitGateCount_CcxDecomposesOverLimit_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n";
  for (int i = 0; i < 40; ++i) qasm += "ccx q[0],q[1],q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Gate count error: 240 two-qubit gates after decomposition exceed "
            "limit 200");
}

TEST(CMSSVerifier, TotalGateCount_500_Passes) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n";
  for (int i = 0; i < 500; ++i) {
    qasm += "h q[" + std::to_string(i % 3) + "];\n";
  }
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TotalGateCount_501_Fails) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n";
  for (int i = 0; i < 501; ++i) {
    qasm += "h q[" + std::to_string(i % 3) + "];\n";
  }
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Gate count error: total gate count exceeds limit 500");
}

// ============ MQ02 线性链拓扑（24 比特 Q0-Q23）全场景 ============

TEST(CMSSVerifier, MQ02_MultiQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, MQ02_MultiQubit_NoTarget_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());  // bits=24
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[25];\n"
      "cx q[0],q[1];\ncx q[2],q[3];\ncx q[4],q[5];\n"
      "cx q[6],q[7];\ncx q[8],q[9];\ncx q[10],q[11];\n"
      "cx q[12],q[13];\ncx q[14],q[15];\ncx q[16],q[17];\n"
      "cx q[18],q[19];\ncx q[20],q[21];\ncx q[22],q[23];\n"
      "h q[24];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 25 qubits, but chip only has 24");
}

TEST(CMSSVerifier, MQ02_AllSingleQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_mq02_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, MQ02_AllSingleQubit_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_mq02_params());  // bits=24
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[25];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\nh q[4];\n"
      "h q[5];\nh q[6];\nh q[7];\nh q[8];\nh q[9];\n"
      "h q[10];\nh q[11];\nh q[12];\nh q[13];\nh q[14];\n"
      "h q[15];\nh q[16];\nh q[17];\nh q[18];\nh q[19];\n"
      "h q[20];\nh q[21];\nh q[22];\nh q[23];\nh q[24];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 25 qubits, but chip only has 24");
}

TEST(CMSSVerifier, MQ02_AllSingleQubit_DisconnectedTarget_ReturnsTrue) {
  auto params = make_mq02_params();
  params.target_bits = {0, 10};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, MQ02_AllSingleQubit_TargetCountMismatch_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1, 2, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, MQ02_AllSingleQubit_TargetOutOfRange_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 24};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 24 out of range [0, 24)");
}

TEST(CMSSVerifier, MQ02_TargetOutOfRange_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 24};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 24 out of range [0, 24)");
}

TEST(CMSSVerifier, MQ02_TargetCountMismatch_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1, 2};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, MQ02_TargetDuplicate_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 0, 1, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, MQ02_TargetDuplicateMiddle_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, MQ02_TargetConnected_Adjacent_ReturnsTrue) {
  auto params = make_mq02_params();
  params.target_bits = {0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, MQ02_TargetConnected_Chain_ReturnsTrue) {
  auto params = make_mq02_params();
  params.target_bits = {10, 11, 12};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, MQ02_TargetDisconnected_NonAdjacent_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 5};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

TEST(CMSSVerifier, MQ02_TargetDisconnected_ChainEnds_ReturnsFalse) {
  auto params = make_mq02_params();
  params.target_bits = {0, 23};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

// ============ QZ01 表面码拓扑（17 比特 Q0-Q16）全场景 ============

TEST(CMSSVerifier, QZ01_MultiQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_qz01_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_MultiQubit_NoTarget_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_qz01_params());  // bits=17
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[25];\n"
      "cx q[0],q[1];\ncx q[2],q[3];\ncx q[4],q[5];\n"
      "cx q[6],q[7];\ncx q[8],q[9];\ncx q[10],q[11];\n"
      "cx q[12],q[13];\ncx q[14],q[15];\ncx q[16],q[17];\n"
      "cx q[18],q[19];\ncx q[20],q[21];\ncx q[22],q[23];\n"
      "h q[24];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 25 qubits, but chip only has 17");
}

TEST(CMSSVerifier, QZ01_AllSingleQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_qz01_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_AllSingleQubit_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_qz01_params());  // bits=17
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[25];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\nh q[4];\n"
      "h q[5];\nh q[6];\nh q[7];\nh q[8];\nh q[9];\n"
      "h q[10];\nh q[11];\nh q[12];\nh q[13];\nh q[14];\n"
      "h q[15];\nh q[16];\nh q[17];\nh q[18];\nh q[19];\n"
      "h q[20];\nh q[21];\nh q[22];\nh q[23];\nh q[24];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 25 qubits, but chip only has 17");
}

TEST(CMSSVerifier, QZ01_AllSingleQubit_DisconnectedTarget_ReturnsTrue) {
  auto params = make_qz01_params();
  params.target_bits = {0, 8};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_AllSingleQubit_TargetCountMismatch_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 1, 2, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, QZ01_AllSingleQubit_TargetOutOfRange_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 17};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 17 out of range [0, 17)");
}

TEST(CMSSVerifier, QZ01_TargetOutOfRange_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 17};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 17 out of range [0, 17)");
}

TEST(CMSSVerifier, QZ01_TargetCountMismatch_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 9, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, QZ01_TargetDuplicate_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 0, 9, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, QZ01_TargetDuplicateMiddle_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, QZ01_TargetConnected_DirectEdge_ReturnsTrue) {
  auto params = make_qz01_params();
  params.target_bits = {0, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_TargetConnected_ThroughHub_ReturnsTrue) {
  auto params = make_qz01_params();
  params.target_bits = {0, 3, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_TargetConnected_FourQubitStar_ReturnsTrue) {
  auto params = make_qz01_params();
  params.target_bits = {3, 4, 9, 11};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n"
      "h q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_TargetDisconnected_NoEdge_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

// ============ QZ01 数量/去重校验（与拓扑结构无关，但用 QZ01 拓扑验证）
// ============

TEST(CMSSVerifier, QZ01_TargetBitsCountMatch_ReturnsTrue) {
  auto params = make_qz01_params();
  params.target_bits = {0, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, QZ01_TargetBitsCountMoreThan_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 9, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, QZ01_TargetBitsCountLessThan_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, QZ01_TargetBitsDuplicate_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 0, 9, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, QZ01_TargetBitsDuplicateMiddle_ReturnsFalse) {
  auto params = make_qz01_params();
  params.target_bits = {0, 0, 9};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

// ============ make_test_params 拓扑全场景（8比特，耦合0-1-2，最大连通=3）
// ============

TEST(CMSSVerifier, TestParams_MultiQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_test_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TestParams_MultiQubit_NoTarget_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_test_params());  // bits=8
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[10];\n"
      "cx q[0],q[1];\ncx q[2],q[3];\ncx q[4],q[5];\n"
      "cx q[6],q[7];\ncx q[8],q[9];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: circuit requires 10 qubits, but chip only has 8");
}

TEST(CMSSVerifier, TestParams_AllSingleQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_test_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TestParams_AllSingleQubit_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_test_params());  // bits=8
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[10];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\nh q[4];\n"
      "h q[5];\nh q[6];\nh q[7];\nh q[8];\nh q[9];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: circuit requires 10 qubits, but chip only has 8");
}

TEST(CMSSVerifier, TestParams_AllSingleQubit_DisconnectedTarget_ReturnsTrue) {
  auto params = make_test_params();
  params.target_bits = {0, 5};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier,
     TestParams_AllSingleQubit_TargetCountMismatch_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 1, 2, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, TestParams_AllSingleQubit_TargetOutOfRange_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 8};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 8 out of range [0, 8)");
}

TEST(CMSSVerifier, TestParams_TargetOutOfRange_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 8};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 8 out of range [0, 8)");
}

TEST(CMSSVerifier, TestParams_TargetCountMismatch_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 1, 2};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, TestParams_TargetDuplicate_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 0, 1, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, TestParams_TargetDuplicateMiddle_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, TestParams_TargetConnected_Adjacent_ReturnsTrue) {
  auto params = make_test_params();
  params.target_bits = {0, 1};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TestParams_TargetConnected_Chain_ReturnsTrue) {
  auto params = make_test_params();
  params.target_bits = {0, 1, 2};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, TestParams_TargetDisconnected_ReturnsFalse) {
  auto params = make_test_params();
  params.target_bits = {0, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

TEST(CMSSVerifier,
     TestParams_TargetDisconnected_PartiallyConnected_ReturnsFalse) {
  auto params = make_test_params();
  // target {0,1,3}：{0,1}连通，{3}孤立，整体不构成单一连通图
  params.target_bits = {0, 1, 3};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

// ============ make_shenglian_params 拓扑全场景（83比特，60条边，最大连通=55）
// ============

TEST(CMSSVerifier, Shenglian_MultiQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_shenglian_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Shenglian_MultiQubit_NoTarget_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_shenglian_params());  // bits=83
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[84];\n";
  for (int i = 0; i < 84; ++i) qasm += "h q[" + std::to_string(i) + "];\n";
  qasm += "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 84 qubits, but chip only has 83");
}

TEST(CMSSVerifier, Shenglian_AllSingleQubit_NoTarget_Fits_ReturnsTrue) {
  CMSSVerifier verifier(make_shenglian_params());
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Shenglian_AllSingleQubit_ExceedsBits_ReturnsFalse) {
  CMSSVerifier verifier(make_shenglian_params());  // bits=83
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[84];\n";
  for (int i = 0; i < 84; ++i) qasm += "h q[" + std::to_string(i) + "];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit requires 84 qubits, but chip only has 83");
}

TEST(CMSSVerifier, Shenglian_AllSingleQubit_DisconnectedTarget_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 40};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Shenglian_AllSingleQubit_TargetCountMismatch_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 18, 25};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, Shenglian_AllSingleQubit_TargetOutOfRange_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 83};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n"
      "h q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 83 out of range [0, 83)");
}

TEST(CMSSVerifier, Shenglian_TargetOutOfRange_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 83};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 83 out of range [0, 83)");
}

TEST(CMSSVerifier, Shenglian_TargetCountMismatch_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 18};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(CMSSVerifier, Shenglian_TargetDuplicate_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 15, 22, 22};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, Shenglian_TargetDuplicateMiddle_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 15, 22};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

TEST(CMSSVerifier, Shenglian_TargetConnected_Adjacent_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22};  // edge 15-22 exists
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Shenglian_TargetConnected_Chain_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 29};  // 15-22-29 chain
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(CMSSVerifier, Shenglian_TargetDisconnected_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 16};  // no edge 15-16
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}

TEST(CMSSVerifier,
     Shenglian_TargetDisconnected_PartiallyConnected_ReturnsFalse) {
  auto params = make_shenglian_params();
  // target {15,22,18}：{15,22}连通，{18}孤立，整体不构成单一连通图
  params.target_bits = {15, 22, 18};
  CMSSVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cx q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bits do not form a connected graph");
}
