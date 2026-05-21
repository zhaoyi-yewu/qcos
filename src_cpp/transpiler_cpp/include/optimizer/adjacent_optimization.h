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

#include <optional>
#include <set>
#include <string>

#include "circuit/dag_circuit.h"

namespace qcos {

/**
 * @class AdjacentPhaseOptPass
 * @brief 合并相邻的相位门
 */
class AdjacentPhaseOptPass {
 public:
  /**
   * @brief 构造相邻相位门合并 pass
   */
  AdjacentPhaseOptPass();

  /**
   * @brief 在 DAG 上执行相邻相位门合并
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 被删除的门数量
   */
  int run(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

 private:
  std::set<std::string> phase_gates_;
};

}  // namespace qcos