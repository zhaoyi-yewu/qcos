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

import logging

from fastapi import Depends

from wy_qcos.api import schemas
from wy_qcos.api.posiq.routes_jsonrpc import errors as jsonrpc_errors
from wy_qcos.api.posiq.routes_jsonrpc.routes import metrics_api_v1
from wy_qcos.common.constant import Constant
from wy_qcos.metrics import metrics_collector

from .dependencies.authentication import auth


logger = logging.getLogger(__name__)
module_name = "METRICS"


@metrics_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def get_system_health(
    body: schemas.GetSystemHealthRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetSystemHealthResponse:
    """Get system health status.

    Args:
        body: Get system health request
        auth_data: Authentication data

    Returns:
        System health response
    """
    func_name = "get_system_health"
    logger.info(f"Call {func_name}")

    try:
        system_stats = metrics_collector.system_health_metrics.get_values()
        component_stats = {
            Constant.COMPONENT_NAME_FASTAPI: Constant.COMPONENT_STATUS_ONLINE
            if system_stats.fastapi_healthy
            else Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_REDIS: Constant.COMPONENT_STATUS_ONLINE
            if system_stats.redis_healthy
            else Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_PREFECT: Constant.COMPONENT_STATUS_ONLINE
            if system_stats.prefect_healthy
            else Constant.COMPONENT_STATUS_OFFLINE,
            Constant.COMPONENT_NAME_WORKER: Constant.COMPONENT_STATUS_ONLINE
            if system_stats.worker_healthy
            else Constant.COMPONENT_STATUS_OFFLINE,
        }
        _response_info = {
            Constant.SYSTEM_HEALTHY: system_stats.overall_healthy,
            Constant.HEARTBEAT_TIMESTAMP: system_stats.heartbeat_timestamp,
            Constant.COMPONENT_STATUS: component_stats,
        }
        response_info = schemas.GetSystemHealthResponse.model_validate(
            _response_info
        )
        return response_info
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        return jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )


@metrics_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def get_api_stats(
    body: schemas.GetApiStatsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetApiStatsResponse:
    """Get API access statistics.

    Args:
        body: Get API statistics request
        auth_data: Authentication data

    Returns:
        API statistics response
    """
    func_name = "get_api_stats"
    logger.info(f"Call {func_name}")

    try:
        api_stats = metrics_collector.api_metrics.get_api_stats()

        _response_info = {
            Constant.API_TOTAL_REQUESTS: api_stats[
                Constant.API_TOTAL_REQUESTS
            ],
            Constant.API_LAST_HOUR_REQUESTS: api_stats[
                Constant.API_LAST_HOUR_REQUESTS
            ],
            Constant.API_LAST_DAY_REQUESTS: api_stats[
                Constant.API_LAST_DAY_REQUESTS
            ],
        }
        response_info = schemas.GetApiStatsResponse.model_validate(
            _response_info
        )
        return response_info
    except Exception as e:
        logger.error(f"Failed to get API stats: {e}")
        return jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )


@metrics_api_v1.method(
    tags=[module_name.lower()],
    openapi_extra={"allowed_roles": [Constant.ROLE_ADMIN]},
)
def get_job_stats(
    body: schemas.GetJobStatsRequest | None = None,
    auth_data: dict | None = Depends(auth),
) -> schemas.GetJobStatsResponse:
    """Get job statistics.

    Args:
        body: Get job statistics request
        auth_data: Authentication data

    Returns:
        Job statistics response
    """
    func_name = "get_job_stats"
    logger.info(f"Call {func_name}")

    try:
        job_metrics_data = metrics_collector.job_metrics.get_values()

        _response_info = {
            Constant.JOB_METRICS_FIELD_TOTAL: job_metrics_data.total,
            Constant.JOB_METRICS_FIELD_COMPLETED: job_metrics_data.completed,
            Constant.JOB_METRICS_FIELD_FAILED: job_metrics_data.failed,
            Constant.JOB_METRICS_FIELD_RUNNING: job_metrics_data.running,
            Constant.JOB_METRICS_FIELD_QUEUED: job_metrics_data.queued,
            Constant.JOB_METRICS_FIELD_CANCELLING: job_metrics_data.cancelling,
            Constant.JOB_METRICS_FIELD_CANCELLED: job_metrics_data.cancelled,
            Constant.JOB_METRICS_FIELD_DELETING: job_metrics_data.deleting,
            Constant.JOB_METRICS_FIELD_DELETED: job_metrics_data.deleted,
            Constant.JOB_METRICS_FIELD_UNKNOWN: job_metrics_data.unknown,
            Constant.JOB_METRICS_FIELD_SUBMITTED_JOB_RATE_MIN: (
                job_metrics_data.submitted_job_rate_min
            ),
            Constant.JOB_METRICS_FIELD_COMPLETED_JOB_RATE_MIN: (
                job_metrics_data.completed_job_rate_min
            ),
        }
        response_info = schemas.GetJobStatsResponse.model_validate(
            _response_info
        )
        return response_info
    except Exception as e:
        logger.error(f"Failed to get job stats: {e}")
        return jsonrpc_errors.handle_error_internal_server(
            module_name, func_name, (False, str(e))
        )
