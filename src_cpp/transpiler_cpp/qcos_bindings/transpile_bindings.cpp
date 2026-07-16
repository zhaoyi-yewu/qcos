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
#include <nanobind/stl/vector.h>

#include "transpile/transpile.h"

namespace nb = nanobind;
using namespace qcos;

void bind_transpile(nb::module_& m) {
  // 绑定 TranspileTimings — 各阶段耗时记录
  nb::class_<TranspileTimings>(m, "TranspileTimings",
                               "Timing breakdown for each transpile stage.")
      .def(nb::init<>())
      .def_rw("parse_time", &TranspileTimings::parse_time)
      .def_rw("opt_time1", &TranspileTimings::opt_time1)
      .def_rw("decompose_1q2q_time", &TranspileTimings::decompose_1q2q_time)
      .def_rw("decompose_rule_time", &TranspileTimings::decompose_rule_time)
      .def_rw("mapping_time", &TranspileTimings::mapping_time)
      .def_rw("decompose_apply_time", &TranspileTimings::decompose_apply_time)
      .def_rw("decomposed_time", &TranspileTimings::decomposed_time)
      .def_rw("opt_time2", &TranspileTimings::opt_time2)
      .def_rw("transpile_time", &TranspileTimings::transpile_time)
      .def_rw("total_time", &TranspileTimings::total_time);

  // 绑定 TranspileResult — transpile 函数返回值
  nb::class_<TranspileResult>(m, "TranspileResult",
                              "Result of the all-in-one transpile function.")
      .def(nb::init<>())
      .def_rw("basis_gate_list", &TranspileResult::basis_gate_list)
      .def_rw("num_qubits", &TranspileResult::num_qubits)
      .def_rw("timings", &TranspileResult::timings);

  // 绑定 transpile 函数 — 释放 GIL 以允许 Python 侧并发
  m.def(
      "transpile",
      [](const std::string& qasm_string,
         const std::vector<std::string>& supp_basis_gates,
         const std::vector<std::pair<int, int>>& coupling_list, int opt_level,
         const std::vector<double>& edge_fidelities,
         const std::vector<double>& single_qubit_fidelities) {
        nb::gil_scoped_release release;
        return transpile(qasm_string, supp_basis_gates, coupling_list,
                         opt_level, edge_fidelities, single_qubit_fidelities);
      },
      nb::arg("qasm_string"), nb::arg("supp_basis_gates"),
      nb::arg("coupling_list"), nb::arg("opt_level") = 1,
      nb::arg("edge_fidelities") = std::vector<double>{},
      nb::arg("single_qubit_fidelities") = std::vector<double>{},
      R"(
        All-in-one transpile function (sabre routing, single-circuit path).

        Combines parse + transpile into a single C++ call, avoiding intermediate
        Python/C++ data transfer overhead.

        Args:
            qasm_string (str): QASM circuit string.
            supp_basis_gates (list[str]): Supported basis gate names.
            coupling_list (list[tuple[int, int]]): Physical qubit coupling edges
                (must be pre-normalized via normalize_topology).
            opt_level (int, optional): Optimization level (0-3). Defaults to 1.
            edge_fidelities (list[float], optional): Edge fidelity values
                corresponding to coupling_list. Empty means not used.
            single_qubit_fidelities (list[float], optional): Single-qubit
                fidelity array indexed by physical qubit ID. Empty means not used.

        Returns:
            TranspileResult: Contains basis_gate_list, num_qubits, and timings.
              )");
}
