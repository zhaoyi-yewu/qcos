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

#include <vector>
#include <memory>
#include <unordered_map>
#include <string>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"
#include "decomposer/equivalence_graph.h"

namespace qcos {

/**
 * @brief Applies gate decomposition rules to quantum circuits.
 *
 * This class is responsible for:
 * - applying a single decomposition rule
 * - recursively expanding decomposition paths
 * - transforming circuits using decomposition tables
 *
 * It converts high-level gates into equivalent
 * lower-level gate sequences.
 */
class RuleApplier {
 public:

  /// Alias for quantum operation pointer
  using OpPtr = std::unique_ptr<BaseOperation>;

  /// Alias for operation list
  using OpList = std::vector<OpPtr>;

  /**
   * @brief Decomposition lookup table.
   *
   * Maps:
   *   gate -> decomposed gate sequence
   */
  using DecompositionTable =
      std::unordered_map<
          ParamGate,
          std::vector<ParamGate>,
          ParamGateHash>;

  /**
   * @brief Apply a single decomposition rule.
   *
   * Replaces:
   *   target gate
   *
   * With:
   *   equivalent source gate sequence
   *
   * Example:
   *   CX -> H + CZ + H
   *
   * Parameter substitution and qubit mapping
   * are automatically handled.
   *
   * @param op Original operation
   * @param target Target gate pattern
   * @param sources Replacement gate sequence
   *
   * @return Expanded operation sequence
   */
  OpList apply_one_rule(
      const BaseOperation& op,
      const ParamGate& target,
      const std::vector<ParamGate>& sources);

  /**
   * @brief Apply recursive decomposition path expansion.
   *
   * Expands all gates in a circuit according to
   * the provided optimal rule dictionary.
   *
   * Gates already in the target gate set
   * remain unchanged.
   *
   * @param circuit Input circuit
   * @param target Allowed target gate set
   * @param rule_dict Optimal decomposition rules
   *
   * @return Fully expanded circuit
   */
  OpList apply_path(
      const std::vector<OpPtr>& circuit,
      const std::vector<std::string>& target,
      const std::unordered_map<std::string, EquivalenceRule>& rule_dict);

  /**
   * @brief Apply decomposition using a decomposition table.
   *
   * Performs direct table-driven expansion.
   *
   * This version is intended to support:
   * - fully expanded decompositions
   * - efficient circuit rewriting
   * - cached decomposition results
   *
   * @param circuit Input circuit
   * @param table Decomposition lookup table
   *
   * @return Decomposed circuit
   */
  OpList apply_with_decomposition_table(
      const std::vector<OpPtr>& circuit,
      const DecompositionTable& table);

 private:

  /**
   * @brief Evaluate a parameter expression.
   *
   * Example:
   *   "theta / 2"
   *   "pi + lambda"
   *
   * Uses the provided parameter environment
   * to substitute symbolic variables.
   *
   * @param expr Expression string
   * @param env Variable environment
   *
   * @return Evaluated numeric result
   */
  double eval_expr(
      const std::string& expr,
      const std::unordered_map<std::string, double>& env);
};

} // namespace qcos