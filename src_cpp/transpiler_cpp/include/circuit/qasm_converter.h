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
#include <string_view>
#include <vector>

#include "circuit/base_operation.h"

namespace qcos {

std::string to_qasm2(
    const std::vector<std::shared_ptr<BaseOperation>>& operations);

std::string to_qasm3(
    const std::vector<std::shared_ptr<BaseOperation>>& operations);

void save_qasm(const std::string& path,
               const std::vector<std::shared_ptr<BaseOperation>>& operations,
               const std::string& version = "2.0");

namespace detail {

std::string convert_op_to_qasm2(const BaseOperation& op);
std::string convert_op_to_qasm3(const BaseOperation& op);
std::string to_lower(std::string_view s);

}  // namespace detail

}  // namespace qcos
