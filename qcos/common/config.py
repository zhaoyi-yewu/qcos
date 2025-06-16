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
import os

from qcos.common import errors


class Config:
    """
    Config class
    """
    # General configs
    VERSION = "1.0.0"
    DAEMON = False
    API_VERSION = "v1"
    PROGRAM_NAME = "WuYue-QCOS"
    PROGRAM_AUTHOR = "CMSS"
    PLATFORM_VERSION = f"五岳量子计算操作系统(qcos) v{VERSION}"

    # [DEFAULT]
    DEBUG = False
    WORKERS = 4

    # [API_SERVER]
    API_SERVER_LISTEN_IP = "127.0.0.1"
    API_SERVER_PORT = 18400
    API_LOG_FILE = "/var/log/qcos/qcos-api.log"

    # [SSL]
    USE_SSL = False
    CERT_FILE = None
    KEY_FILE = None

    # [DECOMPOSE_RULE]
    DECOMPOSE_RULE = None

    EXTRA_CONFIGS = {}

    @classmethod
    def parse_config_file(cls, config_file, extra_config=False):
        """
        Parse config file

        :param config_file: Config file path
        :param extra_config: Extra configs for drivers
        """
        if not os.path.isfile(config_file):
            raise errors.GenericException(
                f"Can't find config file: {config_file}")

        config_parser = configparser.ConfigParser()
        try:
            config_parser.read(config_file)
        except errors.Exception as e:
            raise errors.GenericException(
                f"Error reading config file: {config_file}")

        if extra_config:
            for section, options in config_parser.items():
                for option in options.items():
                    key, value = option
                    if section not in cls.EXTRA_CONFIGS:
                        cls.EXTRA_CONFIGS[section] = {}
                    cls.EXTRA_CONFIGS[section][key] = value
        else:
            for section, options in config_parser.items():
                for option in options.items():
                    key, value = option
                    key_upper = key.upper()
                    if hasattr(cls, key_upper):
                        _value = getattr(cls, key_upper)
                        _type = type(_value)
                        if _value is None:
                            raise errors.Exception(
                                f"Invalid key type: {key}, "
                                f"None is not allowed")
                        converted_value = _type(value)
                        if _type is bool:
                            converted_value = value.lower() == "true"
                        setattr(cls, key_upper, converted_value)
                    else:
                        raise errors.Exception(
                            f"Can't find config key: {key}")

    @classmethod
    def show_info(cls):
        """
        Show class variables.
        """
        outputs = ["[Configs]"]
        for k, v in vars(cls).items():
            if not k.startswith("__") and not isinstance(v, classmethod):
                if v:
                    outputs.append(f"{k:<20}: {v}")
        return "\n".join(outputs) + "\n"
