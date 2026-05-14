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

#include "compiler/definitions.hpp"
#include "compiler/operations/control.hpp"
#include "compiler/operations/op_type.hpp"
#include "compiler/operations/operation.hpp"
#include "compiler/qasm_to_origin_ir.hpp"

namespace py = pybind11;
using namespace qc;

void bind_parser(py::module_& m) {
  py::enum_<Control::Type>(m, "ControlType")
      .value("Pos", Control::Type::Pos)
      .value("Neg", Control::Type::Neg)
      .export_values();

  py::class_<Control>(m, "Control")
      // 构造函数：Control(QBit q=..., ControlType t=ControlType.Pos)
      .def(py::init<const QBit, const Control::Type>(), py::arg("qubit") = 0,
           py::arg("type") = true)
      // 绑定成员变量
      .def_readwrite("qubit", &Control::qubit)
      .def_readwrite("type", &Control::type)
      // 绑定 toString() -> Python __str__
      .def("__str__", &Control::toString)
      .def("__repr__", &Control::toString);

  py::enum_<qc::OpType>(m, "OpType")
      .value("otNone", qc::OpType::otNone)
      .value("otGPhase", qc::OpType::otGPhase)
      .value("otI", qc::OpType::otI)
      .value("otBarrier", qc::OpType::otBarrier)
      .value("otH", qc::OpType::otH)
      .value("otX", qc::OpType::otX)
      .value("otY", qc::OpType::otY)
      .value("otZ", qc::OpType::otZ)
      .value("otS", qc::OpType::otS)
      .value("otSdg", qc::OpType::otSdg)
      .value("otT", qc::OpType::otT)
      .value("otTdg", qc::OpType::otTdg)
      .value("otV", qc::OpType::otV)
      .value("otVdg", qc::OpType::otVdg)
      .value("otU", qc::OpType::otU)
      .value("otU2", qc::OpType::otU2)
      .value("otP", qc::OpType::otP)
      .value("otSX", qc::OpType::otSX)
      .value("otSXdg", qc::OpType::otSXdg)
      .value("otRX", qc::OpType::otRX)
      .value("otRY", qc::OpType::otRY)
      .value("otRZ", qc::OpType::otRZ)
      .value("otSWAP", qc::OpType::otSWAP)
      .value("ot_iSWAP", qc::OpType::ot_iSWAP)
      .value("ot_iSWAPdg", qc::OpType::ot_iSWAPdg)
      .value("otPeres", qc::OpType::otPeres)
      .value("otPeresdg", qc::OpType::otPeresdg)
      .value("otDCX", qc::OpType::otDCX)
      .value("otECR", qc::OpType::otECR)
      .value("otRXX", qc::OpType::otRXX)
      .value("otRYY", qc::OpType::otRYY)
      .value("otRZZ", qc::OpType::otRZZ)
      .value("otRZX", qc::OpType::otRZX)
      .value("otXXminusYY", qc::OpType::otXXminusYY)
      .value("otXXplusYY", qc::OpType::otXXplusYY)
      .value("otCompound", qc::OpType::otCompound)
      .value("otMeasure", qc::OpType::otMeasure)
      .value("otReset", qc::OpType::otReset)
      .value("otTeleportation", qc::OpType::otTeleportation)
      .value("otClassicControlled", qc::OpType::otClassicControlled)
      .value("otATrue", qc::OpType::otATrue)
      .value("otAFalse", qc::OpType::otAFalse)
      .value("otMultiATrue", qc::OpType::otMultiATrue)
      .value("otMultiAFalse", qc::OpType::otMultiAFalse)
      .value("otOpCount", qc::OpType::otOpCount)
      // fj add
      .value("otCNOT", qc::OpType::otCNOT)
      .value("otTOFFOLI", qc::OpType::otTOFFOLI)
      .value("otCZ", qc::OpType::otCZ)
      .value("otU3", qc::OpType::otU3)
      .value("otCU", qc::OpType::otCU)
      .value("otU1", qc::OpType::otU1)
      .value("otCH", qc::OpType::otCH)
      .value("otCRX", qc::OpType::otCRX)
      .value("otCRY", qc::OpType::otCRY)
      .value("otCRZ", qc::OpType::otCRZ)
      .value("otRCCX", qc::OpType::otRCCX)
      .value("otRC3X", qc::OpType::otRC3X)
      .value("otCP", qc::OpType::otCP)
      .value("otCSWAP", qc::OpType::otCSWAP)
      .value("otC3X", qc::OpType::otC3X)
      .value("otCY", qc::OpType::otCY)
      .value("otCSX", qc::OpType::otCSX)
      .value("otC3SQRTX", qc::OpType::otC3SQRTX)
      .value("otCU3", qc::OpType::otCU3)
      .value("otC4X", qc::OpType::otC4X)
      .value("otCS", qc::OpType::otCS)
      .value("otCSdg", qc::OpType::otCSdg)
      .value("otCCZ", qc::OpType::otCCZ)
      .value("otR", qc::OpType::otR)
      .value("otW", qc::OpType::otW)
      .export_values();

  py::class_<Operation>(m, "Operation")
      .def_readonly("controls", &Operation::controls)
      .def_readonly("targets", &Operation::targets)
      .def_readonly("parameter", &Operation::parameter)
      .def_readonly("type", &Operation::type)
      .def_readonly("name", &Operation::name);

  m.def("convert_qasm_string_to_operations",
        &convert_qasm_string_to_operations,
        R"(
            将QASM字符串转换为操作列表
                
            Args:
                qasm_str: QASM格式的量子电路字符串
                
            Returns:
                返回解析得到的量子操作列表
                
            Example:
                >>> import high_performance
                >>> qasm = "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0], q[1];"
                >>> ops = high_performance.convert_qasm_string_to_operations(qasm)
                >>> print(f"解析到 {len(ops)} 个操作")
        )",
        py::arg("qasm_str"));

  m.def("convert_qasm_string_to_qcos_operations",
        &convert_qasm_string_to_qcos_operations,
        R"(
            将QASM字符串转换为操作列表

            Args:
                qasm_str: QASM格式的量子电路字符串

            Returns:
                返回解析得到的量子操作列表

            Example:
                >>> import high_performance
                >>> qasm = "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0], q[1];"
                >>> ops, num_qubits = high_performance.convert_qasm_string_to_qcos_operations(qasm)
                >>> print(f"解析到 {len(ops)} 个操作")
        )",
        py::arg("qasm_str"));
}