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
#include <string>
#include <string_view>
#include <vector>

namespace Constant {
// 单量子门常量
inline constexpr std::string_view SINGLE_QUBIT_GATE_X = "x";
inline constexpr std::string_view SINGLE_QUBIT_GATE_Y = "y";
inline constexpr std::string_view SINGLE_QUBIT_GATE_Z = "z";
inline constexpr std::string_view SINGLE_QUBIT_GATE_H = "h";
inline constexpr std::string_view SINGLE_QUBIT_GATE_S = "s";
inline constexpr std::string_view SINGLE_QUBIT_GATE_T = "t";
inline constexpr std::string_view SINGLE_QUBIT_GATE_P = "p";
inline constexpr std::string_view SINGLE_QUBIT_GATE_U = "u";
inline constexpr std::string_view SINGLE_QUBIT_GATE_U_UPPERCASE = "U";
inline constexpr std::string_view SINGLE_QUBIT_GATE_R = "r";
inline constexpr std::string_view SINGLE_QUBIT_GATE_RX = "rx";
inline constexpr std::string_view SINGLE_QUBIT_GATE_RY = "ry";
inline constexpr std::string_view SINGLE_QUBIT_GATE_RZ = "rz";
inline constexpr std::string_view SINGLE_QUBIT_GATE_SX = "sx";
inline constexpr std::string_view SINGLE_QUBIT_GATE_SXDG = "sxdg";
inline constexpr std::string_view SINGLE_QUBIT_GATE_I = "id";
inline constexpr std::string_view SINGLE_QUBIT_GATE_SDG = "sdg";
inline constexpr std::string_view SINGLE_QUBIT_GATE_TDG = "tdg";
inline constexpr std::string_view SINGLE_QUBIT_GATE_U1 = "u1";
inline constexpr std::string_view SINGLE_QUBIT_GATE_U2 = "u2";
inline constexpr std::string_view SINGLE_QUBIT_GATE_U3 = "u3";
inline constexpr std::string_view SINGLE_QUBIT_GATE_RESET = "reset";

// 单量子门列表
inline const std::vector<std::string> SINGLE_QUBIT_GATE_LIST = {
    std::string(SINGLE_QUBIT_GATE_X),
    std::string(SINGLE_QUBIT_GATE_Y),
    std::string(SINGLE_QUBIT_GATE_Z),
    std::string(SINGLE_QUBIT_GATE_H),
    std::string(SINGLE_QUBIT_GATE_S),
    std::string(SINGLE_QUBIT_GATE_T),
    std::string(SINGLE_QUBIT_GATE_P),
    std::string(SINGLE_QUBIT_GATE_U),
    std::string(SINGLE_QUBIT_GATE_U_UPPERCASE),
    std::string(SINGLE_QUBIT_GATE_R),
    std::string(SINGLE_QUBIT_GATE_RX),
    std::string(SINGLE_QUBIT_GATE_RY),
    std::string(SINGLE_QUBIT_GATE_RZ),
    std::string(SINGLE_QUBIT_GATE_SX),
    std::string(SINGLE_QUBIT_GATE_SXDG),
    std::string(SINGLE_QUBIT_GATE_I),
    std::string(SINGLE_QUBIT_GATE_SDG),
    std::string(SINGLE_QUBIT_GATE_TDG),
    std::string(SINGLE_QUBIT_GATE_U1),
    std::string(SINGLE_QUBIT_GATE_U2),
    std::string(SINGLE_QUBIT_GATE_U3),
};

// 双量子门常量
inline constexpr std::string_view TWO_QUBIT_GATE_CH = "ch";
inline constexpr std::string_view TWO_QUBIT_GATE_CRX = "crx";
inline constexpr std::string_view TWO_QUBIT_GATE_CRY = "cry";
inline constexpr std::string_view TWO_QUBIT_GATE_CRZ = "crz";
inline constexpr std::string_view TWO_QUBIT_GATE_CX = "cx";
inline constexpr std::string_view TWO_QUBIT_GATE_CX_UPPERCASE = "CX";
inline constexpr std::string_view TWO_QUBIT_GATE_CY = "cy";
inline constexpr std::string_view TWO_QUBIT_GATE_CZ = "cz";
inline constexpr std::string_view TWO_QUBIT_GATE_SWAP = "swap";
inline constexpr std::string_view TWO_QUBIT_GATE_ISWAP = "iswap";
inline constexpr std::string_view TWO_QUBIT_GATE_CU1 = "cu1";
inline constexpr std::string_view TWO_QUBIT_GATE_CP = "cp";
inline constexpr std::string_view TWO_QUBIT_GATE_CS = "cs";
inline constexpr std::string_view TWO_QUBIT_GATE_CSDG = "csdg";
inline constexpr std::string_view TWO_QUBIT_GATE_CU3 = "cu3";
inline constexpr std::string_view TWO_QUBIT_GATE_ECR = "ecr";
inline constexpr std::string_view TWO_QUBIT_GATE_DCX = "dcx";
inline constexpr std::string_view TWO_QUBIT_GATE_CSX = "csx";
inline constexpr std::string_view TWO_QUBIT_GATE_CU = "cu";
inline constexpr std::string_view TWO_QUBIT_GATE_RXX = "rxx";
inline constexpr std::string_view TWO_QUBIT_GATE_RYY = "ryy";
inline constexpr std::string_view TWO_QUBIT_GATE_RZZ = "rzz";
inline constexpr std::string_view TWO_QUBIT_GATE_RZX = "rzx";

// 双量子门列表
inline const std::vector<std::string> TWO_QUBIT_GATE_LIST = {
    std::string(TWO_QUBIT_GATE_CH),
    std::string(TWO_QUBIT_GATE_CRX),
    std::string(TWO_QUBIT_GATE_CRY),
    std::string(TWO_QUBIT_GATE_CRZ),
    std::string(TWO_QUBIT_GATE_CX),
    std::string(TWO_QUBIT_GATE_CX_UPPERCASE),
    std::string(TWO_QUBIT_GATE_CY),
    std::string(TWO_QUBIT_GATE_CZ),
    std::string(TWO_QUBIT_GATE_SWAP),
    std::string(TWO_QUBIT_GATE_ISWAP),
    std::string(TWO_QUBIT_GATE_CU1),
    std::string(TWO_QUBIT_GATE_CP),
    std::string(TWO_QUBIT_GATE_CS),
    std::string(TWO_QUBIT_GATE_CSDG),
    std::string(TWO_QUBIT_GATE_CU3),
    std::string(TWO_QUBIT_GATE_ECR),
    std::string(TWO_QUBIT_GATE_DCX),
    std::string(TWO_QUBIT_GATE_CSX),
    std::string(TWO_QUBIT_GATE_CU),
    std::string(TWO_QUBIT_GATE_RXX),
    std::string(TWO_QUBIT_GATE_RZZ),
};

// 三量子门常量
inline constexpr std::string_view THREE_QUBIT_GATE_CCX = "ccx";
inline constexpr std::string_view THREE_QUBIT_GATE_CCZ = "ccz";
inline constexpr std::string_view THREE_QUBIT_GATE_CSWAP = "cswap";
inline constexpr std::string_view THREE_QUBIT_GATE_RCCX = "rccx";

// 三量子门列表
inline const std::vector<std::string> THREE_QUBIT_GATE_LIST = {
    std::string(THREE_QUBIT_GATE_CCX),
    std::string(THREE_QUBIT_GATE_CCZ),
    std::string(THREE_QUBIT_GATE_CSWAP),
    std::string(THREE_QUBIT_GATE_RCCX),
};

// 四量子门常量
inline constexpr std::string_view FOUR_QUBIT_GATE_RC3X = "rc3x";
inline constexpr std::string_view FOUR_QUBIT_GATE_C3X = "c3x";
inline constexpr std::string_view FOUR_QUBIT_GATE_C3SQRTX = "c3sqrtx";

// 四量子门列表
inline const std::vector<std::string> FOUR_QUBIT_GATE_LIST = {
    std::string(FOUR_QUBIT_GATE_RC3X),
    std::string(FOUR_QUBIT_GATE_C3X),
    std::string(FOUR_QUBIT_GATE_C3SQRTX),
};

// 五量子门常量
inline constexpr std::string_view FIVE_QUBIT_GATE_C4X = "c4x";

// 五量子门列表
inline const std::vector<std::string> FIVE_QUBIT_GATE_LIST = {
    std::string(FIVE_QUBIT_GATE_C4X),
};

// 所有门列表
inline const std::vector<std::string> ALL_GATE_LIST = {
    // 单量子门
    std::string(SINGLE_QUBIT_GATE_X),
    std::string(SINGLE_QUBIT_GATE_Y),
    std::string(SINGLE_QUBIT_GATE_Z),
    std::string(SINGLE_QUBIT_GATE_H),
    std::string(SINGLE_QUBIT_GATE_S),
    std::string(SINGLE_QUBIT_GATE_T),
    std::string(SINGLE_QUBIT_GATE_P),
    std::string(SINGLE_QUBIT_GATE_U),
    std::string(SINGLE_QUBIT_GATE_U_UPPERCASE),
    std::string(SINGLE_QUBIT_GATE_R),
    std::string(SINGLE_QUBIT_GATE_RX),
    std::string(SINGLE_QUBIT_GATE_RY),
    std::string(SINGLE_QUBIT_GATE_RZ),
    std::string(SINGLE_QUBIT_GATE_SX),
    std::string(SINGLE_QUBIT_GATE_SXDG),
    std::string(SINGLE_QUBIT_GATE_I),
    std::string(SINGLE_QUBIT_GATE_SDG),
    std::string(SINGLE_QUBIT_GATE_TDG),
    std::string(SINGLE_QUBIT_GATE_U1),
    std::string(SINGLE_QUBIT_GATE_U2),
    std::string(SINGLE_QUBIT_GATE_U3),

    // 双量子门
    std::string(TWO_QUBIT_GATE_CH),
    std::string(TWO_QUBIT_GATE_CRX),
    std::string(TWO_QUBIT_GATE_CRY),
    std::string(TWO_QUBIT_GATE_CRZ),
    std::string(TWO_QUBIT_GATE_CX),
    std::string(TWO_QUBIT_GATE_CX_UPPERCASE),
    std::string(TWO_QUBIT_GATE_CY),
    std::string(TWO_QUBIT_GATE_CZ),
    std::string(TWO_QUBIT_GATE_SWAP),
    std::string(TWO_QUBIT_GATE_ISWAP),
    std::string(TWO_QUBIT_GATE_CU1),
    std::string(TWO_QUBIT_GATE_CP),
    std::string(TWO_QUBIT_GATE_CS),
    std::string(TWO_QUBIT_GATE_CSDG),
    std::string(TWO_QUBIT_GATE_CU3),
    std::string(TWO_QUBIT_GATE_ECR),
    std::string(TWO_QUBIT_GATE_DCX),
    std::string(TWO_QUBIT_GATE_CSX),
    std::string(TWO_QUBIT_GATE_CU),
    std::string(TWO_QUBIT_GATE_RXX),
    std::string(TWO_QUBIT_GATE_RYY),
    std::string(TWO_QUBIT_GATE_RZZ),
    std::string(TWO_QUBIT_GATE_RZX),

    // 三量子门
    std::string(THREE_QUBIT_GATE_CCX),
    std::string(THREE_QUBIT_GATE_CCZ),
    std::string(THREE_QUBIT_GATE_CSWAP),
    std::string(THREE_QUBIT_GATE_RCCX),

    // 四量子门
    std::string(FOUR_QUBIT_GATE_RC3X),
    std::string(FOUR_QUBIT_GATE_C3X),
    std::string(FOUR_QUBIT_GATE_C3SQRTX),

    // 五量子门
    std::string(FIVE_QUBIT_GATE_C4X),
};

// 特殊常量
inline constexpr std::string_view ALL_GATES = "all";
}  // namespace Constant
