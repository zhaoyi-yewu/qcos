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

"""Registry of reverse-proxy targets mounted under ``/v1/proxy/<name>``.

Each entry is a :class:`ProxyTarget` dataclass:

* ``path_segment`` — the URL path segment the proxy is mounted at,
  e.g. ``"prometheus"`` → ``/v1/proxy/prometheus``.
* ``config_getter`` — a zero-arg callable returning the configured
  upstream base URL. Returning an empty string disables the mount.
* ``health_path`` — a lightweight upstream path used by the
  ``get_proxy_health`` RPC to probe liveness (e.g. ``/-/healthy``
  for Prometheus and Alertmanager).

Adding a new proxied service requires only two changes:

1. Add a new ``XXX_BASE_URL`` field to
   :class:`wy_qcos.common.config.ProxySection` (default ``""``).
2. Append a new :class:`ProxyTarget` entry to :data:`PROXY_TARGETS`.
"""

from collections.abc import Callable
from dataclasses import dataclass

from wy_qcos.common.config import Config


@dataclass(frozen=True)
class ProxyTarget:
    """A single reverse-proxy upstream registration."""

    path_segment: str
    config_getter: Callable[[], str]
    health_path: str


#: All supported proxy targets. The getter is resolved at call time so
#: tests can monkeypatch ``Config.PROXY`` attributes without re-importing
#: this module.
PROXY_TARGETS: list[ProxyTarget] = [
    ProxyTarget(
        path_segment="prometheus",
        config_getter=lambda: Config.PROXY.PROMETHEUS_BASE_URL,
        health_path="/-/healthy",
    ),
    ProxyTarget(
        path_segment="alertmanager",
        config_getter=lambda: Config.PROXY.ALERTMANAGER_BASE_URL,
        health_path="/-/healthy",
    ),
]
