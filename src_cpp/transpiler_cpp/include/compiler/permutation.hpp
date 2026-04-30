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

#pragma once

#include <cstddef>
#include <functional>
#include <map>

#include "compiler/definitions.hpp"
#include "compiler/operations/control.hpp"

namespace qc {
class Permutation : public std::map<QBit, QBit> {
 public:
  [[nodiscard]] inline Controls apply(const Controls& controls) const {
    if (empty()) {
      return controls;
    }
    Controls c{};
    for (const auto& control : controls) {
      c.emplace(at(control.qubit), control.type);
    }
    return c;
  }
  [[nodiscard]] inline Targets apply(const Targets& targets) const {
    if (empty()) {
      return targets;
    }
    Targets t{};
    for (const auto& target : targets) {
      t.emplace_back(at(target));
    }
    return t;
  }
};
}  // namespace qc

// define hash function for Permutation
namespace std {
template <>
struct hash<qc::Permutation> {
  std::size_t operator()(const qc::Permutation& p) const {
    std::size_t seed = 0;
    for (const auto& [k, v] : p) {
      qc::hashCombine(seed, k);
      qc::hashCombine(seed, v);
    }
    return seed;
  }
};
}  // namespace std
