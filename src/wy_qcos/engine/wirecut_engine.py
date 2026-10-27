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
import json
import time
from typing import Any

import numpy as np
import redis
from loguru import logger
from prefect import flow, get_client, task
from prefect.runtime import flow_run

from wy_qcos.common import errors
from wy_qcos.common.constant import Constant
from wy_qcos.common.library import Library
from wy_qcos.db.utils import db_utils
from wy_qcos.db.utils.db_utils import get_redis_client
from wy_qcos.db.database import init_database
from wy_qcos.engine.common import init_logger
from wy_qcos.engine.job_engine import (
    create_src_code_info,
    format_error_results,
    get_src_code_cnt,
    register_signals,
    update_progress,
)
from wy_qcos.engine.qubo import (
    SubQUBOMultiSolution,
    check_matrix,
    check_qubo_matrix_bit_width,
    get_spins_num,
    ising_matrix_to_qubo_matrix,
    precision_reduction,
    qubo_matrix_to_ising_matrix,
    scale_to_integer_matrix,
)

# TTL (seconds) for wirecut sub-job redis keys. Set to 7 days so
# that sub-job result keys are automatically cleaned up by redis
# after expiry, avoiding manual deletion and key accumulation.
WIRECUT_SUBJOB_REDIS_TTL = 7 * 24 * 60 * 60

# How long (seconds) poll_job_results blocks on a single pub/sub
# get_message call before giving up and re-reading the redis keys
# of all still-pending sub-jobs. This bounds the delay of the
# snapshot fallback so a lost pub/sub notification (SET succeeds
# but PUBLISH is lost) can never hang the parent flow forever.
POLL_MESSAGE_TIMEOUT = 5.0

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

    # Build monitor_info: the driver field starts as None and is
    # updated per sub-circuit during execution. ``sub_job_progress``
    # holds the latest progress value reported by each sub-job via
    # pub/sub so task_monitor can compute an aggregated progress.
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
        "db_config": job_data.get("db_config", {}),
        "running": True,
        "driver": None,
        "source_code_index": 0,
        "source_code_count": 0,
        "agg_sub_job_list": [],
        "progress": -1,
        "sub_job_progress": {},
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
        f"Wirecut engine: {len(available_devices)} available "
        f"device(s) for job_id: {job_id}"
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

    # start task-monitor
    logger.info(f"Starting task_monitor for job_id: {job_id}")
    flow_task_monitor(monitor_info)
    logger.info(f"task_monitor started for job_id: {job_id}")

    transpiler_info = job_info.get("transpiler", {})
    _get_transpiler_instance(transpiler_info)

    redis_instance = redis.Redis.from_url(
        monitor_info["redis"]["url"],
        decode_responses=True,
        protocol=2,
    )

    src_code_info = create_src_code_info(job_data)
    source_code_count = get_src_code_cnt(src_code_info)
    monitor_info["source_code_count"] = source_code_count

    code_type = job_data.get("code_type")
    sync_client = get_client(sync_client=True)

    if code_type == Constant.CODE_TYPE_QUBO:
        logger.info(
            f"QUBO job detected, running subqubo_schedule for job_id: {job_id}"
        )
        job_results_list = subqubo_schedule(
            job_info,
            src_code_info,
            available_devices,
            monitor_info,
            sync_client,
            redis_instance,
            deployments,
            source_code_count,
        )
    else:
        schedule_results = wirecut_schedule(src_code_info, available_devices)
        logger.debug(f"Wirecut schedule_results: {schedule_results}")
        new_job_list = submit_jobs(
            schedule_results,
            job_info,
            monitor_info,
            sync_client,
            source_code_count,
            deployments,
        )
        job_results_list = poll_job_results(
            new_job_list,
            job_id=job_id,
            redis_instance=redis_instance,
            monitor_info=monitor_info,
        )

    monitor_info["running"] = False
    monitor_info["progress"] = 100
    _db_config = monitor_info.get("db_config", {})
    _results_db_storage = _db_config.get(
        "results_db_storage",
        Constant.RESULTS_DB_STORAGE_DEFAULT,
    )
    update_progress(
        job_id,
        db_engine,
        100,
        results_db_storage=_results_db_storage,
        flow_run_id=flow_run_id,
        ttl=_db_config.get("ttl"),
    )
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
    # TODO: implement jobs merge
    sample = (
        'OPENQASM 2.0;\ninclude "qelib1.inc";\nqreg q[2];\n'
        "creg c[2];\n"
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


def _get_device_max_qubits(device):
    """Get max_qubits from a serialized device dict.

    The serialized device (DeviceState.to_dict()) may carry qubit
    counts under different keys depending on the serialization
    path; this helper tries the common locations.

    Args:
        device: serialized device dict from available_devices.

    Returns:
        int max_qubits, or 0 if not found.
    """
    max_qubits = device.get("max_qubits")
    if max_qubits is None:
        configs = device.get("configs") or {}
        max_qubits = configs.get("max_qubits")
    if max_qubits is None:
        max_qubits = device.get("available_qubits", 0)
    return int(max_qubits) if max_qubits else 0


def _extract_subqubo_solution(record):
    """Extract the solutionVector from a sub-job redis record.

    The sub-flow (job_flow) stores its return value via
    db_job_callback into redis as ``record["results"]``, which is a
    list of per-source-code result dicts. Each result dict carries
    a ``results`` key holding the driver output, whose
    ``out_data[0].solutionVector`` is the QUBO solution vector.
    This helper defensively traverses the nested structure so it
    works regardless of minor serialization differences.

    Args:
        record: redis job record dict from poll_job_results.

    Returns:
        list: solution vector (e.g. [0, 1, 0, 1]), or empty list
        if not found.
    """
    if not record:
        return []

    results = record.get("results")

    if isinstance(results, list):
        for result in results:
            if not isinstance(result, dict):
                continue
            inner = result.get("results")
            if isinstance(inner, dict):
                out_data = inner.get("out_data", [])
                if out_data and isinstance(out_data[0], dict):
                    solution = out_data[0].get("solutionVector", [])
                    if solution:
                        return list(solution)
            if isinstance(result.get("out_data"), list) and result["out_data"]:
                item = result["out_data"][0]
                if isinstance(item, dict) and item.get("solutionVector"):
                    return list(item["solutionVector"])

    if isinstance(results, dict):
        out_data = results.get("out_data", [])
        if out_data and isinstance(out_data[0], dict):
            solution = out_data[0].get("solutionVector", [])
            if solution:
                return list(solution)

    return []


def _build_subqubo_schedule_entries(subqubo_tasks, available_devices):
    """Build schedule entries for one subqubo iteration round.

    Distributes the N_E sub-QUBO matrices across available devices
    in round-robin order. Each entry has the shape expected by
    :func:`submit_jobs`.

    Args:
        subqubo_tasks: list of dicts, each containing the sub-QUBO
            matrix under ``"matrix"``.
        available_devices: list of serialized device dicts.

    Returns:
        list of schedule entries for submit_jobs.
    """
    device_count = len(available_devices)
    schedule_results = []
    for i, sub_task in enumerate(subqubo_tasks):
        device = available_devices[i % device_count]
        schedule_results.append({
            "device_name": device["name"],
            "driver_name": device["driver_name"],
            "driver_module_name": device["driver_module_name"],
            "driver_class_name": device["driver_class_name"],
            "driver_package_paths": device["driver_package_paths"],
            "configs": device.get("configs"),
            "source_codes": [sub_task["matrix"]],
        })
    return schedule_results


def subqubo_schedule(
    job_info,
    src_code_info,
    available_devices,
    monitor_info,
    sync_client,
    redis_instance,
    deployments,
    source_code_count,
):
    """Schedule sub-QUBO tasks across multiple devices with iteration.

    Unlike :func:`wirecut_schedule` (one-shot dispatch), sub-QUBO
    solving is an iterative optimisation: each round decomposes the
    original QUBO into N_E sub-QUBOs, dispatches them in parallel
    across the available device pool, collects results, merges them
    back into the solution pool, and repeats until the energy
    converges.

    This function is self-contained: it performs the QUBO
    preprocessing (matrix validation, precision reduction, total
    spin count) and the full iteration loop internally, so
    :func:`wirecut_flow` only needs to branch on ``code_type``.
    The baseline ``max_qubits`` is the minimum across all available
    devices, ensuring every sub-QUBO fits on any device.

    Args:
        job_info: original job info dict.
        src_code_info: SourceCodeInfo built by create_src_code_info.
        available_devices: list of serialized device dicts.
        monitor_info: monitor info dict (updated in place for
            progress aggregation).
        sync_client: prefect sync client for sub-flow submission.
        redis_instance: redis client for sub-job result polling.
        deployments: deployments dict for deployment id resolution.
        source_code_count: total source code count (for logging).

    Returns:
        list: job results list with the final solution pool, shaped
        like a single poll_job_results record so the caller can
        treat qubo and circuit branches uniformly.
    """
    job_data = job_info["data"]
    job_id = job_data["job_id"]

    # extract original QUBO matrix from src_code_info
    src_code_map = src_code_info.src_code_list[0]
    src_code_key = next(iter(src_code_map))
    qubo_matrix = src_code_map[src_code_key]
    logger.info(
        f"subqubo_schedule: job_id={job_id}, matrix size="
        f"{len(qubo_matrix)}x"
        f"{len(qubo_matrix[0]) if qubo_matrix else 0}, "
        f"devices={len(available_devices)}"
    )

    # baseline max_qubits: minimum across all available devices
    max_qubits = min(
        (_get_device_max_qubits(d) for d in available_devices),
        default=0,
    )
    if max_qubits <= 0:
        err_msg = "No available device with valid max_qubits for subqubo"
        logger.error(err_msg)
        raise ValueError(f"Subqubo error: {err_msg}")

    # preprocessing (mirrors run_qubo_code)
    success, err_msg = check_matrix(qubo_matrix)
    if not success and err_msg:
        raise ValueError(f"Subqubo error: {err_msg}")

    success, err_msg = check_qubo_matrix_bit_width(
        np.array(qubo_matrix), Constant.MAX_QUBO_BIT_WIDTH
    )
    if not success and err_msg:
        raise ValueError(f"Subqubo error: {err_msg}")

    ising_matrix = qubo_matrix_to_ising_matrix(np.array(qubo_matrix))
    scaled_ising_matrix = scale_to_integer_matrix(ising_matrix)
    max_precision_value = 2 ** (Constant.MAX_QUBO_BIT_WIDTH - 1) - 1
    _, _, total_spins_num = get_spins_num(
        scaled_ising_matrix, max_precision_value
    )

    # if the problem already fits on a single device, skip iteration
    # and dispatch once (no sub-QUBO decomposition needed)
    if total_spins_num <= max_qubits + 1:
        logger.info(
            f"subqubo_schedule: total_spins_num={total_spins_num} "
            f"<= max_qubits+1={max_qubits + 1}, single dispatch"
        )
        schedule_results = _build_subqubo_schedule_entries(
            [{"matrix": qubo_matrix}], available_devices
        )
        new_job_list = submit_jobs(
            schedule_results,
            job_info,
            monitor_info,
            sync_client,
            source_code_count,
            deployments,
        )
        return poll_job_results(
            new_job_list,
            job_id=job_id,
            redis_instance=redis_instance,
            monitor_info=monitor_info,
        )

    # iteration loop (mirrors run_subqubo_code)
    subqubo_size = int(
        np.floor(max_qubits * len(qubo_matrix) / total_spins_num)
    )
    if subqubo_size <= max_qubits / 4:
        err_msg = (
            f"SubQUBO size {subqubo_size} below threshold "
            f"{int(max_qubits / 4)}."
        )
        raise ValueError(f"Subqubo error: {err_msg}")

    # use a local SubQUBO instance instead of the global singleton
    # to avoid thread-safety issues when multiple wirecut_flow
    # instances run concurrently in different prefect workers
    local_subqubo = SubQUBOMultiSolution(
        subqubo_size=subqubo_size,
        qubo_matrix=np.array(qubo_matrix),
    )
    solution_pool = local_subqubo.init_instance_pool()
    best_solution, _ = local_subqubo.find_best_solution(solution_pool)
    converged_num = 0
    cycles_num = 0
    max_iterations = 100

    while converged_num <= local_subqubo.get_max_converged_num():
        cycles_num += 1
        if cycles_num > max_iterations:
            logger.warning(
                f"subqubo reached max iterations "
                f"({max_iterations}), returning best solution "
                f"so far, job_id={job_id}"
            )
            break
        logger.info(
            f"subqubo cycle {cycles_num}, converged={converged_num}, "
            f"job_id={job_id}"
        )
        solution_pool = local_subqubo.optimize_solution_pool(solution_pool)
        n_e_pools = local_subqubo.create_sub_solution_pools(solution_pool)

        # build N_E sub-QUBO tasks for this round
        subqubo_tasks = []
        for i in range(local_subqubo.N_E):
            subqubo_matrix, tmp_solution, extracted_index = (
                local_subqubo.construct_subqubo(n_e_pools[i])
            )
            need_precision_reduction = False
            last_idx = []
            success, err_msg = check_qubo_matrix_bit_width(
                np.array(subqubo_matrix), Constant.MAX_QUBO_BIT_WIDTH
            )
            if not success:
                if err_msg:
                    raise ValueError(f"Subqubo error: {err_msg}")
                # err_msg is empty: bit width exceeded but matrix
                # structure is valid — enter precision reduction,
                # not an error
                need_precision_reduction = True
                subqubo_ising_matrix = qubo_matrix_to_ising_matrix(
                    np.array(subqubo_matrix)
                )
                subqubo_precision_ising_matrix, last_idx, _ = (
                    precision_reduction(
                        subqubo_ising_matrix, Constant.MAX_QUBO_BIT_WIDTH
                    )
                )
                subqubo_matrix = ising_matrix_to_qubo_matrix(
                    subqubo_precision_ising_matrix
                )
                subqubo_matrix = subqubo_matrix.tolist()
            # ensure native Python types for prefect JSON
            # serialization (construct_subqubo may return numpy
            # int64 elements that pydantic cannot serialize)
            subqubo_matrix = np.array(subqubo_matrix).tolist()
            subqubo_tasks.append({
                "matrix": subqubo_matrix,
                "tmp_solution": tmp_solution,
                "extracted_index": extracted_index,
                "need_precision_reduction": need_precision_reduction,
                "last_idx": last_idx,
            })

        # dispatch all N_E sub-QUBOs in parallel across devices
        # use a per-cycle job_id suffix so each round's sub-tasks
        # have distinct names (platform rejects duplicate task_name)
        round_job_id = f"{job_id}_c{cycles_num}"
        round_job_info = copy.deepcopy(job_info)
        round_job_info["data"]["job_id"] = round_job_id
        schedule_results = _build_subqubo_schedule_entries(
            subqubo_tasks, available_devices
        )
        new_job_list = submit_jobs(
            schedule_results,
            round_job_info,
            monitor_info,
            sync_client,
            source_code_count,
            deployments,
        )
        sub_records = poll_job_results(
            new_job_list,
            job_id=round_job_id,
            redis_instance=redis_instance,
            monitor_info=monitor_info,
        )

        # merge results back into new solutions
        new_solutions = []
        for i, sub_task in enumerate(subqubo_tasks):
            record = sub_records[i] if i < len(sub_records) else {}
            subqubo_solution = _extract_subqubo_solution(record)
            if not subqubo_solution:
                continue
            if subqubo_solution and sub_task["need_precision_reduction"]:
                subqubo_solution = list(
                    np.array(subqubo_solution)[sub_task["last_idx"][:-1]]
                )
            solution = local_subqubo.merge_solution(
                sub_task["tmp_solution"],
                subqubo_solution,
                sub_task["extracted_index"],
            )
            new_solutions.append(solution)

        x_best, solution_pool = local_subqubo.update_solution_pool(
            solution_pool, new_solutions
        )
        if best_solution.energy > x_best.energy:
            best_solution.solution = x_best.solution.copy()
            best_solution.energy = x_best.energy
            converged_num = 0
        else:
            converged_num += 1

    # build final results from solution_pool
    out_data = []
    for i in range(len(solution_pool)):
        out_data.append({
            "result": i + 1,
            "quboValue": solution_pool[i].energy,
            "solutionVector": solution_pool[i].solution.tolist(),
        })

    logger.info(
        f"subqubo_schedule completed: job_id={job_id}, "
        f"cycles={cycles_num}, solutions={len(out_data)}"
    )

    # wrap in the same record shape poll_job_results returns so the
    # caller (wirecut_flow) treats qubo and circuit branches alike
    return [
        {
            "job_id": job_id,
            "job_status": Constant.JOB_STATUS_COMPLETED,
            "progress": 100,
            "results": [
                {
                    "results": {"out_data": out_data},
                    "metadata": {"status": Constant.JOB_STATUS_COMPLETED},
                    "num_qubits": len(qubo_matrix),
                }
            ],
        }
    ]


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

    for idx, device_schedule in enumerate(schedule_results):
        device_name = device_schedule["device_name"]
        source_codes = device_schedule["source_codes"]
        sub_job_id = f"{job_id}_{idx}"

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
        wirecut_job_data["job_id"] = sub_job_id
        wirecut_job_data["job_name"] = None
        wirecut_job_data["backend"] = device_name
        wirecut_job_data["backend_type"] = Constant.BACKEND_TYPE_DEVICE
        wirecut_job_data["source_code"] = source_codes
        wirecut_job_data["options"]["enable_wirecut"] = False
        wirecut_job_data["circuit_aggregation"] = None
        if "filtered_devices" in wirecut_job_data:
            del wirecut_job_data["filtered_devices"]
        wirecut_job_data["db_config"] = {
            "results_db_storage": Constant.RESULTS_DB_STORAGE_REDIS,
            "ttl": WIRECUT_SUBJOB_REDIS_TTL,
        }
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
            wirecut_flow_run_name = (
                f"{Constant.WIRECUT_FLOW_RUN_PREFIX}{sub_job_id}"
            )
            wirecut_work_queue_name = (
                f"{Constant.WORK_POOL_DEV}|{device_name}_"
                f"{Constant.SUB_WIRECUT_PRIORITY}"
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
                f"Submitted sub-flow ... job_id:{sub_job_id}, "
                f"device={device_name}, "
                f"driver={device_schedule['driver_class_name']}, "
                f"deploy_id={wirecut_deploy_id}, "
                f"work_queue={wirecut_work_queue_name}"
            )
            logger.info(
                f"Submitted sub-flow for sub-circuit or subqubo: "
                f"job_id:{sub_job_id}, "
                f"flow_run_name={wirecut_flow_run_name}, "
                f"flow_run_id={wirecut_flow_run_id}, "
                f"device={device_name}"
            )
            wirecut_job = {
                "flow_run_id": wirecut_flow_run_id,
                "job_id": sub_job_id,
                "circuit": None,
            }
            wirecut_job_list.append(wirecut_job)
        except Exception as e:
            err_msg = (
                f"Failed to submit sub-flow for sub-circuit "
                f"or subqubo: {str(e)}"
            )
            logger.error(err_msg)
            raise ValueError(err_msg)
    return wirecut_job_list


def _snapshot_pending_jobs(
    redis_client,
    pending,
    pending_ids,
    collected_results,
    sub_job_progress,
):
    """Read back redis keys of still-pending sub-jobs.

    Used both right after subscribing (to close the race where a
    sub-job reached terminal status before the subscription was
    established, as redis pub/sub does not replay old messages)
    and whenever the listen loop times out without a message (to
    recover from a lost pub/sub notification: the sub-job side
    performs the redis SET and the PUBLISH as two separate calls,
    so a record can be safely stored in redis while its
    notification never arrives).

    Args:
        redis_client: redis client instance.
        pending (list): list of (flow_run_id, redis_key, channel)
            triples in new_job_list order.
        pending_ids (set): ids of sub-jobs not collected yet;
            updated in place.
        collected_results (dict): collected terminal records keyed
            by flow_run_id; updated in place.
        sub_job_progress (dict): per-sub-job latest progress; keyed
            by flow_run_id, updated in place.
    """
    for flow_run_id, redis_key, _ in pending:
        if flow_run_id not in pending_ids:
            continue
        try:
            raw_record = redis_client.get(redis_key)
        except Exception as e:
            logger.warning(
                f"Poll job results: failed to read back {redis_key}: {str(e)}"
            )
            continue
        if not raw_record:
            continue
        try:
            record = json.loads(raw_record)
        except Exception as e:
            logger.warning(
                f"Poll job results: failed to parse record in "
                f"{redis_key}: {str(e)}"
            )
            continue
        progress = record.get("progress")
        if progress is not None:
            sub_job_progress[flow_run_id] = progress
        job_status = record.get("job_status")
        if job_status in Constant.JOB_TERMINAL_STATUSES:
            collected_results[flow_run_id] = record
            pending_ids.discard(flow_run_id)
            logger.info(
                f"Poll job results: sub-job {flow_run_id} reached "
                f"terminal status={job_status} (read back from "
                f"redis)"
            )


def poll_job_results(
    new_job_list,
    job_id=None,
    redis_instance=None,
    monitor_info=None,
):
    """Watch sub-job results via redis pub/sub.

    Each sub-job stores its result in redis under the key
    ``{REDIS_CHANNEL_JOB_PREFIX}/{flow_run_name}/{flow_run_id}`` and
    publishes a notification on the pub/sub channel
    ``{REDIS_CHANNEL_JOB_PREFIX}/{flow_run_name}/{flow_run_id}`` on
    every update (including progress changes). This function
    subscribes to those channels — mirroring the
    ``subscribe_device_info`` pattern — and collects results as
    terminal-status notifications arrive. Non-terminal notifications
    are used to update the per-sub-job progress stored in
    ``monitor_info["sub_job_progress"]`` so the task_monitor can
    compute an aggregated parent-job progress.

    Because redis pub/sub does not replay messages published before
    the subscription is established, a sub-job may already have
    reached terminal status before this function subscribes (e.g.
    a fast sub-job finishing while ``submit_jobs`` is still
    looping). To close that race the channels are subscribed first
    and every sub-job redis key is then read back once;
    already-terminal sub-jobs are collected from that snapshot
    while later updates arrive through the subscription.

    Additionally, the sub-job side performs the redis SET and the
    pub/sub PUBLISH as two separate calls, so a terminal record can
    be safely stored in redis while its notification is lost. The
    listen loop therefore blocks on ``get_message`` with a bounded
    timeout (:data:`POLL_MESSAGE_TIMEOUT`) and, whenever no message
    arrives in time, re-reads the redis keys of the still-pending
    sub-jobs as a fallback, so a lost notification can never hang
    the parent flow forever.

    Args:
        new_job_list (list): sub-job list returned by submit_jobs,
            each item containing ``flow_run_id`` and
            ``flow_run_name``.
        job_id (str): parent wirecut job id (for logging).
        redis_instance: redis client instance. When None, the
            global redis client set via set_redis_client in the
            current worker process is used; if that is also None
            the function returns an empty list.
        monitor_info (dict): optional monitor info dict. When
            provided, per-sub-job progress values received from
            pub/sub are written into
            ``monitor_info["sub_job_progress"]`` keyed by
            flow_run_id.

    Returns:
        list: job results list, one entry per sub-job.
    """
    redis_client = redis_instance or get_redis_client()
    if redis_client is None:
        logger.error("Poll job results: redis client not initialized")
        return []

    if not new_job_list:
        logger.info("Poll job results: no sub-jobs to watch")
        return []

    # build the list of (flow_run_id, redis_key, channel) triples
    # in order. The channel and redis key embed both flow_run_name
    # (sub-job id) and flow_run_id so the subscriber can match a
    # notification back to its sub-job.
    pending = []
    for item in new_job_list:
        # NOTE: use a distinct local name so the ``job_id`` parameter
        # (used for logging) is not shadowed by the sub-job's id.
        sub_job_id = item.get("job_id", None)
        flow_run_id = str(item["flow_run_id"])
        redis_key = (
            f"{Constant.REDIS_CHANNEL_JOB_PREFIX}/{sub_job_id}/{flow_run_id}"
        )
        channel = redis_key
        pending.append((flow_run_id, redis_key, channel))

    pending_ids = {fid for fid, _, _ in pending}
    channel_to_fid = {ch: fid for fid, _, ch in pending}

    collected_results = {}
    sub_job_progress = monitor_info["sub_job_progress"] if monitor_info else {}

    logger.info(
        f"Poll job results: {job_id}, watching {len(pending_ids)} "
        f"sub-job(s) via pub/sub"
    )

    # subscribe to the job notification channels and listen for
    # messages (same pattern as subscribe_device_info). Each sub-job
    # publishes its updated record on the channel
    # "{REDIS_CHANNEL_JOB_PREFIX}/{job_id}/{flow_run_id}" on
    # every update (see RedisJobStorageBackend.update_job). The
    # message data is the record JSON so we can read progress and
    # status directly without an extra redis GET.
    pubsub = redis_client.pubsub()
    channels = [ch for fid, _, ch in pending]
    if channels:
        pubsub.subscribe(*channels)

    # Redis pub/sub does not replay messages published before the
    # subscription is established, so a sub-job that reached terminal
    # status during the submit->subscribe window would never be
    # observed via the subscription. Subscribe first, then read back
    # each sub-job redis key once: already-terminal sub-jobs are
    # collected from this snapshot while updates published after
    # the SUBSCRIBE call are delivered by the subscription itself,
    # so no notification can fall in between.
    _snapshot_pending_jobs(
        redis_client,
        pending,
        pending_ids,
        collected_results,
        sub_job_progress,
    )

    # Listen with a bounded timeout. The sub-job side performs
    # redis SET and pub/sub PUBLISH as two separate calls, so a
    # terminal notification can be lost even though the record is
    # safely stored in redis (SET and PUBLISH are not atomic). When
    # no message arrives within POLL_MESSAGE_TIMEOUT seconds, re-read
    # the redis keys of all still-pending sub-jobs as a fallback so
    # the parent eventually collects every terminal record and never
    # blocks forever on a lost notification.
    try:
        while pending_ids:
            msg = pubsub.get_message(timeout=POLL_MESSAGE_TIMEOUT)
            # only process actual messages (skip subscribe/ping
            # confirmations); get_message returns None on timeout
            # without a message
            if msg is None:
                _snapshot_pending_jobs(
                    redis_client,
                    pending,
                    pending_ids,
                    collected_results,
                    sub_job_progress,
                )
                continue
            if msg.get("type") != "message":
                continue

            channel = msg.get("channel", b"")
            if isinstance(channel, bytes):
                channel = channel.decode("utf-8")

            flow_run_id = channel_to_fid.get(channel)
            if flow_run_id is None:
                continue

            # the message data is the updated record JSON
            data = msg.get("data")
            try:
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                record = json.loads(data)
            except Exception as e:
                logger.debug(
                    f"Poll job results: failed to parse "
                    f"notification on {channel}: {str(e)}"
                )
                continue

            # record latest progress for aggregation
            progress = record.get("progress")
            if progress is not None:
                sub_job_progress[flow_run_id] = progress

            if flow_run_id in collected_results:
                continue

            job_status = record.get("job_status")
            if job_status in Constant.JOB_TERMINAL_STATUSES:
                collected_results[flow_run_id] = record
                pending_ids.discard(flow_run_id)
                logger.info(
                    f"Poll job results: sub-job "
                    f"{flow_run_id} reached terminal "
                    f"status={job_status}"
                )
    finally:
        pubsub.unsubscribe()
        pubsub.close()

    if pending_ids:
        logger.warning(
            f"Poll job results: {len(pending_ids)} "
            f"sub-job(s) did not reach terminal status: "
            f"{pending_ids}"
        )

    # delete the consumed redis keys
    for _, redis_key, _ in pending:
        if redis_client.delete(redis_key):
            logger.debug(f"Poll job results: deleted redis key {redis_key}")

    # build the final results list in the same order as new_job_list
    job_results_list = []
    for flow_run_id, _, _ in pending:
        record = collected_results.get(flow_run_id, {})
        job_results_list.append(record)

    # print all sub-job results
    logger.info(
        f"Poll job results: collected {len(job_results_list)} "
        f"sub-job result(s)"
    )
    for idx, record in enumerate(job_results_list):
        logger.info(f"--- sub-job[{idx}] result: {record}")

    return job_results_list


def merge_job_results(job_results_list):
    """Merge job results.

    Args:
        job_results_list: sub-job results list.

    Returns:
        merged job results.
    """
    merged_job_results = []
    err_msgs = []
    for job_results in job_results_list:
        job_status = job_results.get("job_status")
        _job_results = job_results.get("results", [])
        if job_status != Constant.JOB_STATUS_COMPLETED:
            for _job_result in _job_results:
                err_info = _job_result.get("error", {})
                err_msg = err_info.get("message", "")
                err_msgs.append(err_msg)
        # TODO: implement jobs merge
        merged_job_results.append(job_results)
    if err_msgs:
        driver = None
        err_cls = errors.WirecutEngineSubJobError
        err_msg = "\n".join(err_msgs)
        merged_job_results = [format_error_results(driver, err_cls, err_msg)]

    return merged_job_results


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


@task(persist_result=False)
def task_monitor(monitor_info):
    """Monitor wirecut sub-job progress and update parent progress.

    Reads the per-sub-job progress values stored in
    ``monitor_info["sub_job_progress"]`` (populated by
    :func:`poll_job_results` from pub/sub notifications) and computes
    the parent job progress as the average of all sub-job progress
    values. When the aggregated value changes, it is written to the
    database via :func:`update_progress`.

    The loop runs while ``monitor_info["running"]`` is True, sleeping
    1 second between iterations. On exit it sets the parent progress
    to 100.

    Args:
        monitor_info: monitor info dict containing at least
            ``job_id``, ``db_engine``, ``running`` and
            ``sub_job_progress``.
    """
    job_id = monitor_info.get("job_id")
    db_engine = monitor_info.get("db_engine")
    flow_run_id = monitor_info.get("flow_run_id")
    last_job_progress = -1

    # resolve storage backend config from monitor_info so that
    # progress updates are persisted to the correct backend (sql or
    # redis) matching the job's db_config.
    db_config = monitor_info.get("db_config", {})
    results_db_storage = db_config.get(
        "results_db_storage",
        Constant.RESULTS_DB_STORAGE_DEFAULT,
    )
    ttl = db_config.get("ttl")

    if not job_id or not db_engine:
        logger.warning(
            "task_monitor: job_id or db_engine not found in monitor_info"
        )
        return

    while monitor_info["running"]:
        sub_job_progress = monitor_info.get("sub_job_progress", {})
        if sub_job_progress:
            values = list(sub_job_progress.values())
            avg_progress = int(sum(values) / len(values))
        else:
            avg_progress = 0

        if avg_progress != last_job_progress:
            update_progress(
                job_id,
                db_engine,
                avg_progress,
                results_db_storage=results_db_storage,
                flow_run_id=flow_run_id,
                ttl=ttl,
            )
            last_job_progress = avg_progress
        time.sleep(1)

    # ensure final progress is set to 100
    update_progress(
        job_id,
        db_engine,
        100,
        results_db_storage=results_db_storage,
        flow_run_id=flow_run_id,
        ttl=ttl,
    )


def flow_task_monitor(monitor_info):
    """Flow: start the wirecut task monitor.

    Submits :func:`task_monitor` as a background prefect task.

    Args:
        monitor_info: monitor info dict
    """
    task_monitor.submit(monitor_info)
