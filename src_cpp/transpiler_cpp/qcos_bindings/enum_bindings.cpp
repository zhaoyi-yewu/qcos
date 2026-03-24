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

#include "circuit/base_operation.h"

namespace py = pybind11;
using namespace qcos;

void bind_enums(py::module_& m) {
  py::enum_<OperationType>(m, "OperationType")
      .value("MEASURE", OperationType::MEASURE)
      .value("SINGLE_QUBIT_OPERATION", OperationType::SINGLE_QUBIT_OPERATION)
      .value("DOUBLE_QUBIT_OPERATION", OperationType::DOUBLE_QUBIT_OPERATION)
      .value("TRIPLE_QUBIT_OPERATION", OperationType::TRIPLE_QUBIT_OPERATION)
      .value("FOUR_QUBIT_OPERATION", OperationType::FOUR_QUBIT_OPERATION)
      .value("FIVE_QUBIT_OPERATION", OperationType::FIVE_QUBIT_OPERATION)
      .value("SYNC", OperationType::SYNC)
      .value("MOVE", OperationType::MOVE)
      .export_values();
}