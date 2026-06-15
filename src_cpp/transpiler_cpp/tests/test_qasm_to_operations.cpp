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

#include <time.h>

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "compiler/qasm_to_origin_ir.hpp"
#include "gtest/gtest.h"

using namespace std;

#ifndef PRECISION
#define PRECISION 0.000001
#endif  // !PRECISION

class QASMToOperationsTest {
 public:
  std::string SX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
creg c[2];
SX q[1];
)";

  std::string SXdg_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
creg c[2];
SXdg q[1];
sxdg q[0];
)";

  std::string ISWAP_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
iswap q[0],q[1];
)";

  std::string DCX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
DCX q[0],q[1];
dcx q[0],q[1];
)";

  std::string CP_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
CP(3.14) q[0],q[1];

)";

  std::string CS_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
CS q[0],q[1];
cs q[0],q[1];
)";

  std::string CSdg_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
CSdg q[0],q[1];
csdg q[0],q[1];
)";

  std::string CCZ_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[3] q;
CCZ q[0],q[1],q[2];
ccz q[0],q[1],q[2];
)";

  std::string ECR_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
ECR q[0],q[1];
ecr q[0],q[1];
)";

  std::string R_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
R(3.14,3.15) q[0];
r(3.14,3.15) q[0];
)";

  std::string XXMinusYY_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
XXMinusYY(3.14,3.15) q[0],q[1];
xx_minus_yy(3.14,3.15) q[0],q[1];
)";

  std::string XXPlusYY_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
XXPlusYY(3.14,3.15) q[0],q[1];
xx_plus_yy(3.14,3.15) q[0],q[1];
)";

  std::string V_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
V q[0];
v q[0];
)";

  std::string W_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
W q[0];
w q[0];
)";

  std::string CCX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

toffoli q[0], q[1], q[2];
TOFFOLI q[0], q[1], q[2];
ccx q[0], q[1], q[2];
CCX q[0], q[1], q[2];
)";

  std::string CH_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

ch q[0], q[1];
)";

  std::string CNOT_CZ_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

cx q[0], q[1];
CX q[0], q[1];
cnot q[0], q[1];
CNOT q[0], q[1];

cz q[0], q[1];
CZ q[1], q[0];
)";

  std::string CRX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
crx(3.14) q[0], q[1];
CRX(3.14) q[0], q[1];
)";

  std::string CRY_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
cry(3.14) q[0], q[1];
CRY(3.14) q[0], q[1];
)";

  std::string CRZ_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;
crz(3.14) q[0], q[1];
CRZ(3.14) q[0], q[1];
)";

  std::string CSWAP_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;

cswap q[0], q[1], q[2];
CSWAP q[0], q[1], q[2];
)";

  std::string CSX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

csx q[0], q[1];
CSX q[0], q[1];
)";

  std::string CU_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

cu(3.14, 3.15, 3.16, 3.17) q[1], q[2];
CU(3.14, 3.15, 3.16, 3.17) q[1], q[2];
)";

  std::string CU1_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

cp(3.14)q[0], q[1];
cu1(3.14)q[0], q[1];
CP(3.14)q[0], q[1];
CU1(3.14)q[0], q[1];
cphase(3.14)q[0], q[1];
CPHASE(3.14)q[0], q[1];
)";

  std::string CU3_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

cu3(3.14, 3.15, 3.16) q[1], q[2];
CU3(3.14, 3.15, 3.16) q[1], q[2];
)";

  std::string CY_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

cy q[0], q[1];
)";

  std::string C3SQRTX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

c3sqrtx q[0], q[1], q[2], q[3];
C3SQRTX q[0], q[1], q[2], q[3];
)";

  std::string C3X_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

c3x q[0], q[1], q[2], q[3];
C3X q[0], q[1], q[2], q[3];
)";

  std::string C4X_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[5] q;

c4x q[0], q[1], q[2], q[3], q[4];
C4X q[0], q[1], q[2], q[3], q[4];
)";

  std::string H_X_Y_Z_S_T_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;
h q[0];
H q[1];

id q[1];
u0 q[3];

x q[0];
X q[1];

y q[0];
Y q[1];

z q[0];
Z q[1];

s q[0];
S q[1];

t q[0];
T q[1];
)";

  std::string RCCX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
rccx q[0], q[1], q[2];
RCCX q[0], q[1], q[2];
)";

  std::string RC3X_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;
rc3x q[0], q[1], q[2], q[3];
RC3X q[0], q[1], q[2], q[3];
)";

  std::string RXX_RYY_RZZ_RZX_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

rxx(3.14) q[0], q[1];
RXX(3.15) q[0], q[1];

ryy(3.14) q[0], q[1];
RYY(3.15) q[0], q[1];

rzz(3.14) q[0], q[1];
RZZ(3.15) q[0], q[1];

rzx(3.14) q[0], q[1];
RZX(3.15) q[0], q[1];
)";

  std::string RX_RY_RZ_P_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

rx(3.14) q[0];
RX(3.15) q[1];

ry(3.14) q[0];
RY(3.15) q[1];

rz(3.14) q[0];
RZ(3.15) q[1];

p(3.14) q[0];
P(3.15) q[0];
u1(3.16) q[0];
U1(3.17) q[0];
phase(3.18) q[0];
)";

  std::string SDG_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;

sdg q[0];
SDG q[0];
Sdg q[0];
)";

  std::string SWAP_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

swap q[0], q[1];
SWAP q[1], q[0];
)";

  std::string TDG_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[2] q;

tdg q[0];
TDG q[0];
Tdg q[0];
)";

  std::string U2_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

u2(3.14, 3.15) q[0];
U2(3.14, 3.15) q[0];
)";

  std::string U3_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[4] q;

u(3.14, 3.15, 3.16) q[0];
u3(3.14, 3.15, 3.16) q[0];
U(3.14, 3.15, 3.16) q[0];
U3(3.14, 3.15, 3.16) q[0];
)";

  // quantum instructions

  std::string RESET_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[3] q;
reset q[0];
)";

  std::string MEASURE_qasm = R"(
qubit[4] q;
bit[4] c;
x q[2];
c[2] = measure q[2];
)";

  std::string BARRIER_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[5] q;
barrier q[0],q[1],q[2],q[3];
barrier;
)";

  // Classical expr
  std::string Classical_expr_qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";

qubit[5] q;
bit[2] c;
rz(pi - 5) q[0];
c[1] = measure q[0]; 
)";

  std::string a_b = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[100] q;
bit[100] c;
for int m in [0:49999] {
    rx(1) q;
}
measure q -> c;
)";

  std::string qasm_path1 =
      std::string(TEST_DATA_DIR) + R"(qasm/2.0/bigadder.qasm)";
  std::string qasm_path2 =
      std::string(TEST_DATA_DIR) +
      R"(qasm/2.0/benchmark/random_n100_d50000_clifford_197783.qasm)";

  static bool test_qasm2operations(const std::string& qasm_str) {
    std::vector<std::shared_ptr<qcos::BaseOperation>> operations =
        convert_qasm_string_to_qcos_operations(qasm_str).first;
    return true;
  }

  static bool test_qasm2operationsfromfile(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
      std::cerr << "Error: Failed to open file: " << filepath << std::endl;
      return false;
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    file.close();
    std::string qasm_str = buffer.str();
    std::vector<std::shared_ptr<qcos::BaseOperation>> operations =
        convert_qasm_string_to_qcos_operations(qasm_str).first;
    return true;
  }
};

TEST(QASMToGateOperation, StandardGate) {
  QASMToOperationsTest test_;

  bool test_actual = true;
  try {
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.SX_qasm);

    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.SXdg_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.ISWAP_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.DCX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CS_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.ECR_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.R_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CSdg_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CCX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CH_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.CNOT_CZ_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CRX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CRY_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CRZ_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CSWAP_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CSX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CU_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CU1_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CU3_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CY_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.CP_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.C3SQRTX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.C3X_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.C4X_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.H_X_Y_Z_S_T_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.RCCX_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.RC3X_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.RXX_RYY_RZZ_RZX_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.RX_RY_RZ_P_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.SDG_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.SWAP_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.TDG_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.U2_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.U3_qasm);
  }

  catch (const std::exception& e) {
    std::cout << "Got a exception: " << e.what() << std::endl;
  } catch (...) {
    std::cout << "Got an unknow exception: " << std::endl;
  }

  ASSERT_TRUE(test_actual);
}

TEST(QASMToGateOperation, Instructions) {
  QASMToOperationsTest test_;
  bool test_actual = true;
  try {
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.MEASURE_qasm);
    test_actual = test_actual &&
                  QASMToOperationsTest::test_qasm2operations(test_.RESET_qasm);
    test_actual = test_actual && QASMToOperationsTest::test_qasm2operations(
                                     test_.BARRIER_qasm);

  }

  catch (const std::exception& e) {
    std::cout << "Got a exception: " << e.what() << std::endl;
  } catch (...) {
    std::cout << "Got an unknow exception: " << std::endl;
  }

  ASSERT_TRUE(test_actual);
}

TEST(QASMToGateOperation, QASMInstance) {
  QASMToOperationsTest test_;
  bool test_actual = true;
  try {
    test_actual =
        test_actual &&
        QASMToOperationsTest::test_qasm2operationsfromfile(test_.qasm_path1);
  } catch (const std::exception& e) {
    std::cout << "Got a exception: " << e.what() << std::endl;
  } catch (...) {
    std::cout << "Got an unknow exception: " << std::endl;
  }

  ASSERT_TRUE(test_actual);
}

TEST(QASMToGateOperation, N100D50000Instance) {
  QASMToOperationsTest test_;
  bool test_actual = true;
  try {
    test_actual =
        test_actual &&
        QASMToOperationsTest::test_qasm2operationsfromfile(test_.qasm_path2);
  } catch (const std::exception& e) {
    std::cout << "Got a exception: " << e.what() << std::endl;
  } catch (...) {
    std::cout << "Got an unknow exception: " << std::endl;
  }

  ASSERT_TRUE(test_actual);
}
