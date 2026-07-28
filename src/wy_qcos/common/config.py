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
from typing import Any, Literal
from pydantic import BaseModel, Field, ValidationError, ConfigDict

from wy_qcos.common import errors
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import _s, Library


# ==================== Section Models ====================


class DefaultSection(BaseModel):
    """DEFAULT section configuration."""

    model_config = ConfigDict(extra="forbid")

    DEBUG: bool = Field(default=False, description="Debug mode flag")
    MAX_JOBS: int = Field(
        default=-1,
        ge=-1,
        description="Maximum number of jobs (all status). "
        "Set to -1 for unlimited.",
    )
    MAX_QUEUED_JOBS: int = Field(
        default=-1,
        ge=-1,
        description="Maximum number of queued+running jobs. "
        "Set to -1 for unlimited.",
    )
    AUTH_MODE: Literal["no", "jwt", "virtual_instance"] = Field(
        default=Constant.AUTH_MODE_NO,
        description="Authentication mode: 'no', 'jwt', or 'virtual_instance'",
    )
    JOB_SCAN_INTERVAL: int = Field(
        default=60,
        ge=1,
        description="Job scan interval in minutes",
    )
    JOB_EXPIRE_DAYS: int | float = Field(
        default=-1,
        ge=-1,
        description="Job expiration days (supports int and float), "
        "jobs older than this will be auto-deleted. "
        "Set to -1 to disable expiration (never auto-delete).",
    )
    FLOW_EXPIRE_DAYS: int | float = Field(
        default=-1,
        ge=-1,
        description="Completed Prefect flow-run expiration days "
        "(supports int and float). Completed flow-runs of the "
        "'job-flow' older than this will be auto-deleted. "
        "Set to -1 to disable (never auto-delete).",
    )
    GC_INTERVAL: int | float = Field(
        default=1,
        ge=-1,
        description="Garbage collection interval in days. Periodically "
        "runs gc.collect() on all 3 generations and malloc_trim(0) "
        "to release freed memory back to the OS. "
        "Set to -1 to disable periodic GC. Default: 1 (daily).",
    )
    VENV_DIR: str = Field(
        default="/var/lib/qcos/venv",
        description="Default virtual environment base directory",
    )


class APIServerSection(BaseModel):
    """API_SERVER section configuration."""

    model_config = ConfigDict(extra="forbid")

    API_WORKERS: int = Field(
        default=8, ge=1, le=256, description="Number of API workers (1-256)"
    )
    API_SERVER_LISTEN_IP: str = Field(
        default=Constant.DEFAULT_API_SERVER_LISTEN_IP,
        description="API server listen IP ('' for all addresses)",
    )
    API_SERVER_LISTEN_PORT: int = Field(
        default=Constant.DEFAULT_API_SERVER_LISTEN_PORT,
        ge=1024,
        le=65535,
        description="API server listen port (1024-65535)",
    )


class MetricsServerSection(BaseModel):
    """METRICS_SERVER section configuration."""

    model_config = ConfigDict(extra="forbid")

    METRICS_SERVER_LISTEN_IP: str = Field(
        default=Constant.DEFAULT_METRICS_SERVER_LISTEN_IP,
        description="Metrics server listen IP ('' for all addresses)",
    )
    METRICS_SERVER_LISTEN_PORT: int = Field(
        default=Constant.DEFAULT_METRICS_SERVER_LISTEN_PORT,
        ge=1024,
        le=65535,
        description="Metrics server listen port (1024-65535)",
    )


class PrefectSection(BaseModel):
    """PREFECT section configuration."""

    model_config = ConfigDict(extra="forbid")

    PREFECT_API_URL: str | None = Field(
        default="http://127.0.0.1:4200/api", description="Prefect API URL"
    )
    PREFECT_SERVER_DATABASE_CONNECTION_URL: str = Field(
        default="sqlite+aiosqlite:////var/qcos/db/prefect.db?timeout=30&journal_mode=WAL",
        description="Prefect database connection URL",
        json_schema_extra={"sensitive": True, "db_connection_url": True},
    )
    PREFECT_WORKER_QUERY_SECONDS: int = Field(
        default=30,
        ge=1,
        description="Prefect worker query interval in seconds",
    )
    PREFECT_WORKER_PREFETCH_SECONDS: int = Field(
        default=1,
        ge=1,
        description="Prefect worker prefetch interval in seconds",
    )
    PREFECT_WORKER_HEARTBEAT_SECONDS: int = Field(
        default=30,
        ge=1,
        description="Prefect worker heartbeat interval in seconds",
    )
    PREFECT_LOCAL_STORAGE_PATH: str = Field(
        default="/var/qcos/storage", description="Prefect local storage path"
    )
    PREFECT_LOGGING_LEVEL: Literal[
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ] = Field(
        default="INFO",
        description="Prefect logging level"
        " (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )


class TranspilerSection(BaseModel):
    """TRANSPILER section configuration."""

    model_config = ConfigDict(extra="forbid")

    DEBUG: bool = Field(
        default=False, description="Enable transpiler perf logging"
    )


class RedisSection(BaseModel):
    """REDIS section configuration."""

    model_config = ConfigDict(extra="forbid")

    REDIS_SERVER_IP: str = Field(
        default=Constant.DEFAULT_REDIS_SERVER_IP,
        description="Redis server IP address",
    )
    REDIS_SERVER_PORT: int = Field(
        default=Constant.DEFAULT_REDIS_SERVER_PORT,
        ge=1024,
        le=65535,
        description="Redis server port (1024-65535)",
    )


class DatabaseSection(BaseModel):
    """DATABASE section configuration."""

    model_config = ConfigDict(extra="forbid")

    QCOS_DATABASE_CONNECTION_URL: str = Field(
        default="sqlite:////var/qcos/db/qcos.db?timeout=30&journal_mode=WAL",
        description="QCOS database connection URL (sqlite or postgresql)",
        json_schema_extra={"sensitive": True, "db_connection_url": True},
    )

    def validate_url(self) -> None:
        """Validate database URL supports only sqlite or postgresql."""
        url = self.QCOS_DATABASE_CONNECTION_URL.lower()
        if not (url.startswith("sqlite") or url.startswith("postgresql")):
            raise ValueError(
                f"Invalid database URL: {self.QCOS_DATABASE_CONNECTION_URL}. "
                "Only 'sqlite' and 'postgresql' are supported."
            )


class UsersSection(BaseModel):
    """USERS section configuration."""

    model_config = ConfigDict(extra="forbid")

    MAX_JOBS: int = Field(
        default=-1,
        ge=-1,
        description="Maximum jobs per user/virtual instance. "
        "Set to -1 for unlimited.",
    )
    PASSWORD_EXPIRY_DAYS: int = Field(
        default=90, ge=0, description="Password expiry days (0 = never expire)"
    )
    MAX_LOGIN_ATTEMPTS: int = Field(
        default=5,
        ge=1,
        description="Maximum login attempts before account lockout",
    )
    MAX_LOGIN_LOGS: int = Field(
        default=10000,
        ge=100,
        description="Maximum number of login logs to keep in database",
    )
    LOCKOUT_DURATION_MINUTES: int = Field(
        default=30, ge=1, description="Account lockout duration in minutes"
    )
    ACCESS_CONTROL_MODEL_FILE: str = Field(
        default="/etc/qcos/roles/casbin_model.conf",
        description="Casbin access control model file path",
    )
    ACCESS_CONTROL_POLICY_FILE: str = Field(
        default="/etc/qcos/roles/policy.conf",
        description="Casbin access control policy file path",
    )
    DEFAULT_ADMIN_PASSWORD: str | None = Field(
        default=None,
        description="Default admin password (encrypted)",
        json_schema_extra={"sensitive": True},
    )
    JWT_AUTH_SECRET_KEY: str = Field(
        default=_s("47pW_6k8A4iU1Z8-r8G2j4_xN9M5V3L7Q9p2X1Y4Z0A"),
        description="JWT authentication secret key",
        json_schema_extra={"sensitive": True},
    )
    JWT_AUTH_ALGORITHM: str = Field(
        default="HS256",
        description="JWT authentication algorithm (HS256, HS512, RS256, etc.)",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, ge=1, description="Access token expiry time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, ge=1, description="Refresh token expiry time in days"
    )


class VirtSection(BaseModel):
    """VIRT section configuration."""

    model_config = ConfigDict(extra="forbid")

    PASSWORD_SALT: str = Field(
        default="123456",
        description="Salt for password/encryption",
        json_schema_extra={"sensitive": True},
    )


class LogSection(BaseModel):
    """LOG section configuration."""

    model_config = ConfigDict(extra="forbid")

    API_LOG_FILE: str = Field(
        default="/var/log/qcos/qcos-api.log", description="API log file path"
    )
    LOG_FORMAT: str = Field(
        default="%(asctime)s %(levelname)s %(filename)s:"
        "%(lineno)s %(message)s",
        description="Log message format",
    )
    LOG_ROTATE_MAX_SIZE_MB: int = Field(
        default=10, ge=1, description="Log file max size in MB before rotation"
    )
    LOG_ROTATE_BACKUP_COUNT: int = Field(
        default=10, ge=1, description="Number of backup log files to keep"
    )
    LOG_ROTATE_COMPRESSION: bool = Field(
        default=True, description="Enable log file compression"
    )


class SSLSection(BaseModel):
    """SSL section configuration."""

    model_config = ConfigDict(extra="forbid")

    USE_SSL: bool = Field(
        default=False, description="Enable HTTPS for API server"
    )
    CERT_FILE: str | None = Field(
        default=None, description="SSL certificate file path"
    )
    KEY_FILE: str | None = Field(
        default=None, description="SSL private key file path"
    )
    CACERT_FILE: str | None = Field(
        default=None, description="SSL CA certificate file path (optional)"
    )


class DevicesSection(BaseModel):
    """DEVICES section configuration."""

    model_config = ConfigDict(extra="forbid")

    DEVICE_LIST: list[str] = Field(
        default_factory=list, description="List of enabled quantum devices"
    )


class ConfigModel(BaseModel):
    """Complete QCOS configuration model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    DEFAULT: DefaultSection = Field(default_factory=DefaultSection)
    API_SERVER: APIServerSection = Field(default_factory=APIServerSection)
    METRICS_SERVER: MetricsServerSection = Field(
        default_factory=MetricsServerSection
    )
    PREFECT: PrefectSection = Field(default_factory=PrefectSection)
    TRANSPILER: TranspilerSection = Field(default_factory=TranspilerSection)
    REDIS: RedisSection = Field(default_factory=RedisSection)
    DATABASE: DatabaseSection = Field(default_factory=DatabaseSection)
    USERS: UsersSection = Field(default_factory=UsersSection)
    VIRT: VirtSection = Field(default_factory=VirtSection)
    LOG: LogSection = Field(default_factory=LogSection)
    SSL: SSLSection = Field(default_factory=SSLSection)
    DEVICES: DevicesSection = Field(default_factory=DevicesSection)


# ==================== Config Manager ====================


class Config:
    """QCOS Configuration Manager using Pydantic.

    Manages configuration from TOML files with type validation,
    default values, and value ranges. Access is ALWAYS through Section:

    Example:
        Config.DEFAULT.DEBUG
        Config.API_SERVER.API_SERVER_LISTEN_PORT
        Config.USERS.PASSWORD_EXPIRY_DAYS
    """

    # Store the pydantic model instance
    _model: ConfigModel | None = None

    # Extra configs not in VALID_SECTIONS
    _EXTRA_CONFIGS: dict[str, dict[str, Any]] = {}

    # Driver env configs
    _DRIVER_ENV_CONFIGS: dict[str, Any] = {}

    # Valid sections for configuration
    VALID_SECTIONS = [
        "DEFAULT",
        "API_SERVER",
        "METRICS_SERVER",
        "PREFECT",
        "REDIS",
        "DATABASE",
        "USERS",
        "VIRT",
        "LOG",
        "SSL",
        "DEVICES",
    ]

    # Expose sections as class attributes for type hints and access
    DEFAULT: DefaultSection = DefaultSection()
    API_SERVER: APIServerSection = APIServerSection()
    METRICS_SERVER: MetricsServerSection = MetricsServerSection()
    PREFECT: PrefectSection = PrefectSection()
    TRANSPILER: TranspilerSection = TranspilerSection()
    REDIS: RedisSection = RedisSection()
    DATABASE: DatabaseSection = DatabaseSection()
    USERS: UsersSection = UsersSection()
    VIRT: VirtSection = VirtSection()
    LOG: LogSection = LogSection()
    SSL: SSLSection = SSLSection()
    DEVICES: DevicesSection = DevicesSection()

    @classmethod
    def initialize(cls):
        """Initialize Config with default values."""
        if cls._model is None:
            cls._model = ConfigModel()

        # Always update section attributes from _model
        # (they may have been updated by load_config_file)
        cls.DEFAULT = cls._model.DEFAULT
        cls.API_SERVER = cls._model.API_SERVER
        cls.METRICS_SERVER = cls._model.METRICS_SERVER
        cls.PREFECT = cls._model.PREFECT
        cls.TRANSPILER = cls._model.TRANSPILER
        cls.REDIS = cls._model.REDIS
        cls.DATABASE = cls._model.DATABASE
        cls.USERS = cls._model.USERS
        cls.VIRT = cls._model.VIRT
        cls.LOG = cls._model.LOG
        cls.SSL = cls._model.SSL
        cls.DEVICES = cls._model.DEVICES

    @classmethod
    def load_config_file(cls, config_file: str, extra_config: bool = False):
        """Load configuration from TOML file.

        Args:
            config_file: Path to TOML configuration file
            extra_config: Whether to load as extra config
                (not in VALID_SECTIONS)

        Raises:
            GenericException: If file cannot be read or config is invalid
        """
        cls.initialize()

        def decrypt_value(value, section_key):
            """Decrypt encrypted configuration values."""
            if isinstance(value, str) and value.startswith(
                Constant.ENCRYPTION_PREFIX
            ):
                _success, _err_msg, decrypted_value = Library.decrypt_text(
                    value,
                    encryption_prefix=Constant.ENCRYPTION_PREFIX,
                    fernet_key=Constant.DEFAULT_FERNET_KEY,
                )
                if not _success:
                    raise errors.GenericException(
                        f"Can't decrypt text: {value} ({section_key})"
                    )
                return decrypted_value
            return value

        # Read TOML file
        success, err_msg, config_values = Library.read_toml_file(config_file)
        if not success:
            raise errors.GenericException(
                f"Error in config file: {config_file}. Reason: {err_msg}"
            )
        config_values = config_values.unwrap()

        if extra_config:
            # Load extra configs
            for section, options in config_values.items():
                if section not in cls._EXTRA_CONFIGS:
                    cls._EXTRA_CONFIGS[section] = {}
                for key, value in options.items():
                    cls._EXTRA_CONFIGS[section][key] = decrypt_value(
                        value, f"{section}:{key}"
                    )
        else:
            # Load main configs
            model_data = {}
            for section, options in config_values.items():
                if section in cls.VALID_SECTIONS:
                    section_data = {}
                    for key, value in options.items():
                        # Normalize key to uppercase to match Pydantic
                        # field names
                        normalized_key = (
                            key.upper() if isinstance(key, str) else key
                        )
                        decrypted_val = decrypt_value(
                            value, f"{section}:{key}"
                        )
                        section_data[normalized_key] = decrypted_val
                    model_data[section] = section_data
                else:
                    # Store extra configs
                    if section not in cls._EXTRA_CONFIGS:
                        cls._EXTRA_CONFIGS[section] = {}
                    for key, value in options.items():
                        cls._EXTRA_CONFIGS[section][key] = decrypt_value(
                            value, f"{section}:{key}"
                        )

            # Create pydantic model from loaded data
            try:
                # If model already exists, merge data instead of replacing
                if cls._model is not None:
                    for section_name, section_data in model_data.items():
                        existing_section = getattr(cls._model, section_name)
                        # Update existing section with new data
                        updated_data = existing_section.model_dump()
                        updated_data.update(section_data)
                        # Create new section instance
                        section_class = type(existing_section)
                        setattr(
                            cls._model,
                            section_name,
                            section_class(**updated_data),
                        )
                else:
                    # First time loading, create new model
                    cls._model = ConfigModel(**model_data)

                cls.initialize()  # Update section attributes
            except (ValueError, ValidationError) as e:
                # Extract and format validation errors
                err_list = e.errors() if hasattr(e, "errors") else []
                err_msgs = ", ".join([
                    f"{err['msg']} {','.join(err['loc'])}" for err in err_list
                ])
                raise errors.GenericException(
                    f"Configuration validation error: [{e.title}] {err_msgs}"
                )

    @classmethod
    def load_driver_env_file(cls, config_file: str):
        """Load driver environment configuration file.

        Args:
            config_file: Path to driver env config file
        """
        Path(config_file).parent
        _configs = {}
        configs = {}
        success, err_msg, _configs = Library.read_toml_file(config_file)
        if not success:
            cls._DRIVER_ENV_CONFIGS = configs
            return

        # Sort dict - copy_from items at end
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
            if "envs" not in driver_info:
                raise Exception(f"[{driver_class}] 'envs' must be specified")
        cls._DRIVER_ENV_CONFIGS = configs

    @classmethod
    def validate(cls):
        """Validate current configuration."""
        cls.initialize()
        # Pydantic validation happens during model creation

        # Validate database URL
        cls.DATABASE.validate_url()

        # Remove duplicates from device list
        cls.DEVICES.DEVICE_LIST = Library.remove_duplicates(
            cls.DEVICES.DEVICE_LIST
        )

    @classmethod
    def get_config(cls) -> ConfigModel | None:
        """Get the configuration model.

        Returns:
            ConfigModel instance
        """
        cls.initialize()
        return cls._model

    @classmethod
    def get_extra_configs(cls) -> dict[str, dict[str, Any]]:
        """Get extra configurations.

        Returns:
            Extra configs dictionary
        """
        return cls._EXTRA_CONFIGS

    @classmethod
    def get_driver_env_configs(cls) -> dict[str, Any]:
        """Get driver environment configurations.

        Returns:
            Driver env configs dictionary
        """
        return cls._DRIVER_ENV_CONFIGS

    @classmethod
    def get_configs(cls, mask_password: bool = False) -> dict[str, Any]:
        """Get all configurations as dictionary.

        Args:
            mask_password: Whether to mask password values

        Returns:
            Dictionary of all configurations (nested by section)
        """
        cls.initialize()
        configs = cls._model.model_dump()
        if mask_password:
            configs = Library.mask_password(configs)
        return configs

    @classmethod
    def show_info(cls) -> str:
        """Show configuration information with sensitive fields masked.

        Returns:
            Formatted configuration information string
            with masked sensitive values
        """
        cls.initialize()
        outputs = ["[QCOS Configuration]"]

        # Show sections with masked sensitive values
        for section_name in cls.VALID_SECTIONS:
            section_obj = getattr(cls._model, section_name, None)
            if section_obj:
                outputs.append(f"\n[{section_name}]")
                section_obj.model_dump()
                # Mask sensitive fields in section data
                masked_data = Library.mask_password_from_pydantic(
                    section_obj,
                )
                for key, value in masked_data.items():
                    outputs.append(f"  {key:<30}: {value}")

        # Show extra configs if any (also masked)
        if cls._EXTRA_CONFIGS:
            outputs.append("\n[EXTRA CONFIGS]")
            for section, items in cls._EXTRA_CONFIGS.items():
                outputs.append(f"\n  [{section}]")
                # Mask sensitive fields in extra configs
                masked_items = Library.mask_password(items)
                for key, value in masked_items.items():
                    outputs.append(f"    {key:<28}: {value}")

        return "\n" + "\n".join(outputs) + "\n"
