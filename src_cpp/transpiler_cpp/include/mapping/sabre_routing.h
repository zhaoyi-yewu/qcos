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

#include <algorithm>
#include <deque>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "circuit/gate_operation.h"

namespace qcos {

// forward declaration
class SABRE;

bool validate_routing(const SABRE& sabre,
                      const std::vector<GateOperation>& logical_gates,
                      const std::vector<GateOperation>& physical_gates,
                      std::vector<int>& initial_l2p);

/**
 * @brief SABRE算法中的节点结构
 *
 * 每个节点对应一个量子门，并维护其逻辑比特、前驱节点数量、
 * 后继节点以及可以附加执行的单量子比特门。
 */
class Node {
 public:
  Node(const GateOperation& gate_op)
      : gate(gate_op), bits(gate_op.targets), pre_number(0) {}
  /// 当前节点对应的量子门
  GateOperation gate;
  /// 当前门作用的逻辑比特
  std::vector<int> bits;
  /// 当前节点的后继节点
  std::vector<std::shared_ptr<Node>> edges;
  /// 跟随在双量子比特门之后、可以与此节点一起执行的单量子比特门
  std::vector<std::shared_ptr<Node>> attach;
  /// 未执行的前驱节点数量
  int pre_number;
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
   * @param extention_size 扩展集大小，用于lookahead成本计算，默认20
   * @param weight 前沿层与扩展层成本权重，默认0.5
   * @param decay 物理比特衰减系数，默认0.001
   */
  SABRE(const std::vector<std::pair<int, int>>& coupling_list,
        int extention_size = 20, double weight = 0.5, double decay = 0.001);

  /**
   * @brief 执行SABRE算法，将逻辑量子门映射到物理量子门
   * @param gates_list 待映射的逻辑门序列
   * @param initial_l2p 初始逻辑到物理映射(可为空)
   */
  void execute(const std::vector<GateOperation>& gates_list,
               const std::vector<int>& initial_l2p = {});

  /**
   * @brief 将逻辑量子门转换为物理量子门
   * @param logic_gate 逻辑量子门
   * @return GateOperation 对应的物理量子门
   */
  GateOperation phy_gate(const GateOperation& logic_gate);

  /**
   * @brief 获取已经routing完成的物理门序列
   * @return std::vector<GateOperation> 物理门操作列表
   */
  inline std::vector<GateOperation> get_physical_gates() const {
    return phy_exe_gates_;
  }

  friend bool validate_routing(
      const SABRE& sabre, const std::vector<GateOperation>& logical_gates,
      const std::vector<GateOperation>& physical_gates,
      std::vector<int>& initial_l2p);

 private:
  int phy_qubit_num_;   ///< 物理量子比特总数
  int extention_size_;  ///< 扩展深度
  double weight_;       ///< 扩展层权重
  double decay_;        ///< SWAP衰减因子
  std::unordered_map<int, std::unordered_set<int>>
      adj_list_;                                    ///< 物理耦合图邻接表
  std::vector<std::vector<int>> dist_;              ///< 最短路径距离矩阵
  std::vector<int> cur_l2p_;                        ///< 当前逻辑到物理映射
  std::vector<int> cur_p2l_;                        ///< 当前物理到逻辑映射
  std::vector<std::shared_ptr<Node>> front_layer_;  ///< 前沿层节点列表
  std::vector<GateOperation> phy_exe_gates_;        ///< 映射后的物理门序列
  std::vector<int> logic2phy_;                      ///< 最终逻辑到物理映射
  std::vector<int> phy2logic_;                      ///< 最终物理到逻辑映射

  /**
   * @brief 构建物理耦合图
   * @param coupling_list 物理耦合对
   */
  void build_coupling_graph(
      const std::vector<std::pair<int, int>>& coupling_list);

  /**
   * @brief 初始化物理量子比特的最短路径距离矩阵
   */
  void init_distance_matrix();

  /**
   * @brief 判断节点是否可以在当前物理映射上执行
   * @param node 待检查节点
   * @return true 可以执行,false 不可执行
   */
  bool can_execute(const std::shared_ptr<Node>& node);

  /**
   * @brief 获取前沿层可行的SWAP候选
   * @return std::vector<std::pair<int,int>> SWAP候选物理比特对
   */
  std::vector<std::pair<int, int>> obtain_swaps();

  /**
   * @brief 获取候选SWAP对应的临时映射
   * @param edge SWAP对
   * @return std::vector<int> 临时逻辑到物理映射
   */
  std::vector<int> get_temp_mapping(const std::pair<int, int>& edge);

  /**
   * @brief 启发式代价计算
   * @param logic2phy 当前逻辑到物理映射
   * @param h_total 输出总代价
   * @param e_count 输出扩展集节点数量
   * @param front_qubit_gate_map 前沿层中每个逻辑比特影响的节点列表
   * @param extend_qubit_gate_map 扩展层中每个逻辑比特影响的节点列表
   */
  void heuristic_cost(
      const std::vector<int>& logic2phy, double& h_total, int& e_count,
      std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
          front_qubit_gate_map,
      std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
          extend_qubit_gate_map);

  /**
   * @brief 计算候选SWAP对的启发式代价增量
   * @param old_l2p 旧逻辑到物理映射
   * @param new_l2p 新逻辑到物理映射
   * @param swap SWAP对
   * @param extend_size 扩展层深度
   * @param front_qubit_gate_map 前沿层中每个逻辑比特影响的节点列表
   * @param extend_qubit_gate_map 扩展层中每个逻辑比特影响的节点列表
   * @return double 启发式代价增量
   */
  double delta_heuristic_cost(
      const std::vector<int>& old_l2p, const std::vector<int>& new_l2p,
      const std::pair<int, int>& swap, int extend_size,
      std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
          front_qubit_gate_map,
      std::unordered_map<int, std::vector<std::shared_ptr<Node>>>&
          extend_qubit_gate_map);

  /**
   * @brief 获取逻辑量子比特数量
   * @param gates_list 待映射逻辑门序列
   * @return int 最大逻辑量子比特编号+1
   */
  int get_qubit_num_from_ir(
      const std::vector<GateOperation>& gates_list) const;
};

}  // namespace qcos
