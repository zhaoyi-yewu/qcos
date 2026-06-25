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

#include <nanobind/nanobind.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "utils/load_files.h"

namespace nb = nanobind;
using namespace qcos;

void bind_utils(nb::module_& m) {
  m.def("load_config_file", &load_config_file, nb::arg("filename"),
        R"(
从配置文件中加载量子芯片耦合列表.

Args:
    filename (str): 配置文件路径

Returns:
    list[tuple[int,int]]: 耦合对列表
)");

  m.def("load_qasm_to_gate_list", &load_qasm_to_gate_list, nb::arg("filename"),
        R"(
将QASM文件加载为门操作列表.

Args:
    filename (str): QASM文件路径

Returns:
    list[GateOperation]: 解析得到的门操作列表
)");
}
