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

#include <unordered_map>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @brief 两比特门频率统计条目
 *
 * 记录一对逻辑比特 (control, target) 在电路中作为两比特门出现的次数。
 */
struct TwoQubitPair {
  int control;  ///< 逻辑控制比特
  int target;   ///< 逻辑目标比特
  int count;    ///< 该方向出现次数
};

/**
 * @brief 离子阱初始映射
 *
 * 封装映射过程中的全部数据和逻辑：构造时接收原始输入
 * （门序列、耦合边、保真度），内部完成数据预处理（频率统计），
 * solve() 按排列数自动选择精确枚举或贪心+局部搜索。
 *
 * 使用方式：构造后调用 solve() 获取最优映射。
 */
class IonTrapLayout {
 public:
  /**
   * @brief 构造映射求解器
   *
   * 内部完成数据预处理：从门序列提取两比特门频率表，
   * 从耦合边+保真度构建可靠性查表。
   *
   * @param gates_list 逻辑门序列
   * @param coupling_list 物理耦合边（有向）
   * @param edge_fidelities 与 coupling_list 对应的边保真度
   * @param single_qubit_fidelities 按物理比特 ID 索引的单比特保真度
   * @param num_logical 逻辑比特数
   */
  IonTrapLayout(const std::vector<GateOperation>& gates_list,
                const std::vector<std::pair<int, int>>& coupling_list,
                const std::vector<double>& edge_fidelities,
                const std::vector<double>& single_qubit_fidelities,
                int num_logical);

  /**
   * @brief 求解最优映射
   *
   * 按排列数自动选择策略：
   * - P(num_physical, num_logical) <= 2000000：精确枚举，全局最优
   * - 超过阈值：贪心初始化 + 局部搜索
   *
   * @return 逻辑到物理映射，逻辑 i -> 物理 mapping[i]
   */
  std::vector<int> solve() const;

 private:
  /**
   * @brief 从 coupling_list 推断物理比特总数（最大节点 ID + 1）
   * @param coupling_list 物理耦合边列表
   * @return 物理比特总数
   * @note 示例：coupling_list = {{0,1},{1,2},{2,3}} -> 返回 4
   */
  static int count_physical_qubits(
      const std::vector<std::pair<int, int>>& coupling_list);

  /**
   * @brief 构建保真度哈希查表，key = p1*num_physical+p2
   * @param coupling_list 物理耦合边列表
   * @param edge_fidelities 与 coupling_list 对应的边保真度
   * @param num_physical 物理比特总数
   * @return 保真度查表，key = ctrl*num_physical+targ
   * @note 示例：边 (0,1) 保真度 0.99，num_physical=4 -> key=1, value=0.99
   */
  static std::unordered_map<size_t, double> build_fidelity_lookup(
      const std::vector<std::pair<int, int>>& coupling_list,
      const std::vector<double>& edge_fidelities, int num_physical);

  /**
   * @brief 从门序列提取两比特门对及其频率
   * @param gates_list 逻辑门序列
   * @return 两比特门对列表，每项包含 (control, target, count)
   * @note 示例：电路含 3 个 CX(0,1) 和 2 个 CX(1,2) ->
   *       [{0,1,3}, {1,2,2}]
   */
  static std::vector<TwoQubitPair> extract_two_qubit_pairs(
      const std::vector<GateOperation>& gates_list);

  /**
   * @brief 计算排列数 P(n, k) = n!/(n-k)!
   * @param num_physical 物理比特数 n
   * @param num_logical 逻辑比特数 k
   * @return P(n,k)，溢出时返回 LLONG_MAX
   * @note 示例：P(10,3) = 720, P(20,5) = 1860480
   */
  static long long count_permutations(int num_physical, int num_logical);

  /**
   * @brief 计算给定映射的目标函数值（log 域）
   * @param placement 逻辑->物理映射，placement[i] 为逻辑 i 对应的物理比特
   * @return log 域得分 = Σ(count * log(fidelity))，不可行时返回 -infinity
   * @note 示例：placement=[0,1,2]，边 (0,1) 保真度 0.99 出现 3 次 ->
   *       score = 3*log(0.99) ≈ -0.0302
   */
  double compute_score(const std::vector<int>& placement) const;

  /**
   * @brief 递归枚举所有排列
   * @param placement [in/out] 当前排列状态
   * @param depth 当前填充位置索引（0 到 num_logical_-1）
   * @param best_score [in/out] 当前最优得分
   * @param best_mapping [in/out] 当前最优映射
   */
  void enumerate_permutations(std::vector<int>& placement, int depth,
                              double& best_score,
                              std::vector<int>& best_mapping) const;

  /**
   * @brief 精确枚举所有排列，返回全局最优映射
   * @return 全局最优的逻辑->物理映射
   * @note 示例：4 物理比特、3 逻辑比特 -> 枚举 P(4,3)=24 种排列，
   *       返回得分最高的映射
   */
  std::vector<int> brute_force_optimal() const;

  /**
   * @brief 在未使用物理比特中为已分配比特找保真度最高的搭档
   * @param fixed_physical 已分配的物理比特 ID
   * @param used 已使用的物理比特标记数组
   * @return 保真度最高的搭档物理比特 ID，找不到返回 -1
   * @note 示例：fixed_physical=2，可用 {0,1,3}，边 (2,1) 保真度最高 -> 返回 1
   */
  int find_best_partner(int fixed_physical,
                        const std::vector<bool>& used) const;

  /**
   * @brief 在未使用物理比特中找保真度最高的一对搭档
   * @param used 已使用的物理比特标记数组
   * @return 保真度最高的 (p1, p2)，找不到返回 (-1, -1)
   * @note 示例：可用 {0,1,2}，边 (0,2) 保真度最高 -> 返回 {0, 2}
   */
  std::pair<int, int> find_best_available_pair(
      const std::vector<bool>& used) const;

  /**
   * @brief 将逻辑比特分配到任意可用物理比特（兜底策略）
   * @param placement [in/out] 逻辑->物理映射
   * @param used [in/out] 已使用的物理比特标记数组
   * @param logical 待分配的逻辑比特 ID
   */
  static void assign_any_available(std::vector<int>& placement,
                                   std::vector<bool>& used, int logical);

  /**
   * @brief 分配所有未放置的逻辑比特
   * @param placement [in/out] 逻辑->物理映射
   * @param used [in/out] 已使用的物理比特标记数组
   * @note 优先按单比特保真度降序分配，无保真度数据时按顺序分配
   */
  void fill_remaining_qubits(std::vector<int>& placement,
                             std::vector<bool>& used) const;

  /**
   * @brief 贪心初始化：按两比特门频率从高到低放置逻辑比特
   * @return 初始映射（逻辑->物理）
   * @note 示例：门频率 CX(0,1)=5, CX(1,2)=3 -> 先放置 {0,1} 到最优物理对，
   *       再为 2 找搭档
   */
  std::vector<int> greedy_initial() const;

  /**
   * @brief 局部搜索优化：交换逻辑比特物理位置，保留提升直到局部最优
   * @param placement 初始映射
   * @return 局部最优映射
   * @note 示例：初始 [0,1,2]，交换 (0,2) 后得分更高 -> 返回 [2,1,0]
   */
  std::vector<int> local_search(std::vector<int> placement) const;

 private:
  std::vector<TwoQubitPair> two_qubit_pairs_;  ///< 两比特门频率表
  std::unordered_map<size_t, double>
      two_qubit_fidelities_;                     ///< 双比特保真度查表
  std::vector<double> single_qubit_fidelities_;  ///< 单比特保真度
  int num_logical_;                              ///< 逻辑比特数
  int num_physical_;                             ///< 物理比特数

  /// 精确枚举的最大排列数，超过则走贪心 + 局部搜索
  static constexpr long long kMaxBruteForcePermutations = 2000000;
};

/**
 * @brief 离子阱噪声自适应初始映射
 *
 * 针对全连通离子阱拓扑，最大化所有两比特门可靠性的几何平均。
 *
 * @param gates_list 逻辑门序列
 * @param coupling_list 物理耦合边（有向，离子阱全连通时包含所有方向）
 * @param edge_fidelities 与 coupling_list 对应的边保真度
 * @param single_qubit_fidelities 按物理比特 ID 索引的单比特保真度
 *        （离子阱中通常为 1.0，log(1.0)=0，不影响结果）
 * @param num_logical 电路声明的逻辑比特总数
 * @return std::vector<int> 逻辑到物理映射，逻辑 i -> 物理 mapping[i]
 */
std::vector<int> ion_trap_layout_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities,
    const std::vector<double>& single_qubit_fidelities, int num_logical);

}  // namespace qcos
