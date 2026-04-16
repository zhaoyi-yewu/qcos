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

#pragma once

#include <array>
#include <complex>
#include <memory>

#include "circuit/base_operation.h"
#include "utils/constant.h"

namespace qcos {

class GateOperation : public BaseOperation {
 public:
  bool hermitian;

  GateOperation(std::string name_, std::vector<int> targets_,
                std::vector<double> arg_value_ = {},
                OperationType op_type_ = OperationType::SINGLE_QUBIT_OPERATION,
                bool hermitian_ = true);

 private:
  void validate_params() const;
};
class H : public GateOperation {
 public:
  H(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class X : public GateOperation {
 public:
  X(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class Y : public GateOperation {
 public:
  Y(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class Z : public GateOperation {
 public:
  Z(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class S : public GateOperation {
 public:
  S(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class SDG : public GateOperation {
 public:
  SDG(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class T : public GateOperation {
 public:
  T(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class TDG : public GateOperation {
 public:
  TDG(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class P : public GateOperation {
 public:
  P(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class R : public GateOperation {
 public:
  R(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class RX : public GateOperation {
 public:
  RX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class RY : public GateOperation {
 public:
  RY(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class RZ : public GateOperation {
 public:
  RZ(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class SX : public GateOperation {
 public:
  SX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class SXDG : public GateOperation {
 public:
  SXDG(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

// 两量子比特门声明
class CZ : public GateOperation {
 public:
  CZ(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CX : public GateOperation {
 public:
  CX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CY : public GateOperation {
 public:
  CY(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class SWAP : public GateOperation {
 public:
  SWAP(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class ISWAP : public GateOperation {
 public:
  ISWAP(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
        OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CH : public GateOperation {
 public:
  CH(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CS : public GateOperation {
 public:
  CS(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CSDG : public GateOperation {
 public:
  CSDG(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CRX : public GateOperation {
 public:
  CRX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CRY : public GateOperation {
 public:
  CRY(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CRZ : public GateOperation {
 public:
  CRZ(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CU1 : public GateOperation {
 public:
  CU1(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CP : public GateOperation {
 public:
  CP(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CU3 : public GateOperation {
 public:
  CU3(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CSX : public GateOperation {
 public:
  CSX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class CU : public GateOperation {
 public:
  CU(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
     OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class ECR : public GateOperation {
 public:
  ECR(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class DCX : public GateOperation {
 public:
  DCX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class RXX : public GateOperation {
 public:
  RXX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class RYY : public GateOperation {
 public:
  RYY(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class RZZ : public GateOperation {
 public:
  RZZ(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

class RZX : public GateOperation {
 public:
  RZX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::DOUBLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 16> to_matrix() const;
  std::string to_string() const;
};

// 三量子比特门声明
class CCX : public GateOperation {
 public:
  CCX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::TRIPLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 64> to_matrix() const;
  std::string to_string() const;
};

class CSWAP : public GateOperation {
 public:
  CSWAP(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
        OperationType gate_type = OperationType::TRIPLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 64> to_matrix() const;
  std::string to_string() const;
};

class RCCX : public GateOperation {
 public:
  RCCX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType gate_type = OperationType::TRIPLE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 64> to_matrix() const;
  std::string to_string() const;
};

// 四量子比特门声明
class RC3X : public GateOperation {
 public:
  RC3X(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType gate_type = OperationType::FOUR_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 256> to_matrix() const;
  std::string to_string() const;
};

class C3X : public GateOperation {
 public:
  C3X(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::FOUR_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 256> to_matrix() const;
  std::string to_string() const;
};
class C3SQRTX : public GateOperation {
 public:
  C3SQRTX(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
          OperationType gate_type = OperationType::FOUR_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 256> to_matrix() const;
  std::string to_string() const;
};

// 五量子比特门声明
class C4X : public GateOperation {
 public:
  C4X(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
      OperationType gate_type = OperationType::FIVE_QUBIT_OPERATION);
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 1024> to_matrix() const;
  std::string to_string() const;
};

// 单量子比特通用门声明
class U1 : public GateOperation {
 public:
  U1(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class U2 : public GateOperation {
 public:
  U2(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class U3 : public GateOperation {
 public:
  U3(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class U : public GateOperation {
 public:
  U(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {});
  std::vector<std::shared_ptr<BaseOperation>> default_decompose();
  std::vector<std::shared_ptr<BaseOperation>> decompose_to_1q2q();
  std::array<std::complex<double>, 4> to_matrix() const;
  std::string to_string() const;
};

class Sync : public BaseOperation {
 public:
  Sync(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType operation_type = qcos::OperationType::SYNC);
  std::string to_string() const;
};

class Measure : public BaseOperation {
 public:
  Measure(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
          OperationType operation_type = qcos::OperationType::MEASURE);
  std::string to_string() const;
};

class Move : public BaseOperation {
 public:
  Move(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
       OperationType operation_type = qcos::OperationType::MOVE);
  std::string to_string() const;
};

class Reset : public BaseOperation {
 public:
  Reset(std::vector<int> targets_ = {}, std::vector<double> arg_value_ = {},
        OperationType operation_type = qcos::OperationType::RESET);
  std::string to_string() const;
};

std::shared_ptr<BaseOperation> create_gate(const std::string& name,
                                           std::vector<int> targets = {},
                                           std::vector<double> arg_value = {},
                                           bool allow_undefined = false);
}  // namespace qcos
