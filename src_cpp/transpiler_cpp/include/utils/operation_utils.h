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

#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @brief 使用共享指针包装 create_gate 生成的门操作
 * @param name 门名称
 * @param targets 目标量子位列表
 * @param args 可选参数列表
 * @return std::shared_ptr<BaseOperation> 新建门操作的共享指针
 */
inline std::shared_ptr<BaseOperation> make_gate(
    const std::string& name, const std::vector<int>& targets,
    const std::vector<double>& args = {}) {
  return std::shared_ptr<BaseOperation>(create_gate(name, targets, args));
}

}  // namespace qcos