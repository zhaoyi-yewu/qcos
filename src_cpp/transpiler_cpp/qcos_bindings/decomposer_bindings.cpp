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
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/unordered_map.h>
#include <nanobind/stl/vector.h>

#include "circuit/base_operation.h"
#include "decomposer/decomposer.h"
#include "decomposer/equivalence_graph.h"

namespace nb = nanobind;
using namespace qcos;

void bind_decomposer(nb::module_& m) {
  // =========================
  // ParamGate
  // =========================
  nb::class_<ParamGate>(m, "ParamGate")
      .def(nb::init<>())
      .def_rw("name", &ParamGate::name)
      .def_rw("qubits", &ParamGate::qubits)
      .def_rw("params", &ParamGate::params);

  // =========================
  // Decomposer
  // =========================
  nb::class_<Decomposer>(m, "Decomposer")
      .def(nb::init<>())

      // -------- get_decompose_rules --------
      .def("get_decompose_rules",
           [](Decomposer& self, const std::vector<std::string>& source,
              const std::vector<std::string>& target) {
             auto result = self.get_decompose_rules(source, target);

             const auto& table = result.first;
             const auto& stats = result.second;

             nb::dict nb_table;

             for (const auto& [key, value] : table) {
               nb_table[nb::cast(key)] = nb::cast(value);
             }

             return nb::make_tuple(nb_table, stats);
           })

      // -------- apply_decompose_rules --------
      .def(
          "apply_decompose_rules",
          &Decomposer::apply_decompose_rules,
          nb::arg("circuit"),
          nb::arg("table"));
}
