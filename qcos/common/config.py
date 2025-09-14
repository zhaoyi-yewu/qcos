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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from qcos.common import errors
from qcos.common.library import Library


class Config:
    """
    Config class
    """
    # General configs
    VERSION = "1.0.0"
    DAEMON = False
    API_VERSION_V1 = "v1"
    API_VERSION = API_VERSION_V1
    PROGRAM_NAME = "WuYue-QCOS"
    PROGRAM_AUTHOR = "CMSS"
    PLATFORM_VERSION = f"五岳量子计算操作系统(qcos) v{VERSION}"

    # [DEFAULT]
    DEBUG = False
    WORKERS = 8

    # [API_SERVER]
    API_SERVER_LISTEN_IP = "127.0.0.1"
    API_SERVER_LISTEN_PORT = 18400
    API_LOG_FILE = "/var/log/qcos/qcos-api.log"
    PREFECT_LOG_FILE = "/var/log/qcos/qcos-prefect.log"

    # [SSL]
    USE_SSL = False
    CERT_FILE = None
    KEY_FILE = None

    # [DEVICES]
    DEVICE_LIST = []

    # extra configs from .toml files
    EXTRA_CONFIGS = {}


    @classmethod
    def parse_toml_file(cls, config_file, extra_config=False):
        """
        Parse a TOML file

        :param config_file: config file
        :param extra_config: is extra config
        """
        success, err_msg, config_values = Library.read_toml_file(config_file)
        config_values = config_values.unwrap()
        if not success:
            raise errors.GenericException(err_msg)
        if extra_config:
            for section, options in config_values.items():
                for option in options.items():
                    key, value = option
                    if section not in cls.EXTRA_CONFIGS:
                        cls.EXTRA_CONFIGS[section] = {}
                    cls.EXTRA_CONFIGS[section][key] = value
        else:
            for section, options in config_values.items():
                for option in options.items():
                    key, value = option
                    key_upper = key.upper()
                    if hasattr(cls, key_upper):
                        setattr(cls, key_upper, value)
                    else:
                        raise errors.GenericException(
                            f"Can't find config key: {key}")

    @classmethod
    def validate(cls):
        # remove duplicated devices
        cls.DEVICE_LIST = Library.remove_duplicates(cls.DEVICE_LIST)
        success, err_msg = Library.validate_schema(cls.DEVICE_LIST,
                                                   [str],
                                                   allow_none=False)
        if not success:
            raise errors.GenericException("Device list must be list of str")

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
