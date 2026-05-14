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

#include "circuit/base_operation.h"
#include "compiler/operations/operation.hpp"

using namespace qc;
std::string qasmfile2str(const std::string& filename);

std::string convert_qasm_to_originir(std::string file_path);
std::string convert_qasm_string_to_originir(std::string qasm_str);
std::vector<std::unique_ptr<Operation>> convert_qasm_string_to_operations(
    std::string qasm_str);
std::pair<std::vector<std::unique_ptr<qcos::BaseOperation>>, int>
convert_qasm_string_to_qcos_operations(std::string qasm_str);
