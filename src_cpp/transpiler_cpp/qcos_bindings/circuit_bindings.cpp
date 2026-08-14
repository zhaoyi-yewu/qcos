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
#include <nanobind/stl/array.h>
#include <nanobind/stl/complex.h>
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"
#include "circuit/qasm_converter.h"
#include "circuit/quantum_circuit.h"

namespace nb = nanobind;
using namespace qcos;

void bind_circuits(nb::module_& m) {
  nb::class_<BaseOperation>(m, "BaseOperation")
      .def(nb::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType>(),
           nb::arg("name"), nb::arg("targets"), nb::arg("arg_value"),
           nb::arg("operation_type"))

      .def_ro("name", &BaseOperation::name)
      .def_prop_rw("targets", &BaseOperation::getTargets,
                   &BaseOperation::setTargets)
      .def_prop_rw("arg_value", &BaseOperation::getArgValue,
                   &BaseOperation::setArgValue)
      .def_ro("operation_type", &BaseOperation::operation_type)
      .def("targets_to_string", &BaseOperation::targets_to_string)
      .def("arg_value_to_string", &BaseOperation::arg_value_to_string)
      .def("__repr__",
           [](BaseOperation& self) {
             return self.name + "(targets=" + self.targets_to_string() +
                    ", arg_value=" + self.arg_value_to_string() + ")";
           })
      .def("__deepcopy__",
           [](const BaseOperation& self, nb::dict) {
             return BaseOperation(self.name, self.targets, self.arg_value,
                                  self.operation_type);
           })
      .def("to_openqasm",
           nb::overload_cast<const std::string&>(&BaseOperation::to_openqasm,
                                                 nb::const_),
           nb::arg("qubit_prefix") = "q");

  nb::class_<GateOperation, BaseOperation>(m, "GateOperation")
      .def(nb::init<std::string, std::vector<int>, std::vector<double>,
                    OperationType, bool>(),
           nb::arg("name"), nb::arg("targets"), nb::arg("arg_value"),
           nb::arg("operation_type"), nb::arg("hermitian") = false)
      .def_ro("hermitian", &GateOperation::hermitian)
      .def("decompose_to_1q2q", &GateOperation::decompose_to_1q2q)
      .def("__deepcopy__", [](const GateOperation& self, nb::dict) {
        return GateOperation(self.name, self.targets, self.arg_value,
                             self.operation_type);
      });

  nb::class_<H, GateOperation>(m, "H")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &H::to_matrix)
      .def("default_decompose", &H::default_decompose)
      .def("__repr__", [](const H& self) { return self.to_string(); });

  nb::class_<X, GateOperation>(m, "X")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &X::to_matrix)
      .def("default_decompose", &X::default_decompose)
      .def("__repr__", [](const X& self) { return self.to_string(); });

  nb::class_<Y, GateOperation>(m, "Y")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &Y::to_matrix)
      .def("default_decompose", &Y::default_decompose)
      .def("__repr__", [](const Y& self) { return self.to_string(); });

  nb::class_<Z, GateOperation>(m, "Z")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &Z::to_matrix)
      .def("default_decompose", &Z::default_decompose)
      .def("__repr__", [](const Z& self) { return self.to_string(); });

  nb::class_<S, GateOperation>(m, "S")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &S::to_matrix)
      .def("default_decompose", &S::default_decompose)
      .def("__repr__", [](const S& self) { return self.to_string(); });

  nb::class_<SDG, GateOperation>(m, "SDG")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SDG::to_matrix)
      .def("default_decompose", &SDG::default_decompose)
      .def("__repr__", [](const SDG& self) { return self.to_string(); });

  nb::class_<T, GateOperation>(m, "T")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &T::to_matrix)
      .def("default_decompose", &T::default_decompose)
      .def("__repr__", [](const T& self) { return self.to_string(); });

  nb::class_<TDG, GateOperation>(m, "TDG")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &TDG::to_matrix)
      .def("default_decompose", &TDG::default_decompose)
      .def("__repr__", [](const TDG& self) { return self.to_string(); });

  nb::class_<P, GateOperation>(m, "P")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &P::to_matrix)
      .def("default_decompose", &P::default_decompose)
      .def("__repr__", [](const P& self) { return self.to_string(); });

  nb::class_<R, GateOperation>(m, "R")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &R::to_matrix)
      .def("default_decompose", &R::default_decompose)
      .def("__repr__", [](const R& self) { return self.to_string(); });

  nb::class_<RX, GateOperation>(m, "RX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RX::to_matrix)
      .def("default_decompose", &RX::default_decompose)
      .def("__repr__", [](const RX& self) { return self.to_string(); });

  nb::class_<RY, GateOperation>(m, "RY")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RY::to_matrix)
      .def("default_decompose", &RY::default_decompose)
      .def("__repr__", [](const RY& self) { return self.to_string(); });

  nb::class_<RZ, GateOperation>(m, "RZ")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &RZ::to_matrix)
      .def("default_decompose", &RZ::default_decompose)
      .def("__repr__", [](const RZ& self) { return self.to_string(); });

  nb::class_<SX, GateOperation>(m, "SX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SX::to_matrix)
      .def("default_decompose", &SX::default_decompose)
      .def("__repr__", [](const SX& self) { return self.to_string(); });

  nb::class_<SXDG, GateOperation>(m, "SXDG")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &SXDG::to_matrix)
      .def("default_decompose", &SXDG::default_decompose)
      .def("__repr__", [](const SXDG& self) { return self.to_string(); });

  nb::class_<CZ, GateOperation>(m, "CZ")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CZ::to_matrix)
      .def("default_decompose", &CZ::default_decompose)
      .def("__repr__", [](const CZ& self) { return self.to_string(); });

  nb::class_<CX, GateOperation>(m, "CX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CX::to_matrix)
      .def("default_decompose", &CX::default_decompose)
      .def("__repr__", [](const CX& self) { return self.to_string(); });

  nb::class_<CY, GateOperation>(m, "CY")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CY::to_matrix)
      .def("default_decompose", &CY::default_decompose)
      .def("__repr__", [](const CY& self) { return self.to_string(); });

  nb::class_<SWAP, GateOperation>(m, "SWAP")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &SWAP::to_matrix)
      .def("default_decompose", &SWAP::default_decompose)
      .def("__repr__", [](const SWAP& self) { return self.to_string(); });

  nb::class_<ISWAP, GateOperation>(m, "ISWAP")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &ISWAP::to_matrix)
      .def("default_decompose", &ISWAP::default_decompose)
      .def("__repr__", [](const ISWAP& self) { return self.to_string(); });

  nb::class_<CH, GateOperation>(m, "CH")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CH::to_matrix)
      .def("default_decompose", &CH::default_decompose)
      .def("__repr__", [](const CH& self) { return self.to_string(); });

  nb::class_<CS, GateOperation>(m, "CS")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CS::to_matrix)
      .def("default_decompose", &CS::default_decompose)
      .def("__repr__", [](const CS& self) { return self.to_string(); });

  nb::class_<CSDG, GateOperation>(m, "CSDG")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CSDG::to_matrix)
      .def("default_decompose", &CSDG::default_decompose)
      .def("__repr__", [](const CSDG& self) { return self.to_string(); });

  nb::class_<CRX, GateOperation>(m, "CRX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CRX::to_matrix)
      .def("default_decompose", &CRX::default_decompose)
      .def("__repr__", [](const CRX& self) { return self.to_string(); });

  nb::class_<CRY, GateOperation>(m, "CRY")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CRY::to_matrix)
      .def("default_decompose", &CRY::default_decompose)
      .def("__repr__", [](const CRY& self) { return self.to_string(); });

  nb::class_<CRZ, GateOperation>(m, "CRZ")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CRZ::to_matrix)
      .def("default_decompose", &CRZ::default_decompose)
      .def("__repr__", [](const CRZ& self) { return self.to_string(); });

  nb::class_<CU1, GateOperation>(m, "CU1")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CU1::to_matrix)
      .def("default_decompose", &CU1::default_decompose)
      .def("__repr__", [](const CU1& self) { return self.to_string(); });

  nb::class_<CP, GateOperation>(m, "CP")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CP::to_matrix)
      .def("default_decompose", &CP::default_decompose)
      .def("__repr__", [](const CP& self) { return self.to_string(); });

  nb::class_<CU3, GateOperation>(m, "CU3")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CU3::to_matrix)
      .def("default_decompose", &CU3::default_decompose)
      .def("__repr__", [](const CU3& self) { return self.to_string(); });

  nb::class_<CSX, GateOperation>(m, "CSX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CSX::to_matrix)
      .def("default_decompose", &CSX::default_decompose)
      .def("__repr__", [](const CSX& self) { return self.to_string(); });

  nb::class_<CU, GateOperation>(m, "CU")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CU::to_matrix)
      .def("default_decompose", &CU::default_decompose)
      .def("__repr__", [](const CU& self) { return self.to_string(); });

  nb::class_<ECR, GateOperation>(m, "ECR")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &ECR::to_matrix)
      .def("default_decompose", &ECR::default_decompose)
      .def("__repr__", [](const ECR& self) { return self.to_string(); });

  nb::class_<DCX, GateOperation>(m, "DCX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &DCX::to_matrix)
      .def("default_decompose", &DCX::default_decompose)
      .def("__repr__", [](const DCX& self) { return self.to_string(); });

  nb::class_<RXX, GateOperation>(m, "RXX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RXX::to_matrix)
      .def("default_decompose", &RXX::default_decompose)
      .def("__repr__", [](const RXX& self) { return self.to_string(); });

  nb::class_<RYY, GateOperation>(m, "RYY")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RYY::to_matrix)
      .def("default_decompose", &RYY::default_decompose)
      .def("__repr__", [](const RYY& self) { return self.to_string(); });

  nb::class_<RZZ, GateOperation>(m, "RZZ")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RZZ::to_matrix)
      .def("default_decompose", &RZZ::default_decompose)
      .def("__repr__", [](const RZZ& self) { return self.to_string(); });

  nb::class_<RZX, GateOperation>(m, "RZX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RZX::to_matrix)
      .def("default_decompose", &RZX::default_decompose)
      .def("__repr__", [](const RZX& self) { return self.to_string(); });

  nb::class_<CCX, GateOperation>(m, "CCX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CCX::to_matrix)
      .def("decompose_to_1q2q", &CCX::decompose_to_1q2q)
      .def("default_decompose", &CCX::default_decompose)
      .def("__repr__", [](const CCX& self) { return self.to_string(); });

  nb::class_<CCZ, GateOperation>(m, "CCZ")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CCZ::to_matrix)
      .def("decompose_to_1q2q", &CCZ::decompose_to_1q2q)
      .def("default_decompose", &CCZ::default_decompose)
      .def("__repr__", [](const CCZ& self) { return self.to_string(); });

  nb::class_<CSWAP, GateOperation>(m, "CSWAP")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &CSWAP::to_matrix)
      .def("decompose_to_1q2q", &CSWAP::decompose_to_1q2q)
      .def("default_decompose", &CSWAP::default_decompose)
      .def("__repr__", [](const CSWAP& self) { return self.to_string(); });

  nb::class_<RCCX, GateOperation>(m, "RCCX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RCCX::to_matrix)
      .def("decompose_to_1q2q", &RCCX::decompose_to_1q2q)
      .def("default_decompose", &RCCX::default_decompose)
      .def("__repr__", [](const RCCX& self) { return self.to_string(); });

  nb::class_<RC3X, GateOperation>(m, "RC3X")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &RC3X::to_matrix)
      .def("decompose_to_1q2q", &RC3X::decompose_to_1q2q)
      .def("default_decompose", &RC3X::default_decompose)
      .def("__repr__", [](const RC3X& self) { return self.to_string(); });

  nb::class_<C3X, GateOperation>(m, "C3X")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &C3X::to_matrix)
      .def("decompose_to_1q2q", &C3X::decompose_to_1q2q)
      .def("default_decompose", &C3X::default_decompose)
      .def("__repr__", [](const C3X& self) { return self.to_string(); });

  nb::class_<C3SQRTX, GateOperation>(m, "C3SQRTX")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &C3SQRTX::to_matrix)
      .def("decompose_to_1q2q", &C3SQRTX::decompose_to_1q2q)
      .def("default_decompose", &C3SQRTX::default_decompose)
      .def("__repr__", [](const C3SQRTX& self) { return self.to_string(); });

  nb::class_<C4X, GateOperation>(m, "C4X")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("to_matrix", &C4X::to_matrix)
      .def("decompose_to_1q2q", &C4X::decompose_to_1q2q)
      .def("default_decompose", &C4X::default_decompose)
      .def("__repr__", [](const C4X& self) { return self.to_string(); });

  nb::class_<U1, GateOperation>(m, "U1")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U1::to_matrix)
      .def("default_decompose", &U1::default_decompose)
      .def("__repr__", [](const U1& self) { return self.to_string(); });

  nb::class_<U2, GateOperation>(m, "U2")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U2::to_matrix)
      .def("default_decompose", &U2::default_decompose)
      .def("__repr__", [](const U2& self) { return self.to_string(); });

  nb::class_<U3, GateOperation>(m, "U3")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U3::to_matrix)
      .def("default_decompose", &U3::default_decompose)
      .def("__repr__", [](const U3& self) { return self.to_string(); });

  nb::class_<U, GateOperation>(m, "U")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def("to_matrix", &U::to_matrix)
      .def("default_decompose", &U::default_decompose)
      .def("__repr__", [](const U& self) { return self.to_string(); });

  nb::class_<Sync, BaseOperation>(m, "Sync")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("__repr__", [](const Sync& self) { return self.to_string(); });

  nb::class_<Measure, BaseOperation>(m, "Measure")
      .def(nb::init<std::vector<int>, std::vector<int>, OperationType>(),
           nb::arg("targets"), nb::arg("cbits") = std::vector<int>{},
           nb::arg("operation_type") = OperationType::MEASURE)
      .def_prop_rw(
          "cbits", [](const Measure& self) { return self.cbits; },
          [](Measure& self, const std::vector<int>& cb) { self.cbits = cb; })
      .def("__repr__", [](const Measure& self) { return self.to_string(); });

  nb::class_<Move, BaseOperation>(m, "Move")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("__repr__", [](const Move& self) { return self.to_string(); });

  nb::class_<Reset, BaseOperation>(m, "Reset")
      .def(nb::init<std::vector<int>, std::vector<double>>(),
           nb::arg("targets"), nb::arg("arg_value") = std::vector<double>())
      .def(nb::init<std::vector<int>, std::vector<double>, OperationType>(),
           nb::arg("targets"), nb::arg("arg_value"), nb::arg("operation_type"))
      .def("__repr__", [](const Reset& self) { return self.to_string(); });

  m.def(
      "create_gate",
      [](std::string name, std::vector<int> targets,
         std::vector<double> arg_value, bool allow_undefined) {
        return create_gate(name, std::move(targets), std::move(arg_value),
                           allow_undefined);
      },
      nb::arg("name"), nb::arg("targets") = std::vector<int>(),
      nb::arg("arg_value") = std::vector<double>(),
      nb::arg("allow_undefined") = false,
      "Create a gate or operation instance by name.");

  nb::class_<QuantumCircuit>(m, "QuantumCircuit")
      .def(nb::init<int, int, double>(), nb::arg("num_qubits") = 0,
           nb::arg("num_clbits") = 0, nb::arg("global_phase") = 0.0)
      .def_static("from_ir", &QuantumCircuit::from_ir, nb::arg("ir"),
                  nb::arg("num_qubits") = 0)
      .def(
          "append",
          [](QuantumCircuit& self, std::shared_ptr<BaseOperation> op) {
            self.append(std::move(op));
          },
          nb::arg("operation"))
      .def("append_operations", &QuantumCircuit::append_operations,
           nb::arg("operations"))
      .def("get_operations", &QuantumCircuit::get_operations)
      .def("num_qubits", &QuantumCircuit::num_qubits)
      .def("num_clbits", &QuantumCircuit::num_clbits)
      .def("global_phase", &QuantumCircuit::global_phase)
      .def("set_global_phase", &QuantumCircuit::set_global_phase,
           nb::arg("phase"))
      .def("set_num_qubits", &QuantumCircuit::set_num_qubits,
           nb::arg("num_qubits"))
      .def("set_num_clbits", &QuantumCircuit::set_num_clbits,
           nb::arg("num_clbits"))
      .def("depth", &QuantumCircuit::depth)
      .def("width", &QuantumCircuit::width)
      .def("size", &QuantumCircuit::size)
      .def("__repr__",
           [](const QuantumCircuit& self) {
             return "QuantumCircuit(num_qubits=" +
                    std::to_string(self.num_qubits()) +
                    ", num_clbits=" + std::to_string(self.num_clbits()) +
                    ", size=" + std::to_string(self.size()) + ")";
           })
      .def("__deepcopy__", [](const QuantumCircuit& self, nb::dict) {
        auto copy = std::make_unique<QuantumCircuit>(
            self.num_qubits(), self.num_clbits(), self.global_phase());
        copy->append_operations(self.get_operations());
        return copy;
      });

  m.def(
       "to_qasm2",
       [](const QuantumCircuit& circuit) {
         return qcos::to_qasm2(circuit.get_operations());
       },
       nb::arg("circuit"))
      .def(
          "to_qasm2",
          [](const std::vector<std::shared_ptr<BaseOperation>>& operations) {
            return qcos::to_qasm2(operations);
          },
          nb::arg("operations"))
      .def(
          "to_qasm3",
          [](const QuantumCircuit& circuit) {
            return qcos::to_qasm3(circuit.get_operations());
          },
          nb::arg("circuit"))
      .def(
          "to_qasm3",
          [](const std::vector<std::shared_ptr<BaseOperation>>& operations) {
            return qcos::to_qasm3(operations);
          },
          nb::arg("operations"))
      .def(
          "save_qasm",
          [](const std::string& path, const QuantumCircuit& circuit,
             const std::string& version) {
            qcos::save_qasm(path, circuit.get_operations(), version);
          },
          nb::arg("path"), nb::arg("circuit"), nb::arg("version") = "2.0");
}
