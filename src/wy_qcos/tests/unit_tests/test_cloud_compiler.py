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
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for the cloud compiler service (cloud.md).

Covers all boundary cases in cloud.md section 4 and the request/response
contract in section 3.
"""

import json

import pytest
from fastapi.testclient import TestClient

from wy_qcos.cloud.app import app
from wy_qcos.cloud.schemas import (
    COMPILER_CMSS,
    INS_LABEL_ALL,
    CompileData,
    CompileRequest,
    CompileResponse,
)
from wy_qcos.cloud.service import (
    CODE_FAIL,
    CODE_SUCCESS,
    MSG_COMPILE_FAILED,
    MSG_SUCCESS,
    MSG_TOPOLOGY_INVALID,
    CompileError,
    compile_qasm,
    request_to_dict,
)

VALID_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
    "qreg q[8];\ncreg c[8];\n"
    "h q[1];\nmeasure q[1] -> c[1];\nmeasure q[2] -> c[2];"
)
VALID_TOPOLOGY = {
    "bits": 65,
    "basisGates": ["h", "rx", "ry", "rz", "cz"],
    "singleParam": [
        {"qubit": "Q0", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q1", "singleQubitGateFidelity": 0.999},
    ],
    "doubleParam": [
        {"linkQubit": "Q0-Q1", "cz": 0.985},
        {"linkQubit": "Q10-Q11", "cz": 0.957},
    ],
}


def _topology_str():
    return json.dumps(VALID_TOPOLOGY)


def _valid_request(**overrides):
    base = {
        "insLabel": 3,
        "compiler": COMPILER_CMSS,
        "qasmType": 2,
        "qasm": VALID_QASM,
        "topology": _topology_str(),
    }
    base.update(overrides)
    return CompileRequest(**base)


# ---------------------------------------------------------------------------
# Service layer: request_to_dict (request flattening)
# ---------------------------------------------------------------------------


class TestRequestToDict:
    def test_flattens_basic_fields(self):
        d = request_to_dict(_valid_request())
        assert d["ins_label"] == 3
        assert d["compiler"] == COMPILER_CMSS
        assert d["qasm_type"] == 2
        assert d["qasm"] == VALID_QASM

    def test_lifts_topology_inner_fields(self):
        d = request_to_dict(_valid_request())
        assert d["bits_num"] == 65
        assert d["basis_gates"] == ["h", "rx", "ry", "rz", "cz"]
        # single_param: dict keyed by qubit name, value = 1 - fidelity (3 dec)
        assert d["single_param"] == {"Q0": 0.001, "Q1": 0.001}
        # double_param: dict keyed by "CZ{a}_{b}", value = 1 - cz (3 dec)
        assert d["double_param"] == {"CZ0_1": 0.015, "CZ10_11": 0.043}

    def test_no_target_bits_key_when_extend_missing(self):
        d = request_to_dict(_valid_request())
        assert "target_bits" not in d

    def test_lifts_extend_target_bits(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology_str(),
        )
        d = request_to_dict(req)
        assert d["target_bits"] == [1, 2, 3, 6, 8]

    def test_error_rates_and_cz_key_derivation(self):
        topology = {
            "bits": 8,
            "basisGates": ["h", "cz"],
            "singleParam": [
                {"qubit": "Q5", "singleQubitGateFidelity": 1.0},
                {"qubit": "Q12", "singleQubitGateFidelity": 0.9999},
            ],
            "doubleParam": [
                {"linkQubit": "Q5-Q6", "cz": 0.985},
                {"linkQubit": "Q10-Q23", "cz": 0.999},
            ],
        }
        d = request_to_dict(_valid_request(topology=json.dumps(topology)))
        # 1 - 1.0 = 0.0; 1 - 0.9999 = 0.0001 -> 3 decimals -> 0.0
        assert d["single_param"] == {"Q5": 0.0, "Q12": 0.0}
        # CZ{a}_{b} derived from Q{a}-Q{b}; 1 - 0.985 = 0.015
        assert d["double_param"] == {"CZ5_6": 0.015, "CZ10_23": 0.001}

    def test_invalid_topology_json_raises(self):
        with pytest.raises(CompileError) as exc:
            request_to_dict(_valid_request(topology="not a json"))
        assert exc.value.msg == MSG_TOPOLOGY_INVALID

    def test_invalid_topology_structure_raises(self):
        bad = json.dumps({"bits": 8, "basisGates": ["h"]})
        with pytest.raises(CompileError) as exc:
            request_to_dict(_valid_request(topology=bad))
        assert exc.value.msg == MSG_TOPOLOGY_INVALID

    def test_missing_topology_bits_raises(self):
        bad = json.dumps({
            "basisGates": ["h"],
            "singleParam": [],
            "doubleParam": [],
        })
        with pytest.raises(CompileError):
            request_to_dict(_valid_request(topology=bad))


# ---------------------------------------------------------------------------
# Service layer: compile_qasm (end-to-end)
# ---------------------------------------------------------------------------


class TestCompileQasm:
    def test_cmss_compile_success(self):
        resp = compile_qasm(_valid_request())
        assert resp.code == CODE_SUCCESS
        assert resp.msg == MSG_SUCCESS
        assert resp.data is not None
        assert resp.data.compiled == ""

    def test_vendor_compiler_only_validates(self):
        resp = compile_qasm(_valid_request(compiler="quarkcircuit"))
        assert resp.code == CODE_SUCCESS
        assert resp.msg == MSG_SUCCESS
        # vendor compiler: no compiled output
        assert resp.data is not None
        assert resp.data.compiled is None

    def test_invalid_topology_json(self):
        resp = compile_qasm(_valid_request(topology="not a json"))
        assert resp.code == CODE_FAIL
        assert resp.msg == MSG_TOPOLOGY_INVALID

    def test_invalid_topology_structure(self):
        bad = json.dumps({"bits": 8, "basisGates": ["h"]})
        resp = compile_qasm(_valid_request(topology=bad))
        assert resp.code == CODE_FAIL
        assert resp.msg == MSG_TOPOLOGY_INVALID

    def test_extend_target_bits_optional(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology_str(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_SUCCESS
        assert resp.data.compiled == ""

    @pytest.mark.parametrize("ins_label", INS_LABEL_ALL)
    def test_all_tech_stacks(self, ins_label):
        resp = compile_qasm(_valid_request(insLabel=ins_label))
        assert resp.code == CODE_SUCCESS

    def test_unexpected_error_is_failure(self, monkeypatch):
        # force an unexpected error inside request_to_dict to verify the
        # global catch-all maps it to code=0
        def _boom(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr("wy_qcos.cloud.service.request_to_dict", _boom)
        resp = compile_qasm(_valid_request())
        assert resp.code == CODE_FAIL
        assert resp.msg == MSG_COMPILE_FAILED


# ---------------------------------------------------------------------------
# HTTP layer via TestClient
# ---------------------------------------------------------------------------


class TestCompileEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def _body(self, **overrides):
        body = {
            "insLabel": 3,
            "compiler": COMPILER_CMSS,
            "qasmType": 2,
            "qasm": VALID_QASM,
            "topology": _topology_str(),
        }
        body.update(overrides)
        return body

    def test_post_compile_success(self, client):
        r = client.post("/compiler/qasm/compile", json=self._body())
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1
        assert data["msg"] == MSG_SUCCESS
        assert data["data"]["compiled"] == ""

    def test_post_vendor_compiler(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(compiler="quarkcircuit"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1
        assert data["data"]["compiled"] is None

    def test_post_invalid_topology(self, client):
        r = client.post(
            "/compiler/qasm/compile", json=self._body(topology="not a json")
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["msg"] == MSG_TOPOLOGY_INVALID

    def test_post_extend_target_bits(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(extend={"targetBits": [1, 2, 3, 6, 8]}),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1

    def test_post_missing_required_field(self, client):
        # global exception capture: missing field -> code=0, not HTTP 422
        r = client.post("/compiler/qasm/compile", json={"insLabel": 3})
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0

    def test_post_qasm_too_long(self, client):
        # qasm max length 10240; exceed it -> validation failure -> code=0
        long_qasm = "OPENQASM 2.0;\n" + "x" * 11000
        r = client.post(
            "/compiler/qasm/compile", json=self._body(qasm=long_qasm)
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0

    def test_openapi_accessible(self, client):
        # cloud.md section 2: access the validation interface via openapi
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/compiler/qasm/compile" in paths

    def test_docs_accessible(self, client):
        r = client.get("/docs")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_compile_request_required_fields(self):
        with pytest.raises(Exception):
            CompileRequest()

    def test_extend_optional(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            topology=_topology_str(),
        )
        assert req.extend is None

    def test_extend_target_bits(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology_str(),
        )
        assert req.extend.targetBits == [1, 2, 3, 6, 8]

    def test_response_serialization(self):
        resp = CompileResponse(
            code=CODE_SUCCESS,
            msg=MSG_SUCCESS,
            data=CompileData(compiled="OPENQASM 2.0;"),
        )
        dumped = resp.model_dump()
        assert dumped["code"] == 1
        assert dumped["data"]["compiled"] == "OPENQASM 2.0;"

    def test_response_failure_no_data(self):
        resp = CompileResponse(code=CODE_FAIL, msg="err")
        dumped = resp.model_dump()
        assert dumped["code"] == 0
        assert dumped["data"] is None
