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

#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @class InverseCancellation
 * @brief 基于 collect_runs 的逆门对消除 pass
 */
class InverseCancellation {
 public:
  /**
   * @brief 描述可对消的单门或逆门对规则项
   */
  struct InverseGateRule {
    /**
     * @brief 构造自反门规则项
     * @param gate 需要成对消去的自反门
     */
    explicit InverseGateRule(GateOperation gate);

    /**
     * @brief 构造逆门对规则项
     * @param gate_0 第一类门
     * @param gate_1 第二类门，必须与 gate_0 互逆
     */
    InverseGateRule(GateOperation gate_0, GateOperation gate_1);

    /**
     * @brief 判断当前规则项是否描述一对互逆门
     * @return true 当前规则项包含 gate_1
     * @return false 当前规则项只描述单个自反门
     */
    bool is_pair() const { return gate_1.has_value(); }

    GateOperation gate_0;
    std::optional<GateOperation> gate_1;
  };

  /**
   * @brief 使用给定的可对消门规则构造 pass
   * @param gates_to_cancel 可对消门或门对规则项列表
   */
  explicit InverseCancellation(
      const std::vector<InverseGateRule>& gates_to_cancel);

  /**
   * @brief 在 DAG 上执行逆门对消
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 被删除的门数量
   */
  int run(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

 private:
  /**
   * @brief 判断一个门或一对门是否互为逆
   * @param gate_0 第一个门
   * @param gate_1 第二个门，为空时判断 gate_0 是否自反
   * @return true 可相互抵消
   * @return false 不可相互抵消
   */
  bool is_inverse(
      const GateOperation& gate_0,
      const std::optional<GateOperation>& gate_1 = std::nullopt) const;

  /**
   * @brief 对所有自反门运行成对消去逻辑
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @param topo_order 预计算的拓扑序节点 id 列表，避免重复计算
   * @return int 被删除的门数量
   */
  int run_on_self_inverse(
      DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates,
      const std::vector<int>& topo_order) const;

  /**
   * @brief 对所有显式逆门对运行消去逻辑
   * @param dag 待优化的量子线路 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @param topo_order 预计算的拓扑序节点 id 列表，避免重复计算
   * @return int 被删除的门数量
   */
  int run_on_inverse_pairs(
      DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates,
      const std::vector<int>& topo_order) const;

  std::vector<InverseGateRule> inverse_gate_pairs_;
  std::set<std::string> self_inverse_gate_names_;
  std::set<std::string> inverse_gate_pairs_names_;
};

}  // namespace qcos
