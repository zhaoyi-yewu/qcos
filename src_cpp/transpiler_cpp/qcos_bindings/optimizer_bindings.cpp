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
#include <nanobind/stl/map.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/set.h>
#include <nanobind/stl/shared_ptr.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include <map>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "circuit/base_operation.h"
#include "circuit/qasm_converter.h"
#include "compiler/qasm_to_ir.hpp"
#include "optimizer/gate_optimizer.h"

namespace nb = nanobind;
using namespace qcos;

void bind_optimizer(nb::module_& m) {
  nb::class_<OptimizeMetrics>(m, "OptimizeMetrics")
      .def_ro("pass_time_ms", &OptimizeMetrics::pass_time_ms,
              "各 pass 耗时 (ms)")
      .def_ro("pass_reduced", &OptimizeMetrics::pass_reduced,
              "各 pass 减少的门数");

  m.def(
      "optimize",
      [](const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level,
         bool verbose, const std::optional<std::set<std::string>>& basis_gates,
         size_t num_threads, bool fast_mode) {
        nb::gil_scoped_release release;
        return optimize(ir, opt_level, verbose, basis_gates, num_threads,
                        fast_mode);
      },
      nb::arg("ir"), nb::arg("opt_level") = 1, nb::arg("verbose") = false,
      nb::arg("basis_gates") = std::nullopt, nb::arg("num_threads") = 1,
      nb::arg("fast_mode") = false,
      R"(
        对 IR 执行优化.

        opt_level:
          0 - 不做优化
          1 - InverseCancellation + AdjacentPhaseOptPass + EquivalencePass
          2 - Level 1 + HadamardGateReduction + RzCommuteOptimization
              + CxCommuteOptimization + PhasePolynomialMerging
          3 - Level 2 + UnitarySynthesis

        num_threads:
          1 - 串行（默认）
          0 - 自动并行（线程数取硬件并发数）
          >1 - 指定线程数并行

        Args:
            ir (list[BaseOperation]): 待优化的操作序列
            opt_level (int, optional): 优化级别. Defaults to 1.
            verbose (bool, optional): 是否打印优化详情. Defaults to False.
            basis_gates (set[str] | None, optional): basis gate 过滤集合.
            num_threads (int, optional): 并行线程数：1=串行，0=自动，>1=指定. Defaults to 1.
            fast_mode (bool, optional): true=只跑一轮, false=跑到收敛. Defaults to False.

        Returns:
            list[BaseOperation]: 优化后的操作序列
      )");

  m.def(
      "optimize_with_analysis",
      [](const std::vector<std::shared_ptr<BaseOperation>>& ir, int opt_level,
         bool verbose, const std::optional<std::set<std::string>>& basis_gates,
         size_t num_threads, bool fast_mode) {
        OptimizeMetrics metrics;
        std::vector<std::shared_ptr<BaseOperation>> result;
        {
          nb::gil_scoped_release release;
          result = optimize(ir, opt_level, verbose, basis_gates, num_threads,
                            fast_mode, &metrics, true);
        }
        return nb::make_tuple(nb::cast(result), nb::cast(metrics));
      },
      nb::arg("ir"), nb::arg("opt_level") = 1, nb::arg("verbose") = false,
      nb::arg("basis_gates") = std::nullopt, nb::arg("num_threads") = 1,
      nb::arg("fast_mode") = false,
      R"(
        执行优化并返回逐 pass 统计信息.

        参数同 optimize, 额外启用 analysis 模式：
        逐 pass 记录耗时和减少门数（仅串行模式有效）。

        Returns:
            tuple[list[BaseOperation], OptimizeMetrics]:
                (optimized_ops, metrics)
     )");

  m.def(
      "optimize_qasm",
      [](const std::string& qasm_str, int opt_level,
         const std::optional<std::set<std::string>>& basis_gates) {
        nb::gil_scoped_release release;
        auto [ops, _] = qasm_to_ir(qasm_str);
        auto optimized =
            optimize(ops, opt_level, false, basis_gates, 1, false);
        // Detect QASM version from the version declaration line only.
        // Match "OPENQASM 3" at the first non-whitespace position, not
        // anywhere in comments or string literals.
        size_t pos = qasm_str.find_first_not_of(" \t\n\r");
        if (pos != std::string::npos &&
            qasm_str.compare(pos, 10, "OPENQASM 3") == 0) {
          return to_qasm3(optimized);
        }
        return to_qasm2(optimized);
      },
      nb::arg("qasm_str"), nb::arg("opt_level") = 1,
      nb::arg("basis_gates") = std::nullopt,
      R"(
        Optimize a QASM circuit string and return the optimized QASM string.

        Parses the input QASM, runs optimization passes, and converts back
        to the same QASM version as the input — without routing or gate
        decomposition.

        Args:
            qasm_str: OpenQASM 2.0/3.0 circuit string.
            opt_level: Optimization level 0-3, default 1.
            basis_gates: Gate filter set. None = preserve original gate set.

        Returns:
            str: Optimized OpenQASM string (2.0 or 3.0).
      )");
}
