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

from collections import OrderedDict
from pathlib import Path

from wy_qcos.common import errors
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library


class Config:
    """Config class."""

    # General configs
    DAEMON = False

    # [DEFAULT]
    DEBUG = False
    # [GLOBAL CONFIG] max jobs (all status)
    MAX_JOBS = 10000
    # [GLOBAL CONFIG] max queued+running jobs
    MAX_QUEUED_JOBS = 1000
    # [GLOBAL CONFIG] default venv base dir
    VENV_DIR = "/var/lib/qcos/venv"

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

    # [REDIS]
    # REDIS server ip
    REDIS_SERVER_IP = Constant.DEFAULT_REDIS_SERVER_IP
    # REDIS server port
    REDIS_SERVER_PORT = Constant.DEFAULT_REDIS_SERVER_PORT

    # [DATABASE]
    # eg. without db: fake,
    # pg: "postgresql+pg8000://postgres:${password}@100.78.61.22:5432/qcos"
    # sqlite: "sqlite:////var/qcos/db/qcos.db"
    QCOS_DATABASE_CONNECTION_URL = "fake"

    # [USERS]
    ENABLE_USER_MGMT = True
    PASSWORD_EXPIRY_DAYS = 90
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    ADMIN_PASSWORD = None

    # [LOG]
    # api log file
    API_LOG_FILE = "/var/log/qcos/qcos-api.log"
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

    # [PREFECT]
    PREFECT_SERVER_DATABASE_CONNECTION_URL = (
        "sqlite+aiosqlite:///var/qcos/db/prefect.db"
    )
    PREFECT_API_URL = "http://127.0.0.1:4200/api"
    PREFECT_WORKER_QUERY_SECONDS = 30
    PREFECT_WORKER_PREFETCH_SECONDS = 1
    PREFECT_WORKER_HEARTBEAT_SECONDS = 30
    PREFECT_LOCAL_STORAGE_PATH = "/var/qcos/storage"
    PREFECT_LOGGING_LEVEL = "INFO"

    # valid sections
    VALID_SECTIONS = [
        "DEFAULT",
        "VIRT",
        "API_SERVER",
        "REDIS",
        "DATABASE",
        "USERS",
        "LOG",
        "SSL",
        "PREFECT",
        "DEVICES",
    ]

    # extra configs from .toml files
    _EXTRA_CONFIGS = {}

    # driver env configs
    _DRIVER_ENV_CONFIGS = {}

    @classmethod
    def load_config_file(cls, config_file, extra_config=False):
        """Parse a config file.

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
                    if section not in cls._EXTRA_CONFIGS:
                        cls._EXTRA_CONFIGS[section] = {}
                    cls._EXTRA_CONFIGS[section][key] = decrypt_value(
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
                        if section not in cls._EXTRA_CONFIGS:
                            cls._EXTRA_CONFIGS[section] = {}
                        cls._EXTRA_CONFIGS[section][key] = decrypt_value(
                            value, f"{section}:{key}"
                        )

    @classmethod
    def load_driver_env_file(cls, config_file):
        """Load and validate driver env configuration file.

        Args:
            config_file: config file path
        """
        driver_deps_file_path = Path(config_file).parent
        _configs = {}
        configs = {}
        success, err_msg, _configs = Library.read_toml_file(config_file)
        if not success:
            cls._DRIVER_ENV_CONFIGS = configs
            return

        # sort dict
        # dicts contain key: "copy_from" will put at the end of configs
        non_copy_items = []
        copy_items = []
        for key, value in _configs.items():
            if isinstance(value, dict) and "copy_from" in value:
                copy_from_value = value["copy_from"]
                if copy_from_value not in _configs:
                    raise Exception(
                        f"Invalid copy_from: {copy_from_value} in [{key}]"
                    )
                ref_driver_name = copy_from_value
                ref_driver = _configs[ref_driver_name]
                if "copy_from" in ref_driver:
                    raise Exception(
                        f"Invalid copy_from: {ref_driver_name} in [{key}]. "
                        f"Can't reference the driver: {ref_driver_name}"
                    )
                copy_items.append((key, value))
            else:
                non_copy_items.append((key, value))
        sorted_items = non_copy_items + copy_items
        configs = OrderedDict(sorted_items)
        for driver_class, driver_info in configs.items():
            if "copy_from" in driver_info:
                continue
            if "deps_filepaths" not in driver_info:
                raise Exception(
                    f"[{driver_class}] ‘deps_filepaths’ must be specified"
                )
            if "envs" not in driver_info:
                raise Exception(f"[{driver_class}] ‘envs’ must be specified")
            deps_filepaths = driver_info["deps_filepaths"]
            deps_filepaths_list = []
            for deps_filepath in deps_filepaths:
                deps_abs_filepath = (
                    driver_deps_file_path / deps_filepath
                ).resolve()
                deps_filepaths_list.append(str(deps_abs_filepath))
            driver_info["deps_filepaths"] = deps_filepaths_list
        cls._DRIVER_ENV_CONFIGS = configs

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
    def get_configs(cls, mask_password=False):
        configs = {}
        cls_vars = vars(cls)
        for k, v in cls_vars.items():
            if (
                k.startswith("__")
                or k.startswith("_")
                or isinstance(v, classmethod)
            ):
                continue
            configs[k] = v
        if mask_password:
            configs = Library.mask_password(configs)
        return configs

    @classmethod
    def get_extra_configs(cls):
        """Get extra configs.

        Returns:
            extra configs
        """
        return cls._EXTRA_CONFIGS

    @classmethod
    def get_driver_env_configs(cls):
        """Get driver env configs.

        Returns:
            driver env configs
        """
        return cls._DRIVER_ENV_CONFIGS

    @classmethod
    def show_info(cls):
        """Show class variables."""
        configs = cls.get_configs(mask_password=True)
        outputs = ["[Configs]"]
        for k, v in configs.items():
            outputs.append(f"{k:<20}: {v}")
        return "\n" + "\n".join(outputs) + "\n"
