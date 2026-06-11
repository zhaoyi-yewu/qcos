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

#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "circuit/base_operation.h"
#include "optimizer/gate_optimizer.h"

namespace py = pybind11;
using namespace qcos;

void bind_optimizer(py::module_& m) {
  m.def("optimize", &optimize, py::arg("ir"), py::arg("opt_level") = 1,
        py::arg("verbose") = false, py::arg("basis_gates") = std::nullopt,
        R"pbdoc(
对 IR 执行优化.

opt_level:
  0 - 不做优化
  1 - InverseCancellation + AdjacentPhaseOptPass
  2 - Level 1 + EquivalencePass
  3 - Level 2 + CliffordRzOptimization

Args:
    ir (list[BaseOperation]): 待优化的操作序列
    opt_level (int, optional): 优化级别. Defaults to 1.
    verbose (bool, optional): 是否打印优化详情. Defaults to False.
    basis_gates (set[str] | None, optional): basis gate 过滤集合.

Returns:
    list[BaseOperation]: 优化后的操作序列
)pbdoc");
}
