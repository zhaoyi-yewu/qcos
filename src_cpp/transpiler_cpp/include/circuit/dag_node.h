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
#include <vector>

#include "circuit/base_operation.h"

namespace qcos {

/**
 * @class DAGNode
 * @brief DAG 中所有节点类型的公共基类
 */
class DAGNode {
 public:
  /**
   * @brief 使用给定编号构造节点
   * @param nid 节点编号
   */
  explicit DAGNode(int nid = -1) : node_id_(nid) {}
  virtual ~DAGNode() = default;

  /**
   * @brief 返回节点编号
   * @return int 节点编号
   */
  int node_id() const { return node_id_; }

  /**
   * @brief 设置节点编号
   * @param nid 节点编号
   */
  void set_node_id(int nid) { node_id_ = nid; }

  bool operator<(const DAGNode& other) const {
    return node_id_ < other.node_id_;
  }
  bool operator>(const DAGNode& other) const {
    return node_id_ > other.node_id_;
  }

  /**
   * @brief 返回用于字典序拓扑排序的排序键
   * @return std::string 排序键
   */
  virtual std::string sort_key() const { return ""; }

 protected:
  int node_id_;
};

/**
 * @class DAGOpNode
 * @brief 表示量子门操作的 DAG 节点
 */
class DAGOpNode : public DAGNode {
 public:
  /**
   * @brief 构造操作节点
   * @param op 门操作对象
   * @param qargs 量子位参数
   * @param cargs 经典位参数
   */
  DAGOpNode(std::shared_ptr<BaseOperation> op, std::vector<int> qargs = {},
            std::vector<int> cargs = {});

  /**
   * @brief 返回门操作名称
   * @return const std::string& 门操作名称
   */
  const std::string& name() const { return op->name; }

  /**
   * @brief 更新门操作名称
   * @param new_name 新名称
   */
  void set_name(const std::string& new_name) { op->name = new_name; }

  /**
   * @brief 返回操作节点的排序键
   * @return std::string 排序键
   */
  std::string sort_key() const override { return sort_key_; }

  /**
   * @brief 生成便于调试的字符串表示
   * @return std::string 节点描述字符串
   */
  std::string repr() const;

  /// 当前节点承载的门操作对象
  std::shared_ptr<BaseOperation> op;
  /// 门操作作用到的量子位列表
  std::vector<int> qargs;
  /// 门操作作用到的经典位列表
  std::vector<int> cargs;
  /// 外部算法使用的辅助标记位
  int flag = 0;

 private:
  std::string sort_key_;
};

/**
 * @class DAGInNode
 * @brief 表示某条线路输入端的 DAG 节点
 */
class DAGInNode : public DAGNode {
 public:
  /**
   * @brief 构造输入节点
   * @param wire 所属线路编号
   */
  explicit DAGInNode(int wire) : DAGNode(), wire_(wire) {}

  /**
   * @brief 返回节点所属线路编号
   * @return int 线路编号
   */
  int wire() const { return wire_; }

  /**
   * @brief 返回固定排序键
   * @return std::string 固定值 "[]"
   */
  std::string sort_key() const override { return "[]"; }

 private:
  int wire_;
};

/**
 * @class DAGOutNode
 * @brief 表示某条线路输出端的 DAG 节点
 */
class DAGOutNode : public DAGNode {
 public:
  /**
   * @brief 构造输出节点
   * @param wire 所属线路编号
   */
  explicit DAGOutNode(int wire) : DAGNode(), wire_(wire) {}

  /**
   * @brief 返回节点所属线路编号
   * @return int 线路编号
   */
  int wire() const { return wire_; }

  /**
   * @brief 返回固定排序键
   * @return std::string 固定值 "[]"
   */
  std::string sort_key() const override { return "[]"; }

 private:
  int wire_;
};

}  // namespace qcos
