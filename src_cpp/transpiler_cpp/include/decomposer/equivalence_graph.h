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

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <tuple>

namespace qcos {

/**
 * @brief Represents a parameterized quantum gate.
 *
 * Example:
 * RX(q0, theta)
 *
 * Corresponds to:
 * - name   = "RX"
 * - qubits = {"q0"}
 * - params = {"theta"}
 *
 * This structure is mainly used for:
 * - equivalence rules
 * - gate decomposition
 * - decomposition table construction
 */
struct ParamGate {

    /// Gate name, e.g. RX / CX / U3
    std::string name;

    /// List of qubits operated on by this gate
    std::vector<std::string> qubits;

    /// Parameter expression list
    std::vector<std::string> params;

    /**
     * @brief Compare two ParamGate objects.
     *
     * Equality is determined by:
     * - gate name
     * - qubits
     * - parameters
     *
     * @param other Another ParamGate object
     * @return true if all fields are identical
     * @return false otherwise
     */
    bool operator==(const ParamGate& other) const;
};

/**
 * @brief Hash function for ParamGate.
 *
 * Enables ParamGate to be used in:
 * - std::unordered_map
 * - std::unordered_set
 */
struct ParamGateHash {

    /**
     * @brief Compute hash value for a ParamGate.
     *
     * @param g Input gate
     * @return std::size_t Hash value
     */
    std::size_t operator()(const ParamGate& g) const;
};

/**
 * @brief Represents an equivalence rule between quantum gates.
 *
 * A rule describes:
 *
 * target <=> sources
 *
 * Example:
 *
 * CX(q0,q1) = H(q1); CZ(q0,q1); H(q1)
 *
 * Used for:
 * - gate decomposition
 * - gate rewriting
 * - equivalence graph construction
 */
struct EquivalenceRule {

    /// Target gate to be decomposed or replaced
    ParamGate target;

    /// Equivalent source gate sequence
    std::vector<ParamGate> sources;

    /**
     * @brief Default constructor.
     */
    EquivalenceRule() = default;

    /**
     * @brief Construct rule from DSL string.
     *
     * Example:
     * "CX(q0,q1)=H(q1);CZ(q0,q1);H(q1)"
     *
     * @param dsl DSL formatted equivalence rule
     */
    EquivalenceRule(const std::string& dsl);

private:

    /**
     * @brief Parse a DSL rule string.
     *
     * Input format:
     * "A(...) = B(...); C(...); ..."
     *
     * Output:
     * - target gate
     * - source gate sequence
     *
     * @param dsl DSL string
     * @return Parsed target and source gates
     */
    std::pair<ParamGate, std::vector<ParamGate>>
    parse_dsl(const std::string& dsl);

    /**
     * @brief Parse a single gate block.
     *
     * Example:
     * "RX(q0,theta)"
     *
     * @param block Gate description block
     * @return Parsed ParamGate object
     */
    ParamGate parse_gate_block(const std::string& block);
};

/**
 * @brief Represents an edge in the equivalence graph.
 *
 * Describes:
 * src gate --(rule)--> dst gate
 *
 * Used for:
 * - graph construction
 * - visualization
 * - decomposition path search
 */
struct RuleEdge {

    /// Source gate name
    std::string src;

    /// Destination gate name
    std::string dst;

    /// Associated equivalence rule
    const EquivalenceRule* rule;

    /**
     * @brief Edge direction/type.
     *
     * Common values:
     * - "forward"
     * - "reverse"
     */
    std::string kind;
};

/**
 * @brief Graph representation of gate equivalence relationships.
 *
 * Maintains:
 * - equivalence rules
 * - forward/reverse indices
 * - optimal decomposition search
 * - recursive gate expansion
 *
 * Main functionalities:
 * - generate optimal decompositions
 * - build decomposition tables
 * - export graph visualization
 */
class EquivalenceGraph {
public:

    /**
     * @brief Construct an equivalence graph.
     *
     * Typically initializes all built-in equivalence rules.
     */
    EquivalenceGraph();

    /**
     * @brief Generate optimal decomposition rule dictionary.
     *
     * Given:
     * - source gate set (hardware-supported gates)
     * - target gate set (gates to decompose)
     *
     * Searches for optimal decomposition rules.
     *
     * @param source Supported primitive gate set
     * @param target Target gate set
     *
     * @return Mapping:
     * gate name -> optimal equivalence rule
     */
    std::unordered_map<std::string, EquivalenceRule>
    get_optimal_decomposition_rule_dictionary(
        const std::vector<std::string>& source,
        const std::vector<std::string>& target
    );

    /**
     * @brief Get all rule edges in the graph.
     *
     * Useful for:
     * - graph analysis
     * - visualization
     * - DOT export
     *
     * @return List of RuleEdge objects
     */
    std::vector<RuleEdge> rule_edges();

    /**
     * @brief Export graph in Graphviz DOT format.
     *
     * Example usage:
     *
     * dot -Tpng graph.dot -o graph.png
     *
     * @return DOT formatted graph string
     */
    std::string to_dot();

    /**
     * @brief Build complete decomposition table.
     *
     * Returns:
     * 1. Fully expanded decomposition table
     * 2. Gate cost table
     *
     * Expanded decompositions only contain gates
     * allowed in the target gate set.
     *
     * @param source Primitive gate set
     * @param target Target gate set
     *
     * @return Pair of:
     * - decomposition table
     * - cost table
     */
    std::pair<
        std::unordered_map<
            ParamGate,
            std::vector<ParamGate>,
            ParamGateHash
        >,
        std::unordered_map<std::string, int>
    >
    build_full_decomposition_table(
        const std::vector<std::string>& source,
        const std::vector<std::string>& target
    );

private:

    /// All equivalence rules
    std::vector<EquivalenceRule> rules;

    /**
     * @brief Forward decomposition index.
     *
     * Key:
     *   target gate name
     *
     * Value:
     *   rules that decompose this gate
     */
    std::unordered_map<
        std::string,
        std::vector<const EquivalenceRule*>
    > forward_index;

    /**
     * @brief Reverse decomposition index.
     *
     * Key:
     *   source gate name
     *
     * Value:
     *   rules containing this gate
     */
    std::unordered_map<
        std::string,
        std::vector<const EquivalenceRule*>
    > reverse_index;

    /**
     * @brief Compute cost of an equivalence rule.
     *
     * Cost may depend on:
     * - gate count
     * - two-qubit gate count
     * - circuit depth
     * - hardware preference
     *
     * Used for optimal decomposition search.
     *
     * @param rule Input equivalence rule
     * @return Rule cost
     */
    double rule_cost(const EquivalenceRule& rule);

    /**
     * @brief Rewrite parameter expressions using parameter mapping.
     *
     * Example:
     * theta -> pi/2
     *
     * @param exprs Original parameter expressions
     * @param param_map Parameter substitution map
     * @return Rewritten parameter expressions
     */
    std::vector<std::string> rewrite_params(
        const std::vector<std::string>& exprs,
        const std::unordered_map<std::string, std::string>& param_map
    );

    /**
     * @brief Recursively expand a gate decomposition.
     *
     * Expands a gate into primitive gates according to
     * the provided decomposition rules.
     *
     * Uses:
     * - memoization cache
     * - cycle detection
     *
     * @param gate Gate to expand
     * @param rule_map Optimal decomposition rules
     * @param target_set Allowed primitive gate set
     * @param cache Expansion cache
     * @param path Current recursion path for cycle detection
     *
     * @return Fully expanded gate sequence
     */
    std::vector<ParamGate> expand_gate_recursive(
        const ParamGate& gate,
        const std::unordered_map<std::string, EquivalenceRule>& rule_map,
        const std::unordered_set<std::string>& target_set,
        std::unordered_map<ParamGate, std::vector<ParamGate>, ParamGateHash>& cache,
        std::unordered_set<ParamGate, ParamGateHash>& path
    );
};

} // namespace qcos