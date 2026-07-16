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
  std::vector<int> orig_to_dense;  ///< 原始 ID → 稠密 ID, 不可用量子位填 -1
  std::vector<int> dense_to_orig;  ///< 稠密 ID → 原始 ID
  int dense_count = 0;             ///< 稠密化后的物理位总数
};

/**
 * @brief 芯片拓扑稠密化: 过滤低保真度边、保留最大连通分量、将稀疏物理 ID
 * 压缩为 0..N-1
 *
 * @param chip [in/out] 芯片标定数据, 原地修改为稠密 ID 空间
 * @param fidelity_threshold 保真度阈值, 低于此值的边被过滤(<=0 表示不过滤)
 * @return PhysicalIdRemap 映射表, 供 restore_physical_ids 后处理使用
 */
PhysicalIdRemap densify_chip_topology(ChipCalibration& chip,
                                      double fidelity_threshold = 0.0);

/**
 * @brief 将稠密物理 ID 还原为原始物理 ID
 *
 * @param remap densify_chip_topology 返回的映射表
 * @param physical_gates [in/out] 物理门序列
 * @param logic2phy [in/out] 逻辑→物理映射
 */
void restore_physical_ids(const PhysicalIdRemap& remap,
                          std::vector<GateOperation>& physical_gates,
                          std::vector<int>& logic2phy);

}  // namespace qcos
