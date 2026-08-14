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
#include <utility>
#include <vector>

#include "circuit/base_operation.h"

namespace qcos {

/**
 * @brief 校验参数，由 Python 层解析 API 请求后填充
 *
 * 包含校验所需的全部输入：
 *   topology.bits        -> bits
 *   topology.basisGates  -> basis_gates
 *   topology.singleParam -> single_qubit_fidelities
 *   topology.doubleParam -> coupling_list / edge_fidelities
 *   extend.targetBits    -> target_bits（可选，空表示不限制）
 *
 * Python 侧负责将 "Q0" -> 0、"Q0-Q1" -> (0, 1) 的字符串转 int 转换。
 */
struct VerifyParams {
  int bits = 0;  ///< 真机可用量子比特数（topology.bits）
  std::vector<std::string>
      basis_gates;  ///< 真机支持的基础门集合（topology.basisGates）
  std::vector<std::pair<int, int>>
      coupling_list;  ///< 有向耦合边列表（topology.doubleParam）
  std::vector<double> edge_fidelities;  ///< 与 coupling_list 对应的 CZ 保真度
  std::vector<double>
      single_qubit_fidelities;  ///< 按物理位 ID 索引的单比特保真度
  std::vector<int>
      target_bits;  ///< 自定义比特位（extend.targetBits，空表示不限制）
};

/**
 * @brief 校验结果
 *
 * passed 为 true 表示校验通过，message 为空；
 * passed 为 false 时 message 包含失败原因。
 */
struct VerifyResult {
  bool passed = true;
  std::string message;  ///< 失败原因，passed=true 时为空

  /** @brief 设置失败原因，同时将 passed 置为 false */
  void add_failure(const std::string& msg) {
    passed = false;
    message = msg;
  }
};

/**
 * @brief 量子真机校验器抽象基类（Quantum Processing Unit Verifier）
 *
 * 在提交电路到真机执行前，本地校验电路是否符合目标真机的约束条件，
 * 避免提交后浪费时间。子类实现各真机的具体校验规则。
 *
 * 校验流程（verify 按顺序调用）：
 *   1. check_qasm_syntax2  — QASM 语法校验
 *   2. check_topology      — 拓扑结构校验（纯虚，子类实现）
 *   3. check_depth_and_gate_count — 深度/门数量校验（虚函数，有默认实现）
 */
class QPUVerifier {
 public:
  explicit QPUVerifier(const VerifyParams& params);
  virtual ~QPUVerifier() = default;

  /**
   * @brief 完整校验（纯虚，子类实现）
   *
   * 子类按序调用 check_qasm_syntax2 -> check_topology ->
   * check_depth_and_gate_count，并处理结果返回。
   * @param qasm_string  QASM 电路字符串
   * @param verbose      是否在校验结束时打印结果信息
   * @return VerifyResult，passed=true 表示通过，message 包含失败原因
   */
  virtual VerifyResult verify(const std::string& qasm_string,
                              bool verbose = false) const = 0;

  /**
   * @brief QASM 语法校验（虚函数）
   *
   * 基类默认实现：检查 OPENQASM 2.0 声明并解析电路，解析结果缓存到
   * parsed_operations_ / parsed_num_qubits_ 供后续 check 使用，
   * 并执行 Measure 规则校验（Measure 必须在线路末尾，每个比特最多一次）。
   * 子类可 override 调用基类后附加自身语法规则。
   * @param qasm_string  QASM 电路字符串
   * @return true=通过，false=不通过
   */
  virtual bool check_qasm_syntax2(const std::string& qasm_string) const;

  /**
   * @brief 拓扑结构校验（纯虚，子类实现）
   */
  virtual bool check_topology() const = 0;

  /**
   * @brief 深度/两比特门数量/总门数量校验（虚函数，默认限值 200/200/不限）
   *
   * 子类可 override 调用基类传入自定义限值。
   */
  virtual bool check_depth_and_gate_count() const {
    return check_depth_and_gate_count(200, 200, -1);
  }

 protected:
  /**
   * @brief 深度/两比特门数量/总门数量校验实现
   * @param max_depth   最大深度，-1 表示不限
   * @param max_2q_size 最大两比特门数量，-1 表示不限
   * @param max_size    最大总门数量，-1 表示不限
   */
  bool check_depth_and_gate_count(int max_depth, int max_2q_size,
                                  int max_size) const;

  /// Measure 门必须在线路末尾，且每个比特最多测量一次
  bool check_measure_rules() const;

  /// target_bits 越界检查
  bool check_target_bits_range() const;

  /// target_bits 越界检查 + 去重 + 数量校验
  bool check_target_bits_range_and_count() const;

  /// 最大连通分量节点数 >= required
  bool check_largest_component_sufficient(int required) const;

  /// 检测 parsed_operations_ 中是否含多比特门
  bool has_multi_qubit_gates() const;

  int max_qubits_;
  std::vector<std::pair<int, int>> coupling_list_;
  std::vector<double> edge_fidelities_;
  std::vector<double> single_qubit_fidelities_;
  mutable std::vector<int> target_bits_;
  mutable std::vector<std::shared_ptr<BaseOperation>> parsed_operations_;
  mutable int parsed_num_qubits_ = 0;
  mutable VerifyResult result_;
};

}  // namespace qcos
