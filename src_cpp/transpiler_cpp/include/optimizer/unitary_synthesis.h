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

#include <complex>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "optimizer/optimization_pass.h"
#include "optimizer/matrix_utils.h"
#include "optimizer/one_qubit_euler_decomposer.h"
#include "optimizer/two_qubit_decomposer.h"

namespace qcos {

/**
 * @brief 将酉矩阵分解为目标门集中的基础门序列
 *
 * 核心接口：输入矩阵 + 基础门集 → 输出门序列。
 *
 * 根据矩阵维度自动选择分解算法：
 *   - 2×2 → 单比特 ZYZ 欧拉角分解
 *   - 4×4 → 双比特 KAK/Weyl Chamber 分解
 *
 * @param unitary     输入酉矩阵 (2×2 或 4×4)
 * @param basis_gates 目标基础门名称集合，如 {"cx", "rz", "ry"}
 * @param qubits      门作用的量子位编号 (可选)
 *                    2×2 默认 {0}，4×4 默认 {0, 1}
 * @return 基础门操作序列，按执行顺序排列
 *
 * @code
 * // 示例：将 H 门分解为 rz+ry 基
 * auto h_mat = matrix_utils::gate_to_matrix(create_gate("h", {0}));
 * auto gates = decompose_unitary(h_mat, {"rz", "ry"});
 * // gates = [Rz(λ), Ry(θ), Rz(φ)]
 *
 * // 示例：将 CX 门分解为 cx+rz+ry 基
 * auto cx_mat = matrix_utils::gate_to_matrix(create_gate("cx", {0,1}));
 * auto gates = decompose_unitary(cx_mat, {"cx", "rz", "ry"});
 * // gates = [CX(0,1)] (直接匹配)
 * @endcode
 *
 * @throws std::invalid_argument 矩阵维度不支持 (非 2×2 且非 4×4)
 * @throws std::invalid_argument 矩阵不是酉矩阵
 */
std::vector<std::shared_ptr<BaseOperation>> decompose_unitary(
    const CMatrix& unitary, const std::set<std::string>& basis_gates,
    const std::vector<int>& qubits = {});

class UnitarySynthesis : public OptimizationPass {
 public:
  using OpPtr = std::shared_ptr<BaseOperation>;
  using OpList = std::vector<OpPtr>;

  UnitarySynthesis(
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt,
      double approximation_degree = 1.0, size_t max_block_size = 2,
      bool verbose = false);

  int run(DAGCircuit& dag,
          const std::optional<std::set<std::string>>& basis_gates =
              std::nullopt) override;

  std::string name() const override { return "UnitarySynthesis"; }

  OpList synthesize_block(const CMatrix& unitary,
                          const std::vector<int>& qubits);

 private:
  std::optional<std::set<std::string>> basis_gates_;
  double approximation_degree_;
  size_t max_block_size_;
  bool verbose_;

  OpList synthesize_1q(const CMatrix& u, int qubit);
  OpList synthesize_2q(const CMatrix& u, int q0, int q1);
};

class ConsolidateBlocks {
 public:
  using OpPtr = std::shared_ptr<BaseOperation>;

  ConsolidateBlocks(
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt,
      double approximation_degree = 1.0, size_t min_block_size = 2);

  int run(
      DAGCircuit& dag,
      const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

 private:
  std::optional<std::set<std::string>> basis_gates_;
  double approximation_degree_;
  size_t min_block_size_;
};

}  // namespace qcos
