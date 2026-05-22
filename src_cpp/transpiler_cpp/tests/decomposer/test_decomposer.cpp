#include <gtest/gtest.h>
#include <cmath>
#include <unordered_set>

#include "circuit/gate_operation.h"
#include "decomposer/decomposer.h"

using namespace qcos;

// ===== helper =====
void validate_gate_ir(const BaseOperation* op,
                      const std::string& name,
                      const std::vector<int>& targets,
                      int qubit_count,
                      bool is_two_qubit) {
  EXPECT_EQ(op->name, name);
  EXPECT_EQ(op->targets, targets);
  EXPECT_EQ(op->targets.size(), qubit_count);

  if (is_two_qubit) {
    EXPECT_EQ(op->operation_type, OperationType::DOUBLE_QUBIT_OPERATION);
  } else {
    EXPECT_EQ(op->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
  }
}

void validate_ir_equals(const std::vector<std::unique_ptr<BaseOperation>>& a,
                        const std::vector<std::unique_ptr<BaseOperation>>& b) {
  ASSERT_EQ(a.size(), b.size());

  for (size_t i = 0; i < a.size(); ++i) {
    EXPECT_EQ(a[i]->name, b[i]->name);
    EXPECT_EQ(a[i]->targets, b[i]->targets);
    EXPECT_EQ(a[i]->arg_value, b[i]->arg_value);
  }
}

// ===== test =====
TEST(DecomposerCppTest, DecomposeBasisOnly) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(create_gate("rx", {0}, {M_PI}));
  source.push_back(create_gate("ry", {0}, {M_PI}));
  source.push_back(create_gate("rz", {0}, {M_PI}));
  source.push_back(create_gate("cx", {0, 1}, {}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate names =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ⚠️ 关键：source 会被 move
  auto result = d.apply_decompose_rules(source, table);

  // ===== validate =====
  validate_gate_ir(result[0].get(), "rx", {0}, 1, false);
  validate_gate_ir(result[1].get(), "ry", {0}, 1, false);
  validate_gate_ir(result[2].get(), "rz", {0}, 1, false);
  validate_gate_ir(result[3].get(), "cx", {0, 1}, 2, true);

  // ⚠️ source 已经被 move，不能再用
}

TEST(DecomposerCppTest, DecomposeHGate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(create_gate("h", {0}, {}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 2);

  // ===== validate gate 0 =====
  EXPECT_EQ(result[0]->name, "ry");
  EXPECT_EQ(result[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 1 =====
  EXPECT_EQ(result[1]->name, "rx");
  EXPECT_EQ(result[1]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[1]->targets.size(), 1);
  EXPECT_EQ(result[1]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
}

TEST(DecomposerCppTest, DecomposePGate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(create_gate("p", {0}, {M_PI}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 1);

  // ===== validate gate 0 =====
  EXPECT_EQ(result[0]->name, "rz");
  EXPECT_EQ(result[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
}

TEST(DecomposerCppTest, DecomposeRYGate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(create_gate("ry", {0}, {M_PI}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 1);

  // ===== validate gate 0 =====
  EXPECT_EQ(result[0]->name, "ry");
  EXPECT_EQ(result[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
}


TEST(DecomposerCppTest, DecomposeCYGate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(create_gate("cy", {0, 1}, {}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 3);

  // ===== gate 0: rz(-pi/2) on qubit 1 =====
  EXPECT_EQ(result[0]->name, "rz");
  EXPECT_EQ(result[0]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
  ASSERT_EQ(result[0]->arg_value.size(), 1);
  EXPECT_NEAR(result[0]->arg_value[0], -M_PI / 2, 1e-9);

  // ===== gate 1: cx(0,1) =====
  EXPECT_EQ(result[1]->name, "cx");
  EXPECT_EQ(result[1]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(result[1]->targets.size(), 2);
  EXPECT_EQ(result[1]->operation_type, OperationType::DOUBLE_QUBIT_OPERATION);

  // ===== gate 2: rz(pi/2) on qubit 1 =====
  EXPECT_EQ(result[2]->name, "rz");
  EXPECT_EQ(result[2]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[2]->targets.size(), 1);
  EXPECT_EQ(result[2]->operation_type, OperationType::SINGLE_QUBIT_OPERATION);
  ASSERT_EQ(result[2]->arg_value.size(), 1);
  EXPECT_NEAR(result[2]->arg_value[0], M_PI / 2, 1e-9);

}

TEST(DecomposerCppTest, DecomposeCU3Gate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(
      create_gate("cu3", {0, 1}, {M_PI, M_PI, M_PI}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 14);

  // ===== validate gate 0 =====
  EXPECT_EQ(result[0]->name, "rz");
  EXPECT_EQ(result[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 1 =====
  EXPECT_EQ(result[1]->name, "rz");
  EXPECT_EQ(result[1]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[1]->targets.size(), 1);
  EXPECT_EQ(result[1]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 2 =====
  EXPECT_EQ(result[2]->name, "cx");
  EXPECT_EQ(result[2]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(result[2]->targets.size(), 2);
  EXPECT_EQ(result[2]->operation_type,
            OperationType::DOUBLE_QUBIT_OPERATION);

  // ===== validate gate 3 =====
  EXPECT_EQ(result[3]->name, "rz");
  EXPECT_EQ(result[3]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[3]->targets.size(), 1);
  EXPECT_EQ(result[3]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 4 =====
  EXPECT_EQ(result[4]->name, "rx");
  EXPECT_EQ(result[4]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[4]->targets.size(), 1);
  EXPECT_EQ(result[4]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 5 =====
  EXPECT_EQ(result[5]->name, "rz");
  EXPECT_EQ(result[5]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[5]->targets.size(), 1);
  EXPECT_EQ(result[5]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 6 =====
  EXPECT_EQ(result[6]->name, "rx");
  EXPECT_EQ(result[6]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[6]->targets.size(), 1);
  EXPECT_EQ(result[6]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 7 =====
  EXPECT_EQ(result[7]->name, "rz");
  EXPECT_EQ(result[7]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[7]->targets.size(), 1);
  EXPECT_EQ(result[7]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 8 =====
  EXPECT_EQ(result[8]->name, "cx");
  EXPECT_EQ(result[8]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(result[8]->targets.size(), 2);
  EXPECT_EQ(result[8]->operation_type,
            OperationType::DOUBLE_QUBIT_OPERATION);

  // ===== validate gate 9 =====
  EXPECT_EQ(result[9]->name, "rz");
  EXPECT_EQ(result[9]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[9]->targets.size(), 1);
  EXPECT_EQ(result[9]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 10 =====
  EXPECT_EQ(result[10]->name, "rx");
  EXPECT_EQ(result[10]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[10]->targets.size(), 1);
  EXPECT_EQ(result[10]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 11 =====
  EXPECT_EQ(result[11]->name, "rz");
  EXPECT_EQ(result[11]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[11]->targets.size(), 1);
  EXPECT_EQ(result[11]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 12 =====
  EXPECT_EQ(result[12]->name, "rx");
  EXPECT_EQ(result[12]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[12]->targets.size(), 1);
  EXPECT_EQ(result[12]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 13 =====
  EXPECT_EQ(result[13]->name, "rz");
  EXPECT_EQ(result[13]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[13]->targets.size(), 1);
  EXPECT_EQ(result[13]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);
}

TEST(DecomposerCppTest, DecomposeCUGate) {
  Decomposer d;

  // ===== source =====
  std::vector<std::unique_ptr<BaseOperation>> source;
  source.push_back(
      create_gate("cu", {0, 1}, {M_PI, M_PI, M_PI, M_PI}));

  // ===== target =====
  std::vector<std::string> target = {"rx", "ry", "rz", "cx"};

  // ===== gate name list =====
  std::unordered_set<std::string> name_set;
  for (const auto& op : source) {
    name_set.insert(op->name);
  }
  std::vector<std::string> gate_name_list(name_set.begin(), name_set.end());

  // ===== rules =====
  auto [table, usage] = d.get_decompose_rules(gate_name_list, target);

  // ===== apply =====
  auto result = d.apply_decompose_rules(source, table);

  // ===== assert size =====
  ASSERT_EQ(result.size(), 15);

  // ===== validate gate 0 =====
  EXPECT_EQ(result[0]->name, "rz");
  EXPECT_EQ(result[0]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[0]->targets.size(), 1);
  EXPECT_EQ(result[0]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 1 =====
  EXPECT_EQ(result[1]->name, "rz");
  EXPECT_EQ(result[1]->targets, std::vector<int>({0}));
  EXPECT_EQ(result[1]->targets.size(), 1);
  EXPECT_EQ(result[1]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 2 =====
  EXPECT_EQ(result[2]->name, "rz");
  EXPECT_EQ(result[2]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[2]->targets.size(), 1);
  EXPECT_EQ(result[2]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 3 =====
  EXPECT_EQ(result[3]->name, "cx");
  EXPECT_EQ(result[3]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(result[3]->targets.size(), 2);
  EXPECT_EQ(result[3]->operation_type,
            OperationType::DOUBLE_QUBIT_OPERATION);

  // ===== validate gate 4 =====
  EXPECT_EQ(result[4]->name, "rz");
  EXPECT_EQ(result[4]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[4]->targets.size(), 1);
  EXPECT_EQ(result[4]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 5 =====
  EXPECT_EQ(result[5]->name, "rx");
  EXPECT_EQ(result[5]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[5]->targets.size(), 1);
  EXPECT_EQ(result[5]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 6 =====
  EXPECT_EQ(result[6]->name, "rz");
  EXPECT_EQ(result[6]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[6]->targets.size(), 1);
  EXPECT_EQ(result[6]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 7 =====
  EXPECT_EQ(result[7]->name, "rx");
  EXPECT_EQ(result[7]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[7]->targets.size(), 1);
  EXPECT_EQ(result[7]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 8 =====
  EXPECT_EQ(result[8]->name, "rz");
  EXPECT_EQ(result[8]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[8]->targets.size(), 1);
  EXPECT_EQ(result[8]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 9 =====
  EXPECT_EQ(result[9]->name, "cx");
  EXPECT_EQ(result[9]->targets, std::vector<int>({0, 1}));
  EXPECT_EQ(result[9]->targets.size(), 2);
  EXPECT_EQ(result[9]->operation_type,
            OperationType::DOUBLE_QUBIT_OPERATION);

  // ===== validate gate 10 =====
  EXPECT_EQ(result[10]->name, "rz");
  EXPECT_EQ(result[10]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[10]->targets.size(), 1);
  EXPECT_EQ(result[10]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 11 =====
  EXPECT_EQ(result[11]->name, "rx");
  EXPECT_EQ(result[11]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[11]->targets.size(), 1);
  EXPECT_EQ(result[11]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 12 =====
  EXPECT_EQ(result[12]->name, "rz");
  EXPECT_EQ(result[12]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[12]->targets.size(), 1);
  EXPECT_EQ(result[12]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 13 =====
  EXPECT_EQ(result[13]->name, "rx");
  EXPECT_EQ(result[13]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[13]->targets.size(), 1);
  EXPECT_EQ(result[13]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);

  // ===== validate gate 14 =====
  EXPECT_EQ(result[14]->name, "rz");
  EXPECT_EQ(result[14]->targets, std::vector<int>({1}));
  EXPECT_EQ(result[14]->targets.size(), 1);
  EXPECT_EQ(result[14]->operation_type,
            OperationType::SINGLE_QUBIT_OPERATION);
}
