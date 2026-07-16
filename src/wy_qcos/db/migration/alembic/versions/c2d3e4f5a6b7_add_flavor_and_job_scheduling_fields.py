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

"""Add flavor table and job auto scheduling fields.

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-07-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from wy_qcos.db.models.base import GUID


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create flavor table
    op.create_table(
        "flavor",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=True,
            server_default="true",
        ),
        sa.Column("specs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_flavor_name"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_flavor_id"), "flavor", ["id"], unique=False)

    # Add auto scheduling fields to job table
    op.add_column(
        "job",
        sa.Column("flavor_id", GUID(), nullable=True),
    )
    op.add_column(
        "job",
        sa.Column("extra_specs", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_job_flavor_id_flavor",
        "job",
        "flavor",
        ["flavor_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_job_flavor_id_flavor", "job", type_="foreignkey")
    op.drop_column("job", "extra_specs")
    op.drop_column("job", "flavor_id")

    op.drop_index(op.f("ix_flavor_id"), table_name="flavor")
    op.drop_table("flavor")
