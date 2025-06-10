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

import logging
import os

from datetime import datetime


logger = logging.getLogger(__name__)


class Library(object):
    """
    Library class
    """
    @staticmethod
    def create_pid_file(file_path):
        try:
            pid = os.getpid()
            with open(file_path, "w") as f:
                f.write(str(pid))
        except Exception as e:
            print(f"Unable to create pid file: {file_path}")

    @staticmethod
    def mkdir(dir):
        if not os.path.exists(dir):
            os.mkdir(dir)
            return True
        return False

    @staticmethod
    def mkdirs(dir):
        sub_path = os.path.dirname(dir)
        if not os.path.exists(sub_path):
            Library.mkdirs(sub_path)
        if not os.path.exists(dir):
            os.mkdir(dir)

    @staticmethod
    def rm_file(file):
        if os.path.isfile(file):
            try:
                os.remove(file)
            except Exception as e:
                pass
        return True

    @staticmethod
    def get_current_datetime():
        now = datetime.now()
        return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def validate_values_enum(value, argument_name, value_list):
        """
        Validate values for enum parameter
        :param value: value
        :param argument_name: argument name
        :param value_list: valid value list
        :return: success, error message
        """
        if value not in value_list:
            return (False, [f"Invalid argument: {argument_name}: {value}, "
                           f"valid values: {','.join(value_list)}"])
        return True, None

    @staticmethod
    def validate_values_range(
            value, argument_name, min_value=None, max_value=None):
        """
        Validate values for range parameter
        :param value: value
        :param argument_name: argument name
        :param min_value: minimum range value
        :param min_value: maximum range value
        :return: success, error message
        """
        err_msgs = []
        if min_value:
            if value < min_value:
                err_msgs.append(f"Invalid argument: {argument_name}: {value}, "
                           f"value should >= {min_value}")
        if max_value:
            if value > max_value:
                err_msgs.append(f"Invalid argument: {argument_name}: {value}, "
                           f"value should <= {max_value}")
        if err_msgs:
            return False, err_msgs
        return True, None
