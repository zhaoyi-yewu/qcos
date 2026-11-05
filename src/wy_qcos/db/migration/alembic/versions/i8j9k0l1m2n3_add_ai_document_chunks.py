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
"""Add ai_document_chunks table for RAG knowledge base.

Revision ID: i8j9k0l1m2n3
Revises: h7c8d9e0f1g2
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i8j9k0l1m2n3"
down_revision: str | Sequence[str] | None = "h7c8d9e0f1g2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector in THIS database before the conditional ALTER
    # below (CREATE EXTENSION is per-database; enabling it in the
    # "postgres" maintenance database does not make the vector type
    # available in "qcos"). The migration usually runs as the "qcos"
    # user, which is NOT a superuser and cannot create extensions.
    # run-docker.sh is therefore expected to pre-enable the extension
    # with the postgres superuser (psql -d qcos). If it is somehow
    # missing and the current role lacks permission, warn and continue:
    # the DO blocks below degrade gracefully and re-running the
    # migration after enabling the extension converts the column.
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except sa.exc.OperationalError as exc:
        print(
            "WARNING: could not create pgvector extension "
            f"({exc.orig if hasattr(exc, 'orig') else exc}); "
            "the embedding column stays as Text until the extension is "
            "enabled by a superuser and the migration is re-run."
        )

    op.create_table(
        "ai_document_chunks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chunk_id", sa.String(256), nullable=False),
        # Use Text for file paths to avoid length limits on deep nesting
        sa.Column("source_file", sa.Text(), nullable=False),
        sa.Column("section_path", sa.Text(), nullable=True),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        # pgvector column: use raw SQL because SQLAlchemy does not have
        # a native Vector type without the pgvector-python package.
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chunk_id"),
    )

    # Convert embedding column to vector type if pgvector is available
    # (this is a no-op if the extension is missing)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            ) THEN
                ALTER TABLE ai_document_chunks
                ALTER COLUMN embedding TYPE vector(1024)
                USING embedding::vector;
            END IF;
        END
        $$;
        """
    )

    # HNSW index for cosine similarity search (only when pgvector exists)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            ) THEN
                CREATE INDEX ai_document_chunks_embedding_idx
                ON ai_document_chunks
                USING hnsw (embedding vector_cosine_ops);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ai_document_chunks_embedding_idx")
    op.drop_table("ai_document_chunks")
