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

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext as _build_ext


def get_files(base_dirs, dest_dir_prefix="",
              exclude_files=[], exclude_dirs=[]):
    """Get files from base_dirs.

    Args:
        base_dirs: base dir list
        dest_dir_prefix: dest dir prefix
        exclude_files: exclude files
        exclude_dirs: exclude dirs

    Returns:
        files tuple list
    """
    data_files = []

    for base_dir in base_dirs:
        _base_dir = Path(base_dir)

        # check dir exists
        if not _base_dir.exists() or not _base_dir.is_dir():
            return data_files

        # get files under base_dir
        file_list = []
        for file_path in _base_dir.glob("*"):
            if file_path.is_dir():
                continue

            if file_path.is_file():
                is_match_exclude_file = False
                for exclude_file in exclude_files:
                    if re.match(exclude_file, str(file_path)):
                        is_match_exclude_file = True
                if not is_match_exclude_file:
                    file_list.append(str(file_path))
        if file_list:
            target_dir = f"{dest_dir_prefix}{_base_dir}".replace("../", "")
            data_files.append((target_dir, file_list))

        # get files under base_dir recursively
        for dir_path in _base_dir.rglob("*"):
            if not dir_path.is_dir():
                continue
            target_dir = f"{dest_dir_prefix}{dir_path}".replace("../", "")
            file_list = []
            is_match_exclude_dir = False
            for exclude_dir in exclude_dirs:
                if re.match(exclude_dir, str(dir_path)):
                    is_match_exclude_dir = True
            if is_match_exclude_dir:
                continue
            for file_path in dir_path.glob("*"):
                if file_path.is_file():
                    is_match_exclude_file = False
                    for exclude_file in exclude_files:
                        if re.match(exclude_file, str(file_path)):
                            is_match_exclude_file = True
                    if not is_match_exclude_file:
                        file_list.append(str(file_path))
            if file_list:
                data_files.append((target_dir, file_list))
    return data_files


# Include package data
data_files = get_files(["etc/qcos", "samples"],
                       dest_dir_prefix="share/wy_qcos/",
                       exclude_dirs=["samples/qasm/benchpress"])  # too large

# Add database migration files
db_migration_files = get_files(["src/wy_qcos/db/migration"],
                               dest_dir_prefix="share/wy_qcos/")
data_files.extend(db_migration_files)
data_files.append(("tests", ["src/wy_qcos/tests/pytest.ini"]))
data_files.append(("share/wy_qcos/cicd/", ["cicd/run-tests.sh"]))
data_files.append(("share/wy_qcos/scripts/", ["build-scripts/db-manager.sh"]))


# Build the C++ extension (high_performance) via CMake. Declaring it as an
# Extension makes setuptools treat the .so as a real compiled extension, so the
# wheel gets a correct platform/ABI tag (e.g. cp314-cp314-macosx_..._x86_64)
# instead of py3-none-any. No package_data / MANIFEST.in needed.
_PROJECT_ROOT = Path(__file__).parent.resolve()
_CPP_SOURCE_DIR = _PROJECT_ROOT / "src_cpp" / "transpiler_cpp"


class CMakeExtension(Extension):
    """Extension built by CMake."""

    def __init__(self, name):
        super().__init__(name, sources=[])


class CMakeBuildExt(_build_ext):
    """Run CMake configure/build for the extension."""

    def build_extension(self, ext):
        ext_path = Path(self.get_ext_fullpath(ext.name))
        ext_path.parent.mkdir(parents=True, exist_ok=True)

        build_dir = Path(self.build_temp) / "cmake_high_performance"
        build_dir.mkdir(parents=True, exist_ok=True)

        subprocess.check_call(
            [
                "cmake",
                "-S",
                str(_CPP_SOURCE_DIR),
                "-B",
                str(build_dir),
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
                "-DUSE_PYQCOS=ON",
                f"-DPython_EXECUTABLE={sys.executable}",
            ]
        )
        subprocess.check_call(
            [
                "cmake",
                "--build",
                str(build_dir),
                "--target",
                "high_performance",
                "--config",
                "Release",
                "--parallel",
                str(self._parallel_jobs()),
            ]
        )

        built = self._find_built_so()
        shutil.copyfile(str(built), str(ext_path))

    @staticmethod
    def _find_built_so():
        dist_dir = _CPP_SOURCE_DIR / "dist"
        candidates = sorted(dist_dir.rglob("high_performance*.so"))
        if not candidates:
            raise RuntimeError(
                f"high_performance .so not found under {dist_dir} "
                "(did the CMake build succeed?)"
            )
        return candidates[0]

    @staticmethod
    def _parallel_jobs():
        n = os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL")
        if n and n.isdigit():
            return int(n)
        return os.cpu_count() or 1


setup(
    packages=find_packages(where="src"),
    include_package_data=True,
    ext_modules=[CMakeExtension("wy_qcos.transpiler.high_performance")],
    cmdclass={"build_ext": CMakeBuildExt},
    data_files=data_files,
)
