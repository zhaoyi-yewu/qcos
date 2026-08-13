#ifndef QCOS_OPTIMIZER_OPTIMIZATION_PASS_H_
#define QCOS_OPTIMIZER_OPTIMIZATION_PASS_H_

#pragma once

#include <optional>
#include <set>
#include <string>

#include "circuit/dag_circuit.h"

namespace qcos {

/**
 * @brief 所有优化 pass 的公共基类
 *
 * 统一 run() 签名为 int 返回值（减少的门数量），
 * 并要求提供 pass 名称用于日志和调试。
 */
class OptimizationPass {
 public:
  virtual ~OptimizationPass() = default;

  /**
   * @brief 在 DAG 上执行优化
   * @param dag 待优化的量子线路 DAG（原地修改）
   * @param basis_gates 可选 basis gate 过滤集合
   * @return int 被减少的门数量（0 表示无变化）
   */
  virtual int run(DAGCircuit& dag,
                  const std::optional<std::set<std::string>>& basis_gates) = 0;

  /**
   * @brief 返回 pass 名称，用于日志
   */
  virtual std::string name() const = 0;
};

}  // namespace qcos

#endif  // QCOS_OPTIMIZER_OPTIMIZATION_PASS_H_
