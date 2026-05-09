#pragma once

#include <vector>
#include <memory>
#include <unordered_map>
#include <string>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"
#include "decomposer/equivalence_graph.h"

namespace qcos {

class RuleApplier {
 public:
  using OpPtr = std::unique_ptr<BaseOperation>;
  using OpList = std::vector<OpPtr>;

  using DecompositionTable =
      std::unordered_map<ParamGate,
                         std::vector<ParamGate>,
                         ParamGateHash>;

  // ===== 单条规则 =====
  OpList apply_one_rule(
      const BaseOperation& op,
      const ParamGate& target,
      const std::vector<ParamGate>& sources);

  // ===== 路径展开 =====
  OpList apply_path(
      const std::vector<OpPtr>& circuit,
      const std::vector<std::string>& target,
      const std::unordered_map<std::string, EquivalenceRule>& rule_dict);

  // ===== table 驱动展开（修复版）=====
  OpList apply_with_decomposition_table(
      const std::vector<OpPtr>& circuit,
      const DecompositionTable& table);

 private:
  double eval_expr(
      const std::string& expr,
      const std::unordered_map<std::string, double>& env);
};

} // namespace qcos