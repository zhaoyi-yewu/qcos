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
#include <unordered_map>
#include <vector>

#include "circuit/dag_circuit.h"

namespace qcos {

/**
 * @class OptimizingTemplate
 * @brief 保存模板 DAG、锚点和可选替换 DAG 的模板匹配对象
 */
class OptimizingTemplate {
 public:
  /**
   * @brief 使用模板 DAG、替换 DAG 和锚点信息构造匹配模板
   * @param template_dag 模板线路对应的 DAG
   * @param replacement_dag 可选的替换 DAG；可为空
   * @param anchor 模板比较时的锚点量子位编号
   * @param weight 优化减少的门数量
   */
  OptimizingTemplate(DAGCircuit template_dag,
                     std::optional<DAGCircuit> replacement_dag = std::nullopt,
                     int anchor = 0, int weight = 1);

  /**
   * @brief 从给定起点开始比较模板 DAG 与目标 DAG 是否匹配
   * @param dag 待匹配的目标 DAG
   * @param start_node 目标 DAG 中的起始门节点
   * @param anchor_qubit 目标 DAG 中与模板 anchor 对应的量子位
   * @return std::unordered_map<int, DAGOpNode*> 模板节点 id
   * 到目标节点的映射；不匹配时返回空映射
   */
  std::unordered_map<int, DAGOpNode*> compare(DAGCircuit& dag,
                                              DAGOpNode* start_node,
                                              int anchor_qubit) const;

  DAGCircuit template_dag_;
  std::optional<DAGCircuit> replacement_dag_;
  int anchor_;
  int weight_;
};

/**
 * @brief 生成 Rz 门交换优化模板集合
 * @return std::vector<OptimizingTemplate> 模板列表
 */
std::vector<OptimizingTemplate> generate_single_qubit_gate_templates();

/**
 * @brief 生成 Hadamard 门优化模板集合
 * @return std::vector<OptimizingTemplate> 模板列表
 */
std::vector<OptimizingTemplate> generate_hadamard_gate_templates();

/**
 * @brief 生成从控制比特开始的 CNOT 优化模板集合
 * @return std::vector<OptimizingTemplate> 模板列表
 */
std::vector<OptimizingTemplate> generate_cnot_ctrl_templates();

/**
 * @brief 生成从目标比特开始的 CNOT 优化模板集合
 * @return std::vector<OptimizingTemplate> 模板列表
 */
std::vector<OptimizingTemplate> generate_cnot_targ_templates();

/**
 * @brief 按 basis gate 过滤模板集合
 * @param templates 原始模板集合
 * @param basis_gates 允许保留的 basis gate 集合
 * @param ignore_replacement 为 true 时仅检查模板 DAG 本体
 * @return std::vector<const OptimizingTemplate*> 过滤后的模板视图
 */
std::vector<const OptimizingTemplate*> filter_templates_by_basis(
    const std::vector<OptimizingTemplate>& templates,
    const std::set<std::string>& basis_gates, bool ignore_replacement = true);

}  // namespace qcos