#include <cmath>
#include <memory>
#include <unordered_set>
#include <vector>

#include <gtest/gtest.h>

#include "circuit/gate_operation.h"
#include "decomposer/decomposer.h"

using namespace qcos;

/* ============================================================
 * Helper Utilities
 * ============================================================ */

/**
 * @brief Validate basic gate IR properties.
 *
 * Checks:
 * - gate name
 * - target qubits
 * - qubit count
 * - operation type
 *
 * @param op Gate operation pointer
 * @param expected_name Expected gate name
 * @param expected_targets Expected target qubits
 * @param expected_qubit_count Expected qubit count
 * @param expect_two_qubit Whether the gate is a two-qubit gate
 */
void ValidateGateIR(
    const BaseOperation* op,
    const std::string& expected_name,
    const std::vector<int>& expected_targets,
    int expected_qubit_count,
    bool expect_two_qubit) {

  ASSERT_NE(op, nullptr);

  EXPECT_EQ(op->name, expected_name);
  EXPECT_EQ(op->targets, expected_targets);
  EXPECT_EQ(op->targets.size(), expected_qubit_count);

  if (expect_two_qubit) {
    EXPECT_EQ(
        op->operation_type,
        OperationType::DOUBLE_QUBIT_OPERATION);
  } else {
    EXPECT_EQ(
        op->operation_type,
        OperationType::SINGLE_QUBIT_OPERATION);
  }
}

/**
 * @brief Compare two IR operation sequences.
 *
 * Verifies:
 * - gate names
 * - target qubits
 * - gate parameters
 *
 * @param lhs First IR sequence
 * @param rhs Second IR sequence
 */
void ValidateIREquals(
    const std::vector<std::unique_ptr<BaseOperation>>& lhs,
    const std::vector<std::unique_ptr<BaseOperation>>& rhs) {

  ASSERT_EQ(lhs.size(), rhs.size());

  for (size_t i = 0; i < lhs.size(); ++i) {

    EXPECT_EQ(lhs[i]->name, rhs[i]->name);
    EXPECT_EQ(lhs[i]->targets, rhs[i]->targets);
    EXPECT_EQ(lhs[i]->arg_value, rhs[i]->arg_value);
  }
}

/**
 * @brief Build unique gate-name list from a circuit.
 *
 * Used to generate the source gate set
 * required by the decomposer.
 *
 * @param circuit Input circuit
 * @return Unique gate name list
 */
std::vector<std::string> BuildGateNameList(
    const std::vector<std::unique_ptr<BaseOperation>>& circuit) {

  std::unordered_set<std::string> name_set;

  for (const auto& op : circuit) {
    name_set.insert(op->name);
  }

  return {
      name_set.begin(),
      name_set.end()
  };
}

/* ============================================================
 * Tests
 * ============================================================ */

/**
 * @brief Test identity decomposition.
 *
 * Verifies that primitive basis gates remain unchanged
 * when the target basis already contains them.
 */
TEST(DecomposerCppTest, DecomposeBasisOnly) {

  Decomposer decomposer;

  // ------------------------------------------------
  // Build source circuit
  // ------------------------------------------------

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate("rx", {0}, {M_PI}));

  source.push_back(
      create_gate("ry", {0}, {M_PI}));

  source.push_back(
      create_gate("rz", {0}, {M_PI}));

  source.push_back(
      create_gate("cx", {0, 1}, {}));

  // ------------------------------------------------
  // Target basis
  // ------------------------------------------------

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  // ------------------------------------------------
  // Build decomposition rules
  // ------------------------------------------------

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  // ------------------------------------------------
  // Apply decomposition
  // ------------------------------------------------

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 4);

  // ------------------------------------------------
  // Validate result
  // ------------------------------------------------

  ValidateGateIR(
      result[0].get(),
      "rx",
      {0},
      1,
      false);

  ValidateGateIR(
      result[1].get(),
      "ry",
      {0},
      1,
      false);

  ValidateGateIR(
      result[2].get(),
      "rz",
      {0},
      1,
      false);

  ValidateGateIR(
      result[3].get(),
      "cx",
      {0, 1},
      2,
      true);
}

/**
 * @brief Test H gate decomposition.
 *
 * Expected:
 *   h -> ry + rx
 */
TEST(DecomposerCppTest, DecomposeHGate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate("h", {0}, {}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 2);

  ValidateGateIR(
      result[0].get(),
      "ry",
      {0},
      1,
      false);

  ValidateGateIR(
      result[1].get(),
      "rx",
      {0},
      1,
      false);
}

/**
 * @brief Test phase gate decomposition.
 *
 * Expected:
 *   p(theta) -> rz(theta)
 */
TEST(DecomposerCppTest, DecomposePGate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate("p", {0}, {M_PI}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 1);

  ValidateGateIR(
      result[0].get(),
      "rz",
      {0},
      1,
      false);
}

/**
 * @brief Test identity preservation for RY gate.
 *
 * Since RY already belongs to the target basis,
 * decomposition should not modify it.
 */
TEST(DecomposerCppTest, DecomposeRYGate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate("ry", {0}, {M_PI}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 1);

  ValidateGateIR(
      result[0].get(),
      "ry",
      {0},
      1,
      false);
}

/**
 * @brief Test CY gate decomposition.
 *
 * Expected:
 *   cy ->
 *     rz(-pi/2)
 *     cx
 *     rz(pi/2)
 */
TEST(DecomposerCppTest, DecomposeCYGate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate("cy", {0, 1}, {}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 3);

  // rz(-pi/2)
  ValidateGateIR(
      result[0].get(),
      "rz",
      {1},
      1,
      false);

  ASSERT_EQ(result[0]->arg_value.size(), 1);

  EXPECT_NEAR(
      result[0]->arg_value[0],
      -M_PI / 2,
      1e-9);

  // cx
  ValidateGateIR(
      result[1].get(),
      "cx",
      {0, 1},
      2,
      true);

  // rz(pi/2)
  ValidateGateIR(
      result[2].get(),
      "rz",
      {1},
      1,
      false);

  ASSERT_EQ(result[2]->arg_value.size(), 1);

  EXPECT_NEAR(
      result[2]->arg_value[0],
      M_PI / 2,
      1e-9);
}

/**
 * @brief Test CU3 gate decomposition.
 *
 * This test validates:
 * - recursive decomposition
 * - multi-level expansion
 * - parameter propagation
 * - target basis correctness
 */
TEST(DecomposerCppTest, DecomposeCU3Gate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate(
          "cu3",
          {0, 1},
          {M_PI, M_PI, M_PI}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 14);

  // ------------------------------------------------
  // Validate gate sequence structure
  // ------------------------------------------------

  const std::vector<std::string> expected_names = {
      "rz", "rz", "cx", "rz",
      "rx", "rz", "rx", "rz",
      "cx", "rz", "rx", "rz",
      "rx", "rz"
  };

  for (size_t i = 0; i < expected_names.size(); ++i) {

    EXPECT_EQ(
        result[i]->name,
        expected_names[i]);
  }

  // Validate CX locations
  ValidateGateIR(
      result[2].get(),
      "cx",
      {0, 1},
      2,
      true);

  ValidateGateIR(
      result[8].get(),
      "cx",
      {0, 1},
      2,
      true);
}

/**
 * @brief Test controlled-U gate decomposition.
 *
 * Verifies:
 * - recursive expansion correctness
 * - decomposition table correctness
 * - generated target basis consistency
 */
TEST(DecomposerCppTest, DecomposeCUGate) {

  Decomposer decomposer;

  std::vector<std::unique_ptr<BaseOperation>> source;

  source.push_back(
      create_gate(
          "cu",
          {0, 1},
          {M_PI, M_PI, M_PI, M_PI}));

  std::vector<std::string> target = {
      "rx",
      "ry",
      "rz",
      "cx"
  };

  auto gate_names = BuildGateNameList(source);

  auto [table, usage] =
      decomposer.get_decompose_rules(
          gate_names,
          target);

  auto result =
      decomposer.apply_decompose_rules(
          source,
          table);

  ASSERT_EQ(result.size(), 15);

  // ------------------------------------------------
  // Expected gate structure
  // ------------------------------------------------

  const std::vector<std::string> expected_names = {
      "rz", "rz", "rz", "cx",
      "rz", "rx", "rz", "rx",
      "rz", "cx", "rz", "rx",
      "rz", "rx", "rz"
  };

  for (size_t i = 0; i < expected_names.size(); ++i) {

    EXPECT_EQ(
        result[i]->name,
        expected_names[i]);
  }

  // Validate CX locations
  ValidateGateIR(
      result[3].get(),
      "cx",
      {0, 1},
      2,
      true);

  ValidateGateIR(
      result[9].get(),
      "cx",
      {0, 1},
      2,
      true);
}