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
#include "verify/quafu_verifier.h"

using namespace qcos;

TEST(QuafuVerifier, CheckQasmSyntax_ValidQasm2) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "creg c[2];\n"
      "h q[0];\n"
      "cz q[0],q[1];\n"
      "measure q[0] -> c[0];\n";

  EXPECT_TRUE(verifier.check_qasm_syntax2(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_Qasm3Header_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "OPENQASM 3.0;\n"
      "include \"stdgates.inc\";\n"
      "qubit[2] q;\n"
      "h q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax2(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_NoHeader_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm = "qreg q[2];\nh q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax2(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_InvalidGate_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  // "foobar" 不是合法门名，解析会失败
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "foobar q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax2(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_CommentBeforeHeader) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "// this is a comment\n"
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n";

  EXPECT_TRUE(verifier.check_qasm_syntax2(qasm));
}

// Measure 之后出现非 Measure 门 -> False
TEST(QuafuVerifier, CheckQasmSyntax_GateAfterMeasure_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

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

// 同一比特被多次测量 -> False
TEST(QuafuVerifier, CheckQasmSyntax_DuplicateMeasure_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

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

// 多比特各自测量一次且在末尾 -> True
TEST(QuafuVerifier, CheckQasmSyntax_MultipleMeasureAtEnd_ReturnsTrue) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "creg c[3];\n"
      "h q[0];\n"
      "cz q[0],q[1];\n"
      "measure q[0] -> c[0];\n"
      "measure q[1] -> c[1];\n"
      "measure q[2] -> c[2];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// check_topology（通过 verify 测试，check_qasm_syntax 负责填充缓存）

TEST(QuafuVerifier, CheckTopology_AllSingleQubit_FitsBits_ReturnsTrue) {
  QuafuVerifier verifier(make_test_params());  // bits=8

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "h q[0];\n"
      "rx(1.570796) q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier, CheckTopology_AllSingleQubit_ExceedsBits_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());  // bits=8

  // 实际操作使用了 10 个不同比特（q[0]~q[9]），超过 bits=8
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

TEST(QuafuVerifier,
     CheckTopology_HasTwoQubitGate_FitsLargestComponent_ReturnsTrue) {
  // 两个连通分量：{0,1,2}（3 节点）和 {5,6}（2 节点），最大分量 3 节点
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {5, 6}, {6, 5}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.0,
                                    0.0,   0.999, 0.999, 0.0};

  QuafuVerifier verifier(params);

  // qreg q[3] 含双比特门，num_qubits=3 <= 最大连通分量节点数=3
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "h q[0];\n"
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier,
     CheckTopology_HasTwoQubitGate_ExceedsLargestComponent_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {5, 6}, {6, 5}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.0,
                                    0.0,   0.999, 0.999, 0.0};

  QuafuVerifier verifier(params);

  // 实际操作使用了 5 个不同比特（q[0]~q[4]），超过最大连通分量节点数=3
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[5];\n"
      "h q[0];\nh q[1];\nh q[2];\nh q[3];\nh q[4];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: circuit requires 5 qubits, but largest connected "
            "component only has 3");
}

TEST(QuafuVerifier, CheckTopology_ZeroQubits_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());
  // qreg q[0] 声明 0 个比特
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[0];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: circuit has no qubits");
}

// target_bits（规则2，含多比特门时触发）

TEST(QuafuVerifier, CheckTopology_TargetBitsInSameComponent_ReturnsTrue) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {5, 6}, {6, 5}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.0,
                                    0.0,   0.999, 0.999, 0.0};
  // target_bits 都在 {0,1,2} 分量内
  params.target_bits = {0, 1, 2};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "h q[2];\n"
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier,
     CheckTopology_TargetBitsInDifferentComponents_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {5, 6}, {6, 5}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.0,
                                    0.0,   0.999, 0.999, 0.0};
  // target_bits 跨越两个分量
  params.target_bits = {0, 5};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

TEST(QuafuVerifier, CheckTopology_TargetBitsWithIsolatedQubit_ReturnsFalse) {
  // target_bits 包含孤立比特（不在任何耦合边中）和连通比特
  // 孤立比特 7 不在 coupling_list 中
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.999};
  // 7 是孤立比特，0 在连通分量 {0,1,2} 中
  params.target_bits = {0, 7};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// target_bits 整体位于同一连通分量，但自身诱导子图不连通：应失败
TEST(QuafuVerifier,
     CheckTopology_TargetBitsNotFormingConnectedComponent_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  // 耦合图整体连通：0-1-2-3 链
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 0 与 3 在同一连通分量，但诱导子图无边，各自孤立
  params.target_bits = {0, 3};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// target_bits 恰好为一条直连耦合边：诱导子图连通，应通过
TEST(QuafuVerifier, CheckTopology_TargetBitsDirectlyConnected_ReturnsTrue) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {5, 6}, {6, 5}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.0,
                                    0.0,   0.999, 0.999, 0.0};
  // 5 与 6 直连，诱导子图只有一条边，连通
  params.target_bits = {5, 6};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 两个 target_bits 中间隔一个非 target 节点：诱导子图断开，应失败
TEST(QuafuVerifier,
     CheckTopology_TargetBitsSplitByNonTargetNode_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  // 链 0-1-2-3，整体连通
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 0 与 3 都和 1/2 相邻，但 1、2 不在 target_bits 中
  // 诱导子图中 0、3 之间无边，各自孤立
  params.target_bits = {0, 3};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// 三个 target_bits 首尾相连构成链：诱导子图连通，应通过
TEST(QuafuVerifier, CheckTopology_TargetBitsFormChain_ReturnsTrue) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 0-1-2 首尾相邻，诱导子图为 0-1、1-2 两条边，连通
  params.target_bits = {0, 1, 2};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "h q[2];\n"
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// target {0,1,4} 诱导子图：{0,1}连通(容量2)、{4}孤立(容量1)
// 电路 3 比特全连通(团大小3)，超过最大容量2，不可行
TEST(QuafuVerifier, CheckTopology_TargetBitsWithOneIsolated_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 0、1 直连容量2，4 孤立容量1
  params.target_bits = {0, 1, 4};

  QuafuVerifier verifier(params);

  // cz q[0],q[1] + cz q[1],q[2] 使 0,1,2 形成连通团大小3
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cz q[0],q[1];\n"
      "cz q[1],q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// target_bits 有重复但去重后数量正确且连通：应通过
TEST(QuafuVerifier, CheckTopology_TargetBitsDuplicate_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // target_bits 含重复 0，应报错
  params.target_bits = {0, 0, 1, 1, 2};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cz q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

// target_bits 含重复值：应报错
TEST(QuafuVerifier, CheckTopology_TargetBitsDuplicateMiddle_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // target_bits 含重复 1，应报错
  params.target_bits = {0, 1, 1};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cz q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: duplicate target_bits");
}

// target_bits 数量多于电路实际使用比特数：应失败
TEST(QuafuVerifier, CheckTopology_TargetBitsTooMany_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 电路用 2 比特，target_bits 给 3 比特
  params.target_bits = {0, 1, 2};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

// target_bits 数量少于电路实际使用比特数：应失败
TEST(QuafuVerifier, CheckTopology_TargetBitsTooFew_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98, 0.97, 0.97};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 电路用 3 比特，target_bits 只给 2 比特
  params.target_bits = {0, 1};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cz q[0],q[1];\n"
      "h q[2];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

TEST(QuafuVerifier, CheckTopology_TargetBitsOutOfRange_ReturnsFalse) {
  // target_bits 越界（>=bits=8），无论有无多比特门都返回 false
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}};
  params.edge_fidelities = {0.99, 0.99};
  params.single_qubit_fidelities = {0.999, 0.999, 0.0, 0.0,
                                    0.0,   0.0,   0.0, 0.0};
  params.target_bits = {0, 10};

  QuafuVerifier verifier(params);

  // 含双比特门时越界
  std::string qasm_with_cz =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm_with_cz);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target_bit 10 out of range [0, 8)");

  // 全单比特门时越界同样返回 false
  std::string qasm_single =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n";
  auto result2 = verifier.verify(qasm_single);
  EXPECT_FALSE(result2.passed);
  EXPECT_EQ(result2.message,
            "Topology error: target_bit 10 out of range [0, 8)");
}

// 真实芯片拓扑：target_bits 诱导子图分 3 个连通区(容量 5/3/1 及若干 1)。
// 电路在 bin0(5) 和 bin1(3) 的比特间放 cz，形成 6 比特连通团，
// 超过任一 target 连通区容量，不可行。
TEST(QuafuVerifier,
     CheckTopology_RealChip_TargetBitsNotConnected_ReturnsFalse) {
  VerifyParams params;
  params.bits = 83;
  params.coupling_list = {
      {15, 22}, {16, 22}, {16, 23}, {17, 23}, {18, 24}, {18, 25}, {20, 27},
      {22, 29}, {23, 30}, {25, 32}, {27, 34}, {28, 35}, {29, 35}, {30, 36},
      {30, 37}, {31, 37}, {31, 38}, {32, 38}, {32, 39}, {33, 39}, {34, 40},
      {34, 41}, {36, 43}, {37, 44}, {38, 45}, {39, 46}, {41, 48}, {42, 49},
      {43, 49}, {43, 50}, {45, 51}, {46, 53}, {47, 53}, {48, 54}, {49, 56},
      {50, 57}, {51, 58}, {53, 60}, {54, 61}, {59, 66}, {60, 66}, {61, 67},
      {61, 68}, {62, 68}, {62, 69}, {63, 70}, {64, 71}, {66, 73}, {67, 74},
      {68, 75}, {69, 76}, {70, 77}, {71, 77}, {73, 79}, {73, 80}, {74, 80},
      {74, 81}, {75, 81}, {75, 82}, {76, 82}};
  // bin0={15,16,17,22,23} 容量5, bin1={18,24,25} 容量3, 其余孤立容量1
  params.target_bits = {15, 16, 17, 18, 20, 22, 23, 24, 25, 35,
                        36, 37, 38, 39, 40, 79, 80, 81, 82};

  QuafuVerifier verifier(params);

  // cz 链: 15-22-16-23-17(全在 bin0) 再连 17-18(跨 bin0/bin1)
  // 形成 6 比特连通团, 超过最大 bin 容量 5
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[83];\n"
      "cz q[15],q[22];\n"
      "cz q[22],q[16];\n"
      "cz q[16],q[23];\n"
      "cz q[23],q[17];\n"
      "cz q[17],q[18];\n"
      "h q[20];\n"
      "h q[24];\n"
      "h q[25];\n"
      "h q[35];\n"
      "h q[36];\n"
      "h q[37];\n"
      "h q[38];\n"
      "h q[39];\n"
      "h q[40];\n"
      "h q[79];\n"
      "h q[80];\n"
      "h q[81];\n"
      "h q[82];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// bin-packing: target 两个连通区(6,4), 电路三个团(4,3,3)
// 4 放进 bin4, 3+3 放进 bin6, 恰好放满, 可行
TEST(QuafuVerifier, CheckTopology_BinPacking_MultiComponentFits_ReturnsTrue) {
  VerifyParams params;
  params.bits = 12;
  // bin0: 0-1-2-3-4-5 (容量6), bin1: 6-7-8-9 (容量4)
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2},
                          {3, 4}, {4, 3}, {4, 5}, {5, 4}, {6, 7}, {7, 6},
                          {7, 8}, {8, 7}, {8, 9}, {9, 8}};
  params.edge_fidelities = std::vector<double>(16, 0.99);
  params.single_qubit_fidelities = std::vector<double>(12, 0.999);
  params.target_bits = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};

  QuafuVerifier verifier(params);

  // 电路团: {0,1,2,3}大小4, {4,5,6}大小3, {7,8,9}大小3
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[10];\n"
      "cz q[0],q[1];\n"
      "cz q[1],q[2];\n"
      "cz q[2],q[3];\n"
      "cz q[4],q[5];\n"
      "cz q[5],q[6];\n"
      "cz q[7],q[8];\n"
      "cz q[8],q[9];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// bin-packing: target 两个连通区(5,5), 电路两个团(6,4)
// 团6 超过任一 bin 容量5, 不可行
TEST(QuafuVerifier,
     CheckTopology_BinPacking_BigComponentExceedsBin_ReturnsFalse) {
  VerifyParams params;
  params.bits = 12;
  // bin0: 0-1-2-3-4 (容量5), bin1: 5-6-7-8-9 (容量5)
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}, {2, 3}, {3, 2},
                          {3, 4}, {4, 3}, {5, 6}, {6, 5}, {6, 7}, {7, 6},
                          {7, 8}, {8, 7}, {8, 9}, {9, 8}};
  params.edge_fidelities = std::vector<double>(16, 0.99);
  params.single_qubit_fidelities = std::vector<double>(12, 0.999);
  params.target_bits = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};

  QuafuVerifier verifier(params);

  // 电路团: {0,1,2,3,4,5}大小6 (跨 bin0/bin1), {6,7,8,9}大小4
  // 团6 超过最大 bin 容量5
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[10];\n"
      "cz q[0],q[1];\n"
      "cz q[1],q[2];\n"
      "cz q[2],q[3];\n"
      "cz q[3],q[4];\n"
      "cz q[4],q[5];\n"
      "cz q[6],q[7];\n"
      "cz q[7],q[8];\n"
      "cz q[8],q[9];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// bin-packing: target 两个连通区(3,3), 电路一个大团(4) + 两个单比特
// 大团4 超过最大 bin 容量3, 单比特优化不参与回溯, 不可行
TEST(QuafuVerifier,
     CheckTopology_BinPacking_SinglesSkipButBigFails_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  // bin0: 0-1-2 (容量3), bin1: 3-4-5 (容量3)
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1},
                          {3, 4}, {4, 3}, {4, 5}, {5, 4}};
  params.edge_fidelities = std::vector<double>(8, 0.99);
  params.single_qubit_fidelities = std::vector<double>(8, 0.999);
  params.target_bits = {0, 1, 2, 3, 4, 5};

  QuafuVerifier verifier(params);

  // 电路团: {0,1,2,3}大小4 (跨 bin0/bin1), 单比特 4,5
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[6];\n"
      "cz q[0],q[1];\n"
      "cz q[1],q[2];\n"
      "cz q[2],q[3];\n"
      "h q[4];\n"
      "h q[5];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// 真实芯片拓扑完整数据：83 比特、60 条耦合边、19 个 target_bits。
// target 诱导子图: bin0={15,16,17,22,23}容量5, bin1={18,24,25}容量3,
// 11 个孤立比特各容量1。电路来自真实编译请求，交互图形成 4 个连通团
// (大小 6/5/4/4), 最大团 6 > 最大 bin 5, 不可映射, 应失败。
TEST(QuafuVerifier, CheckTopology_RealChip_BinPackingFails_ReturnsFalse) {
  VerifyParams params;
  params.bits = 83;
  params.coupling_list = {
      {15, 22}, {16, 22}, {16, 23}, {17, 23}, {18, 24}, {18, 25}, {20, 27},
      {22, 29}, {23, 30}, {25, 32}, {27, 34}, {28, 35}, {29, 35}, {30, 36},
      {30, 37}, {31, 37}, {31, 38}, {32, 38}, {32, 39}, {33, 39}, {34, 40},
      {34, 41}, {36, 43}, {37, 44}, {38, 45}, {39, 46}, {41, 48}, {42, 49},
      {43, 49}, {43, 50}, {45, 51}, {46, 53}, {47, 53}, {48, 54}, {49, 56},
      {50, 57}, {51, 58}, {53, 60}, {54, 61}, {59, 66}, {60, 66}, {61, 67},
      {61, 68}, {62, 68}, {62, 69}, {63, 70}, {64, 71}, {66, 73}, {67, 74},
      {68, 75}, {69, 76}, {70, 77}, {71, 77}, {73, 79}, {73, 80}, {74, 80},
      {74, 81}, {75, 81}, {75, 82}, {76, 82}};
  params.edge_fidelities = {
      0.989, 0.997, 0.996, 0.998, 0.988, 0.995, 0.981, 0.992, 0.994, 0.978,
      0.997, 0.993, 0.993, 0.973, 0.986, 0.985, 0.987, 0.988, 0.993, 0.991,
      0.997, 0.997, 0.985, 0.990, 0.997, 0.982, 0.995, 0.996, 0.998, 0.990,
      0.994, 0.996, 0.992, 0.996, 0.991, 0.994, 0.991, 0.995, 0.997, 0.983,
      0.990, 0.983, 0.989, 0.999, 0.987, 0.995, 0.992, 0.988, 0.986, 0.997,
      0.996, 0.995, 0.998, 0.984, 0.996, 0.982, 0.993, 0.984, 0.996, 0.998};
  params.single_qubit_fidelities = {
      0.997, 0.997, 0.999, 0.997, 0.999, 0.999, 0.999, 0.976, 0.996, 0.996,
      0.994, 0.994, 0.997, 0.998, 0.999, 0.999, 0.999, 0.999, 0.996, 0.999,
      0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.997, 0.999, 0.999, 0.999,
      0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999,
      0.999, 0.999, 0.999, 0.997, 0.995, 0.999, 0.999, 0.999, 0.999, 0.999,
      0.999, 0.999, 0.999, 0.999, 0.998, 0.999, 0.999, 0.999, 0.996, 0.998,
      0.999, 0.999, 0.996, 0.999, 0.999, 0.999, 0.999, 0.992, 0.999, 0.999,
      0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999, 0.999,
      0.999, 0.999, 0.999};
  params.target_bits = {15, 16, 17, 18, 20, 22, 23, 24, 25, 35,
                        36, 37, 38, 39, 40, 79, 80, 81, 82};

  QuafuVerifier verifier(params);

  // 真实电路: 交互团 {15,16,17,18}=4, {20,22,23,24,25}=5,
  // {35,36,37,38,39,40}=6, {79,80,81,82}=4。bins=[5,3,1*11],
  // 最大团 6 > 最大 bin 5, 不可映射。
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[83];\n"
      "creg c[83];\n"
      "cz q[16],q[15];\n"
      "cy q[22],q[20];\n"
      "rzz(1.570796) q[24],q[25];\n"
      "ccz q[36],q[37],q[35];\n"
      "ccz q[39],q[40],q[38];\n"
      "ccx q[82],q[80],q[79];\n"
      "id q[15];\n"
      "cy q[16],q[17];\n"
      "cswap q[24],q[23],q[22];\n"
      "ccx q[38],q[37],q[36];\n"
      "cy q[40],q[39];\n"
      "cswap q[79],q[81],q[80];\n"
      "x q[82];\n"
      "t q[16];\n"
      "t q[17];\n"
      "ryy(1.570796) q[24],q[23];\n"
      "cz q[80],q[79];\n"
      "h q[81];\n"
      "ccx q[17],q[15],q[18];\n"
      "x q[15];\n"
      "t q[16];\n"
      "sx q[17];\n"
      "cx q[16],q[15];\n"
      "iswap q[18],q[17];\n"
      "y q[15];\n"
      "rx(1.570796) q[16];\n"
      "tdg q[17];\n"
      "cp(1.570796) q[16],q[15];\n"
      "swap q[18],q[17];\n"
      "rzz(1.570796) q[16],q[15];\n"
      "ryy(1.570796) q[17],q[16];\n"
      "rxx(1.570796) q[15],q[16];\n"
      "ccx q[16],q[17],q[15];\n"
      "z q[15];\n"
      "sxdg q[16];\n"
      "ry(1.570796) q[17];\n"
      "h q[15];\n"
      "rz(1.570796) q[16];\n"
      "p(1.570796) q[15];\n"
      "cswap q[16],q[18],q[17];\n"
      "ccz q[16],q[17],q[15];\n"
      "u3(1.570796,1.570796,1.570796) q[15];\n"
      "s q[15];\n"
      "sdg q[15];\n"
      "rxx(1.570796) q[16],q[15];\n"
      "rzz(1.570796) q[17],q[15];\n"
      "measure q[15] -> c[15];\n"
      "measure q[16] -> c[16];\n"
      "measure q[17] -> c[17];\n"
      "measure q[18] -> c[18];\n"
      "measure q[20] -> c[20];\n"
      "measure q[22] -> c[22];\n"
      "measure q[23] -> c[23];\n"
      "measure q[24] -> c[24];\n"
      "measure q[25] -> c[25];\n"
      "measure q[35] -> c[35];\n"
      "measure q[36] -> c[36];\n"
      "measure q[37] -> c[37];\n"
      "measure q[38] -> c[38];\n"
      "measure q[39] -> c[39];\n"
      "measure q[40] -> c[40];\n"
      "measure q[79] -> c[79];\n"
      "measure q[80] -> c[80];\n"
      "measure q[81] -> c[81];\n"
      "measure q[82] -> c[82];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// === Shenglian 拓扑 bin-packing 综合用例 ===

// 1. 4比特 cx[0,1]+measure 0,1, target=[15,22](相连), 电路2比特→可装入→PASS
TEST(QuafuVerifier, Shenglian_CxMeasure2_TargetConnected_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "creg c[4];\n"
      "cx q[0],q[1];\n"
      "measure q[0] -> c[0];\n"
      "measure q[1] -> c[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 2. 4比特 cx[0,1]+measure 0,1, target=[15,16](不相连), 电路团2 >
// bin[1,1]→FAIL
TEST(QuafuVerifier, Shenglian_CxMeasure2_TargetDisconnected_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 16};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "creg c[4];\n"
      "cx q[0],q[1];\n"
      "measure q[0] -> c[0];\n"
      "measure q[1] -> c[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// 3. 4比特 cx[0,1]+measure 0,1,2,3(用4比特), target=[15,22](2个),
// 数量不符→FAIL
TEST(QuafuVerifier, Shenglian_CxMeasure4_TargetCountMismatch_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "creg c[4];\n"
      "cx q[0],q[1];\n"
      "measure q[0] -> c[0];\n"
      "measure q[1] -> c[1];\n"
      "measure q[2] -> c[2];\n"
      "measure q[3] -> c[3];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Topology error: target qubits number mismatch with circuit");
}

// 4. 4比特 x[0],x[1]+measure 2,3, target=[15,16,18,20](不相连),
//    全单比特门, 不触发连通性检查, 数量匹配→PASS
TEST(QuafuVerifier, Shenglian_AllSingleQubit_DisconnectedTarget_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 16, 18, 20};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[4];\n"
      "creg c[4];\n"
      "x q[0];\n"
      "x q[1];\n"
      "measure q[2] -> c[2];\n"
      "measure q[3] -> c[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 5. 6比特 cx[0,1]+cx[2,3](用4比特), target=[15,22,18,25](两对相连),
//    items[2,2], bins[2,2], 可装入→PASS
TEST(QuafuVerifier, Shenglian_TwoCx_TwoConnectedPairs_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 18, 25};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[6];\n"
      "creg c[6];\n"
      "cx q[0],q[1];\n"
      "cx q[2],q[3];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 6. 6比特 cx[0,1]+cx[2,3]+x[4]+x[5](用6比特), target=[15,22,18,25,20,40],
//    items[2,2,1,1], bins[2,2,1,1], 可装入→PASS
TEST(QuafuVerifier, Shenglian_TwoCxTwoSingle_SixTargets_ReturnsTrue) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 18, 25, 20, 40};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[6];\n"
      "creg c[6];\n"
      "cx q[0],q[1];\n"
      "cx q[2],q[3];\n"
      "x q[4];\n"
      "x q[5];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 7. 6比特 cx[0,1]+cx[2,3]+cx[4,5](用6比特), target=[15,22,18,25,20,40],
//    items[2,2,2], bins[2,2,1,1], 第三个团2放不进容量1的bin→FAIL
TEST(QuafuVerifier, Shenglian_ThreeCx_ThirdCantFit_ReturnsFalse) {
  auto params = make_shenglian_params();
  params.target_bits = {15, 22, 18, 25, 20, 40};
  QuafuVerifier verifier(params);
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[6];\n"
      "creg c[6];\n"
      "cx q[0],q[1];\n"
      "cx q[2],q[3];\n"
      "cx q[4],q[5];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(
      result.message,
      "Topology error: circuit topology cannot be mapped onto target_bits");
}

// check_depth_and_gate_count

TEST(QuafuVerifier, CheckDepthAndGateCount_200Cx_ReturnsTrue) {
  QuafuVerifier verifier(make_test_params());
  // 200 个 cx 门，刚好在限制内
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n";
  for (int i = 0; i < 200; ++i) qasm += "cx q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier, CheckDepthAndGateCount_201Cx_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());
  // 201 个 cx 门，超出限制
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n";
  for (int i = 0; i < 201; ++i) qasm += "cx q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "Gate count error: 201 multi-qubit gates exceed limit 200");
}

TEST(QuafuVerifier,
     CheckDepthAndGateCount_CcxDecomposesOverLimit_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());
  // 40 个 ccx 门：多比特门数 40 <= 200（第一次检查通过），
  // 但分解后约 240 个 cx 门 > 200（第二次检查失败）
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

TEST(QuafuVerifier, CheckDepth_200SequentialGates_Passes) {
  QuafuVerifier verifier(make_test_params());
  // 200 个 h 门串行在同一比特上，深度 = 200
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[1];\n";
  for (int i = 0; i < 200; ++i) qasm += "h q[0];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier, CheckDepth_201SequentialGates_Fails) {
  QuafuVerifier verifier(make_test_params());
  // 201 个 h 门串行在同一比特上，深度 = 201 > 200
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

// verify（完整入口）

TEST(QuafuVerifier, Verify_ValidCircuit_ReturnsTrue) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "creg c[2];\n"
      "h q[0];\n"
      "cz q[0],q[1];\n"
      "measure q[0] -> c[0];\n";

  EXPECT_TRUE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier, Verify_InvalidQasm_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm = "OPENQASM 3.0;\nqubit[2] q;\n";

  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message,
            "QASM syntax error: only OPENQASM 2.0 is supported");
}
