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
  py::class_<BaseOperation>(m, "BaseOperation")
      .def(py::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType>(),
           py::arg("name"), py::arg("targets"), py::arg("arg_value"),
           py::arg("operation_type"))

      .def_readonly("name", &BaseOperation::name)
      .def_readonly("targets", &BaseOperation::targets)
      .def_readonly("arg_value", &BaseOperation::arg_value)
      .def_readonly("operation_type", &BaseOperation::operation_type);

  py::class_<GateOperation, BaseOperation>(m, "GateOperation")
      .def(py::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType, bool>(),
           py::arg("name"), py::arg("targets"), py::arg("arg_value"),
           py::arg("operation_type"), py::arg("hermitian") = false)

      .def_readonly("hermitian", &GateOperation::hermitian);
}