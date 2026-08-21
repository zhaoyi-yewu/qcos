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
#include <stdexcept>

#include "circuit/base_operation.h"

namespace qcos {

/**
 * @class QuantumCircuit
 * @brief 量子线路，按顺序保存门操作
 */
class QuantumCircuit {
 public:
  /**
   * @brief 构造量子线路
   * @param num_qubits 量子位数量
   * @param num_clbits 经典位数量
   * @param global_phase 全局相位
   */
  explicit QuantumCircuit(int num_qubits = 0, int num_clbits = 0,
                          double global_phase = 0.0);

  /**
   * @brief 由 IR 序列构造量子线路
   * @param ir 操作 IR 序列
   * @param num_qubits 可选显式量子位数量
   * @return std::shared_ptr<QuantumCircuit> 新建线路对象
   */
  static std::shared_ptr<QuantumCircuit> from_ir(
      const std::vector<std::shared_ptr<BaseOperation>>& ir,
      int num_qubits = 0);

  /**
   * @brief 在线路末尾追加一个操作
   * @param operation 待追加操作
   */
  void append(std::shared_ptr<BaseOperation> operation);

  /**
   * @brief 在线路末尾批量追加操作
   * @param operations 待追加操作列表
   */
  void append_operations(
      const std::vector<std::shared_ptr<BaseOperation>>& operations);

  /**
   * @brief 返回当前操作序列
   * @return const std::vector<std::shared_ptr<BaseOperation>>& 操作列表
   */
  const std::vector<std::shared_ptr<BaseOperation>>& get_operations() const {
    return operations_;
  }

  /**
   * @brief 返回量子位数量
   * @return int 量子位数量
   */
  int num_qubits() const { return num_qubits_; }

  /**
   * @brief 返回经典位数量
   * @return int 经典位数量
   */
  int num_clbits() const { return num_clbits_; }

  /**
   * @brief 返回全局相位
   * @return double 全局相位
   */
  double global_phase() const { return global_phase_; }

  /**
   * @brief 设置全局相位
   * @param phase 新相位值
   */
  void set_global_phase(double phase) { global_phase_ = phase; }

  /**
   * @brief 设置量子位数量
   * @param num_qubits 量子位数量
   */
  inline void set_num_qubits(int num_qubits) {
    if (num_qubits < 0) {
      throw std::invalid_argument("num_qubits must be non-negative");
    }
    num_qubits_ = num_qubits;
  }

  /**
   * @brief 设置经典位数量
   * @param num_clbits 经典位数量
   */
  inline void set_num_clbits(int num_clbits) {
    if (num_clbits < 0) {
      throw std::invalid_argument("num_clbits must be non-negative");
    }
    num_clbits_ = num_clbits;
  }

  /**
   * @brief 计算线路深度
   * @return int 门深度
   */
  int depth() const;

  /**
   * @brief 返回线路宽度
   * @return int 量子位与经典位总数
   */
  int width() const { return num_qubits_ + num_clbits_; }

  /**
   * @brief 返回操作数量
   * @return int 操作个数
   */
  int size() const { return static_cast<int>(operations_.size()); }

 private:
  int num_qubits_;
  int num_clbits_;
  double global_phase_;
  std::vector<std::shared_ptr<BaseOperation>> operations_;
};

}  // namespace qcos
