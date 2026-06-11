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

#include "optimizer/gate_optimizer.h"

#include <functional>
#include <stdexcept>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "optimizer/adjacent_optimization.h"
#include "optimizer/clifford_rz_optimization.h"
#include "optimizer/inverse_cancellation.h"
#include "optimizer/subcircuit_rewrite.h"

namespace qcos {

std::vector<std::shared_ptr<BaseOperation>> optimize(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level,
    bool verbose, const std::optional<std::set<std::string>>& basis_gates) {
  if (opt_level == 0) {
    return ir;
  }
  if (opt_level < 0 || opt_level > 3) {
    throw std::runtime_error("Unsupported optimization level: " +
                             std::to_string(opt_level));
  }

  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

  // 构造各优化 pass
  InverseCancellation inverse_optimizer({
      InverseCancellation::InverseGateRule(H({0})),
      InverseCancellation::InverseGateRule(CX({0, 1})),
      InverseCancellation::InverseGateRule(S({0}), SDG({0})),
      InverseCancellation::InverseGateRule(T({0}), TDG({0})),
      InverseCancellation::InverseGateRule(X({0})),
      InverseCancellation::InverseGateRule(Y({0})),
      InverseCancellation::InverseGateRule(Z({0})),
      InverseCancellation::InverseGateRule(SWAP({0, 1})),
      InverseCancellation::InverseGateRule(CZ({0, 1})),
      InverseCancellation::InverseGateRule(CCX({0, 1, 2})),
  });

  AdjacentPhaseOptPass adjacent_phase_optimizer;
  EquivalencePass equivalence_optimizer;
  CliffordRzOptimization commutative_optimizer(verbose);

  using PassFn = std::function<void(DAGCircuit&)>;
  std::vector<PassFn> _opt;

  _opt.push_back(
      [&](DAGCircuit& dag) { inverse_optimizer.run(dag, basis_gates); });
  _opt.push_back([&](DAGCircuit& dag) {
    adjacent_phase_optimizer.run(dag, basis_gates);
  });
  if (opt_level >= 2) {
    _opt.push_back(
        [&](DAGCircuit& dag) { equivalence_optimizer.run(dag, basis_gates); });
  }
  if (opt_level >= 3) {
    _opt.push_back(
        [&](DAGCircuit& dag) { commutative_optimizer.run(dag, basis_gates); });
  }

  // 迭代执行 pass 列表直到不再缩减
  while (true) {
    int init_size = dag.size();
    for (auto& pass_fn : _opt) {
      pass_fn(dag);
    }
    int new_size = dag.size();
    if (new_size >= init_size) break;
  }

  // 将 DAG 转回 IR
  std::vector<std::shared_ptr<BaseOperation>> result;
  for (auto* node : dag.topological_op_nodes()) {
    result.push_back(node->op);
  }
  return result;
}

}  // namespace qcos
