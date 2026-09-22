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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""In-memory pagination and sorting utilities for list APIs."""

from wy_qcos.api.schemas.params import PageParams


def parse_query(query):
    """Extract filters/pagination/sort from a JSON-RPC query dict.

    The pagination value (a plain dict from the wire) is validated
    into a PageParams object so downstream code can access
    .page / .page_size as attributes.

    Args:
        query: dict that may contain 'filters', 'pagination',
               and 'sort' keys, or None/empty.

    Returns:
        Tuple (filters, pagination, sort):
        - filters: dict | None
        - pagination: PageParams | None
        - sort: list[str] | None
    """
    if not query:
        return None, None, None
    filters = query.get("filters")
    raw_pagination = query.get("pagination")
    sort = query.get("sort")
    pagination = None
    if raw_pagination is not None:
        if isinstance(raw_pagination, PageParams):
            pagination = raw_pagination
        else:
            pagination = PageParams.model_validate(raw_pagination)
    return filters, pagination, sort


def _get_sort_key(item, field_name):
    """Extract sort key from a dict or object by field name.

    Args:
        item: a dict or an object with attributes
        field_name: the field/attribute name to extract

    Returns:
        The value of the field, or None if not found.
    """
    if isinstance(item, dict):
        return item.get(field_name)
    return getattr(item, field_name, None)


def apply_memory_sort(items, sort):
    """Sort an in-memory list by multiple fields.

    Each sort field may be prefixed with '-' for descending order.
    Multiple fields are applied as tie-breakers in order.

    Args:
        items: list of dicts or objects to sort
        sort: list of field names with optional '-' prefix.
              Example: ["-created_at", "name"] sorts by
              created_at DESC, then name ASC.

    Returns:
        A new sorted list (original list is not modified).
    """
    if not sort:
        return list(items)
    sorted_items = list(items)
    # Apply sorts in reverse order so the first field is the primary key.
    # Python's sort is stable, so earlier sorts are preserved as
    # tie-breakers.
    for field_spec in reversed(sort):
        descending = field_spec.startswith("-")
        field_name = field_spec[1:] if descending else field_spec

        def _sort_key(x, fn=field_name):
            val = _get_sort_key(x, fn)
            # Convert None to empty string for safe comparison
            if val is None:
                return ""
            return val

        sorted_items.sort(
            key=_sort_key,
            reverse=descending,
        )
    return sorted_items


def paginate_list(items, page, page_size):
    """Paginate an in-memory list.

    Args:
        items: full list of items
        page: 1-based page number
        page_size: items per page, -1 for unlimited

    Returns:
        dict with keys: items, total, page, page_size, total_pages
    """
    total = len(items)
    if page_size == -1:
        page_items = list(items)
        total_pages = 1
    else:
        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]
        if total > 0 and page_size > 0:
            total_pages = (total + page_size - 1) // page_size
        else:
            total_pages = 0
    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def _coerce_value(filter_value, item_value):
    """Coerce filter value to match item value type.

    Handles string "true"/"false" -> bool, numeric strings ->
    int/float, and string representations of other types.

    Args:
        filter_value: the filter value (usually a string from CLI)
        item_value: the actual item value to match against

    Returns:
        Coerced filter value, or original if no coercion needed.
    """
    if not isinstance(filter_value, str):
        return filter_value
    # If item is bool, convert string "true"/"false"
    if isinstance(item_value, bool):
        if filter_value.lower() in ("true", "1", "yes"):
            return True
        if filter_value.lower() in ("false", "0", "no"):
            return False
        return filter_value
    # If item is int, try converting string to int
    if isinstance(item_value, int) and not isinstance(item_value, bool):
        try:
            return int(filter_value)
        except ValueError:
            return filter_value
    # If item is float, try converting string to float
    if isinstance(item_value, float):
        try:
            return float(filter_value)
        except ValueError:
            return filter_value
    # Try string comparison of item_value
    return str(item_value) if not isinstance(item_value, str) else filter_value


def apply_memory_filters(items, filters):
    """Filter an in-memory list by exact match conditions.

    All filter conditions are combined with AND logic.
    String filter values are coerced to match the item value's type
    (e.g. "true" -> True, "123" -> 123).

    Args:
        items: list of dicts or objects to filter
        filters: dict of field -> value conditions.
                 If a value is a list, uses IN semantics.

    Returns:
        A new filtered list.
    """
    if not filters:
        return list(items)
    result = []
    for item in items:
        match = True
        for key, value in filters.items():
            item_value = _get_sort_key(item, key)
            if isinstance(value, list):
                # Coerce each value in the list
                coerced = [_coerce_value(v, item_value) for v in value]
                if item_value not in coerced:
                    match = False
                    break
            else:
                coerced = _coerce_value(value, item_value)
                if item_value != coerced:
                    match = False
                    break
        if match:
            result.append(item)
    return result
