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

"""Unit tests for SubcircuitResultCache."""

import json
from unittest.mock import MagicMock, patch

import pytest

from wy_qcos.transpiler.common.wirecut.result_cache import (
    SUBCIRCUIT_RESULT_CACHE_PREFIX,
    SUBCIRCUIT_RESULT_CACHE_TTL,
    SUBCIRCUIT_RESULT_CACHE_VERSION,
    SubcircuitResultCache,
    _json_default,
)


class TestSubcircuitResultCache:
    """Test SubcircuitResultCache class."""

    def test_init_without_redis(self):
        cache = SubcircuitResultCache()
        assert cache.redis_client is None

    def test_init_with_redis(self):
        mock_redis = MagicMock()
        cache = SubcircuitResultCache(mock_redis)
        assert cache.redis_client is mock_redis

    def test_from_job_info_no_redis_config(self):
        job_info = {"global": {"configs": {}}}
        cache = SubcircuitResultCache.from_job_info(job_info)
        assert cache.redis_client is None

    def test_from_job_info_with_redis_url(self):
        job_info = {
            "global": {
                "configs": {"REDIS": {"REDIS_URL": "redis://localhost:6379/0"}}
            }
        }
        with patch("redis.Redis.from_url") as mock_from_url:
            mock_client = MagicMock()
            mock_from_url.return_value = mock_client
            cache = SubcircuitResultCache.from_job_info(job_info)
            assert cache.redis_client is mock_client
            mock_from_url.assert_called_once()

    def test_execution_context(self):
        job_info = {
            "data": {
                "backend": "dev1",
                "driver_options": {"opt": 1},
                "dry_run": True,
                "qec_options": {"qec": 1},
                "shots": 2048,
                "transpiler_options": {"t": 1},
            },
            "device": {"name": "dev1"},
            "driver": {"name": "drv1"},
            "transpiler": {"name": "cmss"},
        }
        ctx = SubcircuitResultCache.execution_context(job_info)
        assert ctx["backend"] == "dev1"
        assert ctx["device"] == {"name": "dev1"}
        assert ctx["driver"] == {"name": "drv1"}
        assert ctx["driver_options"] == {"opt": 1}
        assert ctx["dry_run"] is True
        assert ctx["qec_options"] == {"qec": 1}
        assert ctx["shots"] == 2048
        assert ctx["transpiler"] == {"name": "cmss"}
        assert ctx["transpiler_options"] == {"t": 1}

    def test_execution_context_defaults(self):
        job_info = {"data": {}}
        ctx = SubcircuitResultCache.execution_context(job_info)
        assert ctx["dry_run"] is False
        assert ctx["shots"] == 10  # Constant.DEFAULT_SHOTS

    def test_execution_context_none_values(self):
        job_info = {
            "data": {
                "backend": None,
                "driver_options": None,
                "qec_options": None,
                "transpiler_options": None,
            },
            "device": None,
            "driver": None,
            "transpiler": None,
        }
        ctx = SubcircuitResultCache.execution_context(job_info)
        assert ctx["backend"] is None
        assert ctx["device"] is None
        assert ctx["driver"] is None
        assert ctx["transpiler"] is None

    def test_cache_key(self):
        job_info = {"data": {"backend": "dev1"}}
        key = SubcircuitResultCache.cache_key("qasm_code", job_info)
        assert key.startswith(f"{SUBCIRCUIT_RESULT_CACHE_PREFIX}:")
        # Same input should produce same key
        key2 = SubcircuitResultCache.cache_key("qasm_code", job_info)
        assert key == key2

    def test_cache_key_different_for_different_input(self):
        job_info1 = {"data": {"backend": "dev1"}}
        job_info2 = {"data": {"backend": "dev2"}}
        key1 = SubcircuitResultCache.cache_key("qasm", job_info1)
        key2 = SubcircuitResultCache.cache_key("qasm", job_info2)
        assert key1 != key2

    def test_get_no_redis(self):
        cache = SubcircuitResultCache()
        assert cache.get("qasm", {}) is None

    def test_get_redis_error(self):
        import redis as redis_module

        mock_redis = MagicMock()
        mock_redis.get.side_effect = redis_module.RedisError(
            "connection error"
        )
        cache = SubcircuitResultCache(mock_redis)
        result = cache.get("qasm", {})
        assert result is None
        # After error, redis_client should be set to None
        assert cache.redis_client is None

    def test_get_cache_miss(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        cache = SubcircuitResultCache(mock_redis)
        assert cache.get("qasm", {}) is None

    def test_get_invalid_version(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({
            "version": 999,
            "result": {"counts": {"0": 100}},
        })
        cache = SubcircuitResultCache(mock_redis)
        assert cache.get("qasm", {}) is None

    def test_get_invalid_result_type(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({
            "version": SUBCIRCUIT_RESULT_CACHE_VERSION,
            "result": "not-a-dict",
        })
        cache = SubcircuitResultCache(mock_redis)
        assert cache.get("qasm", {}) is None

    def test_get_invalid_json(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "not-json"
        cache = SubcircuitResultCache(mock_redis)
        assert cache.get("qasm", {}) is None

    def test_get_success(self):
        mock_redis = MagicMock()
        expected = {"counts": {"0": 512, "1": 512}}
        mock_redis.get.return_value = json.dumps({
            "version": SUBCIRCUIT_RESULT_CACHE_VERSION,
            "result": expected,
        })
        cache = SubcircuitResultCache(mock_redis)
        result = cache.get("qasm", {})
        assert result == expected

    def test_set_no_redis(self):
        cache = SubcircuitResultCache()
        # Should not raise
        cache.set("qasm", {}, {"counts": {}})

    def test_set_empty_result(self):
        mock_redis = MagicMock()
        cache = SubcircuitResultCache(mock_redis)
        cache.set("qasm", {}, {})
        mock_redis.set.assert_not_called()

    def test_set_serialization_error(self):
        mock_redis = MagicMock()
        cache = SubcircuitResultCache(mock_redis)

        class Unserializable:
            pass

        cache.set("qasm", {}, {"bad": Unserializable()})
        mock_redis.set.assert_not_called()

    def test_set_redis_error(self):
        import redis as redis_module

        mock_redis = MagicMock()
        mock_redis.set.side_effect = redis_module.RedisError(
            "connection error"
        )
        cache = SubcircuitResultCache(mock_redis)
        cache.set("qasm", {}, {"counts": {"0": 100}})
        # After error, redis_client should be set to None
        assert cache.redis_client is None

    def test_set_success(self):
        mock_redis = MagicMock()
        cache = SubcircuitResultCache(mock_redis)
        result = {"counts": {"0": 512, "1": 512}}
        cache.set("qasm", {}, result)
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0].startswith(SUBCIRCUIT_RESULT_CACHE_PREFIX)
        payload = json.loads(call_args[0][1])
        assert payload["version"] == SUBCIRCUIT_RESULT_CACHE_VERSION
        assert payload["result"] == result
        assert call_args[1]["ex"] == SUBCIRCUIT_RESULT_CACHE_TTL


class TestJsonDefault:
    """Test _json_default helper function."""

    def test_numpy_tolist(self):
        class FakeArray:
            def tolist(self):
                return [1, 2, 3]

        assert _json_default(FakeArray()) == [1, 2, 3]

    def test_numpy_item(self):
        class FakeScalar:
            def item(self):
                return 42

        assert _json_default(FakeScalar()) == 42

    def test_unserializable_raises(self):
        class Unknown:
            pass

        with pytest.raises(TypeError, match="not JSON serializable"):
            _json_default(Unknown())
