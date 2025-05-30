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


class Config(object):

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
    API_SERVER_LISTEN_ADDR = "unix://var/run/qcos/qcos-api.sock"
    API_LOG_FILE = "/var/log/qcos/qcos-api.log"

    # [SSL]
    USE_SSL = False
    CERT_FILE = None
    KEY_FILE = None
