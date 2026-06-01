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

#include <time.h>

#include <iostream>
#include <string>
#include <vector>

#include "compiler/qasm_to_origin_ir.hpp"
#include "gtest/gtest.h"

using namespace std;

#ifndef PRECISION
#define PRECISION 0.000001
#endif  // !PRECISION

class QASMToOperationsTest {
 public:
  std::string qasm_path =
      std::string(TEST_DATA_DIR) +
      R"(qasm/2.0/benchmark/random_n100_d50000_clifford_197783.qasm)";

  static bool test_qasm2operationsfromfile(const std::string& filepath) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
      std::cerr << "Error: Failed to open file: " << filepath << std::endl;
      return false;
    }
    std::stringstream buffer;
    buffer << file.rdbuf();
    file.close();
    std::string qasm_str = buffer.str();
    std::vector<std::shared_ptr<qcos::BaseOperation>> operations =
        std::move(convert_qasm_string_to_qcos_operations(qasm_str).first);
    return true;
  }
};

TEST(QASMToOperations, StandardGate) {
  QASMToOperationsTest test_;

  bool test_actual = true;
  try {
    test_actual =
        test_actual &&
        QASMToOperationsTest::test_qasm2operationsfromfile(test_.qasm_path);
  }

  catch (const std::exception& e) {
    std::cout << "Got a exception: " << e.what() << std::endl;
  } catch (...) {
    std::cout << "Got an unknow exception: " << std::endl;
  }

  ASSERT_TRUE(test_actual);
}
