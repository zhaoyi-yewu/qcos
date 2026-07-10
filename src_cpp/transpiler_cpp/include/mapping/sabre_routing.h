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
#include "mapping/mapping_utils.h"

namespace qcos {

// forward declaration
class SABRE;

std::vector<int> sabre_initial_mapping(
    const std::vector<GateOperation>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list);

/**
 * @brief 使用SABRE算法对逻辑门序列执行routing。
 *
 * 内部将 measure 门从门序列中分离: measure 不参与路由, 路由后追加到
 * 返回结果末尾(已转为物理 ID)。初始映射由内部调用 sabre_initial_mapping 完成。
 *
 * @param gates_list 待映射的逻辑门序列。
 * @param coupling_list 物理耦合图边列表。
 * @param edge_fidelities 边保真度数组(与 coupling_list 对应),
 * 空则不使用保真度。
 * @param single_qubit_fidelities 单比特保真度数组, 空则不使用。
 * @param fidelity_threshold 保真度阈值, 低于此值的边被过滤(<=0 不过滤), 默认
 * 0.8。
 * @param extension_size 扩展集大小，用于 lookahead 成本计算，默认 20。
 * @param weight 前沿层与扩展层成本权重，默认 0.5。
 * @param decay SWAP 衰减系数，默认 0.001。
 * @return std::vector<std::shared_ptr<BaseOperation>> routing 后的物理门序列。
 */
std::vector<std::shared_ptr<BaseOperation>> sabre_routing(
    const std::vector<std::shared_ptr<BaseOperation>>& gates_list,
    const std::vector<std::pair<int, int>>& coupling_list,
    const std::vector<double>& edge_fidelities = {},
    const std::vector<double>& single_qubit_fidelities = {},
    double fidelity_threshold = 0.8, int extension_size = 20,
    double weight = 0.5, double decay = 0.001);

/**
 * @brief SABRE算法中的节点结构
 *
 * 每个节点对应一个量子门，并维护其逻辑比特、前驱节点数量、
 * 后继节点以及可以附加执行的单量子比特门。
 */
class Node {
 public:
  Node(const GateOperation& gate_op)
      : gate(gate_op), bits(gate_op.targets), pre_number(0), index(-1) {}
  /// 当前节点对应的量子门
  GateOperation gate;
  /// 当前门作用的逻辑比特
  std::vector<int> bits;
  /// 当前节点的后继节点
  std::vector<Node*> edges;
  /// 跟随在双量子比特门之后、可以与此节点一起执行的单量子比特门
  std::vector<Node*> attach;
  /// 未执行的前驱节点数量
  int pre_number;
  /// 节点在pool中的索引
  int index;
};

/**
 * @class SABRE
 * @brief 实现SABRE量子电路映射算法
 *
 * SABRE算法用于将逻辑量子比特映射到物理量子比特，同时尽量减少SWAP门的使用。
 * 支持前沿层(front layer)和扩展层(lookahead set)的启发式代价计算。
 */
class SABRE {
 public:
  /**
   * @brief SABRE算法构造函数
   * @param coupling_list 量子芯片物理耦合关系，每个元素为一对物理量子比特编号
   * @param edge_fidelities 边保真度数组(与coupling_list对应)，空则不使用保真度
   * @param single_qubit_fidelities 单比特保真度数组，空则不使用
   * @param fidelity_threshold 保真度阈值，低于此值的边被过滤(<=0不过滤)
   * @param extension_size 扩展集大小，用于lookahead成本计算，默认20
   * @param weight 前沿层与扩展层成本权重，默认0.5
   * @param decay 物理比特衰减系数，默认0.001
   */
  SABRE(const std::vector<std::pair<int, int>>& coupling_list,
        const std::vector<double>& edge_fidelities = {},
        const std::vector<double>& single_qubit_fidelities = {},
        double fidelity_threshold = 0.8, int extension_size = 20,
        double weight = 0.5, double decay = 0.001);

  /**
   * @brief 执行SABRE算法
   *
   * 内部处理: measure 分离 → 保真度过滤/ID稠密化 → 路由 → measure 追加。
   * 结果通过 get_physical_gates() 获取。
   *
   * @param gates_list 待映射的逻辑门序列(可含 measure)
   */
  void execute(const std::vector<std::shared_ptr<BaseOperation>>& gates_list);

  /**
   * @brief 将逻辑量子门转换为物理量子门
   * @param logic_gate 逻辑量子门
   * @return GateOperation 对应的物理量子门
   */
  GateOperation phy_gate(const GateOperation& logic_gate);

  /**
   * @brief 获取已经routing完成的物理门序列(含measure)
   * @return std::vector<std::shared_ptr<BaseOperation>> 物理门操作列表
   */
  inline const std::vector<std::shared_ptr<BaseOperation>>&
  get_physical_gates() const {
    return phy_exe_gates_;
  }

  /**
   * @brief 获取最终的逻辑->物理映射
   * @return std::vector<int> mapping where index is logical qubit and value is
   * physical qubit
   */
  inline std::vector<int> get_logic2phy() const { return logic2phy_; }

  friend std::vector<int> sabre_initial_mapping(
      const std::vector<GateOperation>& gates_list,
      const std::vector<std::pair<int, int>>& coupling_list);

 private:
  int max_phy_qubit_id_;      ///< 最大物理比特 ID (数组按 ID 索引, 大小为
                              ///< max_phy_qubit_id_+1)
  int active_phy_qubit_num_;  ///< 活跃物理比特数 (耦合图中出现的去重位数)
  int logic_qubit_num_ = 0;   ///< 电路使用的逻辑位数 (含被 measure 引用的位)
  std::vector<std::pair<int, int>> coupling_list_;  ///< 物理耦合边列表
  std::vector<double>
      edge_fidelities_;  ///< 边保真度数组(与coupling_list_对应)
  std::vector<double> single_qubit_fidelities_;  ///< 单比特保真度数组
  double fidelity_threshold_;                    ///< 保真度过滤阈值
  int extension_size_;                           ///< 扩展深度
  double weight_;                                ///< 扩展层权重
  double decay_;                                 ///< SWAP衰减因子
  std::vector<std::vector<int>> adj_list_;       ///< 物理耦合图邻接表
  std::vector<std::vector<bool>> adj_matrix_;    ///< 邻接矩阵(O(1)查询)
  std::vector<std::vector<int>> dist_;           ///< 最短路径距离矩阵
  std::vector<int> cur_l2p_;                     ///< 当前逻辑到物理映射
  std::vector<int> cur_p2l_;                     ///< 当前物理到逻辑映射
  std::vector<Node*> front_layer_;               ///< 前沿层节点列表
  std::vector<std::shared_ptr<BaseOperation>>
      phy_exe_gates_;            ///< 映射后的物理门序列(含measure)
  std::vector<int> logic2phy_;   ///< 最终逻辑到物理映射
  bool did_preprocess_ = false;  ///< 是否做了 ID 稠密化预处理
  PhysicalIdRemap remap_;        ///< 稠密化→原始 ID 映射

  // 预分配的热路径缓冲区
  std::vector<std::pair<int, int>> candidate_swaps_;
  std::vector<std::vector<Node*>> front_qubit_gate_map_;
  std::vector<std::vector<Node*>> extend_qubit_gate_map_;
  std::vector<int> temp_indegree_;
  std::vector<int> touched_indices_;

  /**
   * @brief 构建物理耦合图
   * @param coupling_list 物理耦合对
   */
  void build_coupling_graph(
      const std::vector<std::pair<int, int>>& coupling_list);

  /**
   * @brief 初始化物理量子比特的最短路径距离矩阵
   *
   * 功能：对每个有邻居的物理结点执行BFS，计算到其它结点的最短路径并
   * 填充成员变量`dist_`，用于后续启发式代价评估的O(1)距离查询。
   */
  void init_distance_matrix();

  /**
   * @brief 判断节点是否可以在当前物理映射上执行 (内联,使用邻接矩阵O(1)查询)
   */
  inline bool can_execute(const Node* node) const {
    if (node->bits.size() == 1) return true;
    return adj_matrix_[cur_l2p_[node->bits[0]]][cur_l2p_[node->bits[1]]];
  }

  /**
   * @brief 获取前沿层可行的SWAP候选(输出到预分配向量)
   * @param candidates 输出的候选SWAP列表
   */
  void obtain_swaps(std::vector<std::pair<int, int>>& candidates);

  /**
   * @brief 启发式代价计算(使用预分配的qubit-gate映射)
   * @param logic2phy 输入的逻辑->物理映射（只读）
   * @param h_total 输出：计算得到的启发式总代价
   * @param e_count 输出：实际扩展集中包含的门数量
   *
   * 说明：该函数计算前沿层的平均距离(h_basic)和扩展集合的平均距离(h_extend)，
   * 并将结果合成到`h_total`。同时会填充`front_qubit_gate_map_`与
   * `extend_qubit_gate_map_`，以便`delta_heuristic_cost`在评估候选SWAP时
   * 只遍历受影响节点。函数使用`touched_indices_`对`temp_indegree_`
   * 做增量重置以避免全量清零开销。
   */
  void heuristic_cost(const std::vector<int>& logic2phy, double& h_total,
                      int& e_count);

  /**
   * @brief 计算候选SWAP对的启发式代价增量(无需临时映射向量)
   * @param old_l2p 当前逻辑->物理映射（只读）
   * @param swap 要评估的物理位对(phy_u,phy_v)，总是以(min,max)形式传入
   * @param extend_size 扩展集合的实际大小（用于归一化）
   * @return double 返回应用该swap后的启发式代价增量(delta)
   *
   * 说明：函数不会复制整个映射向量，而是通过按需查询的新映射视图
   * (内部lambda`new_phy`)来计算受影响节点的距离差。仅遍历与
   * `swap`相关的前沿与扩展桶，从而达到增量评估的目的，复杂度与受
   * 影响的节点数成正比。
   */
  double delta_heuristic_cost(const std::vector<int>& old_l2p,
                              const std::pair<int, int>& swap,
                              int extend_size);

  /**
   * @brief 获取逻辑量子比特数量
   * @param gates_list 待映射逻辑门序列
   * @return int 最大逻辑量子比特编号+1
   */
  int get_qubit_num_from_ir(
      const std::vector<GateOperation>& gates_list) const;

  /**
   * @brief 为 cur_l2p_ 中未分配的逻辑位分配物理位
   *
   * 优先分配已分配位的邻居，其次分配耦合图中任意未使用位。
   */
  void extend_l2p_with_unused_qubits(int old_size);

  std::vector<GateOperation> execute_routing(
      const std::vector<GateOperation>& gates_list,
      const std::vector<int>& initial_l2p);
};

}  // namespace qcos
