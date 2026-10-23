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
#     WARRANTIES OF ANY KIND,
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""MCP Server for QCOS quantum computing operating system.

This module creates an MCP (Model Context Protocol) server that exposes
QCOS quantum computing capabilities to AI assistants. It is designed to
be mounted on the existing FastAPI application, sharing the same HTTP
port as the JSON-RPC API.

The MCP tools communicate with the QCOS backend via internal HTTP
JSON-RPC calls to the same FastAPI app, reusing authentication and
dependency injection. This avoids circular imports and keeps the MCP
layer cleanly separated from the business logic.

Tools provided:

- qcos_login: Authenticate and obtain JWT token
- qcos_get_version: Get QCOS system version and capabilities
- qcos_list_devices: List available quantum devices
- qcos_get_device_detail: Get details of a specific device
- qcos_submit_job: Submit a quantum computing job (QASM code)
- qcos_list_jobs: List quantum jobs with optional filters
- qcos_get_job_status: Get status of a specific job
- qcos_get_job_result: Get execution results of a job
- qcos_cancel_jobs: Cancel one or more jobs
- qcos_delete_jobs: Delete one or more jobs
- qcos_update_job: Update a queued job's attributes

Flavor management (preset scheduling policies):

- qcos_create_flavor / qcos_update_flavor / qcos_get_flavor /
  qcos_get_flavors / qcos_delete_flavors

Device group management:

- qcos_create_device_group / qcos_update_device_group /
  qcos_get_device_group / qcos_get_device_groups /
  qcos_delete_device_groups

Device operations:

- qcos_set_device: Update device state/enable/qubits
- qcos_calibrate_device / qcos_get_calibrate_results
- qcos_set_device_options / qcos_get_device_options

Driver and transpiler info:

- qcos_get_drivers / qcos_get_driver
- qcos_get_transpilers / qcos_get_transpiler

Project management:

- qcos_create_project / qcos_get_project / qcos_get_projects /
  qcos_update_project / qcos_delete_project

User and role management (admin only):

- qcos_create_user / qcos_get_user / qcos_get_users /
  qcos_update_user / qcos_delete_user / qcos_change_password
- qcos_create_role / qcos_get_role / qcos_get_roles /
  qcos_update_role / qcos_delete_role
- qcos_get_user_mgmt / qcos_set_user_mgmt
- qcos_get_login_logs / qcos_clear_login_logs

System monitoring:

- qcos_get_current_user: Get current authenticated user info
- qcos_get_system_health / qcos_get_api_stats / qcos_get_job_stats
- qcos_ping / qcos_system_info / qcos_show_mem / qcos_gc_mem
- qcos_list_workers / qcos_restart_worker

Resources provided:

- qcos://version: QCOS system version info
- qcos://devices: Available quantum devices summary
"""

import json
import logging
import os
import uuid
from typing import Any

import httpx

# Support both MCP 1.x (FastMCP) and 2.x (MCPServer) APIs
try:
    from mcp.server.fastmcp import FastMCP as _MCPServer

    _MCP_VERSION = 1
except ImportError:
    from mcp.server.mcpserver import MCPServer as _MCPServer

    _MCP_VERSION = 2

# MCP 2.x transport security: allow all hosts by default for internal
# network deployment. Set MCP_ALLOWED_HOSTS env var to restrict.
# This disables the "Invalid Host header" security check that blocks
# non-localhost connections.
os.environ.setdefault("MCP_ALLOWED_HOSTS", "*")
logger = logging.getLogger(__name__)

# QCOS internal API base URL - points to the same FastAPI app.
# In production this is typically "http://127.0.0.1:<port>".
# The port is read from environment or config at mount time.
_QCOS_BASE_URL = os.environ.get("QCOS_MCP_BASE_URL", "http://127.0.0.1:18400")

# Token storage: in a single-process deployment this is sufficient.
# For multi-worker deployments, use a shared store (e.g. Redis).
_auth_token: str | None = None


def _get_auth_headers() -> dict:
    """Build Authorization headers for internal JSON-RPC calls.

    Returns:
        dict with Authorization header if token is set, empty dict otherwise.
    """
    if _auth_token:
        return {"Authorization": f"Bearer {_auth_token}"}
    return {}


async def _jsonrpc_call(
    endpoint: str,
    method: str,
    params: dict | None = None,
    query: dict | None = None,
) -> dict:
    """Send a JSON-RPC 2.0 request to the QCOS backend.

    Args:
        endpoint: API endpoint path (e.g. "/v1/job")
        method: JSON-RPC method name (e.g. "submit_job")
        params: request parameters dict
        query: Optional query parameters dict (e.g. pagination,
            sort). When provided, passed as JSON-RPC "query" field.

    Returns:
        The "result" field from the JSON-RPC response.

    Raises:
        RuntimeError: if the HTTP request fails, the JSON-RPC call
            returns an error, or the response body cannot be parsed.
    """
    url = f"{_QCOS_BASE_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    headers.update(_get_auth_headers())

    body: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
    }
    if params is not None or query is not None:
        body["params"] = {}
        if params is not None:
            body["params"]["body"] = params
        if query is not None:
            body["params"]["query"] = query

    logger.debug(
        "JSON-RPC request: %s %s, method=%s, params=%s",
        "POST",
        url,
        method,
        params,
    )

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=body, headers=headers)

        # Check HTTP status code first - non-200 means the request
        # itself failed (e.g. server not running, auth required, etc.)
        if resp.status_code != 200:
            raise RuntimeError(
                f"QCOS backend returned HTTP {resp.status_code} "
                f"({resp.reason_phrase}) for {endpoint}. "
                f"Response: {resp.text[:500]}"
            )

        try:
            data = resp.json()
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse JSON response from {endpoint}: {e}. "
                f"Raw response: {resp.text[:500]}"
            )

        logger.debug(
            "JSON-RPC response: status=%s, data=%s",
            resp.status_code,
            data,
        )

        if "error" in data:
            err = data["error"]
            msg = err.get("message", "Unknown error")
            details = err.get("data", {}).get("details", "")
            raise RuntimeError(f"QCOS API error: {msg}. {details}")

        result = data.get("result", {})
        if not result:
            logger.warning(
                "JSON-RPC call to %s/%s returned empty result. "
                "Full response: %s",
                endpoint,
                method,
                data,
            )
        return result
    except httpx.RequestError as e:
        raise RuntimeError(f"Failed to connect to QCOS backend: {e}")


# ---------------------------------------------------------------------------
# MCP Server instance
# ---------------------------------------------------------------------------

# MCP 2.x: patch transport_security to allow all hosts for internal
# network deployment. The default only allows localhost which blocks
# connections from non-localhost IPs (e.g. internal network IP).
if _MCP_VERSION >= 2:
    try:
        from mcp.server import transport_security as _ts

        # Patch TransportSecurityMiddleware to disable DNS rebinding
        # protection by always returning a settings with it disabled.
        _orig_init = _ts.TransportSecurityMiddleware.__init__

        def _patched_init(self, settings=None):
            # Force disable DNS rebinding protection
            _orig_init(
                self,
                _ts.TransportSecuritySettings(
                    enable_dns_rebinding_protection=False,
                    allowed_hosts=["*"],
                    allowed_origins=["*"],
                ),
            )

        _ts.TransportSecurityMiddleware.__init__ = _patched_init
        logger.info(
            "MCP transport_security: DNS rebinding protection disabled"
        )

        # Also patch _validate_host to always return True
        _ts.TransportSecurityMiddleware._validate_host = (
            lambda self, host: True
        )
        logger.info("MCP transport_security: _validate_host patched")

    except ImportError as e:
        logger.warning(f"Could not import transport_security: {e}")
    except Exception as e:
        logger.warning(f"Could not patch transport_security: {e}")

mcp = _MCPServer("qcos-mcp-server")

# Cached streamable HTTP app (single instance, reused by lifespan init
# and request forwarding). This is critical: streamable_http_app() creates
# a new Starlette app each time, and the lifespan (task group init) must
# be on the SAME instance that serves requests.
_mcp_http_app = None


def get_mcp_http_app():
    """Get the cached MCP streamable HTTP app (singleton).

    Creates it on first call, then returns the same instance.
    This ensures lifespan init and request forwarding use the same app.
    """
    global _mcp_http_app
    if _mcp_http_app is None:
        _mcp_http_app = mcp.streamable_http_app()
    return _mcp_http_app


async def init_mcp_lifespan() -> object | None:
    """Initialize MCP server task group (required for MCP 2.x).

    This must be called during the FastAPI app lifespan startup to
    initialize the internal session manager's task group before any
    HTTP requests can be served.

    Returns:
        The streamable HTTP app's ASGI lifespan context if
        successfully initialized, None otherwise.
    """
    global _mcp_http_app
    if _MCP_VERSION < 2:
        return None

    try:
        app_instance = get_mcp_http_app()

        # MCP 2.x streamable_http_app() returns a Starlette app whose
        # router.lifespan_context initializes the session manager task group.
        # We manually enter it to trigger initialization.
        lifespan_handler = None
        if hasattr(app_instance, "router"):
            router = app_instance.router
            if hasattr(router, "lifespan_context"):
                lifespan_handler = router.lifespan_context
        elif hasattr(app_instance, "lifespan_context"):
            lifespan_handler = app_instance.lifespan_context

        if lifespan_handler is not None:
            ctx = lifespan_handler(app_instance)
            await ctx.__aenter__()
            logger.info("MCP server lifespan initialized (v2.x)")
            return ctx

        # Fallback: search for session_manager in routes or mcp attributes
        if hasattr(app_instance, "router"):
            for route in getattr(app_instance.router, "routes", []):
                if hasattr(route, "app") and hasattr(
                    route.app, "session_manager"
                ):
                    sm = route.app.session_manager
                    if hasattr(sm, "start"):
                        await sm.start()
                        logger.info("MCP session_manager started directly")
                        return sm

        for attr in (
            "_session_manager",
            "session_manager",
            "_streamable_http_manager",
        ):
            obj = getattr(mcp, attr, None)
            if obj is not None and hasattr(obj, "session_manager"):
                sm = obj.session_manager
                if hasattr(sm, "start"):
                    await sm.start()
                    logger.info("MCP session_manager started via mcp attr")
                    return sm

        logger.warning("MCP server: could not initialize task group")
        return None
    except Exception as e:
        logger.warning(f"Failed to initialize MCP server lifespan: {e}")
        return None


async def cleanup_mcp_lifespan(ctx: object | None) -> None:
    """Cleanup MCP server task group (required for MCP 2.x).

    Args:
        ctx: The context returned by init_mcp_lifespan
             (lifespan context or session_manager).
    """
    if ctx is None:
        return
    try:
        # If it's a lifespan context (has __aexit__)
        if hasattr(ctx, "__aexit__"):
            await ctx.__aexit__(None, None, None)
            logger.info("MCP server lifespan cleaned up")
        # If it's a session_manager (has stop)
        elif hasattr(ctx, "stop"):
            await ctx.stop()
            logger.info("MCP session_manager stopped")
    except Exception as e:
        logger.warning(f"Error cleaning up MCP server lifespan: {e}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_login(username: str, password: str) -> str:
    """Authenticate to QCOS and obtain a JWT token.

    This must be called before any other QCOS tool that requires
    authentication. The token is stored automatically for subsequent calls.

    Args:
        username: Username for authentication (e.g. "admin")
        password: Password for authentication

    Returns:
        JSON string with login info including user_name and token expiry.
    """
    global _auth_token
    result = await _jsonrpc_call(
        "/v1/auth", "login", {"username": username, "password": password}
    )
    _auth_token = result.get("access_token")
    # Return without exposing the full token for security
    safe_result = {
        "user_name": result.get("user_name"),
        "token_type": result.get("token_type", "bearer"),
        "expires_in": result.get("expires_in"),
        "status": "logged in" if _auth_token else "login failed",
    }
    return json.dumps(safe_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def qcos_get_version(details: bool = True) -> str:
    """Get QCOS system version, API version, and capabilities.

    This endpoint does not require authentication. Useful for discovering
    available quantum devices, drivers, and transpilers.

    Args:
        details: If True, include detailed capabilities (devices, drivers,
            transpilers, tech_types, profiling, driver_transpiler_mappings).
            Default is True.

    Returns:
        JSON string with the following fields:
        - version: Server version (e.g. "1.8.0")
        - api_version: Current API version (e.g. "v1")
        - supported_api_versions: List of supported API versions with status
        - platform_version: Platform version string
        - auth_mode: Authentication mode ("yes" or "no")
        - capabilities: (only when details=True) Dict containing:
            - job_types: Supported job types
            - drivers: Device driver info (name, code types, description)
            - transpilers: Transpiler info (alias_name, supported_code_types)
            - tech_types: Technology type info
            - profiling: Profiling info
            - driver_transpiler_mappings: Driver-to-transpiler mappings
    """
    result = await _jsonrpc_call("/version", "version", {"details": details})
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_list_devices(details: bool = True) -> str:
    """List all available quantum devices.

    Returns device names, alias names, driver info, qubit counts, and
    supported gate sets. Requires prior authentication via qcos_login.

    Args:
        details: If True, include detailed device specs. Default is True.

    Returns:
        JSON string mapping device names to device info.
    """
    result = await _jsonrpc_call(
        "/v1/device", "get_devices", {"details": details}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_device_detail(name: str, details: bool = True) -> str:
    """Get detailed information about a specific quantum device.

    Args:
        name: Device name (e.g. "dummy", "wuyue_hanyuan1")
        details: If True, include full specs. Default is True.

    Returns:
        JSON string with device details.
    """
    result = await _jsonrpc_call(
        "/v1/device", "get_device", {"name": name, "details": details}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_submit_job(
    source_code: list,
    code_type: str = "qasm",
    backend: str = "",
    flavor_id: str = "",
    extra_specs: dict | None = None,
    shots: int = 1024,
    job_name: str = "",
    description: str = "",
    transpiler: str = "",
    dry_run: bool = False,
    job_priority: int = 5,
) -> str:
    r"""Submit a quantum computing job to QCOS.

    The quantum circuit is specified as QASM source code. QCOS will
    transpile the circuit and execute it on the specified (or auto-
    selected) quantum device.

    Either ``backend`` or ``flavor_id`` must be specified (mutually
    exclusive). ``extra_specs`` is only allowed together with
    ``flavor_id``.

    Args:
        source_code: List of quantum source code strings. Each element is
            the raw source code text (not a file path). Example:
            ["OPENQASM 2.0; include \\"qelib1.inc\\"; qreg q[2]; ..."]
            For backward compatibility, dicts with a "code" key are also
            accepted (the "code" value is extracted automatically).
        code_type: Code type - "qasm", "qasm2", or "qasm3". Default "qasm".
        backend: Backend device name. Mutually exclusive with flavor_id.
            If empty, auto-scheduling is used (requires flavor_id).
        flavor_id: Flavor ID (UUID string) for auto scheduling.
            Mutually exclusive with backend.
        extra_specs: Extra scheduling specifications dict. Only allowed
            together with flavor_id. Overrides flavor specs.
        shots: Number of measurement shots. Default 1024.
        job_name: Optional job name.
        description: Optional job description.
        transpiler: Transpiler name. If empty, uses device default.
        dry_run: If True, simulate without real execution. Default False.
        job_priority: Job priority 1-10 (1=highest). Default 5.

    Returns:
        JSON string with job_id and submission status.
    """
    # Normalize source_code: accept both list[str] and list[dict]
    # (extract "code" from dicts for backward compatibility)
    normalized_code = []
    for item in source_code:
        if isinstance(item, dict):
            normalized_code.append(item.get("code", ""))
        elif isinstance(item, str):
            normalized_code.append(item)
        else:
            normalized_code.append(str(item))

    params = {
        "source_code": normalized_code,
        "code_type": code_type,
        "shots": shots,
        "job_type": "sampling",
        "dry_run": dry_run,
        "job_priority": job_priority,
    }
    if backend:
        params["backend"] = backend
    if flavor_id:
        params["flavor_id"] = flavor_id
    if extra_specs:
        params["extra_specs"] = extra_specs
    if job_name:
        params["job_name"] = job_name
    if description:
        params["description"] = description
    if transpiler:
        params["transpiler"] = transpiler

    result = await _jsonrpc_call("/v1/job", "submit_job", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_list_jobs(
    job_status: str = "",
    backend: str = "",
    page_size: int = 20,
    page_num: int = 1,
) -> str:
    """List quantum computing jobs with optional filtering.

    Args:
        job_status: Filter by job status (e.g. "running", "succeeded",
            "failed"). Empty string means no filter.
        backend: Filter by backend device name. Empty means no filter.
        page_size: Number of jobs per page. Default 20.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with job list.
    """
    query: dict[str, Any] = {
        "pagination": {"page_size": page_size, "page_num": page_num},
    }
    if job_status:
        query["filters"] = {"job_status": job_status}
    if backend:
        query.setdefault("filters", {})["backend"] = backend

    result = await _jsonrpc_call("/v1/job", "get_jobs", query)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_job_status(job_id: str) -> str:
    """Get the current status of a specific quantum job.

    Args:
        job_id: Job UUID string.

    Returns:
        JSON string with job status, progress, and metadata.
    """
    result = await _jsonrpc_call(
        "/v1/job", "get_job_status", {"job_id": job_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_job_result(job_id: str) -> str:
    """Get the execution results of a completed quantum job.

    Returns measurement counts, probabilities, and other result data.

    Args:
        job_id: Job UUID string.

    Returns:
        JSON string with job results including measurement counts.
    """
    result = await _jsonrpc_call(
        "/v1/job", "get_job_results", {"job_id": job_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_cancel_jobs(job_ids: list) -> str:
    """Cancel one or more quantum jobs.

    Only jobs that are in "queued" or "running" status can be cancelled.

    Args:
        job_ids: List of job UUID strings to cancel.

    Returns:
        JSON string with cancellation results.
    """
    result = await _jsonrpc_call(
        "/v1/job", "cancel_jobs", {"job_ids": job_ids}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_jobs(job_ids: list) -> str:
    """Delete one or more quantum jobs from the system.

    Deleted jobs are permanently removed. Cancel running jobs first.

    Args:
        job_ids: List of job UUID strings to delete.

    Returns:
        JSON string with deletion results.
    """
    result = await _jsonrpc_call(
        "/v1/job", "delete_jobs", {"job_ids": job_ids}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_job(
    job_id: str,
    job_name: str = "",
    description: str = "",
    job_priority: int = 0,
) -> str:
    """Update attributes of a queued job.

    Only jobs in QUEUED state can be updated. Pass non-empty / non-zero
    values for fields you want to change; omitted fields (empty string
    or 0) are ignored.

    Args:
        job_id: Job UUID string.
        job_name: New job name. Empty string means no change.
        description: New job description. Empty string means no change.
        job_priority: New job priority 1-10 (1=highest). 0 means no change.

    Returns:
        JSON string with updated job info.
    """
    params: dict = {"job_id": job_id}
    if job_name:
        params["job_name"] = job_name
    if description:
        params["description"] = description
    if job_priority:
        params["job_priority"] = job_priority
    result = await _jsonrpc_call("/v1/job", "update_job", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Flavor management tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_create_flavor(
    name: str,
    device_groups: list,
    description: str = "",
    is_public: bool = True,
    min_qubits: int = 0,
    max_qubits: int = 0,
    gate_fidelity_1q_min: float = 0.0,
    gate_fidelity_2q_min: float = 0.0,
    extra_properties: dict | None = None,
    project_id: str = "",
) -> str:
    """Create a flavor (preset scheduling policy).

    A flavor bundles scheduling constraints (qubit range, gate fidelity
    thresholds) with a set of device groups. At submit time, specifying
    a flavor_id triggers auto-scheduling across the flavor's device
    groups.

    Args:
        name: Flavor name (must be unique).
        device_groups: List of device group ID (UUID) strings. At least
            one is required.
        description: Optional flavor description.
        is_public: Whether the flavor is visible to all projects.
            Default True.
        min_qubits: Minimum qubit count filter. 0 means no limit.
        max_qubits: Maximum qubit count filter. 0 means no limit.
        gate_fidelity_1q_min: Min 1-qubit gate fidelity [0,1].
            0.0 means no limit.
        gate_fidelity_2q_min: Min 2-qubit gate fidelity [0,1].
            0.0 means no limit.
        extra_properties: Optional extra scheduling properties dict.
        project_id: Optional project ID (UUID string). Defaults to the
            current user's project.

    Returns:
        JSON string with the created flavor info.
    """
    params: dict = {"name": name, "device_groups": device_groups}
    if description:
        params["description"] = description
    params["is_public"] = is_public
    if min_qubits:
        params["min_qubits"] = min_qubits
    if max_qubits:
        params["max_qubits"] = max_qubits
    if gate_fidelity_1q_min:
        params["gate_fidelity_1q_min"] = gate_fidelity_1q_min
    if gate_fidelity_2q_min:
        params["gate_fidelity_2q_min"] = gate_fidelity_2q_min
    if extra_properties:
        params["extra_properties"] = extra_properties
    if project_id:
        params["project_id"] = project_id
    result = await _jsonrpc_call("/v1/flavor", "create_flavor", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_flavor(
    flavor_id: str,
    name: str = "",
    description: str = "",
    is_public: bool | None = None,
    min_qubits: int = 0,
    max_qubits: int = 0,
    gate_fidelity_1q_min: float = 0.0,
    gate_fidelity_2q_min: float = 0.0,
    extra_properties: dict | None = None,
    device_groups: list | None = None,
    project_id: str = "",
) -> str:
    """Update a flavor by ID.

    Only provided (non-empty) fields are updated. To clear
    extra_properties, pass an empty dict via extra_properties.

    Args:
        flavor_id: Flavor ID (UUID string).
        name: New flavor name. Empty string means no change.
        description: New description. Empty string means no change.
        is_public: New visibility. None means no change.
        min_qubits: New min qubits. 0 means no change.
        max_qubits: New max qubits. 0 means no change.
        gate_fidelity_1q_min: New min 1q fidelity. 0.0 means no change.
        gate_fidelity_2q_min: New min 2q fidelity. 0.0 means no change.
        extra_properties: Dict to merge into existing extra_properties.
            None means no change to extra_properties.
        device_groups: List of device group ID strings to replace the
            existing mapping. None means no change.
        project_id: Optional project ID (UUID string).

    Returns:
        JSON string with the updated flavor info.
    """
    params: dict = {"flavor_id": flavor_id}
    if name:
        params["name"] = name
    if description:
        params["description"] = description
    if is_public is not None:
        params["is_public"] = is_public
    if min_qubits:
        params["min_qubits"] = min_qubits
    if max_qubits:
        params["max_qubits"] = max_qubits
    if gate_fidelity_1q_min:
        params["gate_fidelity_1q_min"] = gate_fidelity_1q_min
    if gate_fidelity_2q_min:
        params["gate_fidelity_2q_min"] = gate_fidelity_2q_min
    if extra_properties is not None:
        params["extra_properties"] = extra_properties
    if device_groups is not None:
        params["device_groups"] = device_groups
    if project_id:
        params["project_id"] = project_id
    result = await _jsonrpc_call("/v1/flavor", "update_flavor", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_flavor(flavor_id: str) -> str:
    """Get a flavor by ID.

    Args:
        flavor_id: Flavor ID (UUID string).

    Returns:
        JSON string with flavor details including device_groups.
    """
    result = await _jsonrpc_call(
        "/v1/flavor", "get_flavor", {"flavor_id": flavor_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_flavors(
    flavor_name: str = "",
    flavor_ids: list | None = None,
    page_size: int = 0,
    page_num: int = 1,
) -> str:
    """List flavors with optional filtering and pagination.

    Args:
        flavor_name: Exact flavor name filter. Empty means no filter.
        flavor_ids: List of flavor ID (UUID) strings for IN-query.
            None means no filter.
        page_size: Page size for pagination. 0 means no pagination
            (return all).
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with flavor list or paginated response.
    """
    filters: dict = {}
    if flavor_name:
        filters["flavor_name"] = flavor_name
    if flavor_ids:
        filters["flavor_ids"] = flavor_ids
    params: dict = {}
    if filters:
        params["filters"] = filters
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call(
        "/v1/flavor", "get_flavors", params or None, query or None
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_flavors(flavor_ids: list) -> str:
    """Delete one or more flavors by ID (batch).

    Each flavor is deleted independently; individual failures do not
    abort the batch.

    Args:
        flavor_ids: List of flavor ID (UUID) strings to delete.

    Returns:
        JSON string with per-flavor deletion results.
    """
    result = await _jsonrpc_call(
        "/v1/flavor", "delete_flavors", {"flavor_ids": flavor_ids}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Device group management tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_create_device_group(
    name: str,
    device_names: list,
    description: str = "",
    is_public: bool = True,
    project_id: str = "",
) -> str:
    """Create a device group.

    A device group is a named collection of device names used by
    flavors for auto-scheduling.

    Args:
        name: Device group name (must be unique).
        device_names: List of device names in this group (required).
        description: Optional group description.
        is_public: Whether the group is visible to all projects.
            Default True.
        project_id: Optional project ID (UUID string). Defaults to the
            current user's project.

    Returns:
        JSON string with the created device group info.
    """
    params: dict = {"name": name, "device_names": device_names}
    if description:
        params["description"] = description
    params["is_public"] = is_public
    if project_id:
        params["project_id"] = project_id
    result = await _jsonrpc_call(
        "/v1/device_group", "create_device_group", params
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_device_group(
    group_id: str,
    name: str = "",
    description: str = "",
    device_names: list | None = None,
    is_public: bool | None = None,
    project_id: str = "",
) -> str:
    """Update a device group by ID.

    Only provided (non-empty) fields are updated.

    Args:
        group_id: Device group ID (UUID string).
        name: New group name. Empty string means no change.
        description: New description. Empty string means no change.
        device_names: New list of device names. None means no change.
        is_public: New visibility. None means no change.
        project_id: Optional project ID (UUID string).

    Returns:
        JSON string with the updated device group info.
    """
    params: dict = {"group_id": group_id}
    if name:
        params["name"] = name
    if description:
        params["description"] = description
    if device_names is not None:
        params["device_names"] = device_names
    if is_public is not None:
        params["is_public"] = is_public
    if project_id:
        params["project_id"] = project_id
    result = await _jsonrpc_call(
        "/v1/device_group", "update_device_group", params
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_device_group(group_id: str) -> str:
    """Get a device group by ID.

    Args:
        group_id: Device group ID (UUID string).

    Returns:
        JSON string with device group details.
    """
    result = await _jsonrpc_call(
        "/v1/device_group", "get_device_group", {"group_id": group_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_device_groups(
    group_name: str = "",
    group_ids: list | None = None,
    page_size: int = 0,
    page_num: int = 1,
) -> str:
    """List device groups with optional filtering and pagination.

    Args:
        group_name: Exact group name filter. Empty means no filter.
        group_ids: List of group ID (UUID) strings for IN-query.
            None means no filter.
        page_size: Page size for pagination. 0 means no pagination.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with device group list or paginated response.
    """
    filters: dict = {}
    if group_name:
        filters["group_name"] = group_name
    if group_ids:
        filters["group_ids"] = group_ids
    params: dict = {}
    if filters:
        params["filters"] = filters
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call(
        "/v1/device_group", "get_device_groups", params or None, query or None
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_device_groups(group_ids: list) -> str:
    """Delete one or more device groups by ID (batch).

    Groups referenced by flavors cannot be deleted; those are skipped
    with an error per-group.

    Args:
        group_ids: List of device group ID (UUID) strings to delete.

    Returns:
        JSON string with per-group deletion results.
    """
    result = await _jsonrpc_call(
        "/v1/device_group", "delete_device_groups", {"group_ids": group_ids}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Device operation tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_set_device(
    device_name: str,
    state: str = "",
    enable: bool | None = None,
    max_qubits: str = "",
    available_qubits: str = "",
) -> str:
    """Set device attributes (state, enable, max_qubits, available_qubits).

    Each field is optional; when omitted (empty string or None) the
    corresponding attribute is not changed.

    Args:
        device_name: Device name.
        state: Device state. One of: auto, online, offline, busy,
            calibrating, maintain, unknown. Empty string means no change.
        enable: Enable or disable the device. None means no change.
        max_qubits: Max qubits. "auto" restores driver default, or a
            positive integer string. Empty string means no change.
        available_qubits: Available qubits. "auto" restores driver
            default, or a positive integer string. Empty means no change.

    Returns:
        JSON string with updated device attributes.
    """
    params: dict = {"device_name": device_name}
    if state:
        params["state"] = state
    if enable is not None:
        params["enable"] = enable
    if max_qubits:
        params["max_qubits"] = max_qubits
    if available_qubits:
        params["available_qubits"] = available_qubits
    result = await _jsonrpc_call("/v1/device", "set_device", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_calibrate_device(
    device_name: str, method: str, options: dict | None = None
) -> str:
    """Trigger a calibration action on a device.

    Args:
        device_name: Device name.
        method: Calibration method name (device-specific).
        options: Optional calibration options dict.

    Returns:
        JSON string with calibration response details.
    """
    params: dict = {"device_name": device_name, "method": method}
    if options is not None:
        params["options"] = options
    result = await _jsonrpc_call("/v1/device", "calibrate_device", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_calibrate_results(device_name: str, method: str) -> str:
    """Get the results of a calibration action on a device.

    Args:
        device_name: Device name.
        method: Calibration method name.

    Returns:
        JSON string with calibration result details.
    """
    result = await _jsonrpc_call(
        "/v1/device",
        "get_calibrate_results",
        {"device_name": device_name, "method": method},
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_set_device_options(
    device_name: str, method: str, options: dict | None = None
) -> str:
    """Set device options for a specific method.

    Args:
        device_name: Device name.
        method: Method name (device-specific).
        options: Options dict to set.

    Returns:
        JSON string with the set-options response details.
    """
    params: dict = {"device_name": device_name, "method": method}
    if options is not None:
        params["options"] = options
    result = await _jsonrpc_call("/v1/device", "set_device_options", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_device_options(device_name: str, method: str) -> str:
    """Get device options for a specific method.

    Args:
        device_name: Device name.
        method: Method name (device-specific).

    Returns:
        JSON string with device option details.
    """
    result = await _jsonrpc_call(
        "/v1/device",
        "get_device_options",
        {"device_name": device_name, "method": method},
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Driver and transpiler info tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_get_drivers() -> str:
    """List all available quantum device drivers.

    Returns:
        JSON string mapping driver names to driver info (version,
        tech_type, max_qubits, supported transpilers/code types, etc.).
    """
    result = await _jsonrpc_call("/v1/driver", "get_drivers", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_driver(name: str) -> str:
    """Get detailed information about a specific device driver.

    Args:
        name: Driver name.

    Returns:
        JSON string with driver details.
    """
    result = await _jsonrpc_call("/v1/driver", "get_driver", {"name": name})
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_transpilers() -> str:
    """List all available quantum circuit transpilers.

    Returns:
        JSON string mapping transpiler names to transpiler info
        (alias, version, supported code types, options schema).
    """
    result = await _jsonrpc_call("/v1/transpiler", "get_transpilers", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_transpiler(name: str) -> str:
    """Get detailed information about a specific transpiler.

    Args:
        name: Transpiler name.

    Returns:
        JSON string with transpiler details.
    """
    result = await _jsonrpc_call(
        "/v1/transpiler", "get_transpiler", {"name": name}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Project management tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_create_project(project_name: str, description: str = "") -> str:
    """Create a new project.

    Args:
        project_name: Project name.
        description: Optional project description.

    Returns:
        JSON string with the created project info (id, name, etc.).
    """
    params: dict = {"project_name": project_name}
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/project", "create_project", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_project(project_id: str) -> str:
    """Get a project by ID.

    Args:
        project_id: Project ID (UUID string).

    Returns:
        JSON string with project details.
    """
    result = await _jsonrpc_call(
        "/v1/project", "get_project", {"project_id": project_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_projects(
    project_name: str = "", page_size: int = 0, page_num: int = 1
) -> str:
    """List projects with optional filtering and pagination.

    Args:
        project_name: Exact project name filter. Empty means no filter.
        page_size: Page size for pagination. 0 means no pagination.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with project list or paginated response.
    """
    filters: dict = {}
    if project_name:
        filters["project_name"] = project_name
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call(
        "/v1/project", "get_projects", None, query or None
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_project(
    project_id: str,
    project_name: str = "",
    description: str = "",
) -> str:
    """Update a project by ID.

    Only provided (non-empty) fields are updated.

    Args:
        project_id: Project ID (UUID string).
        project_name: New project name. Empty string means no change.
        description: New description. Empty string means no change.

    Returns:
        JSON string with the updated project info.
    """
    params: dict = {"project_id": project_id}
    if project_name:
        params["project_name"] = project_name
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/project", "update_project", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_project(project_id: str) -> str:
    """Delete a project by ID.

    Projects that have reserved resources (users, jobs) cannot be
    deleted until those are removed.

    Args:
        project_id: Project ID (UUID string).

    Returns:
        JSON string with deletion result (name, deleted_at).
    """
    result = await _jsonrpc_call(
        "/v1/project", "delete_project", {"project_id": project_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# User and role management tools (admin only)
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_get_current_user() -> str:
    """Get the current authenticated user's info.

    Uses the token stored by qcos_login. Useful for checking which
    user/project the MCP session is acting as.

    Returns:
        JSON string with current user info (user_name, project_id,
        roles, etc.).
    """
    result = await _jsonrpc_call("/v1/auth", "me", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_user_mgmt() -> str:
    """Get user management status (auth_mode, password policy).

    Returns:
        JSON string with auth_mode, password_expiry_days,
        max_login_attempts, lockout_duration_minutes.
    """
    result = await _jsonrpc_call("/v1/user", "get_user_mgmt", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_set_user_mgmt(auth_mode: str) -> str:
    """Set the user authentication mode.

    Args:
        auth_mode: Authentication mode - "no", "jwt", or
            "virtual_instance".

    Returns:
        JSON string with the updated auth_mode and message.
    """
    result = await _jsonrpc_call(
        "/v1/user", "set_user_mgmt", {"auth_mode": auth_mode}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_create_user(
    user_name: str,
    password: str,
    roles: list | None = None,
    project_id: str = "",
    password_expiry_days: int = 0,
    is_enabled: bool = True,
    is_locked: bool = False,
    description: str = "",
) -> str:
    """Create a new user.

    Args:
        user_name: User name.
        password: User password.
        roles: List of role names. Default ["user"] if None.
        project_id: Optional project ID (UUID string). Defaults to
            the default project.
        password_expiry_days: Password expiry days. 0 means use default.
        is_enabled: Whether the user is enabled. Default True.
        is_locked: Whether the user is locked. Default False.
        description: Optional user description.

    Returns:
        JSON string with the created user info.
    """
    params: dict = {"user_name": user_name, "password": password}
    if roles is not None:
        params["roles"] = roles
    if project_id:
        params["project_id"] = project_id
    if password_expiry_days:
        params["password_expiry_days"] = password_expiry_days
    params["is_enabled"] = is_enabled
    params["is_locked"] = is_locked
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/user", "create_user", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_user(user_id: str) -> str:
    """Get a user by ID.

    Args:
        user_id: User ID (UUID string).

    Returns:
        JSON string with user details.
    """
    result = await _jsonrpc_call("/v1/user", "get_user", {"user_id": user_id})
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_users(
    user_name: str = "", page_size: int = 0, page_num: int = 1
) -> str:
    """List users with optional filtering and pagination.

    Args:
        user_name: Filter by exact user name. Empty means no filter.
        page_size: Page size for pagination. 0 means no pagination.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with user list or paginated response.
    """
    filters: dict = {}
    if user_name:
        filters["user_name"] = user_name
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call("/v1/user", "get_users", None, query or None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_user(
    user_id: str,
    roles: list | None = None,
    password_expiry_days: int = 0,
    is_enabled: bool | None = None,
    is_locked: bool | None = None,
    description: str = "",
) -> str:
    """Update a user by ID.

    Only provided (non-empty / non-None) fields are updated.

    Args:
        user_id: User ID (UUID string).
        roles: New list of role names. None means no change.
        password_expiry_days: New password expiry days. 0 means no change.
        is_enabled: New enabled status. None means no change.
        is_locked: New locked status. None means no change.
        description: New description. Empty string means no change.

    Returns:
        JSON string with the updated user info.
    """
    params: dict = {"user_id": user_id}
    if roles is not None:
        params["roles"] = roles
    if password_expiry_days:
        params["password_expiry_days"] = password_expiry_days
    if is_enabled is not None:
        params["is_enabled"] = is_enabled
    if is_locked is not None:
        params["is_locked"] = is_locked
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/user", "update_user", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_user(user_id: str, force: bool = False) -> str:
    """Delete a user by ID.

    Non-force delete fails if the user has associated jobs. Force delete
    cascades deletion of related resources.

    Args:
        user_id: User ID (UUID string).
        force: Force delete and cascade-delete related resources.
            Default False.

    Returns:
        JSON string with deletion result (user_name, deleted_at).
    """
    params: dict = {"user_id": user_id, "force": force}
    result = await _jsonrpc_call("/v1/user", "delete_user", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_change_password(
    user_id: str, new_password: str, old_password: str = ""
) -> str:
    """Change a user's password.

    Non-admin password changes require the old_password. Admins can
    change any user's password without old_password.

    Args:
        user_id: User ID (UUID string).
        new_password: New password.
        old_password: Old password (required for non-admin changes).
            Empty string means skip (admin context).

    Returns:
        JSON string with password change result.
    """
    params: dict = {"user_id": user_id, "new_password": new_password}
    if old_password:
        params["old_password"] = old_password
    result = await _jsonrpc_call("/v1/user", "change_password", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_create_role(
    role_name: str,
    permissions: list | None = None,
    description: str = "",
) -> str:
    """Create a new role.

    Args:
        role_name: Role name.
        permissions: List of permission strings. Default [] if None.
        description: Optional role description.

    Returns:
        JSON string with the created role info.
    """
    params: dict = {"role_name": role_name}
    if permissions is not None:
        params["permissions"] = permissions
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/user", "create_role", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_role(role_id: str) -> str:
    """Get a role by ID.

    Args:
        role_id: Role ID (UUID string).

    Returns:
        JSON string with role details.
    """
    result = await _jsonrpc_call("/v1/user", "get_role", {"role_id": role_id})
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_roles(
    role_name: str = "", page_size: int = 0, page_num: int = 1
) -> str:
    """List roles with optional filtering and pagination.

    Args:
        role_name: Filter by exact role name. Empty means no filter.
        page_size: Page size for pagination. 0 means no pagination.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with role list or paginated response.
    """
    filters: dict = {}
    if role_name:
        filters["role_name"] = role_name
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call("/v1/user", "get_roles", None, query or None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_update_role(
    role_id: str,
    permissions: list | None = None,
    description: str = "",
) -> str:
    """Update a role by ID.

    Only provided (non-None / non-empty) fields are updated.

    Args:
        role_id: Role ID (UUID string).
        permissions: New list of permission strings. None means no change.
        description: New description. Empty string means no change.

    Returns:
        JSON string with the updated role info.
    """
    params: dict = {"role_id": role_id}
    if permissions is not None:
        params["permissions"] = permissions
    if description:
        params["description"] = description
    result = await _jsonrpc_call("/v1/user", "update_role", params)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_delete_role(role_id: str) -> str:
    """Delete a role by ID.

    Args:
        role_id: Role ID (UUID string).

    Returns:
        JSON string with deletion result (role_name).
    """
    result = await _jsonrpc_call(
        "/v1/user", "delete_role", {"role_id": role_id}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_login_logs(
    user_id: str = "",
    user_name: str = "",
    start_time: str = "",
    end_time: str = "",
    page_size: int = 0,
    page_num: int = 1,
) -> str:
    """Get login logs with optional filtering and pagination.

    user_id and user_name are mutually exclusive; provide at most one.

    Args:
        user_id: Filter by user ID (UUID string). Empty means no filter.
        user_name: Filter by user name. Empty means no filter.
        start_time: Filter by start time (ISO format). Empty = no filter.
        end_time: Filter by end time (ISO format). Empty = no filter.
        page_size: Page size for pagination. 0 means no pagination.
        page_num: Page number (1-based). Default 1.

    Returns:
        JSON string with login log list or paginated response.
    """
    params: dict = {}
    if user_id:
        params["user_id"] = user_id
    if user_name:
        params["user_name"] = user_name
    if start_time:
        params["start_time"] = start_time
    if end_time:
        params["end_time"] = end_time
    query: dict = {}
    if page_size:
        query["pagination"] = {"page_size": page_size, "page_num": page_num}
    result = await _jsonrpc_call(
        "/v1/user", "get_login_logs", params or None, query or None
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_clear_login_logs(user_id: str = "", user_name: str = "") -> str:
    """Clear login logs, optionally for a specific user.

    user_id and user_name are mutually exclusive. If neither is
    provided, all login logs are cleared.

    Args:
        user_id: Clear logs for this user ID (UUID string). Empty = all.
        user_name: Clear logs for this user name. Empty = all.

    Returns:
        JSON string with the count of deleted logs.
    """
    params: dict = {}
    if user_id:
        params["user_id"] = user_id
    if user_name:
        params["user_name"] = user_name
    result = await _jsonrpc_call(
        "/v1/user", "clear_login_logs", params or None
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# System monitoring tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def qcos_get_system_health() -> str:
    """Get overall system health status.

    Reports the health of core components: fastapi, redis, prefect,
    and worker processes.

    Returns:
        JSON string with system_healthy flag, heartbeat timestamp,
        and per-component status.
    """
    result = await _jsonrpc_call("/v1/metrics", "get_system_health", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_api_stats() -> str:
    """Get API request statistics.

    Returns:
        JSON string with total_requests, last_hour_requests,
        and last_day_requests.
    """
    result = await _jsonrpc_call("/v1/metrics", "get_api_stats", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_get_job_stats() -> str:
    """Get job statistics by status.

    Returns:
        JSON string with job counts grouped by status (total,
        completed, failed, running, queued, cancelled, etc.).
    """
    result = await _jsonrpc_call("/v1/metrics", "get_job_stats", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_ping(message: str = "") -> str:
    """Ping the QCOS system to check connectivity.

    Args:
        message: Optional ping message.

    Returns:
        JSON string with pong message.
    """
    params: dict = {}
    if message:
        params["message"] = message
    result = await _jsonrpc_call("/v1/system", "ping", params or None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_system_info() -> str:
    """Get high-level system info (total jobs count).

    Returns:
        JSON string with total_jobs_count.
    """
    result = await _jsonrpc_call("/v1/system", "system_info", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_show_mem() -> str:
    """Show API server process memory usage.

    Returns:
        JSON string with pid, rss_mb, vms_mb, thread_count,
        num_objects, cpu_percent.
    """
    result = await _jsonrpc_call("/v1/system", "show_mem", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_gc_mem(generations: int = 2) -> str:
    """Run garbage collection on the API server process.

    Args:
        generations: GC generations to collect (0, 1, or 2).
            Default 2 (full collection).

    Returns:
        JSON string with collected count, count before/after, etc.
    """
    result = await _jsonrpc_call(
        "/v1/system", "gc_mem", {"generations": generations}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_list_workers() -> str:
    """List all Prefect workers and their status.

    Returns:
        JSON string with a list of workers (worker_name, work_pool,
        device_name, worker_status, pid).
    """
    result = await _jsonrpc_call("/v1/system", "list_workers", None)
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


@mcp.tool()
async def qcos_restart_worker(worker_name: str) -> str:
    """Restart a specific Prefect worker.

    Args:
        worker_name: Worker name to restart.

    Returns:
        JSON string with restart result.
    """
    result = await _jsonrpc_call(
        "/v1/system", "restart_worker", {"worker_name": worker_name}
    )
    return json.dumps(result, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("qcos://version")
async def resource_version() -> str:
    """Provide QCOS system version information as a resource.

    Returns:
        JSON string with version, api_version, supported_api_versions,
        platform_version, and auth_mode info.
    """
    try:
        result = await _jsonrpc_call("/version", "version", {"details": False})
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        return f"Failed to get version: {e}"


@mcp.resource("qcos://devices")
async def resource_devices() -> str:
    """Provide available quantum device summary as a resource.

    Returns:
        JSON string mapping device names to basic info.
    """
    try:
        result = await _jsonrpc_call(
            "/v1/device", "get_devices", {"details": False}
        )
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        return f"Failed to get devices: {e}"
