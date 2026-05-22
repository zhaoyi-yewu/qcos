#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <tuple>
namespace qcos {
struct ParamGate {
    std::string name;
    std::vector<std::string> qubits;
    std::vector<std::string> params;

    bool operator==(const ParamGate& other) const;
};

// hash 支持（用于 unordered_map）
struct ParamGateHash {
    std::size_t operator()(const ParamGate& g) const;
};

struct EquivalenceRule {
    ParamGate target;
    std::vector<ParamGate> sources;
    
    EquivalenceRule()=default;
    EquivalenceRule(const std::string& dsl);

private:
    std::pair<ParamGate, std::vector<ParamGate>> parse_dsl(const std::string& dsl);
    ParamGate parse_gate_block(const std::string& block);
};

struct RuleEdge {
    std::string src;
    std::string dst;
    const EquivalenceRule* rule;
    std::string kind;
};

class EquivalenceGraph {
public:
    EquivalenceGraph();

    std::unordered_map<std::string, EquivalenceRule>
    get_optimal_decomposition_rule_dictionary(
        const std::vector<std::string>& source,
        const std::vector<std::string>& target
    );

    std::vector<RuleEdge> rule_edges();

    std::string to_dot();

    std::pair<
        std::unordered_map<ParamGate, std::vector<ParamGate>, ParamGateHash>,
        std::unordered_map<std::string, int>
    >
    build_full_decomposition_table(
        const std::vector<std::string>& source,
        const std::vector<std::string>& target
    );

private:
    std::vector<EquivalenceRule> rules;

    std::unordered_map<std::string, std::vector<const EquivalenceRule*>> forward_index;
    std::unordered_map<std::string, std::vector<const EquivalenceRule*>> reverse_index;

    double rule_cost(const EquivalenceRule& rule);

    std::vector<std::string> rewrite_params(
        const std::vector<std::string>& exprs,
        const std::unordered_map<std::string, std::string>& param_map
    );

    std::vector<ParamGate> expand_gate_recursive(
        const ParamGate& gate,
        const std::unordered_map<std::string, EquivalenceRule>& rule_map,
        const std::unordered_set<std::string>& target_set,
        std::unordered_map<ParamGate, std::vector<ParamGate>, ParamGateHash>& cache,
        std::unordered_set<ParamGate, ParamGateHash>& path
    );
};
}