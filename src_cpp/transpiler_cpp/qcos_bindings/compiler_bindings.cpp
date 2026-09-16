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
