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

import json
from unittest.mock import Mock, patch

import redis

from wy_qcos.transpiler.common.wirecut.result_cache import (
    SUBCIRCUIT_RESULT_CACHE_TTL,
    SubcircuitResultCache,
)


def _job_info(job_id="job-1", shots=1024):
    return {
        "data": {
            "job_id": job_id,
            "backend": "dummy",
            "driver_options": {"seed": 7},
            "shots": shots,
        },
        "device": {"name": "dummy", "configs": {}},
        "driver": {"module_name": "driver", "class_name": "Driver"},
        "transpiler": {
            "module_name": "transpiler",
            "class_name": "Transpiler",
        },
        "global": {
            "configs": {
                "REDIS": {
                    "REDIS_URL": "redis://127.0.0.1:6379/0",
                }
            }
        },
    }


class TestSubcircuitResultCache:
    def test_cache_key_is_shared_between_jobs(self):
        first_job = _job_info(job_id="job-1")
        second_job = _job_info(job_id="job-2")

        first_key = SubcircuitResultCache.cache_key("OPENQASM;", first_job)
        second_key = SubcircuitResultCache.cache_key("OPENQASM;", second_job)

        assert first_key == second_key
        assert first_key != SubcircuitResultCache.cache_key(
            "OPENQASM;", _job_info(shots=2048)
        )

    @patch("wy_qcos.transpiler.common.wirecut.result_cache.redis.Redis")
    def test_from_job_info_uses_job_redis_config(self, mock_redis):
        cache = SubcircuitResultCache.from_job_info(_job_info())

        assert cache.redis_client == mock_redis.from_url.return_value
        mock_redis.from_url.assert_called_once_with(
            "redis://127.0.0.1:6379/0",
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            protocol=2,
        )

    def test_set_uses_twelve_hour_expiry_and_get_restores_result(self):
        redis_client = Mock()
        cache = SubcircuitResultCache(redis_client)
        result = {"00": 700, "11": 324}

        cache.set("OPENQASM;", _job_info(), result)

        cache_key, payload = redis_client.set.call_args.args
        assert cache_key == cache.cache_key("OPENQASM;", _job_info())
        assert json.loads(payload)["result"] == result
        assert redis_client.set.call_args.kwargs["ex"] == (
            SUBCIRCUIT_RESULT_CACHE_TTL
        )

        redis_client.get.return_value = payload
        assert cache.get("OPENQASM;", _job_info()) == result

    def test_redis_failure_is_treated_as_cache_miss(self):
        redis_client = Mock()
        redis_client.get.side_effect = redis.RedisError("unavailable")
        cache = SubcircuitResultCache(redis_client)

        assert cache.get("OPENQASM;", _job_info()) is None
        assert cache.redis_client is None

    def test_invalid_cached_result_is_treated_as_cache_miss(self):
        redis_client = Mock()
        redis_client.get.return_value = json.dumps({
            "version": 1,
            "result": [0.5, 0.5],
        })
        cache = SubcircuitResultCache(redis_client)

        assert cache.get("OPENQASM;", _job_info()) is None

    def test_missing_redis_config_disables_cache(self):
        cache = SubcircuitResultCache.from_job_info({"data": {}})

        assert cache.redis_client is None
