#pragma once

#include <memory>
#include <vector>
#include <string>
#include <unordered_map>
#include <utility>

#include "circuit/base_operation.h"
#include "decomposer/rule_applier.h"
#include "decomposer/equivalence_graph.h"

namespace qcos {

// ===== Decomposer =====
class Decomposer {
 public:
  using OpPtr = std::unique_ptr<BaseOperation>;
  using OpList = std::vector<OpPtr>;

  using DecompositionTable =
      std::unordered_map<ParamGate,
                         std::vector<ParamGate>,
                         ParamGateHash>;

  using UsageStats = std::unordered_map<std::string, int>;

 public:
  Decomposer();

  std::pair<DecompositionTable, UsageStats>
  get_decompose_rules(
      const std::vector<std::string>& source,
      const std::vector<std::string>& target);

  OpList apply_decompose_rules(
      const std::vector<OpPtr>& circuit,
      const DecompositionTable& table);

 private:
  static std::unique_ptr<EquivalenceGraph> graph_;
  RuleApplier applier_;
};
}