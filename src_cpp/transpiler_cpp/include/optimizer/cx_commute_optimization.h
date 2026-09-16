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
 * @class CxCommuteOptimization
 * @brief 使用交换规则优化 CNOT 门
 *
 * 自动管理 parameterize/deparameterize。
 */
class CxCommuteOptimization : public OptimizationPass {
 public:
  explicit CxCommuteOptimization(bool verbose = false);

  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;
  std::string name() const override { return "CxCommuteOptimization"; }

 private:
  std::vector<OptimizingTemplate> cx_commute_ctrl_templates_;
  std::vector<OptimizingTemplate> cx_commute_targ_templates_;
  bool verbose_;
};

}  // namespace qcos
