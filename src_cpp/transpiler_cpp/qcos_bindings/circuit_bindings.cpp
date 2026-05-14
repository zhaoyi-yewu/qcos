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
#include "circuit/gate_operation.h"

namespace py = pybind11;
using namespace qcos;

void bind_circuits(py::module_& m) {
  py::class_<BaseOperation, std::unique_ptr<BaseOperation>>(m, "BaseOperation")
      .def(py::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType>(),
           py::arg("name"), py::arg("targets"), py::arg("arg_value"),
           py::arg("operation_type"))

      .def_readonly("name", &BaseOperation::name)
      .def_property("targets", &BaseOperation::getTargets,
                    &BaseOperation::setTargets)
      .def_property("arg_value", &BaseOperation::getArgValue,
                    &BaseOperation::setArgValue)
      .def_readonly("operation_type", &BaseOperation::operation_type)
      .def("targets_to_string", &BaseOperation::targets_to_string)
      .def("arg_value_to_string", &BaseOperation::arg_value_to_string)
      .def("__repr__",
           [](BaseOperation& self) {
             return self.name + "(targets=" + self.targets_to_string() +
                    ", arg_value=" + self.arg_value_to_string() + ")";
           })
      .def("__deepcopy__",
           [](const BaseOperation& self, py::dict) {
             return BaseOperation(self.name, self.targets, self.arg_value,
                                  self.operation_type);
           })
      .def("to_openqasm",
           py::overload_cast<const std::string&>(&BaseOperation::to_openqasm,
                                                 py::const_),
           py::arg("qubit_prefix") = "q");

  py::class_<GateOperation, BaseOperation, std::unique_ptr<GateOperation>>(
      m, "GateOperation")
      .def(py::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType, bool>(),
           py::arg("name"), py::arg("targets"), py::arg("arg_value"),
           py::arg("operation_type"), py::arg("hermitian") = false)
      .def_readonly("hermitian", &GateOperation::hermitian);
}