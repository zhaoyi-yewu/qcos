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
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <string>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/quantum_circuit.h"

namespace qcos {

class QasmConverter {
 public:
  explicit QasmConverter(const QuantumCircuit& circuit);

  std::string to_qasm2() const;
  std::string to_qasm3() const;

  void save(const std::string& path, const std::string& version = "2.0") const;

 private:
  std::string convert_op_to_qasm2(const BaseOperation& op) const;
  std::string convert_op_to_qasm3(const BaseOperation& op) const;
  static std::string to_lower(std::string_view s);

  std::vector<std::shared_ptr<BaseOperation>> operations_;
  int qubit_num_;
};

}  // namespace qcos
