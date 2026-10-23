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

"""Unit tests for paginate_list utility function and shared fixtures."""

from pydantic import BaseModel

from wy_qcos.common.pagination import paginate_list


# -- Shared fixtures (used by test_filters/test_search/test_sort) -------- #


class Item(BaseModel):
    """Test item model for filter/sort/search tests."""

    name: str
    value: int
    active: bool


def make_items():
    """Build a list of test items."""
    return [
        Item(name="beta", value=2, active=True),
        Item(name="alpha", value=1, active=False),
        Item(name="gamma", value=3, active=True),
    ]


def make_dicts():
    """Build a list of test dicts."""
    return [
        {"name": "beta", "value": 2, "active": True},
        {"name": "alpha", "value": 1, "active": False},
        {"name": "gamma", "value": 3, "active": True},
    ]


# -- paginate_list tests ------------------------------------------------- #


class TestPaginateList:
    """Tests for paginate_list."""

    def test_single_page(self):
        """Items fit in one page."""
        items = list(range(10))
        result = paginate_list(items, page=1, page_size=20)
        assert result["items"] == items
        assert result["total"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 20
        assert result["total_pages"] == 1

    def test_multi_page(self):
        """Items span multiple pages."""
        items = list(range(25))
        result = paginate_list(items, page=2, page_size=10)
        assert result["items"] == list(range(10, 20))
        assert result["total"] == 25
        assert result["total_pages"] == 3

    def test_last_page_partial(self):
        """Last page has fewer items."""
        items = list(range(25))
        result = paginate_list(items, page=3, page_size=10)
        assert result["items"] == list(range(20, 25))
        assert result["total_pages"] == 3

    def test_empty_list(self):
        """Empty list returns empty page."""
        result = paginate_list([], page=1, page_size=10)
        assert result["items"] == []
        assert result["total"] == 0
        assert result["total_pages"] == 0

    def test_page_out_of_range(self):
        """Page beyond range returns empty items."""
        items = list(range(5))
        result = paginate_list(items, page=10, page_size=10)
        assert result["items"] == []
        assert result["total"] == 5
        assert result["total_pages"] == 1

    def test_page_size_negative_one_unlimited(self):
        """page_size=-1 returns all items."""
        items = list(range(50))
        result = paginate_list(items, page=1, page_size=-1)
        assert result["items"] == items
        assert result["total"] == 50
        assert result["total_pages"] == 1
