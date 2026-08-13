/*
 * Copyright header - see existing files for full text
 */

#include "optimizer/phase_polynomial_merging.h"

#include <algorithm>
#include <cmath>
#include <unordered_map>
#include <vector>

#include "optimizer/collect_block.h"

namespace qcos {

PhasePolynomialMerging::PhasePolynomialMerging(bool verbose)
    : verbose_(verbose) {}

int PhasePolynomialMerging::run(
    DAGCircuit& dag, const std::optional<std::set<std::string>>& basis_gates) {
  const auto op_counts = dag.count_ops();
  auto rz_it = op_counts.find("rz");
  if (rz_it == op_counts.end() || rz_it->second <= 1) {
    return 0;
  }

  std::set<std::string> collect_gates = {"cx", "rz", "x"};
  auto blocks = collect_all_matching_blocks(dag, collect_gates);

  int reduced = 0;
  for (auto& block : blocks) {
    reduced += parse_cnot_rz_circuit(block, dag);
  }

  if (verbose_) {
    std::clog << name() << ": " << reduced << " gates reduced\n";
  }
  return reduced;
}

int PhasePolynomialMerging::parse_cnot_rz_circuit(
    const std::vector<DAGOpNode*>& node_list, DAGCircuit& dag) {
  // 相位多项式: 单项式 -> 累加相位
  std::unordered_map<int, double> phases;
  // 每个单项式的第一个 Rz 门: 单项式 -> (节点, 符号)
  std::unordered_map<int, std::pair<DAGOpNode*, int>> first_rz;
  // 每个量子位当前的线性函数
  std::unordered_map<int, int> cur_phases;
  // 待删除的重复 Rz 节点
  std::vector<DAGOpNode*> to_remove;
  int cnt = 0;

  for (DAGOpNode* node : node_list) {
    if (node->flag == -1) continue;

    // 初始化量子位的线性函数
    for (int qubit : node->qargs) {
      if (cur_phases.find(qubit) == cur_phases.end()) {
        cur_phases[qubit] = 1 << (qubit + 1);
      }
    }

    if (node->name() == "cx") {
      int control = node->qargs[0];
      int target = node->qargs[1];
      cur_phases[target] ^= cur_phases[control];
    } else if (node->name() == "x") {
      int qubit = node->qargs[0];
      // 翻转常数项
      cur_phases[qubit] ^= 1;
    } else if (node->name() == "rz") {
      int qubit_phase = cur_phases[node->qargs[0]];
      int sign = (qubit_phase & 1) ? -1 : 1;
      int mono = qubit_phase >> 1;
      double angle =
          node->op->arg_value.empty() ? 0.0 : node->op->arg_value[0];

      phases[mono] = sign * angle + (phases.count(mono) ? phases[mono] : 0.0);

      if (first_rz.find(mono) == first_rz.end()) {
        first_rz[mono] = {node, sign};
      } else {
        // 同一单项式已有 Rz 门，合并角度后删除当前节点
        to_remove.push_back(node);
      }
    }
  }

  // 更新或删除每个单项式的第一个 Rz 门
  for (auto& [mono, pack] : first_rz) {
    DAGOpNode* node = pack.first;
    int sign = pack.second;
    if (node->flag == -1) continue;

    if (std::abs(phases[mono]) <= 1e-8) {
      dag.remove_op_node(node);
      ++cnt;
    } else {
      node->op->arg_value = {sign * phases[mono]};
    }
  }

  // 删除重复的 Rz 门
  for (DAGOpNode* node : to_remove) {
    if (node->flag == -1) continue;
    dag.remove_op_node(node);
    ++cnt;
  }

  return cnt;
}

}  // namespace qcos
