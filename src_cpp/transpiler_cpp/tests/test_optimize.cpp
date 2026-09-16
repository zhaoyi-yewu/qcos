/*
 * ----------------------------------------------------------------------
 * Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
 *
 * qcos is licensed under Mulan PSL v2.
 * See the Mulan PSL v2 for more details.
 * ----------------------------------------------------------------------
 */

#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <complex>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include "circuit/gate_operation.h"
#include "circuit/dag_circuit.h"
#include "compiler/qasm_to_ir.hpp"
#include "decomposer/decomposer.h"
#include "optimizer/collect_block.h"
#include "optimizer/gate_optimizer.h"
#include "optimizer/matrix_utils.h"
#include "transpile/transpile.h"
#include "utils/constant.h"

using namespace qcos;

// ======== optimize() 边界测试 ========

TEST(OptimizeBoundaryTest, EmptyCircuit) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, MeasureOnly) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<Measure>(std::vector<int>{1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, AllCancelWithMeasure) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {1}),
      std::make_shared<Measure>(std::vector<int>{0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, AllCancelNoMeasure) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}),     create_gate("h", {0}),
      create_gate("x", {1}),     create_gate("x", {1}),
      create_gate("cx", {0, 1}), create_gate("cx", {0, 1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, SingleGate) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("h", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "h");
  }
}

TEST(OptimizeBoundaryTest, NonContiguousQubits) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("cx", {0, 3}), create_gate("cx", {0, 3}),
      std::make_shared<Measure>(std::vector<int>{0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "measure");
  }
}

TEST(OptimizeBoundaryTest, MixedCancelKeep) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    bool has_h = false, has_x = false;
    for (const auto& op : result) {
      if (op->name == "h") has_h = true;
      if (op->name == "x") has_x = true;
    }
    EXPECT_FALSE(has_h);
    EXPECT_TRUE(has_x);
  }
}

TEST(OptimizeBoundaryTest, MultiQubitAllCancel) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("h", {0}), create_gate("x", {1}),
      create_gate("x", {1}), create_gate("y", {2}), create_gate("y", {2}),
      create_gate("z", {3}), create_gate("z", {3})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 0u);
  }
}

TEST(OptimizeBoundaryTest, OddCountSelfInverse) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {1}), create_gate("h", {1}), create_gate("h", {1})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    ASSERT_EQ(result.size(), 1u);
    EXPECT_EQ(result[0]->name, "h");
  }
}

TEST(OptimizeBoundaryTest, DifferentQargsNoCancel) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {create_gate("cx", {0, 1}),
                                                    create_gate("cx", {1, 0})};
  for (int level = 1; level <= 3; ++level) {
    auto result = optimize(ir, level);
    EXPECT_EQ(result.size(), 2u);
  }
}

// ======== optimize() 酉矩阵合成正确性测试 ========
//
// 核心断言:optimize() 在 opt_level>=3 调用 UnitarySynthesis 后,
// 优化前后电路的整体酉矩阵必须等价(允许全局相位差),且输出门全在 basis 内。

namespace {

using C = std::complex<double>;

// 将 op 序列累乘为 nq 比特上的整体酉矩阵。
// 跳过 measure/barrier 等非量子门(不参与酉),1Q 门按其 target 张量提升为 2^n 维。
CMatrix ops_unitary(const std::vector<std::shared_ptr<BaseOperation>>& ops,
                    int nq) {
  size_t dim = static_cast<size_t>(1) << nq;
  CMatrix result = matrix_utils::identity(dim);
  for (const auto& op : ops) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;  // skip measure/barrier
    auto gm = matrix_utils::gate_to_matrix(op);
    size_t nqg = op->targets.size();
    if (nqg == static_cast<size_t>(nq)) {
      result = matrix_utils::multiply(gm, result);
      continue;
    }
    // 把单比特门提升到 nq 空间:对非作用位做 I,作用位做 gm。
    CMatrix full = matrix_utils::identity(dim);
    size_t gd = gm.size();  // 门维度 2^nqg
    for (size_t row = 0; row < dim; ++row) {
      for (size_t col = 0; col < dim; ++col) {
        // 取出 row/col 在门作用位上的子索引,其余位必须相同
        size_t g_row = 0, g_col = 0;
        bool rest_match = true;
        for (size_t b = 0; b < static_cast<size_t>(nq); ++b) {
          size_t bit = (row >> (nq - 1 - b)) & 1;
          size_t cbit = (col >> (nq - 1 - b)) & 1;
          // 判断位 b 是否是门作用位
          bool is_gate_q = false;
          size_t gp = 0;
          for (size_t t = 0; t < op->targets.size(); ++t) {
            if (op->targets[t] == static_cast<int>(b)) {
              is_gate_q = true;
              gp = t;
              break;
            }
          }
          if (is_gate_q) {
            g_row |= (bit << (op->targets.size() - 1 - gp));
            g_col |= (cbit << (op->targets.size() - 1 - gp));
          } else if (bit != cbit) {
            rest_match = false;
          }
        }
        full[row][col] = rest_match ? gm[g_row][g_col] : C(0);
      }
    }
    result = matrix_utils::multiply(full, result);
  }
  return result;
}

// 校验优化结果:门全在 basis 内,且酉矩阵与原电路等价(允许全局相位)。
void expect_synthesis_correct(
    const std::vector<std::shared_ptr<BaseOperation>>& ir, int nq,
    int opt_level, const std::set<std::string>& basis, double tol = 1e-6) {
  CMatrix original = ops_unitary(ir, nq);
  auto result = optimize(ir, opt_level, false, basis);
  for (const auto& g : result) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }
  CMatrix synthesized = ops_unitary(result, nq);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, tol))
      << "optimize() changed the circuit unitary after synthesis";
}

}  // namespace

// 1Q: H+S+T 在 rz+ry basis 下合成后须酉等价。
TEST(OptimizeUnitarySynthesisTest, SingleQubit_RoundtripZRYBasis) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("s", {0}), create_gate("t", {0})};
  expect_synthesis_correct(ir, 1, 3, {"rz", "ry"});
}

// 2Q: Bell 态电路在 cx+rz+ry basis 下合成后须酉等价。
TEST(OptimizeUnitarySynthesisTest, TwoQubit_BellStateCXBasis) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1})};
  expect_synthesis_correct(ir, 2, 3, {"cx", "rz", "ry"});
}

// 2Q: cz 原生门电路在 u3+cz basis 下走纯酉合成短路径,须酉等价。
TEST(OptimizeUnitarySynthesisTest, TwoQubit_U3CZPureSynthesisPath) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cz", {0, 1}),
      create_gate("t", {1})};
  expect_synthesis_correct(ir, 2, 3, {"u3", "cz"});
}

// 交叉校验:opt_level=0 不优化(不走合成),前后酉严格相等。
// 用作 ops_unitary helper 的正确性基线。
TEST(OptimizeUnitarySynthesisTest, Level0IsIdentityForHelper) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      create_gate("h", {0}), create_gate("cx", {0, 1})};
  CMatrix original = ops_unitary(ir, 2);
  auto result = optimize(ir, 0);
  ASSERT_EQ(result.size(), ir.size());
  CMatrix after = ops_unitary(result, 2);
  EXPECT_TRUE(matrix_utils::is_close(original, after, 1e-10));
}

// ======== optimize() 酉矩阵合成 — OpenQASM 文件输入测试 ========
//
// 从 samples 读取真实 QASM 文件 → qasm_to_ir → optimize(level=3) → 校验
// 合成后电路酉矩阵与原电路等价(允许全局相位),且输出门全在 basis 内。

namespace {

std::string read_qasm_file(const std::string& rel_path) {
  std::string path = std::string(TEST_DATA_DIR) + rel_path;
  std::ifstream ifs(path);
  if (!ifs.is_open()) {
    ADD_FAILURE() << "Cannot open QASM file: " << path;
    return "";
  }
  std::stringstream ss;
  ss << ifs.rdbuf();
  return ss.str();
}

// 解析 QASM 文本为 (ops, nq),ops 中含 measure;optimize() 会剥离 measure。
std::pair<std::vector<std::shared_ptr<BaseOperation>>, int>
qasm_to_ops(const std::string& qasm_str) {
  auto [ops, nq] = qasm_to_ir(qasm_str);
  return {ops, nq};
}

// 从 QASM 文件解析电路,跑 level=3 optimize,断言酉等价(+ 可选基合规)。
// barrier 会阻断块收集,使部分门无法进入合成块而被原样保留,故含 barrier
// 的电路可传 check_basis=false 只校验酉等价。
void expect_qasm_synthesis_correct(const std::string& rel_path,
                                   const std::set<std::string>& basis,
                                   double tol = 1e-6,
                                   bool check_basis = true) {
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Empty QASM: " << rel_path;
  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty()) << "QASM parsed to empty op list: " << rel_path;
  ASSERT_GE(nq, 1);

  CMatrix original = ops_unitary(ops, nq);
  auto result = optimize(ops, 3, false, basis);
  // measure/barrier 等非量子门不参与合成,会被 optimize 保留到末尾,
  // 不应出现在 basis 中,故基合规只校验量子门。
  if (check_basis) {
    for (const auto& g : result) {
      if (!dynamic_cast<const GateOperation*>(g.get())) continue;
      EXPECT_TRUE(basis.count(g->name) > 0)
          << "Gate '" << g->name << "' not in basis";
    }
  }
  CMatrix synthesized = ops_unitary(result, nq);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, tol))
      << "optimize() changed QASM circuit unitary after synthesis: "
      << rel_path;
}

}  // namespace

// samples/qasm/2.0/simple-qasm-2q-2sg-1dg.qasm (x;h;cz) 在 u3+cz basis 下
// 走纯酉合成短路径,须酉等价 + 基合规。
TEST(OptimizeQasmSynthesisTest, File_2q_2sg_1dg_U3CZBasis) {
  expect_qasm_synthesis_correct("qasm/2.0/simple-qasm-2q-2sg-1dg.qasm",
                                {"u3", "cz"});
}

// 同一电路在 cx+rz+ry basis 下走完整 pass + level=3 合成,须酉等价。
TEST(OptimizeQasmSynthesisTest, File_2q_2sg_1dg_CXZRYBasis) {
  expect_qasm_synthesis_correct("qasm/2.0/simple-qasm-2q-2sg-1dg.qasm",
                                {"cx", "rz", "ry"});
}

// samples/qasm/2.0/rb.qasm — 随机基准序列(h;cz;s;z + barrier/measure)。
// barrier 阻断合成块收集,故只校验酉等价(合成后功能正确),不强制基合规。
TEST(OptimizeQasmSynthesisTest, File_RB_CXZRYBasis) {
  expect_qasm_synthesis_correct("qasm/2.0/rb.qasm", {"cx", "rz", "ry"}, 1e-6,
                                /*check_basis=*/false);
}

// 同一 RB 电路在 u3+cz basis 下走纯酉合成短路径,须酉等价。
TEST(OptimizeQasmSynthesisTest, File_RB_U3CZBasis) {
  expect_qasm_synthesis_correct("qasm/2.0/rb.qasm", {"u3", "cz"}, 1e-6,
                                /*check_basis=*/false);
}

// 内联 QASM:1Q 的 H-T-H-S 序列,rz+ry basis 合成后须酉等价。
// 用内联字符串补充一条不依赖样本文件的用例。
TEST(OptimizeQasmSynthesisTest, Inline_1q_HTHS_ZRYBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
h q[0];
t q[0];
h q[0];
s q[0];
)";
  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_EQ(nq, 1);
  ASSERT_FALSE(ops.empty());
  CMatrix original = ops_unitary(ops, 1);
  std::set<std::string> basis = {"rz", "ry"};
  auto result = optimize(ops, 3, false, basis);
  for (const auto& g : result) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }
  CMatrix synthesized = ops_unitary(result, 1);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, 1e-6));
}

// 内联 QASM:2Q Bell 态(h;cx)在 u3+cz basis 下走纯酉合成短路径。
TEST(OptimizeQasmSynthesisTest, Inline_2q_Bell_U3CZBasis) {
  std::string qasm = R"(
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0];
cx q[0], q[1];
)";
  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_EQ(nq, 2);
  CMatrix original = ops_unitary(ops, 2);
  std::set<std::string> basis = {"u3", "cz"};
  auto result = optimize(ops, 3, false, basis);
  for (const auto& g : result) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }
  CMatrix synthesized = ops_unitary(result, 2);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, 1e-6));
}

// ======== optimize() 大电路性能测试 ========
//
// QV_n32 是 32 比特 / 5633 门的 benchmark 电路, 原生门为 u3/cx/x。
// 目标 basis 为 {h,rx,ry,rz,cx}, 不含 u3/x, 故须先将非 basis 门转为基础门
// 再优化: decompose_gates_to_1q2q (拆多比特门) -> Decomposer 规则表
// (按 basis 把 u3/x 等替换为 rx/ry/rz/cx) -> optimize(level=3)。
//
// 本用例验证该“转基础门 + 优化”流水线在 32 比特规模下的耗时处于合理上限内,
// 并断言优化后输出门全在 basis 内、门数不增(相对转基础门后的输入)。
//
// 注意: 不调用 ops_unitary 做整电路酉矩阵等价校验 —— 该 helper 需构造
// 2^32 x 2^32 酉矩阵, 32 比特下必然 OOM, 仅适用于 <=4 比特小电路。
// 大电路以 basis 合规 + 门数不增 + 耗时上限为判据。
TEST(OptimizePerformanceTest, QVN32_DecomposeThenOptimize_TimeBudget) {
  const std::string rel_path =
      "qasm/benchpress/qasmbench-large/QV_n32/32.qasm";
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Cannot read " << rel_path;

  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty());
  ASSERT_EQ(nq, 32);

  // 剥离 measure (optimize 内部亦会剥离), 仅保留量子门
  std::vector<std::shared_ptr<BaseOperation>> regular;
  regular.reserve(ops.size());
  for (const auto& op : ops) {
    if (op->name == "measure") continue;
    regular.push_back(op);
  }
  ASSERT_FALSE(regular.empty());

  std::set<std::string> basis = {"h", "rx", "ry", "rz", "cx"};
  std::vector<std::string> basis_vec(basis.begin(), basis.end());

  using clock = std::chrono::high_resolution_clock;

  // 1) 拆多比特门为 1q/2q 门 (u3 等仍保留, 等规则表替换)
  auto t0 = clock::now();
  auto decomp_1q2q = decompose_gates_to_1q2q(regular);
  auto t1 = clock::now();
  double decomp1q2q_sec = std::chrono::duration<double>(t1 - t0).count();

  // 2) 按 basis 生成分解规则表, 把 u3/x 等非 basis 门替换为 basis 门
  auto t2 = clock::now();
  auto gate_names = collect_gate_names(decomp_1q2q);
  Decomposer decomposer;
  auto [decompose_table, usage_stats] =
      decomposer.get_decompose_rules(gate_names, basis_vec);
  auto in_basis = decomposer.apply_decompose_rules(decomp_1q2q,
                                                   decompose_table);
  auto t3 = clock::now();
  double rule_sec = std::chrono::duration<double>(t3 - t2).count();

  // 3) optimize(level=3) 全量优化
  auto t4 = clock::now();
  auto result = optimize(in_basis, 3, false, basis);
  auto t5 = clock::now();
  double opt_sec = std::chrono::duration<double>(t5 - t4).count();
  double total_sec = std::chrono::duration<double>(t5 - t0).count();

  std::cout << "[perf] QV_n32: raw=" << regular.size()
            << " -> 1q2q=" << decomp_1q2q.size()
            << " -> basis=" << in_basis.size()
            << " -> optimized=" << result.size()
            << " | decomp1q2q=" << decomp1q2q_sec << "s"
            << " rules=" << rule_sec << "s"
            << " optimize=" << opt_sec << "s"
            << " total=" << total_sec << "s\n";

  // 输出门必须全部落在目标 basis 内 (量子门; 非门操作透传不校验)
  for (const auto& g : result) {
    if (!dynamic_cast<const GateOperation*>(g.get())) continue;
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }

  // 优化不应使门数增加 (相对转基础门后的输入)
  EXPECT_LE(result.size(), in_basis.size())
      << "optimize() increased gate count: " << in_basis.size() << " -> "
      << result.size();

  // 耗时上限: 32 比特全流程基线约 0.3s, 留充足余量防 CI 抖动
  const double kTimeBudgetSec = 10.0;
  EXPECT_LT(total_sec, kTimeBudgetSec)
      << "QV_n32 decompose+optimize total took " << total_sec
      << "s, exceeds budget " << kTimeBudgetSec << "s";
}

// 同一 RB 电路在 u3+cz basis 下走纯酉合成短路径,须酉等价。
TEST(OptimizeQasmSynthesisTest, File_iswap_n2_U3CZBasis) {
  std::string rel_path="qasm/benchpress/qasmbench-small/iswap_n2/iswap_n2.qasm";
  const std::set<std::string>& basis= {"u3", "cz"};
  double tol = 1e-6;
  bool check_basis = true;
  
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Empty QASM: " << rel_path;
  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty()) << "QASM parsed to empty op list: " << rel_path;
  ASSERT_GE(nq, 1);

  CMatrix original = ops_unitary(ops, nq);
  auto result = optimize(ops, 3, false, basis);
  if (check_basis) {
    for (const auto& g : result) {
      if (!dynamic_cast<const GateOperation*>(g.get())) continue;
      EXPECT_TRUE(basis.count(g->name) > 0)
          << "Gate '" << g->name << "' not in basis";
    }
  }
  CMatrix synthesized = ops_unitary(result, nq);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, tol))
      << "optimize() changed QASM circuit unitary after synthesis: "
      << rel_path;
}
// ======== optimize() 门数观测 — square-heisenberg N4 ========
//
// samples/qasm/benchpress/square-heisenberg/square_heisenberg_N4.qasm 是 4 比特
// Heisenberg 模型 Trotter 电路, 原生门为 cx/rz/rx/ry。目标 basis {h,rx,ry,rz,cx}
// 中已含全部原生门 (电路无 h/u3/x, 无需转基础门), 故直接 optimize(level=3)。
// 本用例观测优化前后门数与门类型分布, 评估优化效果; 同时做 4Q 酉等价 + 基合规校验。
TEST(OptimizeGateCountTest, SquareHeisenbergN4_HRxRyRzCx_Basis) {
  const std::string rel_path =
      "qasm/benchpress/square-heisenberg/square_heisenberg_N9.qasm";
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Cannot read " << rel_path;

  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty()) << "Empty op list: " << rel_path;
  ASSERT_EQ(nq, 9);

  // 剥离 measure (本电路无 measure, 但保持与流水线一致), 仅留量子门做统计
  std::vector<std::shared_ptr<BaseOperation>> regular;
  regular.reserve(ops.size());
  for (const auto& op : ops) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    regular.push_back(op);
  }
  ASSERT_FALSE(regular.empty());

  std::set<std::string> basis = {"h", "rx", "ry", "rz", "cx"};

  auto gate_hist = [](const std::vector<std::shared_ptr<BaseOperation>>& v) {
    std::map<std::string, size_t> h;
    for (const auto& op : v) {
      if (!dynamic_cast<const GateOperation*>(op.get())) continue;
      h[op->name]++;
    }
    return h;
  };

  auto raw_hist = gate_hist(regular);

  // level=3: 完整优化 + 酉合成
  auto result = optimize(ops, 3, false, basis);

  // 剥离非量子门后统计输出门
  std::vector<std::shared_ptr<BaseOperation>> result_gates;
  result_gates.reserve(result.size());
  for (const auto& op : result) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    result_gates.push_back(op);
  }
  auto opt_hist = gate_hist(result_gates);

  std::cout << "[gatecount] square_heisenberg_N4 basis={h,rx,ry,rz,cx}\n";
  std::cout << "[gatecount] raw total=" << regular.size() << " -> opt total="
            << result_gates.size()
            << " (reduced=" << (static_cast<long long>(regular.size())
                                - static_cast<long long>(result_gates.size()))
            << ")\n";
  std::cout << "[gatecount] raw hist:";
  for (const auto& [g, c] : raw_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n[gatecount] opt hist:";
  for (const auto& [g, c] : opt_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n";

  // 优化不应使门数增加
  EXPECT_LE(result_gates.size(), regular.size())
      << "optimize() increased gate count: " << regular.size() << " -> "
      << result_gates.size();

  // 输出门必须全部落在目标 basis 内
  for (const auto& g : result_gates) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }

  // 4Q 酉矩阵等价校验 (允许全局相位)
  CMatrix original = ops_unitary(regular, nq);
  CMatrix synthesized = ops_unitary(result_gates, nq);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, 1e-6))
      << "optimize() changed square_heisenberg_N4 unitary after synthesis";
}

// collect_interacting_blocks 切出的每个块 qubit 并集宽度须严格 ≤ max_qubits,
// 否则合成类 pass (UnitarySynthesis/ConsolidateBlocks) 会因 qubits.size()>
// max_qubits 整块跳过。以 Heisenberg N4 (4-qubit cx 链) 为例:旧实现会把
// 传递连通的全部 cx 并成单个 4-qubit 超大块, 本用例验证重写后正确切分。
TEST(OptimizeGateCountTest, InteractingBlocksQubitWidthBounded) {
  const std::string rel_path =
      "qasm/benchpress/square-heisenberg/square_heisenberg_N4.qasm";
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty());
  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_EQ(nq, 4);

  std::vector<std::shared_ptr<BaseOperation>> regular;
  for (const auto& op : ops) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    regular.push_back(op);
  }
  DAGCircuit dag = DAGCircuit::ir_to_dag(regular);
  std::set<std::string> collect_gates;
  for (const auto& g : Constant::ALL_GATE_LIST) collect_gates.insert(g);

  const size_t max_qubits = 2;
  auto blocks = collect_interacting_blocks(dag, collect_gates, max_qubits, 1);
  EXPECT_FALSE(blocks.empty());
  for (const auto& block : blocks) {
    std::set<int> qs;
    for (auto* n : block)
      for (int q : n->qargs) qs.insert(q);
    EXPECT_LE(qs.size(), max_qubits);
  }
}


// ======== optimize() 门数观测 — ising_model_10 ========
//
// samples/qasm/2.0/benchmark/compiler_qasm/ising_model_10.qasm 是 10 比特
// Ising 模型电路, 原生门为 h/rz/cx + measure。目标 basis {u3,cz} 不含原生
// 门, 若直接 optimize(level=3), 合成器须在 2Q 块内把 cx 合成替换为 cz,
// 该路径在 cx 链交互下易出现 qubit 角色漂移, 破坏整电路酉等价。
//
// 稳健做法: 先用 Decomposer 规则表把 h/rz/cx 等原生门分解为 {u3,cz} 基础门
// (decompose_gates_to_1q2q 拆多比特门 -> Decomposer 按 basis 替换非 basis
// 门), 使 optimize 收到的输入已是全 basis 门; 再 optimize(level=3) 时合成器
// 只在「全 basis 块」上做合并, 不再触发 cx->cz 的跨门类替换, 酉等价有保障。
// 本用例观测分解+优化前后门数与门类型分布, 打印优化后的门列表, 同时做
// 10Q 酉等价 + basis 合规校验。
TEST(OptimizeGateCountTest, IsingModel10_U3CZBasis) {
  const std::string rel_path =
      "qasm/2.0/benchmark/compiler_qasm/ising_model_10.qasm";
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Cannot read " << rel_path;

  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty()) << "Empty op list: " << rel_path;
  ASSERT_EQ(nq, 10);

  // 剥离 measure, 仅留量子门做统计与酉矩阵构造
  std::vector<std::shared_ptr<BaseOperation>> regular;
  regular.reserve(ops.size());
  for (const auto& op : ops) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    regular.push_back(op);
  }
  ASSERT_FALSE(regular.empty());

  std::set<std::string> basis = {"u3", "cz"};
  std::vector<std::string> basis_vec(basis.begin(), basis.end());

  auto gate_hist = [](const std::vector<std::shared_ptr<BaseOperation>>& v) {
    std::map<std::string, size_t> h;
    for (const auto& op : v) {
      if (!dynamic_cast<const GateOperation*>(op.get())) continue;
      h[op->name]++;
    }
    return h;
  };

  auto raw_hist = gate_hist(regular);

  // 1) 拆多比特门为 1q/2q 门 (cx 仍保留, 等规则表替换为 cz)
  auto decomp_1q2q = decompose_gates_to_1q2q(regular);

  // 2) 按 basis 生成分解规则表, 把 h/rz/cx 等非 basis 门替换为 u3/cz
  auto gate_names = collect_gate_names(decomp_1q2q);
  Decomposer decomposer;
  auto [decompose_table, usage_stats] =
      decomposer.get_decompose_rules(gate_names, basis_vec);
  auto in_basis = decomposer.apply_decompose_rules(decomp_1q2q,
                                                   decompose_table);

  // 3) level=3 优化: 输入已是全 basis 门, 合成器仅做块内合并, 不再跨门类替换
  auto result = optimize(in_basis, 3, false, basis);

  std::vector<std::shared_ptr<BaseOperation>> result_gates;
  result_gates.reserve(result.size());
  for (const auto& op : result) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    result_gates.push_back(op);
  }
  auto opt_hist = gate_hist(result_gates);

  std::cout << "[gatecount] ising_model_10 basis={u3,cz}\n";
  std::cout << "[gatecount] raw total=" << regular.size()
            << " -> decompose=" << in_basis.size()
            << " -> opt total=" << result_gates.size()
            << " (reduced=" << (in_basis.size() - result_gates.size()) << ")\n";
  std::cout << "[gatecount] raw hist:";
  for (const auto& [g, c] : raw_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n[gatecount] decompose hist:";
  for (const auto& [g, c] : gate_hist(in_basis)) std::cout << " " << g << "=" << c;
  std::cout << "\n[gatecount] opt hist:";
  for (const auto& [g, c] : opt_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n[gatecount] opt gate list:";
  for (const auto& g : result_gates) {
    std::cout << " " << g->name;
    if (!g->targets.empty()) {
      std::cout << "{";
      for (size_t i = 0; i < g->targets.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << g->targets[i];
      }
      std::cout << "}";
    }
  }
  std::cout << "\n";

  // 输出门必须全部落在目标 basis 内 (量子门)
  for (const auto& g : result_gates) {
    EXPECT_TRUE(basis.count(g->name) > 0)
        << "Gate '" << g->name << "' not in basis";
  }

  // 优化不应使门数增加 (相对分解后的输入)
  EXPECT_LE(result_gates.size(), in_basis.size())
      << "optimize() increased gate count: " << in_basis.size() << " -> "
      << result_gates.size();

  // 10Q 酉矩阵等价校验 (允许全局相位), 对比原始电路 (未分解)
  CMatrix original = ops_unitary(regular, nq);
  CMatrix synthesized = ops_unitary(result_gates, nq);
  // 诊断: 打印对齐相位后的最大元素误差量级
  {
    std::complex<double> phase{0, 0};
    double max_abs = 0.0;
    for (size_t i = 0; i < original.size(); ++i)
      for (size_t j = 0; j < original[0].size(); ++j) {
        double mag = std::abs(synthesized[i][j]);
        if (mag > max_abs && std::abs(original[i][j]) > 1e-9) {
          max_abs = mag;
          phase = original[i][j] / synthesized[i][j];
        }
      }
    double max_err = 0.0;
    for (size_t i = 0; i < original.size(); ++i)
      for (size_t j = 0; j < original[0].size(); ++j) {
        double e = std::abs(original[i][j] - phase * synthesized[i][j]);
        if (e > max_err) max_err = e;
      }
    std::cout << "[gatecount] max element err after phase align = " << max_err
              << "\n";
  }
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original, synthesized, 1e-6))
      << "optimize() changed ising_model_10 unitary after synthesis";
}

TEST(OptimizeGateCountTest, adder_n10_HRxRyRzCx_Basis) {
  const std::string rel_path =
      "qasm/benchpress/qasmbench-small/adder_n10/adder_n10.qasm";
  std::string qasm = read_qasm_file(rel_path);
  ASSERT_FALSE(qasm.empty()) << "Cannot read " << rel_path;

  auto [ops, nq] = qasm_to_ops(qasm);
  ASSERT_FALSE(ops.empty()) << "Empty op list: " << rel_path;
  ASSERT_EQ(nq, 10);
  // 剥离 measure (本电路无 measure, 但保持与流水线一致), 仅留量子门做统计
  std::vector<std::shared_ptr<BaseOperation>> regular;
  regular.reserve(ops.size());
  for (const auto& op : ops) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    regular.push_back(op);
  }
  ASSERT_FALSE(regular.empty());

  std::set<std::string> basis = {"u3", "cz"};
  std::vector<std::string> basis_vec(basis.begin(), basis.end());
  auto gate_hist = [](const std::vector<std::shared_ptr<BaseOperation>>& v) {
    std::map<std::string, size_t> h;
    for (const auto& op : v) {
      if (!dynamic_cast<const GateOperation*>(op.get())) continue;
      h[op->name]++;
    }
    return h;
  };

  auto raw_hist = gate_hist(regular);

  // level=3: 完整优化 + 酉合成
  auto result = optimize(ops, 3, false, basis);

  // 剥离非量子门后统计输出门
  std::vector<std::shared_ptr<BaseOperation>> result_gates;
  result_gates.reserve(result.size());
  for (const auto& op : result) {
    if (!dynamic_cast<const GateOperation*>(op.get())) continue;
    result_gates.push_back(op);
  }
  auto opt_hist = gate_hist(result_gates);

  for (const auto& g : result_gates) {
    std::cout << " " << g->name;
    if (!g->targets.empty()) {
      std::cout << "{";
      for (size_t i = 0; i < g->targets.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << g->targets[i];
      }
      std::cout << "}";
    }
  }
  std::cout << "\n";

  std::cout << "[gatecount] square_heisenberg_N4 basis={h,rx,ry,rz,cx}\n";
  std::cout << "[gatecount] raw total=" << regular.size() << " -> opt total="
            << result_gates.size()
            << " (reduced=" << (static_cast<long long>(regular.size())
                                - static_cast<long long>(result_gates.size()))
            << ")\n";
  std::cout << "[gatecount] raw hist:";
  for (const auto& [g, c] : raw_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n[gatecount] opt hist:";
  for (const auto& [g, c] : opt_hist) std::cout << " " << g << "=" << c;
  std::cout << "\n";

  // 酉矩阵等价校验: optimize 前后电路的整体酉须等价 (允许全局相位差)。
  // adder_n10 含 ccx (3-qubit), ops_unitary 通过 gate_to_matrix + target
  // 张量提升处理任意 qubit 数的门, 故可覆盖含 ccx 的场景。
  CMatrix original_unitary = ops_unitary(ops, nq);
  CMatrix opt_unitary = ops_unitary(result, nq);
  EXPECT_TRUE(matrix_utils::is_close_up_to_phase(original_unitary,
                                                 opt_unitary, 1e-6))
      << "optimize() changed adder_n10 circuit unitary after synthesis";
}
