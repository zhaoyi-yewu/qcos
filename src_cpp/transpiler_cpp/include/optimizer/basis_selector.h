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

#include <map>
#include <optional>
#include <set>
#include <string>
#include <vector>

namespace qcos {

namespace basis_selector {

/**
 * @brief 从基础门集中选择第一个可用的 KAK 门
 *
 * KAK 门优先级: cx > cz > iswap > ecr > rxx > rzx
 *
 * @param basis_gates 目标基础门集合
 * @return 可用的 KAK 门名称，如果没有则返回 nullopt
 */
std::optional<std::string> choose_kak_gate(const std::set<std::string>& basis_gates);

/**
 * @brief 从基础门集中选择第一个可用的 Euler 分解基
 *
 * Euler 基优先级: ZYZ > ZXZ > XYX > U3 > U > PSX > ZSX > RR
 *
 * @param basis_gates 目标基础门集合
 * @return 可用的 Euler 基名称，如果没有则返回 nullopt
 */
std::optional<std::string> choose_euler_basis(const std::set<std::string>& basis_gates);

/**
 * @brief 查找所有匹配的基础
 *
 * @param basis_gates 目标基础门集合
 * @param basis_dict 基础字典 (名称 -> 所需门列表)
 * @return 所有匹配的基础名称列表
 */
std::vector<std::string> find_matching_bases(
    const std::set<std::string>& basis_gates,
    const std::map<std::string, std::vector<std::string>>& basis_dict);

/**
 * @brief 检查基础门集是否支持指定的 Euler 基
 *
 * @param basis_gates 目标基础门集合
 * @param euler_basis Euler 基名称
 * @return 是否支持
 */
bool has_euler_basis(const std::set<std::string>& basis_gates,
                     const std::string& euler_basis);

}  // namespace basis_selector

}  // namespace qcos
