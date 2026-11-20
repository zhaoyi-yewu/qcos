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

"""Build version capability schemas without reading live option values."""

import copy
import logging
from collections.abc import Mapping
from typing import Any

from wy_qcos.common.args_schema import (
    JOB_OPTIONS_METADATA,
    JOB_OPTIONS_SCHEMA,
)
from wy_qcos.common.json_schema import schema_to_json_schema
from wy_qcos.driver.driver_base import DriverBase
from wy_qcos.qem.mitigation_factory import MitigationFactory
from wy_qcos.transpiler.transpiler_base import TranspilerBase
from wy_qcos.scheduler.request_spec import (
    EXTRA_SPECS_METADATA,
    EXTRA_SPECS_SCHEMA,
)

logger = logging.getLogger(__name__)

_QEM_ROOTS = {
    "readout": ("读出误差缓解", "配置读出误差校准和测量结果校正。"),
    "rem": ("读出误差缓解别名", "配置 readout 策略的等价 rem 入口。"),
    "zne": ("零噪声外推", "配置门折叠、噪声倍率和零噪声外推。"),
    "dd": ("动态解耦", "配置空闲窗口中的动态解耦脉冲序列和门时长。"),
}


def _safe_text(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _root_metadata(
    alias_name: str, description: str, children: dict | None = None
) -> dict:
    metadata = {
        "alias_name": alias_name,
        "description": description,
    }
    if children:
        metadata.update(copy.deepcopy(children))
    return metadata


def _generic_object(root: dict, status: str | None = None) -> dict:
    result = schema_to_json_schema(dict, root)
    if status:
        result["x-qcos-schema-status"] = status
    return result


def _log_conversion_failure(category: str, name: str, exc: Exception) -> None:
    logger.warning(
        "Unable to export %s schema for %s: %s",
        category,
        name,
        type(exc).__name__,
    )


def _driver_root(driver_name: str, driver: Any, category: str) -> dict:
    try:
        alias = _safe_text(driver.get_alias_name(), driver_name)
        description = _safe_text(driver.get_description(), "当前量子设备驱动")
    except Exception as exc:
        _log_conversion_failure(category, driver_name, exc)
        alias = driver_name
        description = "当前量子设备驱动"
    subject = "量子纠错" if category == "qec_options" else "驱动"
    return _root_metadata(
        f"{alias}{subject}参数",
        f"{description}的{subject}提交参数，最终校验以后端为准。",
    )


def _transpiler_root(name: str, transpiler: Any) -> dict:
    try:
        alias = _safe_text(transpiler.get_alias_name(), name)
    except Exception as exc:
        _log_conversion_failure("transpiler_options", name, exc)
        alias = name
    return _root_metadata(
        f"{alias}转译参数",
        f"{name} 转译器的提交参数，最终校验以后端为准。",
    )


def _declared_option_names(raw_schema: dict) -> set[str]:
    """Return option names declared by a base class schema."""
    return {getattr(key, "schema", key) for key in raw_schema}


def _mark_parameter_scopes(schema: dict, common_names: set[str]) -> dict:
    """Mark top-level properties as common or implementation-specific."""
    for name, node in schema.get("properties", {}).items():
        if isinstance(node, dict):
            scope = "common" if name in common_names else "specific"
            node["x-qcos-parameter-scope"] = scope
    return schema


def _build_driver_options(drivers: Mapping) -> dict:
    result = {}
    common_names = _declared_option_names(DriverBase().driver_options_schema)
    for name, driver in drivers.items():
        root = _driver_root(name, driver, "driver_options")
        try:
            schema = driver.get_driver_options_schema()
            metadata = driver.get_driver_options_metadata()
            if not isinstance(metadata, dict):
                metadata = {}
            root.update(copy.deepcopy(metadata))
            result[name] = _mark_parameter_scopes(
                schema_to_json_schema(schema, root), common_names
            )
        except Exception as exc:
            _log_conversion_failure("driver_options", name, exc)
            result[name] = _generic_object(root, "unavailable")
    return result


def _build_transpiler_options(transpilers: Mapping) -> dict:
    result = {}
    common_names = _declared_option_names(
        TranspilerBase.base_transpiler_options_schema
    )
    for name, transpiler in transpilers.items():
        root = _transpiler_root(name, transpiler)
        try:
            schema = transpiler.get_transpiler_options_schema()
            metadata = transpiler.get_transpiler_options_metadata()
            if not isinstance(metadata, dict):
                metadata = {}
            root.update(copy.deepcopy(metadata))
            if schema is None:
                schema = {}
            result[name] = _mark_parameter_scopes(
                schema_to_json_schema(schema, root), common_names
            )
        except Exception as exc:
            _log_conversion_failure("transpiler_options", name, exc)
            result[name] = _generic_object(root, "unavailable")
    return result


def _build_qec_options(drivers: Mapping) -> dict:
    result = {}
    for name, driver in drivers.items():
        root = _driver_root(name, driver, "qec_options")
        try:
            schema = driver.get_qec_options_schema()
            metadata = driver.get_qec_options_metadata()
            if not isinstance(metadata, dict):
                metadata = {}
            root.update(copy.deepcopy(metadata))
            if schema is None:
                result[name] = _generic_object(root)
            else:
                result[name] = schema_to_json_schema(schema, root)
        except Exception as exc:
            _log_conversion_failure("qec_options", name, exc)
            result[name] = _generic_object(root, "unavailable")
    return result


def _build_qem_options() -> dict:
    factory = MitigationFactory()
    registry = dict(factory._registry)
    properties = {}
    for name, (alias_name, description) in _QEM_ROOTS.items():
        root = _root_metadata(alias_name, description)
        try:
            strategy_class = registry[name]
            schema = strategy_class.get_qem_options_schema()
            metadata = strategy_class.get_qem_options_metadata()
            if not isinstance(metadata, dict):
                metadata = {}
            root.update(copy.deepcopy(metadata))
            strategy_schema = schema_to_json_schema(schema, root)
            strategy_schema.pop("$schema", None)
            properties[name] = strategy_schema
        except Exception as exc:
            _log_conversion_failure("qem_options", name, exc)
            fallback = _generic_object(root, "unavailable")
            fallback.pop("$schema", None)
            properties[name] = fallback

    root = _root_metadata(
        "量子误差缓解参数",
        "按策略名称配置量子误差缓解；未知名称仍由运行时记录告警并跳过。",
    )
    result = schema_to_json_schema({}, root)
    result["properties"] = properties
    result["additionalProperties"] = True
    return result


def build_capabilities_schemas(drivers: Mapping, transpilers: Mapping) -> dict:
    """Build all six capability schema entries from loaded plugins.

    Args:
        drivers: Loaded driver instances indexed by driver name.
        transpilers: Exposed transpiler instances indexed by public name.

    Returns:
        JSON-serializable dynamic and static capability schemas.
    """
    options_root = _root_metadata(
        "作业通用参数",
        "配置线路或 QUBO 的自动拆分和精度约减行为。",
        JOB_OPTIONS_METADATA,
    )
    extra_specs_root = _root_metadata(
        "Flavor 扩展调度参数",
        "覆盖 Flavor 调度约束的封闭十项参数集合，"
        "字段缺省与 null 的语义以调度代码为准。",
        EXTRA_SPECS_METADATA,
    )
    return {
        "driver_options": _build_driver_options(drivers),
        "transpiler_options": _build_transpiler_options(transpilers),
        "options": schema_to_json_schema(JOB_OPTIONS_SCHEMA, options_root),
        "qem_options": _build_qem_options(),
        "qec_options": _build_qec_options(drivers),
        "extra_specs": schema_to_json_schema(
            EXTRA_SPECS_SCHEMA, extra_specs_root
        ),
    }
