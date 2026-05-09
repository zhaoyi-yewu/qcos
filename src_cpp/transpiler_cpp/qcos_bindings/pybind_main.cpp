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

#include <pybind11/pybind11.h>

namespace py = pybind11;

void bind_enums(py::module_& m);
void bind_circuits(py::module_& m);
void bind_mapping(py::module_& m);
void bind_utils(py::module_& m);
void bind_cpp_mcts(py::module_& m);
void bind_parser(py::module_& m);
void bind_decomposer(py::module_& m);

PYBIND11_MODULE(high_performance, m) {
  m.doc() = "Binding qcos transpiler cpp functions.";

  bind_enums(m);
  bind_circuits(m);
  bind_mapping(m);
  bind_utils(m);
  bind_cpp_mcts(m);
  bind_parser(m);
  bind_decomposer(m);
}