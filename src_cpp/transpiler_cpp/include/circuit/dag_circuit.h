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
#include <map>
#include <memory>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include "circuit/dag_node.h"
#include "circuit/multi_graph.h"

namespace qcos {

class QuantumCircuit;

/**
 * @class DAGCircuit
 * @brief 用有向无环图表示量子线路
 */
class DAGCircuit {
 public:
  /**
   * @brief DAG 中的一条有向边三元组
   */
  struct EdgeTriple {
    /// 边的源节点
    DAGNode* src;
    /// 边的目标节点
    DAGNode* dst;
    /// 边关联的线路编号
    int wire;
  };

  /**
   * @brief 构造一个空 DAG 线路
   */
  DAGCircuit();

  /**
   * @brief 为 DAG 初始化 num_qubits 个比特的量子线路
   * @param num_qubits 需要初始化的量子位数量
   */
  void add_qubits(int num_qubits);

  /**
   * @brief 返回 DAG 中的比特编号列表
   * @return const std::vector<int>& 当前实现下按升序保存的连续比特编号
   */
  const std::vector<int>& wires() const { return qubits_; }

  /**
   * @brief 返回当前活跃节点数量
   * @return int 活跃节点个数
   */
  int node_counter() const { return multi_graph_.num_nodes(); }

  /**
   * @brief 将 DAG 中的门操作从 old_op 重命名为 new_op，并同步更新门计数
   * @param old_op 重命名前的门操作对象
   * @param new_op 重命名后的门操作对象
   */
  void rename_op(const std::shared_ptr<BaseOperation>& old_op,
                 const std::shared_ptr<BaseOperation>& new_op);

  /**
   * @brief 将所有 S、SDG、T、TDG、Z 门转换为 RZ 门
   */
  void parameterize_all_rz();

  /**
   * @brief 将可精确映射的 RZ 门还原为离散相位门
   * @param tolerance 判断角度是否接近 pi/4 整数倍的容差
   */
  void deparameterize_all_rz(double tolerance = 1e-8);

  /**
   * @brief 在线路尾部插入一个门操作
   * @param op 待插入门操作
   * @param qargs 作用线路列表，留空时使用 op->targets
   * @return DAGOpNode* 新增门操作对应的 DAG 节点
   */
  DAGOpNode* apply_operation_back(std::shared_ptr<BaseOperation> op,
                                  std::vector<int> qargs = {});

  /**
   * @brief 在线路头部插入一个门操作
   * @param op 待插入门操作
   * @param qargs 作用线路列表，留空时使用 op->targets
   * @return DAGOpNode* 新增门操作对应的 DAG 节点
   */
  DAGOpNode* apply_operation_front(std::shared_ptr<BaseOperation> op,
                                   std::vector<int> qargs = {});

  /**
   * @brief 返回 DAG 中的门操作数量
   * @return int 门操作个数
   */
  int size() const;

  /**
   * @brief 返回 DAG 深度
   * @return int 最长依赖路径上的操作层数
   */
  int depth() const;

  /**
   * @brief 返回 DAG 宽度
   * @return int 线路数量
   */
  int width() const;

  /**
   * @brief 返回某条线路上的节点序列
   * @param wire 线路编号
   * @param only_ops 为 true 时仅返回门操作对应节点
   * @return std::vector<DAGNode*> 线路上的节点列表
   */
  std::vector<DAGNode*> nodes_on_wire(int wire, bool only_ops = false);

  /**
   * @brief 按给定排序键返回全部节点的字典序拓扑序
   * @param key 自定义排序键函数，留空时使用节点默认排序键
   * @return std::vector<DAGNode*> 拓扑有序的节点列表
   */
  std::vector<DAGNode*> topological_nodes(
      std::function<std::string(const DAGNode*)> key = {});
  std::vector<const DAGNode*> topological_nodes(
      std::function<std::string(const DAGNode*)> key = {}) const;

  /**
   * @brief 按给定排序键返回全部门操作的字典序拓扑序
   * @param key 自定义排序键函数，留空时使用节点默认排序键
   * @return std::vector<DAGOpNode*> 拓扑有序的门操作列表
   */
  std::vector<DAGOpNode*> topological_op_nodes(
      std::function<std::string(const DAGNode*)> key = {});
  std::vector<const DAGOpNode*> topological_op_nodes(
      std::function<std::string(const DAGNode*)> key = {}) const;

  /**
   * @brief 通过节点 id 访问节点对象
   * @param node_id 节点编号
   * @return DAGNode* 节点对象，若节点已删除则为空
   */
  DAGNode* node(int node_id);
  const DAGNode* node(int node_id) const;

  /**
   * @brief 返回当前所有活跃节点
   * @return std::vector<DAGNode*> 活跃节点列表
   */
  std::vector<DAGNode*> nodes();

  /**
   * @brief 返回当前所有活跃门操作
   * @return std::vector<DAGOpNode*> 门操作列表
   */
  std::vector<DAGOpNode*> op_nodes();

  /**
   * @brief 返回所有双量子位门操作
   * @return std::vector<DAGOpNode*> 双量子位门操作列表
   */
  std::vector<DAGOpNode*> two_qubit_ops();

  /**
   * @brief 返回所有三量子位及以上的门操作
   * @return std::vector<DAGOpNode*> 多量子位门操作列表
   */
  std::vector<DAGOpNode*> multi_qubit_ops();

  /**
   * @brief 返回 DAG 中的一条最长路径
   * @return std::vector<DAGNode*> 最长路径节点列表
   */
  std::vector<DAGNode*> longest_path();

  /**
   * @brief 返回指定节点的直接后继节点
   * @param node 查询起点
   * @return std::vector<DAGNode*> 后继节点列表
   */
  std::vector<DAGNode*> successors(const DAGNode* node) const;

  /**
   * @brief 返回指定节点的直接前驱节点
   * @param node 查询目标
   * @return std::vector<DAGNode*> 前驱节点列表
   */
  std::vector<DAGNode*> predecessors(const DAGNode* node) const;

  /**
   * @brief 判断一个节点是否是另一个节点的直接后继
   * @param node 起始节点
   * @param node_succ 待判断的后继节点
   * @return true node_succ 是 node 的直接后继
   * @return false node_succ 不是 node 的直接后继
   */
  bool is_successor(const DAGNode* node, const DAGNode* node_succ);

  /**
   * @brief 判断一个节点是否是另一个节点的直接前驱
   * @param node 目标节点
   * @param node_pred 待判断的前驱节点
   * @return true node_pred 是 node 的直接前驱
   * @return false node_pred 不是 node 的直接前驱
   */
  bool is_predecessor(const DAGNode* node, const DAGNode* node_pred);

  /**
   * @brief 返回指定节点的全部祖先节点
   * @param node 目标节点
   * @return std::set<DAGNode*> 祖先节点集合
   */
  std::set<DAGNode*> ancestors(const DAGNode* node);

  /**
   * @brief 返回指定节点的全部后代节点
   * @param node 起始节点
   * @return std::set<DAGNode*> 后代节点集合
   */
  std::set<DAGNode*> descendants(const DAGNode* node);

  /**
   * @brief 删除一个门操作节点，并在同一 wire 上保留连通性
   * @param node 待删除的门操作节点
   */
  void remove_op_node(DAGOpNode* node);

  /**
   * @brief 将一组节点替换为一个子电路 DAG
   *
   * 删除 block_nodes 中的节点（保留同 wire 连通性），
   * 然后将 replacement_dag 按拓扑序插入到原位置。
   *
   * @param block_nodes 待删除的节点块
   * @param replacement_dag 替换子电路
   * @param qubit_mapping replacement_dag 的 wire -> 当前 circuit wire 的映射
   */
  void replace_block_with_dag(
      const std::vector<DAGOpNode*>& block_nodes,
      const DAGCircuit& replacement_dag,
      const std::unordered_map<int, int>& qubit_mapping);

  /**
   * @brief 收集所有由给定门名组成的连续运行段
   *
   * @param namelist 允许出现在运行段中的门名列表
   * @param topo_order 预计算的拓扑序节点 id 列表指针，为 nullptr
   * 时内部自动计算
   * @return std::set<std::vector<DAGNode*>> 运行段集合
   */
  std::set<std::vector<DAGNode*>> collect_runs(
      const std::vector<std::string>& namelist,
      const std::vector<int>* topo_order = nullptr);

  /**
   * @brief 统计各类门操作数量
   * @return std::unordered_map<std::string, int> 门名到数量的映射
   */
  std::unordered_map<std::string, int> count_ops() const;

  /**
   * @brief 将操作 IR 序列转换为 DAGCircuit
   * @param ir 操作 IR 序列
   * @return DAGCircuit 构造后的 DAG
   */
  static DAGCircuit ir_to_dag(
      const std::vector<std::shared_ptr<BaseOperation>>& ir);

  /**
   * @brief 将 QuantumCircuit 转换为 DAGCircuit
   * @param circ 源量子线路
   * @return DAGCircuit 构造后的 DAG
   */
  static DAGCircuit circuit_to_dag(const QuantumCircuit& circ);

  /**
   * @brief 将 DAGCircuit 转换回 QuantumCircuit
   * @param num_qubits 返回线路的显式量子位数量，留空时保留 DAG 宽度
   * @return std::unique_ptr<QuantumCircuit> 新建量子线路对象
   */
  std::unique_ptr<QuantumCircuit> dag_to_circuit(int num_qubits = 0);

  /**
   * @brief 提取全部双量子位操作并构造新的 DAG
   * @return DAGCircuit 仅包含双量子位门的新 DAG
   */
  DAGCircuit two_qubit_ops_to_dag();

  /**
   * @brief 将 DAG 按拓扑层拆分为多个子 DAG
   *
   * 使用 BFS + Kahn 算法计算拓扑层（同层内门无依赖、可并行执行），
   * 然后将连续若干层合并为一个子 DAG。
   *
   * @param num_chunks 目标拆分块数，实际块数可能略少
   * @return std::vector<DAGCircuit> 子 DAG 列表，按拓扑序排列
   */
  std::vector<DAGCircuit> split_by_layers(int num_chunks);

  /**
   * @brief 返回 DAG 的拓扑层划分（每层内的门可并行执行）
   *
   * 算法：BFS + Kahn，同层节点间无依赖关系。
   * 第 0 层为 InNode 哨兵，最后一层为 OutNode 哨兵，
   * 中间层只包含 DAGOpNode。
   *
   * @return std::vector<std::vector<DAGOpNode*>> 按层排列的门操作列表
   */
  std::vector<std::vector<DAGOpNode*>> layers() const;

  /**
   * @brief 返回指定节点集合的全部出边三元组
   * @param nodes_ptr 可选节点列表指针，留空时遍历全部活跃节点
   * @return std::vector<EdgeTriple> 出边三元组列表
   */
  std::vector<EdgeTriple> edges(
      const std::vector<DAGNode*>* nodes_ptr = nullptr);

  /**
   * @brief 返回底层多重图对象
   * @return MultiGraph& 底层图的可写引用
   */
  MultiGraph& get_multi_graph() { return multi_graph_; }

  /**
   * @brief 返回底层多重图对象的只读引用
   * @return const MultiGraph& 底层图的只读引用
   */
  const MultiGraph& get_multi_graph() const { return multi_graph_; }

  /**
   * @brief 返回输入节点映射
   * @return const std::map<int, DAGInNode*>& wire
   * 到输入节点的映射
   */
  const std::map<int, DAGInNode*>& get_input_map() const { return input_map; }

  /**
   * @brief 返回输出节点映射
   * @return const std::map<int, DAGOutNode*>& wire
   * 到输出节点的映射
   */
  const std::map<int, DAGOutNode*>& get_output_map() const {
    return output_map;
  }

  std::string name;

  /**
   * @brief 增加某类门操作的计数
   * @param op 待统计的操作对象
   */
  void increment_op(const std::shared_ptr<BaseOperation>& op);

  /**
   * @brief 减少某类门操作的计数
   * @param op 待统计的操作对象
   */
  void decrement_op(const std::shared_ptr<BaseOperation>& op);

 private:
  /**
   * @brief 为单条线路创建输入节点、输出节点及直连边
   * @param wire 线路编号
   */
  void add_wire(int wire);

  /**
   * @brief 根据操作列表构建 DAG 主体结构
   * @param ops 操作列表
   */
  void build_from_operations(
      const std::vector<std::shared_ptr<BaseOperation>>& ops);

  std::vector<int> qubits_;
  std::set<int> wires_set_;
  std::map<int, DAGInNode*> input_map;
  std::map<int, DAGOutNode*> output_map;
  MultiGraph multi_graph_;
  std::unordered_map<std::string, int> op_names_;
};

}  // namespace qcos
