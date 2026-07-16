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

import hashlib
import json

import redis
from loguru import logger

from wy_qcos.common.constant import Constant


SUBCIRCUIT_RESULT_CACHE_TTL = 12 * 60 * 60
SUBCIRCUIT_RESULT_CACHE_PREFIX = "qcos:wirecut:subcircuit-result:v1"
SUBCIRCUIT_RESULT_CACHE_VERSION = 1


class SubcircuitResultCache:
    """Redis-backed cache shared by wire-cutting jobs."""

    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    @classmethod
    def from_job_info(cls, job_info):
        """Create a cache using the Redis configuration carried by a job."""
        redis_config = (
            job_info.get("global", {}).get("configs", {}).get("REDIS", {})
        )
        host = redis_config.get("REDIS_SERVER_IP")
        port = redis_config.get("REDIS_SERVER_PORT")
        if host is None or port is None:
            logger.debug(
                "Wire-cut subcircuit cache is disabled: Redis config missing"
            )
            return cls()

        return cls(
            redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=1,
                socket_timeout=1,
            )
        )

    @staticmethod
    def execution_context(job_info):
        """Return fields that can affect a subcircuit execution result."""
        job_data = job_info.get("data", {})
        return {
            "backend": job_data.get("backend"),
            "device": job_info.get("device"),
            "driver": job_info.get("driver"),
            "driver_options": job_data.get("driver_options"),
            "dry_run": job_data.get("dry_run", False),
            "qec_options": job_data.get("qec_options"),
            "shots": job_data.get("shots", Constant.DEFAULT_SHOTS),
            "transpiler": job_info.get("transpiler"),
            "transpiler_options": job_data.get("transpiler_options"),
        }

    @classmethod
    def cache_key(cls, subcircuit, job_info):
        """Build a stable, non-sensitive cache key."""
        key_data = {
            "subcircuit": subcircuit,
            "execution_context": cls.execution_context(job_info),
        }
        serialized = json.dumps(
            key_data,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        return f"{SUBCIRCUIT_RESULT_CACHE_PREFIX}:{digest}"

    def get(self, subcircuit, job_info):
        """Get a cached raw execution result, or ``None`` on a miss."""
        if self.redis_client is None:
            return None

        cache_key = self.cache_key(subcircuit, job_info)
        try:
            cached_value = self.redis_client.get(cache_key)
        except redis.RedisError as exc:
            logger.warning(f"Failed to read subcircuit result cache: {exc}")
            self.redis_client = None
            return None

        if cached_value is None:
            return None
        try:
            payload = json.loads(cached_value)
            if payload.get("version") != SUBCIRCUIT_RESULT_CACHE_VERSION:
                return None
            result = payload.get("result")
            if not isinstance(result, dict):
                logger.warning("Invalid subcircuit result cache entry: result")
                return None
            return result
        except (TypeError, ValueError, AttributeError) as exc:
            logger.warning(f"Invalid subcircuit result cache entry: {exc}")
            return None

    def set(self, subcircuit, job_info, result):
        """Cache a successful raw execution result for twelve hours."""
        if self.redis_client is None or result is None:
            return

        cache_key = self.cache_key(subcircuit, job_info)
        try:
            payload = json.dumps(
                {
                    "version": SUBCIRCUIT_RESULT_CACHE_VERSION,
                    "result": result,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                default=_json_default,
            )
        except (TypeError, ValueError) as exc:
            logger.warning(f"Failed to serialize subcircuit result: {exc}")
            return

        try:
            self.redis_client.set(
                cache_key,
                payload,
                ex=SUBCIRCUIT_RESULT_CACHE_TTL,
            )
        except redis.RedisError as exc:
            logger.warning(f"Failed to write subcircuit result cache: {exc}")
            self.redis_client = None


def _json_default(value):
    """Convert NumPy-like result values to JSON-compatible values."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    value_type = type(value).__name__
    raise TypeError(f"Object of type {value_type} is not JSON serializable")
