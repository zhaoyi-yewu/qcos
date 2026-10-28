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

"""Parse /etc/qcos/qcos-webui.toml and generate runtime artifacts.

Outputs:
    1. env file (source-able by entrypoint.sh)
    2. webui-config.json (fetched by the SPA at boot)
    3. nginx endpoints.conf (per-endpoint reverse proxy blocks)
"""

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path


ENDPOINT_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")
DEFAULT_TOML_PATH = "/etc/qcos/qcos-webui.toml"
DEFAULT_ENV_OUT = "/tmp/webui.env"
DEFAULT_JSON_OUT = "/apps/webui-config.json"
# NOTE: the generated endpoints.conf must live outside /etc/nginx/default.d/
# because nginx.conf already includes /etc/nginx/default.d/*.conf via a
# wildcard. Placing the file under default.d would load it twice and cause
# nginx to fail with "duplicate location" errors.
DEFAULT_NGINX_OUT = "/etc/nginx/qcos/endpoints.conf"
CACERT_PREFIX = "/etc/qcos/ssl/"


def log(msg: str) -> None:
    print(f"[parse-webui-toml] {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    log(f"ERROR: {msg}")
    sys.exit(1)


def validate_endpoint(ep: dict, index: int) -> None:
    """Validate a single endpoint entry."""
    name = ep.get("name")
    if not name:
        fail(f"endpoint #{index}: missing 'name'")
    if not ENDPOINT_NAME_RE.match(name):
        fail(
            f"endpoint '{name}': name must match ^[a-zA-Z0-9_-]+$ "
            f"(letters, digits, dash, underscore)"
        )

    url = ep.get("url")
    if not url:
        fail(f"endpoint '{name}': missing 'url'")
    if not (url.startswith("http://") or url.startswith("https://")):
        fail(
            f"endpoint '{name}': url must start with http:// or https://, "
            f"got '{url}'"
        )

    # use_ssl: explicit SSL/TLS requirement (mirrors OpenStack Neutron style).
    # When true, the url must be https and cacert validation is enforced;
    # when false, the url must be http and cacert is ignored.
    use_ssl = ep.get("use_ssl")
    if use_ssl is None:
        # default: infer from url scheme
        use_ssl = url.startswith("https://")
        ep["use_ssl"] = use_ssl
    else:
        use_ssl = bool(use_ssl)
        ep["use_ssl"] = use_ssl
        if use_ssl and not url.startswith("https://"):
            fail(
                f"endpoint '{name}': use_ssl=true requires https:// url, "
                f"got '{url}'"
            )
        if not use_ssl and url.startswith("https://"):
            log(
                f"endpoint '{name}': use_ssl=false but url is https, "
                f"ssl verification disabled"
            )

    cacert = ep.get("cacert")
    if cacert:
        if not use_ssl:
            log(
                f"endpoint '{name}': cacert is set but use_ssl=false, "
                f"cacert will be ignored"
            )
        else:
            if not cacert.startswith(CACERT_PREFIX):
                fail(
                    f"endpoint '{name}': cacert must be under {CACERT_PREFIX}, "
                    f"got '{cacert}'"
                )
            if not os.path.isfile(cacert):
                fail(
                    f"endpoint '{name}': cacert file not found or not readable: "
                    f"{cacert}"
                )

    # prometheus_url / alertmanager_url: optional direct-access overrides.
    # When set, the WebUI bypasses the QCOS API reverse proxy and talks to
    # the given base URL directly. Only http:// or https:// are allowed.
    for key in ("prometheus_url", "alertmanager_url"):
        val = ep.get(key)
        if val:
            if not isinstance(val, str):
                fail(f"endpoint '{name}': {key} must be a string")
            if not (val.startswith("http://") or val.startswith("https://")):
                fail(
                    f"endpoint '{name}': {key} must start with http:// or https://, "
                    f"got '{val}'"
                )
            ep[key] = val.rstrip("/")


def validate_config(cfg: dict) -> dict:
    """Validate and normalize the raw TOML config."""
    default = cfg.get("DEFAULT", {})

    # Basic fields
    debug = bool(default.get("DEBUG", False))
    listen_ip = str(default.get("LISTEN_IP", "0.0.0.0"))
    listen_port = int(default.get("LISTEN_PORT", 18401))
    default_endpoint = str(default.get("DEFAULT_ENDPOINT", ""))
    probe_timeout = int(default.get("ENDPOINT_PROBE_TIMEOUT_MS", 3000))

    # Endpoints
    endpoints = default.get("QCOS_API_ENDPOINTS", [])
    if not isinstance(endpoints, list):
        fail("QCOS_API_ENDPOINTS must be a TOML array of inline tables")
    if len(endpoints) == 0:
        log("WARNING: QCOS_API_ENDPOINTS is empty; webui will have no selectable endpoint")

    seen_names = set()
    for i, ep in enumerate(endpoints):
        validate_endpoint(ep, i)
        name = ep["name"]
        if name in seen_names:
            fail(f"duplicate endpoint name: '{name}'")
        seen_names.add(name)

    # Default endpoint must exist when set
    if default_endpoint and default_endpoint not in seen_names:
        fail(
            f"DEFAULT_ENDPOINT '{default_endpoint}' does not match any "
            f"endpoint name in QCOS_API_ENDPOINTS"
        )

    return {
        "debug": debug,
        "listen_ip": listen_ip,
        "listen_port": listen_port,
        "default_endpoint": default_endpoint,
        "endpoint_probe_timeout_ms": probe_timeout,
        "endpoints": endpoints,
    }


def write_env(cfg: dict, path: str) -> None:
    """Write shell-sourceable env file."""
    lines = [
        "# Auto-generated by parse-webui-toml.py; do not edit",
        f"export LISTEN_IP={json.dumps(cfg['listen_ip'])}",
        f"export LISTEN_PORT={cfg['listen_port']}",
        f"export DEBUG={str(cfg['debug']).lower()}",
    ]
    if cfg["default_endpoint"]:
        lines.append(f"export DEFAULT_ENDPOINT={json.dumps(cfg['default_endpoint'])}")
    lines.append(
        f"export ENDPOINT_PROBE_TIMEOUT_MS={cfg['endpoint_probe_timeout_ms']}"
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote env file: {path}")


def write_json(cfg: dict, path: str) -> None:
    """Write webui-config.json consumed by the SPA."""
    endpoints = []
    for ep in cfg["endpoints"]:
        entry = {
            "name": ep["name"],
            "alias": ep.get("alias", ep["name"]),
            # Rewrite to same-origin reverse proxy path; the browser never
            # talks to the raw upstream URL directly.
            "url": f"/api/{ep['name']}",
            "use_ssl": ep.get("use_ssl", False),
        }
        # Optional direct-access overrides for monitoring backends.
        # When set, the SPA will call these URLs directly instead of
        # routing through the QCOS API reverse proxy.
        if ep.get("prometheus_url"):
            entry["prometheus_url"] = ep["prometheus_url"]
        if ep.get("alertmanager_url"):
            entry["alertmanager_url"] = ep["alertmanager_url"]
        endpoints.append(entry)

    payload = {
        "debug": cfg["debug"],
        "defaultEndpoint": cfg["default_endpoint"],
        "endpointProbeTimeoutMs": cfg["endpoint_probe_timeout_ms"],
        "endpoints": endpoints,
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"wrote webui-config.json: {path}")


def _nginx_location_block(ep: dict) -> str:
    """Build a single nginx location block for an endpoint."""
    name = ep["name"]
    url = ep["url"].rstrip("/")
    lines = [
        f"location /api/{name}/ {{",
        # Re-emit the security headers inline: nginx does NOT merge
        # add_header across levels, so this location would otherwise
        # silently drop the server-level security headers.
        '    add_header X-Frame-Options "SAMEORIGIN" always;',
        '    add_header X-Content-Type-Options "nosniff" always;',
        '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;',
        f"    proxy_pass {url}/;",
        "    proxy_set_header Host $host;",
        "    proxy_set_header X-Real-IP $remote_addr;",
        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "    proxy_set_header X-Forwarded-Proto $scheme;",
        "    proxy_http_version 1.1;",
        "    proxy_set_header Connection \"\";",
    ]
    if ep.get("use_ssl", False):
        lines.append("    proxy_ssl_verify on;")
        lines.append("    proxy_ssl_verify_depth 2;")
        cacert = ep.get("cacert")
        if cacert:
            lines.append(f"    proxy_ssl_trusted_certificate {cacert};")
    lines.append("}")
    return "\n".join(lines)


def write_nginx(cfg: dict, path: str) -> None:
    """Write nginx endpoints.conf with per-endpoint location blocks."""
    blocks = [
        "# Auto-generated by parse-webui-toml.py; do not edit",
        "# Per-endpoint reverse proxies for QCOS API",
        "",
    ]
    for ep in cfg["endpoints"]:
        blocks.append(_nginx_location_block(ep))
        blocks.append("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(blocks), encoding="utf-8")
    log(f"wrote nginx endpoints.conf: {path}")


DEFAULT_CONFIG = {
    "DEFAULT": {
        "DEBUG": False,
        "LISTEN_IP": "0.0.0.0",
        "LISTEN_PORT": 18401,
        "DEFAULT_ENDPOINT": "local",
        "ENDPOINT_PROBE_TIMEOUT_MS": 3000,
        "QCOS_API_ENDPOINTS": [
            {
                "name": "local",
                "alias": "本地开发环境",
                "url": "http://127.0.0.1:18400",
            }
        ],
    }
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse qcos-webui.toml and generate runtime configs")
    parser.add_argument("--toml", default=DEFAULT_TOML_PATH, help="input TOML path")
    parser.add_argument("--env-out", default=DEFAULT_ENV_OUT, help="output env file")
    parser.add_argument("--json-out", default=DEFAULT_JSON_OUT, help="output JSON file")
    parser.add_argument("--nginx-snippet-out", default=DEFAULT_NGINX_OUT, help="output nginx snippet")
    args = parser.parse_args()

    toml_path = Path(args.toml)
    if not toml_path.exists():
        log(f"WARNING: config file not found: {toml_path}, using built-in defaults")
        raw = DEFAULT_CONFIG
    else:
        try:
            raw = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            fail(f"invalid TOML in {toml_path}: {e}")

    cfg = validate_config(raw)
    write_env(cfg, args.env_out)
    write_json(cfg, args.json_out)
    write_nginx(cfg, args.nginx_snippet_out)
    log("done")


if __name__ == "__main__":
    main()
