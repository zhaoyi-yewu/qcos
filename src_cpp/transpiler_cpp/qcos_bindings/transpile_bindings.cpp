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

#include <stdexcept>

#include "mapping/na_mapping.h"
#include "transpile/transpile.h"

namespace nb = nanobind;
using namespace qcos;

namespace {

/// Parse NAQpuConfig from a Python dict.
NAQpuConfig parse_na_qpu_config(const nb::dict& qpu_cfg) {
  NAQpuConfig cfg;
  nb::list storage_area = nb::cast<nb::list>(qpu_cfg["storage_area"]);
  for (auto pos : storage_area) {
    cfg.storage_area.push_back(nb::cast<std::string>(pos));
  }
  nb::list operate_area = nb::cast<nb::list>(qpu_cfg["operate_area"]);
  for (auto pos : operate_area) {
    cfg.operate_area.push_back(nb::cast<std::string>(pos));
  }
  nb::dict coupler_map = nb::cast<nb::dict>(qpu_cfg["coupler_map"]);
  for (auto item : coupler_map) {
    auto endpoints = nb::cast<std::vector<std::string>>(item.second);
    if (endpoints.size() != 2) {
      throw std::invalid_argument("coupler_map entry must have 2 endpoints");
    }
    cfg.coupler_map.emplace_back(std::string(""),
                                 std::make_pair(endpoints[0], endpoints[1]));
  }
  nb::dict readout_error = nb::cast<nb::dict>(qpu_cfg["readout_error"]);
  for (auto item : readout_error) {
    auto pos = nb::cast<std::string>(item.first);
    auto err = nb::cast<double>(item.second);
    cfg.readout_error[pos] = err;
  }
  return cfg;
}

}  // namespace

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
         const std::vector<std::string>& supp_basis_gates, int opt_level,
         const std::vector<std::pair<int, int>>& coupling_list,
         const std::vector<double>& edge_fidelities,
         const std::vector<double>& single_qubit_fidelities,
         const std::string& layout_method, size_t num_threads, bool fast_mode,
         double fidelity_threshold, double fidelity_weight) {
        nb::gil_scoped_release release;
        return transpile(qasm_string, supp_basis_gates, opt_level,
                         coupling_list, edge_fidelities,
                         single_qubit_fidelities, layout_method, num_threads,
                         fast_mode, fidelity_threshold, fidelity_weight);
      },
      nb::arg("qasm_string"), nb::arg("supp_basis_gates"),
      nb::arg("opt_level") = 1,
      nb::arg("coupling_list") = std::vector<std::pair<int, int>>{},
      nb::arg("edge_fidelities") = std::vector<double>{},
      nb::arg("single_qubit_fidelities") = std::vector<double>{},
      nb::arg("layout_method") = "vf2_layout", nb::arg("num_threads") = 0,
      nb::arg("fast_mode") = true, nb::arg("fidelity_threshold") = -1.0,
      nb::arg("fidelity_weight") = 0.5,
      R"(
        All-in-one transpile function (sabre routing, single-circuit path).

        Combines parse + transpile into a single C++ call, avoiding intermediate
        Python/C++ data transfer overhead.

        Args:
            qasm_string (str): QASM circuit string.
            supp_basis_gates (list[str]): Supported basis gate names.
            opt_level (int, optional): Optimization level (0-3). Defaults to 1.
            coupling_list (list[tuple[int, int]], optional): Physical qubit coupling edges
                (must be pre-normalized via normalize_topology). Empty means skip routing.
            edge_fidelities (list[float], optional): Edge fidelity values
                corresponding to coupling_list. Empty means not used.
            single_qubit_fidelities (list[float], optional): Single-qubit
                fidelity array indexed by physical qubit ID. Empty means not used.
            layout_method (str, optional): Initial layout method: "vf2_layout"
                (default) or "dense_layout".
            num_threads (int, optional): Optimization thread count. 0 = auto
                (hardware_concurrency), 1 = serial, >1 = explicit. Defaults to 0.
            fast_mode (bool, optional): Optimization fast mode. True = run pass
                list only once. Defaults to True.
            fidelity_threshold (float, optional): Fidelity threshold; edges
                below this value are filtered out. Negative value means adaptive
                calculation (mean - std, clamped to [0.3, 0.9]).
                Defaults to -1.0 (adaptive).
            fidelity_weight (float, optional): DenseLayout fidelity weight in [0, 1].
                0.0 = pure density, 1.0 = pure fidelity. Defaults to 0.5.

        Returns:
            TranspileResult: Contains basis_gate_list, num_qubits, and timings.
              )");

  // Bind transpile_na — neutral-atom NA mapping, single-circuit path.
  m.def(
      "transpile_na",
      [](const std::string& qasm_string,
         const std::vector<std::string>& supp_basis_gates,
         const nb::dict& qpu_cfg, int opt_level) {
        auto cfg = parse_na_qpu_config(qpu_cfg);
        nb::gil_scoped_release release;
        return transpile_na(qasm_string, supp_basis_gates, cfg, opt_level);
      },
      nb::arg("qasm_string"), nb::arg("supp_basis_gates"), nb::arg("qpu_cfg"),
      nb::arg("opt_level") = 1,
      R"(
        All-in-one transpile function (neutral-atom NA mapping, single-circuit path).

        Same pipeline as ``transpile`` (sabre) but the routing stage uses
        NARoute, inserting MOVE operations between the storage and operate
        areas so that two-qubit gates act on adjacent sites.

        Args:
            qasm_string (str): QASM circuit string.
            supp_basis_gates (list[str]): Supported basis gate names.
            qpu_cfg (dict): Neutral-atom QPU configuration with keys
                ``storage_area``, ``operate_area``, ``coupler_map`` and
                ``readout_error``.
            opt_level (int, optional): Optimization level (0-3). Defaults to 1.

        Returns:
            TranspileResult: Contains basis_gate_list, num_qubits, and timings.
      )");
}
