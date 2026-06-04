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
#include <pybind11/stl.h>

#include "circuit/base_operation.h"
#include "decomposer/decomposer.h"
#include "decomposer/equivalence_graph.h"

namespace py = pybind11;
using namespace qcos;

void bind_decomposer(py::module_& m) {
  // =========================
  // ParamGate
  // =========================
  py::class_<ParamGate>(m, "ParamGate")
      .def(py::init<>())
      .def_readwrite("name", &ParamGate::name)
      .def_readwrite("qubits", &ParamGate::qubits)
      .def_readwrite("params", &ParamGate::params);

  // =========================
  // Decomposer
  // =========================
  py::class_<Decomposer>(m, "Decomposer")
      .def(py::init<>())

      // -------- get_decompose_rules --------
      .def("get_decompose_rules",
           [](Decomposer& self, const std::vector<std::string>& source,
              const std::vector<std::string>& target) {
             auto result = self.get_decompose_rules(source, target);

             const auto& table = result.first;
             const auto& stats = result.second;

             py::dict py_table;

             for (const auto& [key, value] : table) {
               py_table[py::cast(key)] = py::cast(value);
             }

             return py::make_tuple(py_table, stats);
           })

      // -------- apply_decompose_rules --------
      .def("apply_decompose_rules",
           [](Decomposer& self, const std::vector<BaseOperation*>& circuit_raw,
              const Decomposer::DecompositionTable& table) {
             // Python -> C++ clone
             std::vector<std::shared_ptr<BaseOperation>> circuit;
             circuit.reserve(circuit_raw.size());

             for (auto* ptr : circuit_raw) {
               circuit.push_back(ptr->clone());
             }

             auto result = self.apply_decompose_rules(circuit, table);
             return result;
           });
}