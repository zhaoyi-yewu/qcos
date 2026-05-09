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
#include <vector>
#include <string>
#include <unordered_map>
#include <utility>

#include "circuit/base_operation.h"
#include "decomposer/rule_applier.h"
#include "decomposer/equivalence_graph.h"

namespace qcos {

/**
 * @brief Quantum gate decomposer.
 *
 * This class is responsible for:
 * - generating decomposition rules
 * - expanding gates into supported primitive gates
 * - applying decomposition rules to a quantum circuit
 *
 * Internally it uses:
 * - EquivalenceGraph for rule search
 * - RuleApplier for circuit transformation
 */
class Decomposer {
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
   *
   * Example:
   *   CX -> {H, CZ, H}
   */
  using DecompositionTable =
      std::unordered_map<
          ParamGate,
          std::vector<ParamGate>,
          ParamGateHash>;

  /**
   * @brief Statistics of gate usage during decomposition.
   *
   * Maps:
   *   gate name -> usage count
   */
  using UsageStats = std::unordered_map<std::string, int>;

 public:

  /**
   * @brief Construct a decomposer.
   *
   * Initializes:
   * - equivalence graph
   * - decomposition rule applier
   */
  Decomposer();

  /**
   * @brief Generate decomposition rules.
   *
   * Given:
   * - source gate set (hardware-supported gates)
   * - target gate set (gates to decompose)
   *
   * Builds a complete decomposition table.
   *
   * @param source Primitive gate set
   * @param target Target gate set
   *
   * @return Pair of:
   * - decomposition table
   * - gate usage statistics
   */
  std::pair<DecompositionTable, UsageStats>
  get_decompose_rules(
      const std::vector<std::string>& source,
      const std::vector<std::string>& target);

  /**
   * @brief Apply decomposition rules to a quantum circuit.
   *
   * Replaces unsupported gates using the provided
   * decomposition table.
   *
   * Example:
   *   CX -> H + CZ + H
   *
   * @param circuit Input quantum circuit
   * @param table Decomposition lookup table
   *
   * @return Fully decomposed circuit
   */
  OpList apply_decompose_rules(
      const std::vector<OpPtr>& circuit,
      const DecompositionTable& table);

 private:

  /**
   * @brief Shared equivalence graph instance.
   *
   * Stores all equivalence relationships and
   * decomposition search logic.
   */
  static std::unique_ptr<EquivalenceGraph> graph_;

  /**
   * @brief Rule application engine.
   *
   * Responsible for applying decomposition rules
   * onto actual circuit operations.
   */
  RuleApplier applier_;
};

}  // namespace qcos