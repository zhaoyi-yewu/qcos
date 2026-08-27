/*
 * Copyright header - see existing files for full text
 */

#pragma once

#include <chrono>
#include <iostream>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "optimizer/optimization_pass.h"
#include "optimizer/template.h"

namespace qcos {

/**
 * @class HadamardGateReduction
 * @brief 使用模板匹配减少 Hadamard 门数量
 *
 * 不做 parameterize：模板使用 s/sdg 原始门名进行匹配。
 */
class HadamardGateReduction : public OptimizationPass {
 public:
  explicit HadamardGateReduction(bool verbose = false);

  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;
  std::string name() const override { return "HadamardGateReduction"; }

 private:
  std::vector<OptimizingTemplate> hadamard_templates_;
  bool verbose_;
};

}  // namespace qcos
