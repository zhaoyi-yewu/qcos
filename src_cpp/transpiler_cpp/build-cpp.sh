
#!/usr/bin/env bash
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

set -e

PROJECT_ROOT=$(cd "$(dirname "$0")"; pwd)
BUILD_DIR=${PROJECT_ROOT}/build
DIST_DIR=${PROJECT_ROOT}/dist

NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu)

BUILD_TYPE=${1:-Release}
if [[ "$BUILD_TYPE" != "Release" && "$BUILD_TYPE" != "Debug" ]]; then
    echo "Invalid build type: $BUILD_TYPE"
    echo "Usage: $0 [Release|Debug]"
    exit 1
fi
echo "Build type: $BUILD_TYPE"

mkdir -p ${DIST_DIR}
rm -rf ${DIST_DIR:?}/*

rm -rf ${BUILD_DIR}
mkdir -p ${BUILD_DIR}

cd ${BUILD_DIR}
cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 ..
cmake --build . -j${NPROC}

# if in WuYueOs, copy .so and .pyi to wy_qcos/transpiler
PARENT2_PATH="$(dirname "$(dirname "$PROJECT_ROOT")")"
PARENT2_DIR="$(basename "$PARENT2_PATH")"

if [[ "$PARENT2_DIR" == "WuYueOs" ]]; then
    TARGET_DIR="$PARENT2_PATH/src/wy_qcos/transpiler"
    mkdir -p "$TARGET_DIR"
    echo "Copying dist to $TARGET_DIR"
    if [[ "$(uname -s)" == *"NT"* ]]; then
        cp -r "${DIST_DIR}/Debug/." "$TARGET_DIR/"
    else
        cp -r "${DIST_DIR}/." "$TARGET_DIR/"
    fi
    echo "Copy done"
fi
