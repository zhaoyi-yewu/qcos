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

#include "utils/load_files.h"

#include <cmath>
#include <fstream>
#include <iostream>
#include <regex>
#include <string>
#include <vector>

namespace qcos {

std::vector<std::pair<int, int>> load_config_file(
    const std::string& filename) {
  std::vector<std::pair<int, int>> coupling_list;
  std::ifstream file(filename);

  if (!file.is_open()) {
    std::cerr << "无法打开文件: " << filename << std::endl;
    return coupling_list;
  }

  std::regex coupler_regex(
      R"(coupler_map\.[A-Za-z0-9_]+\s*=\s*\[\s*['"]Q([0-9]+)['"]\s*,\s*['"]Q([0-9]+)['"]\s*\])");

  std::string line;
  while (std::getline(file, line)) {
    if (line.empty() || line[0] == '#') continue;

    std::smatch match;
    if (std::regex_search(line, match, coupler_regex)) {
      if (match.size() == 3) {
        try {
          int p0 = std::stoi(match[1].str());
          int p1 = std::stoi(match[2].str());
          coupling_list.emplace_back(p0, p1);
        } catch (...) {
          continue;
        }
      }
    }
  }
  file.close();
  return coupling_list;
}

double parse_qasm_param(const std::string& s) {
  if (s.empty()) return 0.0;

  if (s.find("pi") != std::string::npos) {
    double pi_val = M_PI;
    double sign = (s.find('-') != std::string::npos) ? -1.0 : 1.0;

    // parse pi/2, pi/4...
    size_t slash_pos = s.find('/');
    if (slash_pos != std::string::npos) {
      try {
        double denominator = std::stod(s.substr(slash_pos + 1));
        return sign * pi_val / denominator;
      } catch (...) {
        return sign * pi_val;
      }
    }
    return sign * pi_val;
  }

  // pure number
  try {
    return std::stod(s);
  } catch (...) {
    return 0.0;
  }
}

std::vector<GateOperation> load_qasm_to_gate_list(
    const std::string& filename) {
  std::vector<GateOperation> gate_list;
  std::ifstream file(filename);

  if (!file.is_open()) {
    std::cerr << "无法打开 QASM 文件: " << filename << std::endl;
    return gate_list;
  }

  static const std::regex single_gate_regex(
      R"(^([a-z0-9]+)\s*(?:\(([^)]*)\))?\s+q\[([0-9]+)\];)",
      std::regex_constants::optimize);
  static const std::regex double_gate_regex(
      R"(^([a-z0-9]+)\s+q\[([0-9]+)\],\s*q\[([0-9]+)\];)",
      std::regex_constants::optimize);

  std::string line;
  while (std::getline(file, line)) {
    line.erase(0, line.find_first_not_of(" \t\r\n"));
    auto last = line.find_last_not_of(" \t\r\n");
    if (last != std::string::npos) line.erase(last + 1);

    if (line.empty() || line.find("OPENQASM") == 0 ||
        line.find("include") == 0 || line.find("qreg") == 0 ||
        line.find("creg") == 0 || line.find("//") == 0) {
      continue;
    }

    std::smatch match;
    if (std::regex_search(line, match, double_gate_regex)) {
      gate_list.emplace_back(match[1].str(),
                             std::vector<int>{std::stoi(match[2].str()),
                                              std::stoi(match[3].str())},
                             std::vector<double>{},
                             OperationType::DOUBLE_QUBIT_OPERATION);
    } else if (std::regex_search(line, match, single_gate_regex)) {
      std::string name = match[1].str();
      std::vector<double> params;
      if (match[2].matched && !match[2].str().empty()) {
        params.push_back(parse_qasm_param(match[2].str()));
      }
      int q0 = std::stoi(match[3].str());
      gate_list.emplace_back(name, std::vector<int>{q0}, params,
                             OperationType::SINGLE_QUBIT_OPERATION);
    }
  }
  file.close();
  return gate_list;
}

}  // namespace qcos
