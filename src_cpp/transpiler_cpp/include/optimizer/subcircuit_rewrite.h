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
#include <vector>

#include "circuit/dag_circuit.h"
#include "optimizer/optimization_pass.h"

namespace qcos {

/**
 * @class EquivalencePass
 * @brief 基于固定等价模板执行子线路重写
 */
class EquivalencePass : public OptimizationPass {
 public:
  /**
   * @brief 构造等价模板重写 pass
   */
  explicit EquivalencePass(bool verbose = false);

  /**
   * @brief 在 DAG 上执行等价模板重写
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 被删除的门数量
   */
  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;

  std::string name() const override { return "EquivalencePass"; }

 private:
  /**
   * @brief 执行所有可用的等价模板替换
   * @param dag 待优化的量子线路 DAG
   * @param enabled_templates 允许执行的模板名称集合
   * @return int 被删除的门数量
   */
  int replace_equivalence_circuits(
      DAGCircuit& dag, const std::set<std::string>& enabled_templates) const;

  /**
   * @brief 根据 basis gate 过滤可用模板
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return std::set<std::string> 可执行的模板名称集合
   */
  std::set<std::string> get_equivalence_circuits(
      const DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates) const;

  bool verbose_;
};

}  // namespace qcos
