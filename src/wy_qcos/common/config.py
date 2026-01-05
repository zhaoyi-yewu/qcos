#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

from wy_qcos.common import errors
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.common.qcos_version import QcosVersion


class Config:
    """Config class."""

    # General configs
    DAEMON = False
    API_VERSION_V1 = "v1"
    API_VERSION = API_VERSION_V1
    PROGRAM_NAME = "WuYue-QCOS"
    PROGRAM_AUTHOR = "CMSS"
    PLATFORM_NAME = "五岳量子计算操作系统(QCOS)"
    PLATFORM_VERSION = f"{PLATFORM_NAME} v{QcosVersion.VERSION}"
    COPYRIGHT = "2024-2026 中移（苏州）软件技术有限公司"

    # [DEFAULT]
    DEBUG = False
    # [GLOBAL CONFIG] max jobs (all status)
    MAX_JOBS = 10000
    # [GLOBAL CONFIG] max queued+running jobs
    MAX_QUEUED_JOBS = 1000

    # [VIRT]
    # enable virtualization
    ENABLE_VIRT = False
    # [GLOBAL CONFIG] max jobs for virtual instance
    MAX_JOBS_PER_VIRTUAL_INSTANCE = 10
    # salt for pwd/encryption
    PASSWORD_SALT = ""

    # [API_SERVER]
    # API workers
    API_WORKERS = 8
    # API server listen ip
    API_SERVER_LISTEN_IP = Constant.DEFAULT_API_SERVER_LISTEN_IP
    # API server listen port
    API_SERVER_LISTEN_PORT = Constant.DEFAULT_API_SERVER_LISTEN_PORT

    # [LOG]
    # api log file
    API_LOG_FILE = "/var/log/qcos/qcos-api.log"
    # prefect log file
    PREFECT_LOG_FILE = "/var/log/qcos/qcos-engine.log"
    # log format
    LOG_FORMAT = (
        "%(asctime)s %(levelname)s %(filename)s:%(lineno)s %(message)s"
    )
    # log rotate, max_size (MB). default: 10MB
    LOG_ROTATE_MAX_SIZE_MB = 10
    # log rotate, backup count. default: 10
    LOG_ROTATE_BACKUP_COUNT = 10
    # log rotate, compression. default: true
    LOG_ROTATE_COMPRESSION = True

    # [SSL]
    # Enable HTTPS for API server
    USE_SSL = False
    # SSL CERT_FILE
    # eg. CERT_FILE = "/etc/qcos/ssl/ssl.crt"
    CERT_FILE = None
    # SSL KEY_FILE
    # eg. KEY_FILE = "/etc/qcos/ssl/ssl.key"
    KEY_FILE = None
    # SSL CACERT_FILE (Optional)
    # eg. CACERT_FILE = "/etc/qcos/ssl/cacert.pem"
    CACERT_FILE = None

    # [DEVICES]
    DEVICE_LIST = []

    # valid sections
    VALID_SECTIONS = ["DEFAULT", "VIRT", "API_SERVER", "LOG", "SSL", "DEVICES"]

    # extra configs from .toml files
    EXTRA_CONFIGS = {}

    @classmethod
    def parse_toml_file(cls, config_file, extra_config=False):
        """Parse a TOML file.

        Args:
            config_file: config file
            extra_config: is extra config (Default value = False)
        """

        def decrypt_value(value, section_key):
            decrypted_value = value
            if isinstance(value, str) and value.startswith(
                Constant.ENCRYPTION_PREFIX
            ):
                success, err_msg, decrypted_value = Library.decrypt_text(
                    value,
                    encryption_prefix=Constant.ENCRYPTION_PREFIX,
                    fernet_key=Constant.DEFAULT_FERNET_KEY,
                )
                if not success:
                    raise errors.GenericException(
                        f"Can't decrypt text: {value} ({section_key})"
                    )
            return decrypted_value

        success, err_msg, config_values = Library.read_toml_file(config_file)
        if not success:
            raise errors.GenericException(
                f"Error in config file: {config_file}. Reason: {err_msg}"
            )
        config_values = config_values.unwrap()
        if extra_config:
            for section, options in config_values.items():
                for option in options.items():
                    key, value = option
                    if section not in cls.EXTRA_CONFIGS:
                        cls.EXTRA_CONFIGS[section] = {}
                    cls.EXTRA_CONFIGS[section][key] = decrypt_value(
                        value, f"{section}:{key}"
                    )
        else:
            for section, options in config_values.items():
                if section in Config.VALID_SECTIONS:
                    for option in options.items():
                        key, value = option
                        key_upper = key.upper()
                        if hasattr(cls, key_upper):
                            setattr(
                                cls, key_upper, decrypt_value(value, key_upper)
                            )
                        else:
                            raise errors.GenericException(
                                f"Can't find config key: {key}"
                            )
                else:
                    for option in options.items():
                        key, value = option
                        if section not in cls.EXTRA_CONFIGS:
                            cls.EXTRA_CONFIGS[section] = {}
                        cls.EXTRA_CONFIGS[section][key] = decrypt_value(
                            value, f"{section}:{key}"
                        )

    @classmethod
    def validate(cls):
        # remove duplicated devices
        cls.DEVICE_LIST = Library.remove_duplicates(cls.DEVICE_LIST)
        success, err_msg = Library.validate_schema(
            cls.DEVICE_LIST, [str], allow_none=False
        )
        if not success:
            raise errors.GenericException("Device list must be list of str")

    @classmethod
    def show_info(cls):
        """Show class variables."""
        configs = {}
        cls_vars = vars(cls)
        for k, v in cls_vars.items():
            if not k.startswith("__") and not isinstance(v, classmethod):
                configs[k] = v
        configs = Library.mask_password(configs)
        outputs = ["[Configs]"]
        for k, v in configs.items():
            outputs.append(f"{k:<20}: {v}")
        return "\n" + "\n".join(outputs) + "\n"
