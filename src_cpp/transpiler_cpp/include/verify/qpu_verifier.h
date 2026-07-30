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
 * 三项核心检查（verify 按顺序调用，check_qasm_syntax 负责解析并缓存结果）：
 *   1. check_qasm_syntax     — QASM 语法校验，解析结果存入 operations_ /
 * num_qubits_
 *   2. check_topology        — 拓扑结构校验
 *   3. check_depth_and_gate_count — 最大深度/门数量校验
 */
class QPUVerifier {
 public:
  virtual ~QPUVerifier() = default;

  /**
   * @brief 完整校验，依次调用三项检查
   * @param qasm_string  QASM 电路字符串
   * @param verbose      是否在校验结束时打印结果信息
   * @return VerifyResult，passed=true 表示通过，message 包含失败原因
   */
  virtual VerifyResult verify(const std::string& qasm_string,
                              bool verbose = false) const = 0;

  /**
   * @brief QASM 语法校验
   *
   * 检查原始 QASM 字符串是否合法。
   * 解析成功后将 operations 和 num_qubits 缓存到成员变量，供后续 check
   * 方法使用。失败时通过 result_ 成员记录原因。
   * @param qasm_string  QASM 电路字符串
   * @return true=通过，false=不通过
   */
  virtual bool check_qasm_syntax(const std::string& qasm_string) const = 0;

  /**
   * @brief 拓扑结构校验
   *
   * 使用 check_qasm_syntax 缓存的解析结果，检查：
   * - 量子比特数是否在芯片范围内
   * - 两比特门操作的目标量子比特对是否存在于耦合图中
   * 失败时通过 result_ 成员记录原因。
   * @return true=通过，false=不通过
   */
  virtual bool check_topology() const = 0;

  /**
   * @brief 最大深度 / 门数量校验
   *
   * 使用 check_qasm_syntax 缓存的解析结果，检查电路规模是否超限。
   * 失败时通过 result_ 成员记录原因。
   * @return true=通过，false=不通过
   */
  virtual bool check_depth_and_gate_count() const = 0;
};

}  // namespace qcos
