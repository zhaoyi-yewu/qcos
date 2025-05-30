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

import configparser
import logging
import os

logger = logging.getLogger(__name__)


class Library(object):
    """
    Library class
    """
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
            except:
                pass
        return True

    @classmethod
    def parse_config_file(cls, config_file):
        if not os.path.isfile(config_file):
            raise Exception("Can't find config file: %s" % config_file)

        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(config_file)
        except Exception as e:
            raise Exception("Error reading config file: %s\nTrace:\n%s" % (config_file, e))
