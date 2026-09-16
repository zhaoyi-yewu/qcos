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

"""Device table model.

Stores the manual device state override. The ``state`` column is
``nullable=True``; when ``NULL`` or ``"auto"`` the effective device
status is taken from in-memory monitor data.
"""

from typing import ClassVar

from sqlalchemy import Column, String, Table

from wy_qcos.db.models.base import BaseTable


class Device(BaseTable):
    """Device table - stores manual state override per device."""

    __tablename__ = "devices"
    __table__: ClassVar[Table]

    # Device name as primary key (no separate id column)
    name = Column(String(128), primary_key=True)
    # Manual state override:
    #   auto / online / offline / busy / disconnected /
    #   calibrating / maintain / unknown
    # NULL is treated the same as "auto"
    state = Column(String(32), nullable=True)
    # Timestamps inherited from BaseTable:
    #   created_at, updated_at
