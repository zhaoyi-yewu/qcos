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

#include "circuit/gate_operation.h"

#include <cmath>
#include <complex>
#include <memory>
#include <stdexcept>

namespace qcos {

GateOperation::GateOperation(std::string name_, std::vector<int> targets_,
                             std::vector<double> arg_value_,
                             OperationType op_type_, bool hermitian_)
    : BaseOperation(std::move(name_), std::move(targets_),
                    std::move(arg_value_), op_type_),
      hermitian(hermitian_) {
  validate_params();
}

void GateOperation::validate_params() const {
  if (operation_type < OperationType::SINGLE_QUBIT_OPERATION) {
    throw std::invalid_argument("Unsupported operation type for gate: " +
                                name);
  }

  size_t expected_targets = static_cast<size_t>(operation_type);
  if (targets.size() != expected_targets) {
    throw std::invalid_argument("Invalid number of targets for gate: " + name);
  }
}

H ::H(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_H, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, true) {}

std::vector<std::unique_ptr<BaseOperation>> H::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  // 创建 RY(pi/2) 门
  std::vector<double> ry_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RY>(targets, ry_args));
  // 创建 RX(pi) 门
  std::vector<double> rx_args = {M_PI};
  gates.push_back(std::make_unique<RX>(targets, rx_args));
  return gates;
}
std::vector<std::unique_ptr<BaseOperation>> H::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<H>(targets, arg_value));
  return gates;
}
std::array<std::complex<double>, 4> H::to_matrix() const {
  const double inv_sqrt2 = 1.0 / std::sqrt(2.0);
  return {std::complex<double>(inv_sqrt2, 0.0),
          std::complex<double>(inv_sqrt2, 0.0),
          std::complex<double>(inv_sqrt2, 0.0),
          std::complex<double>(-inv_sqrt2, 0.0)};
}

std::string H::to_string() const {
  return "H(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

X ::X(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_X, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, true) {}

std::vector<std::unique_ptr<BaseOperation>> X ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  std::vector<double> rx_args = {M_PI};
  gates.push_back(std::make_unique<RX>(targets, rx_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> X ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<X>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> X ::to_matrix() const {
  return {std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
          std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0)};
}

std::string X ::to_string() const {
  return "X(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Y ::Y(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_Y, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, true) {}

std::vector<std::unique_ptr<BaseOperation>> Y ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  std::vector<double> ry_args = {M_PI};
  gates.push_back(std::make_unique<RY>(targets, ry_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> Y ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<Y>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> Y ::to_matrix() const {
  return {std::complex<double>(0.0, 0.0),
          std::complex<double>(0.0, -1.0),  // -i
          std::complex<double>(0.0, 1.0),   // +i
          std::complex<double>(0.0, 0.0)};
}

std::string Y ::to_string() const {
  return "Y(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Z ::Z(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_Z, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, true) {}

std::vector<std::unique_ptr<BaseOperation>> Z ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // 创建 RY(pi) 门
  std::vector<double> ry_args = {M_PI};
  gates.push_back(std::make_unique<RY>(targets, ry_args));

  // 创建 RX(pi) 门
  std::vector<double> rx_args = {M_PI};
  gates.push_back(std::make_unique<RX>(targets, rx_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> Z ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<Z>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> Z ::to_matrix() const {
  return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
          std::complex<double>(0.0, 0.0), std::complex<double>(-1.0, 0.0)};
}

std::string Z ::to_string() const {
  return "Z(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

S ::S(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_S, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> S::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // S门可以用RZ门实现，S = RZ(π/2)
  std::vector<double> rz_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RZ>(targets, rz_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> S ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // RX(3π/2)
  std::vector<double> rx1_args = {3.0 * M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx1_args));

  // RY(π/2)
  std::vector<double> ry_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RY>(targets, ry_args));

  // RX(π/2)
  std::vector<double> rx2_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx2_args));

  return gates;
}

std::array<std::complex<double>, 4> S ::to_matrix() const {
  return {
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 1.0)  // i
  };
}

std::string S ::to_string() const {
  return "S(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

SDG ::SDG(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_SDG, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> SDG ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // RX(3π/2)
  std::vector<double> rx1_args = {3.0 * M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx1_args));

  // RY(3π/2)
  std::vector<double> ry_args = {3.0 * M_PI / 2.0};
  gates.push_back(std::make_unique<RY>(targets, ry_args));

  // RX(π/2)
  std::vector<double> rx2_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx2_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> SDG::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // SDG 门可以用 RZ 门实现，SDG = RZ(-π/2)
  std::vector<double> rz_args = {-M_PI / 2.0};
  gates.push_back(std::make_unique<RZ>(targets, rz_args));

  return gates;
}

std::array<std::complex<double>, 4> SDG ::to_matrix() const {
  return {
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, -1.0)  // -i
  };
}

std::string SDG ::to_string() const {
  return "SDG(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

T ::T(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_T, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> T ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // RZ(π/4)
  std::vector<double> rz_args = {M_PI / 4.0};
  gates.push_back(std::make_unique<RZ>(targets, rz_args));

  return gates;
}

std::array<std::complex<double>, 4> T ::to_matrix() const {
  const double sqrt2_inv = 1.0 / std::sqrt(2.0);
  return {
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(sqrt2_inv, sqrt2_inv)  // (1+i)/√2
  };
}
std::string T ::to_string() const {
  return "T(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

P ::P(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_P, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> P ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  if (!arg_value.empty()) {
    gates.push_back(std::make_unique<RZ>(targets, arg_value));
  }
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> P ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<P>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> P ::to_matrix() const {
  double lambda = arg_value.empty() ? 0.0 : arg_value[0];
  std::complex<double> phase = std::exp(std::complex<double>(0.0, lambda));

  return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
          std::complex<double>(0.0, 0.0), phase};
}

std::string P ::to_string() const {
  return "P(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

R ::R(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_R, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> R ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  if (arg_value.size() >= 2) {
    double theta = arg_value[0];
    double phi = arg_value[1];

    // RZ(phi)
    std::vector<double> rz1_args = {phi};
    gates.push_back(std::make_unique<RZ>(targets, rz1_args));

    // RX(theta)
    std::vector<double> rx_args = {theta};
    gates.push_back(std::make_unique<RX>(targets, rx_args));

    // RZ(-phi)
    std::vector<double> rz2_args = {-phi};
    gates.push_back(std::make_unique<RZ>(targets, rz2_args));
  }
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> R ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<R>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> R ::to_matrix() const {
  if (arg_value.size() < 2) {
    return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
            std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
  }

  double theta = arg_value[0];
  double phi = arg_value[1];

  double c = std::cos(theta / 2.0);
  double s = std::sin(theta / 2.0);

  std::complex<double> exp_neg_i_phi =
      std::exp(std::complex<double>(0.0, -phi));
  std::complex<double> exp_pos_i_phi =
      std::exp(std::complex<double>(0.0, phi));

  std::complex<double> elem01 =
      std::complex<double>(0.0, -1.0) * exp_neg_i_phi * s;
  std::complex<double> elem10 =
      std::complex<double>(0.0, -1.0) * exp_pos_i_phi * s;

  return {std::complex<double>(c, 0.0), elem01, elem10,
          std::complex<double>(c, 0.0)};
}

std::string R ::to_string() const {
  return "R(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

TDG ::TDG(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_TDG, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> TDG ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  std::vector<double> rz_args = {-M_PI / 4.0};
  gates.push_back(std::make_unique<RZ>(targets, rz_args));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> TDG ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<TDG>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> TDG ::to_matrix() const {
  const double sqrt2_inv = 1.0 / std::sqrt(2.0);
  return {
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(sqrt2_inv, -sqrt2_inv)  // (1-i)/√2
  };
}

std::string TDG ::to_string() const {
  return "TDG(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RX ::RX(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_RX, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> RX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RX>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> RX ::to_matrix() const {
  double theta = arg_value.empty() ? 0.0 : arg_value[0];
  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  std::complex<double> elem01 = std::complex<double>(0.0, -sin_theta_2);
  std::complex<double> elem10 = std::complex<double>(0.0, -sin_theta_2);

  return {std::complex<double>(cos_theta_2, 0.0), elem01, elem10,
          std::complex<double>(cos_theta_2, 0.0)};
}

std::string RX ::to_string() const {
  return "RX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RY ::RY(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_RY, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> RY ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RY>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RY ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RY>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> RY ::to_matrix() const {
  double theta = arg_value.empty() ? 0.0 : arg_value[0];
  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  return {std::complex<double>(cos_theta_2, 0.0),
          std::complex<double>(-sin_theta_2, 0.0),
          std::complex<double>(sin_theta_2, 0.0),
          std::complex<double>(cos_theta_2, 0.0)};
}

std::string RY ::to_string() const {
  return "RY(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RZ ::RZ(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_RZ, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> RZ ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RZ>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RZ ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RZ>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> RZ ::to_matrix() const {
  double lambda = arg_value.empty() ? 0.0 : arg_value[0];
  std::complex<double> phase_neg =
      std::exp(std::complex<double>(0.0, -lambda / 2.0));
  std::complex<double> phase_pos =
      std::exp(std::complex<double>(0.0, lambda / 2.0));

  return {phase_neg, std::complex<double>(0.0, 0.0),
          std::complex<double>(0.0, 0.0), phase_pos};
}

std::string RZ ::to_string() const {
  return "RZ(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

SX ::SX(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_SX, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> SX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // SDG
  auto sdg_gates = std::make_unique<SDG>(targets)->default_decompose();
  for (auto& gate : sdg_gates) {
    gates.push_back(std::move(gate));
  }
  sdg_gates.clear();
  ;

  // H
  auto h_gates = std::make_unique<H>(targets)->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // SDG
  auto sdg_gates2 = std::make_unique<SDG>(targets)->default_decompose();
  for (auto& gate : sdg_gates2) {
    gates.push_back(std::move(gate));
  }
  sdg_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> SX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<SX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> SX ::to_matrix() const {
  std::complex<double> elem(0.5, 0.5);        // 0.5 + 0.5i
  std::complex<double> elem_conj(0.5, -0.5);  // 0.5 - 0.5i

  return {elem, elem_conj, elem_conj, elem};
}

std::string SX ::to_string() const {
  return "SX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

SXDG ::SXDG(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_SXDG, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> SXDG ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  // S
  auto s_gates = std::make_unique<S>(targets)->default_decompose();
  for (auto& gate : s_gates) {
    gates.push_back(std::move(gate));
  }
  s_gates.clear();
  ;

  // H
  auto h_gates = std::make_unique<H>(targets)->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // S
  auto s_gates2 = std::make_unique<S>(targets)->default_decompose();
  for (auto& gate : s_gates2) {
    gates.push_back(std::move(gate));
  }
  s_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> SXDG ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<SXDG>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> SXDG ::to_matrix() const {
  std::complex<double> elem(0.5, -0.5);      // 0.5 - 0.5i
  std::complex<double> elem_conj(0.5, 0.5);  // 0.5 + 0.5i

  return {elem, elem_conj, elem_conj, elem};
}

std::string SXDG ::to_string() const {
  return "SXDG(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CZ ::CZ(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CZ, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> CZ ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<CZ>(targets, arg_value));
    return gates;
  }

  // H(目标比特)
  int control = targets[0];
  int target = targets[1];

  auto h_gates =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CX(控制, 目标)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // H(目标比特)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CZ ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CZ>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CZ ::to_matrix() const {
  // Z 门矩阵
  std::array<std::complex<double>, 4> z_matrix = {
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(-1.0, 0.0)};

  // 构建受控Z门矩阵
  std::array<std::complex<double>, 16> cz_matrix = {
      // 前两行：控制比特为0的情况
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      // 后两行：控制比特为1的情况
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(-1.0, 0.0)};

  return cz_matrix;
}

std::string CZ ::to_string() const {
  return "CZ(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CX ::CX(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CX, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> CX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<CX>(targets, arg_value));
    return gates;
  }

  // H(目标比特)
  int control = targets[0];
  int target = targets[1];

  auto h_gates =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CZ(控制, 目标)
  gates.push_back(std::make_unique<CZ>(std::vector<int>{control, target}));

  // H(目标比特)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CX ::to_matrix() const {
  // CNOT 门的标准矩阵表示
  std::array<std::complex<double>, 16> cx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0)};

  return cx_matrix;
}

std::string CX ::to_string() const {
  return "CX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CY ::CY(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CY, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> CY ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<CY>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];

  // SDG(目标)
  auto sdg_gates =
      std::make_unique<SDG>(std::vector<int>{target})->default_decompose();
  for (auto& gate : sdg_gates) {
    gates.push_back(std::move(gate));
  }
  sdg_gates.clear();
  ;

  // CX(控制, 目标)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // S(目标)
  auto s_gates =
      std::make_unique<S>(std::vector<int>{target})->default_decompose();
  for (auto& gate : s_gates) {
    gates.push_back(std::move(gate));
  }
  s_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CY ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CY>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CY ::to_matrix() const {
  // 受控Y门矩阵
  std::array<std::complex<double>, 16> cy_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, -1.0),  // -i

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 1.0), std::complex<double>(0.0, 0.0)  // +i
  };

  return cy_matrix;
}

std::string CY ::to_string() const {
  return "CY(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

SWAP ::SWAP(std::vector<int> targets_, std::vector<double> arg_value_,
            OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_SWAP, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> SWAP ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<SWAP>(targets, arg_value));
    return gates;
  }

  int q0 = targets[0];
  int q1 = targets[1];

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  // CX(q1, q0)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q1, q0}));

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> SWAP ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<SWAP>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> SWAP ::to_matrix() const {
  // SWAP 门矩阵
  std::array<std::complex<double>, 16> swap_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};

  return swap_matrix;
}

std::string SWAP ::to_string() const {
  return "SWAP(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

ISWAP ::ISWAP(std::vector<int> targets_, std::vector<double> arg_value_,
              OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_ISWAP, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> ISWAP ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<ISWAP>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> ISWAP ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<ISWAP>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> ISWAP ::to_matrix() const {
  // iSWAP 门矩阵
  std::array<std::complex<double>, 16> iswap_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 1.0), std::complex<double>(0.0, 0.0),  // +i

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 1.0),  // +i
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};

  return iswap_matrix;
}

std::string ISWAP ::to_string() const {
  return "ISWAP(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CH ::CH(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CH, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> CH ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<CH>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];

  // H(target)
  auto h_gates =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // SDG(target)
  auto sdg_gates =
      std::make_unique<SDG>(std::vector<int>{target})->default_decompose();
  for (auto& gate : sdg_gates) {
    gates.push_back(std::move(gate));
  }
  sdg_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // H(target)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  // T(target)
  auto t_gates =
      std::make_unique<T>(std::vector<int>{target})->default_decompose();
  for (auto& gate : t_gates) {
    gates.push_back(std::move(gate));
  }
  t_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // T(target)
  auto t_gates2 =
      std::make_unique<T>(std::vector<int>{target})->default_decompose();
  for (auto& gate : t_gates2) {
    gates.push_back(std::move(gate));
  }
  t_gates2.clear();
  ;

  // H(target)
  auto h_gates3 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates3) {
    gates.push_back(std::move(gate));
  }
  h_gates3.clear();
  ;

  // S(target)
  auto s_gates =
      std::make_unique<S>(std::vector<int>{target})->default_decompose();
  for (auto& gate : s_gates) {
    gates.push_back(std::move(gate));
  }
  s_gates.clear();
  ;

  // X(target)
  auto x_gates =
      std::make_unique<X>(std::vector<int>{target})->default_decompose();
  for (auto& gate : x_gates) {
    gates.push_back(std::move(gate));
  }
  x_gates.clear();
  ;

  // S(control)
  auto s_control_gates =
      std::make_unique<S>(std::vector<int>{control})->default_decompose();
  for (auto& gate : s_control_gates) {
    gates.push_back(std::move(gate));
  }
  s_control_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CH ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CH>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CH ::to_matrix() const {
  // 受控Hadamard门矩阵
  const double inv_sqrt2 = 1.0 / std::sqrt(2.0);

  std::array<std::complex<double>, 16> ch_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(inv_sqrt2, 0.0),
      std::complex<double>(inv_sqrt2, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(inv_sqrt2, 0.0),
      std::complex<double>(-inv_sqrt2, 0.0)};

  return ch_matrix;
}

std::string CH ::to_string() const {
  return "CH(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CS ::CS(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CS, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CS ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CS>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CS ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CS>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CS ::to_matrix() const {
  // 受控S门矩阵
  std::array<std::complex<double>, 16> cs_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 1.0)  // +i
  };

  return cs_matrix;
}

std::string CS ::to_string() const {
  return "CS(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CSDG ::CSDG(std::vector<int> targets_, std::vector<double> arg_value_,
            OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CSDG, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CSDG ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CSDG>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CSDG ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CSDG>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CSDG ::to_matrix() const {
  // 受控SDG门矩阵
  std::array<std::complex<double>, 16> csdg_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, -1.0)  // -i
  };

  return csdg_matrix;
}

std::string CSDG ::to_string() const {
  return "CSDG(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CRX ::CRX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CRX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CRX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<CRX>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double theta = arg_value[0];

  // H(target)
  auto h_gates =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RZ(target, -theta/2)
  std::vector<double> rz1_args = {-theta / 2.0};
  gates.push_back(std::make_unique<RZ>(std::vector<int>{target}, rz1_args));

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RZ(target, theta/2)
  std::vector<double> rz2_args = {theta / 2.0};
  gates.push_back(std::make_unique<RZ>(std::vector<int>{target}, rz2_args));

  // H(target)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CRX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CRX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CRX ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double half_theta = theta / 2.0;
  double cos_half = std::cos(half_theta);
  double sin_half = std::sin(half_theta);

  std::array<std::complex<double>, 16> crx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_half, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, -sin_half),  // -i·sin

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, -sin_half),  // -i·sin
      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_half, 0.0)};

  return crx_matrix;
}

std::string CRX ::to_string() const {
  return "CRX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CRY ::CRY(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CRY, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CRY ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<CRY>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double theta = arg_value[0];

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RY(target, -theta/2)
  std::vector<double> ry1_args = {-theta / 2.0};
  gates.push_back(std::make_unique<RY>(std::vector<int>{target}, ry1_args));

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RY(target, theta/2)
  std::vector<double> ry2_args = {theta / 2.0};
  gates.push_back(std::make_unique<RY>(std::vector<int>{target}, ry2_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CRY ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CRY>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CRY ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double half_theta = theta / 2.0;
  double cos_half = std::cos(half_theta);
  double sin_half = std::sin(half_theta);

  std::array<std::complex<double>, 16> cry_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(cos_half, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(-sin_half, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(sin_half, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(cos_half, 0.0)};

  return cry_matrix;
}

std::string CRY ::to_string() const {
  return "CRY(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CRZ ::CRZ(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CRZ, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CRZ ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<CRZ>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double theta = arg_value[0];

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RZ(target, -theta/2)
  std::vector<double> rz1_args = {-theta / 2.0};
  gates.push_back(std::make_unique<RZ>(std::vector<int>{target}, rz1_args));

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // RZ(target, theta/2)
  std::vector<double> rz2_args = {theta / 2.0};
  gates.push_back(std::make_unique<RZ>(std::vector<int>{target}, rz2_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CRZ ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CRZ>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CRZ ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  std::complex<double> phase_neg =
      std::exp(std::complex<double>(0.0, -theta / 2.0));
  std::complex<double> phase_pos =
      std::exp(std::complex<double>(0.0, theta / 2.0));

  std::array<std::complex<double>, 16> crz_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), phase_neg,
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), phase_pos};

  return crz_matrix;
}

std::string CRZ ::to_string() const {
  return "CRZ(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CU1 ::CU1(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CU1, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CU1 ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<CU1>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double lambda = arg_value[0];

  // U1(control, lambda/2)
  std::vector<double> u1_control_args = {lambda / 2.0};
  auto u1_control_gates =
      std::make_unique<U1>(std::vector<int>{control}, u1_control_args)
          ->default_decompose();
  for (auto& gate : u1_control_gates) {
    gates.push_back(std::move(gate));
  }
  u1_control_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U1(target, -lambda/2)
  std::vector<double> u1_target_neg_args = {-lambda / 2.0};
  auto u1_target_neg_gates =
      std::make_unique<U1>(std::vector<int>{target}, u1_target_neg_args)
          ->default_decompose();
  for (auto& gate : u1_target_neg_gates) {
    gates.push_back(std::move(gate));
  }
  u1_target_neg_gates.clear();

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U1(target, lambda/2)
  std::vector<double> u1_target_pos_args = {lambda / 2.0};
  auto u1_target_pos_gates =
      std::make_unique<U1>(std::vector<int>{target}, u1_target_pos_args)
          ->default_decompose();
  for (auto& gate : u1_target_pos_gates) {
    gates.push_back(std::move(gate));
  }
  u1_target_pos_gates.clear();

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CU1 ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CU1>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CU1 ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double lambda = arg_value[0];
  std::complex<double> phase = std::exp(std::complex<double>(0.0, lambda));

  std::array<std::complex<double>, 16> cu1_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), phase};

  return cu1_matrix;
}

std::string CU1 ::to_string() const {
  return "CU1(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CP ::CP(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CP, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CP ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<CP>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double lambda = arg_value[0];

  // P(control, lambda/2)
  std::vector<double> p_control_args = {lambda / 2.0};
  auto p_control_gates =
      std::make_unique<P>(std::vector<int>{control}, p_control_args)
          ->default_decompose();
  for (auto& gate : p_control_gates) {
    gates.push_back(std::move(gate));
  }
  p_control_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // P(target, -lambda/2)
  std::vector<double> p_target_neg_args = {-lambda / 2.0};
  auto p_target_neg_gates =
      std::make_unique<P>(std::vector<int>{target}, p_target_neg_args)
          ->default_decompose();
  for (auto& gate : p_target_neg_gates) {
    gates.push_back(std::move(gate));
  }
  p_target_neg_gates.clear();

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // P(target, lambda/2)
  std::vector<double> p_target_pos_args = {lambda / 2.0};
  auto p_target_pos_gates =
      std::make_unique<P>(std::vector<int>{target}, p_target_pos_args)
          ->default_decompose();
  for (auto& gate : p_target_pos_gates) {
    gates.push_back(std::move(gate));
  }
  p_target_pos_gates.clear();

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CP ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CP>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CP ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double lambda = arg_value[0];
  std::complex<double> phase = std::exp(std::complex<double>(0.0, lambda));

  std::array<std::complex<double>, 16> cp_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), phase};

  return cp_matrix;
}

std::string CP ::to_string() const {
  return "CP(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CU3 ::CU3(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CU3, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CU3 ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.size() < 3) {
    gates.push_back(std::make_unique<CU3>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  // U1(control, (lam + phi)/2)
  std::vector<double> u1_control_args = {(lam + phi) / 2.0};
  auto u1_control_gates =
      std::make_unique<U1>(std::vector<int>{control}, u1_control_args)
          ->default_decompose();
  for (auto& gate : u1_control_gates) {
    gates.push_back(std::move(gate));
  }
  u1_control_gates.clear();
  ;

  // U1(target, (lam - phi)/2)
  std::vector<double> u1_target_args = {(lam - phi) / 2.0};
  auto u1_target_gates =
      std::make_unique<U1>(std::vector<int>{target}, u1_target_args)
          ->default_decompose();
  for (auto& gate : u1_target_gates) {
    gates.push_back(std::move(gate));
  }
  u1_target_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U3(target, [-theta/2, 0, -(phi+lam)/2])
  std::vector<double> u3_neg_args = {-theta / 2.0, 0.0, -(phi + lam) / 2.0};
  auto u3_neg_gates =
      std::make_unique<U3>(std::vector<int>{target}, u3_neg_args)
          ->default_decompose();
  for (auto& gate : u3_neg_gates) {
    gates.push_back(std::move(gate));
  }
  u3_neg_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U3(target, [theta/2, phi, 0])
  std::vector<double> u3_pos_args = {theta / 2.0, phi, 0.0};
  auto u3_pos_gates =
      std::make_unique<U3>(std::vector<int>{target}, u3_pos_args)
          ->default_decompose();
  for (auto& gate : u3_pos_gates) {
    gates.push_back(std::move(gate));
  }
  u3_pos_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CU3 ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CU3>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CU3 ::to_matrix() const {
  if (arg_value.size() < 3) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  std::complex<double> exp_i_lam = std::exp(std::complex<double>(0.0, lam));
  std::complex<double> exp_i_phi = std::exp(std::complex<double>(0.0, phi));
  std::complex<double> exp_i_phi_lam =
      std::exp(std::complex<double>(0.0, phi + lam));

  std::complex<double> elem01_neg = -exp_i_lam * sin_theta_2;
  std::complex<double> elem10_pos = exp_i_phi * sin_theta_2;
  std::complex<double> elem11 = exp_i_phi_lam * cos_theta_2;

  std::array<std::complex<double>, 16> cu3_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(cos_theta_2, 0.0),
      std::complex<double>(0.0, 0.0), elem01_neg,

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), elem10_pos,
      std::complex<double>(0.0, 0.0), elem11};

  return cu3_matrix;
}

std::string CU3 ::to_string() const {
  return "CU3(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CSX ::CSX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CSX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CSX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<CSX>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];

  // H(target)
  auto h_gates =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CU1(control, target, π/2)
  std::vector<double> cu1_args = {M_PI / 2.0};
  auto cu1_gates =
      std::make_unique<CU1>(std::vector<int>{control, target}, cu1_args)
          ->default_decompose();
  for (auto& gate : cu1_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_gates.clear();
  ;

  // H(target)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{target})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CSX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CSX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CSX ::to_matrix() const {
  // 受控SX门矩阵
  std::complex<double> elem(0.5, 0.5);        // 0.5 + 0.5i
  std::complex<double> elem_conj(0.5, -0.5);  // 0.5 - 0.5i

  std::array<std::complex<double>, 16> csx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      elem,
      elem_conj,

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      elem_conj,
      elem};

  return csx_matrix;
}

std::string CSX ::to_string() const {
  return "CSX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CU ::CU(std::vector<int> targets_, std::vector<double> arg_value_,
        OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_CU, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CU ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.size() < 4) {
    std::vector<std::unique_ptr<BaseOperation>> gates;
    gates.push_back(std::make_unique<CU>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target = targets[1];
  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];
  double gamma = arg_value[3];

  // P(control, gamma)
  std::vector<double> p_gamma_args = {gamma};
  auto p_gamma_gates =
      std::make_unique<P>(std::vector<int>{control}, p_gamma_args)
          ->default_decompose();
  for (auto& gate : p_gamma_gates) {
    gates.push_back(std::move(gate));
  }
  p_gamma_gates.clear();
  ;

  // P(control, (lam + phi)/2)
  std::vector<double> p_control_args = {(lam + phi) / 2.0};
  auto p_control_gates =
      std::make_unique<P>(std::vector<int>{control}, p_control_args)
          ->default_decompose();
  for (auto& gate : p_control_gates) {
    gates.push_back(std::move(gate));
  }
  p_control_gates.clear();
  ;

  // P(target, (lam - phi)/2)
  std::vector<double> p_target_args = {(lam - phi) / 2.0};
  auto p_target_gates =
      std::make_unique<P>(std::vector<int>{target}, p_target_args)
          ->default_decompose();
  for (auto& gate : p_target_gates) {
    gates.push_back(std::move(gate));
  }
  p_target_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U3(target, [-theta/2, 0, -(phi+lam)/2])
  std::vector<double> u3_neg_args = {-theta / 2.0, 0.0, -(phi + lam) / 2.0};
  auto u3_neg_gates =
      std::make_unique<U3>(std::vector<int>{target}, u3_neg_args)
          ->default_decompose();
  for (auto& gate : u3_neg_gates) {
    gates.push_back(std::move(gate));
  }
  u3_neg_gates.clear();
  ;

  // CX(control, target)
  gates.push_back(std::make_unique<CX>(std::vector<int>{control, target}));

  // U3(target, [theta/2, phi, 0])
  std::vector<double> u3_pos_args = {theta / 2.0, phi, 0.0};
  auto u3_pos_gates =
      std::make_unique<U3>(std::vector<int>{target}, u3_pos_args)
          ->default_decompose();
  for (auto& gate : u3_pos_gates) {
    gates.push_back(std::move(gate));
  }
  u3_pos_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CU ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<CU>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> CU ::to_matrix() const {
  if (arg_value.size() < 4) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];
  double gamma = arg_value[3];

  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  std::complex<double> exp_i_gamma =
      std::exp(std::complex<double>(0.0, gamma));
  std::complex<double> exp_i_gamma_lam =
      std::exp(std::complex<double>(0.0, gamma + lam));
  std::complex<double> exp_i_gamma_phi =
      std::exp(std::complex<double>(0.0, gamma + phi));
  std::complex<double> exp_i_gamma_phi_lam =
      std::exp(std::complex<double>(0.0, gamma + phi + lam));

  std::complex<double> elem_a = exp_i_gamma * cos_theta_2;
  std::complex<double> elem_b = -exp_i_gamma_lam * sin_theta_2;
  std::complex<double> elem_c = exp_i_gamma_phi * sin_theta_2;
  std::complex<double> elem_d = exp_i_gamma_phi_lam * cos_theta_2;

  std::array<std::complex<double>, 16> cu_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), elem_a,
      std::complex<double>(0.0, 0.0), elem_b,

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), elem_c,
      std::complex<double>(0.0, 0.0), elem_d};

  return cu_matrix;
}

std::string CU ::to_string() const {
  return "CU(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

ECR ::ECR(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_ECR, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> ECR ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<ECR>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> ECR ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<ECR>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> ECR ::to_matrix() const {
  // ECR 门矩阵 (Echoed Cross Resonance)
  const double inv_sqrt2 = 1.0 / std::sqrt(2.0);

  std::array<std::complex<double>, 16> ecr_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(0.0, 0.0),
      inv_sqrt2 * std::complex<double>(0.0, 1.0),  // 0, +i/√2
      inv_sqrt2,
      std::complex<double>(0.0, 0.0),

      inv_sqrt2 * std::complex<double>(0.0, 1.0),
      std::complex<double>(0.0, 0.0),  // +i/√2, 0
      std::complex<double>(0.0, 0.0),
      inv_sqrt2,

      inv_sqrt2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      inv_sqrt2 * std::complex<double>(0.0, -1.0),  // 0, -i/√2

      std::complex<double>(0.0, 0.0),
      inv_sqrt2,
      inv_sqrt2 * std::complex<double>(0.0, -1.0),
      std::complex<double>(0.0, 0.0)  // -i/√2, 0
  };

  return ecr_matrix;
}

std::string ECR ::to_string() const {
  return "ECR(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

DCX ::DCX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_DCX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> DCX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2) {
    gates.push_back(std::make_unique<DCX>(targets, arg_value));
    return gates;
  }

  int q0 = targets[0];
  int q1 = targets[1];

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  // CX(q1, q0)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q1, q0}));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> DCX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<DCX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> DCX ::to_matrix() const {
  // DCX 门矩阵 (Double-CNOT)
  std::array<std::complex<double>, 16> dcx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0)};

  return dcx_matrix;
}

std::string DCX ::to_string() const {
  return "DCX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RXX ::RXX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_RXX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RXX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<RXX>(targets, arg_value));
    return gates;
  }

  int q0 = targets[0];
  int q1 = targets[1];
  double theta = arg_value[0];

  // U3(q0, [π/2, theta, 0])
  std::vector<double> u3_args = {M_PI / 2.0, theta, 0.0};
  auto u3_gates =
      std::make_unique<U3>(std::vector<int>{q0}, u3_args)->default_decompose();
  for (auto& gate : u3_gates) {
    gates.push_back(std::move(gate));
  }
  u3_gates.clear();
  ;

  // H(q1)
  auto h_gates =
      std::make_unique<H>(std::vector<int>{q1})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  // U1(q1, -theta)
  std::vector<double> u1_neg_args = {-theta};
  auto u1_neg_gates = std::make_unique<U1>(std::vector<int>{q1}, u1_neg_args)
                          ->default_decompose();
  for (auto& gate : u1_neg_gates) {
    gates.push_back(std::move(gate));
  }
  u1_neg_gates.clear();
  ;

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  // H(q1)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{q1})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  // U2(q0, [-π, π - theta])
  std::vector<double> u2_args = {-M_PI, M_PI - theta};
  auto u2_gates =
      std::make_unique<U2>(std::vector<int>{q0}, u2_args)->default_decompose();
  for (auto& gate : u2_gates) {
    gates.push_back(std::move(gate));
  }
  u2_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RXX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RXX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> RXX ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double theta2 = theta / 2.0;
  double cos_theta2 = std::cos(theta2);
  double sin_theta2 = std::sin(theta2);

  std::complex<double> i_sin_theta2(0.0, sin_theta2);  // i·sin(θ/2)

  std::array<std::complex<double>, 16> rxx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      -i_sin_theta2,

      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0),
      -i_sin_theta2,
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      -i_sin_theta2,
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),

      -i_sin_theta2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0)};

  return rxx_matrix;
}

std::string RXX ::to_string() const {
  return "RXX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RYY ::RYY(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_RYY, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RYY ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RYY>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RYY ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RYY>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> RYY ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double theta2 = theta / 2.0;
  double cos_theta2 = std::cos(theta2);
  double sin_theta2 = std::sin(theta2);

  std::complex<double> i_sin_theta2(0.0, sin_theta2);  // i·sin(θ/2)

  std::array<std::complex<double>, 16> ryy_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      i_sin_theta2,

      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0),
      -i_sin_theta2,
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      -i_sin_theta2,
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),

      i_sin_theta2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0)};

  return ryy_matrix;
}

std::string RYY ::to_string() const {
  return "RYY(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RZZ ::RZZ(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_RZZ, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RZZ ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 2 || arg_value.empty()) {
    gates.push_back(std::make_unique<RZZ>(targets, arg_value));
    return gates;
  }

  int q0 = targets[0];
  int q1 = targets[1];
  double theta = arg_value[0];

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  // U1(q1, theta)
  std::vector<double> u1_args = {theta};
  auto u1_gates =
      std::make_unique<U1>(std::vector<int>{q1}, u1_args)->default_decompose();
  for (auto& gate : u1_gates) {
    gates.push_back(std::move(gate));
  }
  u1_gates.clear();
  ;

  // CX(q0, q1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{q0, q1}));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RZZ ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RZZ>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> RZZ ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double theta2 = theta / 2.0;

  std::complex<double> exp_neg_i_theta2 =
      std::exp(std::complex<double>(0.0, -theta2));
  std::complex<double> exp_pos_i_theta2 =
      std::exp(std::complex<double>(0.0, theta2));

  std::array<std::complex<double>, 16> rzz_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      exp_neg_i_theta2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      exp_pos_i_theta2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      exp_pos_i_theta2,
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0),
      exp_neg_i_theta2};

  return rzz_matrix;
}

std::string RZZ ::to_string() const {
  return "RZZ(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RZX ::RZX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::TWO_QUBIT_GATE_RZX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RZX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RZX>(targets, arg_value));
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RZX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<RZX>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 16> RZX ::to_matrix() const {
  if (arg_value.empty()) {
    std::array<std::complex<double>, 16> identity = {
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
        std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
    return identity;
  }

  double theta = arg_value[0];
  double theta2 = theta / 2.0;
  double cos_theta2 = std::cos(theta2);
  double sin_theta2 = std::sin(theta2);

  std::complex<double> i_sin_theta2(0.0, -sin_theta2);     // -i·sin(θ/2)
  std::complex<double> i_sin_theta2_pos(0.0, sin_theta2);  // +i·sin(θ/2)

  std::array<std::complex<double>, 16> rzx_matrix = {
      // |00⟩, |01⟩, |10⟩, |11⟩
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),
      i_sin_theta2,
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),
      i_sin_theta2,

      i_sin_theta2,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0),
      std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0),
      i_sin_theta2_pos,
      std::complex<double>(0.0, 0.0),
      std::complex<double>(cos_theta2, 0.0)};

  return rzx_matrix;
}

std::string RZX ::to_string() const {
  return "RZX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

CCX ::CCX(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::THREE_QUBIT_GATE_CCX, std::move(targets_),
                    std::move(arg_value_), gate_type) {}

std::vector<std::unique_ptr<BaseOperation>> CCX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<CCX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int t = targets[2];

  // H(t)
  auto h_gates = std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // TDG(t)
  auto tdg_gates =
      std::make_unique<TDG>(std::vector<int>{t})->default_decompose();
  for (auto& gate : tdg_gates) {
    gates.push_back(std::move(gate));
  }
  tdg_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // T(t)
  auto t_gates = std::make_unique<T>(std::vector<int>{t})->default_decompose();
  for (auto& gate : t_gates) {
    gates.push_back(std::move(gate));
  }
  t_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // TDG(t)
  auto tdg_gates2 =
      std::make_unique<TDG>(std::vector<int>{t})->default_decompose();
  for (auto& gate : tdg_gates2) {
    gates.push_back(std::move(gate));
  }
  tdg_gates2.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // T(t)
  auto t_gates2 =
      std::make_unique<T>(std::vector<int>{t})->default_decompose();
  for (auto& gate : t_gates2) {
    gates.push_back(std::move(gate));
  }
  t_gates2.clear();
  ;

  // T(c2)
  auto t_c2_gates =
      std::make_unique<T>(std::vector<int>{c2})->default_decompose();
  for (auto& gate : t_c2_gates) {
    gates.push_back(std::move(gate));
  }
  t_c2_gates.clear();
  ;

  // H(t)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  // T(c1)
  auto t_c1_gates =
      std::make_unique<T>(std::vector<int>{c1})->default_decompose();
  for (auto& gate : t_c1_gates) {
    gates.push_back(std::move(gate));
  }
  t_c1_gates.clear();
  ;

  // TDG(c2)
  auto tdg_c2_gates =
      std::make_unique<TDG>(std::vector<int>{c2})->default_decompose();
  for (auto& gate : tdg_c2_gates) {
    gates.push_back(std::move(gate));
  }
  tdg_c2_gates.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CCX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<CCX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int t = targets[2];

  // 直接返回基本门，不递归分解
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<TDG>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<T>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<TDG>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<T>(std::vector<int>{t}));
  gates.push_back(std::make_unique<T>(std::vector<int>{c2}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));
  gates.push_back(std::make_unique<T>(std::vector<int>{c1}));
  gates.push_back(std::make_unique<TDG>(std::vector<int>{c2}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  return gates;
}

std::array<std::complex<double>, 64> CCX ::to_matrix() const {
  // CCX (Toffoli) 门矩阵
  std::array<std::complex<double>, 64> ccx_matrix = {
      // 初始化 8×8 单位矩阵
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0)};

  return ccx_matrix;
}

std::string CCX ::to_string() const {
  return "CCX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}
CSWAP ::CSWAP(std::vector<int> targets_, std::vector<double> arg_value_,
              OperationType gate_type)
    : GateOperation(Constant::THREE_QUBIT_GATE_CSWAP, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> CSWAP ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<CSWAP>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target1 = targets[1];
  int target2 = targets[2];

  // CX(target2, target1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{target2, target1}));

  // CCX(control, target1, target2)
  auto ccx_gates =
      std::make_unique<CCX>(std::vector<int>{control, target1, target2})
          ->default_decompose();
  for (auto& gate : ccx_gates) {
    gates.push_back(std::move(gate));
  }
  ccx_gates.clear();
  ;

  // CX(target2, target1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{target2, target1}));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> CSWAP ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<CSWAP>(targets, arg_value));
    return gates;
  }

  int control = targets[0];
  int target1 = targets[1];
  int target2 = targets[2];

  // CX(target2, target1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{target2, target1}));

  // CCX(control, target1, target2) -> 使用 decompose_to_1q2q
  auto ccx_gates =
      std::make_unique<CCX>(std::vector<int>{control, target1, target2})
          ->decompose_to_1q2q();
  for (auto& gate : ccx_gates) {
    gates.push_back(std::move(gate));
  }
  ccx_gates.clear();
  ;

  // CX(target2, target1)
  gates.push_back(std::make_unique<CX>(std::vector<int>{target2, target1}));

  return gates;
}

std::array<std::complex<double>, 64> CSWAP ::to_matrix() const {
  // CSWAP (Fredkin) 门矩阵
  std::array<std::complex<double>, 64> cswap_matrix = {
      // 初始化 8×8 单位矩阵
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};

  return cswap_matrix;
}

std::string CSWAP ::to_string() const {
  return "CSWAP(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RCCX ::RCCX(std::vector<int> targets_, std::vector<double> arg_value_,
            OperationType gate_type)
    : GateOperation(Constant::THREE_QUBIT_GATE_RCCX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RCCX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<RCCX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int t = targets[2];

  // U2(t, [0, π])
  std::vector<double> u2_1_args = {0.0, M_PI};
  auto u2_1_gates = std::make_unique<U2>(std::vector<int>{t}, u2_1_args)
                        ->default_decompose();
  for (auto& gate : u2_1_gates) {
    gates.push_back(std::move(gate));
  }
  u2_1_gates.clear();
  ;

  // U1(t, π/4)
  std::vector<double> u1_1_args = {M_PI / 4.0};
  auto u1_1_gates = std::make_unique<U1>(std::vector<int>{t}, u1_1_args)
                        ->default_decompose();
  for (auto& gate : u1_1_gates) {
    gates.push_back(std::move(gate));
  }
  u1_1_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // U1(t, -π/4)
  std::vector<double> u1_2_args = {-M_PI / 4.0};
  auto u1_2_gates = std::make_unique<U1>(std::vector<int>{t}, u1_2_args)
                        ->default_decompose();
  for (auto& gate : u1_2_gates) {
    gates.push_back(std::move(gate));
  }
  u1_2_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // U1(t, π/4)
  std::vector<double> u1_3_args = {M_PI / 4.0};
  auto u1_3_gates = std::make_unique<U1>(std::vector<int>{t}, u1_3_args)
                        ->default_decompose();
  for (auto& gate : u1_3_gates) {
    gates.push_back(std::move(gate));
  }
  u1_3_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // U1(t, -π/4)
  std::vector<double> u1_4_args = {-M_PI / 4.0};
  auto u1_4_gates = std::make_unique<U1>(std::vector<int>{t}, u1_4_args)
                        ->default_decompose();
  for (auto& gate : u1_4_gates) {
    gates.push_back(std::move(gate));
  }
  u1_4_gates.clear();
  ;

  // U2(t, [0, π])
  std::vector<double> u2_2_args = {0.0, M_PI};
  auto u2_2_gates = std::make_unique<U2>(std::vector<int>{t}, u2_2_args)
                        ->default_decompose();
  for (auto& gate : u2_2_gates) {
    gates.push_back(std::move(gate));
  }
  u2_2_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RCCX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 3) {
    gates.push_back(std::make_unique<RCCX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int t = targets[2];

  // 直接返回基本门
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));

  return gates;
}

std::array<std::complex<double>, 64> RCCX ::to_matrix() const {
  // RCCX 门矩阵
  std::array<std::complex<double>, 64> rccx_matrix = {
      // |000⟩, |001⟩, |010⟩, |011⟩, |100⟩, |101⟩, |110⟩, |111⟩
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, -1.0),  // -i

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(-1.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),

      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 1.0),  // +i
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0),
      std::complex<double>(0.0, 0.0), std::complex<double>(0.0, 0.0)};

  return rccx_matrix;
}

std::string RCCX ::to_string() const {
  return "RCCX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

RC3X ::RC3X(std::vector<int> targets_, std::vector<double> arg_value_,
            OperationType gate_type)
    : GateOperation(Constant::FOUR_QUBIT_GATE_RC3X, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> RC3X ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<RC3X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];

  // U2(t, [0, π])
  std::vector<double> u2_1_args = {0.0, M_PI};
  auto u2_1_gates = std::make_unique<U2>(std::vector<int>{t}, u2_1_args)
                        ->default_decompose();
  for (auto& gate : u2_1_gates) {
    gates.push_back(std::move(gate));
  }
  u2_1_gates.clear();
  ;

  // U1(t, π/4)
  std::vector<double> u1_1_args = {M_PI / 4.0};
  auto u1_1_gates = std::make_unique<U1>(std::vector<int>{t}, u1_1_args)
                        ->default_decompose();
  for (auto& gate : u1_1_gates) {
    gates.push_back(std::move(gate));
  }
  u1_1_gates.clear();
  ;

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // U1(t, -π/4)
  std::vector<double> u1_2_args = {-M_PI / 4.0};
  auto u1_2_gates = std::make_unique<U1>(std::vector<int>{t}, u1_2_args)
                        ->default_decompose();
  for (auto& gate : u1_2_gates) {
    gates.push_back(std::move(gate));
  }
  u1_2_gates.clear();
  ;

  // U2(t, [0, π])
  std::vector<double> u2_2_args = {0.0, M_PI};
  auto u2_2_gates = std::make_unique<U2>(std::vector<int>{t}, u2_2_args)
                        ->default_decompose();
  for (auto& gate : u2_2_gates) {
    gates.push_back(std::move(gate));
  }
  u2_2_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // U1(t, π/4)
  std::vector<double> u1_3_args = {M_PI / 4.0};
  auto u1_3_gates = std::make_unique<U1>(std::vector<int>{t}, u1_3_args)
                        ->default_decompose();
  for (auto& gate : u1_3_gates) {
    gates.push_back(std::move(gate));
  }
  u1_3_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // U1(t, -π/4)
  std::vector<double> u1_4_args = {-M_PI / 4.0};
  auto u1_4_gates = std::make_unique<U1>(std::vector<int>{t}, u1_4_args)
                        ->default_decompose();
  for (auto& gate : u1_4_gates) {
    gates.push_back(std::move(gate));
  }
  u1_4_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // U1(t, π/4)
  std::vector<double> u1_5_args = {M_PI / 4.0};
  auto u1_5_gates = std::make_unique<U1>(std::vector<int>{t}, u1_5_args)
                        ->default_decompose();
  for (auto& gate : u1_5_gates) {
    gates.push_back(std::move(gate));
  }
  u1_5_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // U1(t, -π/4)
  std::vector<double> u1_6_args = {-M_PI / 4.0};
  auto u1_6_gates = std::make_unique<U1>(std::vector<int>{t}, u1_6_args)
                        ->default_decompose();
  for (auto& gate : u1_6_gates) {
    gates.push_back(std::move(gate));
  }
  u1_6_gates.clear();
  ;

  // U2(t, [0, π])
  std::vector<double> u2_3_args = {0.0, M_PI};
  auto u2_3_gates = std::make_unique<U2>(std::vector<int>{t}, u2_3_args)
                        ->default_decompose();
  for (auto& gate : u2_3_gates) {
    gates.push_back(std::move(gate));
  }
  u2_3_gates.clear();
  ;

  // U1(t, π/4)
  std::vector<double> u1_7_args = {M_PI / 4.0};
  auto u1_7_gates = std::make_unique<U1>(std::vector<int>{t}, u1_7_args)
                        ->default_decompose();
  for (auto& gate : u1_7_gates) {
    gates.push_back(std::move(gate));
  }
  u1_7_gates.clear();
  ;

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // U1(t, -π/4)
  std::vector<double> u1_8_args = {-M_PI / 4.0};
  auto u1_8_gates = std::make_unique<U1>(std::vector<int>{t}, u1_8_args)
                        ->default_decompose();
  for (auto& gate : u1_8_gates) {
    gates.push_back(std::move(gate));
  }
  u1_8_gates.clear();
  ;

  // U2(t, [0, π])
  std::vector<double> u2_4_args = {0.0, M_PI};
  auto u2_4_gates = std::make_unique<U2>(std::vector<int>{t}, u2_4_args)
                        ->default_decompose();
  for (auto& gate : u2_4_gates) {
    gates.push_back(std::move(gate));
  }
  u2_4_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> RC3X ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<RC3X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];

  // 直接返回基本门
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{M_PI / 4.0}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(std::make_unique<U1>(std::vector<int>{t},
                                       std::vector<double>{-M_PI / 4.0}));
  gates.push_back(std::make_unique<U2>(std::vector<int>{t},
                                       std::vector<double>{0.0, M_PI}));

  return gates;
}

std::array<std::complex<double>, 256> RC3X ::to_matrix() const {
  // RC3X 门矩阵 (16×16)
  std::array<std::complex<double>, 256> rc3x_matrix = {0};

  // 填充单位矩阵
  for (int i = 0; i < 16; ++i) {
    rc3x_matrix[i * 16 + i] = std::complex<double>(1.0, 0.0);
  }

  // 设置特殊元素
  rc3x_matrix[3 * 16 + 3] = std::complex<double>(0.0, 1.0);     // |0011⟩ -> +i
  rc3x_matrix[5 * 16 + 5] = std::complex<double>(-1.0, 0.0);    // |0101⟩ -> -1
  rc3x_matrix[11 * 16 + 11] = std::complex<double>(0.0, -1.0);  // |1011⟩ -> -i
  rc3x_matrix[15 * 16 + 7] =
      std::complex<double>(-1.0, 0.0);  // |1111⟩ -> |0111⟩, -1
  rc3x_matrix[7 * 16 + 15] =
      std::complex<double>(0.0, 1.0);  // |0111⟩ -> |1111⟩, +i

  return rc3x_matrix;
}

std::string RC3X ::to_string() const {
  return "RC3X(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

C3X ::C3X(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::FOUR_QUBIT_GATE_C3X, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> C3X ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<C3X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];
  double pi_8 = M_PI / 8.0;

  // H(t)
  auto h_gates = std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // P(c1, π/8)
  std::vector<double> p_c1_args = {pi_8};
  auto p_c1_gates = std::make_unique<P>(std::vector<int>{c1}, p_c1_args)
                        ->default_decompose();
  for (auto& gate : p_c1_gates) {
    gates.push_back(std::move(gate));
  }
  p_c1_gates.clear();
  ;

  // P(c2, π/8)
  std::vector<double> p_c2_args = {pi_8};
  auto p_c2_gates = std::make_unique<P>(std::vector<int>{c2}, p_c2_args)
                        ->default_decompose();
  for (auto& gate : p_c2_gates) {
    gates.push_back(std::move(gate));
  }
  p_c2_gates.clear();
  ;

  // P(c3, π/8)
  std::vector<double> p_c3_args = {pi_8};
  auto p_c3_gates = std::make_unique<P>(std::vector<int>{c3}, p_c3_args)
                        ->default_decompose();
  for (auto& gate : p_c3_gates) {
    gates.push_back(std::move(gate));
  }
  p_c3_gates.clear();
  ;

  // P(t, π/8)
  std::vector<double> p_t_args = {pi_8};
  auto p_t_gates =
      std::make_unique<P>(std::vector<int>{t}, p_t_args)->default_decompose();
  for (auto& gate : p_t_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_gates.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  // P(c2, -π/8)
  std::vector<double> p_c2_neg_args = {-pi_8};
  auto p_c2_neg_gates =
      std::make_unique<P>(std::vector<int>{c2}, p_c2_neg_args)
          ->default_decompose();
  for (auto& gate : p_c2_neg_gates) {
    gates.push_back(std::move(gate));
  }
  p_c2_neg_gates.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  // CX(c2, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));

  // P(c3, -π/8)
  std::vector<double> p_c3_neg_args = {-pi_8};
  auto p_c3_neg_gates =
      std::make_unique<P>(std::vector<int>{c3}, p_c3_neg_args)
          ->default_decompose();
  for (auto& gate : p_c3_neg_gates) {
    gates.push_back(std::move(gate));
  }
  p_c3_neg_gates.clear();
  ;

  // CX(c1, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));

  // P(c3, π/8)
  std::vector<double> p_c3_pos_args = {pi_8};
  auto p_c3_pos_gates =
      std::make_unique<P>(std::vector<int>{c3}, p_c3_pos_args)
          ->default_decompose();
  for (auto& gate : p_c3_pos_gates) {
    gates.push_back(std::move(gate));
  }
  p_c3_pos_gates.clear();
  ;

  // CX(c2, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));

  // P(c3, -π/8)
  auto p_c3_neg2_gates =
      std::make_unique<P>(std::vector<int>{c3}, p_c3_neg_args)
          ->default_decompose();
  for (auto& gate : p_c3_neg2_gates) {
    gates.push_back(std::move(gate));
  }
  p_c3_neg2_gates.clear();
  ;

  // CX(c1, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // P(t, -π/8)
  std::vector<double> p_t_neg_args = {-pi_8};
  auto p_t_neg_gates = std::make_unique<P>(std::vector<int>{t}, p_t_neg_args)
                           ->default_decompose();
  for (auto& gate : p_t_neg_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_neg_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // P(t, π/8)
  auto p_t_pos_gates =
      std::make_unique<P>(std::vector<int>{t}, p_t_args)->default_decompose();
  for (auto& gate : p_t_pos_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_pos_gates.clear();
  ;

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // P(t, -π/8)
  auto p_t_neg2_gates = std::make_unique<P>(std::vector<int>{t}, p_t_neg_args)
                            ->default_decompose();
  for (auto& gate : p_t_neg2_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_neg2_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // P(t, π/8)
  auto p_t_pos2_gates =
      std::make_unique<P>(std::vector<int>{t}, p_t_args)->default_decompose();
  for (auto& gate : p_t_pos2_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_pos2_gates.clear();
  ;

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // P(t, -π/8)
  auto p_t_neg3_gates = std::make_unique<P>(std::vector<int>{t}, p_t_neg_args)
                            ->default_decompose();
  for (auto& gate : p_t_neg3_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_neg3_gates.clear();
  ;

  // CX(c2, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));

  // P(t, π/8)
  auto p_t_pos3_gates =
      std::make_unique<P>(std::vector<int>{t}, p_t_args)->default_decompose();
  for (auto& gate : p_t_pos3_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_pos3_gates.clear();
  ;

  // CX(c3, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));

  // P(t, -π/8)
  auto p_t_neg4_gates = std::make_unique<P>(std::vector<int>{t}, p_t_neg_args)
                            ->default_decompose();
  for (auto& gate : p_t_neg4_gates) {
    gates.push_back(std::move(gate));
  }
  p_t_neg4_gates.clear();
  ;

  // CX(c1, t)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));

  // H(t)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> C3X ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<C3X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];
  double pi_8 = M_PI / 8.0;

  // 直接返回基本门
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c1}, std::vector<double>{pi_8}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c2}, std::vector<double>{pi_8}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c3}, std::vector<double>{pi_8}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c2}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c3}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c3}, std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{c3}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c3, t}));
  gates.push_back(
      std::make_unique<P>(std::vector<int>{t}, std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, t}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));

  return gates;
}

std::array<std::complex<double>, 256> C3X ::to_matrix() const {
  // C3X 门矩阵 (16×16)
  std::array<std::complex<double>, 256> c3x_matrix = {0};

  // 填充单位矩阵
  for (int i = 0; i < 16; ++i) {
    c3x_matrix[i * 16 + i] = std::complex<double>(1.0, 0.0);
  }

  // 交换 |1111⟩ 和 |0111⟩
  c3x_matrix[15 * 16 + 7] = std::complex<double>(1.0, 0.0);
  c3x_matrix[7 * 16 + 15] = std::complex<double>(1.0, 0.0);
  c3x_matrix[7 * 16 + 7] = std::complex<double>(0.0, 0.0);
  c3x_matrix[15 * 16 + 15] = std::complex<double>(0.0, 0.0);

  return c3x_matrix;
}

std::string C3X ::to_string() const {
  return "C3X(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

C3SQRTX ::C3SQRTX(std::vector<int> targets_, std::vector<double> arg_value_,
                  OperationType gate_type)
    : GateOperation(Constant::FOUR_QUBIT_GATE_C3SQRTX, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> C3SQRTX ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<C3SQRTX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];
  double pi_8 = M_PI / 8.0;

  // H(t)
  auto h_gates = std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CU1(c1, t, π/8)
  std::vector<double> cu1_1_args = {pi_8};
  auto cu1_1_gates = std::make_unique<CU1>(std::vector<int>{c1, t}, cu1_1_args)
                         ->default_decompose();
  for (auto& gate : cu1_1_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_1_gates.clear();
  ;

  // H(t)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  // H(t)
  auto h_gates3 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates3) {
    gates.push_back(std::move(gate));
  }
  h_gates3.clear();
  ;

  // CU1(c2, t, -π/8)
  std::vector<double> cu1_2_args = {-pi_8};
  auto cu1_2_gates = std::make_unique<CU1>(std::vector<int>{c2, t}, cu1_2_args)
                         ->default_decompose();
  for (auto& gate : cu1_2_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_2_gates.clear();
  ;

  // H(t)
  auto h_gates4 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates4) {
    gates.push_back(std::move(gate));
  }
  h_gates4.clear();
  ;

  // CX(c1, c2)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));

  // H(t)
  auto h_gates5 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates5) {
    gates.push_back(std::move(gate));
  }
  h_gates5.clear();
  ;

  // CU1(c2, t, π/8)
  auto cu1_3_gates = std::make_unique<CU1>(std::vector<int>{c2, t}, cu1_1_args)
                         ->default_decompose();
  for (auto& gate : cu1_3_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_3_gates.clear();
  ;

  // H(t)
  auto h_gates6 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates6) {
    gates.push_back(std::move(gate));
  }
  h_gates6.clear();
  ;

  // CX(c2, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));

  // H(t)
  auto h_gates7 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates7) {
    gates.push_back(std::move(gate));
  }
  h_gates7.clear();
  ;

  // CU1(c3, t, -π/8)
  auto cu1_4_gates = std::make_unique<CU1>(std::vector<int>{c3, t}, cu1_2_args)
                         ->default_decompose();
  for (auto& gate : cu1_4_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_4_gates.clear();
  ;

  // H(t)
  auto h_gates8 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates8) {
    gates.push_back(std::move(gate));
  }
  h_gates8.clear();
  ;

  // CX(c1, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));

  // H(t)
  auto h_gates9 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates9) {
    gates.push_back(std::move(gate));
  }
  h_gates9.clear();
  ;

  // CU1(c3, t, π/8)
  std::vector<double> cu1_5_args = {pi_8};
  auto cu1_5_gates = std::make_unique<CU1>(std::vector<int>{c3, t}, cu1_5_args)
                         ->default_decompose();
  for (auto& gate : cu1_5_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_5_gates.clear();
  ;

  // H(t)
  auto h_gates10 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates10) {
    gates.push_back(std::move(gate));
  }
  h_gates10.clear();
  ;

  // CX(c2, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));

  // H(t)
  auto h_gates11 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates11) {
    gates.push_back(std::move(gate));
  }
  h_gates11.clear();
  ;

  // CU1(c3, t, -π/8)
  auto cu1_6_gates = std::make_unique<CU1>(std::vector<int>{c3, t}, cu1_2_args)
                         ->default_decompose();
  for (auto& gate : cu1_6_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_6_gates.clear();
  ;

  // H(t)
  auto h_gates12 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates12) {
    gates.push_back(std::move(gate));
  }
  h_gates12.clear();
  ;

  // CX(c1, c3)
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));

  // H(t)
  auto h_gates13 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates13) {
    gates.push_back(std::move(gate));
  }
  h_gates13.clear();
  ;

  // CU1(c3, t, π/8)
  auto cu1_7_gates = std::make_unique<CU1>(std::vector<int>{c3, t}, cu1_1_args)
                         ->default_decompose();
  for (auto& gate : cu1_7_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_7_gates.clear();
  ;

  // H(t)
  auto h_gates14 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates14) {
    gates.push_back(std::move(gate));
  }
  h_gates14.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> C3SQRTX ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 4) {
    gates.push_back(std::make_unique<C3SQRTX>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int t = targets[3];
  double pi_8 = M_PI / 8.0;

  // 直接返回基本门
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c1, t},
                                        std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c2, t},
                                        std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c2}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c2, t},
                                        std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c3, t},
                                        std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c3, t},
                                        std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c2, c3}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c3, t},
                                        std::vector<double>{-pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CX>(std::vector<int>{c1, c3}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c3, t},
                                        std::vector<double>{pi_8}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));

  return gates;
}

std::array<std::complex<double>, 256> C3SQRTX ::to_matrix() const {
  // C3√X 门矩阵 (16×16)
  std::array<std::complex<double>, 256> c3sqrtx_matrix = {0};

  // 填充单位矩阵
  for (int i = 0; i < 16; ++i) {
    c3sqrtx_matrix[i * 16 + i] = std::complex<double>(1.0, 0.0);
  }

  // 计算 √X 矩阵元素
  std::complex<double> sx_elem1(0.5, 0.5);   // 0.5 + 0.5i
  std::complex<double> sx_elem2(0.5, -0.5);  // 0.5 - 0.5i

  // 当控制比特为 111 时，目标比特应用 √X
  int control_state = 7;  // 二进制 111
  int target_index = 3;   // 目标比特索引

  // 计算受影响的状态
  for (int i = 0; i < 16; ++i) {
    if ((i >> target_index) & 1) {
      // 目标比特为 1
      int control_bits = (i >> (target_index + 1)) << (target_index + 1) |
                         (i & ((1 << target_index) - 1));
      if (control_bits == (control_state << (target_index + 1))) {
        int j = i ^ (1 << target_index);        // 翻转目标比特
        c3sqrtx_matrix[i * 16 + i] = sx_elem1;  // 对角元素
        c3sqrtx_matrix[i * 16 + j] = sx_elem2;  // 非对角元素
        c3sqrtx_matrix[j * 16 + i] = sx_elem2;  // 非对角元素
        c3sqrtx_matrix[j * 16 + j] = sx_elem1;  // 对角元素
      }
    }
  }

  return c3sqrtx_matrix;
}

std::string C3SQRTX ::to_string() const {
  return "C3SQRTX(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

C4X ::C4X(std::vector<int> targets_, std::vector<double> arg_value_,
          OperationType gate_type)
    : GateOperation(Constant::FIVE_QUBIT_GATE_C4X, std::move(targets_),
                    std::move(arg_value_), gate_type, false) {}

std::vector<std::unique_ptr<BaseOperation>> C4X ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 5) {
    gates.push_back(std::make_unique<C4X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int c4 = targets[3];
  int t = targets[4];
  double pi_2 = M_PI / 2.0;

  // H(t)
  auto h_gates = std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates) {
    gates.push_back(std::move(gate));
  }
  h_gates.clear();
  ;

  // CU1(c4, t, π/2)
  std::vector<double> cu1_1_args = {pi_2};
  auto cu1_1_gates = std::make_unique<CU1>(std::vector<int>{c4, t}, cu1_1_args)
                         ->default_decompose();
  for (auto& gate : cu1_1_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_1_gates.clear();
  ;

  // H(t)
  auto h_gates2 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates2) {
    gates.push_back(std::move(gate));
  }
  h_gates2.clear();
  ;

  // C3X(c1, c2, c3, c4)
  auto c3x_gates = std::make_unique<C3X>(std::vector<int>{c1, c2, c3, c4})
                       ->default_decompose();
  for (auto& gate : c3x_gates) {
    gates.push_back(std::move(gate));
  }
  c3x_gates.clear();
  ;

  // H(t)
  auto h_gates3 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates3) {
    gates.push_back(std::move(gate));
  }
  h_gates3.clear();
  ;

  // CU1(c4, t, -π/2)
  std::vector<double> cu1_2_args = {-pi_2};
  auto cu1_2_gates = std::make_unique<CU1>(std::vector<int>{c4, t}, cu1_2_args)
                         ->default_decompose();
  for (auto& gate : cu1_2_gates) {
    gates.push_back(std::move(gate));
  }
  cu1_2_gates.clear();
  ;

  // H(t)
  auto h_gates4 =
      std::make_unique<H>(std::vector<int>{t})->default_decompose();
  for (auto& gate : h_gates4) {
    gates.push_back(std::move(gate));
  }
  h_gates4.clear();
  ;

  // C3X(c1, c2, c3, c4)
  auto c3x_gates2 = std::make_unique<C3X>(std::vector<int>{c1, c2, c3, c4})
                        ->default_decompose();
  for (auto& gate : c3x_gates2) {
    gates.push_back(std::move(gate));
  }
  c3x_gates2.clear();
  ;

  // C3SQRTX(c1, c2, c3, t)
  auto c3sqrtx_gates =
      std::make_unique<C3SQRTX>(std::vector<int>{c1, c2, c3, t})
          ->default_decompose();
  for (auto& gate : c3sqrtx_gates) {
    gates.push_back(std::move(gate));
  }
  c3sqrtx_gates.clear();
  ;

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> C4X ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (targets.size() < 5) {
    gates.push_back(std::make_unique<C4X>(targets, arg_value));
    return gates;
  }

  int c1 = targets[0];
  int c2 = targets[1];
  int c3 = targets[2];
  int c4 = targets[3];
  int t = targets[4];
  double pi_2 = M_PI / 2.0;

  // 直接返回基本门
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c4, t},
                                        std::vector<double>{pi_2}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));

  // 使用 decompose_to_1q2q
  auto c3x_gates = std::make_unique<C3X>(std::vector<int>{c1, c2, c3, c4})
                       ->decompose_to_1q2q();
  for (auto& gate : c3x_gates) {
    gates.push_back(std::move(gate));
  }
  c3x_gates.clear();
  ;

  gates.push_back(std::make_unique<H>(std::vector<int>{t}));
  gates.push_back(std::make_unique<CU1>(std::vector<int>{c4, t},
                                        std::vector<double>{-pi_2}));
  gates.push_back(std::make_unique<H>(std::vector<int>{t}));

  auto c3x_gates2 = std::make_unique<C3X>(std::vector<int>{c1, c2, c3, c4})
                        ->decompose_to_1q2q();
  for (auto& gate : c3x_gates2) {
    gates.push_back(std::move(gate));
  }
  c3x_gates2.clear();
  ;

  auto c3sqrtx_gates =
      std::make_unique<C3SQRTX>(std::vector<int>{c1, c2, c3, t})
          ->decompose_to_1q2q();
  for (auto& gate : c3sqrtx_gates) {
    gates.push_back(std::move(gate));
  }
  c3sqrtx_gates.clear();
  ;

  return gates;
}

std::array<std::complex<double>, 1024> C4X ::to_matrix() const {
  // C4X 门矩阵 (32×32)
  std::array<std::complex<double>, 1024> c4x_matrix = {0};

  // 填充单位矩阵
  for (int i = 0; i < 32; ++i) {
    c4x_matrix[i * 32 + i] = std::complex<double>(1.0, 0.0);
  }

  // 交换 |11111⟩ 和 |01111⟩
  int state_11111 = 31;  // 二进制 11111
  int state_01111 = 15;  // 二进制 01111

  c4x_matrix[state_11111 * 32 + state_01111] = std::complex<double>(1.0, 0.0);
  c4x_matrix[state_01111 * 32 + state_11111] = std::complex<double>(1.0, 0.0);
  c4x_matrix[state_01111 * 32 + state_01111] = std::complex<double>(0.0, 0.0);
  c4x_matrix[state_11111 * 32 + state_11111] = std::complex<double>(0.0, 0.0);

  return c4x_matrix;
}

std::string C4X ::to_string() const {
  return "C4X(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

U1 ::U1(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_U1, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> U1 ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  if (!arg_value.empty()) {
    gates.push_back(std::make_unique<RZ>(targets, arg_value));
  }
  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> U1 ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<U1>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> U1 ::to_matrix() const {
  double lambda = arg_value.empty() ? 0.0 : arg_value[0];
  std::complex<double> phase = std::exp(std::complex<double>(0.0, lambda));

  return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
          std::complex<double>(0.0, 0.0), phase};
}

std::string U1 ::to_string() const {
  return "U1(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

U2 ::U2(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_U2, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> U2 ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (arg_value.size() < 2) {
    gates.push_back(std::make_unique<U2>(targets, arg_value));
    return gates;
  }

  double phi = arg_value[0];
  double lam = arg_value[1];

  // RZ(lam - π/2)
  std::vector<double> rz1_args = {lam - M_PI / 2.0};
  gates.push_back(std::make_unique<RZ>(targets, rz1_args));

  // RX(π/2)
  std::vector<double> rx_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx_args));

  // RZ(phi + π/2)
  std::vector<double> rz2_args = {phi + M_PI / 2.0};
  gates.push_back(std::make_unique<RZ>(targets, rz2_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> U2 ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<U2>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> U2 ::to_matrix() const {
  if (arg_value.size() < 2) {
    return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
            std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
  }

  double phi = arg_value[0];
  double lam = arg_value[1];

  double inv_sqrt2 = 1.0 / std::sqrt(2.0);
  std::complex<double> exp_i_lam = std::exp(std::complex<double>(0.0, lam));
  std::complex<double> exp_i_phi = std::exp(std::complex<double>(0.0, phi));
  std::complex<double> exp_i_phi_lam =
      std::exp(std::complex<double>(0.0, phi + lam));

  return {std::complex<double>(inv_sqrt2, 0.0),
          -exp_i_lam * std::complex<double>(inv_sqrt2, 0.0),
          exp_i_phi * std::complex<double>(inv_sqrt2, 0.0),
          exp_i_phi_lam * std::complex<double>(inv_sqrt2, 0.0)};
}

std::string U2 ::to_string() const {
  return "U2(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

U3 ::U3(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_U3, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> U3 ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (arg_value.size() < 3) {
    gates.push_back(std::make_unique<U3>(targets, arg_value));
    return gates;
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  // RZ(lam)
  std::vector<double> rz1_args = {lam};
  gates.push_back(std::make_unique<RZ>(targets, rz1_args));

  // RX(π/2)
  std::vector<double> rx1_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx1_args));

  // RZ(theta + π)
  std::vector<double> rz2_args = {theta + M_PI};
  gates.push_back(std::make_unique<RZ>(targets, rz2_args));

  // RX(π/2)
  std::vector<double> rx2_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx2_args));

  // RZ(phi + 3π)
  std::vector<double> rz3_args = {phi + 3.0 * M_PI};
  gates.push_back(std::make_unique<RZ>(targets, rz3_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> U3 ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<U3>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> U3 ::to_matrix() const {
  if (arg_value.size() < 3) {
    return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
            std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  std::complex<double> exp_i_lam = std::exp(std::complex<double>(0.0, lam));
  std::complex<double> exp_i_phi = std::exp(std::complex<double>(0.0, phi));
  std::complex<double> exp_i_phi_lam =
      std::exp(std::complex<double>(0.0, phi + lam));

  return {std::complex<double>(cos_theta_2, 0.0),
          -exp_i_lam * std::complex<double>(sin_theta_2, 0.0),
          exp_i_phi * std::complex<double>(sin_theta_2, 0.0),
          exp_i_phi_lam * std::complex<double>(cos_theta_2, 0.0)};
}

std::string U3 ::to_string() const {
  return "U3(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

U ::U(std::vector<int> targets_, std::vector<double> arg_value_)
    : GateOperation(Constant::SINGLE_QUBIT_GATE_U, std::move(targets_),
                    std::move(arg_value_),
                    OperationType::SINGLE_QUBIT_OPERATION, false) {}

std::vector<std::unique_ptr<BaseOperation>> U ::default_decompose() {
  std::vector<std::unique_ptr<BaseOperation>> gates;

  if (arg_value.size() < 3) {
    gates.push_back(std::make_unique<U>(targets, arg_value));
    return gates;
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  // 与 U3 相同的分解
  // RZ(lam)
  std::vector<double> rz1_args = {lam};
  gates.push_back(std::make_unique<RZ>(targets, rz1_args));

  // RX(π/2)
  std::vector<double> rx1_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx1_args));

  // RZ(theta + π)
  std::vector<double> rz2_args = {theta + M_PI};
  gates.push_back(std::make_unique<RZ>(targets, rz2_args));

  // RX(π/2)
  std::vector<double> rx2_args = {M_PI / 2.0};
  gates.push_back(std::make_unique<RX>(targets, rx2_args));

  // RZ(phi + 3π)
  std::vector<double> rz3_args = {phi + 3.0 * M_PI};
  gates.push_back(std::make_unique<RZ>(targets, rz3_args));

  return gates;
}

std::vector<std::unique_ptr<BaseOperation>> U ::decompose_to_1q2q() {
  std::vector<std::unique_ptr<BaseOperation>> gates;
  gates.push_back(std::make_unique<U>(targets, arg_value));
  return gates;
}

std::array<std::complex<double>, 4> U ::to_matrix() const {
  if (arg_value.size() < 3) {
    return {std::complex<double>(1.0, 0.0), std::complex<double>(0.0, 0.0),
            std::complex<double>(0.0, 0.0), std::complex<double>(1.0, 0.0)};
  }

  double theta = arg_value[0];
  double phi = arg_value[1];
  double lam = arg_value[2];

  double cos_theta_2 = std::cos(theta / 2.0);
  double sin_theta_2 = std::sin(theta / 2.0);

  std::complex<double> exp_i_lam = std::exp(std::complex<double>(0.0, lam));
  std::complex<double> exp_i_phi = std::exp(std::complex<double>(0.0, phi));
  std::complex<double> exp_i_phi_lam =
      std::exp(std::complex<double>(0.0, phi + lam));

  return {std::complex<double>(cos_theta_2, 0.0),
          -exp_i_lam * std::complex<double>(sin_theta_2, 0.0),
          exp_i_phi * std::complex<double>(sin_theta_2, 0.0),
          exp_i_phi_lam * std::complex<double>(cos_theta_2, 0.0)};
}

std::string U ::to_string() const {
  return "U(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Sync::Sync(std::vector<int> targets, std::vector<double> arg_value,
           OperationType operation_type)
    : BaseOperation("sync", std::move(targets), std::move(arg_value),
                    operation_type) {}

std::string Sync::to_string() const {
  return "Sync(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Measure::Measure(std::vector<int> targets, std::vector<double> arg_value,
                 OperationType operation_type)
    : BaseOperation("measure", std::move(targets), std::move(arg_value),
                    operation_type) {}

std::string Measure::to_string() const {
  return "Measure(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Move::Move(std::vector<int> targets, std::vector<double> arg_value,
           OperationType operation_type)
    : BaseOperation("move", std::move(targets), std::move(arg_value),
                    operation_type) {}

std::string Move::to_string() const {
  return "Move(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

Reset::Reset(std::vector<int> targets, std::vector<double> arg_value,
             OperationType operation_type)
    : BaseOperation("reset", std::move(targets), std::move(arg_value),
                    operation_type) {}

std::string Reset::to_string() const {
  return "Reset(targets=" + targets_to_string() +
         ", arg_value=" + arg_value_to_string() + ")";
}

std::unique_ptr<BaseOperation> create_gate(const std::string& name,
                                           std::vector<int> targets,
                                           std::vector<double> arg_value,
                                           bool allow_undefined) {
  if (name == Constant::SINGLE_QUBIT_GATE_H) {
    return std::make_unique<H>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_X) {
    return std::make_unique<X>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_Y) {
    return std::make_unique<Y>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_Z) {
    return std::make_unique<Z>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_R) {
    return std::make_unique<R>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_RX) {
    return std::make_unique<RX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_RY) {
    return std::make_unique<RY>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_RZ) {
    return std::make_unique<RZ>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_SX) {
    return std::make_unique<SX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_SXDG) {
    return std::make_unique<SXDG>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_S) {
    return std::make_unique<S>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_T) {
    return std::make_unique<T>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_P) {
    return std::make_unique<P>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_SDG) {
    return std::make_unique<SDG>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_TDG) {
    return std::make_unique<TDG>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_U1) {
    return std::make_unique<U1>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_U2) {
    return std::make_unique<U2>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_U3) {
    return std::make_unique<U3>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::SINGLE_QUBIT_GATE_U) {
    return std::make_unique<U>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CX) {
    return std::make_unique<CX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CY) {
    return std::make_unique<CY>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CZ) {
    return std::make_unique<CZ>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CH) {
    return std::make_unique<CH>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_SWAP) {
    return std::make_unique<SWAP>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CRX) {
    return std::make_unique<CRX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CRY) {
    return std::make_unique<CRY>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CRZ) {
    return std::make_unique<CRZ>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CU1) {
    return std::make_unique<CU1>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CP) {
    return std::make_unique<CP>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CU3) {
    return std::make_unique<CU3>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CSX) {
    return std::make_unique<CSX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CU) {
    return std::make_unique<CU>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_RXX) {
    return std::make_unique<RXX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_RZZ) {
    return std::make_unique<RZZ>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_ISWAP) {
    return std::make_unique<ISWAP>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CS) {
    return std::make_unique<CS>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_CSDG) {
    return std::make_unique<CSDG>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_ECR) {
    return std::make_unique<ECR>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_DCX) {
    return std::make_unique<DCX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_RYY) {
    return std::make_unique<RYY>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::TWO_QUBIT_GATE_RZX) {
    return std::make_unique<RZX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::THREE_QUBIT_GATE_CCX) {
    return std::make_unique<CCX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::THREE_QUBIT_GATE_CSWAP) {
    return std::make_unique<CSWAP>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::THREE_QUBIT_GATE_RCCX) {
    return std::make_unique<RCCX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::FOUR_QUBIT_GATE_RC3X) {
    return std::make_unique<RC3X>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::FOUR_QUBIT_GATE_C3X) {
    return std::make_unique<C3X>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::FOUR_QUBIT_GATE_C3SQRTX) {
    return std::make_unique<C3SQRTX>(std::move(targets), std::move(arg_value));
  } else if (name == Constant::FIVE_QUBIT_GATE_C4X) {
    return std::make_unique<C4X>(std::move(targets), std::move(arg_value));
  } else if (name == "sync") {
    return std::make_unique<Sync>(std::move(targets), std::move(arg_value));
  } else if (name == "measure") {
    return std::make_unique<Measure>(std::move(targets), std::move(arg_value));
  } else if (name == "move") {
    return std::make_unique<Move>(std::move(targets), std::move(arg_value));
  } else if (name == "reset") {
    return std::make_unique<Reset>(std::move(targets), std::move(arg_value));
  } else {
    if (allow_undefined) {
      return std::make_unique<GateOperation>(name, std::move(targets),
                                             std::move(arg_value));
    } else {
      throw std::runtime_error(name + " is not supported");
    }
  }
}
}  // namespace qcos
