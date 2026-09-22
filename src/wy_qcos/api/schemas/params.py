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

"""Common request/response parameter models for list APIs.

This module collects the reusable pagination, sorting and generic
paginated-response models shared across all JSON-RPC list endpoints.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class SortParams(BaseModel):
    """Sort parameters for list APIs.

    Sort field list, prefix '-' means descending.
    Example: ["-created_at", "job_name"] means
    sort by created_at DESC, then job_name ASC.
    """

    model_config = ConfigDict(from_attributes=True)

    sort: list[str] = Field(
        default_factory=list,
        description="Sort fields, '-' prefix = descending",
    )


class PageParams(BaseModel):
    """Pagination parameters for list APIs."""

    model_config = ConfigDict(from_attributes=True)

    page: int = Field(default=1, ge=1, description="Page number, 1-based")
    page_size: int = Field(
        default=20,
        ge=-1,
        le=1000,
        description="Items per page, -1 for unlimited",
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
