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

"""Embedding client for RAG.

Calls an OpenAI-compatible embedding endpoint (vLLM, TEI, Infinity,
OpenAI, etc.) to generate vector embeddings for text chunks.
"""

import logging
from typing import Any

import httpx

from wy_qcos.common.config import Config

logger = logging.getLogger(__name__)


async def embed_texts(
    texts: list[str],
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> list[list[float]]:
    """Generate embeddings for a list of texts.

    Args:
        texts: List of text strings to embed.
        model: Embedding model name. Defaults to
            Config.AI_AGENT.EMBEDDING_MODEL.
        base_url: Embedding endpoint URL. Defaults to
            Config.AI_AGENT.EMBEDDING_BASE_URL.
        api_key: API key. Defaults to Config.AI_AGENT.EMBEDDING_API_KEY.

    Returns:
        List of embedding vectors (each a list of floats).
    """
    cfg = Config.AI_AGENT
    model = model or cfg.EMBEDDING_MODEL
    base_url = (base_url or cfg.EMBEDDING_BASE_URL).rstrip("/")
    api_key = api_key or cfg.EMBEDDING_API_KEY

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    payload: dict[str, Any] = {
        "model": model,
        "input": texts,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{base_url}/embeddings",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    # OpenAI embedding response format: data[i].embedding
    embeddings = [item["embedding"] for item in data.get("data", [])]
    return embeddings


async def embed_single(text: str, **kwargs) -> list[float]:
    """Embed a single text string."""
    results = await embed_texts([text], **kwargs)
    return results[0] if results else []
