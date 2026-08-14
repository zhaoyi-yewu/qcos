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

#include <memory>
#include <set>
#include <string>
#include <vector>

#include "optimizer/basis_selector.h"

using namespace qcos;

// ========================================================================
// Basis Selector Tests
// ========================================================================

TEST(BasisSelectorTest, ChooseKakGateCX) {
  std::set<std::string> basis = {"cx", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "cx");
}

TEST(BasisSelectorTest, ChooseKakGateCZ) {
  std::set<std::string> basis = {"cz", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "cz");
}

TEST(BasisSelectorTest, ChooseKakGatePriority) {
  std::set<std::string> basis = {"cx", "cz", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "cx");
}

TEST(BasisSelectorTest, ChooseKakGateNone) {
  std::set<std::string> basis = {"rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(BasisSelectorTest, ChooseEulerBasisZYZ) {
  std::set<std::string> basis = {"rz", "ry"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZYZ");
}

TEST(BasisSelectorTest, ChooseEulerBasisZXZ) {
  std::set<std::string> basis = {"rz", "rx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZXZ");
}

TEST(BasisSelectorTest, ChooseEulerBasisXYX) {
  std::set<std::string> basis = {"rx", "ry"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "XYX");
}

TEST(BasisSelectorTest, ChooseEulerBasisU3) {
  std::set<std::string> basis = {"u3"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "U3");
}

TEST(BasisSelectorTest, ChooseEulerBasisPriority) {
  std::set<std::string> basis = {"rz", "ry", "rx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZYZ");
}

TEST(BasisSelectorTest, ChooseEulerBasisNone) {
  std::set<std::string> basis = {"cx", "cz"};
  auto result = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(BasisSelectorTest, HasEulerBasisZYZ) {
  std::set<std::string> basis = {"rz", "ry"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "ZYZ"));
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "ZXZ"));
}

TEST(BasisSelectorTest, HasEulerBasisUnknown) {
  std::set<std::string> basis = {"rz", "ry"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "UNKNOWN"));
}

TEST(BasisSelectorTest, FindMatchingBases) {
  std::set<std::string> basis = {"rz", "ry", "rx"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}},
      {"ZXZ", {"rz", "rx"}},
      {"U3", {"u3"}}
  };
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 2u);
  bool has_zyz = false, has_zxz = false, has_u3 = false;
  for (const auto& m : matches) {
    if (m == "ZYZ") has_zyz = true;
    if (m == "ZXZ") has_zxz = true;
    if (m == "U3") has_u3 = true;
  }
  EXPECT_TRUE(has_zyz);
  EXPECT_TRUE(has_zxz);
  EXPECT_FALSE(has_u3);
}
