#!/usr/bin/env python
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

"""Build / refresh the QCOS AI knowledge-base index.

Reads Sphinx sources from docs/sphinx/source/, chunks them, embeds them,
and upserts into the ai_document_chunks pgvector table.

Usage:
    python bin/qcos-ai-indexer.py \
        [--config-file /etc/qcos/qcos.toml] \
        [--docs-dir docs/sphinx/source] \
        [--recreate]            # drop & recreate the table
        [--batch-size 32]
"""

import asyncio
from wy_qcos.ai.rag.indexer import run_indexer


if __name__ == "__main__":
    asyncio.run(run_indexer())
