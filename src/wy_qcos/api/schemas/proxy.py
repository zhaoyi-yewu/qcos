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

"""Pydantic schemas for the reverse-proxy health check API."""

from pydantic import BaseModel, Field


class GetProxyHealthRequest(BaseModel):
    """Get proxy health request (no parameters)."""


class ProxyHealthItem(BaseModel):
    """Health status of a single reverse-proxy upstream."""

    name: str = Field(..., description="Proxy path segment, e.g. 'prometheus'")
    path: str = Field(
        ...,
        description="Public mount path, e.g. '/v1/proxy/prometheus'",
    )
    base_url: str = Field(..., description="Configured upstream base URL")
    enabled: bool = Field(
        ...,
        description="Whether the proxy endpoint is enabled "
        "(base_url not empty)",
    )
    healthy: bool = Field(
        ..., description="Whether the upstream health probe succeeded"
    )
    status: str = Field(
        ...,
        description="Coarse status: 'online' / 'offline' / 'disabled'",
        examples=["online", "offline", "disabled"],
    )
    latency_ms: int | None = Field(
        None,
        description="Round-trip latency of the health probe "
        "(milliseconds). None when disabled or probe failed.",
    )
    detail: str = Field(
        "",
        description="Human-readable error detail when status != online",
    )


class GetProxyHealthResponse(BaseModel):
    """Get proxy health response."""

    targets: list[ProxyHealthItem] = Field(
        default_factory=list,
        description="Health status of every registered proxy target",
    )
