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

namespace qcos {

/**
 * @brief 对 IR 执行多层优化
 *
 * opt_level:
 *   0 - 不做优化
 *   1 - InverseCancellation + AdjacentPhaseOptPass
 *   2 - Level 1 + EquivalencePass
 *   3 - Level 2 + CliffordRzOptimization
 *
 * @param ir 待优化的操作序列
 * @param opt_level 优化级别 (0-3)
 * @param verbose 是否打印优化详情
 * @param basis_gates 可选 basis gate 过滤集合
 * @return std::vector<std::shared_ptr<BaseOperation>> 优化后的操作序列
 */
std::vector<std::shared_ptr<BaseOperation>> optimize(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level = 1,
    bool verbose = false,
    const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

}  // namespace qcos
