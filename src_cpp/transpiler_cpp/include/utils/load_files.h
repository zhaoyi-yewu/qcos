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
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"

namespace qcos {

/**
 * @brief 从配置文件中加载量子芯片耦合列表
 *
 * 解析指定文件中的耦合信息，提取每对耦合的物理量子比特编号
 * 文件中每行格式类似：
 * coupler_map.x=["Q0","Q1"]
 *
 * @param filename 配置文件路径
 * @return std::vector<std::pair<int,int>>
 * 耦合对列表，每个元素为一对物理量子比特编号
 */
std::vector<std::pair<int, int>> load_config_file(const std::string& filename);

/**
 * @brief 解析QASM参数字符串为数值
 *
 * 支持：
 * 1. pi相关参数，如"pi","-pi","pi/2","-pi/4"
 * 2. 普通数字，如"1.57","-0.5"
 *
 * @param s QASM参数字符串
 * @return double 对应的浮点数值，如果解析失败返回0.0
 */
double parse_qasm_param(const std::string& s);

/**
 * @brief 将QASM文件加载为门操作列表
 *
 * 支持单量子比特门和双量子比特门
 * 忽略注释、OPENQASM声明、寄存器声明等非门操作行
 *
 * @param filename QASM文件路径
 * @return std::vector<GateOperation> 返回解析得到的门操作列表
 */
std::vector<GateOperation> load_qasm_to_gate_list(const std::string& filename);

}  // namespace qcos
