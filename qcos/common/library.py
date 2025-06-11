#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import fnmatch
import importlib
import inspect
import logging
import os
import pkgutil

from datetime import datetime

logger = logging.getLogger(__name__)


class Library(object):
    """
    Library
    """
    @staticmethod
    def create_pid_file(file_path):
        """
        Crete pid file

        :param file_path: file path
        """
        try:
            pid = os.getpid()
            with open(file_path, "w") as f:
                f.write(str(pid))
        except Exception as e:
            print(f"Unable to create pid file: {file_path}\n{e}")

    @staticmethod
    def find_dirs(base_dir="/", pattern="*", recursive=False):
        """
        Find all dirs

        :param base_dir: base dir to search
        :param pattern: match pattern
        :param recursive: recursive search
        :return: dir list
        """
        dirs = []
        if os.path.isdir(base_dir):
            dirs.append(base_dir)
            if recursive:
                for root, dir_names, filenames in os.walk(base_dir):
                    for dir_name in fnmatch.filter(dir_names, pattern):
                        _dir_name = os.path.join(root, dir_name)
                        if _dir_name not in dirs:
                            dirs.append(_dir_name)
        return dirs

    @staticmethod
    def find_files(base_dir, pattern="*", recursive=False, exclusives=None):
        """
        Find files under given dir

        :param base_dir: base dir to search
        :param pattern: match pattern
        :param recursive: recursive search
        :param exclusives: filename to exclude
        :return: file list
        """
        files = []
        if recursive:
            for root, dirnames, filenames in os.walk(base_dir):
                for filename in fnmatch.filter(filenames, pattern):
                    file_path = os.path.join(root, filename)
                    skip = False
                    if exclusives:
                        for exc in exclusives:
                            if exc in file_path:
                                skip = True
                                continue
                    if not skip:
                        files.append(file_path)
        else:
            if not os.path.isdir(base_dir):
                return files
            list_of_files = os.listdir(base_dir)
            for entry in list_of_files:
                if fnmatch.fnmatch(entry, pattern):
                    files.append(os.path.join(base_dir, entry))
        return files

    @staticmethod
    def mkdir(dir_name):
        """
        Create dir

        :param dir_name: dir name
        :return: True or False
        """
        if not os.path.exists(dir_name):
            os.mkdir(dir_name)
            return True
        return False

    @staticmethod
    def mkdirs(dir):
        """
        Create dirs

        :param dir: dir name
        """
        sub_path = os.path.dirname(dir)
        if not os.path.exists(sub_path):
            Library.mkdirs(sub_path)
        if not os.path.exists(dir):
            os.mkdir(dir)

    @staticmethod
    def rm_file(file):
        """
        remove file

        :param file: file path
        :return: True or False
        """
        if os.path.isfile(file):
            try:
                os.remove(file)
            except Exception as e:
                pass
        return True

    @staticmethod
    def import_classes(
            pkg_dir, base_module_name="drivers", base_dir=None,
            base_class=None):
        """
        Import class from package dir

        :param pkg_dir: package dir
        :param base_module_name: base module name
        :param base_dir: base dir
        :param base_class: base class
        :return: class dict
        """
        classes = {}
        for (module_loader, name, is_pkg) in pkgutil.iter_modules([pkg_dir]):
            module_path = module_loader.path.replace(base_dir, "")
            module_name = (f"{base_module_name}"
                           f"{module_path.replace('/', '.')}.{name}")
            module = importlib.import_module(module_name)
            for _, obj in inspect.getmembers(module):
                if inspect.isclass(obj):
                    if issubclass(obj, base_class) and obj != base_class:
                        classes[obj.__name__] = obj
        return classes

    @staticmethod
    def get_current_datetime():
        """
        Get current datetime

        :return: datetime in string format: %Y-%m-%dT%H:%M:%S.%fZ
        """
        now = datetime.now()
        return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def validate_values_enum(value, argument_name, value_list):
        """
        Validate values for enum

        :param value: value
        :param argument_name: argument name
        :param value_list: valid value list
        :return: True or False
        """
        if value not in value_list:
            return (False, [f"Invalid argument: {argument_name}={value}. "
                            f"valid values: {', '.join(value_list)}"])
        return True, None

    @staticmethod
    def validate_values_range(
            value, argument_name, min_value=None, max_value=None):
        """
        Validate values for int range

        :param value: value
        :param argument_name: argument name
        :param min_value: minimum value
        :param max_value: maximum value
        :return: True or False
        """
        err_msgs = []
        if min_value:
            if value < min_value:
                err_msgs.append(f"Invalid argument: {argument_name}={value}. "
                                f"value should >= {min_value}")
        if max_value:
            if value > max_value:
                err_msgs.append(f"Invalid argument: {argument_name}={value}. "
                                f"value should <= {max_value}")
        if err_msgs:
            return False, err_msgs
        return True, None

    @staticmethod
    def validate_values_list(value, argument_name, value_type):
        """
        Validate values for list

        :param value: value
        :param argument_name: argument name
        :param value_type: data type of value
        :return: True or False
        """
        if not isinstance(value, list):
            return (False, [f"Invalid argument: {argument_name}={value}. "
                            f"type: list is required"])
        for _value in value:
            if not isinstance(_value, value_type):
                return (False, [f"Invalid argument: {argument_name}={value}. "
                                f"valid list element value type: {value_type}"])
        return True, None
