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

"""Add flavor_device_group mapping table.

Also creates flavors and device_groups tables, and adds
job auto scheduling fields.

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
    # Create flavors table
    op.create_table(
        "flavors",
        sa.Column("id", GUID(), nullable=False),
        sa.Column(
            "project_id",
            GUID(),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column(
            "is_public",
            sa.Boolean(),
            nullable=True,
        ),
        sa.Column("min_qubits", sa.Integer(), nullable=True),
        sa.Column("max_qubits", sa.Integer(), nullable=True),
        sa.Column("gate_fidelity_1q_min", sa.Float(), nullable=True),
        sa.Column("gate_fidelity_2q_min", sa.Float(), nullable=True),
        sa.Column("extra_properties", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_flavor_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_flavors_project_id_projects",
        ),
    )
    op.create_index(op.f("ix_flavors_id"), "flavors", ["id"], unique=False)

    # Create device_groups table
    op.create_table(
        "device_groups",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("project_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("device_names", sa.JSON(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_device_group_name"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_device_groups_project_id_projects",
        ),
    )
    op.create_index(
        op.f("ix_device_groups_id"),
        "device_groups",
        ["id"],
        unique=False,
    )

    # Create flavor_device_group_mappings mapping table
    op.create_table(
        "flavor_device_group_mappings",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("flavor_id", GUID(), nullable=False),
        sa.Column("device_group_id", GUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["flavor_id"],
            ["flavors.id"],
            name="fk_fdgm_flavor_id",
        ),
        sa.ForeignKeyConstraint(
            ["device_group_id"],
            ["device_groups.id"],
            name="fk_fdgm_device_group_id",
        ),
        sa.UniqueConstraint(
            "flavor_id",
            "device_group_id",
            name="uq_fdgm",
        ),
    )
    op.create_index(
        "ix_fdgm_flavor_id",
        "flavor_device_group_mappings",
        ["flavor_id"],
        unique=False,
    )
    op.create_index(
        "ix_fdgm_device_group_id",
        "flavor_device_group_mappings",
        ["device_group_id"],
        unique=False,
    )

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
        "fk_job_flavor_id_flavors",
        "job",
        "flavors",
        ["flavor_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_job_flavor_id_flavors", "job", type_="foreignkey")
    op.drop_column("job", "extra_specs")
    op.drop_column("job", "flavor_id")

    op.drop_index(
        "ix_fdgm_device_group_id",
        table_name="flavor_device_group_mappings",
    )
    op.drop_index(
        "ix_fdgm_flavor_id",
        table_name="flavor_device_group_mappings",
    )
    op.drop_constraint(
        "uq_fdgm",
        "flavor_device_group_mappings",
        type_="unique",
    )
    op.drop_constraint(
        "fk_fdgm_device_group_id",
        "flavor_device_group_mappings",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_fdgm_flavor_id",
        "flavor_device_group_mappings",
        type_="foreignkey",
    )
    op.drop_table("flavor_device_group_mappings")

    op.drop_index(op.f("ix_device_groups_id"), table_name="device_groups")
    op.drop_constraint(
        "fk_device_groups_project_id_projects",
        "device_groups",
        type_="foreignkey",
    )
    op.drop_table("device_groups")

    op.drop_index(op.f("ix_flavors_id"), table_name="flavors")
    op.drop_constraint(
        "fk_flavors_project_id_projects", "flavors", type_="foreignkey"
    )
    op.drop_table("flavors")
