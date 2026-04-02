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
#include <unordered_map>
#include <utility>
#include <vector>

namespace qcos {

struct MCTSGateSpec {
  std::string name;
  std::vector<int> qubits;
  std::vector<double> params;
};

struct MCTSDGNode {
  int id = -1;
  std::vector<int> qubits;
  std::vector<MCTSGateSpec> gates;
  std::vector<int> successors;
  std::vector<int> predecessors;
  int num_gate_2q = 0;
};

struct MCTSDependencyGraph {
  std::unordered_map<int, MCTSDGNode> nodes;
  int num_q_log = 0;
};

struct MCTSArchitectureGraph {
  std::vector<int> nodes;
  std::vector<std::pair<int, int>> edges;
};

struct MCTSSearchConfig {
  MCTSDependencyGraph dg;
  std::vector<int> init_mapping;
  std::string objective = "size";
  std::string select_mode_name = "KS";
  double select_mode_param = 20.0;
  std::string mode_bp_name = "globalscore";
  std::string mode_decision_name = "global_score";
  std::string mode_sim_name = "fix_cx_num";
  int mode_sim_times = 50;
  int mode_sim_num_cx = 10;
  int score_layer = 5;
  bool use_prune = true;
  bool use_hash = true;
  double score_decay_rate_size = 0.7;
  double score_decay_rate_depth = 0.85;
};

struct MCTSRoutingResult {
  std::vector<MCTSGateSpec> mapped_ir;
  std::unordered_map<int, int> mapping_virtual_to_final;
};

class CppMCTSRouting {
 public:
  explicit CppMCTSRouting(int selec_times = 5);
  ~CppMCTSRouting();
  CppMCTSRouting(CppMCTSRouting&&) noexcept;
  CppMCTSRouting& operator=(CppMCTSRouting&&) noexcept;
  CppMCTSRouting(const CppMCTSRouting&) = delete;
  CppMCTSRouting& operator=(const CppMCTSRouting&) = delete;

  MCTSRoutingResult execute_routing(
      const MCTSSearchConfig& search_config,
      const MCTSArchitectureGraph& ag,
      const std::unordered_map<int, int>& initial_layout, int num_q_vir);

  int selec_times() const;
  void set_selec_times(int selec_times);

 private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};

}  // namespace qcos