
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

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/../..)

PROJECT_ROOT=${TOP_DIR}/src_cpp/transpiler_cpp
TARGET_DIR=${TOP_DIR}/src/wy_qcos/transpiler
BUILD_DIR=${PROJECT_ROOT}/build
DIST_DIR=${PROJECT_ROOT}/dist

NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu)

BUILD_TYPE=Release
FORCE_REBUILD=0

for ARG in "$@"; do
    case "$ARG" in
        release|Release)
            BUILD_TYPE=Release
            ;;
        debug|Debug)
            BUILD_TYPE=Debug
            ;;
        rebuild|Rebuild)
            FORCE_REBUILD=1
            ;;
        *)
            echo "Invalid argument: $ARG"
            echo "Usage: $0 [release|debug] [rebuild]"
            echo "   or: $0 [rebuild] [release|debug]"
            exit 1
            ;;
    esac
done

NEED_CLEAN_REBUILD=${FORCE_REBUILD}
if [[ ! -d "${BUILD_DIR}" ]]; then
    NEED_CLEAN_REBUILD=1
fi

echo "Build type: $BUILD_TYPE"
if [[ "$NEED_CLEAN_REBUILD" == "1" ]]; then
    echo "Build mode: clean rebuild"
else
    echo "Build mode: incremental"
fi

mkdir -p ${DIST_DIR}
rm -rf ${DIST_DIR:?}/*

if [[ "$NEED_CLEAN_REBUILD" == "1" ]]; then
    rm -rf ${BUILD_DIR}
fi
mkdir -p ${BUILD_DIR}

cd ${BUILD_DIR}
PYTHON_EXE=${Python_EXECUTABLE:-$(which python3 2>/dev/null || echo python3)}
PY_LIBDIR=$(${PYTHON_EXE} -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')" 2>/dev/null)
PY_LDLIB=$(${PYTHON_EXE} -c "import sysconfig; print(sysconfig.get_config_var('LDLIBRARY') or '')" 2>/dev/null)
PY_INCDIR=$(${PYTHON_EXE} -c "import sysconfig; print(sysconfig.get_path('include') or '')" 2>/dev/null)
PY_LIB=""
[ -n "${PY_LIBDIR}" ] && [ -n "${PY_LDLIB}" ] && PY_LIB="${PY_LIBDIR}/${PY_LDLIB}"
cmake -DCMAKE_BUILD_TYPE=${BUILD_TYPE} -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DPython_EXECUTABLE="${PYTHON_EXE}" \
    ${PY_LIB:+-DPython_LIBRARY="${PY_LIB}"} \
    ${PY_INCDIR:+-DPython_INCLUDE_DIR="${PY_INCDIR}"} \
    ..
make -j${NPROC} ${BUILD_TARGET:-}

# copy .so and .pyi to wy_qcos/transpiler
mkdir -p "$TARGET_DIR"
echo "Copying dist to $TARGET_DIR"
if [[ -d "${DIST_DIR}/${BUILD_TYPE}" ]]; then
    mv ${DIST_DIR}/${BUILD_TYPE}/* $TARGET_DIR/
else
    mv ${DIST_DIR}/* $TARGET_DIR/
fi
echo "Copy done"
