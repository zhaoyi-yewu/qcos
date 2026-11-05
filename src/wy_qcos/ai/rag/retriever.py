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

"""pgvector-based retriever for RAG.

Queries the ai_document_chunks table using cosine similarity on
embeddings to find the most relevant documentation chunks.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import select

from wy_qcos.ai.db import get_async_session_factory
from wy_qcos.common.config import Config
from wy_qcos.db.models import AiDocumentChunk

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved document chunk with similarity score."""

    chunk_id: str
    source_file: str
    section_path: str
    title: str
    content: str
    score: float


class RagRetriever:
    """Retrieve relevant documentation chunks via pgvector."""

    def __init__(self, top_k: int | None = None):
        self.top_k = top_k or Config.AI_AGENT.RAG_TOP_K

    async def retrieve(
        self, query_embedding: list[float], top_k: int | None = None
    ) -> list[RetrievedChunk]:
        """Retrieve the top-k most similar chunks for a query embedding."""
        k = top_k or self.top_k
        factory = get_async_session_factory()
        async with factory() as session:
            try:
                # Use pgvector's ORM integration for cosine distance query.
                # The embedding column is defined as Vector(1024) in the model,
                # so cosine_distance() handles the vector type conversion
                # automatically without raw SQL or CAST.
                distance = AiDocumentChunk.embedding.cosine_distance(
                    query_embedding
                )
                stmt = (
                    select(
                        AiDocumentChunk.chunk_id,
                        AiDocumentChunk.source_file,
                        AiDocumentChunk.section_path,
                        AiDocumentChunk.title,
                        AiDocumentChunk.content,
                        (1 - distance).label("score"),
                    )
                    .order_by(distance)
                    .limit(k)
                )
                result = await session.execute(stmt)
                rows = result.all()
                return [
                    RetrievedChunk(
                        chunk_id=row.chunk_id,
                        source_file=row.source_file,
                        section_path=row.section_path or "",
                        title=row.title or "",
                        content=row.content,
                        score=float(row.score),
                    )
                    for row in rows
                ]
            except Exception as e:
                logger.warning(f"RAG retrieval failed: {e}")
                return []


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a context string for the LLM prompt."""
    if not chunks:
        return ""
    lines = ["Relevant documentation excerpts:"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"\n--- [{i}] {chunk.title} ({chunk.source_file}) ---")
        lines.append(chunk.content[:2000])  # Cap each chunk at 2000 chars
    return "\n".join(lines)
