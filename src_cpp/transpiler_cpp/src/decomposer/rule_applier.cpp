#include <cmath>
#include <functional>
#include <stdexcept>
#include <sstream>

#include "decomposer/rule_applier.h"
#include "utils/exprtk.hpp"

namespace qcos {

// =============================
// eval_expr
// =============================
double RuleApplier::eval_expr(
    const std::string& expr,
    const std::unordered_map<std::string, double>& env) {

  using symbol_table_t = exprtk::symbol_table<double>;
  using expression_t   = exprtk::expression<double>;
  using parser_t       = exprtk::parser<double>;

  std::unordered_map<std::string, double> local_env = env;

  symbol_table_t symbol_table;

  for (auto& kv : local_env) {
    symbol_table.add_variable(kv.first, kv.second);
  }

  symbol_table.add_constants(); // pi, e

  expression_t expression;
  expression.register_symbol_table(symbol_table);

  parser_t parser;
  if (!parser.compile(expr, expression)) {
    throw std::runtime_error(
        "Expr parse error: " + expr + " | " + parser.error());
  }

  return expression.value();
}

// =============================
// apply_one_rule
// =============================
RuleApplier::OpList RuleApplier::apply_one_rule(
    const BaseOperation& op,
    const ParamGate& target,
    const std::vector<ParamGate>& sources) {

  if (target.qubits.size() != op.targets.size()) {
    throw std::runtime_error("Qubit size mismatch");
  }

  if (target.params.size() != op.arg_value.size()) {
    throw std::runtime_error("Param size mismatch");
  }

  // qubit mapping
  std::unordered_map<std::string, int> qubit_map;
  for (size_t i = 0; i < target.qubits.size(); ++i) {
    qubit_map[target.qubits[i]] = op.targets[i];
  }

  // param mapping
  std::unordered_map<std::string, double> env;
  for (size_t i = 0; i < target.params.size(); ++i) {
    env[target.params[i]] = op.arg_value[i];
  }

  env["pi"] = M_PI;
  env["e"]  = M_E;

  OpList result;

  for (const auto& src : sources) {

    std::vector<int> qubits;
    for (const auto& q : src.qubits) {
      if (!qubit_map.count(q)) {
        throw std::runtime_error("Unknown qubit: " + q);
      }
      qubits.push_back(qubit_map[q]);
    }

    std::vector<double> params;
    for (const auto& p : src.params) {
      params.push_back(eval_expr(p, env));
    }

    result.push_back(create_gate(src.name, qubits, params));
  }

  return result;
}

// =============================
// clone helper
// =============================
static std::vector<std::unique_ptr<BaseOperation>> clone_vector(
    const std::vector<std::unique_ptr<BaseOperation>>& src) {

  std::vector<std::unique_ptr<BaseOperation>> dst;
  for (const auto& op : src) {
    dst.push_back(op->clone());
  }
  return dst;
}

// =============================
// apply_path
// =============================
std::vector<std::unique_ptr<BaseOperation>> RuleApplier::apply_path(
    const std::vector<OpPtr>& circuit,
    const std::vector<std::string>& target,
    const std::unordered_map<std::string, EquivalenceRule>& rule_dict) {

  std::unordered_set<std::string> target_set(target.begin(), target.end());

  using OpVec = std::vector<std::unique_ptr<BaseOperation>>;
  std::unordered_map<std::string, OpVec> cache;

  auto make_signature = [](const BaseOperation& op) {
    std::ostringstream oss;
    oss << op.name << "|";
    for (auto t : op.targets) oss << t << ",";
    oss << "|";
    for (auto a : op.arg_value) oss << a << ",";
    return oss.str();
  };

  std::function<OpVec(const BaseOperation&)> decompose =
      [&](const BaseOperation& gate) -> OpVec {

    std::string sig = make_signature(gate);

    if (cache.count(sig)) {
      return clone_vector(cache[sig]);
    }

    OpVec result;

    if (target_set.count(gate.name)) {
      result.push_back(gate.clone());
      cache[sig] = clone_vector(result);
      return result;
    }

    if (!rule_dict.count(gate.name)) {
      throw std::runtime_error("No rule for gate: " + gate.name);
    }

    const auto& rule = rule_dict.at(gate.name);

    auto expanded = apply_one_rule(
        gate,
        rule.target,
        rule.sources);

    for (const auto& op : expanded) {
      auto sub = decompose(*op);
      for (auto& x : sub) {
        result.push_back(std::move(x));
      }
    }

    cache[sig] = clone_vector(result);
    return result;
  };

  OpVec final_result;

  for (const auto& gate : circuit) {
    auto part = decompose(*gate);
    for (auto& op : part) {
      final_result.push_back(std::move(op));
    }
  }

  return final_result;
}

// =============================
// apply_with_decomposition_table（最终正确版）
// =============================
RuleApplier::OpList RuleApplier::apply_with_decomposition_table(
    const std::vector<OpPtr>& circuit,
    const DecompositionTable& table) {

  OpList result;

  for (const auto& op : circuit) {

    bool matched = false;

    for (const auto& [target, sources] : table) {

      if (target.name != op->name) continue;
      if (target.qubits.size() != op->targets.size()) continue;
      if (target.params.size() != op->arg_value.size()) continue;

      matched = true;

      // qubit mapping
      std::unordered_map<std::string, int> qubit_map;
      for (size_t i = 0; i < target.qubits.size(); ++i) {
        qubit_map[target.qubits[i]] = op->targets[i];
      }

      // param mapping（关键修复）
      std::unordered_map<std::string, double> env;
      for (size_t i = 0; i < target.params.size(); ++i) {
        env[target.params[i]] = op->arg_value[i];
      }

      env["pi"] = M_PI;
      env["e"]  = M_E;

      for (const auto& g : sources) {

        std::vector<int> qubits;
        for (const auto& q : g.qubits) {
          if (!qubit_map.count(q)) {
            throw std::runtime_error("Unknown qubit: " + q);
          }
          qubits.push_back(qubit_map[q]);
        }

        std::vector<double> params;
        for (const auto& p : g.params) {
          params.push_back(eval_expr(p, env));
        }

        result.push_back(create_gate(g.name, qubits, params));
      }

      break;
    }

    if (!matched) {
      result.push_back(op->clone());
    }
  }

  return result;
}

} // namespace qcos