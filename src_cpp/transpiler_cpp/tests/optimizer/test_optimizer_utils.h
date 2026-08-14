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

#ifndef TEST_OPTIMIZER_UTILS_H
#define TEST_OPTIMIZER_UTILS_H

#include <cmath>
#include <complex>
#include <vector>

#include "circuit/gate_operation.h"
#include "optimizer/matrix_utils.h"

using namespace qcos;
using C = std::complex<double>;

// Reconstruct U from ZYZ decomposition
inline CMatrix reconstruct_from_zyz(double theta, double phi, double lambda,
                                     double phase) {
  double c = std::cos(theta / 2), s = std::sin(theta / 2);
  CMatrix su2 = {
      {C(c) * std::exp(C(0, -(phi + lambda) / 2)),
       -C(s) * std::exp(C(0, -(phi - lambda) / 2))},
      {C(s) * std::exp(C(0, (phi - lambda) / 2)),
       C(c) * std::exp(C(0, (phi + lambda) / 2))}};
  return matrix_utils::scalar_multiply(std::exp(C(0, phase)), su2);
}

// Check U ≈ V up to global phase
inline bool equal_up_to_global_phase(const CMatrix& a, const CMatrix& b,
                                      double tol = 1e-8) {
  if (a.size() != b.size() || a.empty()) return false;
  double max_abs = 0;
  C phase{1, 0};
  for (size_t i = 0; i < a.size(); ++i)
    for (size_t j = 0; j < a[0].size(); ++j) {
      if (std::abs(a[i][j]) > max_abs && std::abs(b[i][j]) > tol) {
        max_abs = std::abs(a[i][j]);
        phase = a[i][j] / b[i][j];
      }
    }
  if (max_abs < tol) return true;
  CMatrix scaled = matrix_utils::scalar_multiply(phase, b);
  return matrix_utils::is_close(a, scaled, tol);
}

#endif // TEST_OPTIMIZER_UTILS_H
