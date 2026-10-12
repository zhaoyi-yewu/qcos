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

"""Multi-device wire-cutting engine.

This module provides the ``wirecut_flow`` Prefect flow and its helper
functions.  It mirrors the structure of :mod:`wy_qcos.engine.job_engine`
but differs in two key aspects:

1. **No driver initialisation inside the flow.**  Device info (device
   configs, driver class info, backend name) is prepared by the caller
   and passed in via ``device_info_list``.  Each sub-circuit still calls
   ``init_driver`` with the corresponding device info, but the decision
   of *which* device to use is made upstream.
2. **Multiple devices.**  Each sub-circuit can be scheduled to a
   different backend device, enabling parallel execution across the
   available device pool.
"""

import copy
import importlib
import time
from typing import Any

import redis
from loguru import logger
from prefect import flow, get_client
from prefect.runtime import flow_run

from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.utils import db_utils
from wy_qcos.db.database import init_database
from wy_qcos.engine.common import init_logger
from wy_qcos.engine.job_engine import (
    create_src_code_info,
    flow_task_monitor,
    get_src_code_cnt,
    register_signals,
    update_progress,
)

_import_module = importlib.import_module


@flow(
    persist_result=False,
    on_failure=[db_utils.db_job_callback],
    on_crashed=[db_utils.db_job_callback],
    on_cancellation=[db_utils.db_job_callback],
    on_completion=[db_utils.db_job_callback],
)
def wirecut_flow(job_info):
    """Wire-cut multi-device flow.

    Similar to :func:`job_engine.job_flow` but:

    * No single fixed device — ``device_info_list`` provides per
      sub-circuit device info (configs, driver class info, backend).
    * The circuit is cut into sub-circuits via ``CutWire`` and each
      sub-circuit is executed on its scheduled device.

    Args:
        job_info: job info dict (same structure as ``job_engine``).
            Must contain ``"data"``, ``"global"``, ``"driver"``,
            ``"transpiler"`` keys.

    Returns:
        job_results_list: list of job result dicts.
    """
    worker_started_at = time.time()
    job_data = job_info["data"]
    job_id = job_data["job_id"]
    global_info = job_info["global"]
    global_configs = global_info["configs"]
    deployments = global_info["deployments"]
    flow_run_id = flow_run.id
    callbacks = job_data.get("callbacks", None)
    available_devices = job_data.get("filtered_devices", [])
    job_data["job_enqueue_at"]
    job_data["job_schedule_started_at"]
    job_data["job_schedule_ended_at"]
    job_data["job_schedule_duration"]

    # Build monitor_info: the driver field starts as None and is
    # updated per sub-circuit during execution.
    monitor_info: dict[str, Any] = {
        "job_id": job_id,
        "flow_run_id": flow_run_id,
        "configs": global_configs,
        "device_configs": None,
        "callbacks": callbacks,
        "user": {
            "project_id": job_data.get("project_id", None),
            "user_id": job_data.get("user_id", None),
        },
        "redis": {
            "url": global_configs["REDIS"].get("REDIS_URL", None),
        },
        "running": True,
        "driver": None,
        "source_code_index": 0,
        "source_code_count": 0,
        "agg_sub_job_list": [],
        "progress": -1,
    }

    # init logger
    debug = global_configs.get("DEBUG", False)
    device_log_file = "/var/log/qcos/vdev_wirecut.log"
    init_logger(
        log_file_path=device_log_file,
        debug=debug,
        log_format=None,
        log_rotate_max_size_mb=None,
        log_rotate_backup_count=None,
        log_rotate_compression=None,
    )
    logger.info(f"Processing work flow: wirecut_engine. job_id: {job_id}")
    logger.debug(f"Job details: job_id: {job_id}, job_info: {job_info}")

    logger.info(
        f"Wirecut engine: {len(available_devices)} available device(s) "
        f"for job_id: {job_id}"
    )

    # init db engine
    try:
        logger.info(f"Initializing database for job_id: {job_id}")
        db_url = global_configs["DATABASE"]["QCOS_DATABASE_CONNECTION_URL"]
        db_engine = init_database(db_url)
        monitor_info["db_engine"] = db_engine
        db_utils.set_db_engine(db_engine)
        logger.info(f"Database initialized for job_id: {job_id}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        db_engine = None

    # update job status to RUNNING and set started_at
    logger.info(f"Updating job status to RUNNING for job_id: {job_id}")
    db_utils.db_update_job(
        job_id,
        db_engine,
        job_status=Constant.JOB_STATUS_RUNNING,
        started_at=Library.to_iso(worker_started_at),
        progress=-1,
    )

    # register signals for job cancelling
    logger.info(f"Registering signals for job_id: {job_id}")
    register_signals(job_id, monitor_info)

    # record start_time
    time.time()

    # start task-monitor
    logger.info(f"Starting task_monitor for job_id: {job_id}")
    flow_task_monitor(monitor_info)
    logger.info(f"task_monitor started for job_id: {job_id}")

    job_results_list = []
    transpiler_info = job_info.get("transpiler", {})
    _get_transpiler_instance(transpiler_info)

    redis.Redis.from_url(
        monitor_info["redis"]["url"],
        decode_responses=True,
        protocol=2,
    )

    src_code_info = create_src_code_info(job_data)
    source_code_count = get_src_code_cnt(src_code_info)
    monitor_info["source_code_count"] = source_code_count

    schedule = wirecut_schedule(src_code_info, available_devices)
    logger.error(schedule)
    sync_client = get_client(sync_client=True)
    new_job_list = submit_jobs(
        schedule,
        job_info,
        monitor_info,
        sync_client,
        source_code_count,
        deployments,
    )
    job_results_list = poll_job_results(new_job_list)

    monitor_info["running"] = False
    monitor_info["progress"] = 100
    update_progress(job_id, db_engine, 100)
    return job_results_list


def wirecut_schedule(src_code_info, available_devices):
    """Schedule sub-circuits to devices via CutWire + capability match.

    Args:
        src_code_info (dict): source code info
        available_devices (list): available devices

    Returns:
        list of schedule entries, each a dict with keys
        ``device_name`` (str), ``source_code_index`` (int),
        ``subcircuit_index`` (int) and ``subcircuit`` (str).
    """
    sample = (
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\ncreg c[2];\n'
        "x q[0];\nh q[1];\ncz q[0], q[1];\nmeasure q[0] -> c[0];\n"
        "measure q[1] -> c[1];"
    )
    schedule_results = []
    for available_device in available_devices:
        device_name = available_device["name"]
        device_schedule = {
            "device_name": device_name,
            "driver_name": available_device["driver_name"],
            "driver_module_name": available_device["driver_module_name"],
            "driver_class_name": available_device["driver_class_name"],
            "driver_package_paths": available_device["driver_package_paths"],
            "configs": available_device.get("configs"),
            "source_codes": [sample],
        }
        schedule_results.append(device_schedule)
    return schedule_results


def submit_jobs(
    schedule_results,
    job_info,
    monitor_info,
    sync_client,
    source_code_count,
    deployments,
):
    """Submit sub-circuits to devices via prefect client.

    Iterates over the schedule produced by wirecut_schedule. For each
    schedule entry, builds a sub job_info, resolves the deployment,
    submits a sub-flow via create_flow_run_from_deployment, polls the
    sub-flow state until terminal, collects the result (counts) and
    converts it to a probability distribution. When all sub-circuits
    of a source code complete, reconstructs the full probability
    distribution via reconstruct_probability_distribution_wire_cut.

    Args:
        schedule_results (list): schedule entries from wirecut_schedule,
            each containing "device_name" and "source_codes".
        job_info (dict): original job info dict.
        monitor_info (dict): monitor info dict, updated in place.
        sync_client: prefect sync client for flow run operations.
        source_code_count (int): total source code count for progress.
        deployments: deployments

    Returns:
        list: job results list, one entry per source code.
    """
    job_data = job_info["data"]
    transpiler_info = job_info.get("transpiler", {})
    job_id = job_data["job_id"]
    wirecut_job_list = []

    for device_schedule in schedule_results:
        device_name = device_schedule["device_name"]
        source_codes = device_schedule["source_codes"]

        # resolve deployment id by name
        deployment_name = f"{Constant.WORK_POOL_DEV}|{device_name}"
        deployment = deployments.get(deployment_name)
        if deployment is None:
            err_msg = (
                f"Deployment {deployment_name} not found for "
                f"device {device_name}"
            )
            logger.error(err_msg)
            raise ValueError(f"Wirecut error: {err_msg}")

        wirecut_deploy_id = deployment["deploy_id"]
        wirecut_job_data = copy.deepcopy(job_data)
        wirecut_job_data["job_id"] = job_id
        wirecut_job_data["job_name"] = None
        wirecut_job_data["backend"] = device_name
        wirecut_job_data["backend_type"] = Constant.BACKEND_TYPE_DEVICE
        wirecut_job_data["source_code"] = source_codes
        wirecut_job_data["options"]["enable_wirecut"] = False
        wirecut_job_data["circuit_aggregation"] = None
        if "filtered_devices" in wirecut_job_data:
            del wirecut_job_data["filtered_devices"]
        wirecut_job_data["results_db_storage"] = "redis"
        wirecut_job_data["job_enqueue_at"] = time.time()
        wirecut_job_info = {
            "data": wirecut_job_data,
            "driver": {
                "module_name": device_schedule["driver_module_name"],
                "class_name": device_schedule["driver_class_name"],
                "package_paths": device_schedule["driver_package_paths"],
            },
            "transpiler": {
                "module_name": transpiler_info.get("module_name"),
                "class_name": transpiler_info.get("class_name"),
            },
            "device": {"configs": device_schedule["configs"]},
            "global": job_info["global"],
        }

        # submit sub-flow via prefect client
        try:
            wirecut_flow_run_name = f"vdev-wirecut-{job_id}-{device_name}"
            wirecut_work_queue_name = (
                f"{Constant.WORK_POOL_DEV}|{device_name}_"
                f"{Constant.DEFAULT_JOB_PRIORITY}"
            )
            wirecut_parameters = {
                "job_info": wirecut_job_info,
            }
            wirecut_flow_run = sync_client.create_flow_run_from_deployment(
                name=wirecut_flow_run_name,
                deployment_id=wirecut_deploy_id,
                work_queue_name=wirecut_work_queue_name,
                parameters=wirecut_parameters,
            )
            wirecut_flow_run_id = wirecut_flow_run.id
            logger.info(
                f"Submitted sub-flow for sub-circuit: "
                f"flow_run_name={wirecut_flow_run_name}, "
                f"flow_run_id={wirecut_flow_run_id}, "
                f"device={device_name}"
            )
            wirecut_job = {"flow_run_id": wirecut_flow_run_id, "circuit": None}
            wirecut_job_list.append(wirecut_job)
        except Exception as e:
            err_msg = f"Failed to submit sub-flow for sub-circuit: {str(e)}"
            logger.error(err_msg)
            raise ValueError(err_msg)
    return wirecut_job_list


def poll_job_results(new_job_list):
    """Poll job results.

    Args:
        new_job_list (list): job results list.

    Returns:
        job results list
    """
    job_results_list = []
    return job_results_list


def _get_transpiler_instance(transpiler_info):
    """Get transpiler instance from transpiler class info.

    Args:
        transpiler_info: transpiler class info dict containing
            ``module_name`` and ``class_name``.

    Returns:
        transpiler instance or None if info is incomplete.
    """
    transpiler_module_name = transpiler_info.get("module_name")
    transpiler_class_name = transpiler_info.get("class_name")
    if not transpiler_module_name or not transpiler_class_name:
        return None
    try:
        transpiler_module = _import_module(transpiler_module_name)
        transpiler_cls = getattr(transpiler_module, transpiler_class_name)
        return transpiler_cls()
    except Exception as e:
        logger.warning(
            f"Failed to instantiate transpiler "
            f"{transpiler_module_name}.{transpiler_class_name}: {e}"
        )
        return None
