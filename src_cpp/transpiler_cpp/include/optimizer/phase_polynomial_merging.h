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

#include "circuit/dag_node.h"
#include "optimizer/optimization_pass.h"

namespace qcos {

/**
 * @class PhasePolynomialMerging
 * @brief 使用相位多项式方法合并 Rz 门
 *
 * 自动管理 parameterize/deparameterize。
 */
class PhasePolynomialMerging : public OptimizationPass {
 public:
  explicit PhasePolynomialMerging(bool verbose = false);

  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;
  std::string name() const override { return "PhasePolynomialMerging"; }

 private:
  /**
   * @brief 使用相位多项式解析 CNOT-Rz 子电路，合并相同单项式的 Rz 门
   */
  int parse_cnot_rz_circuit(const std::vector<DAGOpNode*>& node_list,
                            DAGCircuit& dag);
  bool verbose_;
};

}  // namespace qcos
