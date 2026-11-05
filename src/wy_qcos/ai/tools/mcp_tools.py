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

"""Register QCOS MCP tools onto a pydantic-ai Agent.

Wraps the existing MCP server tool functions with pydantic-ai's
@agent.tool decorator, injecting auth context via AiDeps. `@agent.tool`
(not `@agent.tool_plain`) is required because every tool takes a
RunContext parameter to reach AiDeps; pydantic-ai rejects RunContext
annotations on plain tools.
"""

import asyncio
import logging
from pathlib import Path

from pydantic_ai import Agent, RunContext

from wy_qcos.ai.deps import AiDeps
from wy_qcos.api.mcp import mcp_server
from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)


def register_mcp_tools(agent: Agent[AiDeps, str]) -> None:
    """Register all QCOS MCP tools onto a pydantic-ai Agent."""

    @agent.tool
    async def qcos_list_devices(ctx: RunContext[AiDeps]) -> str:
        """List all available quantum computing devices."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_list_devices()

    @agent.tool
    async def qcos_get_job_status(ctx: RunContext[AiDeps], job_id: str) -> str:
        """Get the status of a specific quantum job."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_job_status(job_id)

    @agent.tool
    async def qcos_list_jobs(
        ctx: RunContext[AiDeps],
        job_status: str = "",
        backend: str = "",
        page_size: int = 20,
        page_num: int = 1,
    ) -> str:
        """List quantum jobs with optional status and backend filters."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_list_jobs(
                job_status=job_status,
                backend=backend,
                page_size=page_size,
                page_num=page_num,
            )

    @agent.tool
    async def qcos_get_system_health(ctx: RunContext[AiDeps]) -> str:
        """Get QCOS system health status."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_system_health()

    @agent.tool
    async def qcos_get_current_user(ctx: RunContext[AiDeps]) -> str:
        """Get current authenticated user info."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_current_user()

    @agent.tool
    async def qcos_get_version(ctx: RunContext[AiDeps]) -> str:
        """Get QCOS system version info."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_version()

    @agent.tool
    async def qcos_submit_job(
        ctx: RunContext[AiDeps],
        source_code: str,
        code_type: str = "qasm",
        backend: str = "",
        shots: int = 1024,
        job_name: str = "",
    ) -> str:
        """Submit a quantum computing job (QASM code)."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_submit_job(
                source_code=[source_code],
                code_type=code_type,
                backend=backend,
                shots=shots,
                job_name=job_name,
            )

    @agent.tool
    async def qcos_get_job_result(ctx: RunContext[AiDeps], job_id: str) -> str:
        """Get execution results of a completed job."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_job_result(job_id)

    @agent.tool
    async def qcos_cancel_jobs(
        ctx: RunContext[AiDeps], job_ids: list[str]
    ) -> str:
        """Cancel one or more quantum jobs."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_cancel_jobs(job_ids)

    @agent.tool
    async def qcos_get_device_detail(
        ctx: RunContext[AiDeps], name: str
    ) -> str:
        """Get detailed info for a specific quantum device."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_device_detail(name)

    @agent.tool
    async def qcos_get_job_stats(ctx: RunContext[AiDeps]) -> str:
        """Get job statistics grouped by status."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_job_stats()

    @agent.tool
    async def qcos_get_api_stats(ctx: RunContext[AiDeps]) -> str:
        """Get API request statistics."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_get_api_stats()

    @agent.tool
    async def qcos_read_file(
        ctx: RunContext[AiDeps],
        file_path: str,
        max_lines: int = 2000,
        offset: int = 1,
    ) -> str:
        """Read a local source code or documentation file.

        Args:
            ctx: Run context with injected dependencies.
            file_path: Path to the file relative to ``src/wy_qcos/``
                (e.g. ``"ai/agent.py"`` or
                ``"src/wy_qcos/ai/agent.py"`` - both work).
                If the exact path does not exist, a fuzzy search
                across ``src/wy_qcos/`` for a file with the same
                basename is performed, so short names like
                ``"config.py"`` usually resolve correctly.
                Absolute paths and ``..`` traversal are rejected
                for security.
            max_lines: Maximum number of lines to return (default 2000).
                Large files are truncated to prevent token overflow.
            offset: Line number to start reading from (1-based, default 1).

        Returns:
            File content as a string, with line numbers prepended.
        """
        with ctx.deps.auth_context():
            # Catch all validation/IO errors and return them as a
            # string instead of raising. Raising would bubble up to
            # pydantic-ai's tool_execute_error handler and crash the
            # whole SSE stream; returning a message lets the LLM read
            # the error and retry with a more precise path.
            try:
                return await _read_local_file(file_path, max_lines, offset)
            except (ValueError, FileNotFoundError) as e:
                logger.warning(f"qcos_read_file rejected: {e}")
                return (
                    f"ERROR: {e}\n"
                    f"Please retry with a more specific path under "
                    f"src/wy_qcos/ (e.g. 'ai/agent.py' instead of "
                    f"'agent.py')."
                )
            except Exception as e:
                logger.exception("qcos_read_file unexpected error")
                return f"ERROR: failed to read file '{file_path}': {e}"

    # ------------------------------------------------------------------
    # Reverse-proxy (observability) tools
    #
    # Bridge the proxy MCP tools registered on mcp_server so the AI
    # agent can answer questions about logs / metrics / alerts without
    # the WebUI having to expose those endpoints to the user.
    # ------------------------------------------------------------------

    @agent.tool
    async def qcos_proxy_get_health(ctx: RunContext[AiDeps]) -> str:
        """Get health status of all reverse-proxy upstream services.

        Probes Prometheus / Alertmanager / VictoriaLogs via the QCOS
        reverse proxy and returns a per-target status summary.
        """
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_get_health()

    @agent.tool
    async def qcos_proxy_query_metrics(
        ctx: RunContext[AiDeps],
        query: str,
        time: str = "",
        timeout: str = "",
    ) -> str:
        """Run an instant PromQL query against the proxied Prometheus.

        Args:
            ctx: Run context with injected dependencies.
            query: PromQL expression, e.g. ``up`` or
                ``rate(http_requests_total[5m])``.
            time: Optional RFC3339 or Unix timestamp evaluation time.
            timeout: Optional evaluation timeout (e.g. ``30s``).
        """
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_query_metrics(
                query=query, time=time, timeout=timeout
            )

    @agent.tool
    async def qcos_proxy_query_metrics_range(
        ctx: RunContext[AiDeps],
        query: str,
        start: str,
        end: str,
        step: str = "60s",
    ) -> str:
        """Run a range PromQL query against the proxied Prometheus."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_query_metrics_range(
                query=query, start=start, end=end, step=step
            )

    @agent.tool
    async def qcos_proxy_list_metric_names(ctx: RunContext[AiDeps]) -> str:
        """List all metric names known to the proxied Prometheus."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_list_metric_names()

    @agent.tool
    async def qcos_proxy_list_alerts(
        ctx: RunContext[AiDeps],
        status: str = "",
        silenced: bool | None = None,
        inhibited: bool | None = None,
    ) -> str:
        """List current alerts from the proxied Alertmanager.

        Args:
            ctx: Run context with injected dependencies.
            status: Optional filter: ``firing`` / ``pending`` /
                ``resolved``. Empty means no filter.
            silenced: Optional filter by silenced state.
            inhibited: Optional filter by inhibited state.
        """
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_list_alerts(
                status=status, silenced=silenced, inhibited=inhibited
            )

    @agent.tool
    async def qcos_proxy_list_silences(ctx: RunContext[AiDeps]) -> str:
        """List silence rules from the proxied Alertmanager."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_list_silences()

    @agent.tool
    async def qcos_proxy_query_logs(
        ctx: RunContext[AiDeps],
        query: str,
        limit: int = 100,
        start: str = "",
        end: str = "",
    ) -> str:
        """Run a LogsQL query against the proxied VictoriaLogs.

        Args:
            ctx: Run context with injected dependencies.
            query: LogsQL expression, e.g. ``_time:1h AND error``.
            limit: Max number of log entries (default 100).
            start: Optional RFC3339 start timestamp.
            end: Optional RFC3339 end timestamp.
        """
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_query_logs(
                query=query, limit=limit, start=start, end=end
            )

    @agent.tool
    async def qcos_proxy_log_tail(
        ctx: RunContext[AiDeps], lines: int = 100
    ) -> str:
        """Fetch the most recent log lines from the proxied VictoriaLogs."""
        with ctx.deps.auth_context():
            return await mcp_server.qcos_proxy_log_tail(lines=lines)


async def _read_local_file(
    file_path: str, max_lines: int = 2000, offset: int = 1
) -> str:
    """Read a local file and return its content with line numbers.

    Security constraints:
    - Only files under the project root directory are accessible.
    - Absolute paths are rejected.
    - Path traversal (../) is rejected.
    - Only files under src/wy_qcos/ are allowed.

    When the exact path does not exist, a fuzzy search is performed
    across src/wy_qcos/ for a file whose name matches the provided
    path's basename. If exactly one match is found it is used;
    otherwise an error listing the candidates is raised.
    """
    # Resolve source directory from config (src/wy_qcos/)
    src_dir = Path(Config.PROJECT_SRC_DIR).resolve()

    # Reject absolute paths and path traversal
    if Path(file_path).is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {file_path}")
    if ".." in file_path:
        raise ValueError(f"Path traversal is not allowed: {file_path}")

    # Resolve the full path and ensure it's under src/wy_qcos/
    full_path = (src_dir / file_path).resolve()
    try:
        full_path.relative_to(src_dir)
    except ValueError:
        raise ValueError(
            f"File is outside source directory: {file_path}"
        ) from None

    if not full_path.exists():
        # Fuzzy fallback: search for a file with the same basename
        # anywhere under src/wy_qcos/. This lets the AI answer
        # questions like "看一下 config.py 中有哪些参数?" without
        # knowing the exact directory.
        basename = Path(file_path).name
        # Exclude hidden / cache / venv directories (e.g. .pytest_cache)
        # so unrelated boilerplate files don't confuse the fuzzy match.
        _EXCLUDE_PARTS = {
            ".pytest_cache",
            ".git",
            ".ruff_cache",
            "__pycache__",
            ".mypy_cache",
            ".tox",
            "node_modules",
            ".venv",
            "venv",
        }
        matches = sorted(
            m
            for m in src_dir.rglob(basename)
            if not any(part in _EXCLUDE_PARTS for part in m.parts)
        )
        if not matches:
            raise FileNotFoundError(
                f"File not found: {file_path} "
                f"(no file named '{basename}' under src/wy_qcos/)"
            )
        if len(matches) > 1:
            candidates = "\n".join(
                f"  - {m.relative_to(src_dir)}" for m in matches
            )
            raise FileNotFoundError(
                f"File not found: {file_path}. "
                f"Multiple files named '{basename}' exist:\n{candidates}"
            )
        full_path = matches[0]
        rel = full_path.relative_to(src_dir)
        logger.info(f"Fuzzy-matched '{file_path}' to '{rel}'")
    if not full_path.is_file():
        raise ValueError(f"Not a file: {file_path}")

    # Read file content with line numbers
    def _read_sync() -> str:
        with open(full_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        # Apply offset and max_lines
        start_idx = max(0, offset - 1)
        end_idx = start_idx + max_lines
        selected_lines = lines[start_idx:end_idx]

        # Format with line numbers
        result = []
        for i, line in enumerate(selected_lines, start=start_idx + 1):
            result.append(f"{i:4d} | {line.rstrip()}")

        content = "\n".join(result)
        if end_idx < len(lines):
            content += (
                f"\n... ({len(lines) - end_idx} more lines, "
                f"total {len(lines)})"
            )
        return content

    return await asyncio.to_thread(_read_sync)
