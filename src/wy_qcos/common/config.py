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
    CORS_ALLOWED_ORIGINS: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins. Use ['*'] to allow any origin "
        "(insecure, only for development). For production, list the exact "
        "origins of the WebUI, e.g. ['https://qcos.example.com'].",
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


class ProxySection(BaseModel):
    """PROXY section configuration.

    Reverse-proxy upstream endpoints. An empty string disables the
    corresponding proxy mount.
    """

    model_config = ConfigDict(extra="forbid")

    PROMETHEUS_BASE_URL: str = Field(
        default="http://127.0.0.1:9090",
        description="Prometheus base URL ('' to disable proxy endpoint)",
    )
    ALERTMANAGER_BASE_URL: str = Field(
        default="http://127.0.0.1:9093",
        description="Alertmanager base URL ('' to disable proxy endpoint)",
    )
    VICTORIALOGS_BASE_URL: str = Field(
        default="http://127.0.0.1:9428",
        description="VictoriaLogs base URL ('' to disable proxy endpoint)",
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
    QCOS_FLOW_RUN_TIMEOUT: int = Field(
        default=600,
        ge=10,
        description="Timeout in seconds for create_flow_run_from_deployment "
        "calls. Large parameter payloads (e.g. big QUBO matrices) can "
        "cause the Prefect API to hang if the PostgreSQL connection "
        "pool is exhausted. This timeout ensures QCOS fails fast "
        "instead of hanging indefinitely.",
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

    REDIS_URL: str = Field(
        default=f"redis://{Constant.DEFAULT_REDIS_SERVER_IP}:{Constant.DEFAULT_REDIS_SERVER_PORT}/0",
        description="Redis server url",
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
        default="%(asctime)s | %(levelname)s | "
        "%(module)s:%(lineno)s | %(message)s",
        description="Log message format (shared by all QCOS processes)",
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


class DevicesSection(BaseModel):
    """DEVICES section configuration."""

    model_config = ConfigDict(extra="forbid")

    DEVICE_LIST: list[str] = Field(
        default_factory=list, description="List of enabled quantum devices"
    )


class SchedulerSection(BaseModel):
    """SCHEDULER section configuration.

    Controls the auto scheduler behavior, including which filters and
    weighers are enabled. Filter/weigher names must match the class
    names discovered by AutoScheduler at startup by scanning the
    scheduler/filters and scheduler/weighers directories.
    """

    model_config = ConfigDict(extra="forbid")

    # enable auto scheduling (select device automatically when
    # backend is not specified in submit_job)
    ENABLE_AUTO_SCHEDULE: bool = Field(
        default=True,
        description="Enable auto scheduling when backend is not specified",
    )
    # comma-separated list of enabled filter class names; if empty,
    # all filters in DEFAULT_FILTERS are used (plus DeviceGroupFilter
    # when a device_group_manager is available)
    ENABLED_FILTERS: list[str] = Field(
        default_factory=list,
        description="List of enabled filter class names",
    )
    # comma-separated list of enabled weigher class names; if empty,
    # all weighers in DEFAULT_WEIGHERS are used
    ENABLED_WEIGHERS: list[str] = Field(
        default_factory=list,
        description="List of enabled weigher class names",
    )


class TerminalSection(BaseModel):
    """TERMINAL section configuration.

    Mirrors the ``[TERMINAL]`` table documented in
    ``plans/terminal.md`` §7.4. All fields have safe defaults so the
    terminal feature can be enabled by simply flipping ``ENABLED``.
    """

    model_config = ConfigDict(extra="forbid")

    ENABLED: bool = Field(
        default=False,
        description="Master switch for the in-browser terminal",
    )
    IDLE_TIMEOUT_SECONDS: int = Field(
        default=1800,
        ge=0,
        description="Idle session timeout in seconds (0 disables reaper)",
    )
    MAX_SESSIONS_PER_USER: int = Field(
        default=4,
        ge=1,
        description="Max concurrent terminal sessions per user",
    )
    MAX_SESSIONS_TOTAL: int = Field(
        default=128,
        ge=1,
        description="Max concurrent terminal sessions globally",
    )
    DEFAULT_SHELL: str = Field(
        default="/bin/bash",
        description=(
            "Default shell path inside the sandbox; used when "
            "ENTRY_COMMAND is empty"
        ),
    )
    ENTRY_COMMAND: str = Field(
        default="/bin/bash",
        description=(
            "Command spawned inside the sandbox. Change to "
            "'qcos-cli interactive' for a QCOS-native REPL."
        ),
    )
    SANDBOX_ENABLED: bool = Field(
        default=True,
        description=(
            "Use bwrap for per-user isolation; false runs a bare "
            "host shell (debug only)"
        ),
    )
    SANDBOX_ROOT: str = Field(
        default="/var/qcos/users",
        description="Host directory holding one subdir per user UUID",
    )
    QCOS_ROOT: str = Field(
        default="/opt/qcos",
        description="Path bind-mounted read-only inside the sandbox",
    )
    SECCOMP_PROFILE: str = Field(
        default="default",
        description=(
            "seccomp blacklist profile name or path to a custom BPF "
            "file (P1; reserved for future use)"
        ),
    )
    NET_POLICY: str = Field(
        default="none",
        description=(
            "Sandbox network policy: 'none' (default, fully "
            "disconnected), 'local-api-only' (allow only "
            "127.0.0.1:QCOS_API_PORT via host firewall), or 'full' "
            "(no restriction; debug only)"
        ),
    )
    # Optional override. When omitted (None or 0), the value falls back
    # to Config.API_SERVER.API_SERVER_LISTEN_PORT so operators don't
    # have to keep two port fields in sync. Only consumed when
    # NET_POLICY == "local-api-only".
    QCOS_API_PORT: int | None = Field(
        default=None,
        ge=1,
        le=65535,
        description=(
            "QCOS API listen port override; used by NET_POLICY="
            "local-api-only as the only allowed egress target. "
            "Defaults to API_SERVER_LISTEN_PORT when omitted."
        ),
    )
    MAX_UPLOAD_MB: int = Field(
        default=100,
        ge=1,
        description="Per-file upload size cap in megabytes",
    )
    RECORD_TRANSCRIPT: bool = Field(
        default=False,
        description=(
            "Record asciinema .cast transcripts of each session. "
            "Default off; transcripts may contain sensitive output."
        ),
    )
    TRANSCRIPT_DIR: str = Field(
        default="/var/log/qcos/terminal",
        description=(
            "Root directory for transcripts; per-user files land in "
            "{TRANSCRIPT_DIR}/users/{USER_UUID}/ with mode 0700"
        ),
    )


class AISection(BaseModel):
    """AI global section (top-level [AI]).

    Holds only the master switch that gates the whole AI feature
    family. Per-subsystem settings live in dedicated nested sections:

    - ``[AI.MCP_SERVER]`` -> :class:`AIMcpServerSection`
    - ``[AI.AGENT]``      -> :class:`AIAgentSection`
    """

    model_config = ConfigDict(extra="forbid")

    ENABLED: bool = Field(
        default=True,
        description="Global master switch for the AI feature family. "
        "When false, both the MCP server endpoint (/v1/ai/mcp) and "
        "the AI agent chat API (/v1/ai/) are disabled regardless of "
        "their own ENABLED flags.",
    )


class AIMcpServerSection(BaseModel):
    """AI MCP server section ([AI.MCP_SERVER]).

    Controls exposure of the MCP endpoint that lets external LLM
    clients (Claude Desktop, IDEs, ...) invoke QCOS tools.
    """

    model_config = ConfigDict(extra="forbid")

    ENABLED: bool = Field(
        default=True,
        description="Enable the MCP server endpoint (/v1/ai/mcp). "
        "Effective only when [AI].ENABLED is also true.",
    )


class AIAgentSection(BaseModel):
    """AI agent section ([AI.AGENT]) for QCOS AI chat assistant."""

    model_config = ConfigDict(extra="forbid")

    ENABLED: bool = Field(
        default=True,
        description="Master switch for the AI agent chat feature. "
        "Effective only when [AI].ENABLED is also true.",
    )
    # LLM provider: openai_compatible | openai | anthropic
    LLM_PROVIDER: str = Field(
        default="openai_compatible",
        description="LLM provider type",
    )
    LLM_BASE_URL: str = Field(
        default="http://vllm:8000/v1",
        description="LLM endpoint base URL (ignored for openai/anthropic)",
    )
    LLM_API_KEY: str = Field(
        default="",
        description="LLM API key (empty for unauthenticated endpoints)",
        json_schema_extra={"sensitive": True},
    )
    LLM_MODEL: str = Field(
        default="Qwen/Qwen2.5-72B-Instruct",
        description="LLM model name passed to the provider",
    )
    LLM_TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature",
    )
    LLM_MAX_TOKENS: int = Field(
        default=4096,
        ge=1,
        description="Max tokens for LLM response",
    )
    LLM_TIMEOUT: float = Field(
        default=60.0,
        gt=0,
        description="LLM HTTP request timeout in seconds. Guards "
        "against indefinitely hanging LLM endpoints; on expiry the "
        "chat stream returns RUN_ERROR instead of spinning forever. "
        "Applies to text and vision models.",
    )
    # Vision model (optional, falls back to LLM_* when empty)
    VISION_PROVIDER: str = Field(
        default="",
        description="Vision model provider (falls back to LLM_PROVIDER)",
    )
    VISION_BASE_URL: str = Field(
        default="",
        description="Vision model endpoint (falls back to LLM_BASE_URL)",
    )
    VISION_API_KEY: str = Field(
        default="",
        description="Vision model API key (falls back to LLM_API_KEY)",
        json_schema_extra={"sensitive": True},
    )
    VISION_MODEL: str = Field(
        default="",
        description="Vision model name (falls back to LLM_MODEL)",
    )
    # Image attachment limits
    IMAGE_MAX_COUNT_PER_MESSAGE: int = Field(
        default=4,
        ge=1,
        description="Max image attachments per message",
    )
    IMAGE_MAX_BYTES_PER_IMAGE: int = Field(
        default=5242880,
        ge=1024,
        description="Max bytes per image after base64 encoding",
    )
    IMAGE_MAX_TOTAL_BYTES_PER_SESSION: int = Field(
        default=52428800,
        ge=1024,
        description="Max total image bytes per session",
    )
    # Embedding
    EMBEDDING_BASE_URL: str = Field(
        default="http://127.0.0.1:8001/v1/embeddings",
        description="Embedding endpoint base URL",
    )
    EMBEDDING_API_KEY: str = Field(
        default="",
        description="Embedding API key",
        json_schema_extra={"sensitive": True},
    )
    EMBEDDING_MODEL: str = Field(
        default="bge-m3",
        description="Embedding model name",
    )
    EMBEDDING_DIM: int = Field(
        default=1024,
        ge=1,
        description="Embedding vector dimension",
    )
    # Session
    SESSION_TTL_SECONDS: int = Field(
        default=604800,
        ge=60,
        description="AI session TTL in seconds (default 7 days)",
    )
    RAG_TOP_K: int = Field(
        default=8,
        ge=1,
        le=100,
        description="Number of RAG chunks to retrieve",
    )


class ConfigModel(BaseModel):
    """Complete QCOS configuration model."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    DEFAULT: DefaultSection = Field(default_factory=DefaultSection)
    API_SERVER: APIServerSection = Field(default_factory=APIServerSection)
    METRICS_SERVER: MetricsServerSection = Field(
        default_factory=MetricsServerSection
    )
    PROXY: ProxySection = Field(default_factory=ProxySection)
    PREFECT: PrefectSection = Field(default_factory=PrefectSection)
    TRANSPILER: TranspilerSection = Field(default_factory=TranspilerSection)
    REDIS: RedisSection = Field(default_factory=RedisSection)
    DATABASE: DatabaseSection = Field(default_factory=DatabaseSection)
    USERS: UsersSection = Field(default_factory=UsersSection)
    VIRT: VirtSection = Field(default_factory=VirtSection)
    LOG: LogSection = Field(default_factory=LogSection)
    SSL: SSLSection = Field(default_factory=SSLSection)
    DEVICES: DevicesSection = Field(default_factory=DevicesSection)
    SCHEDULER: SchedulerSection = Field(default_factory=SchedulerSection)
    TERMINAL: TerminalSection = Field(default_factory=TerminalSection)
    AI: AISection = Field(default_factory=AISection)
    AI_MCP_SERVER: AIMcpServerSection = Field(
        default_factory=AIMcpServerSection
    )
    AI_AGENT: AIAgentSection = Field(default_factory=AIAgentSection)


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

    # Project root directory for resolving relative paths
    # (e.g. AI agent local file reading). Computed from this file's
    # location: src/wy_qcos/common/config.py -> ../../../
    PROJECT_ROOT: str = str(
        Path(__file__).resolve().parent.parent.parent.parent
    )

    # Project source directory (src/wy_qcos/). Used by AI agent
    # local file reading to restrict access to source code only.
    PROJECT_SRC_DIR: str = str(Path(__file__).resolve().parent.parent.parent)

    # Valid sections for configuration. Nested TOML sections are
    # flattened with a "." separator (e.g. "[AI.MCP_SERVER]" appears
    # here as "AI.MCP_SERVER"); the loader maps them onto ConfigModel
    # attributes by replacing "." with "_" ("AI_MCP_SERVER").
    VALID_SECTIONS = [
        "DEFAULT",
        "API_SERVER",
        "METRICS_SERVER",
        "PROXY",
        "PREFECT",
        "REDIS",
        "DATABASE",
        "USERS",
        "VIRT",
        "LOG",
        "SSL",
        "DEVICES",
        "SCHEDULER",
        "TERMINAL",
        "AI",
        "AI.MCP_SERVER",
        "AI.AGENT",
    ]

    # Mapping from nested TOML section name (dotted) to ConfigModel
    # attribute name (pydantic does not allow "." in field names).
    NESTED_SECTION_ATTR_MAP = {
        "AI.MCP_SERVER": "AI_MCP_SERVER",
        "AI.AGENT": "AI_AGENT",
    }

    # Expose sections as class attributes for type hints and access
    DEFAULT: DefaultSection = DefaultSection()
    API_SERVER: APIServerSection = APIServerSection()
    METRICS_SERVER: MetricsServerSection = MetricsServerSection()
    PROXY: ProxySection = ProxySection()
    PREFECT: PrefectSection = PrefectSection()
    TRANSPILER: TranspilerSection = TranspilerSection()
    REDIS: RedisSection = RedisSection()
    DATABASE: DatabaseSection = DatabaseSection()
    USERS: UsersSection = UsersSection()
    VIRT: VirtSection = VirtSection()
    LOG: LogSection = LogSection()
    SSL: SSLSection = SSLSection()
    DEVICES: DevicesSection = DevicesSection()
    SCHEDULER: SchedulerSection = SchedulerSection()
    TERMINAL: TerminalSection = TerminalSection()
    AI: AISection = AISection()
    AI_MCP_SERVER: AIMcpServerSection = AIMcpServerSection()
    AI_AGENT: AIAgentSection = AIAgentSection()

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
        cls.PROXY = cls._model.PROXY
        cls.PREFECT = cls._model.PREFECT
        cls.TRANSPILER = cls._model.TRANSPILER
        cls.REDIS = cls._model.REDIS
        cls.DATABASE = cls._model.DATABASE
        cls.USERS = cls._model.USERS
        cls.SCHEDULER = cls._model.SCHEDULER
        cls.VIRT = cls._model.VIRT
        cls.LOG = cls._model.LOG
        cls.SSL = cls._model.SSL
        cls.DEVICES = cls._model.DEVICES
        cls.TERMINAL = cls._model.TERMINAL
        cls.AI = cls._model.AI
        cls.AI_MCP_SERVER = cls._model.AI_MCP_SERVER
        cls.AI_AGENT = cls._model.AI_AGENT

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
            # Load main configs. Nested TOML sections (e.g.
            # "[AI.MCP_SERVER]") arrive as sub-dicts inside their parent
            # section ("AI") and are hoisted out into their own flat
            # model_data entries keyed by the dotted path; the dotted
            # path is then mapped to the ConfigModel attribute name via
            # NESTED_SECTION_ATTR_MAP ("." -> "_") so pydantic can
            # consume it.
            model_data: dict[str, dict[str, Any]] = {}

            def _ingest_section(
                dotted_name: str, options: dict[str, Any]
            ) -> None:
                """Merge one TOML section into model_data.

                Splits nested sub-dicts out as their own dotted sections
                and uppercases leaf keys to match pydantic field names.
                """
                if dotted_name not in cls.VALID_SECTIONS:
                    # Store extra configs verbatim
                    if dotted_name not in cls._EXTRA_CONFIGS:
                        cls._EXTRA_CONFIGS[dotted_name] = {}
                    for key, value in options.items():
                        cls._EXTRA_CONFIGS[dotted_name][key] = decrypt_value(
                            value, f"{dotted_name}:{key}"
                        )
                    return
                section_data: dict[str, Any] = {}
                for key, value in options.items():
                    if isinstance(value, dict):
                        # Nested sub-section: recurse with dotted name
                        _ingest_section(f"{dotted_name}.{key}", value)
                        continue
                    # Normalize key to uppercase to match Pydantic
                    # field names
                    normalized_key = (
                        key.upper() if isinstance(key, str) else key
                    )
                    decrypted_val = decrypt_value(
                        value, f"{dotted_name}:{key}"
                    )
                    section_data[normalized_key] = decrypted_val
                if section_data:
                    existing = model_data.setdefault(dotted_name, {})
                    existing.update(section_data)

            for section, options in config_values.items():
                if isinstance(options, dict):
                    _ingest_section(section, options)
                else:
                    # Scalar top-level key (rare) - treat as extra
                    if section not in cls._EXTRA_CONFIGS:
                        cls._EXTRA_CONFIGS[section] = {}
                    cls._EXTRA_CONFIGS[section]["__value__"] = decrypt_value(
                        section, section
                    )

            # Remap dotted section names to ConfigModel attribute
            # names ("." is not allowed in pydantic field names).
            remapped_model_data: dict[str, dict[str, Any]] = {}
            for dotted_name, section_data in model_data.items():
                attr_name = cls.NESTED_SECTION_ATTR_MAP.get(
                    dotted_name, dotted_name
                )
                remapped_model_data[attr_name] = section_data

            # Create pydantic model from loaded data
            try:
                # If model already exists, merge data instead of replacing
                if cls._model is not None:
                    for (
                        section_name,
                        section_data,
                    ) in remapped_model_data.items():
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
                    cls._model = ConfigModel(**remapped_model_data)

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
    def is_ai_agent_enabled(cls) -> bool:
        """Whether the AI agent chat feature is enabled.

        Combines the global ``[AI].ENABLED`` master switch with the
        per-subsystem ``[AI.AGENT].ENABLED`` flag; both must be true
        for the feature to be exposed.
        """
        cls.initialize()
        return bool(cls.AI.ENABLED and cls.AI_AGENT.ENABLED)

    @classmethod
    def is_ai_mcp_server_enabled(cls) -> bool:
        """Whether the AI MCP server endpoint is enabled.

        Combines the global ``[AI].ENABLED`` master switch with the
        per-subsystem ``[AI.MCP_SERVER].ENABLED`` flag; both must be
        true for the endpoint to be exposed.
        """
        cls.initialize()
        return bool(cls.AI.ENABLED and cls.AI_MCP_SERVER.ENABLED)

    @classmethod
    def is_terminal_enabled(cls) -> bool:
        """Whether the in-browser terminal feature is enabled."""
        cls.initialize()
        return bool(cls.TERMINAL.ENABLED)

    @classmethod
    def is_metrics_server_enabled(cls) -> bool:
        """Whether the metrics server is enabled.

        The metrics server is considered enabled when a non-empty
        listen IP is configured.
        """
        cls.initialize()
        return bool(cls.METRICS_SERVER.METRICS_SERVER_LISTEN_IP)

    @classmethod
    def is_proxy_prometheus_enabled(cls) -> bool:
        """Whether the Prometheus reverse proxy is enabled."""
        cls.initialize()
        return bool(cls.PROXY.PROMETHEUS_BASE_URL)

    @classmethod
    def is_proxy_alertmanager_enabled(cls) -> bool:
        """Whether the Alertmanager reverse proxy is enabled."""
        cls.initialize()
        return bool(cls.PROXY.ALERTMANAGER_BASE_URL)

    @classmethod
    def is_proxy_victorialogs_enabled(cls) -> bool:
        """Whether the VictoriaLogs reverse proxy is enabled."""
        cls.initialize()
        return bool(cls.PROXY.VICTORIALOGS_BASE_URL)

    @classmethod
    def is_embedding_enabled(cls) -> bool:
        """Whether the embedding service is enabled.

        The embedding service is considered enabled when the AI agent
        feature is enabled AND a non-empty embedding base URL is
        configured.
        """
        cls.initialize()
        return bool(
            cls.is_ai_agent_enabled() and cls.AI_AGENT.EMBEDDING_BASE_URL
        )

    @classmethod
    def is_vision_enabled(cls) -> bool:
        """Whether the vision (image understanding) model is enabled.

        The vision pipeline is considered enabled when the AI agent
        feature is enabled AND either an explicit ``VISION_MODEL`` is
        configured OR the configured ``VISION_PROVIDER`` is non-empty.
        When neither is set, image attachments would only be passed
        to the text-only model, which usually has no vision support
        and would silently drop them - the UI must therefore disable
        the image-attachment button.
        """
        cls.initialize()
        if not cls.is_ai_agent_enabled():
            return False
        return bool(cls.AI_AGENT.VISION_MODEL or cls.AI_AGENT.VISION_PROVIDER)

    @classmethod
    def get_component_switch_status(cls) -> dict[str, bool | dict[str, bool]]:
        """Get the enable status of all optional components.

        Returns:
            Dictionary mapping component name to its enabled status.
            Top-level entries are either a plain ``bool`` (single
            component) or a nested ``dict[str, bool]`` for component
            groups (``ai`` / ``proxy``) that bundle related features.
        """
        cls.initialize()
        return {
            "ai": {
                Constant.COMPONENT_NAME_AI_AGENT: cls.is_ai_agent_enabled(),
                Constant.COMPONENT_NAME_AI_MCP_SERVER: (
                    cls.is_ai_mcp_server_enabled()
                ),
                Constant.COMPONENT_NAME_EMBEDDING: (
                    cls.is_embedding_enabled()
                ),
                Constant.COMPONENT_NAME_VISION: cls.is_vision_enabled(),
            },
            Constant.COMPONENT_NAME_TERMINAL: cls.is_terminal_enabled(),
            Constant.COMPONENT_NAME_METRICS_SERVER: (
                cls.is_metrics_server_enabled()
            ),
            "proxy": {
                Constant.COMPONENT_NAME_PROXY_PROMETHEUS: (
                    cls.is_proxy_prometheus_enabled()
                ),
                Constant.COMPONENT_NAME_PROXY_ALERTMANAGER: (
                    cls.is_proxy_alertmanager_enabled()
                ),
                Constant.COMPONENT_NAME_PROXY_VICTORIALOGS: (
                    cls.is_proxy_victorialogs_enabled()
                ),
            },
        }

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
