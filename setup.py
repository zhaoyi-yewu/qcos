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

from pathlib import Path
from setuptools import setup, find_packages


def get_files(base_dirs, dest_dir_prefix="", exclude=[]):
    """Get files from base_dirs.

    Args:
        base_dirs: base dir list
        dest_dir_prefix: dest dir prefix
        exclude: exclude files

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
            if file_path.is_file() and file_path.name not in exclude:
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
            for file_path in dir_path.glob("*"):
                if file_path.is_file() and file_path.name not in exclude:
                    file_list.append(str(file_path))
            if file_list:
                data_files.append((target_dir, file_list))
    return data_files


# Include package data
setup(
    packages=find_packages(where="src"),
    include_package_data=True,
    data_files=get_files(["etc/qcos", "samples"],
                         dest_dir_prefix="share/wy_qcos/")
)
