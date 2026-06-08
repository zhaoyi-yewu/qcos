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
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from wy_qcos.db.models.base import GUID


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "a9f862c42ac4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create job table
    op.create_table(
        "job",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("project_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=True),
        sa.Column("flow_run_id", GUID(), nullable=True),
        sa.Column("job_name", sa.String(length=128), nullable=True),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column(
            "job_status",
            sa.String(length=32),
            nullable=True,
            server_default="UNKNOWN",
        ),
        sa.Column("job_priority", sa.Integer(), nullable=True),
        sa.Column("backend", sa.String(length=32), nullable=False),
        sa.Column("code_type", sa.String(length=32), nullable=False),
        sa.Column("source_code", sa.JSON(), nullable=True),
        sa.Column(
            "code_compression_level",
            sa.Integer(),
            nullable=True,
            server_default="0",
        ),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("driver_options", sa.JSON(), nullable=True),
        sa.Column("transpiler", sa.String(length=32), nullable=True),
        sa.Column("transpiler_options", sa.JSON(), nullable=True),
        sa.Column("circuit_aggregation", sa.String(length=32), nullable=True),
        sa.Column("shots", sa.Integer(), nullable=False),
        sa.Column(
            "progress", sa.Integer(), nullable=True, server_default="-1"
        ),
        sa.Column("profiling", sa.JSON(), nullable=True),
        sa.Column("callbacks", sa.JSON(), nullable=True),
        sa.Column(
            "is_callback_success",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "dry_run", sa.Boolean(), nullable=True, server_default="false"
        ),
        sa.Column("results", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_id"), "job", ["id"], unique=False)
    op.create_index(op.f("ix_job_project_id"), "job", ["project_id"])
    op.create_index(op.f("ix_job_user_id"), "job", ["user_id"])
    op.create_index(op.f("ix_job_created_at"), "job", ["created_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_job_created_at"), table_name="job")
    op.drop_index(op.f("ix_job_user_id"), table_name="job")
    op.drop_index(op.f("ix_job_project_id"), table_name="job")
    op.drop_index(op.f("ix_job_id"), table_name="job")
    op.drop_table("job")
