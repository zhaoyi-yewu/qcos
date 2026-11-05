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

"""Document chunker for Markdown and RST files.

Splits documentation into semantic chunks suitable for embedding and
vector storage. Preserves section hierarchy metadata.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentChunk:
    """A single chunk of documentation."""

    chunk_id: str
    source_file: str
    section_path: str
    title: str
    content: str
    metadata: dict


def _chunk_id(source_file: str, index: int) -> str:
    return f"{source_file}#{index}"


def chunk_markdown(text: str, source_file: str) -> list[DocumentChunk]:
    """Split a Markdown document into chunks by headers."""
    lines = text.splitlines()
    chunks: list[DocumentChunk] = []
    current_headers: list[str] = []
    current_content: list[str] = []
    current_title = ""
    chunk_index = 0

    def flush():
        nonlocal chunk_index, current_content, current_title
        if not current_content:
            return
        content = "\n".join(current_content).strip()
        if not content:
            return
        section_path = " > ".join(current_headers)
        chunks.append(
            DocumentChunk(
                chunk_id=_chunk_id(source_file, chunk_index),
                source_file=source_file,
                section_path=section_path,
                title=current_title or section_path.split(" > ")[-1],
                content=content,
                metadata={"format": "markdown"},
            )
        )
        chunk_index += 1
        current_content = []
        current_title = ""

    for line in lines:
        header_match = re.match(r"^(#{1,3})\s+(.+)$", line)
        if header_match:
            flush()
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            # Adjust header stack
            while len(current_headers) >= level:
                current_headers.pop()
            current_headers.append(title)
            current_title = title
        else:
            current_content.append(line)

    flush()
    return chunks


def chunk_rst(text: str, source_file: str) -> list[DocumentChunk]:
    """Split an RST document into chunks by section headers.

    Uses docutils to parse the AST and extract structured sections.
    Falls back to regex-based splitting if docutils is unavailable.
    """
    try:
        import docutils.core
        import docutils.nodes

        # Parse RST into AST
        settings = {"report_level": 5, "halt_level": 5}
        document = docutils.core.publish_doctree(
            text, settings_overrides=settings
        )
        return _chunk_rst_ast(document, source_file)
    except Exception:
        return _chunk_rst_fallback(text, source_file)


def _chunk_rst_ast(document, source_file: str) -> list[DocumentChunk]:
    """Extract chunks from a docutils AST."""
    import docutils.nodes

    chunks: list[DocumentChunk] = []
    section_stack: list[str] = []
    current_content: list[str] = []
    current_title = ""
    chunk_index = 0

    def flush():
        nonlocal chunk_index, current_content, current_title
        content = "\n".join(current_content).strip()
        if not content:
            return
        section_path = " > ".join(section_stack)
        chunks.append(
            DocumentChunk(
                chunk_id=_chunk_id(source_file, chunk_index),
                source_file=source_file,
                section_path=section_path,
                title=current_title or section_path.split(" > ")[-1],
                content=content,
                metadata={"format": "rst"},
            )
        )
        chunk_index += 1
        current_content = []
        current_title = ""

    for node in document.traverse():
        if isinstance(node, docutils.nodes.section):
            flush()
            # Find section title
            title_node = node.next_node(docutils.nodes.title)
            if title_node:
                title = title_node.astext().strip()
                section_stack.append(title)
                current_title = title
        elif isinstance(node, docutils.nodes.paragraph):
            current_content.append(node.astext())
        elif isinstance(node, docutils.nodes.literal_block):
            current_content.append(f"```\n{node.astext()}\n```")

    flush()
    return chunks


def _chunk_rst_fallback(text: str, source_file: str) -> list[DocumentChunk]:
    """Fallback RST chunker using regex when docutils fails."""
    lines = text.splitlines()
    chunks: list[DocumentChunk] = []
    current_headers: list[str] = []
    current_content: list[str] = []
    current_title = ""
    chunk_index = 0

    # RST section underline patterns: =, -, ~, ^, "
    underline_chars = set('=-~^"')

    def flush():
        nonlocal chunk_index, current_content, current_title
        content = "\n".join(current_content).strip()
        if not content:
            return
        section_path = " > ".join(current_headers)
        chunks.append(
            DocumentChunk(
                chunk_id=_chunk_id(source_file, chunk_index),
                source_file=source_file,
                section_path=section_path,
                title=current_title or section_path.split(" > ")[-1],
                content=content,
                metadata={"format": "rst_fallback"},
            )
        )
        chunk_index += 1
        current_content = []
        current_title = ""

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if next line is an underline
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and all(c in underline_chars for c in next_line):
                flush()
                title = line.strip()
                level = 1
                if next_line[0] == "=":
                    level = 1
                elif next_line[0] == "-":
                    level = 2
                elif next_line[0] == "~":
                    level = 3
                else:
                    level = 4
                while len(current_headers) >= level:
                    current_headers.pop()
                current_headers.append(title)
                current_title = title
                i += 2  # Skip title and underline
                continue
        current_content.append(line)
        i += 1

    flush()
    return chunks


def chunk_file(file_path: Path) -> list[DocumentChunk]:
    """Chunk a single documentation file."""
    text = file_path.read_text(encoding="utf-8")
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return chunk_markdown(text, str(file_path))
    if suffix == ".rst":
        return chunk_rst(text, str(file_path))
    return []
