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
  py::class_<BaseOperation, std::unique_ptr<BaseOperation>>(m, "BaseOperation",
                                                            py::dynamic_attr())
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
      .def_readonly("hermitian", &GateOperation::hermitian)
      .def("decompose_to_1q2q", &GateOperation::decompose_to_1q2q)
      .def("__deepcopy__", [](const GateOperation& self, py::dict) {
        return GateOperation(self.name, self.targets, self.arg_value,
                             self.operation_type);
      });

  py::class_<std::complex<double>>(m, "complex")
      .def(py::init<double, double>())
      .def_property_readonly(
          "real", [](const std::complex<double>& c) { return c.real(); })
      .def_property_readonly(
          "imag", [](const std::complex<double>& c) { return c.imag(); });

  py::class_<H, GateOperation, std::unique_ptr<H>>(m, "H")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &H::to_matrix)
      .def("default_decompose", &H::default_decompose)
      .def("__repr__", [](const H& self) { return self.to_string(); });

  py::class_<X, GateOperation, std::unique_ptr<X>>(m, "X")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &X::to_matrix)
      .def("default_decompose", &X::default_decompose)
      .def("__repr__", [](const X& self) { return self.to_string(); });

  py::class_<Y, GateOperation, std::unique_ptr<Y>>(m, "Y")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &Y::to_matrix)
      .def("default_decompose", &Y::default_decompose)
      .def("__repr__", [](const Y& self) { return self.to_string(); });

  py::class_<Z, GateOperation, std::unique_ptr<Z>>(m, "Z")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &Z::to_matrix)
      .def("default_decompose", &Z::default_decompose)
      .def("__repr__", [](const Z& self) { return self.to_string(); });

  py::class_<S, GateOperation, std::unique_ptr<S>>(m, "S")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &S::to_matrix)
      .def("default_decompose", &S::default_decompose)
      .def("__repr__", [](const S& self) { return self.to_string(); });

  py::class_<SDG, GateOperation, std::unique_ptr<SDG>>(m, "SDG")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SDG::to_matrix)
      .def("default_decompose", &SDG::default_decompose)
      .def("__repr__", [](const SDG& self) { return self.to_string(); });

  py::class_<T, GateOperation, std::unique_ptr<T>>(m, "T")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &T::to_matrix)
      .def("default_decompose", &T::default_decompose)
      .def("__repr__", [](const T& self) { return self.to_string(); });

  py::class_<TDG, GateOperation, std::unique_ptr<TDG>>(m, "TDG")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &TDG::to_matrix)
      .def("default_decompose", &TDG::default_decompose)
      .def("__repr__", [](const TDG& self) { return self.to_string(); });

  py::class_<P, GateOperation, std::unique_ptr<P>>(m, "P")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &P::to_matrix)
      .def("default_decompose", &P::default_decompose)
      .def("__repr__", [](const P& self) { return self.to_string(); });

  py::class_<R, GateOperation, std::unique_ptr<R>>(m, "R")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &R::to_matrix)
      .def("default_decompose", &R::default_decompose)
      .def("__repr__", [](const R& self) { return self.to_string(); });

  py::class_<RX, GateOperation, std::unique_ptr<RX>>(m, "RX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RX::to_matrix)
      .def("default_decompose", &RX::default_decompose)
      .def("__repr__", [](const RX& self) { return self.to_string(); });

  py::class_<RY, GateOperation, std::unique_ptr<RY>>(m, "RY")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RY::to_matrix)
      .def("default_decompose", &RY::default_decompose)
      .def("__repr__", [](const RY& self) { return self.to_string(); });

  py::class_<RZ, GateOperation, std::unique_ptr<RZ>>(m, "RZ")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RZ::to_matrix)
      .def("default_decompose", &RZ::default_decompose)
      .def("__repr__", [](const RZ& self) { return self.to_string(); });

  py::class_<SX, GateOperation, std::unique_ptr<SX>>(m, "SX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SX::to_matrix)
      .def("default_decompose", &SX::default_decompose)
      .def("__repr__", [](const SX& self) { return self.to_string(); });

  py::class_<SXDG, GateOperation, std::unique_ptr<SXDG>>(m, "SXDG")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SXDG::to_matrix)
      .def("default_decompose", &SXDG::default_decompose)
      .def("__repr__", [](const SXDG& self) { return self.to_string(); });

  py::class_<CZ, GateOperation, std::unique_ptr<CZ>>(m, "CZ")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CZ::to_matrix)
      .def("default_decompose", &CZ::default_decompose)
      .def("__repr__", [](const CZ& self) { return self.to_string(); });

  py::class_<CX, GateOperation, std::unique_ptr<CX>>(m, "CX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CX::to_matrix)
      .def("default_decompose", &CX::default_decompose)
      .def("__repr__", [](const CX& self) { return self.to_string(); });

  py::class_<CY, GateOperation, std::unique_ptr<CY>>(m, "CY")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CY::to_matrix)
      .def("default_decompose", &CY::default_decompose)
      .def("__repr__", [](const CY& self) { return self.to_string(); });

  py::class_<SWAP, GateOperation, std::unique_ptr<SWAP>>(m, "SWAP")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &SWAP::to_matrix)
      .def("default_decompose", &SWAP::default_decompose)
      .def("__repr__", [](const SWAP& self) { return self.to_string(); });

  py::class_<ISWAP, GateOperation, std::unique_ptr<ISWAP>>(m, "ISWAP")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &ISWAP::to_matrix)
      .def("default_decompose", &ISWAP::default_decompose)
      .def("__repr__", [](const ISWAP& self) { return self.to_string(); });

  py::class_<CH, GateOperation, std::unique_ptr<CH>>(m, "CH")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CH::to_matrix)
      .def("default_decompose", &CH::default_decompose)
      .def("__repr__", [](const CH& self) { return self.to_string(); });

  py::class_<CS, GateOperation, std::unique_ptr<CS>>(m, "CS")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CS::to_matrix)
      .def("default_decompose", &CS::default_decompose)
      .def("__repr__", [](const CS& self) { return self.to_string(); });

  py::class_<CSDG, GateOperation, std::unique_ptr<CSDG>>(m, "CSDG")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CSDG::to_matrix)
      .def("default_decompose", &CSDG::default_decompose)
      .def("__repr__", [](const CSDG& self) { return self.to_string(); });

  py::class_<CRX, GateOperation, std::unique_ptr<CRX>>(m, "CRX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CRX::to_matrix)
      .def("default_decompose", &CRX::default_decompose)
      .def("__repr__", [](const CRX& self) { return self.to_string(); });

  py::class_<CRY, GateOperation, std::unique_ptr<CRY>>(m, "CRY")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CRY::to_matrix)
      .def("default_decompose", &CRY::default_decompose)
      .def("__repr__", [](const CRY& self) { return self.to_string(); });

  py::class_<CRZ, GateOperation, std::unique_ptr<CRZ>>(m, "CRZ")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CRZ::to_matrix)
      .def("default_decompose", &CRZ::default_decompose)
      .def("__repr__", [](const CRZ& self) { return self.to_string(); });

  py::class_<CU1, GateOperation, std::unique_ptr<CU1>>(m, "CU1")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CU1::to_matrix)
      .def("default_decompose", &CU1::default_decompose)
      .def("__repr__", [](const CU1& self) { return self.to_string(); });

  py::class_<CP, GateOperation, std::unique_ptr<CP>>(m, "CP")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CP::to_matrix)
      .def("default_decompose", &CP::default_decompose)
      .def("__repr__", [](const CP& self) { return self.to_string(); });

  py::class_<CU3, GateOperation, std::unique_ptr<CU3>>(m, "CU3")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CU3::to_matrix)
      .def("default_decompose", &CU3::default_decompose)
      .def("__repr__", [](const CU3& self) { return self.to_string(); });

  py::class_<CSX, GateOperation, std::unique_ptr<CSX>>(m, "CSX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CSX::to_matrix)
      .def("default_decompose", &CSX::default_decompose)
      .def("__repr__", [](const CSX& self) { return self.to_string(); });

  py::class_<CU, GateOperation, std::unique_ptr<CU>>(m, "CU")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CU::to_matrix)
      .def("default_decompose", &CU::default_decompose)
      .def("__repr__", [](const CU& self) { return self.to_string(); });

  py::class_<ECR, GateOperation, std::unique_ptr<ECR>>(m, "ECR")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &ECR::to_matrix)
      .def("default_decompose", &ECR::default_decompose)
      .def("__repr__", [](const ECR& self) { return self.to_string(); });

  py::class_<DCX, GateOperation, std::unique_ptr<DCX>>(m, "DCX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &DCX::to_matrix)
      .def("default_decompose", &DCX::default_decompose)
      .def("__repr__", [](const DCX& self) { return self.to_string(); });

  py::class_<RXX, GateOperation, std::unique_ptr<RXX>>(m, "RXX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RXX::to_matrix)
      .def("default_decompose", &RXX::default_decompose)
      .def("__repr__", [](const RXX& self) { return self.to_string(); });

  py::class_<RYY, GateOperation, std::unique_ptr<RYY>>(m, "RYY")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RYY::to_matrix)
      .def("default_decompose", &RYY::default_decompose)
      .def("__repr__", [](const RYY& self) { return self.to_string(); });

  py::class_<RZZ, GateOperation, std::unique_ptr<RZZ>>(m, "RZZ")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RZZ::to_matrix)
      .def("default_decompose", &RZZ::default_decompose)
      .def("__repr__", [](const RZZ& self) { return self.to_string(); });

  py::class_<RZX, GateOperation, std::unique_ptr<RZX>>(m, "RZX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RZX::to_matrix)
      .def("default_decompose", &RZX::default_decompose)
      .def("__repr__", [](const RZX& self) { return self.to_string(); });

  py::class_<CCX, GateOperation, std::unique_ptr<CCX>>(m, "CCX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CCX::to_matrix)
      .def("decompose_to_1q2q", &CCX::decompose_to_1q2q)
      .def("default_decompose", &CCX::default_decompose)
      .def("__repr__", [](const CCX& self) { return self.to_string(); });

  py::class_<CSWAP, GateOperation, std::unique_ptr<CSWAP>>(m, "CSWAP")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &CSWAP::to_matrix)
      .def("decompose_to_1q2q", &CSWAP::decompose_to_1q2q)
      .def("default_decompose", &CSWAP::default_decompose)
      .def("__repr__", [](const CSWAP& self) { return self.to_string(); });

  py::class_<RCCX, GateOperation, std::unique_ptr<RCCX>>(m, "RCCX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RCCX::to_matrix)
      .def("decompose_to_1q2q", &RCCX::decompose_to_1q2q)
      .def("default_decompose", &RCCX::default_decompose)
      .def("__repr__", [](const RCCX& self) { return self.to_string(); });

  py::class_<RC3X, GateOperation, std::unique_ptr<RC3X>>(m, "RC3X")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &RC3X::to_matrix)
      .def("decompose_to_1q2q", &RC3X::decompose_to_1q2q)
      .def("default_decompose", &RC3X::default_decompose)
      .def("__repr__", [](const RC3X& self) { return self.to_string(); });

  py::class_<C3X, GateOperation, std::unique_ptr<C3X>>(m, "C3X")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &C3X::to_matrix)
      .def("decompose_to_1q2q", &C3X::decompose_to_1q2q)
      .def("default_decompose", &C3X::default_decompose)
      .def("__repr__", [](const C3X& self) { return self.to_string(); });

  py::class_<C3SQRTX, GateOperation, std::unique_ptr<C3SQRTX>>(m, "C3SQRTX")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &C3SQRTX::to_matrix)
      .def("decompose_to_1q2q", &C3SQRTX::decompose_to_1q2q)
      .def("default_decompose", &C3SQRTX::default_decompose)
      .def("__repr__", [](const C3SQRTX& self) { return self.to_string(); });

  py::class_<C4X, GateOperation, std::unique_ptr<C4X>>(m, "C4X")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("to_matrix", &C4X::to_matrix)
      .def("decompose_to_1q2q", &C4X::decompose_to_1q2q)
      .def("default_decompose", &C4X::default_decompose)
      .def("__repr__", [](const C4X& self) { return self.to_string(); });

  py::class_<U1, GateOperation, std::unique_ptr<U1>>(m, "U1")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U1::to_matrix)
      .def("default_decompose", &U1::default_decompose)
      .def("__repr__", [](const U1& self) { return self.to_string(); });

  py::class_<U2, GateOperation, std::unique_ptr<U2>>(m, "U2")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U2::to_matrix)
      .def("default_decompose", &U2::default_decompose)
      .def("__repr__", [](const U2& self) { return self.to_string(); });

  py::class_<U3, GateOperation, std::unique_ptr<U3>>(m, "U3")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U3::to_matrix)
      .def("default_decompose", &U3::default_decompose)
      .def("__repr__", [](const U3& self) { return self.to_string(); });

  py::class_<U, GateOperation, std::unique_ptr<U>>(m, "U")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U::to_matrix)
      .def("default_decompose", &U::default_decompose)
      .def("__repr__", [](const U& self) { return self.to_string(); });

  py::class_<Sync, BaseOperation, std::unique_ptr<Sync>>(m, "Sync")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("__repr__", [](const Sync& self) { return self.to_string(); });

  py::class_<Measure, BaseOperation, std::unique_ptr<Measure>>(m, "Measure")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("__repr__", [](const Measure& self) { return self.to_string(); });

  py::class_<Move, BaseOperation, std::unique_ptr<Move>>(m, "Move")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("__repr__", [](const Move& self) { return self.to_string(); });

  py::class_<Reset, BaseOperation, std::unique_ptr<Reset>>(m, "Reset")
      .def(py::init<std::vector<int>, std::vector<double>>(),
           py::arg("targets"), py::arg("arg_value") = std::vector<double>())
      .def(py::init<std::vector<int>, std::vector<double>, OperationType>(),
           py::arg("targets"), py::arg("arg_value"), py::arg("operation_type"))
      .def("__repr__", [](const Reset& self) { return self.to_string(); });

  m.def("create_gate", &create_gate, py::arg("name"),
        py::arg("targets") = std::vector<int>(),
        py::arg("arg_value") = std::vector<double>(),
        py::arg("allow_undefined") = false,
        "Create a gate or operation instance by name.");
}