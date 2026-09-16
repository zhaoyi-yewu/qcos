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
 * @class RzCommuteOptimization
 * @brief 使用交换规则合并相邻 Rz 门
 *
 * 自动管理 parameterize/deparameterize：构造时将离散相位门转为 Rz，
 * 析构时在条件允许时还原。
 */
class RzCommuteOptimization : public OptimizationPass {
 public:
  explicit RzCommuteOptimization(bool verbose = false);

  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;
  std::string name() const override { return "RzCommuteOptimization"; }

 private:
  std::vector<OptimizingTemplate> rz_commute_templates_;
  bool verbose_;
};

}  // namespace qcos
