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
"""Add composite index on job(backend, job_status).

Speeds up COUNT(*) ... WHERE backend=? AND job_status=? queries
issued by get-device / list-devices job_count and the auto
scheduler load counting.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-31
"""

from collections.abc import Sequence


from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Composite index name
INDEX_NAME = "ix_job_backend_job_status"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(INDEX_NAME, "job", ["backend", "job_status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(INDEX_NAME, table_name="job")
