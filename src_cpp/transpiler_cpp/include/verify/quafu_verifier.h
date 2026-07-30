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

#include "verify/qpu_verifier.h"

namespace qcos {

/**
 * @brief 北量院 Quafu（夸父）系列超导芯片校验
 *
 * 从 VerifyParams 读取芯片参数，校验电路是否可在 Quafu 真机上执行：
 * - QASM 语法必须合法（OPENQASM 2.0 + 可解析）
 * - 拓扑约束：比特数 + 连通图 + 用户指定比特
 * - 门数量/深度不超过上限（-1 表示不限）
 */
class QuafuVerifier : public QPUVerifier {
 public:
  /**
   * @brief 从 VerifyParams 构造
   * @param params 校验参数，由 Python 层解析 API 请求后传入
   */
  explicit QuafuVerifier(const VerifyParams& params);

  VerifyResult verify(const std::string& qasm_string,
                      bool verbose = false) const override;

  bool check_qasm_syntax(const std::string& qasm_string) const override;

  bool check_topology() const override;

  bool check_depth_and_gate_count() const override;

 private:
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
