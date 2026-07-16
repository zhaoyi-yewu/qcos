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

#include <iostream>
#include <optional>
#include <unordered_map>
#include <utility>

#include "circuit/base_operation.h"
#include "circuit/gate_operation.h"
#include "compiler/qasm_compiler/parser/exception.hpp"
#include "compiler/qasm_compiler/parser/gate.hpp"
#include "compiler/qasm_compiler/parser/nested_environment.hpp"
#include "compiler/qasm_compiler/parser/parser.hpp"
#include "compiler/qasm_compiler/parser/passes/const_eval_pass.hpp"
#include "compiler/qasm_compiler/parser/passes/type_check_pass.hpp"
#include "compiler/qasm_compiler/parser/statement.hpp"
#include "compiler/qasm_compiler/parser/std_gates.hpp"
#include "compiler/quantum_computation.hpp"

using namespace qasm;
using const_eval::ConstEvalPass;
using const_eval::ConstEvalValue;
using type_checking::InferredType;
using type_checking::TypeCheckPass;

class OpenQasmParser final : public InstVisitor {
  ConstEvalPass constEvalPass;
  TypeCheckPass typeCheckPass;

  NestedEnvironment<std::shared_ptr<DeclarationStatement>> declarations{};
  qc::QuantumComputation* qc{};

  std::vector<std::shared_ptr<qcos::BaseOperation>> ops{};

  // Lazy copy-on-write: hold a const pointer to STANDARD_GATES by default,
  // only create a mutable copy when a custom gate is actually declared.
  const std::unordered_map<std::string, std::shared_ptr<Gate>>* gatesRef =
      &STANDARD_GATES;
  std::optional<std::unordered_map<std::string, std::shared_ptr<Gate>>>
      gatesCopy{};

  // Get mutable gates map — creates a copy on first call (copy-on-write)
  std::unordered_map<std::string, std::shared_ptr<Gate>>& getMutableGates() {
    if (!gatesCopy) {
      gatesCopy = STANDARD_GATES;
      gatesRef = &(*gatesCopy);
    }
    return *gatesCopy;
  }

  // Read-only access to gates — no copy needed
  const std::unordered_map<std::string, std::shared_ptr<Gate>>& getGates()
      const {
    return *gatesRef;
  }

  bool openQASM2CompatMode{false};

  qc::Permutation initialLayout{};
  qc::Permutation outputPermutation{};

  // ── Qubit register cache for fast operand translation ──────────────
  // For QASM 2.0 benchmarks, the register name is almost always "q".
  // Caching the base offset and size avoids a std::map::find() per operand.
  std::string cachedRegName_{};
  qc::QBit cachedRegBase_{0};
  size_t cachedRegSize_{0};

  [[noreturn]] static void error(const std::string& message,
                                 const DebugInfo& debugInfo) {
    throw CompilerError(message, DebugInfo(debugInfo));
  }

  static const std::map<std::string, std::pair<ConstEvalValue, InferredType>>&
  initializeBuiltins() {
    // Cache builtins statically — constructed once, reused across all parsers
    static const auto builtins = []() {
      std::map<std::string, std::pair<ConstEvalValue, InferredType>> m{};

      InferredType const floatTy{std::dynamic_pointer_cast<ResolvedType>(
          std::make_shared<DesignatedType<uint64_t>>(Float, 64))};

      m.emplace("pi", std::pair{ConstEvalValue(qc::qcPI), floatTy});
      m.emplace("π", std::pair{ConstEvalValue(qc::qcPI), floatTy});
      m.emplace("tau", std::pair{ConstEvalValue(qc::TAU), floatTy});
      m.emplace("τ", std::pair{ConstEvalValue(qc::TAU), floatTy});
      m.emplace("euler", std::pair{ConstEvalValue(qc::E), floatTy});
      return m;
    }();
    return builtins;
  }

  void translateGateOperand(
      const std::shared_ptr<GateOperand>& gateOperand,
      std::vector<qc::QBit>& qubits, const qc::QuantumRegisterMap& qregs,
      const DebugInfo& debugInfo) {
    translateGateOperand(gateOperand->identifier, gateOperand->expression,
                         qubits, qregs, debugInfo);
  }

  void translateGateOperand(
      const std::string& gateIdentifier,
      const std::shared_ptr<Expression>& indexExpr,
      std::vector<qc::QBit>& qubits, const qc::QuantumRegisterMap& qregs,
      const DebugInfo& debugInfo) {
    // Fast path: if the register name matches our cache, skip the map lookup.
    qc::QBit regBase = 0;
    size_t regSize = 0;
    if (gateIdentifier == cachedRegName_) {
      regBase = cachedRegBase_;
      regSize = cachedRegSize_;
    } else {
      const auto qubitIter = qregs.find(gateIdentifier);
      if (qubitIter == qregs.end()) {
        error("Usage of unknown quantum register.", debugInfo);
      }
      regBase = qubitIter->second.first;
      regSize = qubitIter->second.second;
      // Update cache for subsequent lookups
      cachedRegName_ = gateIdentifier;
      cachedRegBase_ = regBase;
      cachedRegSize_ = regSize;
    }

    if (indexExpr != nullptr) {
      const auto result = evaluatePositiveConstant(indexExpr, debugInfo);

      if (result >= regSize) {
        error(
            "Index expression must be smaller than the width of the "
            "quantum register.",
            debugInfo);
      }
      qubits.emplace_back(regBase + static_cast<qc::QBit>(result));
    } else {
      for (size_t i = 0; i < regSize; ++i) {
        qubits.emplace_back(regBase + static_cast<qc::QBit>(i));
      }
    }
  }

  void translateBitOperand(const std::string& bitIdentifier,
                           const std::shared_ptr<Expression>& indexExpr,
                           std::vector<qc::Bit>& bits,
                           const DebugInfo& debugInfo) const {
    const auto iter = qc->getCregs().find(bitIdentifier);
    if (iter == qc->getCregs().end()) {
      error("Usage of unknown classical register.", debugInfo);
    }
    auto creg = iter->second;

    if (indexExpr != nullptr) {
      const auto index = evaluatePositiveConstant(indexExpr, debugInfo);
      if (index >= creg.second) {
        error(
            "Index expression must be smaller than the width of the "
            "classical register.",
            debugInfo);
      }

      creg.first += index;
      creg.second = 1;
    }

    for (uint64_t i = 0; i < creg.second; ++i) {
      bits.emplace_back(creg.first + i);
    }
  }

  static uint64_t evaluatePositiveConstant(
      const std::shared_ptr<Expression>& expr,
      const DebugInfo& debugInfo,
      const uint64_t defaultValue = 0) {
    if (expr == nullptr) {
      return defaultValue;
    }

    const auto constInt = std::dynamic_pointer_cast<qasm::Constant>(expr);
    if (!constInt) {
      error("Expected a constant integer expression.", debugInfo);
    }

    return constInt->getUInt();
  }

 public:
  explicit OpenQasmParser(qc::QuantumComputation* quantumComputation)
      : typeCheckPass(&constEvalPass), qc(quantumComputation) {
    for (const auto& [identifier, builtin] : initializeBuiltins()) {
      constEvalPass.addConst(identifier, builtin.first);
      typeCheckPass.addBuiltin(identifier, builtin.second);
    }
  }

  ~OpenQasmParser() override = default;

  void visitProgram(const std::vector<std::shared_ptr<Statement>>& program) {
    // TODO: in the future, don't exit early, but collect all errors
    // To do this, we need to insert make sure that erroneous declarations
    // actually insert a dummy entry; also, we need to synchronize to the next
    // semicolon, to make sure we don't do some weird stuff and report false
    // errors.
    for (const auto& statement : program) {
      try {
        // ── Fast path: skip const_eval and type_check for gate calls ──
        // For the overwhelmingly common case in QASM 2.0 benchmarks,
        // gate calls have no modifiers, no arguments and all operands are
        // constant expressions. In this case:
        //   - const_eval is a no-op on already-constant expressions
        //   - type_check is a no-op for standard gate calls
        // We can skip both passes entirely and go straight to conversion.
        if (auto gateCall =
                std::dynamic_pointer_cast<GateCallStatement>(statement);
            gateCall != nullptr && gateCall->arguments.empty() &&
            gateCall->modifiers.empty()) {
          // Check if all operands are constant (integer index expressions)
          bool allOperandsConst = true;
          for (const auto& op : gateCall->operands) {
            if (op->expression != nullptr &&
                op->expression->kind() != ExpressionKind::Constant) {
              allOperandsConst = false;
              break;
            }
          }
          if (allOperandsConst) {
            // Skip const_eval and type_check — go straight to conversion.
            visitGateCallStatement(gateCall);
            continue;
          }
        }

        // Normal path: run all three passes
        constEvalPass.processStatement(*statement);
        typeCheckPass.processStatement(*statement);
        statement->accept(this);
      } catch (CompilerError& e) {
        std::cerr << e.toString() << '\n';
        throw;
      }
    }
  }

  void visitVersionDeclaration(
      const std::shared_ptr<VersionDeclaration> versionDeclaration) override {
    if (versionDeclaration->version < 3) {
      openQASM2CompatMode = true;
    }
  }

  void visitDeclarationStatement(const std::shared_ptr<DeclarationStatement>
                                     declarationStatement) override {
    const auto identifier = declarationStatement->identifier;
    if (declarations.find(identifier).has_value()) {
      // TODO: show the location of the previous declaration
      error("Identifier '" + identifier + "' already declared.",
            declarationStatement->debugInfo);
    }

    std::shared_ptr<ResolvedType> const ty =
        std::get<1>(declarationStatement->type);

    if (const auto sizedTy =
            std::dynamic_pointer_cast<DesignatedType<uint64_t>>(ty)) {
      const auto designator = sizedTy->getDesignator();
      switch (sizedTy->type) {
        case QBit:
          qc->addQubitRegister(designator, identifier);
          // Cache the first (and typically only) quantum register for fast
          // operand translation in evaluateGateCall.
          if (cachedRegName_.empty()) {
            const auto& qregs = qc->getQregs();
            auto it = qregs.find(identifier);
            if (it != qregs.end()) {
              cachedRegName_ = identifier;
              cachedRegBase_ = it->second.first;
              cachedRegSize_ = it->second.second;
            }
          }
          break;
        case Bit:
        case Int:
        case Uint:
          qc->addClassicalRegister(designator, identifier);
          break;
        case Float:
          // not adding to qc
          break;
        case Angle:
          error("Angle type is currently not supported.",
                declarationStatement->debugInfo);
      }
    } else {
      error("Only sized types are supported.",
            declarationStatement->debugInfo);
    }
    declarations.emplace(identifier, declarationStatement);

    if (declarationStatement->expression == nullptr) {
      // value is uninitialized
      return;
    }
    if (const auto measureExpression =
            std::dynamic_pointer_cast<MeasureExpression>(
                declarationStatement->expression->expression)) {
      assert(!declarationStatement->isConst &&
             "Type check pass should catch this");
      visitMeasureAssignment(identifier, nullptr, measureExpression,
                             declarationStatement->debugInfo);
      return;
    }
    if (declarationStatement->isConst) {
      // nothing to do
      return;
    }

    error("Only measure statements are supported for initialization.",
          declarationStatement->debugInfo);
  }

  void visitAssignmentStatement(const std::shared_ptr<AssignmentStatement>
                                    assignmentStatement) override {
    const auto identifier = assignmentStatement->identifier->identifier;
    const auto declaration = declarations.find(identifier);
    assert(declaration.has_value() && "Checked by type check pass");
    assert(!declaration->get()->isConst && "Checked by type check pass");

    if (const auto measureExpression =
            std::dynamic_pointer_cast<MeasureExpression>(
                assignmentStatement->expression->expression)) {
      visitMeasureAssignment(identifier, assignmentStatement->indexExpression,
                             measureExpression,
                             assignmentStatement->debugInfo);
      return;
    }

    // In the future, handle classical computation.
    error("Classical computation not supported.",
          assignmentStatement->debugInfo);
  }

  void visitInitialLayout(
      const std::shared_ptr<InitialLayout> layout) override {
    if (!initialLayout.empty()) {
      error("Multiple initial layout specifications found.",
            layout->debugInfo);
    }
    initialLayout = layout->permutation;
  }

  void visitOutputPermutation(
      const std::shared_ptr<OutputPermutation> permutation) override {
    if (!outputPermutation.empty()) {
      error("Multiple output permutation specifications found.",
            permutation->debugInfo);
    }
    outputPermutation = permutation->permutation;
  }

  void visitGateStatement(
      const std::shared_ptr<GateDeclaration> gateStatement) override {
    auto identifier = gateStatement->identifier;
    if (gateStatement->isOpaque) {
      if (getGates().find(identifier) == getGates().end()) {
        // only builtin gates may be declared as opaque.
        error("Unsupported opaque gate '" + identifier + "'.",
              gateStatement->debugInfo);
      }

      return;
    }

    if (openQASM2CompatMode) {
      // we need to check if this is a standard gate
      identifier = parseGateIdentifierCompatMode(identifier).first;
    }

    if (auto prevDeclaration = getGates().find(identifier);
        prevDeclaration != getGates().end()) {
      if (std::dynamic_pointer_cast<StandardGate>(prevDeclaration->second)) {
        // we ignore redeclarations of standard gates
        return;
      }
      // TODO: print location of previous declaration
      error("Gate '" + identifier + "' already declared.",
            gateStatement->debugInfo);
    }

    const auto parameters = gateStatement->parameters;
    const auto qubits = gateStatement->qubits;

    // first we check that all parameters
    std::vector<std::string> parameterIdentifiers{};
    for (const auto& parameter : parameters->identifiers) {
      if (std::find(parameterIdentifiers.begin(), parameterIdentifiers.end(),
                    parameter->identifier) != parameterIdentifiers.end()) {
        error("Parameter '" + parameter->identifier + "' already declared.",
              gateStatement->debugInfo);
      }
      parameterIdentifiers.emplace_back(parameter->identifier);
    }
    std::vector<std::string> qubitIdentifiers{};
    for (const auto& qubit : qubits->identifiers) {
      if (std::find(qubitIdentifiers.begin(), qubitIdentifiers.end(),
                    qubit->identifier) != qubitIdentifiers.end()) {
        error("QBit '" + qubit->identifier + "' already declared.",
              gateStatement->debugInfo);
      }
      qubitIdentifiers.emplace_back(qubit->identifier);
    }

    auto compoundGate = std::make_shared<CompoundGate>(CompoundGate(
        parameterIdentifiers, qubitIdentifiers, gateStatement->statements));

    getMutableGates().emplace(identifier, compoundGate);
  }

  void visitGateCallStatement(
      const std::shared_ptr<GateCallStatement> gateCallStatement) override {
    const auto& qregs = qc->getQregs();

    auto ops = evaluateGateCall(
        gateCallStatement, gateCallStatement->identifier,
        gateCallStatement->arguments, gateCallStatement->operands, qregs);
    if (ops.empty()) {
      return;
    }
    // Fast path: single operation — emplace_back directly, skip vector
    // insert + temporary vector overhead.
    if (ops.size() == 1) {
      qc->emplace_back(std::move(ops[0]));
    } else {
      qc->append(std::move(ops));
    }
  }

  std::vector<std::shared_ptr<qcos::BaseOperation>> evaluateGateCall(
      const std::shared_ptr<GateCallStatement>& gateCallStatement,
      const std::string& identifier,
      const std::vector<std::shared_ptr<Expression>>& parameters,
      std::vector<std::shared_ptr<GateOperand>> targets,
      const qc::QuantumRegisterMap& qregs) {
    std::vector<std::shared_ptr<qcos::BaseOperation>> ops;
    auto iter = getGates().find(identifier);
    std::shared_ptr<Gate> gate;
    size_t implicitControls{0};

    if (iter == getGates().end()) {
      if (identifier == "mcx" || identifier == "mcx_gray" ||
          identifier == "mcx_vchain" || identifier == "mcx_recursive" ||
          identifier == "mcphase") {
        // we create a temp gate definition for these gates
        gate =
            getMcGateDefinition(identifier, gateCallStatement->operands.size(),
                                gateCallStatement->debugInfo);
      } else if (openQASM2CompatMode) {
        auto [updatedIdentifier, nControls] =
            parseGateIdentifierCompatMode(identifier);

        iter = getGates().find(updatedIdentifier);
        if (iter == getGates().end()) {
          error("Usage of unknown gate '" + identifier + "'.",
                gateCallStatement->debugInfo);
        }
        gate = iter->second;
        implicitControls = nControls;
      } else {
        error("Usage of unknown gate '" + identifier + "'.",
              gateCallStatement->debugInfo);
      }
    } else {
      gate = iter->second;
    }

    if (gate->getNParameters() != parameters.size()) {
      error("Gate '" + identifier + "' takes " +
                std::to_string(gate->getNParameters()) + " parameters, but " +
                std::to_string(parameters.size()) + " were supplied.",
            gateCallStatement->debugInfo);
    }

    // here we count the number of controls
    std::vector<std::pair<std::shared_ptr<GateOperand>, bool>> controls{};
    // since standard gates may define a number of control targets, we first
    // need to handle those
    size_t nControls{gate->getNControls() + implicitControls};
    if (targets.size() < nControls) {
      error("Gate '" + identifier + "' takes " + std::to_string(nControls) +
                " controls, but only " + std::to_string(targets.size()) +
                " qubits were supplied.",
            gateCallStatement->debugInfo);
    }

    for (size_t i = 0; i < nControls; ++i) {
      controls.emplace_back(targets[i], true);
    }

    bool invertOperation = false;
    for (const auto& modifier : gateCallStatement->modifiers) {
      if (auto ctrlModifier =
              std::dynamic_pointer_cast<CtrlGateModifier>(modifier);
          ctrlModifier != nullptr) {
        size_t const n = evaluatePositiveConstant(ctrlModifier->expression,
                                                  gateCallStatement->debugInfo,
                                                  /*defaultValue=*/1);
        if (targets.size() < n + nControls) {
          error("Gate '" + identifier + "' takes " +
                    std::to_string(n + nControls) + " controls, but only " +
                    std::to_string(targets.size()) + " were supplied.",
                gateCallStatement->debugInfo);
        }

        for (size_t i = 0; i < n; ++i) {
          controls.emplace_back(targets[nControls + i],
                                ctrlModifier->ctrlType);
        }
        nControls += n;
      } else if (auto invModifier =
                     std::dynamic_pointer_cast<InvGateModifier>(modifier);
                 invModifier != nullptr) {
        // if we have an even number of inv modifiers, they cancel each other
        // out
        invertOperation = !invertOperation;
      } else {
        error("Only ctrl/negctrl/inv modifiers are supported.",
              gateCallStatement->debugInfo);
      }
    }
    targets.erase(targets.begin(),
                  targets.begin() + static_cast<int64_t>(nControls));

    if (gate->getNTargets() != targets.size()) {
      error("Gate '" + identifier + "' takes " +
                std::to_string(gate->getNTargets()) + " targets, but " +
                std::to_string(targets.size()) + " were supplied.",
            gateCallStatement->debugInfo);
    }

    // now evaluate all arguments; we only support const arguments.
    std::vector<qc::fp> evaluatedParameters{};
    for (const auto& param : parameters) {
      auto result = constEvalPass.visit(param);
      if (!result.has_value()) {
        error(
            "Only const expressions are supported as gate parameters, but "
            "found '" +
                param->getName() + "'.",
            gateCallStatement->debugInfo);
      }

      evaluatedParameters.emplace_back(result->toExpr()->asFP());
    }

    size_t broadcastingWidth{1};
    qc::Targets targetBits{};
    std::vector<size_t> targetBroadcastingIndices{};
    size_t i{0};
    for (const auto& target : targets) {
      qc::Targets t{};
      translateGateOperand(target, t, qregs, gateCallStatement->debugInfo);

      targetBits.emplace_back(t[0]);

      if (t.size() > 1) {
        if (broadcastingWidth != 1 && t.size() != broadcastingWidth) {
          error("When broadcasting, all registers must be of the same width.",
                gateCallStatement->debugInfo);
        }
        broadcastingWidth = t.size();

        targetBroadcastingIndices.emplace_back(i);
      }

      i++;
    }

    std::vector<qc::Control> controlBits{};
    std::vector<size_t> controlBroadcastingIndices{};
    i = 0;
    for (const auto& [control, type] : controls) {
      qc::Targets c{};
      translateGateOperand(control, c, qregs, gateCallStatement->debugInfo);

      controlBits.emplace_back(
          c[0], type ? qc::Control::Type::Pos : qc::Control::Type::Neg);

      if (c.size() > 1) {
        if (broadcastingWidth != 1 && c.size() != broadcastingWidth) {
          error("When broadcasting, all registers must be of the same width.",
                gateCallStatement->debugInfo);
        }
        broadcastingWidth = c.size();

        controlBroadcastingIndices.emplace_back(i);
      }

      i++;
    }

    // check if any of the bits are duplicate
    // Optimization: for the overwhelmingly common case of ≤2 total qubits
    // with no control bits (single-qubit gates like h/s/t/x), skip the
    // unordered_set entirely — duplicates are impossible with ≤1 element.
    const size_t totalQubits = controlBits.size() + targetBits.size();
    if (totalQubits > 1) {
      std::unordered_set<qc::QBit> allQubits;
      allQubits.reserve(totalQubits);
      for (const auto& control : controlBits) {
        if (!allQubits.emplace(control.qubit).second) {
          error("Duplicate qubit in control list.",
                gateCallStatement->debugInfo);
        }
      }
      for (const auto& qubit : targetBits) {
        if (!allQubits.emplace(qubit).second) {
          error("Duplicate qubit in target list.",
                gateCallStatement->debugInfo);
        }
      }
    }

    if (broadcastingWidth == 1) {
      // Directly return the result — skip intermediate ops vector.
      return applyQuantumOperation(gate, targetBits, controlBits,
                                   evaluatedParameters, invertOperation,
                                   gateCallStatement->debugInfo);
    }

    // if we are broadcasting, we need to create a compound operation
    for (size_t j = 0; j < broadcastingWidth; ++j) {
      // first we apply the operation
      auto nestedOp = applyQuantumOperation(
          gate, targetBits, controlBits, evaluatedParameters, invertOperation,
          gateCallStatement->debugInfo);
      if (nestedOp.empty()) {
        return {};
      }
      ops.insert(ops.end(), std::make_move_iterator(nestedOp.begin()),
                 std::make_move_iterator(nestedOp.end()));

      // after applying the operation, we update the broadcast bits
      for (auto index : targetBroadcastingIndices) {
        targetBits[index] = qc::QBit{targetBits[index] + 1};
      }
      for (auto index : controlBroadcastingIndices) {
        controlBits[index].qubit = qc::QBit{controlBits[index].qubit + 1};
      }
    }
    return ops;
  }

  static std::shared_ptr<Gate> getMcGateDefinition(
      const std::string& identifier, size_t operandSize,
      const DebugInfo& debugInfo) {
    std::vector<std::string> targetParams{};
    std::vector<std::shared_ptr<GateOperand>> operands;
    size_t nTargets = operandSize;
    if (identifier == "mcx_vchain") {
      nTargets -= (nTargets + 1) / 2 - 2;
    } else if (identifier == "mcx_recursive" && nTargets > 5) {
      nTargets -= 1;
    }
    for (size_t i = 0; i < operandSize; ++i) {
      targetParams.emplace_back("q" + std::to_string(i));
      if (i < nTargets) {
        operands.emplace_back(
            std::make_shared<GateOperand>("q" + std::to_string(i), nullptr));
      }
    }
    const size_t nControls = nTargets - 1;

    std::string nestedGateIdentifier = "x";
    std::vector<std::shared_ptr<Expression>> nestedParameters{};
    std::vector<std::string> nestedParameterNames{};
    if (identifier == "mcphase") {
      nestedGateIdentifier = "p";
      nestedParameters.emplace_back(
          std::make_shared<IdentifierExpression>("x"));
      nestedParameterNames.emplace_back("x");
    }

    // ctrl(nTargets - 1) @ x q0, ..., q(nTargets - 1)
    const auto gateCall = GateCallStatement(
        debugInfo, nestedGateIdentifier,
        std::vector<std::shared_ptr<GateModifier>>{
            std::make_shared<CtrlGateModifier>(
                true, std::make_shared<qasm::Constant>(nControls, false))},
        nestedParameters, operands);
    const auto inner = std::make_shared<GateCallStatement>(gateCall);

    const CompoundGate g{nestedParameterNames, targetParams, {inner}};
    return std::make_shared<CompoundGate>(g);
  }

  std::vector<std::shared_ptr<qcos::BaseOperation>> applyQuantumOperation(
      const std::shared_ptr<Gate>& gate, qc::Targets targetBits,
      std::vector<qc::Control> controlBits,
      std::vector<qc::fp> evaluatedParameters, bool invertOperation,
      const DebugInfo& debugInfo) {
    std::vector<std::shared_ptr<qcos::BaseOperation>> ops;

    if (gate->gateKind == GateKind::Standard) {
      auto* standardGate = static_cast<StandardGate*>(gate.get());

      // Handle invert operation
      if (invertOperation) {
        // TODO: we need to define the inverse of each gate
      }

      qc::OpType op_type = standardGate->info.type;

      // ── Fast path: single-qubit, no-control, no-parameter gates ────
      // For Clifford benchmarks (h, s, sdg, t, tdg, x, y, z), this covers
      // the vast majority of gate calls. Avoids two vector allocations
      // (all_qubits + arg_values) and the reserve/push_back overhead.
      if (controlBits.empty() && targetBits.size() == 1 &&
          evaluatedParameters.empty()) {
        std::vector<int> all_qubits{static_cast<int>(targetBits[0])};
        std::vector<double> no_args;
        std::shared_ptr<qcos::BaseOperation> operation;
        switch (op_type) {
          case qc::otH:
            operation = std::make_shared<qcos::H>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otX:
            operation = std::make_shared<qcos::X>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otY:
            operation = std::make_shared<qcos::Y>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otZ:
            operation = std::make_shared<qcos::Z>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otS:
            operation = std::make_shared<qcos::S>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otSdg:
            operation = std::make_shared<qcos::SDG>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otT:
            operation = std::make_shared<qcos::T>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otTdg:
            operation = std::make_shared<qcos::TDG>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otSX:
            operation = std::make_shared<qcos::SX>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otSXdg:
            operation = std::make_shared<qcos::SXDG>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otI:
            operation = nullptr;
            break;
          default:
            // Fall through to general path for gates not in the fast path
            goto general_path;
        }
        if (operation != nullptr) {
          ops.push_back(std::move(operation));
        }
        return ops;
      }

      // ── Fast path: two-qubit (1 control + 1 target), no-parameter gates ──
      // For cx, cz — the most common two-qubit gates in Clifford benchmarks.
      if (controlBits.size() == 1 && targetBits.size() == 1 &&
          evaluatedParameters.empty()) {
        std::vector<int> all_qubits{
            static_cast<int>(controlBits[0].qubit),
            static_cast<int>(targetBits[0])};
        std::vector<double> no_args;
        std::shared_ptr<qcos::BaseOperation> operation;
        switch (op_type) {
          case qc::otCNOT:
            operation = std::make_shared<qcos::CX>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otCZ:
            operation = std::make_shared<qcos::CZ>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otCH:
            operation = std::make_shared<qcos::CH>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otCY:
            operation = std::make_shared<qcos::CY>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otCS:
            operation = std::make_shared<qcos::CS>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otCSdg:
            operation = std::make_shared<qcos::CSDG>(std::move(all_qubits), std::move(no_args));
            break;
          case qc::otSWAP:
            operation = std::make_shared<qcos::SWAP>(std::move(all_qubits), std::move(no_args));
            break;
          default:
            goto general_path;
        }
        if (operation != nullptr) {
          ops.push_back(std::move(operation));
        }
        return ops;
      }

    general_path:
      // All_qubits: control in front, target in back
      std::vector<int> all_qubits;
      all_qubits.reserve(controlBits.size() + targetBits.size());
      // Add control bits first
      for (const auto& control : controlBits) {
        all_qubits.push_back(static_cast<int>(control.qubit));
      }
      // Add target bits next
      for (const auto& target : targetBits) {
        all_qubits.push_back(static_cast<int>(target));
      }
      // Convert parameter types — qc::fp is double, so a simple move suffices.
      // No intermediate vector allocation needed.
      std::vector<double> arg_values;
      if (!evaluatedParameters.empty()) {
        arg_values.reserve(evaluatedParameters.size());
        for (const auto& param : evaluatedParameters) {
          arg_values.push_back(static_cast<double>(param));
        }
      }

      // Directly construct gate from OpType — skip string intermediate
      std::shared_ptr<qcos::BaseOperation> operation;

      switch (op_type) {
        case qc::otH:
          operation = std::make_shared<qcos::H>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otX:
          operation = std::make_shared<qcos::X>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otY:
          operation = std::make_shared<qcos::Y>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otZ:
          operation = std::make_shared<qcos::Z>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otS:
          operation = std::make_shared<qcos::S>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otSdg:
          operation = std::make_shared<qcos::SDG>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otT:
          operation = std::make_shared<qcos::T>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otTdg:
          operation = std::make_shared<qcos::TDG>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otRX:
          operation = std::make_shared<qcos::RX>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otRY:
          operation = std::make_shared<qcos::RY>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otRZ:
          operation = std::make_shared<qcos::RZ>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otP:
          operation = std::make_shared<qcos::P>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otU2:
          operation = std::make_shared<qcos::U2>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otU3:
          operation = std::make_shared<qcos::U3>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otR:
          operation = std::make_shared<qcos::R>(std::move(all_qubits),
                                                std::move(arg_values));
          break;
        case qc::otSX:
          operation = std::make_shared<qcos::SX>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otSXdg:
          operation = std::make_shared<qcos::SXDG>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::otCNOT:
          operation = std::make_shared<qcos::CX>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCZ:
          operation = std::make_shared<qcos::CZ>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otSWAP:
          operation = std::make_shared<qcos::SWAP>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::ot_iSWAP:
          operation = std::make_shared<qcos::ISWAP>(std::move(all_qubits),
                                                    std::move(arg_values));
          break;
        case qc::otCH:
          operation = std::make_shared<qcos::CH>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCY:
          operation = std::make_shared<qcos::CY>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCS:
          operation = std::make_shared<qcos::CS>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCSdg:
          operation = std::make_shared<qcos::CSDG>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::otCRX:
          operation = std::make_shared<qcos::CRX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otCRY:
          operation = std::make_shared<qcos::CRY>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otCRZ:
          operation = std::make_shared<qcos::CRZ>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otCU:
          operation = std::make_shared<qcos::CU>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCU3:
          operation = std::make_shared<qcos::CU3>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otCP:
          operation = std::make_shared<qcos::CP>(std::move(all_qubits),
                                                 std::move(arg_values));
          break;
        case qc::otCSX:
          operation = std::make_shared<qcos::CSX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otECR:
          operation = std::make_shared<qcos::ECR>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otDCX:
          operation = std::make_shared<qcos::DCX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otRXX:
          operation = std::make_shared<qcos::RXX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otRYY:
          operation = std::make_shared<qcos::RYY>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otRZZ:
          operation = std::make_shared<qcos::RZZ>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otRZX:
          operation = std::make_shared<qcos::RZX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otTOFFOLI:
          operation = std::make_shared<qcos::CCX>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otCSWAP:
          operation = std::make_shared<qcos::CSWAP>(std::move(all_qubits),
                                                    std::move(arg_values));
          break;
        case qc::otRCCX:
          operation = std::make_shared<qcos::RCCX>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::otC3X:
          operation = std::make_shared<qcos::C3X>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otC3SQRTX:
          operation = std::make_shared<qcos::C3SQRTX>(std::move(all_qubits),
                                                      std::move(arg_values));
          break;
        case qc::otRC3X:
          operation = std::make_shared<qcos::RC3X>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::otC4X:
          operation = std::make_shared<qcos::C4X>(std::move(all_qubits),
                                                  std::move(arg_values));
          break;
        case qc::otBarrier:
          operation = std::make_shared<qcos::Sync>(std::move(all_qubits),
                                                   std::move(arg_values));
          break;
        case qc::otMeasure:
          operation = std::make_shared<qcos::Measure>(std::move(all_qubits));
          break;
        case qc::otReset:
          operation = std::make_shared<qcos::Reset>(std::move(all_qubits),
                                                    std::move(arg_values));
          break;
        case qc::otI:
          operation = nullptr;
          break;
        default:
          error("Unsupported standard gate type: " + qc::toString(op_type),
                debugInfo);
          return {};
      }

      if (operation != nullptr) {
        ops.push_back(std::move(operation));
      }
      return ops;
    }
    if (gate->gateKind == GateKind::Compound) {
      auto* compoundGate = static_cast<CompoundGate*>(gate.get());
      constEvalPass.pushEnv();

      for (size_t i = 0; i < compoundGate->parameterNames.size(); ++i) {
        constEvalPass.addConst(compoundGate->parameterNames[i],
                               evaluatedParameters[i]);
      }

      auto nestedQubits = qc::QuantumRegisterMap{};
      size_t index = 0;
      for (const auto& qubitIdentifier : compoundGate->targetNames) {
        auto qubit = std::pair{targetBits[index], 1};

        nestedQubits.emplace(qubitIdentifier, qubit);
        index++;
      }

      for (const auto& nestedGate : compoundGate->body) {
        if (auto barrierStatement =
                std::dynamic_pointer_cast<BarrierStatement>(nestedGate);
            barrierStatement != nullptr) {
          std::vector<int> sync_all_qubits;
          sync_all_qubits.reserve(controlBits.size() + targetBits.size());
          for (const auto& control : controlBits) {
            sync_all_qubits.push_back(static_cast<int>(control.qubit));
          }
          for (const auto& target : targetBits) {
            sync_all_qubits.push_back(static_cast<int>(target));
          }
          ops.push_back(
              std::make_shared<qcos::Sync>(std::move(sync_all_qubits)));
        } else if (auto resetStatement =
                       std::dynamic_pointer_cast<ResetStatement>(nestedGate);
                   resetStatement != nullptr) {
          std::vector<int> reset_all_qubits;
          reset_all_qubits.reserve(controlBits.size() + targetBits.size());
          for (const auto& control : controlBits) {
            reset_all_qubits.push_back(static_cast<int>(control.qubit));
          }
          for (const auto& target : targetBits) {
            reset_all_qubits.push_back(static_cast<int>(target));
          }
          ops.push_back(
              std::make_shared<qcos::Reset>(std::move(reset_all_qubits)));
        } else if (auto gateCallStatement =
                       std::dynamic_pointer_cast<GateCallStatement>(
                           nestedGate);
                   gateCallStatement != nullptr) {
          for (const auto& operand : gateCallStatement->operands) {
            // OpenQASM 3.0 doesn't support indexing of gate arguments.
            if (operand->expression != nullptr &&
                std::find(compoundGate->targetNames.begin(),
                          compoundGate->targetNames.end(),
                          operand->identifier) !=
                    compoundGate->targetNames.end()) {
              error("Gate arguments cannot be indexed within gate body.",
                    debugInfo);
            }
          }

          // Invalidate the register cache before the recursive call —
          // nestedQubits maps gate parameter names (e.g. "a","b","c")
          // to single-qubit slices, which differ from the top-level
          // quantum registers that the cache was populated with.
          cachedRegName_.clear();

          auto nestedOps = evaluateGateCall(
              gateCallStatement, gateCallStatement->identifier,
              gateCallStatement->arguments, gateCallStatement->operands,
              nestedQubits);
          if (nestedOps.empty()) {
            error("Failed to evaluate gate call in compound gate.", debugInfo);
            return {};
          }
          ops.insert(ops.end(), nestedOps.begin(), nestedOps.end());
          // Invalidate cache after recursive call — the recursive call may
          // have cached a gate parameter name that doesn't exist in qregs.
          cachedRegName_.clear();
        } else {
          error("Unhandled quantum statement.", debugInfo);
          return {};
        }
      }
      constEvalPass.popEnv();

      if (ops.empty()) {
        return {};
      } else {
        return ops;
      }
    }

    error("Unknown gate type.", debugInfo);
    return {};
  }

  void visitMeasureAssignment(
      const std::string& identifier,
      const std::shared_ptr<Expression>& indexExpression,
      const std::shared_ptr<MeasureExpression>& measureExpression,
      const DebugInfo& debugInfo) {
    const auto decl = declarations.find(identifier);
    if (!decl.has_value()) {
      error("Usage of unknown identifier '" + identifier + "'.", debugInfo);
    }

    if (!std::get<1>(decl.value()->type)->isBit()) {
      error("Measure expression can only be assigned to a bit register.",
            debugInfo);
    }

    std::vector<qc::QBit> qubits{};
    std::vector<qc::Bit> bits{};
    translateGateOperand(measureExpression->gate, qubits, qc->getQregs(),
                         debugInfo);
    translateBitOperand(identifier, indexExpression, bits, debugInfo);

    if (qubits.size() != bits.size()) {
      error(
          "Classical and quantum register must have the same width in "
          "measure statement. Classical register '" +
              identifier + "' has " + std::to_string(bits.size()) +
              " bits, but quantum register '" +
              measureExpression->gate->identifier + "' has " +
              std::to_string(qubits.size()) + " qubits.",
          debugInfo);
    }

    // Convert qubits (QBit=unsigned int) to BaseOperation's constructor
    // Measure can only take a single target, so create one per qubit
    for (const auto& q : qubits) {
      qc->emplace_back(std::make_shared<qcos::Measure>(
          std::vector<int>{static_cast<int>(q)}));
    }
  }

  void visitBarrierStatement(
      const std::shared_ptr<BarrierStatement> barrierStatement) override {
    std::vector<qc::QBit> qubits{};
    for (const auto& gate : barrierStatement->gates) {
      translateGateOperand(gate, qubits, qc->getQregs(),
                           barrierStatement->debugInfo);
    }
    std::vector<int> allBits;
    allBits.reserve(qubits.size());
    for (const auto& q : qubits) {
      allBits.push_back(static_cast<int>(q));
    }
    qc->emplace_back(std::make_shared<qcos::Sync>(std::move(allBits)));
  }

  void visitResetStatement(
      std::shared_ptr<ResetStatement> resetStatement) override {
    std::vector<qc::QBit> qubits{};
    translateGateOperand(resetStatement->gate, qubits, qc->getQregs(),
                         resetStatement->debugInfo);
    std::vector<int> allBits;
    allBits.reserve(qubits.size());
    for (const auto& q : qubits) {
      allBits.push_back(static_cast<int>(q));
    }
    qc->emplace_back(std::make_shared<qcos::Reset>(std::move(allBits)));
  }

  void visitIfStatement(std::shared_ptr<IfStatement> ifStatement) override {
    // TODO: for now we don't support if statements
    /*
    const auto condition =
        std::dynamic_pointer_cast<BinaryExpression>(ifStatement->condition);
    if (condition == nullptr) {
      error("Condition not supported for if statement.",
            ifStatement->debugInfo);
    }

    const auto comparisonKind = getComparisonKind(condition->op);
    if (!comparisonKind) {
      error("Unsupported comparison operator.", ifStatement->debugInfo);
    }

    const auto lhs =
        std::dynamic_pointer_cast<IdentifierExpression>(condition->lhs);
    const auto rhs = std::dynamic_pointer_cast<qasm::Constant>(condition->rhs);

    if (lhs == nullptr) {
      error("Only classical registers are supported in conditions.",
            ifStatement->debugInfo);
    }
    if (rhs == nullptr) {
      error("Can only compare to constants.", ifStatement->debugInfo);
    }

    const auto creg = qc->getCregs().find(lhs->identifier);
    if (creg == qc->getCregs().end()) {
      error("Usage of unknown or invalid identifier '" + lhs->identifier +
                "' in condition.",
            ifStatement->debugInfo);
    }

    // translate statements in then/else blocks
    if (!ifStatement->thenStatements.empty()) {
      auto thenOps = translateBlockOperations(ifStatement->thenStatements);
      qc->emplace_back(std::make_shared<qc::ClassicControlledOperation>(
          thenOps, creg->second, rhs->getUInt(), *comparisonKind));
    }
    if (!ifStatement->elseStatements.empty()) {
      const auto invertedComparsionKind =
          qc::getInvertedComparsionKind(*comparisonKind);
      auto elseOps = translateBlockOperations(ifStatement->elseStatements);
      qc->emplace_back(std::make_shared<qc::ClassicControlledOperation>(
          elseOps, creg->second, rhs->getUInt(), invertedComparsionKind));
    }*/
  }

  // TODO: Should be redesigned when if-statement support is implemented.
  // The working alternatives are visitBarrierStatement/visitResetStatement
  // which use qcos::create_gate().
  /*
  [[nodiscard]] std::unique_ptr<qc::Operation> translateBlockOperations(
      const std::vector<std::shared_ptr<Statement>>& statements) {
    auto blockOps = std::make_unique<qc::CompoundOperation>();
    for (const auto& statement : statements) {
      auto gateCall = std::dynamic_pointer_cast<GateCallStatement>(statement);
      if (gateCall == nullptr) {
        error("Only quantum statements are supported in blocks.",
              statement->debugInfo);
      }
      const auto& qregs = qc->getQregs();

      auto ops =
          evaluateGateCall(gateCall, gateCall->identifier, gateCall->arguments,
                           gateCall->operands, qregs);
      if (!ops.empty()) {
        for (const auto& op : ops) {
          blockOps->emplace_back(op);
        }
      }
    }

    return blockOps;
  }
  */

  std::pair<std::string, size_t> parseGateIdentifierCompatMode(
      const std::string& identifier) {
    // we need to copy as we modify the string and need to return the original
    // string if we don't find a match.
    std::string gateIdentifier = identifier;
    if (getGates().find(identifier) == getGates().end()) {
      return {identifier, 0};
    }
    size_t implicitControls = 0;
    while (!gateIdentifier.empty() && gateIdentifier[0] == 'c') {
      gateIdentifier = gateIdentifier.substr(1);
      implicitControls++;
    }

    if (getGates().find(gateIdentifier) == getGates().end()) {
      return std::pair{identifier, 0};
    }
    return std::pair{gateIdentifier, implicitControls};
  }
};

void qc::QuantumComputation::importOpenQASM(std::istream& is) {
  using namespace qasm;

  // Estimate operation count from input size for pre-allocation
  auto startPos = is.tellg();
  if (startPos != static_cast<std::streampos>(-1)) {
    is.seekg(0, std::ios::end);
    auto endPos = is.tellg();
    is.seekg(startPos);
    if (endPos > startPos && endPos != static_cast<std::streampos>(-1)) {
      auto estimatedOps = static_cast<size_t>((endPos - startPos) / 20);
      ops.reserve(estimatedOps);
    }
  } else {
    // Fallback: tellg() returns -1 for some stream types (e.g. stringstream),
    // causing reserve to be skipped entirely. Use in_avail() as heuristic.
    std::streambuf* buf = is.rdbuf();
    if (buf) {
      auto avail = buf->in_avail();
      if (avail > 0) {
        ops.reserve(static_cast<size_t>(avail / 20));
      }
    }
  }

  Parser p(&is, /*implicitlyIncludeStdgates=*/false);

  const auto program = p.parseProgram();
  OpenQasmParser parser{this};
  parser.visitProgram(program);
}
