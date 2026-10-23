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

"""Unit tests for apply_memory_search and parse_query utility functions."""

from wy_qcos.common.pagination import apply_memory_search, parse_query

from .test_pagination import make_dicts, make_items


# -- apply_memory_search tests ------------------------------------------- #


class TestApplyMemorySearch:
    """Tests for apply_memory_search()."""

    def test_search_basic(self):
        """Search matches substring in specified field."""
        items = make_dicts()
        result = apply_memory_search(items, "alpha", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_case_insensitive(self):
        """Search is case-insensitive."""
        items = make_dicts()
        result = apply_memory_search(items, "ALPHA", ["name"])
        assert len(result) == 1

    def test_search_multiple_fields(self):
        """Search matches any of the given fields (OR logic)."""
        items = make_dicts()
        result = apply_memory_search(items, "2", ["name", "value"])
        assert len(result) == 1
        assert result[0]["name"] == "beta"

    def test_search_no_match(self):
        """No match returns empty list."""
        items = make_dicts()
        result = apply_memory_search(items, "zzz", ["name"])
        assert len(result) == 0

    def test_search_empty_keyword(self):
        """Empty keyword returns all items."""
        items = make_dicts()
        result = apply_memory_search(items, "", ["name"])
        assert len(result) == 3
        assert result is not items

    def test_search_none_keyword(self):
        """None keyword returns all items."""
        items = make_dicts()
        result = apply_memory_search(items, None, ["name"])
        assert len(result) == 3

    def test_search_empty_fields(self):
        """Empty fields list returns all items."""
        items = make_dicts()
        result = apply_memory_search(items, "alpha", [])
        assert len(result) == 3

    def test_search_with_pydantic_models(self):
        """Search works on Pydantic model objects."""
        items = make_items()
        result = apply_memory_search(items, "beta", ["name"])
        assert len(result) == 1
        assert result[0].name == "beta"

    def test_search_none_field_value(self):
        """None field values are skipped without error."""
        items = [{"name": "alpha", "value": None}]
        result = apply_memory_search(items, "alpha", ["name", "value"])
        assert len(result) == 1

    def test_search_wildcard_contains(self):
        """SQL LIKE %keyword% matches contains."""
        items = make_dicts()
        result = apply_memory_search(items, "%alph%", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_wildcard_prefix(self):
        """SQL LIKE keyword% matches prefix."""
        items = make_dicts()
        result = apply_memory_search(items, "alph%", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_wildcard_suffix(self):
        """SQL LIKE %keyword matches suffix."""
        items = make_dicts()
        result = apply_memory_search(items, "%pha", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_wildcard_single_char(self):
        """SQL LIKE _ matches single character."""
        items = make_dicts()
        result = apply_memory_search(items, "alph_", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_multi_keyword_or(self):
        """Space-separated keywords use OR logic."""
        items = make_dicts()
        result = apply_memory_search(items, "alpha gamma", ["name"])
        assert len(result) == 2

    def test_search_multi_keyword_and(self):
        """Plus-prefixed keywords use AND logic."""
        items = make_dicts()
        # alpha contains 'a' and 'l' -> matches
        # beta contains 'a' but not 'l' -> no match
        result = apply_memory_search(items, "+a +l", ["name"])
        assert len(result) == 1
        assert result[0]["name"] == "alpha"

    def test_search_mixed_and_or(self):
        """Mixed AND/OR logic."""
        items = make_dicts()
        # Must contain 'a', optionally contain 'z' or 'm'
        result = apply_memory_search(items, "+a z m", ["name"])
        # alpha: has 'a', no 'z', no 'm' -> matches (OR part is optional)
        # beta: has 'a', no 'z', has 'm' -> matches
        # gamma: has 'a', no 'z', has 'm' -> matches
        assert len(result) == 3


# -- parse_query tests --------------------------------------------------- #


class TestParseQuery:
    """Tests for parse_query() with search parameter."""

    def test_parse_query_none(self):
        """None query returns all None."""
        filters, pagination, sort, search = parse_query(None)
        assert filters is None
        assert pagination is None
        assert sort is None
        assert search is None

    def test_parse_query_empty(self):
        """Empty query returns all None."""
        filters, pagination, sort, search = parse_query({})
        assert filters is None
        assert pagination is None
        assert sort is None
        assert search is None

    def test_parse_query_with_search(self):
        """Query with search extracts search string."""
        query = {
            "filters": {"name": "x"},
            "pagination": {"page": 1, "page_size": 10},
            "sort": ["-created_at"],
            "search": "keyword",
        }
        filters, pagination, sort, search = parse_query(query)
        assert filters == {"name": "x"}
        assert pagination.page == 1
        assert sort == ["-created_at"]
        assert search == "keyword"
