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

import json

from jsonschema import Draft7Validator
from schema import And, Optional, Or

from wy_qcos.common.json_schema import DRAFT_07, schema_to_json_schema


def _field(
    alias="字段",
    description="字段用途说明。",
    schema=None,
    runtime=None,
    **children,
):
    metadata = {
        "alias_name": alias,
        "description": description,
    }
    if schema is not None or runtime is not None:
        metadata["field_constraints"] = {
            "schema": schema or {},
            "runtime": runtime or {},
        }
    metadata.update(children)
    return metadata


def _root(children):
    return {
        "alias_name": "测试根",
        "description": "测试根对象用途说明。",
        **children,
    }


def test_optional_required_nested_arrays_and_dynamic_map():
    schema = {
        "name": str,
        Optional("count"): int,
        Optional("nested"): {"enabled": bool},
        Optional("gate_times"): {str: Or(int, float)},
        Optional("numbers"): [int],
        Optional("bare_list"): list,
    }
    metadata = _root({
        "name": _field("名称", "必填名称。"),
        "count": _field("数量", "可选数量。"),
        "nested": _field(
            "嵌套对象",
            "嵌套配置。",
            enabled=_field("启用", "是否启用。"),
        ),
        "gate_times": _field(
            "门时长",
            "门名称到微秒时长的映射。",
            **{"*": _field("时长", "单门微秒时长。")},
        ),
        "numbers": _field("数值列表", "整数数组。"),
        "bare_list": _field("通用列表", "不限制元素的数组。"),
    })

    result = schema_to_json_schema(schema, metadata)

    assert result["$schema"] == DRAFT_07
    assert result["required"] == ["name"]
    assert result["additionalProperties"] is False
    assert (
        result["properties"]["name"]["field_constraints"]["schema"]["required"]
        is True
    )
    nested = result["properties"]["nested"]
    assert nested["required"] == ["enabled"]
    assert nested["properties"]["enabled"]["alias_name"] == "启用"
    dynamic_value = result["properties"]["gate_times"]["additionalProperties"]
    assert dynamic_value["type"] == "number"
    assert dynamic_value["description"] == "单门微秒时长。"
    assert result["properties"]["numbers"]["items"] == {"type": "integer"}
    assert "items" not in result["properties"]["bare_list"]
    json.dumps(result, ensure_ascii=False)


def test_or_and_known_lambda_constraints_and_runtime_isolation():
    schema = {
        Optional("choice"): Or("mct", "sabre"),
        Optional("number"): Or(int, float),
        Optional("score"): And(int, lambda value: value > 0),
        Optional("pair"): And(list, lambda value: len(value) == 2),
        Optional("nullable"): Or(str, None),
    }
    metadata = _root({
        "choice": _field("算法", "路由算法。"),
        "number": _field("数值", "整数或浮点数。"),
        "score": _field(
            "评分",
            "评分层数。",
            schema={"exclusive_minimum": 0},
            runtime={"maximum": 99},
        ),
        "pair": _field("模式", "两项模式。", schema={"exact_items": 2}),
        "nullable": _field("可空文本", "允许 null 的文本。"),
    })

    result = schema_to_json_schema(schema, metadata)
    properties = result["properties"]

    assert properties["choice"]["enum"] == ["mct", "sabre"]
    assert properties["choice"]["field_constraints"]["schema"]["enum"] == [
        "mct",
        "sabre",
    ]
    assert properties["number"]["type"] == "number"
    assert properties["score"]["exclusiveMinimum"] == 0
    assert "maximum" not in properties["score"]
    assert properties["score"]["field_constraints"]["runtime"] == {
        "maximum": 99
    }
    assert properties["pair"]["minItems"] == 2
    assert properties["pair"]["maxItems"] == 2
    assert properties["nullable"]["type"] == ["string", "null"]
    assert (
        properties["nullable"]["field_constraints"]["schema"]["nullable"]
        is True
    )
    assert "x-qcos-schema-status" not in properties["score"]


def test_unknown_callable_is_partial_and_metadata_falls_back():
    result = schema_to_json_schema(
        {Optional("value"): And(int, lambda value: value > 10)},
        _root({"value": _field("未知约束", "含未知运行时约束。")}),
    )

    field = result["properties"]["value"]
    assert field["type"] == "integer"
    assert field["x-qcos-schema-status"] == "partial"

    fallback = schema_to_json_schema({Optional("other"): str})
    assert fallback["alias_name"] == "未命名（根）"
    assert fallback["properties"]["other"]["alias_name"] == ("未命名（other）")
    json.dumps(fallback, ensure_ascii=False)


def test_length_and_numeric_constraints_use_draft_07_keywords():
    schema = {Optional("text"): str, Optional("value"): int}
    metadata = _root({
        "text": _field(
            "文本",
            "带长度限制的文本。",
            schema={"min_length": 1, "max_length": 8},
        ),
        "value": _field(
            "数值",
            "带排他上限的数值。",
            schema={"exclusive_maximum": 10, "multiple_of": 2},
        ),
    })

    properties = schema_to_json_schema(schema, metadata)["properties"]

    assert properties["text"]["minLength"] == 1
    assert properties["text"]["maxLength"] == 8
    assert properties["value"]["exclusiveMaximum"] == 10
    assert properties["value"]["multipleOf"] == 2


def test_and_uses_type_intersection_instead_of_any_of():
    numeric = schema_to_json_schema(
        And(Or(int, float), int),
        _field("整数交集", "数值与整数的交集。"),
    )

    assert numeric["type"] == "integer"
    assert "anyOf" not in numeric
    assert Draft7Validator(numeric).is_valid(1)
    assert not Draft7Validator(numeric).is_valid(1.5)

    incompatible = schema_to_json_schema(
        And(int, str),
        _field("不兼容交集", "整数与字符串的交集。"),
    )
    assert incompatible["allOf"] == [
        {"type": "integer"},
        {"type": "string"},
    ]
    assert not Draft7Validator(incompatible).is_valid(1)
    assert not Draft7Validator(incompatible).is_valid("1")


def test_literal_or_none_marks_nullable_metadata():
    result = schema_to_json_schema(
        Or("enabled", None),
        _field("可空枚举", "允许 enabled 或 null。"),
    )

    assert result["enum"] == ["enabled", None]
    assert result["field_constraints"]["schema"]["nullable"] is True
    assert Draft7Validator(result).is_valid("enabled")
    assert Draft7Validator(result).is_valid(None)
    assert not Draft7Validator(result).is_valid("disabled")
