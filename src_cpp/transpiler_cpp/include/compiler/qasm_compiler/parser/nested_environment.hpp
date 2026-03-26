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

#include <map>
#include <optional>
#include <string>
#include <vector>

template <typename T>
class NestedEnvironment {
 private:
  std::vector<std::map<std::string, T>> env{};

 public:
  NestedEnvironment() { env.push_back({}); };

  void push() { env.push_back({}); }

  void pop() { env.pop_back(); }

  std::optional<T> find(std::string key) {
    for (auto it = env.rbegin(); it != env.rend(); ++it) {
      auto found = it->find(key);
      if (found != it->end()) {
        return found->second;
      }
    }
    return std::nullopt;
  }

  void emplace(std::string key, T value) { env.back().emplace(key, value); }
};
