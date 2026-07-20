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

"""Pydantic schemas for the cloud compiler service.

These models mirror the request/response contract defined in cloud.md
section 3 (interface contract). Field names, types and max-length
constraints follow the spec table strictly.
"""

from pydantic import BaseModel, Field


# insLabel: technical stack
# 2 光量子 / 3 超导 / 4 离子阱 / 5 中性原子 / 6 金刚石色心
INS_LABEL_PHOTON = 2
INS_LABEL_SUPERCONDUCTING = 3
INS_LABEL_ION_TRAP = 4
INS_LABEL_NEUTRAL_ATOM = 5
INS_LABEL_DIAMOND = 6
INS_LABEL_ALL = [
    INS_LABEL_PHOTON,
    INS_LABEL_SUPERCONDUCTING,
    INS_LABEL_ION_TRAP,
    INS_LABEL_NEUTRAL_ATOM,
    INS_LABEL_DIAMOND,
]

# qasmType: 2 QASM2.0 / 3 QASM3.0
QASM_TYPE_QASM2 = 2
QASM_TYPE_QASM3 = 3
QASM_TYPE_ALL = [QASM_TYPE_QASM2, QASM_TYPE_QASM3]

# Self-developed compiler name. Only cmss performs both circuit
# validation and compilation; other vendor/institution compilers
# (e.g. quarkcircuit) only perform circuit validation.
COMPILER_CMSS = "cmss"
# Vendor compiler name (北量院 Quafu). It only performs circuit validation
# via QuafuVerifier.
COMPILER_QUARKCIRCUIT = "quarkcircuit"


class ExtendTargetBits(BaseModel):
    """Optional extend payload submitted with a task."""

    # custom qubit indices, e.g. [1, 2, 3, 6, 8]
    targetBits: list[int] | None = Field(
        None, description="custom qubit indices, e.g. [1, 2, 3, 6, 8]"
    )


class TopologySingleParam(BaseModel):
    """Single-qubit information entry in topology."""

    qubit: str = Field(..., description="qubit name, e.g. Q0")
    singleQubitGateFidelity: float = Field(
        ..., description="single qubit gate fidelity"
    )


class TopologyDoubleParam(BaseModel):
    """Two-qubit information entry in topology."""

    linkQubit: str = Field(..., description="linked qubit pair, e.g. Q0-Q1")
    cz: float = Field(..., description="cz gate fidelity")


class Topology(BaseModel):
    """Real-machine topology structure.

    topology is sent as a JSON object in the request, whose inner
    structure (bits / basisGates / singleParam / doubleParam) is defined
    by the fields below. Pydantic parses and validates it directly.
    """

    # number of available qubits on the real machine
    bits: int = Field(..., description="number of available qubits")
    # basis gates supported by the real machine
    basisGates: list[str] = Field(
        ..., description="basis gates supported by the real machine"
    )
    # single-qubit information
    singleParam: list[TopologySingleParam] = Field(
        ..., description="single-qubit information"
    )
    # two-qubit information
    doubleParam: list[TopologyDoubleParam] = Field(
        ..., description="two-qubit information"
    )


class CompileRequest(BaseModel):
    """Request body of POST /compiler/qasm/compile.

    Fields follow cloud.md section 3 request parameter table:
    insLabel / compiler / qasmType / qasm / extend / topology.
    """

    # technical stack: 2 光量子 3 超导 4 离子阱 5 中性原子 6 金刚石色心
    insLabel: int = Field(
        ...,
        le=99,
        description=(
            "technical stack: 2 光量子 3 超导 4 离子阱 5 中性原子 6 金刚石色心"
        ),
    )
    # compiler name, e.g. cmss (self-developed) / quarkcircuit (vendor)
    compiler: str = Field(
        ...,
        max_length=64,
        description=(
            "compiler name. cmss (self-developed) performs circuit "
            "validation and compilation; vendor/institution compilers "
            "only perform circuit validation."
        ),
    )
    # task input type: 2 QASM2.0 / 3 QASM3.0
    qasmType: int = Field(
        ...,
        le=99,
        description="task input type: 2 QASM2.0 / 3 QASM3.0",
    )
    # openqasm source code
    qasm: str = Field(
        ...,
        max_length=10240,
        description="openqasm source code",
    )
    # optional parameters submitted with the task
    extend: ExtendTargetBits | None = Field(
        None, description="optional parameters submitted with the task"
    )
    # real-machine topology structure (parsed object, see Topology)
    topology: Topology = Field(
        ...,
        description="real-machine topology structure (JSON object)",
    )


class CompileData(BaseModel):
    """Response entity returned in the data field on success."""

    # compiled circuit (openqasm source code)
    compiled: str | None = Field(
        default=None,
        max_length=5120,
        description="compiled circuit (openqasm source code)",
    )


class CompileResponse(BaseModel):
    """Response body of POST /compiler/qasm/compile.

    Fields follow cloud.md section 3 response parameter table:
    code / msg / data.
    """

    # 1: success / 0: failure
    code: int = Field(..., le=9999, description="1: success / 0: failure")
    # response message
    msg: str = Field(..., max_length=128, description="response message")
    # response entity (json), only present on success
    data: CompileData | None = Field(
        default=None, description="response entity, json format"
    )
