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

#include <utility>
#include <vector>

#include "verify/qpu_verifier.h"

namespace qcos {

/**
 * @brief 北量院 Quafu（夸父）系列超导芯片校验
 *
 * 从 VerifyParams 读取芯片参数，校验电路是否可在 Quafu 真机上执行：
 * - QASM 语法必须合法（OPENQASM 2.0 + 可解析 + Measure 规则）
 * - 拓扑约束：比特数 + 连通图 + 用户指定比特（bin-packing）
 * - 门数量/深度不超过上限
 */
class QuafuVerifier : public QPUVerifier {
 public:
  /**
   * @brief 从 VerifyParams 构造
   * @param params 校验参数，由 Python 层解析 API 请求后传入
   */
  explicit QuafuVerifier(const VerifyParams& params);

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
   * 根据电路是否含多比特门、是否指定 target_bits 分情况校验：
   * - 全单比特门：比特数 <= 真机可用比特数即可
   * - 含多比特门，无 target_bits：最大连通分量节点数 >= 电路比特数
   * - 含多比特门，有 target_bits：电路各连通分量能否装入 target_bits
   *   诱导子图的各连通分量（bin-packing 可行性）
   * @return true 拓扑约束满足
   */
  bool check_topology() const override;

  /**
   * @brief 深度/门数量校验
   *
   * 调用基类实现，限值深度 200、两比特门 200，总门数不限。
   * @return true 未超限
   */
  bool check_depth_and_gate_count() const override;
};

}  // namespace qcos
