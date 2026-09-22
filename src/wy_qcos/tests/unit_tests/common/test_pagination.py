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

"""Unit tests for pagination utility functions."""

from pydantic import BaseModel

from wy_qcos.common.pagination import (
    apply_memory_filters,
    apply_memory_sort,
    paginate_list,
)


# -- Test fixtures ------------------------------------------------------- #


class Item(BaseModel):
    """Test item model for filter/sort tests."""

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


# -- apply_memory_sort tests --------------------------------------------- #


class TestApplyMemorySort:
    """Tests for apply_memory_sort."""

    def test_sort_ascending(self):
        """Sort ascending by field."""
        items = make_dicts()
        result = apply_memory_sort(items, ["name"])
        assert [r["name"] for r in result] == ["alpha", "beta", "gamma"]

    def test_sort_descending(self):
        """Sort descending by field."""
        items = make_dicts()
        result = apply_memory_sort(items, ["-name"])
        assert [r["name"] for r in result] == ["gamma", "beta", "alpha"]

    def test_sort_multi_field(self):
        """Sort by multiple fields."""
        items = [
            {"a": 1, "b": 2},
            {"a": 1, "b": 1},
            {"a": 2, "b": 1},
        ]
        result = apply_memory_sort(items, ["a", "-b"])
        # a ascending, then b descending within a=1
        assert result == [
            {"a": 1, "b": 2},
            {"a": 1, "b": 1},
            {"a": 2, "b": 1},
        ]

    def test_sort_with_pydantic_models(self):
        """Sort works on Pydantic model objects."""
        items = make_items()
        result = apply_memory_sort(items, ["value"])
        assert [r.value for r in result] == [1, 2, 3]

    def test_sort_no_sort_returns_copy(self):
        """Empty sort list returns a copy."""
        items = make_dicts()
        result = apply_memory_sort(items, [])
        assert result == items
        assert result is not items

    def test_sort_missing_field(self):
        """Missing field is handled gracefully."""
        items = [{"name": "a"}, {"name": "b"}]
        result = apply_memory_sort(items, ["missing"])
        # Should not raise, order may vary for None
        assert len(result) == 2


# -- apply_memory_filters tests ------------------------------------------ #


class TestApplyMemoryFilters:
    """Tests for apply_memory_filters."""

    def test_filter_string_match(self):
        """Filter by string field."""
        items = make_dicts()
        result = apply_memory_filters(items, {"name": "alpha"})
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_filter_int_match(self):
        """Filter by int field."""
        items = make_dicts()
        result = apply_memory_filters(items, {"value": 2})
        assert len(result) == 1
        assert result[0]["name"] == "beta"

    def test_filter_bool_direct(self):
        """Filter by bool field (direct bool)."""
        items = make_dicts()
        result = apply_memory_filters(items, {"active": True})
        assert len(result) == 2

    def test_filter_bool_string_coercion(self):
        """String 'true' coerces to bool True."""
        items = make_dicts()
        result = apply_memory_filters(items, {"active": "true"})
        assert len(result) == 2

    def test_filter_string_int_coercion(self):
        """String '2' coerces to int 2."""
        items = make_dicts()
        result = apply_memory_filters(items, {"value": "2"})
        assert len(result) == 1

    def test_filter_multiple_conditions(self):
        """Multiple conditions are AND logic."""
        items = make_dicts()
        result = apply_memory_filters(items, {"active": True, "value": 2})
        assert len(result) == 1
        assert result[0]["name"] == "beta"

    def test_filter_list_values(self):
        """List value uses IN semantics."""
        items = make_dicts()
        result = apply_memory_filters(items, {"name": ["alpha", "gamma"]})
        assert len(result) == 2

    def test_filter_no_match(self):
        """No matching items."""
        items = make_dicts()
        result = apply_memory_filters(items, {"name": "zzz"})
        assert len(result) == 0

    def test_filter_empty_filters(self):
        """Empty filters returns all items."""
        items = make_dicts()
        result = apply_memory_filters(items, None)
        assert len(result) == 3
        assert result is not items

    def test_filter_with_pydantic_models(self):
        """Filter works on Pydantic model objects."""
        items = make_items()
        result = apply_memory_filters(items, {"active": "true"})
        assert len(result) == 2
