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
#include <nanobind/stl/shared_ptr.h>

namespace nb = nanobind;

void bind_enums(nb::module_& m);
void bind_circuits(nb::module_& m);
void bind_mapping(nb::module_& m);
void bind_utils(nb::module_& m);
void bind_cpp_mcts(nb::module_& m);
void bind_parser(nb::module_& m);
void bind_decomposer(nb::module_& m);
void bind_optimizer(nb::module_& m);
void bind_transpile(nb::module_& m);

NB_MODULE(high_performance, m) {
  m.doc() = "Binding qcos transpiler cpp functions.";

  bind_enums(m);
  bind_circuits(m);
  bind_mapping(m);
  bind_utils(m);
  bind_cpp_mcts(m);
  bind_parser(m);
  bind_decomposer(m);
  bind_optimizer(m);
  bind_transpile(m);
}
