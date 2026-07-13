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
 *     WITHOUT WARRANTIES OF ANY KIND,
 * EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
 * MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
 * See the Mulan PSL v2 for the more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

#include "circuit/dag_circuit.h"
#include "circuit/gate_operation.h"
#include "compiler/qasm_to_ir.hpp"
#include "optimizer/gate_optimizer.h"

using namespace qcos;

// ======== ir_layers 单元测试 ========

TEST(IrLayersTest, SequentialOpsOnSameQubit) {
  // 同一 qubit 上的操作应依次递增层号
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {0}),
      create_gate("h", {0}),
  };
  auto layers = ir_layers(ir);
  EXPECT_EQ(layers[0], 1);
  EXPECT_EQ(layers[1], 2);
  EXPECT_EQ(layers[2], 3);
}

TEST(IrLayersTest, ParallelOpsOnDifferentQubits) {
  // 不同 qubit 上的操作层号应为 1（无前驱）
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {1}),
  };
  auto layers = ir_layers(ir);
  EXPECT_EQ(layers[0], 1);
  EXPECT_EQ(layers[1], 1);
}

TEST(IrLayersTest, TwoQubitGateDependsOnBothQubits) {
  // CX(0,1) 的层号 = max(qubit0层号, qubit1层号) + 1
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {1}),
      create_gate("cx", {0, 1}),
  };
  auto layers = ir_layers(ir);
  EXPECT_EQ(layers[0], 1);  // H(0)
  EXPECT_EQ(layers[1], 1);  // X(1)
  EXPECT_EQ(layers[2], 2);  // CX(0,1) 依赖两个 qubit
}

TEST(IrLayersTest, EmptyIR) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  auto layers = ir_layers(ir);
  EXPECT_TRUE(layers.empty());
}

// ======== split_ir_by_layers 单元测试 ========

TEST(SplitIrByLayersTest, SingleChunk) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("cx", {0, 1}),
  };
  auto layers = ir_layers(ir);
  auto segments = split_ir_by_layers(ir, layers, 1);
  ASSERT_EQ(segments.size(), 1u);
  EXPECT_EQ(segments[0].size(), 2u);
}

TEST(SplitIrByLayersTest, TwoChunks) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {1}),
      create_gate("cx", {0, 1}),
      create_gate("h", {0}),
  };
  auto layers = ir_layers(ir);
  auto segments = split_ir_by_layers(ir, layers, 2);
  ASSERT_EQ(segments.size(), 2u);
  // chunk0: H(0), X(1), CX(0,1) = 3 ops; chunk1: H(0) = 1 op
  EXPECT_EQ(segments[0].size(), 3u);
  EXPECT_EQ(segments[1].size(), 1u);
}

TEST(SplitIrByLayersTest, TotalOpsPreserved) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int idx = 0; idx < 500; ++idx) {
    ir.push_back(create_gate("h", {0}));
    ir.push_back(create_gate("x", {1}));
    ir.push_back(create_gate("cx", {0, 1}));
  }

  auto layers = ir_layers(ir);
  for (int num_chunks : {2, 4, 8}) {
    auto segments = split_ir_by_layers(ir, layers, num_chunks);
    size_t total = 0;
    for (auto& seg : segments) total += seg.size();
    EXPECT_EQ(total, ir.size());
  }
}

TEST(SplitIrByLayersTest, EmptySegmentsRemoved) {
  // 所有操作在同一层，请求 4 个 chunk → 只 1 个非空段
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("x", {1}),
  };
  auto layers = ir_layers(ir);
  auto segments = split_ir_by_layers(ir, layers, 4);
  // 两操作都在层 1，只能分到 1 个段
  ASSERT_EQ(segments.size(), 1u);
  EXPECT_EQ(segments[0].size(), 2u);
}

// ======== optimize() 并行正确性测试 ========

static void expect_same_ir(
    const std::vector<std::shared_ptr<BaseOperation>>& a,
    const std::vector<std::shared_ptr<BaseOperation>>& b) {
  ASSERT_EQ(a.size(), b.size());
  for (size_t idx = 0; idx < a.size(); ++idx) {
    EXPECT_EQ(a[idx]->name, b[idx]->name) << "at index " << idx;
    EXPECT_EQ(a[idx]->targets, b[idx]->targets) << "at index " << idx;
  }
}

TEST(OptimizeParallelTest, SmallCircuitHHCX) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("h", {0}),
      create_gate("cx", {0, 1}),
  };

  auto serial = optimize(ir, 1, false);
  auto parallel = optimize(ir, 1, false, std::nullopt, 2);

  EXPECT_LT(parallel.size(), ir.size());
  expect_same_ir(serial, parallel);
}

TEST(OptimizeParallelTest, SerialParallelSameResult) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int idx = 0; idx < 2500; ++idx) {
    ir.push_back(create_gate("h", {0}));
    ir.push_back(create_gate("h", {0}));
  }

  auto serial = optimize(ir, 1, false);
  auto parallel = optimize(ir, 1, false, std::nullopt, 2);

  EXPECT_TRUE(serial.empty());
  EXPECT_TRUE(parallel.empty());
}

TEST(OptimizeParallelTest, CancellationAcrossQubits) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int idx = 0; idx < 1500; ++idx) {
    ir.push_back(create_gate("x", {0}));
    ir.push_back(create_gate("x", {0}));
    ir.push_back(create_gate("cx", {0, 1}));
    ir.push_back(create_gate("cx", {0, 1}));
  }

  auto serial = optimize(ir, 1, false);
  auto parallel = optimize(ir, 1, false, std::nullopt, 2);

  EXPECT_TRUE(serial.empty());
  EXPECT_TRUE(parallel.empty());
}

TEST(OptimizeParallelTest, NoOptimizationLevel0) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),
      create_gate("h", {0}),
  };

  auto result = optimize(ir, 0, false, std::nullopt, 2);
  EXPECT_EQ(result.size(), ir.size());
}

TEST(OptimizeParallelTest, NumThreadsZeroUsesHardwareConcurrency) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  for (int idx = 0; idx < 2500; ++idx) {
    ir.push_back(create_gate("h", {0}));
    ir.push_back(create_gate("h", {0}));
  }

  auto result = optimize(ir, 1, false, std::nullopt, 0);
  EXPECT_TRUE(result.empty());
}

TEST(OptimizeParallelTest, SmallQasmCorrectness) {
  std::string qasm_str =
      "OPENQASM 2.0;\n"
      "include \"qelib1.inc\";\n"
      "qreg q[3];\n"
      "h q[0];\n"
      "h q[0];\n"
      "cx q[0],q[1];\n"
      "cx q[0],q[1];\n"
      "x q[2];\n"
      "x q[2];\n"
      "s q[0];\n"
      "sdg q[0];\n";

  auto [ir, num_qubits] = qasm_to_ir(qasm_str);
  ASSERT_GT(ir.size(), 0u);

  auto serial = optimize(ir, 1, false);
  auto parallel = optimize(ir, 1, false, std::nullopt, 2);

  EXPECT_TRUE(serial.empty());
  EXPECT_TRUE(parallel.empty());
}

// ======== 并行性能与优化效果测试（bwt_n21） ========

TEST(OptimizeParallelTest, ParallelPerformanceBwtN21) {
  // qasm/benchpress/qasmbench-medium/bwt_n21/bwt_n21_transpiled.qasm
  std::string qasm_path = std::string(TEST_DATA_DIR) +
                          "qasm/benchpress/qasmbench-large/multiplier_n75/"
                          "multiplier_n75_transpiled.qasm";
  std::ifstream ifs(qasm_path);
  if (!ifs) GTEST_SKIP() << "QASM file not found: " << qasm_path;

  std::ostringstream oss;
  oss << ifs.rdbuf();
  auto [ir, num_qubits] = qasm_to_ir(oss.str());
  ASSERT_GT(ir.size(), 0u);

  for (int opt_level = 1; opt_level <= 3; ++opt_level) {
    // 串行
    auto t0 = std::chrono::steady_clock::now();
    auto serial = optimize(ir, opt_level);
    auto t1 = std::chrono::steady_clock::now();
    double serial_ms =
        std::chrono::duration<double, std::milli>(t1 - t0).count();

    auto t2 = std::chrono::steady_clock::now();
    auto parallel = optimize(ir, opt_level, false, std::nullopt, 0);
    auto t3 = std::chrono::steady_clock::now();
    double parallel_ms =
        std::chrono::duration<double, std::milli>(t3 - t2).count();

    double speedup = serial_ms / parallel_ms;

    std::cout << "[bwt_n21] Level " << opt_level << " | serial=" << serial_ms
              << "ms (" << serial.size() << " gates)"
              << " | parallel=" << parallel_ms << "ms (" << parallel.size()
              << " gates)"
              << " | speedup=" << speedup << "x" << std::endl;
  }
}
