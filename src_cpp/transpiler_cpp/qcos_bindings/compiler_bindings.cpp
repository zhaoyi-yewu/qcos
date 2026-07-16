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
#include <nanobind/stl/optional.h>
#include <nanobind/stl/pair.h>
#include <nanobind/stl/set.h>
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "compiler/definitions.hpp"
#include "compiler/operations/control.hpp"
#include "compiler/operations/op_type.hpp"
#include "compiler/operations/operation.hpp"
#include "compiler/qasm_to_ir.hpp"

namespace nb = nanobind;
using namespace qc;

void bind_parser(nb::module_& m) {
  nb::enum_<Control::Type>(m, "ControlType")
      .value("Pos", Control::Type::Pos)
      .value("Neg", Control::Type::Neg)
      .export_values();

  nb::class_<Control>(m, "Control")
      // 构造函数：Control(QBit q=..., ControlType t=ControlType.Pos)
      .def(nb::init<const QBit, const Control::Type>(), nb::arg("qubit") = 0,
           nb::arg("type") = true)
      // 绑定成员变量
      .def_rw("qubit", &Control::qubit)
      .def_rw("type", &Control::type)
      // 绑定 toString() -> Python __str__
      .def("__str__", &Control::toString)
      .def("__repr__", &Control::toString);

  nb::enum_<qc::OpType>(m, "OpType")
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

  nb::class_<Operation>(m, "Operation")
      .def_ro("controls", &Operation::controls)
      .def_ro("targets", &Operation::targets)
      .def_ro("parameter", &Operation::parameter)
      .def_ro("type", &Operation::type)
      .def_ro("name", &Operation::name);

  m.def(
      "qasm_to_ir",
      [](const std::string& qasm_str) {
        nb::gil_scoped_release release;
        return qasm_to_ir(qasm_str);
      },
      R"(
            将QASM字符串转换为操作列表

            Args:
                qasm_str: QASM格式的量子电路字符串

            Returns:
                返回解析得到的量子操作列表

            Example:
                >>> import high_performance
                >>> qasm = "OPENQASM 2.0; qreg q[2]; h q[0]; cx q[0], q[1];"
                >>> ops, num_qubits = high_performance.qasm_to_ir(qasm)
                >>> print(f"解析到 {len(ops)} 个操作")
        )",
      nb::arg("qasm_str"));
}
