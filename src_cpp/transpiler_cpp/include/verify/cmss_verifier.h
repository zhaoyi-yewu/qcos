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

#include <string>

#include "verify/qpu_verifier.h"

namespace qcos {

/**
 * @brief CMSS 编译器校验
 *
 * - QASM 语法：OPENQASM 2.0 声明且可解析 + Measure 规则
 * - 比特数：电路实际使用比特数不超过真机可用比特数
 * - target_bits 越界：每个 target_bit 在 [0, bits) 范围内
 * - target_bits 数量：去重后与电路实际使用比特数一致
 * - 全单比特门（无 target_bits）：仅校验比特数是否足够
 * - 全单比特门（有 target_bits）：比特数 + 越界 + 数量校验，不检查连通性
 * - 含多比特门（无 target_bits）：最大连通分量节点数 >= 电路比特数
 * - 含多比特门（有 target_bits）：target_bits 必须构成单一连通图，
 *   且数量与电路实际使用比特数一致
 * - 深度 <= 200，两比特门数量 <= 200，总门数量 <= 500（分解后）
 */
class CMSSVerifier : public QPUVerifier {
 public:
  /**
   * @brief 从 VerifyParams 构造
   * @param params 校验参数，由 Python 层解析 API 请求后传入
   */
  explicit CMSSVerifier(const VerifyParams& params);

  /**
   * @brief 完整校验入口
   *
   * 按序执行 check_qasm_syntax2 -> check_topology ->
   * check_depth_and_gate_count，任一失败则终止并返回原因。
   * @param qasm_string QASM 电路字符串
   * @param verbose 是否在校验结束时打印结果信息
   * @return VerifyResult，passed=true 表示全部通过
   */
  VerifyResult verify(const std::string& qasm_string,
                      bool verbose = false) const override;

  /**
   * @brief QASM 语法校验
   *
   * 直接委托基类实现（含 OPENQASM 2.0 校验 + 解析 + Measure 规则）。
   * @param qasm_string QASM 电路字符串
   * @return true 语法合法
   */
  bool check_qasm_syntax2(const std::string& qasm_string) const override;

  /**
   * @brief 拓扑结构校验
   *
   * 根据电路是否含多比特门、是否指定 target_bits 分四种情况：
   * - 全单比特门，无 target_bits：仅校验比特数 <= 真机可用比特数
   * - 全单比特门，有 target_bits：比特数 + target_bits 越界 + 数量校验
   * - 含多比特门，无 target_bits：最大连通分量节点数 >= 电路比特数
   * - 含多比特门，有 target_bits：target_bits 必须构成单一连通图，
   *   且数量与电路实际使用比特数一致
   * @return true 拓扑约束满足
   */
  bool check_topology() const override;

  /**
   * @brief 深度/门数量校验
   *
   * 调用基类实现，限值深度 200、两比特门 200、总门数 500（分解后）。
   * @return true 未超限
   */
  bool check_depth_and_gate_count() const override;
};

}  // namespace qcos
