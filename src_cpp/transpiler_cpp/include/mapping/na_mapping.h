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
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @struct NAQpuConfig
 * @brief 中性原子 QPU 拓扑配置
 *
 * 对应 Python 侧 qpu_config 中与 NA mapping 相关的字段。位置以字符串
 * 形式表示（如 "S27"、"P100"），与 Python 实现保持一致。
 */
struct NAQpuConfig {
  /// 存储区位置列表
  std::vector<std::string> storage_area;
  /// 操作区位置列表
  std::vector<std::string> operate_area;
  /// 耦合器映射：门名 -> (端点A, 端点B)
  std::vector<std::pair<std::string, std::pair<std::string, std::string>>>
      coupler_map;
  /// 读出错误率：位置 -> 错误值
  std::unordered_map<std::string, double> readout_error;
};

/**
 * @struct NAGraph
 * @brief 中性原子操作区耦合图
 *
 * 仅包含两端均在 operate_area 中的边，提供邻接查询与全源最短路径距离
 * 查询（对应 Python 实现中 networkx 的 shortest_path_length）。
 */
struct NAGraph {
  /// 邻接表：位置 -> 相邻位置集合
  std::unordered_map<std::string, std::unordered_set<std::string>> adj;
  /// 位置 -> (位置 -> 最短路径距离) 的全源距离表
  std::unordered_map<std::string, std::unordered_map<std::string, int>>
      shortest_length;

  /// 添加一条无向边
  void add_edge(const std::string& a, const std::string& b);

  /// 返回某位置的全部邻居
  const std::unordered_set<std::string>& neighbors(
      const std::string& p) const;

  /// 判断两个位置是否直接相邻
  bool is_adjacent(const std::string& a, const std::string& b) const;

  /// 计算全源最短路径距离（BFS），填充 shortest_length
  void build_shortest_length();
};

/**
 * @struct NADagNode
 * @brief NA routing 依赖图节点
 *
 * 对应 Python 实现中 rustworkx DAG 节点。单比特门节点会把可合并的连续单
 * 比特门聚合到 gate 列表中；两比特门节点仅持有一个门。
 */
struct NADagNode {
  /// 节点包含的门列表（单比特门可能为多个，两比特门仅一个）
  std::vector<std::shared_ptr<BaseOperation>> gate;
  /// 节点涉及的逻辑比特
  std::vector<int> qubits;
  /// 节点类型：single 或 multi
  std::string type;
  /// 对应原始门序列中的索引
  int original_idx = -1;
  /// 后继节点索引列表
  std::vector<int> successors;
  /// 未执行的前驱数量
  int in_degree = 0;
};

/**
 * @class NASingleRoute
 * @brief 中性原子单比特路由（仅支持单比特门）
 *
 * 对应 Python 侧 NASingleRoute，将逻辑量子比特按读出错误率从小到大
 * 映射到存储区，并按量子比特分组输出门序列。
 */
class NASingleRoute {
 public:
  NASingleRoute() = default;

  /**
   * @brief 配置 qpu_config、gates、qbit_num，并构建逻辑比特到存储区映射
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAQpuConfig& qpu_config);

  /**
   * @brief 遍历比特门，将逻辑量子比特映射到物理量子比特
   * @return (映射后的门列表, final_layout)，final_layout 始终为空
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order();

  /// 逻辑比特 -> 存储区位置
  std::unordered_map<int, std::string> logical_to_storage;

 protected:
  NAQpuConfig qpu_config_;
  NAGraph ag_;
  std::vector<std::shared_ptr<BaseOperation>> gates_;
  int qbit_num_ = 0;
};

/**
 * @class NARoute
 * @brief 中性原子路由（支持单/两比特门与 MOVE 操作）
 *
 * 对应 Python 侧 NARoute，在操作区与存储区之间移动原子，使两比特门的两
 * 个比特处于相邻位置后执行。支持按拓扑序执行（execute_with_order）与
 * overlap 优化执行（execute_with_opt）。
 */
class NARoute {
 public:
  NARoute() = default;

  /**
   * @brief 配置 qpu_config、gates、qbit_num，并构建耦合图
   */
  void prepare_data(int qbit_num,
                    const std::vector<std::shared_ptr<BaseOperation>>& gates,
                    const NAQpuConfig& qpu_config);

  /**
   * @brief 按顺序执行门，不进行优化
   * @return (映射后的门列表, final_layout)，final_layout 始终为空
   */
  std::pair<std::vector<std::shared_ptr<BaseOperation>>,
            std::unordered_map<int, int>>
  execute_with_order();

  /**
   * @brief 按拓扑序执行门，进行简单的 overlap 优化
   * @return 映射后的门列表
   */
  std::vector<std::shared_ptr<BaseOperation>> execute_with_opt();

  /**
   * @brief 构建 DAG，返回 (DAG 节点列表, 测量操作列表, 原始索引->DAG索引映射)
   */
  std::tuple<std::vector<NADagNode>,
             std::vector<std::shared_ptr<BaseOperation>>,
             std::unordered_map<int, int>>
  get_rx_dag();

  /// 比特初始映射及映射表构建
  void get_init_mapping();

  /// 获取当前可执行的节点（入度为 0）
  std::vector<int> get_front_layer() const;

  /// 在操作区中寻找可放置比特的位置，若不存在则返回空
  std::string find_pos(int dis) const;

  /// 将比特移回存储区，并更新映射表
  void back(const std::string& o);

  /// 将比特移到操作区，并更新映射表
  void put(int q, const std::string& o);

  /// 将比特从操作区某一位置移到另一位置，并更新映射表
  void mov(const std::string& o1, const std::string& o2);

  /// 将操作区中不属于当前可执行门的比特移回存储区
  void pre_back(const std::vector<NADagNode>& nodes);

  /// 获取操作区某一位置的相邻空位置，若不存在则返回空
  std::string get_empty_neighbor(const std::string& p) const;

  /// 获取操作区某一位置的相邻非上锁位置，若不存在则返回空
  std::string get_unlocked_neighbor(const std::string& p) const;

  /// 将比特1和比特2移到相邻位置（两者均已在操作区）
  bool mov_to_neighbors(const std::string& p1, const std::string& p2);

  /// 将 q 放到 p1 的相邻位置（q 在存储区）
  bool put_to_neighbors1(const std::string& p1, int q);

  /// 将比特 q1、q2 放到相邻位置（两者均在存储区）
  bool put_to_neighbors2(int q1, int q2);

  /// 执行两比特门
  void execute_multi_nodes(const std::vector<NADagNode>& nodes);

  /// 两比特门执行前，将比特先放置在操作区合适的位置
  std::vector<NADagNode> mov_multi_nodes(const std::vector<NADagNode>& nodes);

  /// 执行单比特门
  void execute_single_node(const NADagNode& node);

  /// 判断两个单比特节点的门列表是否满足 nd2 为 nd1 的后缀
  bool overlap(int nd1, int nd2) const;

  /// 将 overlap 中的 put 操作放入对应的位置
  std::vector<std::shared_ptr<BaseOperation>> add_put(
      std::vector<std::shared_ptr<BaseOperation>> res,
      std::shared_ptr<BaseOperation> opt);

  /// 调整 put 操作的位置，调用 add_put，放入合适的位置
  void adjust_pos(const std::vector<int>& pos,
                  const std::vector<int>& posq);

  /// 执行单比特门，通过 overlap 进行优化
  void execute_single_node_opt();

  /// 从当前可执行节点中找可执行的节点
  std::pair<int, std::vector<int>> get_max_common();

  /// 逻辑比特 -> 存储区位置
  std::unordered_map<int, std::string> logical_to_storage;
  /// 逻辑比特 -> 操作区位置（无映射时为空字符串）
  std::unordered_map<int, std::string> logical_to_op;
  /// 操作区位置 -> 逻辑比特（无映射时为 -1）
  std::unordered_map<std::string, int> op_to_logical;
  /// 初始映射（始终为空，与 Python 实现保持一致）
  std::unordered_map<int, int> initial_layout;

 private:
  NAQpuConfig qpu_config_;
  NAGraph ag_;
  std::vector<std::shared_ptr<BaseOperation>> gates_;
  int qbit_num_ = 0;

  std::vector<NADagNode> dag_;
  std::vector<NADagNode> dag_opt_;
  std::vector<std::shared_ptr<BaseOperation>> measure_;
  std::unordered_map<int, int> node_indices_;
  std::unordered_set<std::string> op_occupied_;
  /// 两端均空闲的边集合，以 "min\0max" 形式存储（保证有序与去重）
  std::unordered_set<std::string> free_edges_;
  std::unordered_set<std::string> locked_;
  std::vector<std::shared_ptr<BaseOperation>> res_;
  std::vector<int> front_layer_;
  /// 上一个执行的节点索引（对应 Python self.pre_node，原为节点 dict，
  /// 这里统一用索引并在需要时通过 dag_ 查询节点数据）
  int pre_node_idx_ = -1;
  bool has_pre_node_ = false;

  /// Move 门 -> (源位置, 目标位置)，承载位置字符串
  /// （C++ BaseOperation.arg_value 为 double，无法直接存储位置字符串）
  std::unordered_map<BaseOperation*, std::pair<std::string, std::string>>
      move_positions_;

  /// 将 (a, b) 规整为 (min, max) 的有序对
  static std::pair<std::string, std::string> sorted_edge(const std::string& a,
                                                         const std::string& b);

  /// 将有序对编码为 free_edges_ 的 key
  static std::string edge_key(const std::string& a, const std::string& b);

  /// 从 key 解析出有序对
  static std::pair<std::string, std::string> parse_edge_key(
      const std::string& key);

  /// 创建一个 Move 操作并登记其位置对
  std::shared_ptr<BaseOperation> make_move(int q, const std::string& from,
                                           const std::string& to);

  /// 依据 logical_to_storage 重新计算并设置各门 targets / arg_value
  /// （对应 Python 末尾的逻辑->物理转换）
  void finalize_gates(bool deep_copy_layout);

  /// 从 dag_opt_ 中移除指定节点：清空其门、并将后继节点入度减 1
  /// （对应 rustworkx 的 remove_node）
  void remove_dag_opt_node(int idx);
};

}  // namespace qcos
