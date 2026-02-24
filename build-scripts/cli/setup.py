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
# -------

import re
from pathlib import Path
from setuptools import setup, find_packages


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
data_files = get_files(["../../samples"],
                       dest_dir_prefix="share/wy_qcos_client/",
                       exclude_dirs=["samples/qasm/benchpress"])  # too large
data_files.append(("tests", ["../../src/wy_qcos_client/tests/pytest.ini"]))
data_files.append(("share/wy_qcos_client/cicd/", ["../../cicd/run-tests.sh"]))
setup(
    packages=find_packages(where="../../src"),
    include_package_data=True,
    data_files=data_files
)
