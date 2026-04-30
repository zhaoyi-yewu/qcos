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

#include "compiler/qasm_to_origin_ir.hpp"

std::string qasmfile2str(const std::string& filename) {
  std::stringstream ss;
  std::ifstream ifs;
  ifs.open(filename);
  if (ifs.is_open()) {
    std::string line;
    std::cout << "### opened qasm file:" << filename << std::endl;
    while (std::getline(ifs, line)) {
      ss << line;
    }
    ifs.close();
  } else {
    std::cerr << "###Error: qasmfile2str open " << filename << "failed."
              << std::endl;
    exit(-1);
    return {};
  }
  return ss.str();
}

std::string convert_qasm_to_originir(std::string qasm_filepath) {
  return QuantumComputation::fromQASM(qasmfile2str(qasm_filepath))
      .toOriginIR();
}
std::string convert_qasm_string_to_originir(std::string qasm_str) {
  return QuantumComputation::fromQASM(qasm_str).toOriginIR();
}
std::vector<std::unique_ptr<Operation>> convert_qasm_string_to_operations(
    std::string qasm_str) {
  auto qc = QuantumComputation::fromQASM(qasm_str);
  auto& ops_ref = qc.getOps();

  std::vector<std::unique_ptr<Operation>> result;
  result.reserve(ops_ref.size());

  // 移动元素到新vector
  for (auto& op : ops_ref) {
    result.push_back(std::move(op));
  }

  return result;
}
