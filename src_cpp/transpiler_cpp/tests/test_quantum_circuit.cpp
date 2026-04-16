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
#include <stdexcept>
#include <vector>

#include "circuit/gate_operation.h"
#include "circuit/quantum_circuit.h"

using namespace qcos;

TEST(QuantumCircuitTest, InitValidAndInvalid) {
  QuantumCircuit qc(2, 2);

  EXPECT_EQ(qc.num_qubits(), 2);
  EXPECT_EQ(qc.num_clbits(), 2);
  EXPECT_EQ(qc.size(), 0);

  EXPECT_THROW(QuantumCircuit(-1, -1), std::invalid_argument);
}

TEST(QuantumCircuitTest, AppendPreservesOrderAndTargets) {
  QuantumCircuit qc(2, 2);
  qc.append(std::make_shared<X>(std::vector<int>{0}));
  qc.append(std::make_shared<CX>(std::vector<int>{0, 1}));
  qc.append(std::make_shared<H>(std::vector<int>{1}));

  const auto& gates = qc.get_operations();
  ASSERT_EQ(gates.size(), 3u);
  EXPECT_EQ(gates[0]->name, "x");
  EXPECT_EQ(gates[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(gates[1]->name, "cx");
  EXPECT_EQ(gates[1]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(gates[2]->name, "h");
  EXPECT_EQ(gates[2]->targets, std::vector<int>({1}));
}

TEST(QuantumCircuitTest, AppendOperationsAndSetters) {
  QuantumCircuit qc;
  qc.set_num_qubits(2);
  qc.set_num_clbits(2);
  qc.set_global_phase(3.14159265358979323846);

  std::vector<std::shared_ptr<BaseOperation>> gates = {
      std::make_shared<X>(std::vector<int>{0}),
      std::make_shared<CX>(std::vector<int>{0, 1}),
      std::make_shared<H>(std::vector<int>{1})};
  qc.append_operations(gates);

  EXPECT_EQ(qc.num_qubits(), 2);
  EXPECT_EQ(qc.num_clbits(), 2);
  EXPECT_DOUBLE_EQ(qc.global_phase(), 3.14159265358979323846);
  ASSERT_EQ(qc.get_operations().size(), 3u);
  EXPECT_EQ(qc.get_operations()[1]->name, "cx");

  EXPECT_THROW(qc.set_num_qubits(-1), std::invalid_argument);
  EXPECT_THROW(qc.set_num_clbits(-1), std::invalid_argument);
}

TEST(QuantumCircuitTest, DepthWidthAndSize) {
  QuantumCircuit qc(2, 2);
  qc.append(std::make_shared<X>(std::vector<int>{0}));
  qc.append(std::make_shared<H>(std::vector<int>{1}));
  qc.append(std::make_shared<CX>(std::vector<int>{0, 1}));

  EXPECT_EQ(qc.depth(), 2);
  // quantum bit + classical bit
  EXPECT_EQ(qc.width(), 4);
  EXPECT_EQ(qc.num_qubits(), 2);
  EXPECT_EQ(qc.size(), 3);
}

TEST(QuantumCircuitTest, FromIrBuildsCircuitAndExpandsWidth) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<H>(std::vector<int>{0}),
      std::make_shared<CX>(std::vector<int>{0, 1}),
      std::make_shared<H>(std::vector<int>{1})};

  auto circuit = QuantumCircuit::from_ir(ir);
  ASSERT_NE(circuit, nullptr);
  EXPECT_EQ(circuit->num_qubits(), 2);
  EXPECT_EQ(circuit->size(), 3);

  QuantumCircuit appended;
  appended.append(std::make_shared<H>(std::vector<int>{2}));
  EXPECT_EQ(appended.num_qubits(), 3);
  EXPECT_THROW(appended.append(nullptr), std::invalid_argument);
}