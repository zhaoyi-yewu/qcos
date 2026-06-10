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

#include "optimizer/template.h"

namespace qcos {

/**
 * @class CliffordRzOptimization
 */
class CliffordRzOptimization {
 public:
  /**
   * @brief 构造优化 pass
   * @param verbose 为 true 时打印逐步优化信息
   */
  explicit CliffordRzOptimization(bool verbose = false);

  /**
   * @brief 执行 Hadamard 模板优化
   * @param dag 待优化的 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 优化掉的门数量
   */
  int reduce_hadamard_gates(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

  /**
   * @brief 返回节点在指定量子位上的直接后继门节点
   * @param dag 目标 DAG
   * @param cur_node 当前节点
   * @param qubit 指定量子位
   * @return DAGOpNode* 指定量子位上的后继门节点；不存在时返回空指针
   */
  DAGOpNode* get_next_node_on_specific_qubit(DAGCircuit& dag,
                                             DAGOpNode* cur_node,
                                             int qubit) const;

  /**
   * @brief 使用交换规则合并 Rz 门
   * @param dag 待优化的 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 删除的门数量
   */
  int cancel_single_qubit_gates(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

  /**
   * @brief 使用交换规则优化 CNOT 门
   * @param dag 待优化的 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 删除的门数量
   */
  int cancel_two_qubit_gates(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

  /**
   * @brief 使用相位多项式方法合并 Rz 门
   * @param dag 待优化的 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 删除的门数量
   */
  int merge_rotations(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

  /**
   * @brief 执行完整的 Clifford + Rz 优化流程
   * @param dag 待优化的 DAG
   * @param basis_gates 可选 basis gate 过滤集合
   * @return DAGCircuit& 优化后的 DAG
   */
  DAGCircuit& run(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

 private:
  using MethodPtr = int (CliffordRzOptimization::*)(
      DAGCircuit&, const std::optional<std::set<std::string>>&);

  std::unordered_map<int, std::pair<const char*, MethodPtr>> step_methods_ = {
      {1,
       {"reduce_hadamard_gates",
        &CliffordRzOptimization::reduce_hadamard_gates}},
      {2,
       {"cancel_single_qubit_gates",
        &CliffordRzOptimization::cancel_single_qubit_gates}},
      {3,
       {"cancel_two_qubit_gates",
        &CliffordRzOptimization::cancel_two_qubit_gates}},
      {4,
       {"merge_rotations",
        &CliffordRzOptimization::merge_rotations}}};

  /// 优化步骤执行顺序
  std::vector<int> routine_ = {1, 2, 3, 4};

  /**
   * @brief 使用相位多项式解析 CNOT-Rz 子电路，合并相同单项式的 Rz 门
   * @param node_list 子电路节点列表（仅含 cx、rz、x 门）
   * @param dag 所属 DAG，用于删除节点
   * @return int 删除的 Rz 门数量
   */
  int parse_cnot_rz_circuit(const std::vector<DAGOpNode*>& node_list,
                            DAGCircuit& dag);

  std::vector<OptimizingTemplate> hadamard_templates_;
  std::vector<OptimizingTemplate> single_qubit_gate_templates_;
  std::vector<OptimizingTemplate> cnot_ctrl_template_;
  std::vector<OptimizingTemplate> cnot_targ_template_;
  bool verbose_;
};

}  // namespace qcos