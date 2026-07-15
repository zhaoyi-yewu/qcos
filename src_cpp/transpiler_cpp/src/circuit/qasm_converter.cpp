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

#include "circuit/gate_operation.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace qcos {

namespace detail {

std::string to_lower(std::string_view s) {
  std::string result(s);
  std::transform(result.begin(), result.end(), result.begin(),
                 [](unsigned char c) { return std::tolower(c); });
  return result;
}

std::string convert_op_to_qasm2(const BaseOperation& op) {
  std::string name_lower = to_lower(op.name);
  if (name_lower == "measure") {
    const auto& t = op.targets;
    const auto* measure = dynamic_cast<const Measure*>(&op);
    const auto& c = measure ? measure->cbits : t;
    return "measure q[" + std::to_string(t[0]) + "] -> c[" +
           std::to_string(c[0]) + "];";
  }
  if (name_lower == "reset") {
    return "reset q[" + std::to_string(op.targets[0]) + "];";
  }
  return op.to_openqasm("q");
}

std::string convert_op_to_qasm3(const BaseOperation& op) {
  std::string name_lower = to_lower(op.name);
  if (name_lower == "measure") {
    const auto& t = op.targets;
    const auto* measure = dynamic_cast<const Measure*>(&op);
    const auto& c = measure ? measure->cbits : t;
    return "measure q[" + std::to_string(t[0]) + "] -> c[" +
           std::to_string(c[0]) + "];";
  }
  if (name_lower == "reset") {
    return "reset q[" + std::to_string(op.targets[0]) + "];";
  }
  return op.to_openqasm("q");
}

}  // namespace detail

std::string to_qasm2(
    const std::vector<std::shared_ptr<BaseOperation>>& operations) {
  std::ostringstream body;
  int max_idx = -1;
  for (const auto& op : operations) {
    if (!op->targets.empty()) {
      int local_max =
          *std::max_element(op->targets.begin(), op->targets.end());
      max_idx = std::max(max_idx, local_max);
    }
    body << detail::convert_op_to_qasm2(*op) << "\n";
  }
  int qubit_num = max_idx >= 0 ? max_idx + 1 : 0;

  std::ostringstream oss;
  oss << "OPENQASM 2.0;\n";
  oss << "include \"qelib1.inc\";\n";
  oss << "qreg q[" << qubit_num << "];\n";
  oss << "creg c[" << qubit_num << "];\n";
  oss << "\n";
  oss << body.str();

  return oss.str();
}

std::string to_qasm3(
    const std::vector<std::shared_ptr<BaseOperation>>& operations) {
  std::ostringstream body;
  int max_idx = -1;
  for (const auto& op : operations) {
    if (!op->targets.empty()) {
      int local_max =
          *std::max_element(op->targets.begin(), op->targets.end());
      max_idx = std::max(max_idx, local_max);
    }
    body << detail::convert_op_to_qasm3(*op) << "\n";
  }
  int qubit_num = max_idx >= 0 ? max_idx + 1 : 0;

  std::ostringstream oss;
  oss << "OPENQASM 3.0;\n";
  oss << "include \"stdgates.inc\";\n";
  oss << "qubit[" << qubit_num << "] q;\n";
  oss << "bit[" << qubit_num << "] c;\n";
  oss << "\n";
  oss << body.str();

  return oss.str();
}

void save_qasm(const std::string& path,
               const std::vector<std::shared_ptr<BaseOperation>>& operations,
               const std::string& version) {
  std::string text;
  if (version.size() >= 1 && version[0] == '2') {
    text = to_qasm2(operations);
  } else if (version.size() >= 1 && version[0] == '3') {
    text = to_qasm3(operations);
  } else {
    throw std::invalid_argument("Unknown QASM version: " + version);
  }

  std::ofstream ofs(path);
  if (!ofs) {
    throw std::runtime_error("Failed to open file: " + path);
  }
  ofs << text;
}

}  // namespace qcos
