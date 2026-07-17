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
 * @brief 从 IR 直接计算每个操作的拓扑层号，无需构建 DAG
 *
 * 对每个 qubit 追踪最近层号，每个门的层号 = max(前驱层号) + 1。
 *
 * @param ir 操作序列
 * @return 每个操作对应的拓扑层号（1-based）
 */
std::vector<int> ir_layers(
    const std::vector<std::shared_ptr<BaseOperation>>& ir);

/**
 * @brief 按层号将 IR 拆分为 num_chunks 个段
 *
 * 向上取整计算每段包含的层数，空段自动移除，返回的实际段数可能少于
 * num_chunks。
 *
 * @param ir 操作序列
 * @param op_layers ir_layers() 返回的层号
 * @param num_chunks 目标段数
 * @return 拆分后的段列表（非空）
 */
std::vector<std::vector<std::shared_ptr<BaseOperation>>> split_ir_by_layers(
    const std::vector<std::shared_ptr<BaseOperation>>& ir,
    const std::vector<int>& op_layers, int num_chunks);

/**
 * @brief 对 IR 执行多层优化
 *
 * opt_level:
 *   0 - 不做优化
 *   1 - InverseCancellation + AdjacentPhaseOptPass
 *   2 - Level 1 + EquivalencePass
 *   3 - Level 2 + CliffordRzOptimization
 *
 * num_threads:
 *   1 - 串行（默认）
 *   0 - 自动并行（线程数取 hardware_concurrency）
 *   >1 - 指定线程数并行
 *
 * fast_mode:
 *   false（默认）- 反复执行 pass 列表直到电路规模不再减小
 *   true - 快速模式，只执行一轮 pass，无论是否收敛。
 *
 * @param ir 待优化的操作序列
 * @param opt_level 优化级别 (0-3)
 * @param verbose 是否打印优化详情
 * @param basis_gates 可选 basis gate 过滤集合
 * @param num_threads 并行线程数：1=串行，0=自动，>1=指定
 * @param fast_mode 快速模式：true 只跑一轮，false 跑到收敛
 * @return std::vector<std::shared_ptr<BaseOperation>> 优化后的操作序列
 */
std::vector<std::shared_ptr<BaseOperation>> optimize(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level = 1,
    bool verbose = false,
    const std::optional<std::set<std::string>>& basis_gates = std::nullopt,
    size_t num_threads = 1, bool fast_mode = false);

}  // namespace qcos
