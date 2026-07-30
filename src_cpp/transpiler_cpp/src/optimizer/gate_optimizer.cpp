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

#include <algorithm>
#include <stdexcept>
#include <thread>
#include <unordered_map>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/dag_node.h"
#include "circuit/gate_operation.h"
#include "optimizer/adjacent_optimization.h"
#include "optimizer/clifford_rz_optimization.h"
#include "optimizer/inverse_cancellation.h"
#include "optimizer/subcircuit_rewrite.h"
#include "optimizer/unitary_synthesis.h"

namespace qcos {

namespace {

/**
 * @brief 计算实际并行线程数
 *
 * 根据用户请求、电路规模和优化级别综合确定：
 * - 0=自动（取硬件并发数），1=串行，>1=指定
 * - 按电路规模限制：每线程至少 N 个 ops（Level 1/2: 30000, Level 3: 10000）
 * - 上限统一取系统硬件线程数
 * - 小电路自然退化为串行
 *
 * @param num_threads 用户请求的线程数（0=自动）
 * @param ir_size 电路操作数
 * @param opt_level 优化级别 (1-3)
 * @return 实际可用线程数（1 表示应走串行路径）
 */
size_t compute_parallel_threads(size_t num_threads, size_t ir_size,
                                int opt_level) {
  size_t requested_threads = num_threads;
  if (requested_threads == 0)
    requested_threads = std::max(1u, std::thread::hardware_concurrency());

  // Level 1/2: 每线程至少 30000 ops
  // Level 3:   每线程至少 10000 ops
  // 上限统一取系统线程数
  size_t max_threads_by_ops;
  size_t thread_limit =
      std::max(1u, std::thread::hardware_concurrency());
  if (opt_level >= 3) {
    max_threads_by_ops = ir_size / 10000;
  } else {
    max_threads_by_ops = ir_size / 30000;
  }
  if (max_threads_by_ops < 1) max_threads_by_ops = 1;
  return std::min({requested_threads, max_threads_by_ops, thread_limit});
}

/**
 * @brief 对 IR 执行优化：ir_to_dag → 优化 pass 列表 → 返回优化后的 ops
 *
 * @param ir 待优化的操作序列
 * @param opt_level 优化级别 (1-3)
 * @param verbose 是否打印优化详情
 * @param basis_gates 可选 basis gate 过滤集合
 * @return 优化后的操作序列
 */
std::vector<std::shared_ptr<BaseOperation>> optimize_ir(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level,
    bool verbose, const std::optional<std::set<std::string>>& basis_gates,
    bool fast_mode) {
  DAGCircuit dag = DAGCircuit::ir_to_dag(ir);

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
  UnitarySynthesis unitary_synth(basis_gates);

  using PassFn = std::function<void(DAGCircuit&)>;
  std::vector<PassFn> passes;

  passes.push_back(
      [&](DAGCircuit& dag) { inverse_optimizer.run(dag, basis_gates); });
  passes.push_back([&](DAGCircuit& dag) {
    adjacent_phase_optimizer.run(dag, basis_gates);
  });
  if (opt_level >= 2) {
    passes.push_back(
        [&](DAGCircuit& dag) { equivalence_optimizer.run(dag, basis_gates); });
    passes.push_back(
        [&](DAGCircuit& dag) { unitary_synth.run(dag, basis_gates); });
  }
  if (opt_level >= 3) {
    passes.push_back(
        [&](DAGCircuit& dag) { commutative_optimizer.run(dag, basis_gates); });
  }

  // 若基础门集为u,rz，那么只执行 UnitarySynthesis
  if (basis_gates.has_value() &&
      (basis_gates.value() == std::set<std::string>{"u", "cz"} ||
       basis_gates.value() == std::set<std::string>{"u3", "cz"})) {
    passes.clear();
    passes.push_back(
        [&](DAGCircuit& dag) { unitary_synth.run(dag, basis_gates); });
  }


  while (true) {
    int init_size = dag.size();
    for (auto& pass_fn : passes) {
      pass_fn(dag);
    }
    // fast_mode：只执行一轮 pass
    if (fast_mode || dag.size() >= init_size) break;
  }

  std::vector<std::shared_ptr<BaseOperation>> result;
  result.reserve(dag.size());
  for (auto* node : dag.topological_op_nodes()) {
    result.push_back(node->op);
  }
  return result;
}

}  // namespace

std::vector<int> ir_layers(
    const std::vector<std::shared_ptr<BaseOperation>>& ir) {
  std::unordered_map<int, int> qubit_last_layer;
  std::vector<int> op_layer(ir.size(), 0);
  for (size_t op_idx = 0; op_idx < ir.size(); ++op_idx) {
    int layer = 0;
    for (int qubit : ir[op_idx]->targets) {
      auto iter = qubit_last_layer.find(qubit);
      if (iter != qubit_last_layer.end()) {
        layer = std::max(layer, iter->second);
      }
    }
    ++layer;
    op_layer[op_idx] = layer;
    for (int qubit : ir[op_idx]->targets) {
      qubit_last_layer[qubit] = layer;
    }
  }
  return op_layer;
}

std::vector<std::vector<std::shared_ptr<BaseOperation>>> split_ir_by_layers(
    const std::vector<std::shared_ptr<BaseOperation>>& ir,
    const std::vector<int>& op_layers, int num_chunks) {
  if (op_layers.empty() || num_chunks <= 1) {
    return {ir};
  }
  int max_layer = *std::max_element(op_layers.begin(), op_layers.end());
  // 向上取整：确保所有层都能被分配
  int layers_per_chunk = (max_layer + num_chunks - 1) / num_chunks;

  std::vector<std::vector<std::shared_ptr<BaseOperation>>> segments(
      num_chunks);
  for (size_t op_idx = 0; op_idx < ir.size(); ++op_idx) {
    int chunk_idx = (op_layers[op_idx] - 1) / layers_per_chunk;
    if (chunk_idx >= num_chunks) chunk_idx = num_chunks - 1;
    segments[chunk_idx].push_back(ir[op_idx]);
  }

  // 移除空段
  std::vector<std::vector<std::shared_ptr<BaseOperation>>> result;
  result.reserve(num_chunks);
  for (auto& seg : segments) {
    if (!seg.empty()) {
      result.push_back(std::move(seg));
    }
  }
  return result;
}

std::vector<std::shared_ptr<BaseOperation>> optimize(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level,
    bool verbose, const std::optional<std::set<std::string>>& basis_gates,
    size_t num_threads, bool fast_mode) {
  if (opt_level == 0) {
    return ir;
  }
  if (opt_level < 0 || opt_level > 3) {
    throw std::runtime_error("Unsupported optimization level: " +
                             std::to_string(opt_level));
  }

  // 提取 measure, 优化完成后追加到末尾
  std::vector<std::shared_ptr<BaseOperation>> regular_ops;
  std::vector<std::shared_ptr<BaseOperation>> measures;
  regular_ops.reserve(ir.size());
  for (const auto& op : ir) {
    if (op->name == "measure") {
      measures.push_back(op);
    } else {
      regular_ops.push_back(op);
    }
  }

  size_t N =
      compute_parallel_threads(num_threads, regular_ops.size(), opt_level);

  std::vector<std::shared_ptr<BaseOperation>> optimized;
  if (N <= 1) {
    optimized =
        optimize_ir(regular_ops, opt_level, verbose, basis_gates, fast_mode);
  } else {
    // 并行：从 IR 按层拆分 → 各线程 optimize_ir → 合并
    auto op_layers = ir_layers(regular_ops);
    auto segments =
        split_ir_by_layers(regular_ops, op_layers, static_cast<int>(N));

    // 每个线程的优化结果，各线程写各自索引，无竞争
    std::vector<std::vector<std::shared_ptr<BaseOperation>>> opt_segments(
        segments.size());

    std::vector<std::thread> threads;
    threads.reserve(segments.size());
    for (size_t seg_idx = 0; seg_idx < segments.size(); ++seg_idx) {
      threads.emplace_back([&segments, &opt_segments, seg_idx, opt_level,
                            verbose, &basis_gates, fast_mode]() {
        opt_segments[seg_idx] = optimize_ir(segments[seg_idx], opt_level,
                                            verbose, basis_gates, fast_mode);
      });
    }
    for (auto& worker : threads) {
      worker.join();
    }

    // 合并所有段的 ops（按拓扑序拼接）
    size_t total_size = 0;
    for (const auto& seg : opt_segments) {
      total_size += seg.size();
    }
    optimized.reserve(total_size);
    for (auto& seg : opt_segments) {
      optimized.insert(optimized.end(), std::make_move_iterator(seg.begin()),
                       std::make_move_iterator(seg.end()));
    }
  }

  // 追加 measure 到末尾
  optimized.insert(optimized.end(), measures.begin(), measures.end());
  return optimized;
}

}  // namespace qcos
