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

#include "optimizer/one_qubit_euler_decomposer.h"

#include <cassert>
#include <cmath>
#include <stdexcept>

#include "circuit/gate_operation.h"

namespace qcos {

namespace {

using C = std::complex<double>;

double mod_2pi(double angle, double atol = 0.0) {
  double wrapped = std::fmod(angle + M_PI, 2.0 * M_PI);
  if (wrapped < 0) wrapped += 2.0 * M_PI;
  wrapped -= M_PI;
  if (std::abs(wrapped - M_PI) < atol) return -M_PI;
  return wrapped;
}

bool is_zero_angle(double angle, double atol = 1e-12) {
  return std::abs(mod_2pi(angle, atol)) < atol;
}

}  // namespace

SingleQubitDecomp decompose_single_qubit(const CMatrix& u) {
  using C = std::complex<double>;
  assert(u.size() == 2 && u[0].size() == 2);

  C det = u[0][0] * u[1][1] - u[0][1] * u[1][0];
  double det_arg = std::arg(det);
  double phase = det_arg / 2.0;

  double theta = 2.0 * std::atan2(std::abs(u[1][0]), std::abs(u[0][0]));

  double ang1 = std::arg(u[1][1]);
  double ang2 = std::arg(u[1][0]);
  double phi = ang1 + ang2 - det_arg;
  double lambda = ang1 - ang2;

  return {theta, phi, lambda, phase};
}

std::vector<std::shared_ptr<BaseOperation>> single_qubit_unitary_to_basis(
    const CMatrix& u, int qubit,
    const std::optional<std::set<std::string>>& basis_gates) {

  auto decomp = decompose_single_qubit(u);
  double theta = decomp.theta;
  double phi = decomp.phi;
  double lambda = decomp.lambda;
  double phase = decomp.phase;

  std::vector<std::shared_ptr<BaseOperation>> result;
  auto targets = std::vector<int>{qubit};

  auto has_gate = [&](const std::string& g) -> bool {
    if (!basis_gates.has_value()) return true;
    return basis_gates->count(g) > 0;
  };

  constexpr double atol = 1e-12;

  if (is_zero_angle(theta, atol) && is_zero_angle(phi, atol) &&
      is_zero_angle(lambda, atol)) {
    return result;
  }

  if (has_gate("u3")) {
    result.push_back(std::make_shared<U3>(targets,
        std::vector<double>{theta, mod_2pi(phi), mod_2pi(lambda)}));
    return result;
  }
  if (has_gate("u")) {
    result.push_back(std::make_shared<U>(targets,
        std::vector<double>{theta, mod_2pi(phi), mod_2pi(lambda)}));
    return result;
  }

  bool has_rz = has_gate("rz");
  bool has_ry = has_gate("ry");
  bool has_rx = has_gate("rx");

  if (has_rz && has_ry) {
    double global_phase = phase - (phi + lambda) / 2.0;
    (void)global_phase;

    if (std::abs(theta) < atol) {
      double combined = mod_2pi(phi + lambda, atol);
      if (std::abs(combined) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{combined}));
    } else if (std::abs(theta - M_PI) < atol) {
      double lam2 = lambda - phi;
      phi = 0.0;
      double mod_lam = mod_2pi(lam2, atol);
      double mod_phi = mod_2pi(phi, atol);
      if (std::abs(mod_lam) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_lam}));
      result.push_back(std::make_shared<RY>(targets, std::vector<double>{M_PI}));
      if (std::abs(mod_phi) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_phi}));
    } else {
      if (is_zero_angle(lambda + M_PI, atol) || is_zero_angle(phi + M_PI, atol)) {
        lambda += M_PI;
        theta = -theta;
        phi += M_PI;
      }
      double mod_lam = mod_2pi(lambda, atol);
      double mod_phi = mod_2pi(phi, atol);
      if (std::abs(mod_lam) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_lam}));
      if (std::abs(theta) > atol)
        result.push_back(std::make_shared<RY>(targets, std::vector<double>{theta}));
      if (std::abs(mod_phi) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_phi}));
    }
    return result;
  }

  if (has_rx && has_rz) {
    double phi_zxz = phi + M_PI / 2.0;
    double lam_zxz = lambda - M_PI / 2.0;

    if (std::abs(theta) < atol) {
      double combined = mod_2pi(phi_zxz + lam_zxz, atol);
      if (std::abs(combined) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{combined}));
    } else {
      if (is_zero_angle(lam_zxz + M_PI, atol) || is_zero_angle(phi_zxz + M_PI, atol)) {
        lam_zxz += M_PI;
        theta = -theta;
        phi_zxz += M_PI;
      }
      double mod_lam = mod_2pi(lam_zxz, atol);
      double mod_phi = mod_2pi(phi_zxz, atol);
      if (std::abs(mod_lam) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_lam}));
      if (std::abs(theta) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{theta}));
      if (std::abs(mod_phi) > atol)
        result.push_back(std::make_shared<RZ>(targets, std::vector<double>{mod_phi}));
    }
    return result;
  }

  if (has_rx && has_ry) {
    // XYX Euler basis via Hadamard conjugation:
    //   Rx(a).Ry(b).Rx(c) = H.Rz(a).Ry(-b).Rz(c).H
    // So H.U.H has ZYZ decomposition (theta, phi, lam) meaning
    //   U = Rx(phi').Ry(theta).Rx(lam') with phi'=phi+pi, lam'=lam+pi
    C m00 = 0.5 * (u[0][0] + u[0][1] + u[1][0] + u[1][1]);
    C m01 = 0.5 * (u[0][0] - u[0][1] + u[1][0] - u[1][1]);
    C m10 = 0.5 * (u[0][0] + u[0][1] - u[1][0] - u[1][1]);
    C m11 = 0.5 * (u[0][0] - u[0][1] - u[1][0] + u[1][1]);

    CMatrix h_mat = {{m00, m01}, {m10, m11}};
    auto d = decompose_single_qubit(h_mat);
    double xyx_theta = d.theta;
    double xyx_phi = mod_2pi(d.phi + M_PI);
    double xyx_lam = mod_2pi(d.lambda + M_PI);
    (void)d.phase;  // global phase discarded

    // KAK builder: k_gate=RX, a_gate=RY
    // Emission order: RX(lam), RY(theta), RX(phi) so that
    // product = RX(phi) . RY(theta) . RX(lam)
    if (std::abs(xyx_theta) < atol) {
      double combined = mod_2pi(xyx_lam + xyx_phi, atol);
      if (std::abs(combined) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{combined}));
    } else if (std::abs(xyx_theta - M_PI) < atol) {
      double lam2 = xyx_lam - xyx_phi;
      xyx_phi = 0.0;
      double mod_lam = mod_2pi(lam2, atol);
      double mod_phi = mod_2pi(xyx_phi, atol);
      if (std::abs(mod_lam) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{mod_lam}));
      result.push_back(std::make_shared<RY>(targets, std::vector<double>{M_PI}));
      if (std::abs(mod_phi) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{mod_phi}));
    } else {
      if (is_zero_angle(xyx_lam + M_PI, atol) || is_zero_angle(xyx_phi + M_PI, atol)) {
        xyx_lam += M_PI;
        xyx_theta = -xyx_theta;
        xyx_phi += M_PI;
      }
      double mod_lam = mod_2pi(xyx_lam, atol);
      double mod_phi = mod_2pi(xyx_phi, atol);
      if (std::abs(mod_lam) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{mod_lam}));
      if (std::abs(xyx_theta) > atol)
        result.push_back(std::make_shared<RY>(targets, std::vector<double>{xyx_theta}));
      if (std::abs(mod_phi) > atol)
        result.push_back(std::make_shared<RX>(targets, std::vector<double>{mod_phi}));
    }
    return result;
  }

  result.push_back(std::make_shared<U3>(targets,
      std::vector<double>{theta, mod_2pi(phi), mod_2pi(lambda)}));
  return result;
}

}  // namespace qcos
