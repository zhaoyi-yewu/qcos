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

"""Build the standalone HTML documentation pages for QCOS APIs.

Outputs two files under ``docs/openapi-docs/dist/``:

1. ``qcos-api-docs.html``  - ReDoc rendering of the FastAPI OpenAPI schema
   (the RESTful/JSON-RPC endpoints).
2. ``qcos-mcp-docs.html``  - Custom HTML rendering of the MCP tool catalog
   exposed at ``POST/SSE /v1/ai/mcp``. MCP is not a RESTful protocol, so
   the tools cannot be expressed in OpenAPI; instead we use the MCP SDK's
   built-in reflection API ``mcp.list_tools()`` which returns each tool
   with its ``name`` / ``description`` / ``input_schema`` (a pydantic
   generated JSON Schema). Only constructing the ``MCPServer`` instance
   and calling ``list_tools()`` is required - no network listener, no
   background tasks, no QCOS backend connection.

ReDoc template trick originally from
https://github.com/Redocly/redoc/issues/726#issuecomment-645414239
"""

import asyncio
import html as html_module
import json
import os
import sys

import fastapi_jsonrpc as jsonrpc

current_dir = os.path.split(os.path.realpath(__file__))[0]
top_dir = os.path.abspath(f"{current_dir}/../../src")
sys.path.insert(0, top_dir)
from wy_qcos.api.fastapi_server import app
from wy_qcos.api.mcp.mcp_server import mcp as mcp_server
from wy_qcos.common.constant import Constant
from wy_qcos.common.qcos_version import QcosVersion

# MCP transport endpoint (kept in sync with fastapi_server.MCP_ENDPOINT).
MCP_ENDPOINT = "/v1/ai/mcp"

HTML_TEMPLATE = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8">
    <title>QCOS API Doc - v{QcosVersion.VERSION}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            margin: 0;
            padding: 0;
        }}
    </style>
    <style data-styled="" data-styled-version="4.4.1"></style>
</head>
<body>
    <div id="redoc-container"></div>
    <script src="js/redoc.standalone.js"> </script>
    <script>
        var spec = %s;
        Redoc.init(spec, {{}}, document.getElementById("redoc-container"));
    </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# MCP tool introspection via the MCP SDK's native reflection API
# ---------------------------------------------------------------------------


def _group_of(name):
    """Map a tool name like ``qcos_list_devices`` to its sidebar group.

    Strip the ``qcos_`` prefix, drop any leading verbs (get/list/create/
    update/delete/set/submit/cancel/...), then take the next token as the
    resource. Falls back to ``misc`` for short names.
    """
    verbs = {
        "get", "list", "create", "update", "delete", "set", "submit",
        "cancel", "calibrate", "clear", "change", "restart", "show",
        "gc", "ping", "login", "system",
    }
    parts = name.split("_")
    if parts and parts[0] == "qcos":
        parts = parts[1:]
    while parts and parts[0] in verbs:
        parts = parts[1:]
    return parts[0] if parts else "misc"


def _split_summary_body(description):
    """Split a tool description into first-line summary and remaining body.

    FastMCP already merged the docstring's ``Args:`` / ``Returns:``
    sections into ``input_schema.<param>.description`` and the tool's
    ``output_schema``, so the raw description here typically only carries
    the leading free-form prose. We still keep the body in case authors
    write multi-paragraph explanations.
    """
    if not description:
        return "", ""
    text = description.strip()
    if not text:
        return "", ""
    lines = text.splitlines()
    summary = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    return summary, body


def _json_schema_type_str(prop):
    """Render a JSON Schema property as a readable type string.

    Handles ``type``, ``anyOf`` (Optional), ``$ref``, ``items``, and the
    pydantic-generated ``additionalProperties`` patterns that show up for
    ``dict`` / ``list`` / ``Optional[...]`` annotations.
    """
    if not isinstance(prop, dict):
        return "any"
    if "anyOf" in prop:
        variants = [_json_schema_type_str(p) for p in prop["anyOf"]]
        # Deduplicate while preserving order
        seen = []
        for v in variants:
            if v not in seen:
                seen.append(v)
        return " | ".join(seen)
    if "$ref" in prop:
        return prop["$ref"].rsplit("/", 1)[-1]
    t = prop.get("type")
    if t == "array":
        items = prop.get("items") or {}
        item_t = _json_schema_type_str(items) if items else "any"
        return f"list[{item_t}]"
    if t == "object":
        if prop.get("additionalProperties") in (True, {}, None):
            return "dict"
        return "object"
    if t == "null":
        return "None"
    if t:
        return str(t)
    return "any"


def _mcp_tool_to_dict(tool):
    """Convert an ``mcp.types.Tool`` pydantic model into a render-ready dict.

    The ``input_schema`` produced by FastMCP/MCPServer is already a fully
    resolved JSON Schema with ``properties`` / ``required`` /
    ``description`` / ``default`` / ``title`` populated from the function
    signature and docstring - no AST parsing required.
    """
    summary, body = _split_summary_body(tool.description or "")

    schema = tool.input_schema or {}
    properties = schema.get("properties") or {}
    required_names = set(schema.get("required") or [])

    params = []
    for name, prop in properties.items():
        if not isinstance(prop, dict):
            prop = {}
        params.append(
            {
                "name": name,
                "type": _json_schema_type_str(prop),
                "default": prop.get("default", None),
                "has_default": "default" in prop,
                "required": name in required_names,
                "description": prop.get("description", "")
                or prop.get("title", ""),
            }
        )

    return {
        "name": tool.name,
        "summary": summary,
        "description": body,
        "params": params,
        "group": _group_of(tool.name),
    }


def extract_mcp_tools():
    """Fetch the MCP tool catalog via ``mcp.list_tools()``.

    Only constructs the ``MCPServer`` instance (already done at module
    import time) and awaits its ``list_tools()`` coroutine. No HTTP
    listener is started, no QCOS backend connection is made; the call is
    pure in-process reflection.
    """
    tools = asyncio.run(mcp_server.list_tools())
    result = [_mcp_tool_to_dict(t) for t in tools]
    result.sort(key=lambda t: t["name"])
    return result


# ---------------------------------------------------------------------------
# MCP HTML rendering
# ---------------------------------------------------------------------------


_MCP_CSS = """
:root {
    --brand: #1f6feb;
    --bg: #fafbfc;
    --sidebar-bg: #f4f6f8;
    --border: #e1e4e8;
    --text: #24292e;
    --muted: #6a737d;
    --code-bg: #f6f8fa;
    --required: #d73a49;
}
* { box-sizing: border-box; }
html, body {
    margin: 0; padding: 0; height: 100%;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
                 "Hiragino Sans GB", "Microsoft YaHei", Helvetica, Arial,
                 sans-serif;
    color: var(--text); background: var(--bg);
}
.layout { display: flex; min-height: 100vh; }
.sidebar {
    width: 260px; flex-shrink: 0; background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    padding: 16px 12px; overflow-y: auto; height: 100vh;
    position: sticky; top: 0;
}
.sidebar h1 { font-size: 16px; margin: 0 0 4px; }
.sidebar .subtitle { font-size: 12px; color: var(--muted); margin-bottom: 16px; }
.sidebar .endpoint {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    background: var(--code-bg); padding: 4px 6px; border-radius: 4px;
    font-size: 12px; margin-bottom: 16px; word-break: break-all;
}
.sidebar .group { margin-bottom: 8px; }
.sidebar .group-title {
    font-size: 12px; text-transform: uppercase; color: var(--muted);
    letter-spacing: 0.5px; padding: 4px 8px;
}
.sidebar .tool-link {
    display: block; padding: 4px 12px; font-size: 13px;
    color: var(--text); text-decoration: none;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    border-left: 2px solid transparent;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sidebar .tool-link:hover { background: #e8ebee; }
.sidebar .tool-link.active {
    border-left-color: var(--brand); background: #e8f0fe; color: var(--brand);
}
.content { flex: 1; padding: 24px 32px; max-width: 980px; }
.content header {
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px; margin-bottom: 24px;
}
.content header h1 { margin: 0 0 4px; font-size: 24px; }
.content header p { margin: 4px 0; color: var(--muted); }
.tool-card {
    background: #fff; border: 1px solid var(--border); border-radius: 6px;
    padding: 20px 24px; margin-bottom: 20px; scroll-margin-top: 20px;
}
.tool-card h2 {
    margin: 0 0 4px; font-size: 18px;
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    color: var(--brand);
}
.tool-card .group-tag {
    display: inline-block; font-size: 11px; background: #eef1f4;
    padding: 2px 6px; border-radius: 10px; color: var(--muted);
    margin-left: 8px; vertical-align: middle;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.tool-card .summary { font-weight: 600; margin: 8px 0; }
.tool-card .description {
    color: var(--text); white-space: pre-wrap; margin: 8px 0 12px;
    font-size: 14px; line-height: 1.55;
}
.tool-card h3 {
    margin: 12px 0 6px; font-size: 13px; text-transform: uppercase;
    letter-spacing: 0.5px; color: var(--muted);
    border-bottom: 1px solid var(--border); padding-bottom: 4px;
}
.params-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.params-table th, .params-table td {
    text-align: left; padding: 6px 8px;
    border-bottom: 1px solid var(--border); vertical-align: top;
}
.params-table th { background: var(--code-bg); font-weight: 600; }
.params-table .p-name,
.params-table .p-type,
.params-table .p-default {
    font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
.params-table .p-type { color: var(--muted); font-size: 12px; }
.params-table .p-required { color: var(--required); font-weight: 600; }
.params-table .p-default { font-size: 12px; color: var(--muted); }
.footer {
    color: var(--muted); font-size: 12px;
    padding: 12px 0; text-align: center;
}
@media (max-width: 800px) { .sidebar { display: none; } }
"""

_MCP_JS = """
document.addEventListener('DOMContentLoaded', function () {
    var links = document.querySelectorAll('.tool-link');
    var cards = document.querySelectorAll('.tool-card');
    function activate(id) {
        links.forEach(function (a) {
            a.classList.toggle('active', a.getAttribute('href') === '#' + id);
        });
    }
    links.forEach(function (a) {
        a.addEventListener('click', function () {
            activate(a.getAttribute('href').slice(1));
        });
    });
    var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
            if (e.isIntersecting) { activate(e.target.id); }
        });
    }, { rootMargin: '-40% 0px -55% 0px' });
    cards.forEach(function (c) { observer.observe(c); });
});
"""


def _esc(text):
    return html_module.escape(str(text) if text is not None else "")


def _render_mcp_param_row(p):
    default = json.dumps(p["default"]) if p["has_default"] else ""
    required = '<span class="p-required">*</span>' if p["required"] else ""
    return (
        "<tr>"
        f'<td class="p-name">{_esc(p["name"])}{required}</td>'
        f'<td class="p-type">{_esc(p["type"])}</td>'
        f'<td class="p-default">{_esc(default)}</td>'
        f'<td class="p-desc">{_esc(p["description"])}</td>'
        "</tr>"
    )


def _render_mcp_tool_card(tool):
    params_html = ""
    if tool["params"]:
        rows = "\n".join(_render_mcp_param_row(p) for p in tool["params"])
        params_html = f"""
        <h3>Parameters</h3>
        <table class="params-table">
            <thead>
                <tr><th>Name</th><th>Type</th><th>Default</th><th>Description</th></tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """
    return f"""
    <div class="tool-card" id="{_esc(tool['name'])}">
        <h2>{_esc(tool['name'])}
            <span class="group-tag">{_esc(tool['group'])}</span>
        </h2>
        <div class="summary">{_esc(tool['summary'])}</div>
        <div class="description">{_esc(tool['description'])}</div>
        {params_html}
    </div>
    """


def render_mcp_html(tools, version):
    """Render the MCP tool catalog as a standalone HTML page."""
    groups = {}
    for t in tools:
        groups.setdefault(t["group"], []).append(t)
    group_names = sorted(groups.keys())

    sidebar_groups = []
    for g in group_names:
        links = "\n".join(
            f'<a class="tool-link" href="#{_esc(t["name"])}">{_esc(t["name"])}</a>'
            for t in groups[g]
        )
        sidebar_groups.append(
            f'<div class="group">'
            f'<div class="group-title">{_esc(g)} ({len(groups[g])})</div>'
            f"{links}</div>"
        )
    sidebar_html = "\n".join(sidebar_groups)
    cards_html = "\n".join(_render_mcp_tool_card(t) for t in tools)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{_esc(Constant.PLATFORM_NAME)} MCP API Doc - v{_esc(version)}</title>
    <style>{_MCP_CSS}</style>
</head>
<body>
<div class="layout">
    <aside class="sidebar">
        <h1>{_esc(Constant.PLATFORM_NAME)} MCP API</h1>
        <div class="subtitle">v{_esc(version)} &middot; {len(tools)} tools</div>
        <div class="endpoint">POST/SSE {_esc(MCP_ENDPOINT)}</div>
        {sidebar_html}
    </aside>
    <main class="content">
        <header>
            <h1>{_esc(Constant.PLATFORM_NAME)} MCP Tools Reference</h1>
            <p>
                Auto-generated via the MCP SDK's native reflection API
                (<code>mcp.list_tools()</code>). The QCOS MCP server speaks
                the Model Context Protocol over
                <code>POST/SSE {_esc(MCP_ENDPOINT)}</code>; each tool below
                corresponds to one entry in the MCP <code>tools/list</code>
                response.
            </p>
        </header>
        {cards_html}
        <div class="footer">
            Generated by docs/openapi-docs/make-openapi-docs.py
            &middot; {_esc(Constant.PLATFORM_NAME)} v{_esc(version)}
        </div>
    </main>
</div>
<script>{_MCP_JS}</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_openapi_html(output_dir):
    """Render the main OpenAPI ReDoc page (existing behaviour)."""
    file_path = os.path.join(output_dir, "qcos-api-docs.html")
    with open(file_path, "w") as fd:
        openapi_dict = app.openapi()
        openapi_dict["info"]["title"] = f"{Constant.PLATFORM_NAME} API文档"
        openapi_dict["info"]["version"] = f"v{QcosVersion.VERSION}"
        # Drop JSON-RPC entrypoint dispatcher routes (e.g. POST /v1/auth).
        # They are just batch dispatchers and only produce noise "POST
        # Entrypoint" headings in ReDoc; real methods live under sub-paths
        # such as /v1/auth/login.
        entrypoint_paths = {
            route.path
            for route in app.routes
            if isinstance(route, jsonrpc.EntrypointRoute)
        }
        openapi_dict["paths"] = {
            path: methods
            for path, methods in openapi_dict["paths"].items()
            if path not in entrypoint_paths
        }
        openapi_str = json.dumps(openapi_dict)
        print(HTML_TEMPLATE % openapi_str, file=fd)
    print(f"Successfully created qcos api docs: {file_path}")


def _build_mcp_html(output_dir):
    """Render the MCP tool catalog HTML page via ``mcp.list_tools()``."""
    tools = extract_mcp_tools()
    if not tools:
        raise RuntimeError(
            "mcp.list_tools() returned an empty tool catalog"
        )
    file_path = os.path.join(output_dir, "qcos-mcp-docs.html")
    with open(file_path, "w", encoding="utf-8") as fd:
        fd.write(render_mcp_html(tools, QcosVersion.VERSION))
    print(
        f"Successfully created qcos mcp api docs: {file_path} "
        f"({len(tools)} tools)"
    )


if __name__ == "__main__":
    output_dir = f"{current_dir}/dist"
    os.makedirs(output_dir, mode=0o755, exist_ok=True)
    _build_openapi_html(output_dir)
    _build_mcp_html(output_dir)
