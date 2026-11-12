#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of MulanPSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

"""Unit tests for multi-model AI agent configuration."""

import pytest

from wy_qcos.common import errors
from wy_qcos.common.config import (
    AIAgentSection,
    AIModelConfig,
    Config,
    UnknownAIModelError,
)
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library


def _entry(model_id="a", **kwargs):
    return {"ID": model_id, "MODEL": f"m-{model_id}", **kwargs}


class TestModelBasics:
    def test_single_model_default(self):
        section = AIAgentSection(MODELS=[_entry("only")])
        assert section.default_model_id == "only"
        resolved = section.resolve_model()
        assert resolved.id == "only"
        assert resolved.model == "m-only"

    def test_first_entry_is_default(self):
        section = AIAgentSection(
            MODELS=[_entry("a"), _entry("b"), _entry("c")]
        )
        assert section.default_model_id == "a"
        assert section.default_model().ID == "a"
        # Explicit default ID and implicit default resolve identically.
        assert section.resolve_model("a") == section.resolve_model()

    def test_empty_models_rejected_on_validate(self):
        section = AIAgentSection()
        with pytest.raises(ValueError, match="MODELS"):
            section.validate_models()
        with pytest.raises(ValueError, match="MODELS"):
            section.resolve_model()
        assert section.default_model_id is None
        assert section.public_models() == []

    def test_duplicate_ids_rejected(self):
        with pytest.raises(ValueError, match="Duplicate"):
            AIAgentSection(MODELS=[_entry("x"), _entry("x")])

    def test_invalid_id_rejected(self):
        with pytest.raises(ValueError, match="ID"):
            AIModelConfig(ID=" bad id ", MODEL="m")
        with pytest.raises(ValueError, match="ID"):
            AIModelConfig(ID="_leading", MODEL="m")

    def test_id_is_stripped(self):
        entry = AIModelConfig(ID="  padded  ", MODEL="m")
        assert entry.ID == "padded"

    def test_too_many_models_rejected(self):
        with pytest.raises(ValueError, match="32"):
            AIAgentSection(MODELS=[_entry(f"m{i}") for i in range(33)])

    def test_unknown_id_raises_dedicated_error(self):
        section = AIAgentSection(MODELS=[_entry("a")])
        with pytest.raises(UnknownAIModelError, match="nope"):
            section.resolve_model("nope")
        # ValueError subclass -> mappable to HTTP 400 by generic handlers.
        assert issubclass(UnknownAIModelError, ValueError)


class TestSharedDefaultsAndOverrides:
    def test_inherit_shared_defaults(self):
        section = AIAgentSection(
            LLM_TEMPERATURE=0.5,
            LLM_MAX_TOKENS=1024,
            LLM_TIMEOUT=42.0,
            SYSTEM_PROMPT="shared",
            VISION_SYSTEM_PROMPT="shared-v",
            MODELS=[_entry("a")],
        )
        resolved = section.resolve_model("a")
        assert resolved.temperature == 0.5
        assert resolved.max_tokens == 1024
        assert resolved.timeout == 42.0
        assert resolved.system_prompt == "shared"
        assert resolved.vision_system_prompt == "shared-v"
        assert resolved.model_settings_enabled is False

    def test_per_model_overrides(self):
        section = AIAgentSection(
            LLM_TEMPERATURE=0.5,
            MODELS=[
                _entry(
                    "a",
                    TEMPERATURE=0.1,
                    MAX_TOKENS=128,
                    TIMEOUT=5.0,
                    MODEL_SETTINGS_ENABLED=True,
                    SYSTEM_PROMPT="custom",
                    VISION_SYSTEM_PROMPT="custom-v",
                )
            ],
        )
        resolved = section.resolve_model("a")
        assert resolved.temperature == 0.1
        assert resolved.max_tokens == 128
        assert resolved.timeout == 5.0
        assert resolved.model_settings_enabled is True
        assert resolved.system_prompt == "custom"
        assert resolved.vision_system_prompt == "custom-v"

    def test_display_name_defaults_to_model(self):
        section = AIAgentSection(
            MODELS=[_entry("a"), _entry("b", DISPLAY_NAME="B 模型")]
        )
        assert section.resolve_model("a").display_name == "m-a"
        assert section.resolve_model("b").display_name == "B 模型"


class TestLegacyMigration:
    @pytest.mark.parametrize(
        "field",
        [
            "LLM_PROVIDER",
            "LLM_BASE_URL",
            "LLM_API_KEY",
            "LLM_MODEL",
            "VISION_PROVIDER",
            "VISION_BASE_URL",
            "VISION_API_KEY",
            "VISION_MODEL",
        ],
    )
    def test_legacy_fields_rejected_with_hint(self, field):
        with pytest.raises(ValueError, match="MODELS"):
            AIAgentSection(**{field: "x"})


class TestVisionResolution:
    def test_vision_disabled_returns_none(self):
        section = AIAgentSection(MODELS=[_entry("a")])
        assert section.resolve_vision("a") is None

    def test_vision_falls_back_to_own_connection(self):
        section = AIAgentSection(
            MODELS=[
                _entry(
                    "a",
                    PROVIDER="openai",
                    BASE_URL="http://a/v1",
                    API_KEY="ka",
                    VISION_ENABLED=True,
                )
            ]
        )
        vision = section.resolve_vision("a")
        assert vision.provider == "openai"
        assert vision.base_url == "http://a/v1"
        assert vision.api_key == "ka"
        assert vision.model == "m-a"

    def test_vision_overrides(self):
        section = AIAgentSection(
            MODELS=[
                _entry(
                    "a",
                    BASE_URL="http://a/v1",
                    API_KEY="ka",
                    VISION_ENABLED=True,
                    VISION_PROVIDER="anthropic",
                    VISION_BASE_URL="http://av/v1",
                    VISION_API_KEY="kv",
                    VISION_MODEL="m-vision",
                )
            ]
        )
        vision = section.resolve_vision("a")
        assert vision.provider == "anthropic"
        assert vision.base_url == "http://av/v1"
        assert vision.api_key == "kv"
        assert vision.model == "m-vision"


class TestPublicModels:
    def test_public_payload_has_no_sensitive_fields(self):
        section = AIAgentSection(
            MODELS=[
                _entry(
                    "a",
                    BASE_URL="http://secret-host/v1",
                    API_KEY="sk-secret",
                    VISION_ENABLED=True,
                )
            ]
        )
        public = section.public_models()
        assert public == [
            {
                "id": "a",
                "display_name": "m-a",
                "model": "m-a",
                "supports_vision": True,
            }
        ]
        dumped = str(public)
        assert "sk-secret" not in dumped
        assert "secret-host" not in dumped
        assert "API_KEY" not in dumped
        assert "BASE_URL" not in dumped


class TestMasking:
    def test_model_api_keys_masked_recursively(self):
        section = AIAgentSection(
            MODELS=[
                _entry("a", API_KEY="sk-a", VISION_API_KEY="sk-av"),
                _entry("b", API_KEY="sk-b"),
            ]
        )
        masked = Library.mask_password_from_pydantic(section)
        assert masked["MODELS"][0]["API_KEY"] == "*" * 8
        assert masked["MODELS"][0]["VISION_API_KEY"] == "*" * 8
        assert masked["MODELS"][1]["API_KEY"] == "*" * 8
        # Non-sensitive fields stay readable.
        assert masked["MODELS"][0]["ID"] == "a"
        assert masked["MODELS"][0]["MODEL"] == "m-a"
        # Original object is untouched.
        assert section.MODELS[0].API_KEY == "sk-a"


class TestConfigFileLoading:
    def _write_config(self, tmp_path, body):
        config_file = tmp_path / "qcos-test.toml"
        config_file.write_text(body, encoding="utf-8")
        return str(config_file)

    def test_models_array_replaces_not_appends(self, tmp_path):
        """Repeated main-config loads replace MODELS wholesale."""
        path = self._write_config(
            tmp_path,
            """
[AI.AGENT]
[[AI.AGENT.MODELS]]
ID = "first"
MODEL = "m-first"
[[AI.AGENT.MODELS]]
ID = "second"
MODEL = "m-second"
""",
        )
        Config.load_config_file(path)
        assert [m.ID for m in Config.AI_AGENT.MODELS] == ["first", "second"]
        Config.load_config_file(path)
        assert [m.ID for m in Config.AI_AGENT.MODELS] == ["first", "second"]

    def test_recursive_decryption(self, tmp_path):
        ok, _err, encrypted = Library.encrypt_text(
            "sk-live",
            encryption_prefix=Constant.ENCRYPTION_PREFIX,
            fernet_key=Constant.DEFAULT_FERNET_KEY,
        )
        assert ok
        path = self._write_config(
            tmp_path,
            f"""
[AI.AGENT]
[[AI.AGENT.MODELS]]
ID = "enc"
MODEL = "m-enc"
API_KEY = "{encrypted}"
VISION_ENABLED = true
VISION_API_KEY = "{encrypted}"
""",
        )
        Config.load_config_file(path)
        resolved = Config.AI_AGENT.resolve_model("enc")
        assert resolved.api_key == "sk-live"
        assert Config.AI_AGENT.resolve_vision("enc").api_key == "sk-live"

    def test_decryption_failure_hides_ciphertext(self, tmp_path):
        cipher = f"{Constant.ENCRYPTION_PREFIX}invalid-ciphertext"
        path = self._write_config(
            tmp_path,
            f"""
[AI.AGENT]
[[AI.AGENT.MODELS]]
ID = "bad"
MODEL = "m-bad"
API_KEY = "{cipher}"
""",
        )
        with pytest.raises(errors.GenericException) as exc_info:
            Config.load_config_file(path)
        assert "invalid-ciphertext" not in str(exc_info.value)


@pytest.fixture(autouse=True)
def _restore_default_config():
    """Keep the global Config pristine for other test modules."""
    yield
    fresh = AIAgentSection()
    Config.AI_AGENT = fresh
    if Config._model is not None:
        Config._model.AI_AGENT = fresh
