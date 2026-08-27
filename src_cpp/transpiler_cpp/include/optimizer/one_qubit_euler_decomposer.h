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

#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "circuit/base_operation.h"
#include "optimizer/matrix_utils.h"

namespace qcos {

struct SingleQubitDecomp {
  double theta;
  double phi;
  double lambda;
  double phase;
};

/**
 * @brief 将 2x2 酉矩阵分解为 ZYZ 欧拉角
 *
 * 分解公式: U = e^{i*phase} * Rz(phi) * Ry(theta) * Rz(lambda)
 *
 * @param u 2x2 酉矩阵
 * @return SingleQubitDecomp 分解结果 (theta, phi, lambda, phase)
 */
SingleQubitDecomp decompose_single_qubit(const CMatrix& u);

/**
 * @brief 将单比特酉矩阵转换为目标基础门序列
 *
 * 根据 basis_gates 选择合适的分解基：
 * - {"rz", "ry"}: ZYZ 分解
 * - {"rz", "rx"}: ZXZ 分解
 * - {"rx", "ry"}: XYX 分解
 * - {"u3"}: 直接使用 U3 门
 *
 * @param u 2x2 酉矩阵
 * @param qubit 目标量子位
 * @param basis_gates 可选的目标基础门集合
 * @return 基础门操作序列
 */
std::vector<std::shared_ptr<BaseOperation>> single_qubit_unitary_to_basis(
    const CMatrix& u, int qubit,
    const std::optional<std::set<std::string>>& basis_gates);

}  // namespace qcos
