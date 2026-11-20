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

import re
from typing import Any
from unittest.mock import patch

import pytest

from wy_qcos.common.capability_schemas import build_capabilities_schemas
from wy_qcos.driver.cetc.driver_cetc_base import DriverCetcBase
from wy_qcos.driver.driver_qubo_base import DriverQuboBase
from wy_qcos.driver.dummy.driver_dummy import DriverDummy
from wy_qcos.driver.qudoor.driver_qudoor_abaqu100 import (
    DriverQudoorAbaQu100,
)
from wy_qcos.driver.stim.driver_stim import DriverStim
from wy_qcos.qem.mitigation_factory import MitigationFactory
from wy_qcos.scheduler.request_spec import RequestSpec
from wy_qcos.transpiler.cmss.transpiler_cmss import TranspilerCmss
from wy_qcos.transpiler.dummy.transpiler_dummy import TranspilerDummy

TranspilerHighPerformanceCmss: Any = None
try:
    from wy_qcos.transpiler.cmss.transpiler_cmss_for_cpp import (
        TranspilerHighPerformanceCmss as _TranspilerHighPerformanceCmss,
    )
except ModuleNotFoundError:
    pass
else:
    TranspilerHighPerformanceCmss = _TranspilerHighPerformanceCmss


CONSTRAINT_KEYWORDS = {
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


def _assert_complete_metadata(schema, path="root"):
    for key in ("alias_name", "description"):
        assert isinstance(schema.get(key), str), f"{path}.{key} is missing"
        assert schema[key].strip(), f"{path}.{key} is empty"
        assert re.search(r"[\u4e00-\u9fff]", schema[key]), path
    constraints = schema.get("field_constraints")
    assert isinstance(constraints, dict), path
    assert set(constraints) == {"schema", "runtime"}, path
    assert isinstance(constraints["schema"], dict), path
    assert isinstance(constraints["runtime"], dict), path

    for name, child in schema.get("properties", {}).items():
        _assert_complete_metadata(child, f"{path}.{name}")
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        _assert_complete_metadata(additional, f"{path}.*")


def _assert_constraints_match(schema, path="root", required=None):
    constraints = schema["field_constraints"]["schema"]
    for source, target in CONSTRAINT_KEYWORDS.items():
        if source in constraints:
            assert schema.get(target) == constraints[source], path
    if "exact_items" in constraints:
        assert schema["minItems"] == constraints["exact_items"], path
        assert schema["maxItems"] == constraints["exact_items"], path
    if constraints.get("nullable"):
        assert "null" in schema["type"], path
    if constraints.get("required"):
        assert required is not None and path.rsplit(".", 1)[-1] in required

    child_required = schema.get("required")
    for name, child in schema.get("properties", {}).items():
        _assert_constraints_match(
            child, f"{path}.{name}", required=child_required
        )
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        _assert_constraints_match(additional, f"{path}.*")


def _drivers():
    return {
        "DriverDummy": DriverDummy(),
        "DriverCetcBase": DriverCetcBase(),
        "DriverQudoorAbaQu100": DriverQudoorAbaQu100(),
        "DriverQuboBase": DriverQuboBase(),
        "DriverStim": DriverStim(),
    }


def _transpilers(include_hp=True):
    transpilers = {
        "cmss": TranspilerCmss(),
        "dummy": TranspilerDummy(),
    }
    if include_hp and TranspilerHighPerformanceCmss is not None:
        transpilers["high_performance_cmss"] = TranspilerHighPerformanceCmss()
    return transpilers


@pytest.fixture(scope="module")
def capabilities():
    return build_capabilities_schemas(_drivers(), _transpilers())


def test_recursive_metadata_and_constraints_for_all_current_fields(
    capabilities,
):
    _assert_complete_metadata(capabilities["options"], "options")
    _assert_complete_metadata(capabilities["qem_options"], "qem_options")
    _assert_complete_metadata(capabilities["extra_specs"], "extra_specs")
    _assert_constraints_match(capabilities["options"], "options")
    _assert_constraints_match(capabilities["qem_options"], "qem_options")
    _assert_constraints_match(capabilities["extra_specs"], "extra_specs")

    for category in ("driver_options", "transpiler_options", "qec_options"):
        for name, schema in capabilities[category].items():
            path = f"{category}.{name}"
            _assert_complete_metadata(schema, path)
            _assert_constraints_match(schema, path)


def test_qec_and_transpiler_none_semantics(capabilities):
    generic_qec = capabilities["qec_options"]["DriverDummy"]
    assert generic_qec["type"] == "object"
    assert generic_qec["additionalProperties"] is True

    stim_qec = capabilities["qec_options"]["DriverStim"]
    assert stim_qec["additionalProperties"] is False
    assert stim_qec["required"] == ["qec_code"]
    error_inject = stim_qec["properties"]["error_inject"]
    assert set(error_inject["required"]) == {"error_type", "noise_prob"}
    assert "minimum" not in error_inject["properties"]["noise_prob"]

    empty_transpiler = capabilities["transpiler_options"]["dummy"]
    assert empty_transpiler["properties"] == {}
    assert empty_transpiler["additionalProperties"] is False


def test_qem_root_allows_unknown_strategies(capabilities):
    qem_root = capabilities["qem_options"]
    assert qem_root["additionalProperties"] is True
    assert "unknown_strategy" not in qem_root["properties"]

    for strategy in qem_root["properties"].values():
        assert strategy["additionalProperties"] is False
        assert strategy["properties"]


def test_qem_strategies_nullable_map(capabilities):
    qem = capabilities["qem_options"]["properties"]
    assert set(qem) == {"readout", "zne", "dd"}
    for name in ("readout", "zne", "dd"):
        assert qem[name]["properties"]["enabled"]["default"] is False

    nullable_paths = {
        "zne.scale_factors",
        "zne.scale_factor",
        "zne.polynomial_degree",
        "zne.folding_seed",
        "zne.fold_gate_names",
        "dd.gate_times",
    }
    for strategy_name, strategy in qem.items():
        for field_name, field in strategy["properties"].items():
            nullable = field["field_constraints"]["schema"].get(
                "nullable", False
            )
            assert nullable is (
                f"{strategy_name}.{field_name}" in nullable_paths
            )
    zne = qem["zne"]["properties"]
    assert zne["scale_factors"]["items"]["type"] == "number"
    assert "null" not in zne["scale_factors"]["items"]["type"]
    assert "Factory" in zne["fold_gate_names"]["description"]
    gate_times = qem["dd"]["properties"]["gate_times"]
    assert gate_times["type"] == ["object", "null"]
    assert gate_times["additionalProperties"]["type"] == "number"
    assert "微秒" in gate_times["description"]


def test_extra_specs_ten_keys_nullable_and_sensitive_values(capabilities):
    extra_specs = capabilities["extra_specs"]
    assert len(extra_specs["properties"]) == 10
    assert extra_specs["additionalProperties"] is False
    for name, field in extra_specs["properties"].items():
        assert field["field_constraints"]["schema"]["nullable"] is True
        assert "null" in field["type"], name
        assert "minimum" not in field
        assert "maximum" not in field
    for name in ("qc:gate_fidelity_1q_min", "qc:gate_fidelity_2q_min"):
        assert "不生效" in extra_specs["properties"][name]["description"]

    token = capabilities["driver_options"]["DriverCetcBase"]["properties"][
        "token"
    ]
    assert token["writeOnly"] is True
    assert "default" not in token
    compiler = capabilities["driver_options"]["DriverDummy"]["properties"][
        "compiler"
    ]
    assert "default" not in compiler


def test_extra_specs_validation_whitelist_is_unchanged(capabilities):
    supported_values = {
        name: None for name in capabilities["extra_specs"]["properties"]
    }
    assert RequestSpec.validate_extra_specs(supported_values) == (True, None)

    valid, message = RequestSpec.validate_extra_specs({"unknown": 1})
    assert valid is False
    assert "Unsupported extra_specs field: 'unknown'" in message


def test_qem_export_does_not_instantiate_strategies():
    with patch.object(MitigationFactory, "create") as create:
        build_capabilities_schemas({}, {})
    create.assert_not_called()
