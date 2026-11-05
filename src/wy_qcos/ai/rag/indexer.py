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

"""Index builder for the QCOS AI knowledge base.

Reads Sphinx documentation sources, chunks them, generates embeddings,
and upserts into the ai_document_chunks pgvector table.
"""

import argparse
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from wy_qcos.ai.db import get_async_session_factory
from wy_qcos.ai.rag.chunker import chunk_file
from wy_qcos.ai.rag.embedder import embed_texts
from wy_qcos.common.config import Config
from wy_qcos.db.models import AiDocumentChunk

logger = logging.getLogger(__name__)


async def index_directory(
    docs_dirs: list[Path],
    batch_size: int = 32,
    recreate: bool = False,
):
    """Index all documentation files under one or more directories."""
    factory = get_async_session_factory()
    async with factory() as session:
        # The ai_document_chunks table is created via Alembic migration.
        # Only check that it exists before proceeding.
        try:
            await session.execute(select(AiDocumentChunk).limit(1))
        except Exception as exc:
            logger.error(
                "Table ai_document_chunks does not exist. "
                "Run 'alembic upgrade head' first."
            )
            raise RuntimeError("ai_document_chunks table missing") from exc

        # Collect all .md and .rst files from every docs dir
        files = []
        for docs_dir in docs_dirs:
            if not docs_dir.exists():
                logger.warning(
                    f"Docs dir does not exist, skipping: {docs_dir}"
                )
                continue
            dir_files = sorted(
                list(docs_dir.rglob("*.md")) + list(docs_dir.rglob("*.rst"))
            )
            logger.info(
                f"Found {len(dir_files)} documentation files under {docs_dir}"
            )
            files.extend(dir_files)

        logger.info(f"Total files to index: {len(files)}")

        all_chunks = []
        for f in files:
            try:
                chunks = chunk_file(f)
                all_chunks.extend(chunks)
                logger.debug(f"  {f.name}: {len(chunks)} chunks")
            except Exception as e:
                logger.warning(f"Failed to chunk {f}: {e}")

        logger.info(f"Total chunks to index: {len(all_chunks)}")

        # Embed and upsert in batches
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            texts = [c.content for c in batch]
            try:
                embeddings = await embed_texts(texts)
            except Exception as e:
                logger.error(f"Embedding failed for batch {i}: {e}")
                continue

            now = datetime.now()
            for chunk, emb in zip(batch, embeddings):
                # Pass the embedding list directly; pgvector's Vector type
                # accepts list or ndarray, not string.
                stmt = pg_insert(AiDocumentChunk).values(
                    chunk_id=chunk.chunk_id,
                    source_file=chunk.source_file,
                    section_path=chunk.section_path,
                    title=chunk.title,
                    content=chunk.content,
                    embedding=emb,
                    metadata_=chunk.metadata,
                    created_at=now,
                    updated_at=now,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["chunk_id"],
                    set_={
                        "source_file": stmt.excluded.source_file,
                        "section_path": stmt.excluded.section_path,
                        "title": stmt.excluded.title,
                        "content": stmt.excluded.content,
                        "embedding": stmt.excluded.embedding,
                        "metadata": stmt.excluded.metadata,
                        "updated_at": now,
                    },
                )
                await session.execute(stmt)

            await session.commit()
            logger.info(
                f"Indexed batch {i // batch_size + 1}/"
                f"{(len(all_chunks) + batch_size - 1) // batch_size}"
            )

        logger.info("Indexing complete")


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Build / refresh the QCOS AI knowledge-base index."
    )
    parser.add_argument(
        "-c",
        "--config-file",
        dest="config_file",
        default="/etc/qcos/qcos.toml",
        help="Path to the QCOS config file (default: /etc/qcos/qcos.toml). "
        "The database connection URL is read from its "
        "[DATABASE] section.",
    )
    parser.add_argument(
        "--docs-dir",
        dest="docs_dirs",
        type=Path,
        nargs="+",
        default=[Path("docs/sphinx/source")],
        help="One or more paths to Sphinx documentation source directories. "
        "Accepts multiple values separated by spaces.",
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop and recreate the ai_document_chunks table",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of chunks to embed per batch",
    )
    return parser.parse_args(argv)


async def run_indexer(argv: list[str] | None = None):
    """Entry point called by bin/qcos-ai-indexer.py."""
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Load QCOS config (DATABASE / AI sections) from the TOML file.
    Config.load_config_file(args.config_file)
    await index_directory(
        args.docs_dirs,
        batch_size=args.batch_size,
        recreate=args.recreate,
    )


if __name__ == "__main__":
    asyncio.run(run_indexer())
