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

#include "circuit/quantum_circuit.h"

#include <algorithm>
#include <unordered_set>

namespace qcos {

QuantumCircuit::QuantumCircuit(int num_qubits, int num_clbits,
                               double global_phase)
    : num_qubits_(num_qubits),
      num_clbits_(num_clbits),
      global_phase_(global_phase) {
  if (num_qubits < 0 || num_clbits < 0) {
    throw std::invalid_argument(
        "Number of qubits and clbits must be non-negative.");
  }
}

std::shared_ptr<QuantumCircuit> QuantumCircuit::from_ir(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int num_qubits) {
  auto circuit = std::make_shared<QuantumCircuit>(num_qubits);
  circuit->append_operations(ir);
  return circuit;
}

void QuantumCircuit::append(std::shared_ptr<BaseOperation> operation) {
  if (!operation) {
    throw std::invalid_argument("Invalid operation type!");
  }
  if (!operation->targets.empty()) {
    int max_target = *std::max_element(operation->targets.begin(),
                                       operation->targets.end());
    if (max_target + 1 > num_qubits_) {
      num_qubits_ = max_target + 1;
    }
  }
  operations_.push_back(std::move(operation));
}

void QuantumCircuit::append_operations(
    const std::vector<std::shared_ptr<BaseOperation>>& operations) {
  for (const auto& operation : operations) {
    if (!operation->targets.empty()) {
      int max_target = *std::max_element(operation->targets.begin(),
                                         operation->targets.end());
      if (max_target + 1 > num_qubits_) {
        num_qubits_ = max_target + 1;
      }
    }
    operations_.push_back(operation);
  }
}

int QuantumCircuit::depth() const {
  std::vector<int> qubit_ops(num_qubits_ + num_clbits_, 0);
  static const std::unordered_set<std::string> ignore_gates = {"sync", "reset",
                                                               "move"};
  for (const auto& operation : operations_) {
    int max_level = 0;
    for (int qubit : operation->targets) {
      if (qubit < static_cast<int>(qubit_ops.size())) {
        int level = ignore_gates.count(operation->name) ? qubit_ops[qubit]
                                                        : qubit_ops[qubit] + 1;
        max_level = std::max(max_level, level);
      }
    }
    for (int qubit : operation->targets) {
      if (qubit < static_cast<int>(qubit_ops.size())) {
        qubit_ops[qubit] = max_level;
      }
    }
  }
  return qubit_ops.empty()
             ? 0
             : *std::max_element(qubit_ops.begin(), qubit_ops.end());
}

}  // namespace qcos
