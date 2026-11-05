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
#     EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
#     MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Tests for shell.py AI features.

Covers AI SSE stream consumption (_print_ai_stream), the ai-ask command
and the ai-chat interactive REPL commands.
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from wy_qcos_client.common import errors
from wy_qcos_client.shell import AiAsk, AiChat, _print_ai_stream


class TestPrintAiStream:
    def _response(self, lines):
        resp = MagicMock()
        resp.iter_lines.return_value = iter(lines)
        return resp

    def test_chunk_and_done(self, capsys):
        events = [
            "data: " + json.dumps({"type": "chunk", "delta": "你"}),
            "data: " + json.dumps({"type": "chunk", "delta": "好"}),
            "data: " + json.dumps({"type": "done", "message_id": "sid-1"}),
            "",
            "not a data line",
        ]
        resp = self._response(events)
        ret = _print_ai_stream(resp)
        assert ret == "sid-1"
        out = capsys.readouterr().out
        assert "你好" in out
        resp.close.assert_called_once()

    def test_session_id_spelling_preferred(self):
        resp = self._response([
            "data: "
            + json.dumps({
                "type": "done",
                "session_id": "s1",
                "message_id": "m",
            })
        ])
        assert _print_ai_stream(resp) == "s1"

    def test_error_event_raises(self):
        resp = self._response([
            "data: " + json.dumps({"type": "error", "error": "boom"})
        ])
        with pytest.raises(errors.GenericException, match="boom"):
            _print_ai_stream(resp)
        resp.close.assert_called_once()

    def test_invalid_json_line_skipped(self, capsys):
        resp = self._response(["data: {invalid json"])
        assert _print_ai_stream(resp) is None
        resp.close.assert_called_once()

    def test_tool_events_shown(self, capsys):
        resp = self._response([
            "data: " + json.dumps({"type": "tool_call", "tool": "qcos_ping"}),
            "data: "
            + json.dumps({"type": "tool_result", "tool": "qcos_ping"}),
        ])
        _print_ai_stream(resp, show_tool_events=True)
        out = capsys.readouterr().out
        assert "[tool call: qcos_ping]" in out
        assert "[tool result: qcos_ping]" in out

    def test_tool_events_hidden_by_default(self, capsys):
        resp = self._response([
            "data: " + json.dumps({"type": "tool_call", "tool": "qcos_ping"}),
        ])
        _print_ai_stream(resp, show_tool_events=False)
        out = capsys.readouterr().out
        assert "tool call" not in out


class TestAiAsk:
    def test_take_action(self):
        cmd = AiAsk(Mock(), None)
        cmd.app.client = Mock()
        resp = MagicMock()
        cmd.app.client.ai_chat_stream.return_value = resp
        parsed = Mock(
            message=["hello", "world"],
            session_id=None,
            no_rag=False,
            show_tools=True,
        )
        with patch("wy_qcos_client.shell._print_ai_stream") as mock_print:
            cmd.take_action(parsed)
        cmd.app.client.ai_chat_stream.assert_called_once_with(
            message="hello world", session_id=None, enable_rag=True
        )
        mock_print.assert_called_once_with(resp, show_tool_events=True)


class TestAiChatRepl:
    def _make_cmd(self, inputs, client_mock=None):
        cmd = AiChat(Mock(), None)
        cmd.app.client = client_mock or Mock()
        # keep stdin prompts quiet
        inputs_iter = iter(inputs)

        def fake_input(prompt=""):
            try:
                return next(inputs_iter)
            except StopIteration as e:
                raise EOFError from e

        return cmd, fake_input

    def test_exit_immediately(self, capsys):
        cmd, fake_input = self._make_cmd(["/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "AI chat session started" in out

    def test_eof_breaks(self, capsys):
        cmd, _ = self._make_cmd([])
        with patch("builtins.input", side_effect=EOFError):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )

    def test_help_command(self, capsys):
        cmd, fake_input = self._make_cmd(["/help", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "/new [title]" in out

    def test_new_session_command(self, capsys):
        client_mock = Mock()
        client_mock.ai_create_session.return_value = {
            "session_id": "s-new",
            "title": "t",
        }
        cmd, fake_input = self._make_cmd(
            ["/new my title", "/exit"], client_mock
        )
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        client_mock.ai_create_session.assert_called_once_with(title="my title")
        out = capsys.readouterr().out
        assert "New session created: s-new" in out

    def test_new_session_default_title(self, capsys):
        client_mock = Mock()
        client_mock.ai_create_session.return_value = {
            "session_id": "s-new",
        }
        cmd, fake_input = self._make_cmd(["/new", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        client_mock.ai_create_session.assert_called_once_with(
            title="CLI conversation"
        )

    def test_list_sessions_command(self, capsys):
        client_mock = Mock()
        client_mock.ai_list_sessions.return_value = [
            {
                "session_id": "s1",
                "created_at": 1700000000,
                "message_count": 3,
                "title": "hello",
            }
        ]
        cmd, fake_input = self._make_cmd(["/list", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id="s1", no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "s1" in out
        assert "hello" in out

    def test_list_sessions_empty(self, capsys):
        client_mock = Mock()
        client_mock.ai_list_sessions.return_value = []
        cmd, fake_input = self._make_cmd(["/list", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "No sessions found" in capsys.readouterr().out

    def test_use_command(self, capsys):
        cmd, fake_input = self._make_cmd(["/use s9", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Switched to session: s9" in capsys.readouterr().out

    def test_use_without_arg(self, capsys):
        cmd, fake_input = self._make_cmd(["/use", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Usage: /use <session_id>" in capsys.readouterr().out

    def test_history_command(self, capsys):
        client_mock = Mock()
        client_mock.ai_get_session.return_value = {
            "messages": [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ]
        }
        cmd, fake_input = self._make_cmd(["/history", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id="s1", no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "[user] hi" in out
        assert "[assistant] hello" in out

    def test_history_without_session(self, capsys):
        cmd, fake_input = self._make_cmd(["/history", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "No active session" in capsys.readouterr().out

    def test_delete_command(self, capsys):
        client_mock = Mock()
        cmd, fake_input = self._make_cmd(["/delete s1", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id="s1", no_rag=False, show_tools=False)
            )
        client_mock.ai_delete_session.assert_called_once_with("s1")
        out = capsys.readouterr().out
        assert "Session deleted: s1" in out

    def test_delete_without_arg(self, capsys):
        cmd, fake_input = self._make_cmd(["/delete", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Usage: /delete" in capsys.readouterr().out

    def test_rag_toggle(self, capsys):
        cmd, fake_input = self._make_cmd(["/rag off", "/rag on", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "RAG: off" in out
        assert "RAG: on" in out

    def test_tools_toggle(self, capsys):
        cmd, fake_input = self._make_cmd(["/tools on", "/tools off", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        out = capsys.readouterr().out
        assert "Tool markers: on" in out
        assert "Tool markers: off" in out

    def test_unknown_command(self, capsys):
        cmd, fake_input = self._make_cmd(["/frobnicate", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Unknown command: /frobnicate" in capsys.readouterr().out

    def test_empty_line_skipped(self, capsys):
        cmd, fake_input = self._make_cmd(["", "/exit"])
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        # no chat request happened
        cmd.app.client.ai_chat_stream.assert_not_called()

    def test_regular_message_streams(self, capsys):
        client_mock = Mock()
        resp = MagicMock()
        resp.iter_lines.return_value = iter([
            "data: " + json.dumps({"type": "chunk", "delta": "reply"}),
            "data: " + json.dumps({"type": "done", "message_id": "s-new"}),
        ])
        client_mock.ai_chat_stream.return_value = resp
        cmd, fake_input = self._make_cmd(["hi", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        client_mock.ai_chat_stream.assert_called_once_with(
            message="hi", session_id=None, enable_rag=True
        )
        out = capsys.readouterr().out
        assert "reply" in out

    def test_generic_exception_printed(self, capsys):
        client_mock = Mock()
        client_mock.ai_chat_stream.side_effect = errors.GenericException(
            "AI down"
        )
        cmd, fake_input = self._make_cmd(["hi", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Error: AI down" in capsys.readouterr().out

    def test_request_failure_printed(self, capsys):
        client_mock = Mock()
        client_mock.ai_chat_stream.side_effect = RuntimeError("net")
        cmd, fake_input = self._make_cmd(["hi", "/exit"], client_mock)
        with patch("builtins.input", side_effect=fake_input):
            cmd.take_action(
                Mock(session_id=None, no_rag=False, show_tools=False)
            )
        assert "Request failed: net" in capsys.readouterr().out
