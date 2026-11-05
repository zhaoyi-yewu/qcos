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

"""AI document chunk model for RAG knowledge base."""

from sqlalchemy import BigInteger, Column, String, Text

from wy_qcos.db.models.base import BaseTable, JSONBType

# pgvector is only available when the extension is installed in PostgreSQL.
# Use a conditional import so the model can still be loaded in environments
# without pgvector (e.g. unit tests with SQLite).
try:
    from pgvector.sqlalchemy import Vector

    _VECTOR_TYPE = Vector(1024)
except ImportError:
    _VECTOR_TYPE = Text  # fallback for non-pg databases


class AiDocumentChunk(BaseTable):
    """AI document chunk table - stores embedded documentation segments."""

    __tablename__ = "ai_document_chunks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chunk_id = Column(String(256), unique=True, nullable=False)
    source_file = Column(Text, nullable=False)
    section_path = Column(Text, nullable=True)
    title = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(_VECTOR_TYPE, nullable=True)
    metadata_ = Column("metadata", JSONBType, nullable=True)
