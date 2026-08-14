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

#pragma once

#include <utility>
#include <vector>

#include "verify/qpu_verifier.h"

namespace qcos {

/// 8 比特、4 条耦合边的简单测试拓扑
inline VerifyParams make_test_params() {
  VerifyParams params;
  params.bits = 8;
  params.basis_gates = {"h", "rx", "ry", "rz", "cz"};
  params.coupling_list = {{0, 1}, {1, 0}, {1, 2}, {2, 1}};
  params.edge_fidelities = {0.99, 0.99, 0.98, 0.98};
  params.single_qubit_fidelities = {0.999, 0.999, 0.999, 0.999,
                                    0.0,   0.0,   0.0,   0.0};
  return params;
}

/// Shenglian 真实芯片拓扑：83 比特、60 条耦合边
inline VerifyParams make_shenglian_params() {
  VerifyParams params;
  params.bits = 83;
  params.basis_gates = {"h", "x", "rx", "ry", "rz", "cz", "cx", "measure"};
  params.coupling_list = {
      {15, 22}, {16, 22}, {16, 23}, {17, 23}, {18, 24}, {18, 25}, {20, 27},
      {22, 29}, {23, 30}, {25, 32}, {27, 34}, {28, 35}, {29, 35}, {30, 36},
      {30, 37}, {31, 37}, {31, 38}, {32, 38}, {32, 39}, {33, 39}, {34, 40},
      {34, 41}, {36, 43}, {37, 44}, {38, 45}, {39, 46}, {41, 48}, {42, 49},
      {43, 49}, {43, 50}, {45, 51}, {46, 53}, {47, 53}, {48, 54}, {49, 56},
      {50, 57}, {51, 58}, {53, 60}, {54, 61}, {59, 66}, {60, 66}, {61, 67},
      {61, 68}, {62, 68}, {62, 69}, {63, 70}, {64, 71}, {66, 73}, {67, 74},
      {68, 75}, {69, 76}, {70, 77}, {71, 77}, {73, 79}, {73, 80}, {74, 80},
      {74, 81}, {75, 81}, {75, 82}, {76, 82}};
  params.edge_fidelities = std::vector<double>(60, 0.99);
  params.single_qubit_fidelities = std::vector<double>(83, 0.999);
  return params;
}

/// MQ02 真机拓扑：24 比特线性链（Q0-Q23），24 条耦合边（双向 48 条）
/// 数据来源：MQ02_coupler_metrics / MQ02_qubit_metrics（2026-08-07）
inline VerifyParams make_mq02_params() {
  VerifyParams params;
  params.bits = 24;
  params.basis_gates = {"h", "x", "rx", "ry", "rz", "cz", "cx"};
  // 线性链 Q0-Q1-...-Q23
  params.coupling_list = {
      {0, 1},   {1, 0},   {1, 2},   {2, 1},   {2, 3},   {3, 2},   {3, 4},
      {4, 3},   {4, 5},   {5, 4},   {5, 6},   {6, 5},   {6, 7},   {7, 6},
      {7, 8},   {8, 7},   {8, 9},   {9, 8},   {9, 10},  {10, 9},  {10, 11},
      {11, 10}, {11, 12}, {12, 11}, {12, 13}, {13, 12}, {13, 14}, {14, 13},
      {14, 15}, {15, 14}, {15, 16}, {16, 15}, {16, 17}, {17, 16}, {17, 18},
      {18, 17}, {18, 19}, {19, 18}, {19, 20}, {20, 19}, {20, 21}, {21, 20},
      {21, 22}, {22, 21}, {22, 23}, {23, 22}};
  params.edge_fidelities = {
      0.99448, 0.99448, 0.99661, 0.99661, 0.99414, 0.99414, 0.99734, 0.99734,
      0.99793, 0.99793, 0.99464, 0.99464, 0.98715, 0.98715, 0.98982, 0.98982,
      0.99447, 0.99447, 0.99645, 0.99645, 0.99705, 0.99705, 0.99726, 0.99726,
      0.99470, 0.99470, 0.99806, 0.99806, 0.99676, 0.99676, 0.99585, 0.99585,
      0.99549, 0.99549, 0.99316, 0.99316, 0.99672, 0.99672, 0.99602, 0.99602,
      0.99656, 0.99656, 0.99824, 0.99824, 0.99692, 0.99692};
  params.single_qubit_fidelities = {
      0.99960, 0.99967, 0.99952, 0.99951, 0.99960, 0.99968, 0.99968, 0.99802,
      0.99893, 0.99953, 0.99969, 0.99959, 0.99929, 0.99962, 0.99973, 0.99848,
      0.99961, 0.99960, 0.99959, 0.99952, 0.99971, 0.99965, 0.99969, 0.99950};
  return params;
}

/// QZ01 表面码真机拓扑：17 比特（Q0-Q16），24 条耦合边（双向 48 条）
/// 数据来源：QZ01-surface_code_coupler_metrics /
/// QZ01-surface_code_qubit_metrics（2026-08-07）
inline VerifyParams make_qz01_params() {
  VerifyParams params;
  params.bits = 17;
  params.basis_gates = {"h", "x", "rx", "ry", "rz", "cz", "cx"};
  params.coupling_list = {
      {0, 9},  {9, 0},  {1, 9},  {9, 1},  {1, 10}, {10, 1}, {1, 13}, {13, 1},
      {2, 10}, {10, 2}, {2, 13}, {13, 2}, {3, 9},  {9, 3},  {3, 11}, {11, 3},
      {4, 9},  {9, 4},  {4, 10}, {10, 4}, {4, 11}, {11, 4}, {4, 12}, {12, 4},
      {5, 10}, {10, 5}, {5, 12}, {12, 5}, {5, 14}, {14, 5}, {6, 11}, {11, 6},
      {6, 15}, {15, 6}, {7, 11}, {11, 7}, {7, 12}, {12, 7}, {7, 15}, {15, 7},
      {8, 12}, {12, 8}, {8, 14}, {14, 8}, {3, 16}, {16, 3}, {0, 16}, {16, 0}};
  params.edge_fidelities = {
      0.99509, 0.99509, 0.99437, 0.99437, 0.99577, 0.99577, 0.99553, 0.99553,
      0.99575, 0.99575, 0.99151, 0.99151, 0.99523, 0.99523, 0.99486, 0.99486,
      0.99533, 0.99533, 0.99466, 0.99466, 0.99370, 0.99370, 0.99399, 0.99399,
      0.99638, 0.99638, 0.99356, 0.99356, 0.99623, 0.99623, 0.99074, 0.99074,
      0.99520, 0.99520, 0.99316, 0.99316, 0.99104, 0.99104, 0.99358, 0.99358,
      0.99433, 0.99433, 0.99442, 0.99442, 0.99405, 0.99405, 0.99464, 0.99464};
  params.single_qubit_fidelities = {
      0.99950, 0.99925, 0.99933, 0.99934, 0.99950, 0.99927,
      0.99896, 0.99909, 0.99934, 0.99934, 0.99946, 0.99919,
      0.99932, 0.99935, 0.99935, 0.99925, 0.99929};
  return params;
}

}  // namespace qcos
