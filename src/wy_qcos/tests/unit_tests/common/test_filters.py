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

"""Unit tests for apply_memory_filters utility function."""

from wy_qcos.common.pagination import apply_memory_filters

from .test_pagination import make_dicts, make_items


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
