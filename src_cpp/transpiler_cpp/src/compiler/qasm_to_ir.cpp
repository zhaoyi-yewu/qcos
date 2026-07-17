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

#include "compiler/qasm_to_ir.hpp"

#include "circuit/gate_operation.h"
#include "compiler/quantum_computation.hpp"

using namespace qcos;

std::pair<std::vector<std::shared_ptr<qcos::BaseOperation>>, int> qasm_to_ir(
    const std::string& qasm_str) {
  qc::QuantumComputation qc{};
  qc.importOpenQASM(qasm_str);
  int qubits_num = static_cast<int>(qc.getNqubits());
  return {std::move(qc.getOps()), qubits_num};
}
