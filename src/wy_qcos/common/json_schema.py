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

"""Convert Python schema declarations to annotated JSON Schema."""

import copy
import json
import logging
from typing import Any

from schema import And, Optional, Or, Schema

logger = logging.getLogger(__name__)

DRAFT_07 = "http://json-schema.org/draft-07/schema#"
_METADATA_KEYS = {
    "alias_name",
    "description",
    "field_constraints",
    "default",
    "writeOnly",
}
_CONSTRAINT_KEYWORDS = {
    "minimum": "minimum",
    "maximum": "maximum",
    "exclusive_minimum": "exclusiveMinimum",
    "exclusive_maximum": "exclusiveMaximum",
    "multiple_of": "multipleOf",
    "min_length": "minLength",
    "max_length": "maxLength",
    "pattern": "pattern",
    "min_items": "minItems",
    "max_items": "maxItems",
    "unique_items": "uniqueItems",
    "min_properties": "minProperties",
    "max_properties": "maxProperties",
    "enum": "enum",
}
_TYPE_MAPPING = {
    bool: "boolean",
    int: "integer",
    float: "number",
    str: "string",
    dict: "object",
    list: "array",
}


def _json_copy(value: Any) -> tuple[Any, bool]:
    """Return a JSON-compatible deep copy and whether it is safe."""
    try:
        copied = copy.deepcopy(value)
        json.dumps(copied, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError):
        return None, False
    return copied, True


def _metadata_for_child(metadata: dict, key: str) -> dict:
    child = metadata.get(key, {})
    return child if isinstance(child, dict) else {}


def _missing_metadata(path: str, alias_name: Any, description: Any) -> None:
    if not isinstance(alias_name, str) or not alias_name.strip():
        logger.warning("Schema metadata alias is missing at %s", path)
    if not isinstance(description, str) or not description.strip():
        logger.warning("Schema metadata description is missing at %s", path)


def _base_metadata(
    metadata: dict,
    field_name: str,
    path: str,
    log_missing: bool = True,
) -> tuple[dict, dict]:
    alias_name = metadata.get("alias_name")
    description = metadata.get("description")
    if log_missing:
        _missing_metadata(path, alias_name, description)
    if not isinstance(alias_name, str) or not alias_name.strip():
        alias_name = f"未命名（{field_name}）"
    if not isinstance(description, str) or not description.strip():
        description = "缺少字段说明，具体约束以后端提交校验为准。"

    raw_constraints = metadata.get("field_constraints", {})
    if not isinstance(raw_constraints, dict):
        raw_constraints = {}
    schema_constraints = raw_constraints.get("schema", {})
    runtime_constraints = raw_constraints.get("runtime", {})
    if not isinstance(schema_constraints, dict):
        schema_constraints = {}
    if not isinstance(runtime_constraints, dict):
        runtime_constraints = {}
    schema_constraints, schema_safe = _json_copy(schema_constraints)
    runtime_constraints, runtime_safe = _json_copy(runtime_constraints)
    if not schema_safe:
        schema_constraints = {}
    if not runtime_safe:
        runtime_constraints = {}
    constraints = {
        "schema": schema_constraints,
        "runtime": runtime_constraints,
    }
    annotations = {
        "alias_name": alias_name,
        "description": description,
        "field_constraints": constraints,
    }
    for key in ("default", "writeOnly"):
        if key not in metadata:
            continue
        value, safe = _json_copy(metadata[key])
        if safe:
            annotations[key] = value
    return annotations, constraints


def _merge_schema(target: dict, source: dict) -> None:
    """Merge simple schema fragments without retaining Python objects."""
    for key, value in source.items():
        if key in {
            "alias_name",
            "description",
            "field_constraints",
            "x-qcos-schema-status",
        }:
            continue
        if key == "type" and "type" in target and target[key] != value:
            current_type = target[key]
            if {current_type, value} == {"integer", "number"}:
                target[key] = "integer"
            else:
                target.pop("type")
                target.setdefault("allOf", []).extend([
                    {"type": current_type},
                    {"type": value},
                ])
        elif key == "anyOf" and "anyOf" in target:
            target[key].extend(copy.deepcopy(value))
        elif key not in target:
            target[key] = copy.deepcopy(value)


def _convert_and(
    schema_obj: And, metadata: dict, path: str
) -> tuple[dict, bool]:
    result: dict[str, Any] = {}
    has_callable = False
    for arg in schema_obj._args:
        if callable(arg) and not isinstance(arg, type):
            has_callable = True
            continue
        converted, child_callable = _convert(
            arg,
            metadata,
            path,
            log_missing=False,
            apply_metadata=False,
        )
        has_callable = has_callable or child_callable
        _merge_schema(result, converted)
    return result, has_callable


def _is_literal(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _combine_type_schemas(parts: list[dict]) -> dict | None:
    type_names = [part.get("type") for part in parts]
    if any(not isinstance(name, str) for name in type_names):
        return None
    if "integer" in type_names and "number" in type_names:
        parts = [part for part in parts if part.get("type") != "integer"]
        type_names = [part.get("type") for part in parts]

    structures = {}
    for part in parts:
        type_name = part["type"]
        structure = {
            key: value
            for key, value in part.items()
            if key not in _METADATA_KEYS and key != "type"
        }
        if any(key in {"anyOf", "enum"} for key in structure):
            return None
        if type_name in structures and structures[type_name] != structure:
            return None
        structures[type_name] = structure

    type_names = list(dict.fromkeys(type_names))
    result: dict[str, Any] = {
        "type": type_names[0] if len(type_names) == 1 else type_names
    }
    for structure in structures.values():
        for key, value in structure.items():
            if key in result and result[key] != value:
                return None
            result[key] = copy.deepcopy(value)
    return result


def _convert_or(
    schema_obj: Or, metadata: dict, path: str
) -> tuple[dict, bool]:
    args = schema_obj._args
    if args and all(_is_literal(arg) for arg in args):
        return {"enum": list(args)}, False

    parts = []
    has_callable = False
    for arg in args:
        converted, child_callable = _convert(
            arg,
            metadata,
            path,
            log_missing=False,
            apply_metadata=False,
        )
        has_callable = has_callable or child_callable
        parts.append(converted)
    combined = _combine_type_schemas(parts)
    if combined is not None:
        return combined, has_callable
    return {"anyOf": parts}, has_callable


def _convert_dict(
    schema_obj: dict,
    metadata: dict,
    path: str,
    log_missing: bool = True,
    apply_metadata: bool = True,
) -> tuple[dict, bool]:
    if len(schema_obj) == 1 and next(iter(schema_obj)) is str:
        value_schema = next(iter(schema_obj.values()))
        value_metadata = _metadata_for_child(metadata, "*")
        value_path = f"{path}.*" if path else "*"
        additional, has_callable = _convert(
            value_schema, value_metadata, value_path, field_name="*"
        )
        result: dict[str, Any] = {
            "type": "object",
            "additionalProperties": additional,
        }
        if not apply_metadata:
            return result, has_callable
        annotations, constraints = _base_metadata(
            metadata, path or "根", path, log_missing=log_missing
        )
        result.update(annotations)
        return _apply_constraints(result, constraints), has_callable

    properties = {}
    required = []
    has_callable = False
    for key, value_schema in schema_obj.items():
        is_optional = isinstance(key, Optional)
        if is_optional:
            field_name = key._schema
        elif isinstance(key, str):
            field_name = key
        else:
            raise TypeError(
                "Only named or dynamic string map keys are supported"
            )
        child_metadata = _metadata_for_child(metadata, field_name)
        child_path = f"{path}.{field_name}" if path else field_name
        converted, child_callable = _convert(
            value_schema,
            child_metadata,
            child_path,
            field_name=field_name,
        )
        has_callable = has_callable or child_callable
        if not is_optional:
            required.append(field_name)
            child_constraints = converted.setdefault(
                "field_constraints", {"schema": {}, "runtime": {}}
            )
            child_constraints["schema"]["required"] = True
        if is_optional and hasattr(key, "default"):
            default, safe = _json_copy(key.default)
            if safe:
                converted["default"] = default
        properties[field_name] = converted

    result = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        result["required"] = required
    if not apply_metadata:
        return result, has_callable
    annotations, constraints = _base_metadata(
        metadata, path or "根", path, log_missing=log_missing
    )
    result.update(annotations)
    return _apply_constraints(result, constraints), has_callable


def _apply_constraints(result: dict, constraints: dict) -> dict:
    schema_constraints = constraints["schema"]
    for source_key, target_key in _CONSTRAINT_KEYWORDS.items():
        if source_key in schema_constraints:
            result[target_key] = copy.deepcopy(schema_constraints[source_key])
    if "exact_items" in schema_constraints:
        result["minItems"] = schema_constraints["exact_items"]
        result["maxItems"] = schema_constraints["exact_items"]
    if schema_constraints.get("nullable"):
        current_type = result.get("type")
        if isinstance(current_type, str):
            if current_type != "null":
                result["type"] = [current_type, "null"]
        elif isinstance(current_type, list):
            if "null" not in current_type:
                result["type"] = [*current_type, "null"]
        elif current_type is None and "anyOf" in result:
            if {"type": "null"} not in result["anyOf"]:
                result["anyOf"].append({"type": "null"})
    return result


def _convert(
    schema_obj: Any,
    metadata: dict | None = None,
    path: str = "",
    field_name: str = "根",
    log_missing: bool = True,
    apply_metadata: bool = True,
) -> tuple[dict, bool]:
    metadata = metadata if isinstance(metadata, dict) else {}
    if isinstance(schema_obj, Schema):
        schema_obj = schema_obj._schema

    if isinstance(schema_obj, dict):
        return _convert_dict(
            schema_obj,
            metadata,
            path,
            log_missing=log_missing,
            apply_metadata=apply_metadata,
        )

    has_callable = False
    if isinstance(schema_obj, Or):
        result, has_callable = _convert_or(schema_obj, metadata, path)
    elif isinstance(schema_obj, And):
        result, has_callable = _convert_and(schema_obj, metadata, path)
    elif isinstance(schema_obj, type) and schema_obj in _TYPE_MAPPING:
        result = {"type": _TYPE_MAPPING[schema_obj]}
        if schema_obj is dict:
            result["additionalProperties"] = True
    elif isinstance(schema_obj, list):
        result = {"type": "array"}
        if schema_obj:
            item_metadata = _metadata_for_child(metadata, "items")
            item_path = f"{path}.items" if path else "items"
            items, has_callable = _convert(
                schema_obj[0],
                item_metadata,
                item_path,
                field_name="items",
                log_missing=False,
                apply_metadata=False,
            )
            result["items"] = items
    elif schema_obj is None:
        result = {"type": "null"}
    elif _is_literal(schema_obj):
        result = {"enum": [schema_obj]}
    elif callable(schema_obj):
        result = {}
        has_callable = True
    else:
        result = {}
        has_callable = True

    if not apply_metadata:
        return result, has_callable
    annotations, constraints = _base_metadata(
        metadata, field_name, path, log_missing=log_missing
    )
    result.update(annotations)
    if "enum" in result:
        constraints["schema"]["enum"] = copy.deepcopy(result["enum"])
        if any(value is None for value in result["enum"]):
            constraints["schema"]["nullable"] = True
    current_type = result.get("type")
    if current_type == "null" or (
        isinstance(current_type, list) and "null" in current_type
    ):
        constraints["schema"]["nullable"] = True
    result = _apply_constraints(result, constraints)
    if has_callable and not constraints["schema"]:
        result["x-qcos-schema-status"] = "partial"
    return result, has_callable


def schema_to_json_schema(
    schema_obj: Any, metadata: dict | None = None
) -> dict:
    """Convert a Python schema object to a self-contained draft-07 schema.

    Metadata is maintained beside the original schema. Missing metadata is
    replaced with safe display text so one incomplete plugin cannot break the
    version endpoint.

    Args:
        schema_obj: Python schema declaration.
        metadata: Independent metadata tree keyed by relative field path.

    Returns:
        JSON-serializable draft-07 schema with QCOS display annotations.
    """
    converted, _ = _convert(schema_obj, metadata)
    return {"$schema": DRAFT_07, **converted}
