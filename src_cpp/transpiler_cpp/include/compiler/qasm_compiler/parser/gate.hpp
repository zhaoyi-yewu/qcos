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

#include "compiler/qasm_compiler/parser/nested_environment.hpp"
#include "compiler/qasm_compiler/parser/statement.hpp"
#include "compiler/quantum_computation.hpp"

namespace qasm {
enum class GateKind { Standard, Compound };

struct GateInfo {
  size_t nControls;
  size_t nTargets;
  size_t nParameters;
  qc::OpType type;
};

struct Gate {
  GateKind gateKind;

  virtual ~Gate() = default;

  virtual size_t getNControls() = 0;
  virtual size_t getNTargets() = 0;
  virtual size_t getNParameters() = 0;

 protected:
  explicit Gate(GateKind kind) : gateKind(kind) {}
};

struct StandardGate : Gate {
  GateInfo info;

  explicit StandardGate(const GateInfo& gateInfo)
      : Gate(GateKind::Standard), info(gateInfo) {}

  size_t getNControls() override { return info.nControls; }

  size_t getNTargets() override { return info.nTargets; }
  size_t getNParameters() override { return info.nParameters; }
};

struct CompoundGate : Gate {
  std::vector<std::string> parameterNames;
  std::vector<std::string> targetNames;
  std::vector<std::shared_ptr<QuantumStatement>> body;

  explicit CompoundGate(
      std::vector<std::string> parameters, std::vector<std::string> targets,
      std::vector<std::shared_ptr<QuantumStatement>> bodyStatements)
      : Gate(GateKind::Compound),
        parameterNames(std::move(parameters)),
        targetNames(std::move(targets)),
        body(std::move(bodyStatements)) {}

  size_t getNControls() override { return 0; }

  size_t getNTargets() override { return targetNames.size(); }
  size_t getNParameters() override { return parameterNames.size(); }
};
}  // namespace qasm
