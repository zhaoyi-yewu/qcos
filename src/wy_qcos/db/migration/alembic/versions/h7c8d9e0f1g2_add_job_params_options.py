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
"""Add params and options columns to job table.

Revision ID: h7c8d9e0f1g2
Revises: g6b7c8d9e0f1
Create Date: 2026-09-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h7c8d9e0f1g2"
down_revision: str | Sequence[str] | None = "g6b7c8d9e0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "job"


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        TABLE_NAME,
        sa.Column("params", sa.JSON(), nullable=True),
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("options", sa.JSON(), nullable=True),
    )
    op.add_column(
        TABLE_NAME,
        sa.Column("backend_type", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column(TABLE_NAME, "backend_type")
    op.drop_column(TABLE_NAME, "options")
    op.drop_column(TABLE_NAME, "params")
