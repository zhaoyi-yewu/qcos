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
#include <vector>

namespace Constant {
// 单量子门常量
inline const std::string SINGLE_QUBIT_GATE_X = "x";
inline const std::string SINGLE_QUBIT_GATE_Y = "y";
inline const std::string SINGLE_QUBIT_GATE_Z = "z";
inline const std::string SINGLE_QUBIT_GATE_H = "h";
inline const std::string SINGLE_QUBIT_GATE_S = "s";
inline const std::string SINGLE_QUBIT_GATE_T = "t";
inline const std::string SINGLE_QUBIT_GATE_P = "p";
inline const std::string SINGLE_QUBIT_GATE_U = "u";
inline const std::string SINGLE_QUBIT_GATE_U_UPPERCASE = "U";
inline const std::string SINGLE_QUBIT_GATE_R = "r";
inline const std::string SINGLE_QUBIT_GATE_RX = "rx";
inline const std::string SINGLE_QUBIT_GATE_RY = "ry";
inline const std::string SINGLE_QUBIT_GATE_RZ = "rz";
inline const std::string SINGLE_QUBIT_GATE_SX = "sx";
inline const std::string SINGLE_QUBIT_GATE_SXDG = "sxdg";
inline const std::string SINGLE_QUBIT_GATE_SDG = "sdg";
inline const std::string SINGLE_QUBIT_GATE_TDG = "tdg";
inline const std::string SINGLE_QUBIT_GATE_U1 = "u1";
inline const std::string SINGLE_QUBIT_GATE_U2 = "u2";
inline const std::string SINGLE_QUBIT_GATE_U3 = "u3";
inline const std::string SINGLE_QUBIT_GATE_RESET = "reset";

// 单量子门列表
inline const std::vector<std::string> SINGLE_QUBIT_GATE_LIST = {
    SINGLE_QUBIT_GATE_X,           SINGLE_QUBIT_GATE_Y,
    SINGLE_QUBIT_GATE_Z,           SINGLE_QUBIT_GATE_H,
    SINGLE_QUBIT_GATE_S,           SINGLE_QUBIT_GATE_T,
    SINGLE_QUBIT_GATE_P,           SINGLE_QUBIT_GATE_U,
    SINGLE_QUBIT_GATE_U_UPPERCASE, SINGLE_QUBIT_GATE_R,
    SINGLE_QUBIT_GATE_RX,          SINGLE_QUBIT_GATE_RY,
    SINGLE_QUBIT_GATE_RZ,          SINGLE_QUBIT_GATE_SX,
    SINGLE_QUBIT_GATE_SXDG,        SINGLE_QUBIT_GATE_SDG,
    SINGLE_QUBIT_GATE_TDG,         SINGLE_QUBIT_GATE_U1,
    SINGLE_QUBIT_GATE_U2,          SINGLE_QUBIT_GATE_U3,
};

// 双量子门常量
inline const std::string TWO_QUBIT_GATE_CH = "ch";
inline const std::string TWO_QUBIT_GATE_CRX = "crx";
inline const std::string TWO_QUBIT_GATE_CRY = "cry";
inline const std::string TWO_QUBIT_GATE_CRZ = "crz";
inline const std::string TWO_QUBIT_GATE_CX = "cx";
inline const std::string TWO_QUBIT_GATE_CX_UPPERCASE = "CX";
inline const std::string TWO_QUBIT_GATE_CY = "cy";
inline const std::string TWO_QUBIT_GATE_CZ = "cz";
inline const std::string TWO_QUBIT_GATE_SWAP = "swap";
inline const std::string TWO_QUBIT_GATE_ISWAP = "iswap";
inline const std::string TWO_QUBIT_GATE_CU1 = "cu1";
inline const std::string TWO_QUBIT_GATE_CP = "cp";
inline const std::string TWO_QUBIT_GATE_CS = "cs";
inline const std::string TWO_QUBIT_GATE_CSDG = "csdg";
inline const std::string TWO_QUBIT_GATE_CU3 = "cu3";
inline const std::string TWO_QUBIT_GATE_ECR = "ecr";
inline const std::string TWO_QUBIT_GATE_DCX = "dcx";
inline const std::string TWO_QUBIT_GATE_CSX = "csx";
inline const std::string TWO_QUBIT_GATE_CU = "cu";
inline const std::string TWO_QUBIT_GATE_RXX = "rxx";
inline const std::string TWO_QUBIT_GATE_RYY = "ryy";
inline const std::string TWO_QUBIT_GATE_RZZ = "rzz";
inline const std::string TWO_QUBIT_GATE_RZX = "rzx";

// 双量子门列表
inline const std::vector<std::string> TWO_QUBIT_GATE_LIST = {
    TWO_QUBIT_GATE_CH,    TWO_QUBIT_GATE_CRX,  TWO_QUBIT_GATE_CRY,
    TWO_QUBIT_GATE_CRZ,   TWO_QUBIT_GATE_CX,   TWO_QUBIT_GATE_CX_UPPERCASE,
    TWO_QUBIT_GATE_CY,    TWO_QUBIT_GATE_CZ,   TWO_QUBIT_GATE_SWAP,
    TWO_QUBIT_GATE_ISWAP, TWO_QUBIT_GATE_CU1,  TWO_QUBIT_GATE_CP,
    TWO_QUBIT_GATE_CS,    TWO_QUBIT_GATE_CSDG, TWO_QUBIT_GATE_CU3,
    TWO_QUBIT_GATE_ECR,   TWO_QUBIT_GATE_DCX,  TWO_QUBIT_GATE_CSX,
    TWO_QUBIT_GATE_CU,    TWO_QUBIT_GATE_RXX,  TWO_QUBIT_GATE_RZZ,
};

// 三量子门常量
inline const std::string THREE_QUBIT_GATE_CCX = "ccx";
inline const std::string THREE_QUBIT_GATE_CSWAP = "cswap";
inline const std::string THREE_QUBIT_GATE_RCCX = "rccx";

// 三量子门列表
inline const std::vector<std::string> THREE_QUBIT_GATE_LIST = {
    THREE_QUBIT_GATE_CCX,
    THREE_QUBIT_GATE_CSWAP,
    THREE_QUBIT_GATE_RCCX,
};

// 四量子门常量
inline const std::string FOUR_QUBIT_GATE_RC3X = "rc3x";
inline const std::string FOUR_QUBIT_GATE_C3X = "c3x";
inline const std::string FOUR_QUBIT_GATE_C3SQRTX = "c3sqrtx";

// 四量子门列表
inline const std::vector<std::string> FOUR_QUBIT_GATE_LIST = {
    FOUR_QUBIT_GATE_RC3X,
    FOUR_QUBIT_GATE_C3X,
    FOUR_QUBIT_GATE_C3SQRTX,
};

// 五量子门常量
inline const std::string FIVE_QUBIT_GATE_C4X = "c4x";

// 五量子门列表
inline const std::vector<std::string> FIVE_QUBIT_GATE_LIST = {
    FIVE_QUBIT_GATE_C4X,
};

// 所有门列表
inline const std::vector<std::string> ALL_GATE_LIST = {
    // 单量子门
    SINGLE_QUBIT_GATE_X,
    SINGLE_QUBIT_GATE_Y,
    SINGLE_QUBIT_GATE_Z,
    SINGLE_QUBIT_GATE_H,
    SINGLE_QUBIT_GATE_S,
    SINGLE_QUBIT_GATE_T,
    SINGLE_QUBIT_GATE_P,
    SINGLE_QUBIT_GATE_U,
    SINGLE_QUBIT_GATE_U_UPPERCASE,
    SINGLE_QUBIT_GATE_R,
    SINGLE_QUBIT_GATE_RX,
    SINGLE_QUBIT_GATE_RY,
    SINGLE_QUBIT_GATE_RZ,
    SINGLE_QUBIT_GATE_SX,
    SINGLE_QUBIT_GATE_SXDG,
    SINGLE_QUBIT_GATE_SDG,
    SINGLE_QUBIT_GATE_TDG,
    SINGLE_QUBIT_GATE_U1,
    SINGLE_QUBIT_GATE_U2,
    SINGLE_QUBIT_GATE_U3,

    // 双量子门
    TWO_QUBIT_GATE_CH,
    TWO_QUBIT_GATE_CRX,
    TWO_QUBIT_GATE_CRY,
    TWO_QUBIT_GATE_CRZ,
    TWO_QUBIT_GATE_CX,
    TWO_QUBIT_GATE_CX_UPPERCASE,
    TWO_QUBIT_GATE_CY,
    TWO_QUBIT_GATE_CZ,
    TWO_QUBIT_GATE_SWAP,
    TWO_QUBIT_GATE_ISWAP,
    TWO_QUBIT_GATE_CU1,
    TWO_QUBIT_GATE_CP,
    TWO_QUBIT_GATE_CS,
    TWO_QUBIT_GATE_CSDG,
    TWO_QUBIT_GATE_CU3,
    TWO_QUBIT_GATE_ECR,
    TWO_QUBIT_GATE_DCX,
    TWO_QUBIT_GATE_CSX,
    TWO_QUBIT_GATE_CU,
    TWO_QUBIT_GATE_RXX,
    TWO_QUBIT_GATE_RYY,
    TWO_QUBIT_GATE_RZZ,
    TWO_QUBIT_GATE_RZX,

    // 三量子门
    THREE_QUBIT_GATE_CCX,
    THREE_QUBIT_GATE_CSWAP,
    THREE_QUBIT_GATE_RCCX,

    // 四量子门
    FOUR_QUBIT_GATE_RC3X,
    FOUR_QUBIT_GATE_C3X,
    FOUR_QUBIT_GATE_C3SQRTX,

    // 五量子门
    FIVE_QUBIT_GATE_C4X,
};

// 特殊常量
inline const std::string ALL_GATES = "all";
}  // namespace Constant
