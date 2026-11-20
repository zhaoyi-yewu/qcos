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

"""System prompt templates for QCOS AI Agent."""

from wy_qcos.common.config import Config
from wy_qcos.common.constant import (
    DEFAULT_AI_SYSTEM_PROMPT,
    DEFAULT_AI_VISION_SYSTEM_PROMPT,
)


def _with_identity(
    prompt: str,
    display_name: str | None,
    upstream_model: str | None,
) -> str:
    """Append the current model identity to a system prompt.

    An LLM cannot sense which deployed model it is, so its answer to
    "who are you" otherwise comes from training data (or imitates the
    session history, e.g. claiming to be a different model used in an
    earlier turn). Injecting the resolved identity lets each configured
    model introduce itself correctly and consistently.
    """
    if not upstream_model:
        return prompt
    name = display_name or upstream_model
    return (
        f"{prompt}\n\n【当前模型身份】你当前由 {name}"
        f"（上游模型 {upstream_model}）驱动，作为 QCOS WebUI 中的 AI "
        '智能体为用户服务。被问"你是谁"时，以此身份作答；历史回答中'
        "其他模型的自我介绍不代表你，也不要声称无法确认自己的身份。"
    )


def build_system_prompt(
    override: str | None = None,
    display_name: str | None = None,
    upstream_model: str | None = None,
) -> str:
    """Return the text prompt for one resolved model.

    Args:
        override: per-model prompt after shared-default merging
            (``ResolvedAIModelConfig.system_prompt``). ``None`` falls
            back to the shared section value for legacy callers.
            An empty string selects the built-in default template.
        display_name: configured model display name used in the
            appended identity section (optional).
        upstream_model: actual upstream model name used in the
            appended identity section; identity is only injected when
            this is set (multi-model sessions).
    """
    if override is not None:
        prompt = override or DEFAULT_AI_SYSTEM_PROMPT
    else:
        prompt = Config.AI_AGENT.SYSTEM_PROMPT or DEFAULT_AI_SYSTEM_PROMPT
    return _with_identity(prompt, display_name, upstream_model)


def build_vision_system_prompt(
    override: str | None = None,
    display_name: str | None = None,
    upstream_model: str | None = None,
) -> str:
    """Return the vision prompt for one resolved model.

    Args:
        override: per-model vision prompt after shared-default
            merging. ``None`` falls back to the shared section value;
            an empty string selects the built-in default template.
        display_name: configured model display name used in the
            appended identity section (optional).
        upstream_model: actual upstream vision model name used in the
            appended identity section; identity is only injected when
            this is set.
    """
    if override is not None:
        prompt = override or DEFAULT_AI_VISION_SYSTEM_PROMPT
    else:
        prompt = (
            Config.AI_AGENT.VISION_SYSTEM_PROMPT
            or DEFAULT_AI_VISION_SYSTEM_PROMPT
        )
    return _with_identity(prompt, display_name, upstream_model)
