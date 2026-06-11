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

#include <functional>
#include <memory>
#include <string>
#include <tuple>
#include <unordered_map>
#include <vector>

#include "circuit/dag_node.h"

namespace qcos {

/**
 * @brief 有向边，target 表示相邻节点 id，wire 表示边承载的线路编号
 */
struct Edge {
  int target;
  int wire;
};

/**
 * @class MultiGraph
 * @brief 面向 DAGCircuit 的轻量有向多重图
 *
 * 图以内存槽位保存节点对象及其入边、出边信息。
 */
class MultiGraph {
 public:
  /**
   * @brief 追加一个节点并返回节点 id
   * @param node 待加入图中的节点对象
   * @return int 新节点 id
   */
  int add_node(std::unique_ptr<DAGNode> node);

  /**
   * @brief 成对追加两个节点并返回两个节点 id
   * @param first 第一个节点
   * @param second 第二个节点
   * @return std::pair<int, int> 节点 id 对，顺序与参数一致
   */
  std::pair<int, int> add_nodes(std::unique_ptr<DAGNode> first,
                                std::unique_ptr<DAGNode> second);

  /**
   * @brief 在两个已存在节点之间添加一条有向边
   * @param src 源节点 id
   * @param dst 目标节点 id
   * @param wire 边关联的线路编号
   */
  void add_edge(int src, int dst, int wire);

  /**
   * @brief 判断两个节点之间是否存在至少一条边
   * @param src 源节点 id
   * @param dst 目标节点 id
   * @return true 存在边
   * @return false 不存在边或节点无效
   */
  bool has_edge(int src, int dst) const;

  /**
   * @brief 返回当前活跃节点数量
   * @return int 活跃节点数量
   */
  int num_nodes() const { return num_active_; }

  /**
   * @brief 通过节点 id 访问当前活跃节点对象
   * @param id 节点 id
   * @return DAGNode* 节点裸指针，节点无效或已删除时返回 nullptr
   */
  DAGNode* operator[](int id);

  /**
   * @brief 通过节点 id 只读访问当前活跃节点对象
   * @param id 节点 id
   * @return const DAGNode* 节点裸指针，节点无效或已删除时返回 nullptr
   */
  const DAGNode* operator[](int id) const;

  /**
   * @brief 返回图中的全部活跃节点
   * @return std::vector<DAGNode*> 节点列表
   */
  std::vector<DAGNode*> nodes() const;

  /**
   * @brief 返回给定节点的所有后继节点
   * @param node_id 节点 id
   * @return std::vector<DAGNode*> 后继节点列表
   */
  std::vector<DAGNode*> successors(int node_id) const;

  /**
   * @brief 返回给定节点的所有前驱节点
   * @param node_id 节点 id
   * @return std::vector<DAGNode*> 前驱节点列表
   */
  std::vector<DAGNode*> predecessors(int node_id) const;

  /**
   * @brief 返回给定节点的所有后继节点 id
   * @param node_id 节点 id
   * @return std::vector<int> 后继节点 id 列表
   */
  std::vector<int> successor_indices(int node_id) const;

  /**
   * @brief 返回给定节点的所有前驱节点 id
   * @param node_id 节点 id
   * @return std::vector<int> 前驱节点 id 列表
   */
  std::vector<int> predecessor_indices(int node_id) const;

  /**
   * @brief 返回节点的全部出边三元组
   * @param node_id 节点 id
   * @return std::vector<std::tuple<int, int, int>> (src, dst, wire) 列表
   */
  std::vector<std::tuple<int, int, int>> out_edges(int node_id) const;

  /**
   * @brief 在后继节点中返回第一条满足线路谓词的节点
   * @param node_id 起始节点 id
   * @param predicate 边线路过滤条件
   * @return DAGNode* 首个满足条件的后继节点，找不到时为空
   */
  DAGNode* find_first_successor_by_edge(
      int node_id, const std::function<bool(int)>& predicate) const;

  /**
   * @brief 返回所有满足线路谓词的前驱节点
   * @param node_id 节点 id
   * @param predicate 边线路过滤条件
   * @return std::vector<DAGNode*> 匹配的前驱节点列表
   */
  std::vector<DAGNode*> find_predecessors_by_edge(
      int node_id, const std::function<bool(int)>& predicate) const;

  /**
   * @brief 返回所有满足线路谓词的后继节点
   * @param node_id 节点 id
   * @param predicate 边线路过滤条件
   * @return std::vector<DAGNode*> 匹配的后继节点列表
   */
  std::vector<DAGNode*> find_successors_by_edge(
      int node_id, const std::function<bool(int)>& predicate) const;

  /**
   * @brief 将新节点插入到多个目标节点的所有入边之前
   * @param new_node_id 新节点 id
   * @param target_ids 需要被改写入边的目标节点 id 列表
   */
  void insert_node_on_in_edges_multiple(int new_node_id,
                                        const std::vector<int>& target_ids);

  /**
   * @brief 将新节点插入到多个源节点的所有出边之后
   * @param new_node_id 新节点 id
   * @param source_ids 需要被改写出边的源节点 id 列表
   */
  void insert_node_on_out_edges_multiple(int new_node_id,
                                         const std::vector<int>& source_ids);

  /**
   * @brief 将新节点插入到指定源节点在指定线路的出边之后
   * @param new_node_id 新节点 id
   * @param source_id 源节点 id
   * @param wire 指定线路
   */
  void insert_node_on_out_edge(int new_node_id, int source_id, int wire);

  /**
   * @brief 将新节点插入到指定目标节点在指定线路的入边之前
   * @param new_node_id 新节点 id
   * @param target_id 目标节点 id
   * @param wire 指定线路
   */
  void insert_node_on_in_edge(int new_node_id, int target_id, int wire);

  /**
   * @brief 删除节点，并按同一 wire 直连其前驱和后继
   * @param node_id 待删除节点 id
   */
  void remove_node_retain_edges(int node_id);

  /**
   * @brief 按给定 key 执行字典序拓扑排序
   * @param key 将节点映射为排序键的函数
   * @return std::vector<DAGNode*> 排序后的节点列表
   */
  std::vector<DAGNode*> lexicographical_topological_sort(
      const std::function<std::string(const DAGNode*)>& key) const;

  /**
   * @brief 计算 DAG 中最长路径长度，单位为边数
   * @return int 最长路径长度
   */
  int dag_longest_path_length() const;

  /**
   * @brief 返回 DAG 中的一条最长路径
   * @return std::vector<int> 路径上的节点 id 列表
   */
  std::vector<int> dag_longest_path() const;

  /**
   * @brief 收集所有连续的匹配运行段
   * @param filter_fn 节点过滤函数，返回 true 表示该节点可加入运行段
   * @return std::vector<std::vector<DAGNode*>> 运行段列表
   */
  std::vector<std::vector<DAGNode*>> collect_runs(
      const std::function<bool(const DAGNode*)>& filter_fn) const;

 private:
  /**
   * @brief 节点槽位，集中保存节点对象及其局部邻接信息
   */
  struct NodeSlot {
    std::unique_ptr<DAGNode> node;
    std::vector<Edge> out_edges;
    std::vector<Edge> in_edges;
    bool active = false;
  };

  /**
   * @brief 返回节点 id 的一个拓扑序
   * @return std::vector<int> 拓扑序节点 id 列表
   */
  std::vector<int> topo_order() const;

  /**
   * @brief 复制一个 DAGNode 对象
   * @param node 待复制节点
   * @return std::unique_ptr<DAGNode> 复制后的新节点
   */
  static std::unique_ptr<DAGNode> clone_node(const DAGNode* node);

  std::vector<NodeSlot> slots_;
  int num_active_ = 0;
};

}  // namespace qcos
