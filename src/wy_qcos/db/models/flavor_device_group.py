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

import uuid
from typing import ClassVar

from sqlalchemy import (
    Column,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql.schema import Table

from wy_qcos.db.models.base import Base, GUID


class FlavorDeviceGroup(Base):
    """FlavorDeviceGroup mapping table.

    Many-to-many relationship between flavors and device_groups.
    Each record links one flavor to one device group.
    No created_at/updated_at fields (pure mapping table).
    """

    __tablename__ = "flavor_device_group_mappings"
    __table__: ClassVar[Table]

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    flavor_id = Column(
        GUID,
        ForeignKey("flavors.id"),
        nullable=False,
    )
    device_group_id = Column(
        GUID,
        ForeignKey("device_groups.id"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "flavor_id",
            "device_group_id",
            name="uq_flavor_device_group",
        ),
    )
