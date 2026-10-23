#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Lightweight standalone build for the C++ transpiler nanobind extension.

This setup.py drives the CMake build in ``src_cpp/transpiler_cpp/`` and
produces a wheel containing:
  - wy_transpiler/high_performance.*.so  (the full nanobind module)
  - wy_transpiler/high_performance.pyi    (hand-written minimal stubs)

The .pyi only documents the transpile / optimize / parse / QASM subset;
the .so still exports the full API but __init__.py __all__ limits star-imports.
It does NOT depend on the full wy-qcos package or its dependency tree.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext as _build_ext

# -- locate the C++ source -------------------------------------------------
# This file lives at src_cpp/packages/wy_transpiler/setup.py. The C++ tree
# transpiler_cpp is two parents up, under src_cpp/.
_HERE = Path(__file__).resolve()
_CPP_SOURCE_DIR = _HERE.parents[2] / "transpiler_cpp"


class CMakeExtension(Extension):
    """A no-op Extension whose build is delegated to CMake."""

    def __init__(self, name):
        super().__init__(name, sources=[])


class CMakeBuildExt(_build_ext):
    """Run the CMake configure/build for the nanobind extension."""

    def build_extension(self, ext):
        ext_path = Path(self.get_ext_fullpath(ext.name))
        ext_path.parent.mkdir(parents=True, exist_ok=True)

        dist_dir = _CPP_SOURCE_DIR / "dist"
        build_dir = Path(self.build_temp) / "cmake_build"
        build_dir.mkdir(parents=True, exist_ok=True)
        subprocess.check_call([  # noqa: S603, S607
            "cmake", "-S", str(_CPP_SOURCE_DIR), "-B", str(build_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DUSE_PYQCOS=ON",
            f"-DPython_EXECUTABLE={sys.executable}",
        ])
        n = os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL")
        jobs = int(n) if n and n.isdigit() else os.cpu_count() or 1
        subprocess.check_call([  # noqa: S603, S607
            "cmake", "--build", str(build_dir),
            "--target", "high_performance", "--config", "Release",
            "--parallel", str(jobs),
        ])
        so = sorted(dist_dir.rglob("high_performance*.so"))

        if not so:
            raise RuntimeError(
                f"high_performance .so not found under {dist_dir}")
        shutil.copyfile(str(so[0]), str(ext_path))


setup(
    ext_modules=[CMakeExtension("wy_transpiler.high_performance")],
    cmdclass={"build_ext": CMakeBuildExt},
)
