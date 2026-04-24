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


# revision identifiers, used by Alembic.
revision: str = "a9f862c42ac4"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table (without roles JSON field - now using
    # user_roles association table)
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_name", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=True),
        sa.Column("is_locked", sa.Boolean(), nullable=True),
        sa.Column("last_login", sa.DateTime(), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(), nullable=True),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.Column("password_expiry_days", sa.Integer(), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(
        op.f("ix_users_user_name"), "users", ["user_name"], unique=True
    )

    # Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("role_name", sa.String(length=50), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
    op.create_index(
        op.f("ix_roles_role_name"), "roles", ["role_name"], unique=True
    )

    # Create user_roles table (many-to-many association table)
    op.create_table(
        "user_roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_roles_id"), "user_roles", ["id"], unique=False
    )
    # Composite unique index to prevent duplicate user-role mappings
    op.create_index(
        "ix_user_roles_user_id_role_id",
        "user_roles",
        ["user_id", "role_id"],
        unique=True,
    )

    # Create login_logs table
    op.create_table(
        "login_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_name", sa.String(length=50), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=False),
        sa.Column("login_time", sa.DateTime(), nullable=True),
        sa.Column("login_status", sa.Boolean(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_login_logs_id"), "login_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_login_logs_user_name"),
        "login_logs",
        ["user_name"],
        unique=False,
    )

    # Create token_blacklist table
    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("token_jti", sa.String(length=36), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_token_blacklist_id"), "token_blacklist", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_token_blacklist_token_jti"),
        "token_blacklist",
        ["token_jti"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_token_blacklist_token_jti"), table_name="token_blacklist"
    )
    op.drop_index(op.f("ix_token_blacklist_id"), table_name="token_blacklist")
    op.drop_table("token_blacklist")

    op.drop_index(op.f("ix_login_logs_user_name"), table_name="login_logs")
    op.drop_index(op.f("ix_login_logs_id"), table_name="login_logs")
    op.drop_table("login_logs")

    # Drop composite index first, then the id index
    op.drop_index("ix_user_roles_user_id_role_id", table_name="user_roles")
    op.drop_index(op.f("ix_user_roles_id"), table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index(op.f("ix_roles_role_name"), table_name="roles")
    op.drop_index(op.f("ix_roles_id"), table_name="roles")
    op.drop_table("roles")

    op.drop_index(op.f("ix_users_user_name"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
