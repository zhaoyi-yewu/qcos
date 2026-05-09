#include "decomposer/decomposer.h"
#include <stdexcept>
namespace qcos {

// ===== static 成员初始化 =====
std::unique_ptr<EquivalenceGraph> Decomposer::graph_ = nullptr;

// =============================
// 构造函数
// =============================
Decomposer::Decomposer() {
  if (!graph_) {
    graph_ = std::make_unique<EquivalenceGraph>();
  }
}

// =============================
// 获取 decomposition table
// =============================
std::pair<Decomposer::DecompositionTable,
          Decomposer::UsageStats>
Decomposer::get_decompose_rules(
    const std::vector<std::string>& source,
    const std::vector<std::string>& target) {

  if (!graph_) {
    throw std::runtime_error("EquivalenceGraph not initialized");
  }

  return graph_->build_full_decomposition_table(source, target);
}

// =============================
// 应用 decomposition
// =============================
Decomposer::OpList
Decomposer::apply_decompose_rules(
    const std::vector<OpPtr>& circuit,
    const DecompositionTable& table) {

  // ✅ 直接传递，不做任何降维转换
  return applier_.apply_with_decomposition_table(circuit, table);
}
}