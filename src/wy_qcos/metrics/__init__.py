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
from .metrics_collector import MetricsCollector

_metrics_collector: MetricsCollector | None = None


def init_metrics_collector() -> MetricsCollector:
    """Create the global MetricsCollector singleton.

    Must be called explicitly from service startup code (the FastAPI
    lifespan handler) instead of relying on import-time side effects,
    so that merely importing this package in tooling contexts
    (Sphinx apidoc builds, scripts, unit-test collection) neither
    registers Prometheus metrics nor emits initialization logs.

    Returns:
        The initialized MetricsCollector singleton.
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_metrics_collector() -> MetricsCollector:
    """Return the initialized MetricsCollector singleton.

    Returns:
        The MetricsCollector singleton.

    Raises:
        RuntimeError: If init_metrics_collector() has not been called.
    """
    if _metrics_collector is None:
        raise RuntimeError(
            "MetricsCollector is not initialized. Call "
            "wy_qcos.metrics.init_metrics_collector() during service "
            "startup first."
        )
    return _metrics_collector
