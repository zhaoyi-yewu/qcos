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

"""Unit tests for apply_memory_sort utility function."""

from wy_qcos.common.pagination import apply_memory_sort

from .test_pagination import make_dicts, make_items


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
