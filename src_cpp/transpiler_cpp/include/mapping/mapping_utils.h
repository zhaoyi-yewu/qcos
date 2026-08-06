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
#include <unordered_map>
#include <utility>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"
#include "mapping/chip_data.h"

namespace qcos {

/**
 * @brief 将 BaseOperation 转换为 GateOperation
 *
 * 若 op 本身已是 GateOperation 则直接拷贝；
 * 若是 measure / sync / reset / move 等特殊操作，则临时当作单量子门处理，
 * 以便参与 SABRE 路由，路由完成后再由 restore_base_operation 还原。
 *
 * @param op 原始 BaseOperation
 * @return 等价的 GateOperation
 * @throw std::invalid_argument 当 op 为不支持的特殊操作类型时
 */
GateOperation to_gate_operation(const BaseOperation& op);

/**
 * @brief 将路由后的 GateOperation 还原为 BaseOperation
 *
 * 优先尝试通过 create_gate 还原为具体的门类型；若还原失败（未知门名），
 * 则回退构造 GateOperation 对象。
 *
 * @param routed_op 路由后的 GateOperation
 * @return 还原后的 BaseOperation（可能为 GateOperation 子类）
 */
std::shared_ptr<BaseOperation> restore_base_operation(
    const GateOperation& routed_op);

/**
 * @brief 物理量子位 ID 稠密化映射表
 *
 * 存储原始物理 ID 空间与稠密 ID 空间的双向映射。
 * 不可用量子位在 orig_to_dense 中记为 -1。
 */
struct PhysicalIdRemap {
  std::vector<int> orig_to_dense;  ///< 原始 ID -> 稠密 ID, 不可用量子位填 -1
  std::vector<int> dense_to_orig;  ///< 稠密 ID -> 原始 ID
  int dense_count = 0;             ///< 稠密化后的物理位总数
};

/**
 * @brief 按保真度阈值过滤低保真度边和单比特
 *
 * 将 single_qubit_fidelities 中保真度 <= threshold 的条目置 0，
 * 同步移除 coupling_list/edge_fidelities 中边保真度 <= threshold
 * 或任一端点单比特保真度 <= threshold 的边。
 *
 * @param chip [in/out] 芯片标定数据，原地修改
 * @param fidelity_threshold 保真度阈值，<=0 时不做任何过滤
 */
void filter_low_fidelity(ChipCalibration& chip, double fidelity_threshold);

/**
 * @brief 找出耦合图中所有连通分量
 *
 * 对 coupling_list 中的节点做 BFS，为每个节点分配一个分量代表 ID。
 * 两个节点在同一连通分量中当且仅当它们对应的代表 ID 相同。
 *
 * @param coupling_list 耦合边列表
 * @return qubit_id -> 分量代表 ID 的映射表
 */
std::unordered_map<int, int> find_connected_components(
    const std::vector<std::pair<int, int>>& coupling_list);

/**
 * @brief 选择耦合图的最大连通分量（仅过滤边列表）
 *
 * 通过 find_connected_components 找出所有连通分量，
 * 只保留节点数最多的那个分量中的边。
 *
 * @param coupling_list [in/out] 耦合边列表，原地过滤为最大连通分量
 */
void select_largest_component(std::vector<std::pair<int, int>>& coupling_list);

/**
 * @brief 选择耦合图的最大连通分量（同步过滤边保真度）
 *
 * 通过 find_connected_components
 * 找出所有连通分量，只保留节点数最多的那个分量。
 *
 * @param coupling_list [in/out] 耦合边列表，原地过滤为最大连通分量
 * @param edge_fidelities [in/out] 边保真度列表，与 coupling_list 同步过滤
 */
void select_largest_component(std::vector<std::pair<int, int>>& coupling_list,
                              std::vector<double>& edge_fidelities);

/**
 * @brief 芯片拓扑稠密化: 将稀疏物理 ID 压缩为 0..N-1
 *
 * 对 chip 中当前耦合边涉及的物理位重新编号为连续 0..N-1，
 * 并同步重建 single_qubit_fidelities。
 *
 * @param chip [in/out] 芯片标定数据, 原地修改为稠密 ID 空间
 * @return PhysicalIdRemap 映射表, 供 restore_physical_ids 后处理使用
 */
PhysicalIdRemap densify_chip_topology(ChipCalibration& chip);

/**
 * @brief 将稠密物理 ID 还原为原始物理 ID
 *
 * @param remap densify_chip_topology 返回的映射表
 * @param physical_gates [in/out] 物理门序列
 * @param logic2phy [in/out] 逻辑->物理映射
 */
void restore_physical_ids(const PhysicalIdRemap& remap,
                          std::vector<GateOperation>& physical_gates,
                          std::vector<int>& logic2phy);

/**
 * @brief 校验映射函数的公共输入参数
 *
 * 检查 coupling_list 非空、edge_fidelities 与 coupling_list 长度一致、
 * 逻辑比特数不超过可用物理比特数（去重计数，排除不连通的孤立比特）。
 *
 * @param coupling_list 物理耦合边列表
 * @param edge_fidelities 边保真度数组，空则跳过长度校验
 * @param num_logical 逻辑比特数
 * @throw std::invalid_argument 当参数不合法时
 */
void validate_mapping_inputs(
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities, int num_logical);

}  // namespace qcos
