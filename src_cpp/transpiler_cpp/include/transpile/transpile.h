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
#include <string>
#include <utility>
#include <vector>

#include "circuit/base_operation.h"
#include "mapping/na_mapping.h"

namespace qcos {

/**
 * @brief 转译过程中各阶段耗时记录
 *
 * 字段含义与 Python TranspileRuntime 对应。
 */
struct TranspileTimings {
  double parse_time = 0.0;
  double opt_time1 = 0.0;
  double decompose_1q2q_time = 0.0;
  double decompose_rule_time = 0.0;
  double mapping_time = 0.0;
  double decompose_apply_time = 0.0;
  double decomposed_time = 0.0;
  double opt_time2 = 0.0;
  double transpile_time = 0.0;
  double total_time = 0.0;
};

/**
 * @brief transpile 函数的返回结果
 *
 * 包含最终门列表、量子比特数和各阶段计时。
 */
struct TranspileResult {
  std::vector<std::shared_ptr<BaseOperation>> basis_gate_list;
  int num_qubits = 0;
  TranspileTimings timings;
};

/**
 * @brief 批量将门列表分解为 1q/2q 门
 *
 * 跳过 measure/sync/reset/barrier 等非门操作，对其余操作调用
 * decompose_to_1q2q() 进行分解。
 *
 * @param ir 输入操作列表
 * @return std::vector<std::shared_ptr<BaseOperation>> 分解后的操作列表
 */
std::vector<std::shared_ptr<BaseOperation>> decompose_gates_to_1q2q(
    const std::vector<std::shared_ptr<BaseOperation>>& ir);

/**
 * @brief 从操作列表中收集去重的门名集合
 *
 * @param ops 操作列表
 * @return std::vector<std::string> 去重后的门名列表
 */
std::vector<std::string> collect_gate_names(
    const std::vector<std::shared_ptr<BaseOperation>>& ops);

/**
 * @brief 一体化转译函数（sabre_routing 单电路路径）
 *
 * 将 parse + transpile 的完整流程合并为一次 C++ 调用，避免
 * Python/C++ 之间的中间数据传递开销。
 *
 * 内部流程：
 *   1. QASM 解析 → qasm_to_ir
 *   2. 优化 #1（opt_level 上限为 1）→ optimize
 *   3. 分解为 1q/2q 门 → decompose_gates_to_1q2q
 *   4. 生成分解规则 → Decomposer::get_decompose_rules
 *   5. SABRE 路由 → sabre_routing
 *   6. 应用分解规则 → Decomposer::apply_decompose_rules
 *   7. 优化 #2（完整 opt_level + basis_gates）→ optimize
 *
 * @param qasm_string QASM 电路字符串
 * @param supp_basis_gates 支持的基础门名列表
 * @param coupling_list 物理耦合图边列表（已规范化为 int 对）
 * @param opt_level 优化级别 (0-3)，默认 1
 * @param edge_fidelities 边保真度，与 coupling_list 对应，空表示不使用，默认空
 * @param single_qubit_fidelities 单比特保真度，按物理位 ID
 * 索引，空表示不使用，默认空
 * @param num_threads 优化阶段线程数：0=自动并行(取 hardware_concurrency)，
 * 1=串行，>1=指定。默认 0，透传给内部 optimize() 调用。
 * @param fast_mode 优化快速模式：true 只跑一轮 pass，透传给内部 optimize()
 * 调用。
 * @param fidelity_threshold 保真度阈值，<0 自适应计算 (mean - std, clamp [0.3,
 * 0.9])，
 * >=0 使用传入值，默认 -1
 * @param fidelity_weight DenseLayout 保真度权重，取值 [0, 1]，默认
 * 0.5（密度与保真度相同权重）
 * @return TranspileResult 包含最终门列表、量子比特数和各阶段计时
 */
TranspileResult transpile(
    const std::string& qasm_string,
    const std::vector<std::string>& supp_basis_gates,
    const std::vector<std::pair<int, int>>& coupling_list, int opt_level = 1,
    const std::vector<double>& edge_fidelities = {},
    const std::vector<double>& single_qubit_fidelities = {},
    size_t num_threads = 0, bool fast_mode = true,
    double fidelity_threshold = -1.0, double fidelity_weight = 0.5);

/**
 * @brief All-in-one transpile function (neutral-atom NA mapping, single
 * circuit).
 *
 * Same pipeline as transpile(sabre); only the routing stage is replaced by
 * NARoute, which inserts MOVE operations between the operate area and the
 * storage area so that two-qubit gates act on adjacent sites.
 *
 * Internal pipeline:
 *   1. QASM parse -> convert_qasm_string_to_qcos_operations
 *   2. Optimize #1 (opt_level capped at 1) -> optimize
 *   3. Decompose into 1q/2q gates -> decompose_gates_to_1q2q
 *   4. Build decompose rules -> Decomposer::get_decompose_rules
 *   5. NA mapping -> NARoute.prepare_data + execute_with_order
 *   6. Apply decompose rules -> Decomposer::apply_decompose_rules
 *   7. Optimize #2 (full opt_level + basis_gates) -> optimize
 *
 * @param qasm_string QASM circuit string.
 * @param supp_basis_gates Supported basis-gate name list.
 * @param qpu_config Neutral-atom QPU topology configuration.
 * @param opt_level Optimization level (0-3); defaults to 1.
 * @return TranspileResult containing the final gate list, qubit count, and
 *         per-stage timings.
 */
TranspileResult transpile_na(const std::string& qasm_string,
                             const std::vector<std::string>& supp_basis_gates,
                             const NAQpuConfig& qpu_config, int opt_level = 1);

}  // namespace qcos
