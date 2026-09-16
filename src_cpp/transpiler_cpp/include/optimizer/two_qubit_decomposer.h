/*
 * ----------------------------------------------------------------------
 * Copyright(c) 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * You can use this software according to the terms and conditions
 * of the Mulan PSL v2.
 * You may obtain a copy of Mulan PSL v2 at:
 *          http://license.coscl.org.cn/MulanPSL2
 * THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
 *      WITHOUT WARRANTIES OF ANY KIND,
 *      EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 *      MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#pragma once

#include <array>
#include <memory>
#include <optional>
#include <set>
#include <string>
#include <vector>

#include "optimizer/matrix_utils.h"

namespace qcos {

// ========================================================================
// Two-Qubit Weyl Decomposition
// ========================================================================

struct TwoQubitDecomp {
  CMatrix k1, k2, k3, k4;  // SU(2) matrices: U = (k1 x k2) . Ud . (k3 x k4)
  double cx, cy, cz;        // Weyl coordinates
  int num_cx;               // Estimated minimum CNOT gates needed
  double global_phase;      // Global phase of the decomposition
};

// Decompose a 4x4 unitary matrix into Weyl coordinates and K matrices
TwoQubitDecomp decompose_two_qubit(const CMatrix& u);

// Decompose a 2-qubit unitary into basis gates
std::vector<std::shared_ptr<BaseOperation>>
two_qubit_unitary_to_basis(
    const CMatrix& u, int qubit0, int qubit1,
    const std::optional<std::set<std::string>>& basis_gates = std::nullopt);

}  // namespace qcos
