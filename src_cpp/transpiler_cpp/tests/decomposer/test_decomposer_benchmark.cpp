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

#include <gtest/gtest.h>

#include <chrono>
#include <fstream>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <unordered_set>
#include <vector>

#include "circuit/gate_operation.h"
#include "compiler/qasm_to_ir.hpp"
#include "decomposer/decomposer.h"

namespace qcos {

/**
 * @brief Build shared gate-name list from a circuit.
 *
 * @param circuit Input circuit
 * @return Shared gate-name list
 */
std::vector<std::string> BuildGateNameList(
    const std::vector<std::shared_ptr<BaseOperation>>& circuit) {
  std::unordered_set<std::string> gate_set;

  for (const auto& op : circuit) {
    gate_set.insert(op->name);
  }

  return {gate_set.begin(), gate_set.end()};
}

/**
 * @brief Validate all gates belong to target basis.
 */
void ValidateTargetBasis(
    const std::vector<std::shared_ptr<BaseOperation>>& circuit,
    const std::unordered_set<std::string>& target_basis) {
  for (const auto& op : circuit) {
    EXPECT_TRUE(target_basis.count(op->name))
        << "Unexpected gate found after decomposition: " << op->name;
  }
}

/**
 * @brief QASM decomposition integration test fixture.
 */
class QasmDecomposerTest : public ::testing::Test {
 protected:
  /**
   * @brief Benchmark QASM file path.
   */
  const std::string qasm_path_ = std::string(TEST_DATA_DIR) +
                                 "/qasm/2.0/benchmark/"
                                 "random_n100_d50000_clifford_197783.qasm";

  /**
   * @brief Load QASM file into string.
   */
  std::string LoadQasmFile(const std::string& filepath) {
    std::ifstream file(filepath);

    EXPECT_TRUE(file.is_open()) << "Failed to open QASM file: " << filepath;

    std::stringstream buffer;
    buffer << file.rdbuf();

    return buffer.str();
  }
};

/**
 * @brief Test QASM parsing and decomposition pipeline.
 *
 * Workflow:
 *   QASM
 *     -> QCOS IR
 *     -> decomposition
 *     -> target basis validation
 */
TEST_F(QasmDecomposerTest, ParseAndDecomposeBenchmarkCircuit) {
  // ------------------------------------------------
  // Load QASM
  // ------------------------------------------------

  const std::string qasm_str = LoadQasmFile(qasm_path_);

  ASSERT_FALSE(qasm_str.empty());

  // ------------------------------------------------
  // Parse QASM
  // ------------------------------------------------

  auto parse_start = std::chrono::high_resolution_clock::now();

  auto parse_result = qasm_to_ir(qasm_str);

  auto parse_end = std::chrono::high_resolution_clock::now();

  auto operations = parse_result.first;

  const auto parse_duration =
      std::chrono::duration<double, std::milli>(parse_end - parse_start);

  std::cout
      << "\n============================================================\n"
      << "                     QASM Parsing Report\n"
      << "============================================================\n"
      << " Operation count : " << operations.size() << "\n"
      << " Elapsed time    : " << std::fixed << std::setprecision(6)
      << parse_duration.count() / 1000.0 << " s\n"
      << "============================================================\n";

  ASSERT_FALSE(operations.empty());

  // ------------------------------------------------
  // Build decomposition
  // ------------------------------------------------

  Decomposer decomposer;

  const std::vector<std::string> target_basis = {"rx", "ry", "rz", "cx"};

  auto gate_names = BuildGateNameList(operations);

  auto decompose_start = std::chrono::high_resolution_clock::now();

  auto [table, usage] =
      decomposer.get_decompose_rules(gate_names, target_basis);

  auto decomposed = decomposer.apply_decompose_rules(operations, table);

  auto decompose_end = std::chrono::high_resolution_clock::now();

  const auto decompose_duration =
      std::chrono::duration<double>(decompose_end - decompose_start);

  std::cout
      << "\n============================================================\n"
      << "                    Decomposition Report\n"
      << "============================================================\n"
      << " Decomposed gate count : " << decomposed.size() << "\n"
      << " Elapsed time          : " << std::fixed << std::setprecision(6)
      << decompose_duration.count() << " s\n"
      << "============================================================\n";

  ASSERT_FALSE(decomposed.empty());

  // ------------------------------------------------
  // Validate target basis
  // ------------------------------------------------

  ValidateTargetBasis(decomposed,
                      {"rx", "ry", "rz", "cx", "measure", "reset", "sync"});
}

}  // namespace qcos