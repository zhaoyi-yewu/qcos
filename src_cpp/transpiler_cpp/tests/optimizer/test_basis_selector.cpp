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

// ========================================================================
// KAK Gate Priority — Full Chain Coverage
//
// choose_kak_gate 按固定优先级返回: cx > cz > iswap > ecr > rxx > rzx。
// 验证每个 KAK 门单独存在时的选择，以及相邻优先级的取舍。
// ========================================================================

TEST(KakGatePriorityTest, ISwapAlone) {
  std::set<std::string> basis = {"iswap", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "iswap");
}

TEST(KakGatePriorityTest, ECRAlone) {
  std::set<std::string> basis = {"ecr", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ecr");
}

TEST(KakGatePriorityTest, RXXAlone) {
  std::set<std::string> basis = {"rxx", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "rxx");
}

TEST(KakGatePriorityTest, RZXAlone) {
  std::set<std::string> basis = {"rzx", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "rzx");
}

TEST(KakGatePriorityTest, CZOverISwap) {
  std::set<std::string> basis = {"cz", "iswap", "rz"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "cz");
}

TEST(KakGatePriorityTest, ISwapOverECR) {
  std::set<std::string> basis = {"iswap", "ecr", "rz"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "iswap");
}

TEST(KakGatePriorityTest, ECROverRXX) {
  std::set<std::string> basis = {"ecr", "rxx", "rz"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ecr");
}

TEST(KakGatePriorityTest, RXXOverRZX) {
  std::set<std::string> basis = {"rxx", "rzx", "rz"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "rxx");
}

TEST(KakGatePriorityTest, AllKakGatesPicksCX) {
  // All six KAK gates present => cx (highest priority).
  std::set<std::string> basis = {"cx", "cz", "iswap", "ecr", "rxx", "rzx"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "cx");
}

TEST(KakGatePriorityTest, LowestPriorityOnly) {
  // Only the lowest-priority KAK gate (rzx) is present.
  std::set<std::string> basis = {"rzx"};
  auto result = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "rzx");
}

TEST(KakGatePriorityTest, NoKakGateWithTwoQubitNonKak) {
  // swap is a 2Q gate but NOT in the KAK list => nullopt.
  std::set<std::string> basis = {"swap", "rz", "ry"};
  auto result = basis_selector::choose_kak_gate(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(KakGatePriorityTest, EmptyBasisReturnsNullopt) {
  std::set<std::string> basis = {};
  auto result = basis_selector::choose_kak_gate(basis);
  EXPECT_FALSE(result.has_value());
}

// ========================================================================
// Euler Basis Selection — Full Configuration Coverage
//
// choose_euler_basis 有 8 种配置: ZYZ > ZXZ > XYX > U3 > U > PSX > ZSX > RR。
// 验证每个基单独存在时的选择，以及优先级回退（缺门时回退到下一可用基）。
// ========================================================================

TEST(EulerBasisSelectionTest, UAlone) {
  std::set<std::string> basis = {"u"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "U");
}

TEST(EulerBasisSelectionTest, PSXAlone) {
  std::set<std::string> basis = {"p", "sx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "PSX");
}

TEST(EulerBasisSelectionTest, ZSXAlone) {
  std::set<std::string> basis = {"rz", "sx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZSX");
}

TEST(EulerBasisSelectionTest, RRAlone) {
  std::set<std::string> basis = {"r"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "RR");
}

TEST(EulerBasisSelectionTest, U3OverU) {
  // U3 has higher priority than U.
  std::set<std::string> basis = {"u3", "u"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "U3");
}

TEST(EulerBasisSelectionTest, UOverPSX) {
  std::set<std::string> basis = {"u", "p", "sx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "U");
}

TEST(EulerBasisSelectionTest, PSXOverZSX) {
  std::set<std::string> basis = {"p", "sx", "rz"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "PSX");
}

TEST(EulerBasisSelectionTest, ZSXOverRR) {
  std::set<std::string> basis = {"rz", "sx", "r"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZSX");
}

TEST(EulerBasisSelectionTest, XYXOverU3) {
  // XYX has higher priority than U3.
  std::set<std::string> basis = {"rx", "ry", "u3"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "XYX");
}

TEST(EulerBasisSelectionTest, ZYZFallbackWhenRyMissing) {
  // basis has rz but not ry => ZYZ unavailable; falls back to ZXZ if rx present.
  std::set<std::string> basis = {"rz", "rx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZXZ");
}

TEST(EulerBasisSelectionTest, ZSXFallbackWhenPSXMissing) {
  // basis has rz + sx but no p => PSX unavailable, ZSX available.
  std::set<std::string> basis = {"rz", "sx"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZSX");
}

TEST(EulerBasisSelectionTest, PartialPSXReturnsNullopt) {
  // Only p (not sx) => PSX incomplete; no other Euler basis matches.
  std::set<std::string> basis = {"p"};
  auto result = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(EulerBasisSelectionTest, PartialZSXReturnsNullopt) {
  // Only sx (not rz) => ZSX incomplete; no other match.
  std::set<std::string> basis = {"sx"};
  auto result = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(EulerBasisSelectionTest, EmptyBasisReturnsNullopt) {
  std::set<std::string> basis = {};
  auto result = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(EulerBasisSelectionTest, OnlyNonEulerGatesReturnsNullopt) {
  std::set<std::string> basis = {"cx", "cz", "iswap", "measure"};
  auto result = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(result.has_value());
}

TEST(EulerBasisSelectionTest, AllEulerGatesPicksZYZ) {
  // All Euler basis gates present => ZYZ (highest priority).
  std::set<std::string> basis = {
      "rz", "ry", "rx", "u3", "u", "p", "sx", "r"};
  auto result = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(result.has_value());
  EXPECT_EQ(result.value(), "ZYZ");
}

// ========================================================================
// has_euler_basis — Exhaustive Coverage
//
// 对 8 种 Euler 基逐一验证: 满足时返回 true，缺门时返回 false，
// 未知基名返回 false。
// ========================================================================

TEST(HasEulerBasisTest, ZXZ_TrueWhenBothPresent) {
  std::set<std::string> basis = {"rz", "rx"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "ZXZ"));
}

TEST(HasEulerBasisTest, ZXZ_FalseWhenRxMissing) {
  std::set<std::string> basis = {"rz"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "ZXZ"));
}

TEST(HasEulerBasisTest, XYX_TrueWhenBothPresent) {
  std::set<std::string> basis = {"rx", "ry"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "XYX"));
}

TEST(HasEulerBasisTest, XYX_FalseWhenRyMissing) {
  std::set<std::string> basis = {"rx"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "XYX"));
}

TEST(HasEulerBasisTest, U3_True) {
  std::set<std::string> basis = {"u3"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "U3"));
}

TEST(HasEulerBasisTest, U3_FalseWhenAbsent) {
  std::set<std::string> basis = {"rz", "ry"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "U3"));
}

TEST(HasEulerBasisTest, U_True) {
  std::set<std::string> basis = {"u"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "U"));
}

TEST(HasEulerBasisTest, U_FalseWhenAbsent) {
  std::set<std::string> basis = {"u3"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "U"));
}

TEST(HasEulerBasisTest, PSX_True) {
  std::set<std::string> basis = {"p", "sx"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "PSX"));
}

TEST(HasEulerBasisTest, PSX_FalseWhenSxMissing) {
  std::set<std::string> basis = {"p"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "PSX"));
}

TEST(HasEulerBasisTest, ZSX_True) {
  std::set<std::string> basis = {"rz", "sx"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "ZSX"));
}

TEST(HasEulerBasisTest, ZSX_FalseWhenRzMissing) {
  std::set<std::string> basis = {"sx"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "ZSX"));
}

TEST(HasEulerBasisTest, RR_True) {
  std::set<std::string> basis = {"r"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "RR"));
}

TEST(HasEulerBasisTest, RR_FalseWhenAbsent) {
  std::set<std::string> basis = {"rz", "ry"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "RR"));
}

TEST(HasEulerBasisTest, UnknownBasisNameReturnsFalse) {
  std::set<std::string> basis = {"rz", "ry", "rx", "u3"};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "ZYX"));
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "XYZ"));
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, ""));
}

TEST(HasEulerBasisTest, EmptyBasisAllFalse) {
  std::set<std::string> basis = {};
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "ZYZ"));
  EXPECT_FALSE(basis_selector::has_euler_basis(basis, "RR"));
}

TEST(HasEulerBasisTest, SupersetBasisStillTrue) {
  // Extra gates present do not break the check.
  std::set<std::string> basis = {"cx", "rz", "ry", "h", "t"};
  EXPECT_TRUE(basis_selector::has_euler_basis(basis, "ZYZ"));
}

// ========================================================================
// find_matching_bases — Edge Cases & Ordering
//
// 覆盖空字典、空 basis、全部匹配、无匹配、顺序保持。
// ========================================================================

TEST(FindMatchingBasesTest, EmptyDictReturnsNothing) {
  std::set<std::string> basis = {"rz", "ry"};
  std::map<std::string, std::vector<std::string>> dict = {};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 0u);
}

TEST(FindMatchingBasesTest, EmptyBasisReturnsNothing) {
  std::set<std::string> basis = {};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}}, {"U3", {"u3"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 0u);
}

TEST(FindMatchingBasesTest, AllMatch) {
  std::set<std::string> basis = {"rz", "ry", "rx", "u3"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}}, {"ZXZ", {"rz", "rx"}}, {"U3", {"u3"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 3u);
}

TEST(FindMatchingBasesTest, NoMatch) {
  std::set<std::string> basis = {"cx", "cz"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}}, {"ZXZ", {"rz", "rx"}}, {"U3", {"u3"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 0u);
}

TEST(FindMatchingBasesTest, SingleRequirementGate) {
  // A dict entry requiring a single gate that is present.
  std::set<std::string> basis = {"r"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"RR", {"r"}}, {"ZYZ", {"rz", "ry"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  ASSERT_EQ(matches.size(), 1u);
  EXPECT_EQ(matches[0], "RR");
}

TEST(FindMatchingBasesTest, PartialMatchExcluded) {
  // ZYZ requires rz AND ry; only rz present => ZYZ excluded, ZXZ included.
  std::set<std::string> basis = {"rz", "rx"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}}, {"ZXZ", {"rz", "rx"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  ASSERT_EQ(matches.size(), 1u);
  EXPECT_EQ(matches[0], "ZXZ");
}

TEST(FindMatchingBasesTest, EmptyRequiredListAlwaysMatches) {
  // A dict entry with an empty required list matches any basis (vacuously true).
  std::set<std::string> basis = {"cx"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"EMPTY", {}}, {"ZYZ", {"rz", "ry"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  ASSERT_EQ(matches.size(), 1u);
  EXPECT_EQ(matches[0], "EMPTY");
}

TEST(FindMatchingBasesTest, OrderingFollowsDictKeySortOrder) {
  // std::map iterates in key-sorted (lexicographic) order; matches appear in
  // that order, NOT the insertion order of the initializer list.
  std::set<std::string> basis = {"rz", "ry", "rx", "u3"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"U3", {"u3"}}, {"ZYZ", {"rz", "ry"}}, {"ZXZ", {"rz", "rx"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  ASSERT_EQ(matches.size(), 3u);
  // Lexicographic key order: "U3" < "ZXZ" < "ZYZ" ('X' < 'Y').
  EXPECT_EQ(matches[0], "U3");
  EXPECT_EQ(matches[1], "ZXZ");
  EXPECT_EQ(matches[2], "ZYZ");
}

TEST(FindMatchingBasesTest, SupersetBasisMatchesAll) {
  // Extra gates in basis do not prevent matches.
  std::set<std::string> basis = {"cx", "rz", "ry", "rx", "h", "t", "s"};
  std::map<std::string, std::vector<std::string>> dict = {
      {"ZYZ", {"rz", "ry"}}, {"ZXZ", {"rz", "rx"}}};
  auto matches = basis_selector::find_matching_bases(basis, dict);
  EXPECT_EQ(matches.size(), 2u);
}

// ========================================================================
// Combined / Integration Scenarios
//
// 模拟真实硬件基门集，验证 choose_kak_gate + choose_euler_basis 的组合行为。
// ========================================================================

TEST(IntegrationTest, IBMSuperconductingBasis) {
  // Typical IBM basis: cx + rz + ry (plus sx for reset/measure).
  std::set<std::string> basis = {"cx", "rz", "sx", "measure", "reset"};
  auto kak = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(kak.has_value());
  EXPECT_EQ(kak.value(), "cx");
  auto euler = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(euler.has_value());
  EXPECT_EQ(euler.value(), "ZSX");  // rz + sx, no rz+ry/rx
}

TEST(IntegrationTest, FullUniversalBasis) {
  // Universal gate set with all standard 1Q + 2Q primitives.
  std::set<std::string> basis = {
      "cx", "cz", "rz", "ry", "rx", "u3", "u", "h", "t", "s", "sx", "p"};
  auto kak = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(kak.has_value());
  EXPECT_EQ(kak.value(), "cx");
  auto euler = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(euler.has_value());
  EXPECT_EQ(euler.value(), "ZYZ");
}

TEST(IntegrationTest, IonTrapBasis) {
  // Ion-trap-style basis: iswap entangler + rx/ry (native rotations).
  std::set<std::string> basis = {"iswap", "rx", "ry", "rz"};
  auto kak = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(kak.has_value());
  EXPECT_EQ(kak.value(), "iswap");
  auto euler = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(euler.has_value());
  EXPECT_EQ(euler.value(), "ZYZ");  // rz + ry present
}

TEST(IntegrationTest, MinimalU3Basis) {
  // Only cx + u3: a valid but minimal universal set.
  std::set<std::string> basis = {"cx", "u3"};
  auto kak = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(kak.has_value());
  EXPECT_EQ(kak.value(), "cx");
  auto euler = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(euler.has_value());
  EXPECT_EQ(euler.value(), "U3");
}

TEST(IntegrationTest, Only1QGatesNoKak) {
  // Pure 1Q basis => no KAK gate available.
  std::set<std::string> basis = {"rz", "ry", "rx"};
  auto kak = basis_selector::choose_kak_gate(basis);
  EXPECT_FALSE(kak.has_value());
  auto euler = basis_selector::choose_euler_basis(basis);
  ASSERT_TRUE(euler.has_value());
  EXPECT_EQ(euler.value(), "ZYZ");
}

TEST(IntegrationTest, Only2QGatesNoEuler) {
  // Pure 2Q basis => KAK available but no Euler basis.
  std::set<std::string> basis = {"cx", "cz", "iswap"};
  auto kak = basis_selector::choose_kak_gate(basis);
  ASSERT_TRUE(kak.has_value());
  EXPECT_EQ(kak.value(), "cx");
  auto euler = basis_selector::choose_euler_basis(basis);
  EXPECT_FALSE(euler.has_value());
}
