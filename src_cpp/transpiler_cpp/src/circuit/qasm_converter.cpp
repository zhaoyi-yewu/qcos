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

#include "circuit/qasm_converter.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace qcos {

QasmConverter::QasmConverter(const QuantumCircuit& circuit)
    : operations_(circuit.get_operations()),
      qubit_num_(circuit.num_qubits()) {
  if (qubit_num_ == 0) {
    int max_idx = -1;
    for (const auto& op : operations_) {
      if (!op->targets.empty()) {
        int local_max = *std::max_element(op->targets.begin(),
                                          op->targets.end());
        max_idx = std::max(max_idx, local_max);
      }
    }
    if (max_idx >= 0) {
      qubit_num_ = max_idx + 1;
    }
  }
}

std::string QasmConverter::to_qasm2() const {
  std::ostringstream oss;
  oss << "OPENQASM 2.0;\n";
  oss << "include \"qelib1.inc\";\n";
  oss << "qreg q[" << qubit_num_ << "];\n";
  oss << "creg c[" << qubit_num_ << "];\n";
  oss << "\n";

  for (const auto& op : operations_) {
    oss << convert_op_to_qasm2(*op) << "\n";
  }

  return oss.str();
}

std::string QasmConverter::convert_op_to_qasm2(const BaseOperation& op) const {
  std::string name_lower = to_lower(op.name);
  if (name_lower == "measure" || name_lower == "reset") {
    const auto& t = op.targets;
    if (name_lower == "measure") {
      return "measure q[" + std::to_string(t[0]) + "] -> c[" +
             std::to_string(t[0]) + "];";
    } else {
      return "reset q[" + std::to_string(t[0]) + "];";
    }
  }
  return op.to_openqasm("q");
}

std::string QasmConverter::to_qasm3() const {
  std::ostringstream oss;
  oss << "OPENQASM 3.0;\n";
  oss << "include \"stdgates.inc\";\n";
  oss << "qubit[" << qubit_num_ << "] q;\n";
  oss << "bit[" << qubit_num_ << "] c;\n";
  oss << "\n";

  for (const auto& op : operations_) {
    oss << convert_op_to_qasm3(*op) << "\n";
  }

  return oss.str();
}

std::string QasmConverter::convert_op_to_qasm3(const BaseOperation& op) const {
  std::string name_lower = to_lower(op.name);
  const auto& t = op.targets;
  if (name_lower == "measure") {
    return "measure q[" + std::to_string(t[0]) + "] -> c[" +
           std::to_string(t[0]) + "];";
  } else if (name_lower == "reset") {
    return "reset q[" + std::to_string(t[0]) + "];";
  }
  return op.to_openqasm("q");
}

void QasmConverter::save(const std::string& path,
                         const std::string& version) const {
  std::string text;
  if (version.size() >= 1 && version[0] == '2') {
    text = to_qasm2();
  } else if (version.size() >= 1 && version[0] == '3') {
    text = to_qasm3();
  } else {
    throw std::invalid_argument("Unknown QASM version: " + version);
  }

  std::ofstream ofs(path);
  if (!ofs) {
    throw std::runtime_error("Failed to open file: " + path);
  }
  ofs << text;
}

std::string QasmConverter::to_lower(std::string_view s) {
  std::string result(s);
  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return result;
}

}  // namespace qcos
