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

#include "compiler/qasm_to_origin_ir.hpp"

#include "circuit/gate_operation.h"
#include "compiler/quantum_computation.hpp"

using namespace qcos;

std::string qasmfile2str(const std::string& filename) {
  std::stringstream ss;
  std::ifstream ifs;
  ifs.open(filename);
  if (ifs.is_open()) {
    std::string line;
    std::cout << "### opened qasm file:" << filename << std::endl;
    while (std::getline(ifs, line)) {
      ss << line;
    }
    ifs.close();
  } else {
    std::cerr << "###Error: qasmfile2str open " << filename << "failed."
              << std::endl;
    exit(-1);
    return {};
  }
  return ss.str();
}
/*
std::string convert_qasm_to_originir(std::string qasm_filepath) {
  return QuantumComputation::fromQASM(qasmfile2str(qasm_filepath))
      .toOriginIR();
}
std::string convert_qasm_string_to_originir(std::string qasm_str) {
  return QuantumComputation::fromQASM(qasm_str).toOriginIR();
}
std::vector<std::unique_ptr<Operation>> convert_qasm_string_to_operations(
    std::string qasm_str) {
  auto qc = QuantumComputation::fromQASM(qasm_str);
  return std::move(qc.getOps());
}
std::pair<std::vector<std::shared_ptr<qcos::BaseOperation>>, int>
convert_qasm_string_to_qcos_operations(std::string qasm_str) {
  auto qc = QuantumComputation::fromQASM(qasm_str);
  const std::vector<std::unique_ptr<Operation>>& ops = qc.getOps();
  int qubits_num = static_cast<int>(qc.getNqubits());
  std::vector<std::shared_ptr<qcos::BaseOperation>> operations;
  operations.reserve(ops.size());
  operations = create_gates(ops);
  return {operations, qubits_num};
}
*/
std::pair<std::vector<std::shared_ptr<qcos::BaseOperation>>, int>
convert_qasm_string_to_qcos_operations(std::string qasm_str) {
  auto qc = qc::QuantumComputation::fromQASM(qasm_str);
  int qubits_num = static_cast<int>(qc.getNqubits());
  return {qc.getOps(), qubits_num};
}
/*
std::vector<std::shared_ptr<qcos::BaseOperation>> create_gates(
    const std::vector<std::unique_ptr<Operation>>& ops) {
  std::vector<std::shared_ptr<qcos::BaseOperation>> operations;
  operations.reserve(ops.size());
  for (const auto& op : ops) {
    std::vector<int> all_qubits;
    std::vector<double> arg_values = op->getParameter();
    for (const auto& control : op->getControls()) {
      all_qubits.push_back(static_cast<int>(control.qubit));
    }

    for (const auto& target : op->getTargets()) {
      all_qubits.push_back(static_cast<int>(target));
    }
    std::shared_ptr<qcos::BaseOperation> operation = nullptr;
    std::vector<std::shared_ptr<qcos::BaseOperation>> subOperations = {};
    switch (op->type) {
      case otI:
        break;
      case otClassicControlled:
        break;
      case otH:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_H, all_qubits, arg_values);
        break;
      case otX:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_X, all_qubits, arg_values);
        break;
      case otY:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_Y, all_qubits, arg_values);
        break;
      case otZ:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_Z, all_qubits, arg_values);
        break;
      case otS:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_S, all_qubits, arg_values);
        break;
      case otT:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_T, all_qubits, arg_values);
        break;
      case otCNOT:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CX, all_qubits, arg_values);
        break;
      case otCZ:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CZ, all_qubits, arg_values);
        break;
      case otSWAP:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_SWAP, all_qubits, arg_values);
        break;
      case otRX:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_RX, all_qubits,
                                arg_values);
        break;
      case otRY:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_RY, all_qubits,
                                arg_values);
        break;
      case otRZ:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_RZ, all_qubits,
                                arg_values);
        break;
      case otP:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_P, all_qubits, arg_values);
        break;
      case otRXX:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_RXX, all_qubits, arg_values);
        break;
      case otRYY:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_RYY, all_qubits, arg_values);
        break;
      case otRZZ:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_RZZ, all_qubits, arg_values);
        break;
      case otRZX:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_RZX, all_qubits, arg_values);
        break;
      case otTOFFOLI:
        operation = create_gate(Constant::THREE_QUBIT_GATE_CCX, all_qubits,
                                arg_values);
        break;
      case otU2:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_U2, all_qubits,
                                arg_values);
        break;
      case otU3:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_U3, all_qubits,
                                arg_values);
        break;
      case otCU:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CU, all_qubits, arg_values);
        break;
      case otCU3:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CU3, all_qubits, arg_values);
        break;
      case otC3X:
        operation =
            create_gate(Constant::FOUR_QUBIT_GATE_C3X, all_qubits, arg_values);
        break;
      case otSdg:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_SDG, all_qubits,
                                arg_values);
        break;
      case otCP:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CP, all_qubits, arg_values);
        break;
      case otCRX:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CRX, all_qubits, arg_values);
        break;
      case otRCCX:
        operation = create_gate(Constant::THREE_QUBIT_GATE_RCCX, all_qubits,
                                arg_values);
        break;
      case otRC3X:
        operation = create_gate(Constant::FOUR_QUBIT_GATE_RC3X, all_qubits,
                                arg_values);
        break;
      case otTdg:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_TDG, all_qubits,
                                arg_values);
        break;
      case otCSWAP:
        operation = create_gate(Constant::THREE_QUBIT_GATE_CSWAP, all_qubits,
                                arg_values);
        break;
      case otCRY:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CRY, all_qubits, arg_values);
        break;
      case otCRZ:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CRZ, all_qubits, arg_values);
        break;
      case otSXdg:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_SXDG, all_qubits,
                                arg_values);
        break;
      case otCH:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CH, all_qubits, arg_values);
        break;
      case otCY:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CY, all_qubits, arg_values);
        break;
      case otSX:
        operation = create_gate(Constant::SINGLE_QUBIT_GATE_SX, all_qubits,
                                arg_values);
        break;
      case otCSX:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CSX, all_qubits, arg_values);
        break;
      case otC3SQRTX:
        operation = create_gate(Constant::FOUR_QUBIT_GATE_C3SQRTX, all_qubits,
                                arg_values);
        break;
      case otC4X:
        operation =
            create_gate(Constant::FIVE_QUBIT_GATE_C4X, all_qubits, arg_values);
        break;
      case ot_iSWAP:
        operation = create_gate(Constant::TWO_QUBIT_GATE_ISWAP, all_qubits,
                                arg_values);
        break;
      case otDCX:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_DCX, all_qubits, arg_values);
        break;
      case otCS:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CS, all_qubits, arg_values);
        break;
      case otCSdg:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_CSDG, all_qubits, arg_values);
        break;
        // case otCCZ:
        // operation = create_gate(Constant::TWO_QUBIT_GATE_CSDG, all_qubits,
        // arg_values); break;
      case otECR:
        operation =
            create_gate(Constant::TWO_QUBIT_GATE_ECR, all_qubits, arg_values);
        break;
      case otR:
        operation =
            create_gate(Constant::SINGLE_QUBIT_GATE_R, all_qubits, arg_values);
        break;
      // case otXXminusYY:
      //   XXMinusYY_dump2originIR(of, qreg[targets[0]].second,
      //                           qreg[targets[1]].second, parameter[0],
      //                           parameter[1]);
      //   break;
      // case otXXplusYY:
      //   XXPlusYY_dump2originIR(of, qreg[targets[0]].second,
      //                          qreg[targets[1]].second, parameter[0],
      //                          parameter[1]);
      //   break;
      // case otV:
      //  operation = create_gate(Constant::SINGLE_QUBIT_GATE_V, all_qubits,
      //  arg_values); break;
      // case otW:
      //  W_dump2originIR(of, qreg[targets[0]].second);
      //  break;
      case otBarrier:
        operation = create_gate("sync", all_qubits, arg_values);
        break;
      case otReset:
        operation = create_gate("reset", all_qubits, arg_values);
        break;
      case otMeasure:
        if (all_qubits.empty()) {
          std::cerr << "Error: Measure operation has no qubits specified."
                    << std::endl;
        } else if (all_qubits.size() == 1) {
          operation = create_gate("measure", all_qubits, arg_values);
        } else if (all_qubits.size() > 1) {
          for (int qubit : all_qubits) {
            std::vector<int> single_qubit{qubit};
            std::vector<double> empty_params{};
            std::shared_ptr<qcos::BaseOperation> measure_op =
                create_gate("measure", single_qubit, empty_params);
            if (measure_op) {
              subOperations.push_back(std::move(measure_op));
            } else {
              std::cerr << "Error: Failed to create measure gate for qubit "
                        << qubit << std::endl;
            }
          }
        } else {
          std::cerr
              << "Error: Invalid number of qubits for measure operation: "
              << all_qubits.size() << std::endl;
        }
        break;
      case otCompound:
        if (auto* compoundOp = dynamic_cast<CompoundOperation*>(op.get())) {
          const auto& compoundOps = compoundOp->getOps();
          subOperations = create_gates(compoundOps);
        }
        break;
      default:
        std::cerr << "Error:BaseOperation::create_gate" << std::endl;
    }
    if (operation) {
      operations.push_back(std::move(operation));
    } else if (subOperations.size() > 0) {
      operations.insert(operations.end(),
                        std::make_move_iterator(subOperations.begin()),
                        std::make_move_iterator(subOperations.end()));
    } else if (op->type == otCompound && subOperations.size() == 0) {
      continue;
    } else if (op->type == otI || op->type == otClassicControlled) {
      continue;
    } else {
      std::cerr << "Warning: Failed to create gate for operation type: "
                << op->name << std::endl;
    }
  }
  return std::move(operations);
}
*/
