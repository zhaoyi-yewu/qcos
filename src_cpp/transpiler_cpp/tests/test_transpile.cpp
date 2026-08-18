/*
 * ----------------------------------------------------------------------
 * Copyright? 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

#include <fstream>
#include <memory>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include "circuit/gate_operation.h"
#include "compiler/qasm_to_ir.hpp"
#include "transpile/transpile.h"

using namespace qcos;

namespace {

// Linear chain topology: 0-1-2-3 (bidirectional)
const std::vector<std::pair<int, int>> kLinear4 = {{0, 1}, {1, 0}, {1, 2},
                                                   {2, 1}, {2, 3}, {3, 2}};

// 2x2 grid topology:
//  0 - 1
//  2 - 3
const std::vector<std::pair<int, int>> kGrid4 = {
    {0, 1}, {1, 0}, {0, 2}, {2, 0}, {1, 3}, {3, 1}, {2, 3}, {3, 2}};

// Common basis gates for tests
const std::vector<std::string> kBasisGates = {"cx", "rz", "sx", "x"};

// Hanyuan-style neutral-atom basis: single-qubit gates only, no
// two-qubit gate to decompose SWAP.
const std::vector<std::string> kHanyuanBasis = {"rx", "ry", "rz"};

// Wuyue-Hanyuan basis: single-qubit gates + cz two-qubit gate.
const std::vector<std::string> kWuyueHanyuanBasis = {"rx", "ry", "cz"};

// Read a qasm file under samples/ into a string. Returns an empty
// string if the file cannot be opened (callers should GTEST_SKIP()).
std::string read_qasm_file(const std::string& rel_path) {
  std::string path = std::string(TEST_DATA_DIR) + rel_path;
  std::ifstream file(path);
  if (!file.is_open()) {
    return "";
  }
  std::stringstream buffer;
  buffer << file.rdbuf();
  return buffer.str();
}

// Read a qasm file, skipping the test if the file is missing. This is
// the preferred entry point for sample-file-driven tests so they
// degrade gracefully when a sample is absent.
std::string read_qasm_or_skip(const std::string& rel_path) {
  auto content = read_qasm_file(rel_path);
  if (content.empty()) {
    ADD_FAILURE() << "qasm sample not found: " << rel_path;
  }
  return content;
}

// Assert that every gate in a transpile result is within the allowed
// set (basis gates + the passed-through non-gate operations). Returns
// the number of gates whose name matches a predicate.
void assertGatesInBasis(
    const TranspileResult& result,
    const std::vector<std::string>& basis_gates,
    const std::set<std::string>& extra_allowed = {"measure"}) {
  std::set<std::string> allowed(basis_gates.begin(), basis_gates.end());
  allowed.insert(extra_allowed.begin(), extra_allowed.end());
  for (const auto& op : result.basis_gate_list) {
    EXPECT_TRUE(allowed.count(op->name))
        << "Unexpected gate '" << op->name << "' in result";
  }
}

// Bell state: 2 qubits, H + CNOT
const std::string kBellQasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[2] q;
bit[2] c;
h q[0];
cx q[0], q[1];
c[0] = measure q[0];
c[1] = measure q[1];
)";

// GHZ-4: 4 qubits, H + 3 CNOTs
const std::string kGhz4Qasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[4] q;
bit[4] c;
h q[0];
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
c[0] = measure q[0];
c[1] = measure q[1];
c[2] = measure q[2];
c[3] = measure q[3];
)";

// Simple single-qubit circuit: H + measure
const std::string kSingleQubitQasm = R"(
OPENQASM 3.0;
include "stdgates.inc";
qubit[1] q;
bit[1] c;
h q[0];
c[0] = measure q[0];
)";

NAQpuConfig make_na_qpu_config() {
  // 8 operate-area positions (4 edges) + 36 storage-area positions
  NAQpuConfig cfg;
  cfg.storage_area = {
      "P144", "P145", "P146", "P147", "P148", "P149", "P150", "P151", "P152",
      "P153", "P154", "P155", "P164", "P165", "P166", "P167", "P168", "P169",
      "P170", "P171", "P172", "P173", "P174", "P175", "P184", "P185", "P186",
      "P187", "P188", "P189", "P190", "P191", "P192", "P193", "P194", "P195"};
  cfg.operate_area = {"P100", "P101", "P106", "P107",
                      "P112", "P113", "P118", "P119"};
  cfg.coupler_map = {
      {"R_G0", {"P100", "P101"}},
      {"R_G1", {"P106", "P107"}},
      {"R_G2", {"P112", "P113"}},
      {"R_G3", {"P118", "P119"}},
  };
  cfg.readout_error = {
      {"P144", 1.0}, {"P145", 2.0}, {"P146", 3.0}, {"P147", 4.0},
      {"P148", 5.0}, {"P149", 5.0}, {"P150", 6.0}, {"P151", 7.0},
      {"P152", 6.0}, {"P153", 5.0}, {"P154", 4.0}, {"P155", 3.0},
      {"P164", 1.0}, {"P165", 2.0}, {"P166", 2.0}, {"P167", 3.0},
      {"P168", 4.0}, {"P169", 5.0}, {"P170", 6.0}, {"P171", 7.0},
      {"P172", 1.0}, {"P173", 3.0}, {"P174", 2.0}, {"P175", 4.0},
      {"P184", 5.0}, {"P185", 6.0}, {"P186", 7.0}, {"P187", 8.0},
      {"P188", 5.0}, {"P189", 3.0}, {"P190", 4.0}, {"P191", 3.0},
      {"P192", 4.0}, {"P193", 5.0}, {"P194", 3.0}, {"P195", 2.0},
  };
  return cfg;
}

}  // namespace

// ---------------------------------------------------------------------------
// decompose_gates_to_1q2q
// ---------------------------------------------------------------------------

TEST(TranspileDecompose1q2q, PassesThroughSingleQubitGates) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<H>(std::vector<int>{0}),
      std::make_shared<RZ>(std::vector<int>{0}, std::vector<double>{1.0}),
      std::make_shared<SX>(std::vector<int>{0}),
  };
  auto result = decompose_gates_to_1q2q(ir);
  EXPECT_EQ(result.size(), 3u);
  EXPECT_EQ(result[0]->name, "h");
  EXPECT_EQ(result[1]->name, "rz");
  EXPECT_EQ(result[2]->name, "sx");
}

TEST(TranspileDecompose1q2q, PassesThroughTwoQubitGates) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<CX>(std::vector<int>{0, 1}),
      std::make_shared<CZ>(std::vector<int>{1, 2}),
  };
  auto result = decompose_gates_to_1q2q(ir);
  EXPECT_EQ(result.size(), 2u);
  EXPECT_EQ(result[0]->name, "cx");
  EXPECT_EQ(result[1]->name, "cz");
}

TEST(TranspileDecompose1q2q, PassesThroughMeasureAndBarrier) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<H>(std::vector<int>{0}),
      std::make_shared<Measure>(std::vector<int>{0}),
      std::make_shared<Measure>(std::vector<int>{1}),
  };
  auto result = decompose_gates_to_1q2q(ir);
  // measure is in skip-list, passed through unchanged
  EXPECT_EQ(result.size(), 3u);
  EXPECT_EQ(result[1]->name, "measure");
  EXPECT_EQ(result[2]->name, "measure");
}

TEST(TranspileDecompose1q2q, PassesThroughBarrierAndReset) {
  std::vector<std::shared_ptr<BaseOperation>> ir = {
      std::make_shared<H>(std::vector<int>{0}),
      std::make_shared<BaseOperation>("barrier", std::vector<int>{0, 1},
                                      std::vector<double>{},
                                      OperationType::SYNC),
      std::make_shared<Reset>(std::vector<int>{0}),
  };
  auto result = decompose_gates_to_1q2q(ir);
  // barrier and reset are in skip-list, passed through unchanged
  EXPECT_EQ(result.size(), 3u);
  EXPECT_EQ(result[1]->name, "barrier");
  EXPECT_EQ(result[2]->name, "reset");
}

TEST(TranspileDecompose1q2q, EmptyInput) {
  std::vector<std::shared_ptr<BaseOperation>> ir;
  auto result = decompose_gates_to_1q2q(ir);
  EXPECT_TRUE(result.empty());
}

// ---------------------------------------------------------------------------
// collect_gate_names
// ---------------------------------------------------------------------------

TEST(TranspileCollectNames, UniqueSortedNames) {
  std::vector<std::shared_ptr<BaseOperation>> ops = {
      std::make_shared<H>(std::vector<int>{0}),
      std::make_shared<CX>(std::vector<int>{0, 1}),
      std::make_shared<H>(std::vector<int>{1}),
      std::make_shared<Measure>(std::vector<int>{0}),
  };
  auto names = collect_gate_names(ops);
  // std::set gives sorted unique: cx, h, measure
  ASSERT_EQ(names.size(), 3u);
  EXPECT_EQ(names[0], "cx");
  EXPECT_EQ(names[1], "h");
  EXPECT_EQ(names[2], "measure");
}

TEST(TranspileCollectNames, EmptyInput) {
  std::vector<std::shared_ptr<BaseOperation>> ops;
  auto names = collect_gate_names(ops);
  EXPECT_TRUE(names.empty());
}

// ---------------------------------------------------------------------------
// transpile_from_qasm
// ---------------------------------------------------------------------------

TEST(TranspileFromQasm, BellState) {
  auto result = transpile_from_qasm(kBellQasm, kBasisGates, 1, kLinear4);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
  // All output gates should be in the basis set or be measure
  std::set<std::string> basis_set(kBasisGates.begin(), kBasisGates.end());
  for (const auto& op : result.basis_gate_list) {
    EXPECT_TRUE(basis_set.count(op->name) || op->name == "measure")
        << "Unexpected gate: " << op->name;
  }
}

TEST(TranspileFromQasm, Ghz4Linear) {
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kLinear4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
  // GHZ-4 needs at least 3 two-qubit gates to connect all qubits
  bool has_cx = false;
  for (const auto& op : result.basis_gate_list) {
    if (op->name == "cx") has_cx = true;
  }
  EXPECT_TRUE(has_cx);
}

TEST(TranspileFromQasm, Ghz4Grid) {
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kGrid4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

TEST(TranspileFromQasm, OptLevel0) {
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 0, kLinear4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
  // opt_level=0 means minimal optimization; timing should still be recorded
  EXPECT_GE(result.timings.total_time, 0.0);
}

TEST(TranspileFromQasm, OptLevel3) {
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 3, kLinear4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

TEST(TranspileFromQasm, TimingsConsistency) {
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kLinear4);
  const auto& t = result.timings;
  // decomposed_time = 1q2q + rule + apply
  EXPECT_NEAR(
      t.decomposed_time,
      t.decompose_1q2q_time + t.decompose_rule_time + t.decompose_apply_time,
      1e-9);
  // transpile_time = opt1 + decomposed + mapping + opt2
  EXPECT_NEAR(t.transpile_time,
              t.opt_time1 + t.decomposed_time + t.mapping_time + t.opt_time2,
              1e-9);
  // total_time >= transpile_time (parse is extra)
  EXPECT_GE(t.total_time, t.transpile_time);
  // parse_time should be non-negative
  EXPECT_GE(t.parse_time, 0.0);
}

TEST(TranspileFromQasm, FastModeVsSerial) {
  auto fast = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kLinear4, {}, {},
                                  "vf2_layout", {}, 1, true);
  auto serial = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kLinear4, {},
                                    {}, "vf2_layout", {}, 1, false);
  EXPECT_EQ(fast.num_qubits, serial.num_qubits);
  EXPECT_FALSE(fast.basis_gate_list.empty());
  EXPECT_FALSE(serial.basis_gate_list.empty());
}

TEST(TranspileFromQasm, WithFidelityParams) {
  // Edge fidelities: 0.99 for each edge
  std::vector<double> edge_fids(kLinear4.size(), 0.99);
  // Single-qubit fidelities: 0.99 for each physical qubit
  std::vector<double> sq_fids = {0.99, 0.99, 0.99, 0.99};
  auto result = transpile_from_qasm(kGhz4Qasm, kBasisGates, 1, kLinear4,
                                    edge_fids, sq_fids);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

TEST(TranspileFromQasm, SingleQubitCircuit) {
  auto result =
      transpile_from_qasm(kSingleQubitQasm, kBasisGates, 1, kLinear4);
  EXPECT_EQ(result.num_qubits, 1);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

// ---------------------------------------------------------------------------
// transpile_from_ir
// ---------------------------------------------------------------------------

TEST(TranspileFromIr, BellState) {
  auto [ir_ops, num_qubits] = qasm_to_ir(kBellQasm);
  auto result =
      transpile_from_ir(ir_ops, num_qubits, kBasisGates, 1, kLinear4);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
  // parse_time should be 0 since QASM parsing is skipped
  EXPECT_EQ(result.timings.parse_time, 0.0);
}

TEST(TranspileFromIr, Ghz4) {
  auto [ir_ops, num_qubits] = qasm_to_ir(kGhz4Qasm);
  auto result =
      transpile_from_ir(ir_ops, num_qubits, kBasisGates, 1, kLinear4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
  EXPECT_EQ(result.timings.parse_time, 0.0);
}

TEST(TranspileFromIr, TimingsConsistency) {
  auto [ir_ops, num_qubits] = qasm_to_ir(kGhz4Qasm);
  auto result =
      transpile_from_ir(ir_ops, num_qubits, kBasisGates, 1, kLinear4);
  const auto& t = result.timings;
  EXPECT_EQ(t.parse_time, 0.0);
  EXPECT_NEAR(
      t.decomposed_time,
      t.decompose_1q2q_time + t.decompose_rule_time + t.decompose_apply_time,
      1e-9);
  EXPECT_NEAR(t.transpile_time,
              t.opt_time1 + t.decomposed_time + t.mapping_time + t.opt_time2,
              1e-9);
  EXPECT_GE(t.total_time, t.transpile_time);
}

TEST(TranspileFromIr, OptLevel0) {
  auto [ir_ops, num_qubits] = qasm_to_ir(kGhz4Qasm);
  auto result =
      transpile_from_ir(ir_ops, num_qubits, kBasisGates, 0, kLinear4);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

// ---------------------------------------------------------------------------
// transpile_na
// ---------------------------------------------------------------------------

TEST(TranspileNa, BellState) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kBellQasm, kBasisGates, cfg);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

TEST(TranspileNa, Ghz4) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kGhz4Qasm, kBasisGates, cfg);
  EXPECT_EQ(result.num_qubits, 4);
  EXPECT_FALSE(result.basis_gate_list.empty());
}

TEST(TranspileNa, TimingsConsistency) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kGhz4Qasm, kBasisGates, cfg);
  const auto& t = result.timings;
  EXPECT_NEAR(
      t.decomposed_time,
      t.decompose_1q2q_time + t.decompose_rule_time + t.decompose_apply_time,
      1e-9);
  EXPECT_NEAR(t.transpile_time,
              t.opt_time1 + t.decomposed_time + t.mapping_time + t.opt_time2,
              1e-9);
  EXPECT_GE(t.total_time, t.transpile_time);
  // parse_time should be non-negative (NA also parses QASM)
  EXPECT_GE(t.parse_time, 0.0);
}

// Hanyuan-style neutral-atom driver: single-qubit basis only
// {rx, ry, rz}, no two-qubit gate to decompose SWAP. A single-qubit
// circuit (h + measure) must transpile without raising a
// "Cannot decompose gate(s) ['swap']" error, since NA routing skips
// SWAP insertion (see build_full_decomposition_table).
TEST(TranspileNa, HanyuanSingleQubitBasis) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kSingleQubitQasm, kHanyuanBasis, cfg);
  EXPECT_EQ(result.num_qubits, 1);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kHanyuanBasis);
}

// Hanyuan basis with a two-qubit gate (cz) should still transpile a
// Bell state, and the result may include NA-specific move gates.
TEST(TranspileNa, WuyueHanyuanBasisBell) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kBellQasm, kWuyueHanyuanBasis, cfg);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kWuyueHanyuanBasis, {"measure", "move"});
}

// A purely single-qubit circuit on the hanyuan basis: only rx/ry/rz
// should appear in the output (h decomposes into rotations).
TEST(TranspileNa, HanyuanSingleQubitNoMoveGate) {
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(kSingleQubitQasm, kHanyuanBasis, cfg);
  bool has_move = false;
  for (const auto& op : result.basis_gate_list) {
    if (op->name == "move") has_move = true;
  }
  // Single-qubit circuit needs no atom movement.
  EXPECT_FALSE(has_move);
}

// ---------------------------------------------------------------------------
// transpile_na — file-driven tests (for issue reproduction)
// ---------------------------------------------------------------------------

// Read a single-qubit qasm file (h/x + measure) from samples/ and
// transpile on the hanyuan basis. This is the minimal reproduction for
// the "Cannot decompose gate(s) ['swap']" regression: the hanyuan
// basis lacks a two-qubit gate, so SWAP decomposition must be skipped.
TEST(TranspileNaFromFile, HanyuanSingleQubitBasis) {
  auto qasm = read_qasm_or_skip("qasm/2.0/simple-qasm-1-bit.qasm");
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(qasm, kHanyuanBasis, cfg);
  EXPECT_EQ(result.num_qubits, 1);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kHanyuanBasis);
}

// Read a 2-qubit qasm file from samples/ and transpile on a basis that
// contains a two-qubit gate. The result may include move gates.
TEST(TranspileNaFromFile, TwoQubitBasisWithCz) {
  auto qasm = read_qasm_or_skip("qasm/2.0/simple-qasm.qasm");
  auto cfg = make_na_qpu_config();
  auto result = transpile_na(qasm, kWuyueHanyuanBasis, cfg);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kWuyueHanyuanBasis, {"measure", "move"});
}

// ---------------------------------------------------------------------------
// transpile_from_qasm — file-driven tests (for issue reproduction)
// ---------------------------------------------------------------------------

// Read a GHZ-style qasm file from samples/ and transpile on the
// superconducting basis with a linear chain topology.
TEST(TranspileFromQasmFile, Ghz4OnLinearChain) {
  auto qasm = read_qasm_or_skip("qasm/2.0/w-state.qasm");
  auto result = transpile_from_qasm(qasm, kBasisGates, 1, kLinear4);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kBasisGates);
}

// Same file on a 2x2 grid topology.
TEST(TranspileFromQasmFile, Ghz4OnGrid) {
  auto qasm = read_qasm_or_skip("qasm/2.0/w-state.qasm");
  auto result = transpile_from_qasm(qasm, kBasisGates, 1, kGrid4);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kBasisGates);
}

// A non-trivial file must transpile without error. This guards against
// regressions in the decomposer / router on realistic inputs
// (randomized benchmarking sequence with cz/barrier/s gates).
TEST(TranspileFromQasmFile, RandomizedBenchmarking) {
  auto qasm = read_qasm_or_skip("qasm/2.0/rb.qasm");
  auto result = transpile_from_qasm(qasm, kBasisGates, 1, kGrid4);
  EXPECT_EQ(result.num_qubits, 2);
  EXPECT_FALSE(result.basis_gate_list.empty());
  assertGatesInBasis(result, kBasisGates);
}

// ---------------------------------------------------------------------------
// Error-message tests
// ---------------------------------------------------------------------------

// When the superconducting basis lacks both cx and cz, SWAP cannot be
// decomposed (swap -> cx -> cz). The decomposer must raise a clear
// error that names SWAP and explains the root cause, rather than
// failing on an unrelated single-qubit gate first.
TEST(TranspileDecomposeError, SwapNeedsTwoQubitGate) {
  // Source contains single-qubit gates that DO decompose (x -> rx),
  // plus an implicit SWAP requirement (enable_mapping=true, SC path).
  // The hanyuan basis {rx,ry,rz} lacks a two-qubit gate, so SWAP is
  // the only undecomposable gate.
  auto [ir_ops, num_qubits] = qasm_to_ir(kSingleQubitQasm);
  // Use a single-qubit circuit so routing is trivial; the decomposer
  // is still asked (via transpile_from_ir) to build SWAP rules.
  EXPECT_THROW(
      {
        try {
          transpile_from_ir(ir_ops, num_qubits, kHanyuanBasis, 1,
                            kLinear4);
        } catch (const std::runtime_error& e) {
          EXPECT_NE(std::string(e.what()).find("swap"), std::string::npos)
              << "Error should mention swap: " << e.what();
          EXPECT_NE(std::string(e.what()).find("cx or cz"),
                    std::string::npos)
              << "Error should mention cx or cz: " << e.what();
          throw;
        }
      },
      std::runtime_error);
}
