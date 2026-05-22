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

#include "decomposer/decomposer.h"

#include <stdexcept>

namespace qcos {

// ==========================================
// Static member initialization
// ==========================================

/**
 * @brief Shared global equivalence graph instance.
 *
 * The graph is initialized lazily when the first
 * Decomposer object is constructed.
 *
 * Using a static instance avoids rebuilding
 * equivalence rules multiple times.
 */
std::unique_ptr<EquivalenceGraph> Decomposer::graph_ = nullptr;

// ==========================================
// Constructor
// ==========================================

/**
 * @brief Construct a Decomposer instance.
 *
 * Lazily initializes the shared EquivalenceGraph.
 *
 * The graph stores:
 * - equivalence rules
 * - decomposition search logic
 * - decomposition graph indices
 */
Decomposer::Decomposer() {
  if (!graph_) {
    graph_ = std::make_unique<EquivalenceGraph>();
  }
}

// ==========================================
// Generate decomposition rules
// ==========================================

/**
 * @brief Build a complete decomposition table.
 *
 * Given:
 * - source gate set (hardware-supported gates)
 * - target gate set (gates requiring decomposition)
 *
 * The equivalence graph searches for optimal
 * decomposition paths and generates:
 * - fully expanded decomposition rules
 * - gate usage statistics
 *
 * @param source Primitive/source gate set
 * @param target Target gate set
 *
 * @return Pair containing:
 * - decomposition table
 * - usage statistics
 *
 * @throws std::runtime_error
 * Thrown if the equivalence graph is not initialized.
 */
std::pair<
    Decomposer::DecompositionTable,
    Decomposer::UsageStats>
Decomposer::get_decompose_rules(
    const std::vector<std::string>& source,
    const std::vector<std::string>& target) {

  if (!graph_) {
    throw std::runtime_error(
        "EquivalenceGraph not initialized");
  }

  return graph_->build_full_decomposition_table(
      source,
      target);
}

// ==========================================
// Apply decomposition rules
// ==========================================

/**
 * @brief Apply decomposition table to a circuit.
 *
 * Expands unsupported gates into equivalent
 * primitive gate sequences using the provided
 * decomposition table.
 *
 * This function directly forwards the table to
 * RuleApplier without performing intermediate
 * transformations or flattening.
 *
 * @param circuit Input quantum circuit
 * @param table Decomposition lookup table
 *
 * @return Fully decomposed circuit
 */
Decomposer::OpList
Decomposer::apply_decompose_rules(
    const std::vector<OpPtr>& circuit,
    const DecompositionTable& table) {

  // Directly apply the decomposition table
  // without additional conversion.
  return applier_.apply_with_decomposition_table(
      circuit,
      table);
}

}  // namespace qcos