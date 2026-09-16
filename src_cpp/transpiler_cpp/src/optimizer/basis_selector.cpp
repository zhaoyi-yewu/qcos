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

#include "optimizer/basis_selector.h"

#include <algorithm>

namespace qcos {

namespace basis_selector {

std::optional<std::string> choose_kak_gate(const std::set<std::string>& basis_gates) {
  // KAK gates in priority order
  const std::vector<std::string> kak_gates = {
      "cx", "cz", "iswap", "ecr", "rxx", "rzx"};

  for (const auto& gate : kak_gates) {
    if (basis_gates.count(gate) > 0) {
      return gate;
    }
  }

  return std::nullopt;
}

std::optional<std::string> choose_euler_basis(const std::set<std::string>& basis_gates) {
  // Euler basis configurations: name -> required gates
  const std::vector<std::pair<std::string, std::vector<std::string>>> euler_bases = {
      {"ZYZ", {"rz", "ry"}},
      {"ZXZ", {"rz", "rx"}},
      {"XYX", {"rx", "ry"}},
      {"U3", {"u3"}},
      {"U", {"u"}},
      {"PSX", {"p", "sx"}},
      {"ZSX", {"rz", "sx"}},
      {"RR", {"r"}},
  };

  for (const auto& [name, required] : euler_bases) {
    bool all_present = true;
    for (const auto& gate : required) {
      if (basis_gates.count(gate) == 0) {
        all_present = false;
        break;
      }
    }
    if (all_present) {
      return name;
    }
  }

  return std::nullopt;
}

std::vector<std::string> find_matching_bases(
    const std::set<std::string>& basis_gates,
    const std::map<std::string, std::vector<std::string>>& basis_dict) {

  std::vector<std::string> result;

  for (const auto& [name, required] : basis_dict) {
    bool all_present = true;
    for (const auto& gate : required) {
      if (basis_gates.count(gate) == 0) {
        all_present = false;
        break;
      }
    }
    if (all_present) {
      result.push_back(name);
    }
  }

  return result;
}

bool has_euler_basis(const std::set<std::string>& basis_gates,
                     const std::string& euler_basis) {

  const std::map<std::string, std::vector<std::string>> euler_requirements = {
      {"ZYZ", {"rz", "ry"}},
      {"ZXZ", {"rz", "rx"}},
      {"XYX", {"rx", "ry"}},
      {"U3", {"u3"}},
      {"U", {"u"}},
      {"PSX", {"p", "sx"}},
      {"ZSX", {"rz", "sx"}},
      {"RR", {"r"}},
  };

  auto it = euler_requirements.find(euler_basis);
  if (it == euler_requirements.end()) {
    return false;
  }

  for (const auto& gate : it->second) {
    if (basis_gates.count(gate) == 0) {
      return false;
    }
  }

  return true;
}

}  // namespace basis_selector

}  // namespace qcos
