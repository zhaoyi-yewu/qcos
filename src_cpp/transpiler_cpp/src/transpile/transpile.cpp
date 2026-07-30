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

#include "transpile/transpile.h"

#include <chrono>
#include <memory>
#include <set>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"
#include "compiler/qasm_to_ir.hpp"
#include "decomposer/decomposer.h"
#include "mapping/na_mapping.h"
#include "mapping/sabre_routing.h"
#include "optimizer/gate_optimizer.h"

namespace qcos {

// 跳过分解的门名集合：这些操作不属于量子门，直接透传
static const std::unordered_set<std::string> kSkipDecomposeNames = {
    "measure", "sync", "reset", "barrier"};

std::vector<std::shared_ptr<BaseOperation>> decompose_gates_to_1q2q(
    const std::vector<std::shared_ptr<BaseOperation>>& ir) {
  std::vector<std::shared_ptr<BaseOperation>> result;
  result.reserve(ir.size());

  for (const auto& op : ir) {
    if (kSkipDecomposeNames.count(op->name)) {
      // 非门操作（measure/sync/reset/barrier）直接克隆透传
      result.push_back(op->clone());
    } else {
      // 尝试转为 GateOperation 以调用 decompose_to_1q2q
      auto* gate = dynamic_cast<GateOperation*>(op.get());
      if (gate) {
        auto decomposed = gate->decompose_to_1q2q();
        for (auto& d : decomposed) {
          result.push_back(std::move(d));
        }
      } else {
        // 非 GateOperation 类型，直接克隆透传
        result.push_back(op->clone());
      }
    }
  }
  return result;
}

std::vector<std::string> collect_gate_names(
    const std::vector<std::shared_ptr<BaseOperation>>& ops) {
  std::set<std::string> name_set;
  for (const auto& op : ops) {
    name_set.insert(op->name);
  }
  return std::vector<std::string>(name_set.begin(), name_set.end());
}

TranspileResult transpile(
    const std::string& qasm_string,
    const std::vector<std::string>& supp_basis_gates,
    const std::vector<std::pair<int, int>>& coupling_list, int opt_level,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities) {
  using clock = std::chrono::high_resolution_clock;

  TranspileResult result;
  TranspileTimings& t = result.timings;

  auto total_start = clock::now();

  // Step 1: Parse — QASM 字符串解析为操作列表
  auto parse_start = clock::now();
  auto [ops, num_qubits] = qasm_to_ir(qasm_string);
  result.num_qubits = num_qubits;
  t.parse_time =
      std::chrono::duration<double>(clock::now() - parse_start).count();

  // Step 2: Optimize #1 — 映射前轻量优化（opt_level 上限为 1）
  auto opt1_start = clock::now();
  std::set<std::string> basis_set(supp_basis_gates.begin(),
                                  supp_basis_gates.end());
  auto optimized_ops =
      optimize(ops, std::min(1, opt_level), false, basis_set, 0);
  t.opt_time1 =
      std::chrono::duration<double>(clock::now() - opt1_start).count();

  // Step 3: Decompose to 1q2q — 将多量子比特门分解为 1q/2q 门
  auto decomp_start = clock::now();
  auto decomposed_ops = decompose_gates_to_1q2q(optimized_ops);
  t.decompose_1q2q_time =
      std::chrono::duration<double>(clock::now() - decomp_start).count();

  // Step 4: Get decompose rules — 根据基础门集合生成分解规则表
  auto rule_start = clock::now();
  auto gate_names = collect_gate_names(decomposed_ops);
  Decomposer decomposer;
  auto [decompose_table, usage_stats] =
      decomposer.get_decompose_rules(gate_names, supp_basis_gates);
  t.decompose_rule_time =
      std::chrono::duration<double>(clock::now() - rule_start).count();

  // Step 5: SABRE routing — 逻辑比特到物理比特的映射与路由
  auto map_start = clock::now();
  auto routed_ops = sabre_routing(decomposed_ops, coupling_list,
                                  edge_fidelities, single_qubit_fidelities);
  t.mapping_time =
      std::chrono::duration<double>(clock::now() - map_start).count();

  // Step 6: Apply decompose rules — 将路由后的门按规则替换为基础门
  auto apply_start = clock::now();
  auto decomposed_circuit =
      decomposer.apply_decompose_rules(routed_ops, decompose_table);
  t.decompose_apply_time =
      std::chrono::duration<double>(clock::now() - apply_start).count();

  // Step 7: Optimize #2 — 路由后全量优化（完整 opt_level + basis_gates 过滤）
  auto opt2_start = clock::now();
  result.basis_gate_list =
      optimize(decomposed_circuit, opt_level, false, basis_set, 0);
  t.opt_time2 =
      std::chrono::duration<double>(clock::now() - opt2_start).count();

  // 汇总计时
  t.total_time =
      std::chrono::duration<double>(clock::now() - total_start).count();
  t.decomposed_time =
      t.decompose_rule_time + t.decompose_1q2q_time + t.decompose_apply_time;
  t.transpile_time =
      t.opt_time1 + t.decomposed_time + t.mapping_time + t.opt_time2;

  // 所有计算步骤完成，集中清空中间变量
  decomposed_circuit = {};
  routed_ops = {};
  decomposed_ops = {};
  optimized_ops = {};
  ops = {};
  return result;
}

TranspileResult transpile_na(const std::string& qasm_string,
                             const std::vector<std::string>& supp_basis_gates,
                             const NAQpuConfig& qpu_config, int opt_level) {
  using clock = std::chrono::high_resolution_clock;

  TranspileResult result;
  TranspileTimings& t = result.timings;

  auto total_start = clock::now();

  // Step 1: Parse — parse the QASM string into an operation list.
  auto parse_start = clock::now();
  auto [ops, num_qubits] = qasm_to_ir(qasm_string);
  result.num_qubits = num_qubits;
  t.parse_time =
      std::chrono::duration<double>(clock::now() - parse_start).count();

  // Step 2: Optimize #1 — lightweight pre-mapping optimization (opt_level capped at 1).
  auto opt1_start = clock::now();
  std::set<std::string> basis_set(supp_basis_gates.begin(),
                                  supp_basis_gates.end());
  auto optimized_ops =
      optimize(ops, std::min(1, opt_level), false, basis_set, 0);
  t.opt_time1 =
      std::chrono::duration<double>(clock::now() - opt1_start).count();

  // Step 3: Decompose to 1q2q — break multi-qubit gates into 1q/2q gates.
  auto decomp_start = clock::now();
  auto decomposed_ops = decompose_gates_to_1q2q(optimized_ops);
  t.decompose_1q2q_time =
      std::chrono::duration<double>(clock::now() - decomp_start).count();

  // Step 4: Get decompose rules — build the decomposition rule table from the basis gates.
  auto rule_start = clock::now();
  auto gate_names = collect_gate_names(decomposed_ops);
  Decomposer decomposer;
  auto [decompose_table, usage_stats] =
      decomposer.get_decompose_rules(gate_names, supp_basis_gates);
  t.decompose_rule_time =
      std::chrono::duration<double>(clock::now() - rule_start).count();

  // Step 5: NA mapping — NARoute maps logical to physical qubits and inserts MOVE.
  auto map_start = clock::now();
  NARoute router;
  router.prepare_data(num_qubits, decomposed_ops, qpu_config);
  auto [routed_ops, layout] = router.execute_with_order();
  t.mapping_time =
      std::chrono::duration<double>(clock::now() - map_start).count();

  // Step 6: Apply decompose rules — replace routed gates with basis gates per the rules.
  auto apply_start = clock::now();
  auto decomposed_circuit =
      decomposer.apply_decompose_rules(routed_ops, decompose_table);
  t.decompose_apply_time =
      std::chrono::duration<double>(clock::now() - apply_start).count();

  // Step 7: Optimize #2 — full post-routing optimization (full opt_level + basis_gates filter).
  auto opt2_start = clock::now();
  result.basis_gate_list =
      optimize(decomposed_circuit, opt_level, false, basis_set, 0);
  t.opt_time2 =
      std::chrono::duration<double>(clock::now() - opt2_start).count();

  // Aggregate timings.
  t.total_time =
      std::chrono::duration<double>(clock::now() - total_start).count();
  t.decomposed_time = t.decompose_rule_time + t.decompose_1q2q_time +
                      t.decompose_apply_time;
  t.transpile_time = t.opt_time1 + t.decomposed_time + t.mapping_time +
                     t.opt_time2;

  return result;
}

}  // namespace qcos
