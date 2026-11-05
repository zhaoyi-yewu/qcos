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

"""AI Agent dependency injection context.

Uses contextvars to propagate user identity through async call chains
so that MCP tools can enforce per-user authorization.
"""

import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, field


# Context variable holding the current AiDeps instance
_ai_deps_var: contextvars.ContextVar["AiDeps | None"] = contextvars.ContextVar(
    "ai_deps", default=None
)


@dataclass
class AiDeps:
    """Dependencies injected into pydantic-ai tools."""

    user_id: str
    session_id: str
    project_id: str | None = None
    rag_context: str = ""
    history: list[dict] = field(default_factory=list)

    @contextmanager
    def auth_context(self):
        """Context manager that sets this AiDeps as the current context."""
        token = _ai_deps_var.set(self)
        try:
            yield
        finally:
            _ai_deps_var.reset(token)


def get_current_deps() -> AiDeps | None:
    """Return the current AiDeps from contextvars, if any."""
    return _ai_deps_var.get()
