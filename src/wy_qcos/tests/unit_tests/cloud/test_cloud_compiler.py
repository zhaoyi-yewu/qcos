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

import base64
import logging

import pytest
from fastapi.testclient import TestClient

from wy_qcos.cloud.app import app
from wy_qcos.cloud.schemas import (
    COMPILER_CMSS,
    COMPILER_QUARKCIRCUIT,
    INS_LABEL_ALL,
    CompileData,
    CompileRequest,
    CompileResponse,
)
from wy_qcos.cloud.service import (
    CODE_FAIL,
    CODE_SUCCESS,
    MSG_COMPILE_FAILED,
    MSG_INVALID_PARAM,
    MSG_SUCCESS,
    MSG_TOPOLOGY_INVALID,
    MSG_VERIFY_FAILED,
    CompileError,
    _build_verify_params,
    _validate_target_bits,
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


def _topology():
    return VALID_TOPOLOGY


# Topology whose largest connected component is {0,1,2} (3 qubits);
# {10,11} is a second component and every other qubit is isolated.
# Used to exercise topology mapping/routing failures.
TOPO_COMP3 = {
    "bits": 65,
    "basisGates": ["h", "rx", "ry", "rz", "cz"],
    "singleParam": [
        {"qubit": "Q0", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q1", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q2", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q10", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q11", "singleQubitGateFidelity": 0.999},
    ],
    "doubleParam": [
        {"linkQubit": "Q0-Q1", "cz": 0.985},
        {"linkQubit": "Q1-Q2", "cz": 0.98},
        {"linkQubit": "Q10-Q11", "cz": 0.957},
    ],
}


def _topo_comp3():
    return TOPO_COMP3


# Real-world QuarkCircuit (北量院 Quafu) topology sample: a 63-qubit chip
# with a single connected component {2,3,4,5,9,10,11,12} (8 qubits) formed
# by the doubleParam coupling edges. Used together with
# QUARKCIRCUIT_MIXED_QASM to exercise a realistic verify-pass scenario.
QUARKCIRCUIT_TOPOLOGY = {
    "bits": 63,
    "basisGates": ["h", "rx", "ry", "rz", "cz"],
    "singleParam": [
        {"qubit": "Q1", "singleQubitGateFidelity": 0.996},
        {"qubit": "Q2", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q3", "singleQubitGateFidelity": 0.998},
        {"qubit": "Q4", "singleQubitGateFidelity": 0.997},
        {"qubit": "Q5", "singleQubitGateFidelity": 0.998},
        {"qubit": "Q9", "singleQubitGateFidelity": 0.997},
        {"qubit": "Q10", "singleQubitGateFidelity": 0.997},
        {"qubit": "Q11", "singleQubitGateFidelity": 0.998},
        {"qubit": "Q12", "singleQubitGateFidelity": 0.998},
    ],
    "doubleParam": [
        {"linkQubit": "Q2-Q9", "cz": 0.974},
        {"linkQubit": "Q3-Q10", "cz": 0.988},
        {"linkQubit": "Q3-Q9", "cz": 0.979},
        {"linkQubit": "Q4-Q10", "cz": 0.984},
        {"linkQubit": "Q4-Q11", "cz": 0.982},
        {"linkQubit": "Q5-Q11", "cz": 0.979},
        {"linkQubit": "Q5-Q12", "cz": 0.985},
    ],
}

# A mixed-gate circuit (1q / 2q / 3q gates: id, rx, rxx, ry, rzz, swap, cx,
# cz, cy, ccx, cswap, ...) touching 8 qubits {1,2,3,4,5,10,11,12}, all of
# which fit inside QUARKCIRCUIT_TOPOLOGY's single 8-qubit component, so the
# QuafuVerifier accepts it.
QUARKCIRCUIT_MIXED_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[13];\ncreg c[13];\n'
    "id q[1];\nrx(1.570796) q[2];\nrxx(1.570796) q[4],q[10];\nx q[1];\n"
    "ry(1.570796) q[2];\nrzz(1.570796) q[11],q[4];\ny q[1];\n"
    "rz(1.570796) q[2];\nswap q[5],q[11];\nz q[1];\np(1.570796) q[2];\n"
    "cx q[11],q[4];\nh q[1];\nu3(1.570796,1.570796,1.570796) q[2];\n"
    "cz q[10],q[4];\ns q[1];\ncy q[4],q[10];\nsdg q[1];\ncy q[10],q[4];\n"
    "t q[1];\nccx q[5],q[12],q[11];\ntdg q[1];\ncswap q[5],q[11],q[12];\n"
    "sx q[1];\nsxdg q[1];\nmeasure q[1] -> c[1];\nmeasure q[2] -> c[2];\n"
    "measure q[3] -> c[3];\nmeasure q[4] -> c[4];\nmeasure q[5] -> c[5];\n"
    "measure q[10] -> c[10];\nmeasure q[11] -> c[11];"
)


def _quarkcircuit_topology():
    return QUARKCIRCUIT_TOPOLOGY


# Topology whose physical qubit ids (Q65, Q66) exceed the declared bit
# count (65). Chip vendors can publish ids past bits_num, so such ids
# must be accepted rather than rejected. Used with ID_ABOVE_BITS_QASM to
# exercise a verify-pass scenario where singleParam/doubleParam reference
# qubits past bits_num.
ID_ABOVE_BITS_TOPOLOGY = {
    "bits": 65,
    "basisGates": ["h", "cz"],
    "singleParam": [{"qubit": "Q66", "singleQubitGateFidelity": 0.999}],
    "doubleParam": [{"linkQubit": "Q65-Q66", "cz": 0.985}],
}

# Minimal circuit touching a single qubit (q[1], a 1q gate); parsed
# num_qubits = 1 <= bits_num(65), so QuafuVerifier accepts it even though
# the topology's qubit ids run past bits_num.
ID_ABOVE_BITS_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[1];\n'
)


def _id_above_bits_topology():
    return ID_ABOVE_BITS_TOPOLOGY


# 4-qubit fully-connected topology (single component {0,1,2,3}) so that a
# 4-qubit circuit with arbitrary 2q/3q pairing maps onto it. Used with
# ALL_GATE_QASM to exercise every gate family the QuafuVerifier accepts.
FULL_CONNECT4_TOPOLOGY = {
    "bits": 8,
    "basisGates": ["h", "rx", "ry", "rz", "cz"],
    "singleParam": [
        {"qubit": "Q0", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q1", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q2", "singleQubitGateFidelity": 0.999},
        {"qubit": "Q3", "singleQubitGateFidelity": 0.999},
    ],
    "doubleParam": [
        {"linkQubit": "Q0-Q1", "cz": 0.985},
        {"linkQubit": "Q0-Q2", "cz": 0.985},
        {"linkQubit": "Q0-Q3", "cz": 0.985},
        {"linkQubit": "Q1-Q2", "cz": 0.985},
        {"linkQubit": "Q1-Q3", "cz": 0.985},
        {"linkQubit": "Q2-Q3", "cz": 0.985},
    ],
}

# Circuit exercising every gate family the verifier parses: 1q (id, x, y,
# z, h, s, sdg, t, tdg, sx, sxdg, rx, ry, rz, p, u3), 2q (rxx, ryy, rzz,
# cphase, swap, iswap, cx, cz, cy), 3q (ccx, ccz, cswap), plus barrier and
# measure. Touches 4 qubits {0,1,2,3} that fit inside FULL_CONNECT4_TOPOLOGY.
ALL_GATE_QASM = (
    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[4];\ncreg c[4];\n'
    "id q[0];\nx q[1];\ny q[2];\nz q[3];\nh q[0];\ns q[1];\nsdg q[2];\n"
    "t q[3];\ntdg q[0];\nsx q[1];\nsxdg q[2];\nrx(1.570796) q[3];\n"
    "ry(1.570796) q[0];\nrz(1.570796) q[1];\np(1.570796) q[2];\n"
    "u3(1.570796,1.570796,1.570796) q[3];\nrxx(1.570796) q[1],q[0];\n"
    "ryy(1.570796) q[2],q[3];\nrzz(1.570796) q[1],q[0];\n"
    "cphase(1.570796) q[2],q[3];\nswap q[1],q[0];\niswap q[2],q[3];\n"
    "cx q[1],q[0];\ncz q[2],q[3];\nccx q[2],q[1],q[3];\ncy q[1],q[0];\n"
    "ccz q[1],q[2],q[0];\ncswap q[2],q[1],q[0];\nbarrier q[0];\n"
    "measure q[0] -> c[0];"
)


def _full_connect4_topology():
    return FULL_CONNECT4_TOPOLOGY


def _decode_msg(msg: str) -> str:
    """Decode the base64-encoded verifier failure message carried in ``msg``.

    The service layer translates the C++ verifier's English failure reason to
    Chinese and base64-encodes it before placing it in the response ``msg``
    field. Tests assert against the decoded Chinese text.
    """
    return base64.b64decode(msg).decode("utf-8")


def _valid_request(**overrides):
    base = {
        "insLabel": 3,
        "compiler": COMPILER_CMSS,
        "qasmType": 2,
        "qasm": VALID_QASM,
        "topology": _topology(),
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
        # single_param: list of (qubit_id, fidelity); qubit id derived
        # from "Q{n}", fidelity passed through unchanged
        assert d["single_param"] == [(0, 0.999), (1, 0.999)]
        # double_param: list of ((a, b), fidelity); edge derived from
        # "Q{a}-Q{b}", cz fidelity passed through unchanged
        assert d["double_param"] == [((0, 1), 0.985), ((10, 11), 0.957)]

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
            topology=_topology(),
        )
        d = request_to_dict(req)
        assert d["target_bits"] == [1, 2, 3, 6, 8]

    def test_fidelities_and_tuple_key_derivation(self):
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
        d = request_to_dict(_valid_request(topology=topology))
        # qubit id derived from "Q{n}"; fidelity passed through unchanged
        # (no rounding / error-rate conversion)
        assert d["single_param"] == [(5, 1.0), (12, 0.9999)]
        # (a, b) edge derived from "Q{a}-Q{b}"; cz fidelity passed through
        assert d["double_param"] == [((5, 6), 0.985), ((10, 23), 0.999)]

    def test_invalid_topology_json_raises(self):
        # topology must be a JSON object, not an arbitrary string;
        # pydantic rejects it at CompileRequest construction time.
        with pytest.raises(Exception):
            _valid_request(topology="not a json")

    def test_invalid_topology_structure_raises(self):
        # topology missing singleParam/doubleParam is rejected by pydantic
        # at CompileRequest construction time.
        with pytest.raises(Exception):
            _valid_request(topology={"bits": 8, "basisGates": ["h"]})

    def test_missing_topology_bits_raises(self):
        # topology missing the required bits field is rejected by pydantic
        # at CompileRequest construction time.
        bad = {
            "basisGates": ["h"],
            "singleParam": [],
            "doubleParam": [],
        }
        with pytest.raises(Exception):
            _valid_request(topology=bad)

    def test_invalid_qubit_name_raises(self):
        # singleParam qubit name must match the Q{n} pattern; the topology
        # object itself is valid (passes pydantic), so the error is raised
        # by the service layer (_parse_qubit_name).
        bad = {
            "bits": 8,
            "basisGates": ["h"],
            "singleParam": [
                {"qubit": "bit0", "singleQubitGateFidelity": 0.999}
            ],
            "doubleParam": [],
        }
        with pytest.raises(CompileError) as exc:
            request_to_dict(_valid_request(topology=bad))
        assert exc.value.msg == MSG_TOPOLOGY_INVALID

    def test_invalid_linkqubit_raises(self):
        # doubleParam linkQubit must match the Q{a}-Q{b} pattern; the
        # topology object itself is valid, so the error is raised by the
        # service layer (_parse_link_qubit).
        bad = {
            "bits": 8,
            "basisGates": ["h"],
            "singleParam": [],
            "doubleParam": [{"linkQubit": "Q0~Q1", "cz": 0.9}],
        }
        with pytest.raises(CompileError) as exc:
            request_to_dict(_valid_request(topology=bad))
        assert exc.value.msg == MSG_TOPOLOGY_INVALID


# ---------------------------------------------------------------------------
# Service layer: _build_verify_params
# ---------------------------------------------------------------------------


class TestBuildVerifyParams:
    def test_basic_fields_mapped(self):
        d = request_to_dict(_valid_request())
        vp = _build_verify_params(d)
        assert vp.bits == 65
        assert vp.basis_gates == ["h", "rx", "ry", "rz", "cz"]

    def test_single_qubit_fidelities_by_index(self):
        d = request_to_dict(_valid_request())
        vp = _build_verify_params(d)
        # single_param [(0, 0.999), (1, 0.999)] -> fidelity kept directly
        assert vp.single_qubit_fidelities[0] == 0.999
        assert vp.single_qubit_fidelities[1] == 0.999
        # the list is sized by the largest qubit id (max+1 = 2), not by
        # bits_num (65): chip vendors may publish ids past the declared
        # bit count, so bits_num is not a safe upper bound for indexing.
        assert len(vp.single_qubit_fidelities) == 2

    def test_single_qubit_fidelity_id_above_bits_num(self):
        # a physical qubit id may exceed bits_num (e.g. Q66 on a 65-qubit
        # chip); it must still be accepted and indexed, and the list is
        # sized to hold it (max id + 1).
        d = request_to_dict(_valid_request())
        d["single_param"] = [(66, 0.999)]  # 66 >= bits_num(65)
        vp = _build_verify_params(d)
        assert vp.single_qubit_fidelities[66] == 0.999
        assert len(vp.single_qubit_fidelities) == 67

    def test_coupling_list_bidirectional(self):
        d = request_to_dict(_valid_request())
        vp = _build_verify_params(d)
        # double_param [((0, 1), 0.985), ((10, 11), 0.957)]
        # -> both directions per edge, fidelity kept directly
        assert (0, 1) in vp.coupling_list
        assert (1, 0) in vp.coupling_list
        assert (10, 11) in vp.coupling_list
        assert (11, 10) in vp.coupling_list
        # fidelity for edge 0-1: cz fidelity 0.985
        idx = vp.coupling_list.index((0, 1))
        assert vp.edge_fidelities[idx] == 0.985

    def test_target_bits_default_empty(self):
        d = request_to_dict(_valid_request())
        vp = _build_verify_params(d)
        assert vp.target_bits == []

    def test_target_bits_from_extend(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_QUARKCIRCUIT,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology(),
        )
        vp = _build_verify_params(request_to_dict(req))
        assert vp.target_bits == [1, 2, 3, 6, 8]

    def test_qubit_id_out_of_range_raises(self):
        # single_param is a list of (qubit_id, fidelity); only a negative
        # qubit id is rejected. An id at or above bits_num is allowed
        # (see test_single_qubit_fidelity_id_above_bits_num).
        d = request_to_dict(_valid_request())
        d["single_param"] = [(-1, 0.999)]
        with pytest.raises(CompileError):
            _build_verify_params(d)


# ---------------------------------------------------------------------------
# Service layer: _validate_target_bits (OR semantics)
# ---------------------------------------------------------------------------
# A target bit is valid when bit <= bits_num OR bit is among the qubit ids
# declared in singleParam / doubleParam. Only bit > bits_num AND not declared
# is rejected (negative bits are always rejected).


class TestValidateTargetBits:
    @staticmethod
    def _params(bits, single, double, target_bits):
        return {
            "bits_num": bits,
            "single_param": [(q, 0.999) for q in single],
            "double_param": [((a, b), 0.985) for a, b in double],
            "target_bits": target_bits,
        }

    def test_no_target_bits_passes(self):
        d = self._params(
            bits=65, single=[0, 1], double=[(0, 1)], target_bits=[]
        )
        assert _validate_target_bits(d) is None

    def test_within_bits_num_passes_even_if_undeclared(self):
        # 5 <= bits_num(65) but 5 is not declared -> OR semantics accepts.
        d = self._params(
            bits=65, single=[0, 1, 2], double=[(0, 1)], target_bits=[5]
        )
        assert _validate_target_bits(d) is None

    def test_declared_in_singleparam_passes(self):
        d = self._params(
            bits=65, single=[0, 1, 2, 11], double=[(0, 1)], target_bits=[11]
        )
        assert _validate_target_bits(d) is None

    def test_declared_in_doubleparam_passes(self):
        # 3 is not in singleParam but is an endpoint of a doubleParam edge.
        d = self._params(
            bits=65, single=[0, 1], double=[(3, 4)], target_bits=[3]
        )
        assert _validate_target_bits(d) is None

    def test_above_bits_num_but_declared_passes(self):
        # 66 > bits_num(65) but 66 is declared -> OR semantics accepts. This
        # case is accepted by the service layer even though the C++ verifier
        # would later reject it on [0, bits_num); this unit test isolates the
        # service-layer rule.
        d = self._params(
            bits=65, single=[66], double=[(65, 66)], target_bits=[66]
        )
        assert _validate_target_bits(d) is None

    def test_above_bits_num_and_undeclared_rejected(self):
        d = self._params(
            bits=65, single=[0, 1], double=[(0, 1)], target_bits=[99]
        )
        msg = _validate_target_bits(d)
        assert msg is not None
        assert "超出真机比特数" in msg
        assert "且不在声明的量子比特中" in msg
        assert "99" in msg and "65" in msg

    def test_negative_rejected(self):
        d = self._params(
            bits=65, single=[0, 1], double=[(0, 1)], target_bits=[-1]
        )
        msg = _validate_target_bits(d)
        assert msg is not None
        assert "不能为负数" in msg

    def test_first_invalid_bit_wins(self):
        # 5 is fine (<= 65), 99 is invalid -> the invalid one is reported.
        d = self._params(
            bits=65, single=[0, 1], double=[(0, 1)], target_bits=[5, 99]
        )
        msg = _validate_target_bits(d)
        assert msg is not None
        assert "99" in msg


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

    def test_quarkcircuit_real_topology_mixed_gates_passes(self):
        # Real-world QuarkCircuit sample: a 63-qubit chip whose coupling
        # edges form a single 8-qubit component {2,3,4,5,9,10,11,12}, and
        # a mixed-gate circuit (1q/2q/3q gates) touching 8 qubits that all
        # fit inside that component -> QuafuVerifier accepts it.
        resp = compile_qasm(
            _valid_request(
                compiler="quarkcircuit",
                qasm=QUARKCIRCUIT_MIXED_QASM,
                topology=_quarkcircuit_topology(),
                extend={"targetBits": []},
            )
        )
        assert resp.code == CODE_SUCCESS
        assert resp.msg == MSG_SUCCESS
        assert resp.data is not None
        assert resp.data.compiled is None

    def test_quarkcircuit_qubit_id_above_bits_num_passes(self):
        # Chip vendors may publish physical qubit ids past the declared
        # bit count (here Q65/Q66 on a 65-qubit chip). Such ids must be
        # accepted; a minimal 1-qubit circuit then passes verification.
        resp = compile_qasm(
            _valid_request(
                compiler="quarkcircuit",
                qasm=ID_ABOVE_BITS_QASM,
                topology=_id_above_bits_topology(),
            )
        )
        assert resp.code == CODE_SUCCESS
        assert resp.msg == MSG_SUCCESS
        assert resp.data is not None
        assert resp.data.compiled is None

    def test_quarkcircuit_all_gate_families_passes(self):
        # Exercises every gate family the QuafuVerifier parses (1q / 2q /
        # 3q, including ccz, cswap, iswap, rxx/ryy/rzz, cphase) plus barrier
        # and measure, on a 4-qubit fully-connected topology -> passes.
        resp = compile_qasm(
            _valid_request(
                compiler="quarkcircuit",
                qasm=ALL_GATE_QASM,
                topology=_full_connect4_topology(),
                extend={"targetBits": []},
            )
        )
        assert resp.code == CODE_SUCCESS
        assert resp.msg == MSG_SUCCESS
        assert resp.data is not None
        assert resp.data.compiled is None

    def test_quarkcircuit_verify_failed(self):
        # measure to an undeclared classical register fails QuafuVerifier
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nmeasure q[0] -> c[0];\n"
        )
        resp = compile_qasm(_valid_request(compiler="quarkcircuit", qasm=qasm))
        assert resp.code == CODE_FAIL
        # the verifier's failure reason is propagated in msg
        # (QASM parse error), translated to Chinese and base64-encoded
        assert "解析" in _decode_msg(resp.msg)

    # --- QASM syntax illegal: verify only runs for quarkcircuit ---

    @pytest.mark.parametrize(
        "qasm",
        [
            # QASM3.0 header is unsupported
            "OPENQASM 3.0;\nqubit[2] q;\nh q[0];\n",
            # missing OPENQASM header
            "qreg q[2];\nh q[0];\n",
            # unknown gate name
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nfoobar q[0];\n',
            # plain garbage
            "this is not qasm at all {{{",
        ],
    )
    def test_qasm_syntax_illegal_fails_verify(self, qasm):
        resp = compile_qasm(_valid_request(compiler="quarkcircuit", qasm=qasm))
        assert resp.code == CODE_FAIL
        # the verifier's failure reason (a QASM syntax / parse error) is
        # propagated in msg instead of a fixed placeholder, translated to
        # Chinese and base64-encoded
        decoded = _decode_msg(resp.msg)
        assert decoded != MSG_VERIFY_FAILED
        assert decoded != MSG_SUCCESS
        assert "语法" in decoded or "解析" in decoded

    def test_qasm3_with_cmss_still_succeeds(self):
        # cmss branch never calls QuafuVerifier, so a QASM3.0 source that
        # would fail syntax validation still returns success.
        resp = compile_qasm(
            _valid_request(
                compiler="cmss",
                qasmType=3,
                qasm="OPENQASM 3.0;\nqubit[2] q;\nh q[0];\n",
            )
        )
        assert resp.code == CODE_SUCCESS

    def test_unsupported_compiler(self):
        resp = compile_qasm(_valid_request(compiler="ibm"))
        assert resp.code == CODE_FAIL
        assert resp.msg == MSG_INVALID_PARAM

    # topology JSON / structure validation is exercised in
    # TestRequestToDict (construction raises) and TestCompileEndpoint
    # (HTTP layer returns MSG_INVALID_PARAM); see test_invalid_qubit_name
    # / test_invalid_linkqubit here for the service-layer format checks.

    # --- topology mapping/routing failures: QuafuVerifier rejects the
    # circuit because it cannot be placed onto the machine topology ---

    def test_two_qubit_gate_exceeds_largest_component(self):
        # circuit needs 4 qubits wired together; the largest connected
        # component of TOPO_COMP3 is {0,1,2} (3 qubits) -> verify fails
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[4];\ncz q[0],q[1];\ncz q[2],q[3];\n"
        )
        resp = compile_qasm(
            _valid_request(
                compiler="quarkcircuit",
                qasm=qasm,
                topology=_topo_comp3(),
            )
        )
        assert resp.code == CODE_FAIL
        assert "连通分量" in _decode_msg(resp.msg)

    def test_two_qubit_gate_on_isolated_qubit(self):
        # cz q[0],q[1] is fine, but extend.targetBits includes q[3] which
        # has no coupling edge -> verify fails (target_bit not in coupling
        # graph). The check only fires when the circuit has a multi-qubit
        # gate, so the cz is required.
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[4];\ncz q[0],q[1];\n'
        )
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [0, 3]},
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_FAIL
        assert "电路拓扑无法映射到自定义比特" in _decode_msg(resp.msg)

    def test_qreg_exceeds_bits_num(self):
        # the verifier counts qubits actually used (not the qreg declaration),
        # so a circuit that touches 66 qubits exceeds topology.bits=65.
        gates = "".join(f"h q[{i}];\n" for i in range(66))
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[66];\n' + gates
        resp = compile_qasm(
            _valid_request(
                compiler="quarkcircuit",
                qasm=qasm,
                topology=_topo_comp3(),
            )
        )
        assert resp.code == CODE_FAIL
        assert "量子比特" in _decode_msg(resp.msg)

    def test_target_bits_span_two_components(self):
        # extend.targetBits [0,10] lie in different connected components
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncz q[0],q[1];\n'
        )
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [0, 10]},
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_FAIL
        assert "电路拓扑无法映射到自定义比特" in _decode_msg(resp.msg)

    def test_target_bits_out_of_range(self):
        # extend.targetBits [0,99]: 99 > bits_num(65) AND 99 is not among
        # the qubit ids declared in TOPO_COMP3 ({0,1,2,10,11}) -> service-
        # layer target_bits validation fails.
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n'
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [0, 99]},
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_FAIL
        assert "超出真机比特数" in _decode_msg(resp.msg)
        assert "且不在声明的量子比特中" in _decode_msg(resp.msg)

    def test_target_bits_negative_rejected(self):
        # extend.targetBits with a negative bit -> service-layer validation
        # fails (target bit must be non-negative).
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n'
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [-1]},
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_FAIL
        assert "不能为负数" in _decode_msg(resp.msg)

    def test_target_bits_within_bits_num_passes(self):
        # extend.targetBits = [5]: 5 <= bits_num(65) so it is accepted even
        # though 5 is not among TOPO_COMP3's declared qubit ids (OR semantics:
        # <= bits_num is sufficient). The circuit uses a 1q gate so the
        # verifier passes too.
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n'
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [5]},
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_SUCCESS

    def test_target_bits_at_max_qubit_id_passes(self):
        # extend.targetBits = [11] is a declared qubit id in TOPO_COMP3 and
        # also <= bits_num(65); the circuit uses a 1q gate so it passes.
        qasm = 'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nh q[0];\n'
        req = CompileRequest(
            insLabel=3,
            compiler="quarkcircuit",
            qasmType=2,
            qasm=qasm,
            extend={"targetBits": [11]},  # declared qubit id in TOPO_COMP3
            topology=_topo_comp3(),
        )
        resp = compile_qasm(req)
        assert resp.code == CODE_SUCCESS

    def test_extend_target_bits_optional(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology(),
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
# Service layer: logging
# ---------------------------------------------------------------------------


class TestLogging:
    def _logged_messages(self, caplog):
        return [r.getMessage() for r in caplog.records]

    def test_request_params_logged_without_qasm(self, caplog):
        caplog.set_level(logging.INFO, logger="wy_qcos.cloud.service")
        compile_qasm(_valid_request())
        msgs = " ".join(self._logged_messages(caplog))
        # input parameters are logged in English
        assert "compile request received" in msgs
        assert "compiler=cmss" in msgs
        assert "qasm_type=2" in msgs
        assert "ins_label=3" in msgs
        # qasm source is never printed; only its length
        assert "qasm_len=" in msgs
        assert "OPENQASM" not in msgs
        assert "qelib1" not in msgs

    def test_success_log_contains_compiler(self, caplog):
        caplog.set_level(logging.INFO, logger="wy_qcos.cloud.service")
        compile_qasm(_valid_request())
        msgs = " ".join(self._logged_messages(caplog))
        assert "compile succeeded" in msgs
        assert "compiler=cmss" in msgs

    def test_failure_log_contains_compiler_and_reason(self, caplog):
        caplog.set_level(logging.WARNING, logger="wy_qcos.cloud.service")
        # verify failure: measure to an undeclared classical register
        qasm = (
            'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
            "qreg q[2];\nmeasure q[0] -> c[0];\n"
        )
        compile_qasm(_valid_request(compiler="quarkcircuit", qasm=qasm))
        msgs = " ".join(self._logged_messages(caplog))
        assert "compile failed" in msgs
        assert "compiler=quarkcircuit" in msgs
        # the failure reason is described in the log
        assert "verification failed" in msgs
        # the verifier's failure message is propagated into the log
        assert "parse" in msgs.lower()

    def test_unsupported_compiler_log_and_msg(self, caplog):
        caplog.set_level(logging.WARNING, logger="wy_qcos.cloud.service")
        resp = compile_qasm(_valid_request(compiler="ibm"))
        msgs = " ".join(self._logged_messages(caplog))
        assert resp.code == CODE_FAIL
        assert resp.msg == MSG_INVALID_PARAM
        assert "compiler=ibm" in msgs
        assert "unsupported compiler" in msgs


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
            "topology": _topology(),
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

    def test_post_quarkcircuit_real_topology_mixed_gates(self, client):
        # Real-world QuarkCircuit sample: 8 qubits of mixed-gate circuit
        # fit inside the chip's single 8-qubit connected component ->
        # verify passes and the response carries the verifier outcome.
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=QUARKCIRCUIT_MIXED_QASM,
                topology=_quarkcircuit_topology(),
                extend={"targetBits": []},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1
        assert data["msg"] == MSG_SUCCESS
        assert data["data"]["compiled"] is None

    def test_post_quarkcircuit_qubit_id_above_bits_num(self, client):
        # Physical qubit ids past bits_num (Q65/Q66 on a 65-qubit chip)
        # are accepted; a minimal 1-qubit circuit passes verification.
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=ID_ABOVE_BITS_QASM,
                topology=_id_above_bits_topology(),
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1
        assert data["msg"] == MSG_SUCCESS
        assert data["data"]["compiled"] is None

    def test_post_quarkcircuit_all_gate_families(self, client):
        # Every gate family (incl. ccz/cswap/iswap/rxx/ryy/rzz/cphase) on
        # a 4-qubit fully-connected topology -> verify passes.
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=ALL_GATE_QASM,
                topology=_full_connect4_topology(),
                extend={"targetBits": []},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 1
        assert data["msg"] == MSG_SUCCESS
        assert data["data"]["compiled"] is None

    def test_post_quarkcircuit_verify_failed(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm='OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                "qreg q[2];\nmeasure q[0] -> c[0];\n",
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "解析" in _decode_msg(data["msg"])

    @pytest.mark.parametrize(
        "qasm",
        [
            "OPENQASM 3.0;\nqubit[2] q;\nh q[0];\n",  # QASM3.0 unsupported
            "qreg q[2];\nh q[0];\n",  # missing OPENQASM header
            'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\nfoobar q[0];\n',
            "this is not qasm at all {{{",  # garbage
        ],
    )
    def test_post_qasm_syntax_illegal(self, client, qasm):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(compiler="quarkcircuit", qasm=qasm),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        decoded = _decode_msg(data["msg"])
        assert decoded != MSG_VERIFY_FAILED
        assert "语法" in decoded or "解析" in decoded

    def test_post_two_qubit_gate_exceeds_component(self, client):
        # largest connected component of TOPO_COMP3 is {0,1,2} (3 qubits);
        # this circuit needs 4 qubits wired together -> verify fails
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                    "qreg q[4];\ncz q[0],q[1];\ncz q[2],q[3];\n"
                ),
                topology=_topo_comp3(),
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "连通分量" in _decode_msg(data["msg"])

    def test_post_two_qubit_gate_on_isolated_qubit(self, client):
        # cz q[0],q[1] is fine, but extend.targetBits includes q[3] which
        # has no coupling edge -> verify fails (the cz is required so the
        # coupling-graph check fires).
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                    "qreg q[4];\ncz q[0],q[1];\n"
                ),
                topology=_topo_comp3(),
                extend={"targetBits": [0, 3]},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "电路拓扑无法映射到自定义比特" in _decode_msg(data["msg"])

    def test_post_qreg_exceeds_bits_num(self, client):
        # the verifier counts qubits actually used (not the qreg
        # declaration), so a circuit touching 66 qubits exceeds bits=65.
        gates = "".join(f"h q[{i}];\n" for i in range(66))
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[66];\n'
                    + gates
                ),
                topology=_topo_comp3(),
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "量子比特" in _decode_msg(data["msg"])

    def test_post_target_bits_span_two_components(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                    "qreg q[2];\ncz q[0],q[1];\n"
                ),
                topology=_topo_comp3(),
                extend={"targetBits": [0, 10]},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "电路拓扑无法映射到自定义比特" in _decode_msg(data["msg"])

    def test_post_target_bits_out_of_range(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                    "qreg q[2];\nh q[0];\n"
                ),
                topology=_topo_comp3(),
                extend={"targetBits": [0, 99]},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "超出真机比特数" in _decode_msg(data["msg"])
        assert "且不在声明的量子比特中" in _decode_msg(data["msg"])

    def test_post_target_bits_negative_rejected(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(
                compiler="quarkcircuit",
                qasm=(
                    'OPENQASM 2.0;\ninclude "qelib1.inc";\n'
                    "qreg q[2];\nh q[0];\n"
                ),
                topology=_topo_comp3(),
                extend={"targetBits": [-1]},
            ),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert "不能为负数" in _decode_msg(data["msg"])

    def test_post_topology_missing_required_field(self, client):
        # topology present but missing singleParam/doubleParam -> pydantic
        # validation fails at the request boundary -> MSG_INVALID_PARAM
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(topology={"bits": 8, "basisGates": ["h"]}),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["msg"] == MSG_INVALID_PARAM

    def test_post_topology_bad_linkqubit(self, client):
        # topology object is valid (passes pydantic), but linkQubit "Q0~Q1"
        # does not match the Q{a}-Q{b} pattern -> service layer raises
        # CompileError -> MSG_TOPOLOGY_INVALID
        bad = {
            "bits": 8,
            "basisGates": ["h"],
            "singleParam": [],
            "doubleParam": [{"linkQubit": "Q0~Q1", "cz": 0.9}],
        }
        r = client.post(
            "/compiler/qasm/compile", json=self._body(topology=bad)
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["msg"] == MSG_TOPOLOGY_INVALID

    def test_post_wrong_type_inslabel(self, client):
        # insLabel must be int; "abc" fails pydantic validation -> code=0
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(insLabel="abc"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0

    def test_post_unsupported_compiler(self, client):
        r = client.post(
            "/compiler/qasm/compile",
            json=self._body(compiler="ibm"),
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["msg"] == MSG_INVALID_PARAM

    def test_post_invalid_topology(self, client):
        # topology must be a JSON object; a bare string fails pydantic
        # validation at the request boundary -> MSG_INVALID_PARAM
        r = client.post(
            "/compiler/qasm/compile", json=self._body(topology="not a json")
        )
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == 0
        assert data["msg"] == MSG_INVALID_PARAM

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
            topology=_topology(),
        )
        assert req.extend is None

    def test_extend_target_bits(self):
        req = CompileRequest(
            insLabel=3,
            compiler=COMPILER_CMSS,
            qasmType=2,
            qasm=VALID_QASM,
            extend={"targetBits": [1, 2, 3, 6, 8]},
            topology=_topology(),
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
