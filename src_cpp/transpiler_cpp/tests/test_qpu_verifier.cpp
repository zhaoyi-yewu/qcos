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

#include "verify/quafu_verifier.h"

using namespace qcos;

namespace {

VerifyParams make_test_params() {
  VerifyParams params;
  params.bits = 8;
  params.basis_gates = {"h", "rx", "ry", "rz", "cz"};
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  return params;
}

}  // namespace

// check_qasm_syntax

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

  EXPECT_TRUE(verifier.check_qasm_syntax(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_Qasm3Header_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "OPENQASM 3.0;\n"
      "include \"stdgates.inc\";\n"
      "qubit[2] q;\n"
      "h q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_NoHeader_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm = "qreg q[2];\nh q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_InvalidGate_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());

  // "foobar" 不是合法门名，解析会失败
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "foobar q[0];\n";

  EXPECT_FALSE(verifier.check_qasm_syntax(qasm));
}

TEST(QuafuVerifier, CheckQasmSyntax_CommentBeforeHeader) {
  QuafuVerifier verifier(make_test_params());

  std::string qasm =
      "// this is a comment\n"
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n";

  EXPECT_TRUE(verifier.check_qasm_syntax(qasm));
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
}

TEST(QuafuVerifier, CheckTopology_ZeroQubits_ReturnsFalse) {
  QuafuVerifier verifier(make_test_params());
  // qreg q[0] 声明 0 个比特
  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[0];\n";
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
  EXPECT_FALSE(verifier.verify(qasm).message.empty());
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_EQ(result.message, "Topology error: target_bits are not connected");
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
      "cz q[0],q[1];\n";
  EXPECT_TRUE(verifier.verify(qasm).passed);
}

// 三个 target_bits 中一个孤立（不在任何耦合边）：诱导子图缺节点，应失败
TEST(QuafuVerifier, CheckTopology_TargetBitsWithOneIsolated_ReturnsFalse) {
  VerifyParams params;
  params.bits = 8;
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  // 0、1 直连，但 4 不在任何耦合边中
  params.target_bits = {0, 1, 4};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: target_bits are not connected");
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
  EXPECT_FALSE(verifier.verify(qasm_with_cz).passed);

  // 全单比特门时越界同样返回 false
  std::string qasm_single =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "h q[0];\n";
  EXPECT_FALSE(verifier.verify(qasm_single).passed);
}

// 真实芯片拓扑：83 比特，18 个 target_bits 诱导子图不连通，应失败
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
  params.target_bits = {15, 16, 17, 18, 20, 22, 23, 24, 25, 35,
                        36, 37, 38, 39, 40, 79, 80, 81, 82};

  QuafuVerifier verifier(params);

  std::string qasm =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[2];\n"
      "cz q[0],q[1];\n";
  auto result = verifier.verify(qasm);
  EXPECT_FALSE(result.passed);
  EXPECT_EQ(result.message, "Topology error: target_bits are not connected");
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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
  EXPECT_FALSE(verifier.verify(qasm).passed);
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

  EXPECT_FALSE(verifier.verify(qasm).passed);
}
