#!/bin/bash
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

# Build the wy-qcos-transpiler-cpp lightweight wheel.
#
# Prerequisites:
#   - cmake >= 3.11
#   - C++17 compiler (gcc / clang)
#   - boost headers (brew install boost / yum install boost-devel)
#   - Python >= 3.11 + nanobind (pip install nanobind)
#
# Usage:
#   ./build.sh cpp       # only compile the .so via setup.py
#   ./build.sh wheel     # build .so + package into .whl
#   ./build.sh install   # build .so + pip install into current env
# ----------------------------------------------------------------------
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
CPP_SOURCE_DIR="${SCRIPT_DIR}/../../transpiler_cpp"
DIST_DIR="${CPP_SOURCE_DIR}/dist"

NPROC=$(nproc 2>/dev/null || sysctl -n hw.ncpu)
export CMAKE_BUILD_PARALLEL_LEVEL=${CMAKE_BUILD_PARALLEL_LEVEL:-${NPROC}}

PYTHON_EXE=${PYTHON_EXE:-$(which python3 2>/dev/null || echo python3)}

# ---------------------------------------------------------------------------
# build_cpp - compile the .so via setup.py (single source of CMake truth)
# ---------------------------------------------------------------------------
build_cpp() {
    echo "=== Building C++ extension via setup.py"
    echo "=== C++ source: ${CPP_SOURCE_DIR}"
    echo "=== Python:     ${PYTHON_EXE}"
    cd "${SCRIPT_DIR}"
    "${PYTHON_EXE}" setup.py build_ext --inplace
}

case "${1:-wheel}" in
    cpp)
        build_cpp
        ;;
    wheel)
        build_cpp
        cd "${SCRIPT_DIR}"
        pip wheel . --no-deps -w dist/
        echo "=== Wheel:"
        ls -la dist/*.whl
        ;;
    install)
        build_cpp
        cd "${SCRIPT_DIR}"
        pip install --no-deps --force-reinstall .
        "${PYTHON_EXE}" -c "from wy_transpiler import transpile_from_qasm; print('OK:', transpile_from_qasm.__name__)"
        ;;
    *)
        echo "Usage: $0 [cpp|wheel|install]"
        exit 1
        ;;
esac
