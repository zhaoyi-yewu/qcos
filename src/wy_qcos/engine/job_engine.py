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

import copy
import importlib
import json

import numpy as np
import os
import signal
import time
from typing import Any

import redis
from loguru import logger
from prefect import flow, task, pause_flow_run
from prefect.input import RunInput
from prefect.runtime import flow_run

from wy_qcos.common.constant import Constant
from wy_qcos.common import errors
from wy_qcos.common.library import (
    Library,
    _is_allowed_module,
    _is_allowed_class_name,
)
from wy_qcos.engine.common import init_logger
from wy_qcos.engine.qubo import (
    subqubo,
    check_matrix,
    check_qubo_matrix_bit_width,
    precision_reduction,
    qubo_matrix_to_ising_matrix,
    ising_matrix_to_qubo_matrix,
    scale_to_integer_matrix,
    get_spins_num,
    process_qubo_solution,
)
from wy_qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from wy_qcos.transpiler.common.wirecut.cut_wire import (
    generate_all_variant_subcircuits_for_execute,
    reconstruct_probability_distribution_wire_cut,
)
from wy_qcos.transpiler.common.wirecut.result_cache import (
    SubcircuitResultCache,
)
from wy_qcos.db.utils import db_utils
from wy_qcos.db.database import init_database


class AggregationInput(RunInput):
    is_parent: bool
    sub_jobs: dict | None = None
    sub_results: list[Any] | None = None


class SourceCodeInfo:
    aggregation_type: str
    src_code_list: list[dict] = []
    sub_flow_list: list[str] = []


@task(persist_result=False)
def init_driver(
    driver_class_info, driver_options=None, device=None, job_info=None
):
    """Init driver from driver_class_info.

    Args:
        driver_class_info: driver class info
        driver_options: driver options
        device: device info
        job_info: job info

    Returns:
        driver
    """
    driver_module_name = driver_class_info["module_name"]
    try:
        # security: validate module name against whitelist before import
        if not _is_allowed_module(driver_module_name):
            raise ValueError(
                f"Driver module '{driver_module_name}' is not in the "
                f"allowed import whitelist"
            )
        # load driver module
        driver_module = importlib.import_module(driver_module_name)

        # security: validate class name before dynamic attribute access
        driver_class_name = driver_class_info["class_name"]
        if not _is_allowed_class_name(driver_class_name):
            raise ValueError(
                f"Driver class name '{driver_class_name}' is not a "
                f"valid identifier or is a dunder attribute"
            )

        # initialize driver class
        driver_class = getattr(driver_module, driver_class_name)
        driver = driver_class()
        device_configs = device.get("configs", None)

        # update driver options
        if driver_options:
            driver.update_driver_options(driver_options)

        # validate device configs
        success, err_msg = driver.validate_driver_configs(device_configs)
        # error handling
        if not success:
            logger.error(err_msg)
            return {"driver": driver, "error": err_msg}

        # copy device configs to driver
        driver.set_configs(device_configs)

        # init driver
        driver.init_driver()

        if job_info:
            # init job
            job_data = job_info["data"]
            remote_transpiler_configs = None
            if not job_data.get("dry_run", False):
                remote_transpiler_configs = driver.fetch_configs()

            # copy cfgs to transpiler cfg inst
            static_transpiler_configs = device_configs.get("transpiler", None)
            trans_cfg_inst.set_max_qubits(driver.get_max_qubits())
            trans_cfg_inst.set_tech_type(driver.tech_type)
            trans_cfg_inst.set_driver_name(driver.get_name())

            # config qpu_config/decomposition_rule from config file
            if static_transpiler_configs:
                qpu_configs = static_transpiler_configs.get(
                    "qpu_configs", None
                )
                decomposition_rule = static_transpiler_configs.get(
                    "decomposition_rule", None
                )
                trans_cfg_inst.set_qpu_cfg(qpu_configs)
                trans_cfg_inst.set_decompose_rule(decomposition_rule)

            # config qpu_config/decomposition_rule dynamically
            # override static_transpiler_configs if necessary
            if remote_transpiler_configs:
                qpu_configs = remote_transpiler_configs.get(
                    "qpu_configs", None
                )
                decomposition_rule = remote_transpiler_configs.get(
                    "decomposition_rule", None
                )
                trans_cfg_inst.set_qpu_cfg(qpu_configs)
                trans_cfg_inst.set_decompose_rule(decomposition_rule)

        return {"driver": driver, "error": None}
    except Exception as e:
        return {"driver": None, "error": ValueError(str(e))}


@task(persist_result=False)
def init_transpiler(transpiler_class_info, transpiler_options):
    """Init transpiler instance.

    Args:
        transpiler_class_info: transpiler class info
        transpiler_options: transpiler options

    Returns:
        transpiler
    """
    transpiler_module_name = transpiler_class_info["module_name"]
    try:
        # security: validate module name against whitelist before import
        if not _is_allowed_module(transpiler_module_name):
            raise ValueError(
                f"Transpiler module '{transpiler_module_name}' is not in "
                f"the allowed import whitelist"
            )
        transpiler_module = importlib.import_module(transpiler_module_name)

        # security: validate class name before dynamic attribute access
        transpiler_class_name = transpiler_class_info["class_name"]
        if not _is_allowed_class_name(transpiler_class_name):
            raise ValueError(
                f"Transpiler class name '{transpiler_class_name}' is not "
                f"a valid identifier or is a dunder attribute"
            )

        transpiler_class = getattr(transpiler_module, transpiler_class_name)
        transpiler = transpiler_class()
        if transpiler_options:
            transpiler.update_transpiler_options(transpiler_options)
        return {"transpiler": transpiler, "error": None}
    except Exception as e:
        return {"transpiler": None, "error": ValueError(str(e))}


@task(persist_result=False)
def task_monitor(monitor_info):
    driver = None
    last_job_progress = 0
    job_id = monitor_info.get("job_id")
    db_engine = monitor_info.get("db_engine")
    agg_sub_job_list = monitor_info.get("agg_sub_job_list")

    if not job_id or not db_engine:
        logger.warning("job_id or db_engine not found in monitor_info")
        return

    while monitor_info["running"]:
        if not driver:
            driver = monitor_info["driver"]
        if driver:
            job_progress = int(
                monitor_info["progress"]
                + int(
                    driver.get_progress() / monitor_info["source_code_count"]
                )
            )
            if last_job_progress != job_progress:
                # update job progress to database
                update_progress(job_id, db_engine, job_progress)
                # update agg sub job progress to database
                if agg_sub_job_list:
                    for sub_job_id in agg_sub_job_list:
                        update_progress(sub_job_id, db_engine, job_progress)
            last_job_progress = job_progress
        time.sleep(1)
    # update job progress to database
    update_progress(job_id, db_engine, 100)
    # update agg sub job progress to database
    if agg_sub_job_list:
        for sub_job_id in agg_sub_job_list:
            update_progress(sub_job_id, db_engine, 100)


@task(persist_result=False)
def parse(src_code_dict, transpiler, code_type):
    """Parse task.

    Args:
        src_code_dict: src_code_dict
        transpiler: transpiler
        code_type(str): code type

    Returns:
        parsed results
    """
    try:
        parsed_src_code = transpiler.parse(src_code_dict, code_type)
        logger.info(f"final parsed src code: {parsed_src_code}")
        return {"parsed_src_code": parsed_src_code, "error": None}
    except Exception as e:
        return {"parsed_src_code": None, "error": ValueError(str(e))}


@task(persist_result=False)
def transpile(parsed_gates, driver, transpiler):
    """Transpile task.

    Args:
        parsed_gates: parsed gates
        driver: driver
        transpiler: transpiler

    Returns:
        basis gate list
    """
    num_qubits = -1
    try:
        supp_basis_gates = driver.get_supported_basis_gates()
        transpile_results, mapping_dict = transpiler.transpile(
            parsed_gates, supp_basis_gates
        )
        num_qubits = transpiler.total_qubits
        logger.info(f"final transpiled_result: {transpile_results}")
        return {
            "transpile_results": transpile_results,
            "mapping_dict": mapping_dict,
            "num_qubits": num_qubits,
            "error": None,
        }
    except Exception as e:
        return {
            "transpile_results": None,
            "mapping_dict": None,
            "num_qubits": num_qubits,
            "error": ValueError(str(e)),
        }


@task(persist_result=False)
def driver_run(job_info, driver, num_qubits, data):
    """Driver: run job.

    Args:
        job_info: job info
        driver: driver
        num_qubits: number of qubits
        data: data

    Returns:
        results
    """
    try:
        job_data = job_info["data"]
        job_id = job_data["job_id"]
        shots = job_data.get("shots", Constant.DEFAULT_SHOTS)
        dry_run = job_data.get("dry_run", False)
        data_type = driver.get_default_data_type()
        qec_options = job_data.get("qec_options", None)
        if dry_run:
            driver.dry_run(
                job_id,
                num_qubits,
                data,
                data_type=data_type,
                shots=shots,
                qec_options=qec_options,
            )
        else:
            driver.run(
                job_id,
                num_qubits,
                data,
                data_type=data_type,
                shots=shots,
                qec_options=qec_options,
            )

        return format_run_results(driver, job_id, data["index"])
    except Exception as e:
        return {"results": None, "metadata": {}, "error": ValueError(str(e))}


def driver_cancel(job_id, driver):
    """Driver: cancel job.

    Args:
        job_id: job id
        driver: driver
    """
    try:
        logger.info(f"Cancel job: job_id: {job_id}")
        if driver:
            driver.cancel(job_id)
        else:
            logger.error(f"Cancel job: job_id: {job_id}. driver is not found")
    except Exception as e:
        logger.error(f"Cancel job: job_id: {job_id} failed. {str(e)}")


def register_signals(job_id, monitor):
    """Register signal handlers.

    Args:
        job_id: job id
        monitor: monitor
    """

    def handle_sigterm(signum, frame):
        """Handles SIGTERM(cancel) signal sent from Prefect.

        Prefect will then kill job_engine process by graceful period (30 secs)

        Args:
            signum: signum
            frame: frame
        """
        logger.info(f"Received sigterm, cancelling job: {job_id} ...")

        # Update job status to CANCELLED in database
        try:
            db_engine = monitor.get("db_engine")
            job_status = Constant.JOB_STATUS_CANCELLING
            db_utils.db_update_job(job_id, db_engine, job_status=job_status)
        except Exception as e:
            logger.error(
                f"Failed to update job status to CANCELLING: {str(e)}"
            )

        driver = monitor["driver"]
        driver_cancel(job_id, driver)

        os._exit(1)  # force to exit when user cancelled a job

    signal.signal(signal.SIGTERM, handle_sigterm)


def update_progress(job_id, db_engine, progress):
    """Update job progress to database.

    Args:
        job_id: job ID
        db_engine: database engine instance
        progress: progress value (0-100)
    """
    db_utils.db_update_job(job_id, db_engine, progress=progress)


def create_src_code_info(job_data):
    """Create src code info.

    Args:
        job_data: job data

    Returns:
        src_code_info
    """
    src_code_info = SourceCodeInfo()
    source_code_list = job_data["source_code"]
    job_id = job_data["job_id"]
    src_code_index = 0
    if job_data["circuit_aggregation"] is None:
        src_code_info.aggregation_type = Constant.AGGREGATION_TYPE_NONE
        src_code_info.src_code_list = []
        for source_code in source_code_list:
            src_code_map = {}
            src_code_map[job_id + "-" + str(src_code_index)] = source_code
            src_code_index += 1
            src_code_info.src_code_list.append(src_code_map)
    else:
        src_code_info.aggregation_type = job_data["circuit_aggregation"]
        src_code_info.src_code_list = []
        src_code_map = {}
        for source_code in source_code_list:
            if len(src_code_map) >= Constant.MAX_AGGREGATION_JOBS:
                src_code_info.src_code_list.append(src_code_map)
                src_code_map.clear()
                continue
            src_code_map[job_id + "-" + str(src_code_index)] = source_code
            src_code_index += 1

        if len(src_code_map) != 0:
            src_code_info.src_code_list.append(src_code_map)
    return src_code_info


def update_src_code_info(src_code_info, aggregation_info):
    """Update src code info.

    Args:
        src_code_info: src_code_info
        aggregation_info: aggregation info

    Returns:
        src_code_info
    """
    length = len(src_code_info.src_code_list)
    if length == 0:
        raise ValueError("unexpected input")

    src_code_map = src_code_info.src_code_list[length - 1]
    src_code_info.src_code_list.pop()
    for job_id, job_value in aggregation_info.sub_jobs.items():
        if len(src_code_map) > Constant.MAX_AGGREGATION_JOBS:
            # Unreachable code
            src_code_info.src_code_list.append(src_code_map)
            src_code_map.clear()
            continue
        src_code = job_value["job_info"]["data"]["source_code"][0]
        src_code_map[job_id + "-0"] = src_code
        flow_run_id = job_value["job_info"]["data"]["flow_run_id"]
        src_code_info.sub_flow_list.append(flow_run_id)

    if len(src_code_map) != 0:
        src_code_info.src_code_list.append(src_code_map)
    return src_code_info


def get_src_code_cnt(src_code_info: SourceCodeInfo):
    """Get total src code count.

    Args:
        src_code_info: src_code_info

    Returns:
        src_code_cnt
    """
    src_code_cnt = 0
    for code_dict in src_code_info.src_code_list:
        src_code_cnt += len(code_dict)

    return src_code_cnt


def split_dict(orig_dict, split_len):
    """Split dict.

    Args:
        orig_dict: orig_dict
        split_len: split_len

    Returns:
        measure_results
    """
    measure_results = [{} for _ in split_len]
    for key, value in orig_dict.items():
        current_index = 0
        for i, length in enumerate(split_len):
            end_index = current_index + length
            sub_key = key[current_index:end_index]
            measure_results[i][sub_key] = value
            current_index = end_index
    return measure_results


def get_internal_aggregated_results(job_results, mapping_dict):
    """Get internal aggregated results.

    Args:
        job_results: job results
        mapping_dict: mapping dict

    Returns:
        aggregated_results
    """
    if mapping_dict is None:
        raise ValueError("mapping_dict is none")
    split_len = []
    for job_id, num_qubits in mapping_dict.items():
        split_len.append(num_qubits)

    aggregated_results = []
    measure_results = split_dict(job_results["results"], split_len)
    for item in measure_results:
        if item is None:
            continue
        single_result = copy.deepcopy(job_results)
        single_result["results"] = item
        single_result["num_qubits"] = len(next(iter(item.keys())))
        single_result["metadata"]["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_INTERNAL
        )

        aggregated_results.append(single_result)

    return aggregated_results


def get_external_aggregated_results(job_results, mapping_dict):
    """Get external aggregated results.

    Args:
        job_results: job results
        mapping_dict: mapping dict

    Returns:
        new job results
    """
    if mapping_dict is None:
        raise ValueError("mapping_dict is none")

    split_len = []
    for job_id, num_qubits in mapping_dict.items():
        split_len.append(num_qubits)

    measure_results = split_dict(job_results["results"], split_len)
    if len(mapping_dict) != len(measure_results):
        raise ValueError("unexpected len of measure_results")
    measure_dict = dict(zip(mapping_dict.keys(), measure_results))
    parent_job = True
    sub_results = {}
    for job_id, value in measure_dict.items():
        if parent_job:
            parent_job = False
            job_results["results"] = value
            job_results["num_qubits"] = len(next(iter(value.keys())))
            continue
        single_result = {
            "results": copy.deepcopy(value),
            "num_qubits": len(next(iter(value.keys()))),
            "metadata": copy.deepcopy(job_results["metadata"]),
            "profiling": copy.deepcopy(job_results["profiling"]),
        }
        single_result["metadata"]["circuit_aggregation"] = (
            Constant.AGGREGATION_TYPE_EXTERNAL
        )
        new_id = job_id.rsplit("-", 1)[0]
        sub_results[new_id] = single_result

    job_results["sub_results"] = sub_results
    return job_results


@flow(
    persist_result=False,
    on_failure=[db_utils.db_job_callback],
    on_crashed=[db_utils.db_job_callback],
    on_cancellation=[db_utils.db_job_callback],
    on_completion=[db_utils.db_job_callback],
)
def job_flow(job_info):
    """Job flow.

    .. code-block:: text

        Detail of job flow:
        Create task_monitor -> Handle Circuit-Aggregation ->
        loop src_code_list ->
        [
            run_code ->
                init_driver ->
                    driver.validate_driver_configs(device_configs)
                    driver.set_configs(device_configs)
                    driver.init_driver() ->
                    driver.fetch_configs() ->
                init_transpiler ->
                flow_parse ->
                    transpiler.parse() ->
                flow_transpile ->
                    transpiler.transpile() ->
                flow_run_driver ->
                    driver_run ->
                        driver.run() / driver.dry_run() ->
            get_results
        ]
        return job_results_list

    Args:
        job_info: job info

    Returns:
        results
    """
    worker_started_at = time.time()
    job_data = job_info["data"]
    job_id = job_data["job_id"]
    global_configs = job_info["global"]["configs"]
    device_configs = job_info["device"]["configs"]
    backend = job_data["backend"]
    flow_run_id = flow_run.id
    callbacks = job_data.get("callbacks", None)
    job_enqueue_at = job_data["job_enqueue_at"]
    scheduling_started_at = job_data["job_schedule_started_at"]
    scheduling_ended_at = job_data["job_schedule_ended_at"]
    scheduling_duration = job_data["job_schedule_duration"]
    monitor_info = {
        "job_id": job_id,
        "flow_run_id": flow_run_id,
        "configs": global_configs,
        "device_configs": device_configs,
        "callbacks": callbacks,
        "user": {
            "project_id": job_data.get("project_id", None),
            "user_id": job_data.get("user_id", None),
        },
        "redis": {
            "ip": global_configs["REDIS"].get("REDIS_SERVER_IP", None),
            "port": global_configs["REDIS"].get("REDIS_SERVER_PORT", None),
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
    if "debug" in device_configs:
        debug = device_configs["debug"]
    device_log_file = f"/var/log/qcos/device_{backend}.log"
    if "device_log_file" in device_configs:
        device_log_file = device_configs["device_log_file"]

    # Extract logging configuration parameters
    log_format = device_configs.get("log_format")
    log_rotate_max_size_mb = device_configs.get("log_rotate_max_size_mb")
    log_rotate_backup_count = device_configs.get("log_rotate_backup_count")
    log_rotate_compression = device_configs.get("log_rotate_compression")

    init_logger(
        log_file_path=device_log_file,
        debug=debug,
        log_format=log_format,
        log_rotate_max_size_mb=log_rotate_max_size_mb,
        log_rotate_backup_count=log_rotate_backup_count,
        log_rotate_compression=log_rotate_compression,
    )
    logger.info(f"Processing work flow: job_engine. job_id: {job_id}")
    logger.debug(f"Job details: job_id: {job_id}, job_info: {job_info}")

    # init db engine
    try:
        db_url = global_configs["DATABASE"]["QCOS_DATABASE_CONNECTION_URL"]
        db_engine = init_database(db_url)
        monitor_info["db_engine"] = db_engine
        db_utils.set_db_engine(db_engine)
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        db_engine = None

    # update job status to RUNNING and set started_at
    db_utils.db_update_job(
        job_id,
        db_engine,
        job_status=Constant.JOB_STATUS_RUNNING,
        started_at=Library.to_iso(worker_started_at),
        progress=-1,
    )

    # register signals for job cancelling
    register_signals(job_id, monitor_info)

    # record parse start_time
    profiling_code_start = time.time()

    # start task-monitor
    flow_task_monitor(monitor_info)

    # handle aggregation jobs
    aggregation_info = None
    src_code_info = create_src_code_info(job_data)
    if src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL:
        # circuit_aggregation(multi) tag flow run will automatically paused
        # here waiting for aggregation_info generated by task manager
        # [LEAK-FIX] Use a short-lived redis instance only for the publish
        # call, then explicitly close its connection pool. Previously the
        # instance was created and never closed, so under high aggregation
        # throughput the GC timing was non-deterministic and idle sockets
        # accumulated in redis-server. Closing immediately after publish
        # (before the blocking pause_flow_run) minimizes socket hold time.
        channel_name = f"{Constant.REDIS_CHANNEL_JOB_AGG_PREFIX}/{flow_run_id}"
        flow_agg_info = {
            "flow_run_id": flow_run_id,
            "aggregation_type": src_code_info.aggregation_type,
            "cancel": False,
        }
        redis_instance = redis.Redis(
            host=monitor_info["redis"]["ip"],
            port=monitor_info["redis"]["port"],
            decode_responses=True,
        )
        try:
            redis_instance.publish(channel_name, json.dumps(flow_agg_info))
        finally:
            try:
                redis_instance.close()
            except Exception as close_err:
                logger.debug(
                    f"Error closing aggregation redis instance: {close_err}"
                )
        aggregation_info = pause_flow_run(
            wait_for_input=AggregationInput, poll_interval=1
        )

        # handle sub job which is unexpected
        # should be processed in db_job_callback
        if not aggregation_info.is_parent:
            return None

        logger.debug(
            f"Process aggregation sub job, aggregation_info: "
            f"{aggregation_info}"
        )

        # update job_status and worker_started_at for agg sub jobs
        for sub_job_id, sub_info_info in aggregation_info.sub_jobs.items():
            db_utils.db_update_job(
                sub_job_id,
                db_engine,
                job_status=Constant.JOB_STATUS_RUNNING,
                started_at=Library.to_iso(worker_started_at),
                progress=-1,
            )
            monitor_info["agg_sub_job_list"].append(sub_job_id)

        # update src_code_info
        src_code_info = update_src_code_info(src_code_info, aggregation_info)

    # run source codes
    driver = None
    job_results_list = []
    source_code_index = 0
    transpiler = None
    percentage_base = 100
    source_code_count = get_src_code_cnt(src_code_info)
    monitor_info["source_code_count"] = source_code_count

    # TODO(xudong) need to handle aggregation failed items
    for src_code_dict in src_code_info.src_code_list:
        monitor_info["source_code_index"] = source_code_index
        monitor_info["progress"] = (
            percentage_base * source_code_index / source_code_count
        )
        job_results, driver, transpiler, mapping_dict = run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
            monitor_info,
        )
        source_code_index += len(src_code_dict)
        # profiling: job
        job_results["profiling"][
            Constant.PROFILING_TYPE_SCHEDULING_STARTED_AT
        ] = Library.to_iso(scheduling_started_at)
        job_results["profiling"][
            Constant.PROFILING_TYPE_SCHEDULING_ENDED_AT
        ] = Library.to_iso(scheduling_ended_at)
        job_results["profiling"][Constant.PROFILING_TYPE_SCHEDULING] = round(
            scheduling_duration, 5
        )
        profiling_queuing_duration = worker_started_at - job_enqueue_at
        job_results["profiling"][
            Constant.PROFILING_TYPE_QUEUING_STARTED_AT
        ] = Library.to_iso(worker_started_at)
        job_results["profiling"][Constant.PROFILING_TYPE_QUEUING_ENDED_AT] = (
            Library.to_iso(job_enqueue_at)
        )
        job_results["profiling"][Constant.PROFILING_TYPE_QUEUING] = round(
            profiling_queuing_duration, 5
        )
        profiling_code_end = time.time()
        profiling_code_duration = profiling_code_end - profiling_code_start
        job_results["profiling"][Constant.PROFILING_TYPE_CODE_STARTED_AT] = (
            Library.to_iso(profiling_code_start)
        )
        job_results["profiling"][Constant.PROFILING_TYPE_CODE_ENDED_AT] = (
            Library.to_iso(profiling_code_end)
        )
        job_results["profiling"][Constant.PROFILING_TYPE_CODE] = round(
            profiling_code_duration, 5
        )

        # handle job aggregation
        if (
            src_code_info.aggregation_type
            == Constant.AGGREGATION_TYPE_INTERNAL
        ):
            aggregated_res = get_internal_aggregated_results(
                job_results, mapping_dict
            )
            job_results_list.extend(aggregated_res)
        elif (
            src_code_info.aggregation_type
            == Constant.AGGREGATION_TYPE_EXTERNAL
        ):
            aggregated_res = get_external_aggregated_results(
                job_results, mapping_dict
            )
            job_results_list.append(aggregated_res)
        else:
            job_results_list.append(job_results)

    # set monitor_info
    monitor_info["running"] = False

    # cancel all agg sub-flows
    # results of sub-flows will be handled by _db_update_job
    if src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL:
        channel_name = f"{Constant.REDIS_CHANNEL_JOB_AGG_PREFIX}/{flow_run_id}"
        flow_agg_info = {
            "flow_run_id": flow_run_id,
            "cancel": True,
            "sub_flow_list": src_code_info.sub_flow_list,
        }
        redis_instance.publish(channel_name, json.dumps(flow_agg_info))

    return job_results_list


def _run_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
):
    """Flow: run.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        job_info: job info
        driver: driver
        transpiler: transpiler

    Returns:
        job results
    """
    logger.info(f"Run source_code_index: {source_code_index}\n")

    transpile_results = None
    num_qubits = None
    job_data = job_info["data"]
    code_type = job_data["code_type"]
    mapping_dict = None

    job_results = {
        "results": None,
        "num_qubits": None,
        "metadata": {"status": Constant.JOB_STATUS_RUNNING},
        "profiling": {},
        "sub_results": None,
    }

    # [flow_parse]
    parse_results, parse_profiling = flow_parse(
        src_code_dict, transpiler, code_type
    )

    job_results["profiling"][
        Constant.PROFILING_TYPE_DRIVER_PARSE_STARTED_AT
    ] = Library.to_iso(parse_profiling["parse_started_at"])
    job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_PARSE_ENDED_AT] = (
        Library.to_iso(parse_profiling["parse_ended_at"])
    )
    job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_PARSE] = round(
        parse_profiling["parse_duration"], 5
    )

    # parser: error handling
    err_msg = parse_results.get("error", None)
    if err_msg:
        job_results = format_error_results(
            driver, errors.JobEngineParseError, err_msg
        )
        return job_results, driver, transpiler, mapping_dict

    # [flow_transpile]
    transpile_task_results, transpile_profiling = flow_transpile(
        parse_results["parsed_src_code"],
        transpiler,
        driver,
    )
    job_results["profiling"][
        Constant.PROFILING_TYPE_DRIVER_TRANSPILE_STARTED_AT
    ] = Library.to_iso(transpile_profiling["transpile_started_at"])
    job_results["profiling"][
        Constant.PROFILING_TYPE_DRIVER_TRANSPILE_ENDED_AT
    ] = Library.to_iso(transpile_profiling["transpile_ended_at"])
    job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_TRANSPILE] = round(
        transpile_profiling["transpile_duration"], 5
    )

    # transpile: error handling
    err_msg = transpile_task_results.get("error", None)
    mapping_dict = transpile_task_results.get("mapping_dict", None)
    if err_msg:
        job_results = format_error_results(
            driver, errors.JobEngineTranspileError, err_msg
        )
        return job_results, driver, transpiler, mapping_dict

    transpile_results = transpile_task_results.get("transpile_results", None)
    num_qubits = transpile_task_results.get("num_qubits", None)
    if transpile_results is None or num_qubits is None:
        raise ValueError("unexpected transpile_results or num_qubits")
    job_results["num_qubits"] = num_qubits
    source_code = next(iter(src_code_dict.values()))

    if driver:
        # [flow_run_driver]
        data = {
            "index": source_code_index,
            "source_code": source_code,
            "transpile_results": transpile_results,
        }

        run_results, driver_run_profiling = flow_run_driver(
            job_info, num_qubits, driver, data
        )

        job_results["profiling"][
            Constant.PROFILING_TYPE_DRIVER_RUN_STARTED_AT
        ] = Library.to_iso(driver_run_profiling["driver_run_started_at"])
        job_results["profiling"][
            Constant.PROFILING_TYPE_DRIVER_RUN_ENDED_AT
        ] = Library.to_iso(driver_run_profiling["driver_run_ended_at"])
        job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_RUN] = round(
            driver_run_profiling["driver_run_duration"], 5
        )

        # profiling
        machine_started_at = None
        machine_ended_at = None
        machine_duration = None
        machine_profiling = run_results.get("machine_profiling", None)
        if machine_profiling:
            machine_started_at = machine_profiling.get(
                "machine_started_at", None
            )
            machine_ended_at = machine_profiling.get("machine_ended_at", None)
            machine_duration = machine_profiling.get("machine_duration", None)
        job_results["profiling"][
            Constant.PROFILING_TYPE_MACHINE_STARTED_AT
        ] = Library.to_iso(machine_started_at)
        job_results["profiling"][Constant.PROFILING_TYPE_MACHINE_ENDED_AT] = (
            Library.to_iso(machine_ended_at)
        )
        if machine_duration:
            job_results["profiling"][Constant.PROFILING_TYPE_MACHINE] = round(
                machine_duration, 5
            )
        else:
            job_results["profiling"][Constant.PROFILING_TYPE_MACHINE] = (
                machine_duration
            )

        # run: error handling
        err_msg = run_results.get("error", None)
        if err_msg:
            job_results = format_error_results(
                driver, errors.JobEngineDriverRunError, err_msg
            )
            return job_results, driver, transpiler, mapping_dict

        # prepare job_results
        job_results["results"] = run_results["results"]
        job_results["metadata"] = run_results["metadata"]
        if "raw_results" in run_results:
            job_results["metadata"]["raw_results"] = run_results["raw_results"]

    return job_results, driver, transpiler, mapping_dict


def run_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
    monitor_info,
):
    """Run code.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        job_info: job info
        driver: driver
        transpiler: transpiler
        monitor_info: monitor info

    Returns:
        job results
    """
    job_results = {}
    mapping_dict = None
    job_data = job_info["data"]
    code_type = job_data["code_type"]

    # init driver (init only once in a flow)
    if not driver:
        future_driver = init_driver.submit(
            job_info["driver"],
            job_data["driver_options"],
            job_info["device"],
            job_info,
        )
        driver_task_result = future_driver.result()
        # init driver: error handling
        err_msg = driver_task_result.get("error", None)
        if err_msg:
            return (
                format_error_results(
                    None, errors.JobEngineDriverInitError, err_msg
                ),
                driver,
                transpiler,
                mapping_dict,
            )
        driver = driver_task_result["driver"]
        logger.info(f"Init driver: {driver.name}")
        monitor_info["driver"] = driver

    # init transpiler (init only once in a flow)
    if not transpiler:
        future_transpiler = init_transpiler.submit(
            job_info["transpiler"],
            job_data.get("transpiler_options", None),
        )
        transpiler_task_result = future_transpiler.result()
        # init transpiler: error handling
        err_msg = transpiler_task_result.get("error", None)
        if err_msg:
            return (
                format_error_results(
                    driver, errors.JobEngineTranspilerInitError, err_msg
                ),
                driver,
                transpiler,
                mapping_dict,
            )
        transpiler = transpiler_task_result["transpiler"]
        logger.info(
            f"Init transpiler: {transpiler.name} ({transpiler.alias_name})"
        )

    if code_type == Constant.CODE_TYPE_QUBO:
        job_results, driver, transpiler, mapping_dict = run_qubo_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
        )
    elif code_type in Constant.CODE_TYPES_ALL_QASM:
        job_results, driver, transpiler, mapping_dict = run_circuit_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
        )
    return job_results, driver, transpiler, mapping_dict


def run_qubo_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
):
    """Run qubo code.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        job_info: job info
        driver: driver
        transpiler: transpiler

    Returns:
        job results
    """
    job_results = {}
    mapping_dict = None
    job_id = job_info["data"]["job_id"]
    max_qubits = driver.get_max_qubits()
    enable_subqubo = driver.get_enable_subqubo()
    enable_prec_reduce = driver.get_enable_prec_reduce()
    qubo_matrix = src_code_dict[f"{job_id}-{source_code_index}"]
    max_precision_value = 2 ** (Constant.MAX_QUBO_BIT_WIDTH - 1) - 1
    # Check if the matrix is valid
    success, err_msg = check_matrix(qubo_matrix)
    if not success and err_msg:
        return (
            format_error_results(
                driver, errors.JobEngineCheckMatrixError, err_msg
            ),
            driver,
            transpiler,
            mapping_dict,
        )
    # Determine in advance whether precision reduction is necessary
    success, err_msg = check_qubo_matrix_bit_width(
        np.array(qubo_matrix), Constant.MAX_QUBO_BIT_WIDTH
    )
    if not success:
        if err_msg:
            return (
                format_error_results(
                    driver, errors.JobEngineCheckWidthError, err_msg
                ),
                driver,
                transpiler,
                mapping_dict,
            )
        if not enable_prec_reduce:
            err_msg = (
                f"The element values in the QUBO matrix "
                f"does not meet {Constant.MAX_QUBO_BIT_WIDTH}-bit signed. "
                f"Consider using enable_prec_reduce."
            )
            return (
                format_error_results(
                    driver, errors.JobEngineCheckWidthError, err_msg
                ),
                driver,
                transpiler,
                mapping_dict,
            )

    ising_matrix = qubo_matrix_to_ising_matrix(np.array(qubo_matrix))
    scaled_ising_matrix = scale_to_integer_matrix(ising_matrix)
    # If the QUBO matrix is to be reduced in precision,
    # calculate the total number of spin bits.
    _, _, total_spins_num = get_spins_num(
        scaled_ising_matrix, max_precision_value
    )
    # Need subqubo and precision reduction
    if total_spins_num > max_qubits + 1:
        if not enable_subqubo:
            qubo_matrix_length = total_spins_num - 1
            driver_name = driver.get_name()
            err_msg = (
                f"Current QUBO matrix scales to {qubo_matrix_length} bits "
                f"after precision reduction, exceeding Device {driver_name}'s"
                f" {max_qubits}-bit limit. Consider using enable_subqubo."
            )
            return (
                format_error_results(
                    driver, errors.JobEngineQubitLimitExceededError, err_msg
                ),
                driver,
                transpiler,
                mapping_dict,
            )
        job_results, driver, transpiler, mapping_dict = run_subqubo_code(
            max_qubits,
            total_spins_num,
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
        )
    # No need to subqubo and precision reduction
    elif total_spins_num == len(qubo_matrix) + 1:
        job_results, driver, transpiler, mapping_dict = _run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
        )
    # No need subqubo, but need precision reduction
    else:
        precision_ising_matrix, last_idx, _ = precision_reduction(
            ising_matrix, Constant.MAX_QUBO_BIT_WIDTH
        )
        precision_qubo_matrix = ising_matrix_to_qubo_matrix(
            precision_ising_matrix
        )
        src_code_dict[f"{job_id}-{source_code_index}"] = precision_qubo_matrix
        job_results, driver, transpiler, mapping_dict = _run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
        )
        if job_results["results"]:
            job_results = process_qubo_solution(
                job_results, last_idx, np.array(qubo_matrix)
            )
    if job_results:
        job_results["num_qubits"] = len(qubo_matrix)
    return job_results, driver, transpiler, mapping_dict


def run_subqubo_code(
    max_qubits,
    total_spins_num,
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
):
    job_results = {}
    mapping_dict = None
    job_id = job_info["data"]["job_id"]
    qubo_matrix = src_code_dict[f"{job_id}-{source_code_index}"]
    logger.info("start subqubo")
    subqubo_size = int(
        np.floor(max_qubits * len(qubo_matrix) / total_spins_num)
    )
    if subqubo_size <= max_qubits / 4:
        err_msg = (
            f"SubQUBO size {subqubo_size} below threshold "
            f"{int(max_qubits / 4)}."
        )
        return (
            format_error_results(
                driver, errors.JobEnginePrecisionTooHighError, err_msg
            ),
            driver,
            transpiler,
            mapping_dict,
        )
    subqubo.set_subqubo_size(subqubo_size)
    subqubo.set_qubo_matrix(np.array(qubo_matrix))
    solution_pool = subqubo.init_instance_pool()
    # find best_solution from solution's pool
    best_solution, _ = subqubo.find_best_solution(solution_pool)
    converged_num = 0
    cycles_num = 0
    sub_job_results = []
    while converged_num <= subqubo.get_max_converged_num():
        cycles_num += 1
        solution_pool = subqubo.optimize_solution_pool(solution_pool)
        n_e_pools = subqubo.create_sub_solution_pools(solution_pool)
        new_solutions = []
        for i in range(subqubo.N_E):
            subqubo_matrix, tmp_solution, extracted_index = (
                subqubo.construct_subqubo(n_e_pools[i])
            )
            # Check if subqubo needs precision reduction
            success, err_msg = check_qubo_matrix_bit_width(
                np.array(subqubo_matrix), Constant.MAX_QUBO_BIT_WIDTH
            )
            need_precision_reduction = False
            last_idx = []
            if not success:
                if err_msg:
                    return (
                        format_error_results(
                            driver, errors.JobEngineCheckWidthError, err_msg
                        ),
                        driver,
                        transpiler,
                        mapping_dict,
                    )
                # Accuracy below target and reduce precision
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
            src_sub_code_dict = {}
            sub_source_code_index = (
                f"{str(source_code_index)}-{str(cycles_num)}-{str(i)}"
            )
            src_sub_code_dict[job_id + sub_source_code_index] = subqubo_matrix
            sub_job_results, driver, transpiler, mapping_dict = _run_code(
                sub_source_code_index,
                src_sub_code_dict,
                job_info,
                driver,
                transpiler,
            )
            logger.info(sub_job_results["results"])
            if sub_job_results["results"]:
                subqubo_solution = (
                    sub_job_results.get("results", {})
                    .get("out_data", [{}])[0]
                    .get("solutionVector", [])
                )
                if need_precision_reduction:
                    subqubo_solution = np.array(subqubo_solution)[
                        last_idx[:-1]
                    ]
                solution = subqubo.merge_solution(
                    tmp_solution, subqubo_solution, extracted_index
                )
                new_solutions.append(solution)
        x_best, solution_pool = subqubo.update_solution_pool(
            solution_pool, new_solutions
        )
        if best_solution.energy > x_best.energy:
            best_solution.solution = x_best.solution.copy()
            best_solution.energy = x_best.energy
            converged_num = 0
        elif best_solution.energy <= x_best.energy:
            converged_num = converged_num + 1
    job_results = sub_job_results
    job_results["results"] = {}
    job_results["results"]["out_data"] = []
    for i in range(len(solution_pool)):
        solution = {}
        solution["result"] = i + 1
        solution["quboValue"] = solution_pool[i].energy
        solution["solutionVector"] = solution_pool[i].solution.tolist()
        job_results["results"]["out_data"].append(solution)
    return job_results, driver, transpiler, mapping_dict


def run_circuit_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
):
    """Run circuit code.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        job_info: job info
        driver: driver
        transpiler: transpiler

    Returns:
        job results
    """
    job_results = {}
    job_id = job_info["data"]["job_id"]
    code_type = job_info["data"]["code_type"]
    # device's max support qubits
    max_qubits = driver.get_max_qubits()
    enable_wirecut = driver.get_enable_wirecut()
    # wirecut qubit width
    wirecut_qubit_width = driver.get_wirecut_qubit_width()
    driver_name = driver.get_name()
    logger.info(f"driver max qubits: {max_qubits}")
    src_code = src_code_dict[f"{job_id}-{source_code_index}"]
    try:
        parse_result = transpiler.parse(src_code_dict, code_type)
        # number of qubits in the circuit
        num_qubits = parse_result[f"{job_id}-{source_code_index}"][0]
    except Exception as e:
        err_msg = f"Src code: {src_code} compile failed: {str(e)}"
        return (
            format_error_results(
                driver, errors.JobEngineCompileError, err_msg
            ),
            driver,
            transpiler,
            None,
        )
    if not enable_wirecut:
        # Check if current circuit qubits exceeds device max support qubits
        if num_qubits > max_qubits:
            err_msg = (
                f"The current circuit is {num_qubits}-bit, exceeding Device "
                f"{driver_name}'s {max_qubits}-bit limit. Consider using "
                f"enable_wirecut option in --driver-options."
            )
            return (
                format_error_results(
                    driver, errors.JobEngineQubitLimitExceededError, err_msg
                ),
                driver,
                transpiler,
                None,
            )
        # Run the circuit
        else:
            job_results, driver, transpiler, mapping_dict = _run_code(
                source_code_index,
                src_code_dict,
                job_info,
                driver,
                transpiler,
            )
    else:
        # Check if wirecut qubit width exceeds device max support qubits
        if wirecut_qubit_width > max_qubits:
            err_msg = (
                f"The current device: {driver_name}'s {max_qubits}-bit limit "
                f"and wirecut qubit width is {wirecut_qubit_width}. Consider "
                f"setting wirecut qubit width less than or equal to device's "
                f"max support qubits."
            )
            return (
                format_error_results(
                    driver,
                    errors.JobEngineWirecutQubitLimitExceededError,
                    err_msg,
                ),
                driver,
                transpiler,
                None,
            )
        # Check if wirecut qubit width exceeds current circuit qubits
        elif wirecut_qubit_width > num_qubits:
            err_msg = (
                f"The current circuit is {num_qubits}-bit, and wirecut qubit "
                f"width is {wirecut_qubit_width}. Consider setting wirecut "
                f"qubit width less than or equal to circuit's qubits."
            )
            return (
                format_error_results(
                    driver,
                    errors.JobEngineWirecutQubitLimitExceededError,
                    err_msg,
                ),
                driver,
                transpiler,
                None,
            )
        # Run the circuit cutting
        else:
            job_results, driver, transpiler, mapping_dict = (
                run_circuit_cutting_code(
                    source_code_index,
                    src_code_dict,
                    num_qubits,
                    job_info,
                    driver,
                    transpiler,
                )
            )
    return job_results, driver, transpiler, mapping_dict


def run_circuit_cutting_code(
    source_code_index,
    src_code_dict,
    num_qubits,
    job_info,
    driver,
    transpiler,
):
    """Run circuit cutting code.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        num_qubits: number of qubits
        job_info: job info
        driver: driver
        transpiler: transpiler

    Returns:
        job results
    """
    job_id = job_info["data"]["job_id"]
    src_code = src_code_dict[f"{job_id}-{source_code_index}"]
    max_qubits = driver.get_max_qubits()
    wirecut_qubit_width = driver.get_wirecut_qubit_width()
    if not isinstance(wirecut_qubit_width, int):
        wirecut_qubit_width = 0
    # If wirecut qubit width is not set, set it to max qubits.
    if wirecut_qubit_width == 0:
        wirecut_qubit_width = max_qubits
    # If wirecut qubit width is less than 2, return error since it's
    # meaningless to cut circuit into subcircuits with 1 or 0 qubit.
    elif wirecut_qubit_width < 2:
        err_msg = (
            f"wirecut qubit width is {wirecut_qubit_width} and should "
            f"be greater than 2"
        )
        return (
            format_error_results(
                driver, errors.JobEngineWirecutQubitLimitExceededError, err_msg
            ),
            driver,
            transpiler,
            None,
        )
    is_complete_reconstruction = True
    max_memory = 2 ** (num_qubits)
    if num_qubits > Constant.COMPLETE_RECONSTRUCTION_THRESHOLD:
        is_complete_reconstruction = False
        max_memory = Constant.DD_MAX_MEMORY
    # Step 1: Generate all subcircuits
    try:
        _, subcircuits, cut_wire = (
            generate_all_variant_subcircuits_for_execute(
                max_subcircuit_width=wirecut_qubit_width,
                qasm=src_code,
                max_memory=max_memory,
                is_complete_reconstruction=is_complete_reconstruction,
            )
        )
    except Exception as e:
        err_msg = f"Generate all variant subcircuits failed: {str(e)}"
        return (
            format_error_results(
                driver, errors.JobEngineCircuitCuttingError, err_msg
            ),
            driver,
            transpiler,
            None,
        )
    # Step 2: Execute all subcircuits
    result_cache = SubcircuitResultCache.from_job_info(job_info)
    sub_results = []
    mapping_dict = None
    job_results = {
        "results": None,
        "num_qubits": num_qubits,
        "metadata": {"status": Constant.JOB_STATUS_COMPLETED},
        "profiling": {},
        "sub_results": None,
    }
    for i in range(len(subcircuits)):
        cached_result = result_cache.get(subcircuits[i], job_info)
        if cached_result is not None:
            logger.info(f"Subcircuit result cache hit: index={i}")
            sub_results.append(counts_to_probs(cached_result))
            continue

        src_sub_code_dict = {}
        sub_source_code_index = f"{str(source_code_index)}-{str(i)}"
        src_sub_code_dict[job_id + sub_source_code_index] = subcircuits[i]
        job_results, driver, transpiler, mapping_dict = _run_code(
            sub_source_code_index,
            src_sub_code_dict,
            job_info,
            driver,
            transpiler,
        )
        if job_results["metadata"]["status"] != "COMPLETED":
            return job_results, driver, transpiler, mapping_dict
        if (
            job_results["metadata"]["status"] == "COMPLETED"
            and job_results["results"] is not None
        ):
            result_cache.set(subcircuits[i], job_info, job_results["results"])
            sub_result = counts_to_probs(job_results["results"])
            sub_results.append(sub_result)
    # Step 3: Reconstruct probability distribution
    try:
        prob, _ = reconstruct_probability_distribution_wire_cut(
            cut_wire,
            sub_results,
            is_complete_reconstruction=is_complete_reconstruction,
        )
    except Exception as e:
        err_msg = (
            f"Reconstruct subcircuits probability distribution "
            f"failed: {str(e)}"
        )
        return (
            format_error_results(
                driver, errors.JobEngineReconProbError, err_msg
            ),
            driver,
            transpiler,
            mapping_dict,
        )
    job_results["num_qubits"] = num_qubits
    job_results["results"] = probs_to_dict(prob)
    return job_results, driver, transpiler, mapping_dict


def counts_to_probs(count_dict):
    """Convert the quantum state count dictionary into a probability array.

    Args:
        count_dict (dict[str, int]): quantum state count dictionary.

    Returns:
        np.ndarray: Probability array sorted in binary order.
    """
    if not count_dict:
        return []
    first_key = next(iter(count_dict))
    n = len(first_key)
    total_states = 2**n
    probs = np.zeros(total_states)
    total_counts = sum(count_dict.values())
    if total_counts == 0:
        return probs
    for binary_str, count in count_dict.items():
        idx = int(binary_str, 2)
        probs[idx] = count / total_counts
    return probs


def probs_to_dict(prob_array):
    """Generic probability array to dictionary function.

    Args:
        prob_array (list): Probability list

    Returns:
        dict: Probability dictionary
    """
    if prob_array is None or len(prob_array) == 0:
        return {}
    n = len(prob_array)
    bits = 0
    while (1 << bits) < n:
        bits += 1
    if (1 << bits) != n:
        bits = max(bits, (n - 1).bit_length())
    result = {}
    for i, prob in enumerate(prob_array):
        if abs(prob) > 1e-12:
            binary_str = format(i, f"0{bits}b")
            result[binary_str] = float(prob)
    return result


def flow_parse(src_code_dict, transpiler, code_type):
    """Flow: parse.

    Args:
        src_code_dict: src_code_dict
        transpiler: transpiler
        code_type(str): code_type

    Returns:
        results, profiling_time
    """
    # record parse start_time
    parse_started_at = time.time()

    # parser
    parse_task = parse.submit(
        src_code_dict,
        transpiler,
        code_type,
        wait_for=[init_driver, init_transpiler],
    )
    parse_task_result = parse_task.result()
    parse_ended_at = time.time()
    parse_duration = parse_ended_at - parse_started_at
    parse_profiling = {
        "parse_started_at": parse_started_at,
        "parse_ended_at": parse_ended_at,
        "parse_duration": parse_duration,
    }
    return parse_task_result, parse_profiling


def flow_transpile(parsed_src_code, transpiler, driver):
    """Flow: transpile.

    Args:
        parsed_src_code: parsed_src_code
        transpiler: transpiler
        driver: driver

    Returns:
        results, profiling_time
    """
    # record transpile start_time
    transpile_started_at = time.time()

    # transpile codes
    transpile_task = transpile.submit(
        parsed_src_code,
        driver,
        transpiler,
        wait_for=[init_driver, init_transpiler, parse],
    )
    transpile_task_results = transpile_task.result()

    # record transpile end_time
    transpile_ended_at = time.time()
    transpile_duration = transpile_ended_at - transpile_started_at
    transpile_profiling = {
        "transpile_started_at": transpile_started_at,
        "transpile_ended_at": transpile_ended_at,
        "transpile_duration": transpile_duration,
    }
    return transpile_task_results, transpile_profiling


def flow_task_monitor(monitor_info):
    """Flow: task monitor.

    Args:
        monitor_info: monitor info
    """
    task_monitor.submit(monitor_info)


def flow_run_driver(job_info, num_qubits, driver, data):
    """Flow: run driver.

    Args:
        job_info: job info
        num_qubits: number of qubits
        driver: driver
        data: data

    Returns:
        results, profiling_time
    """
    # call run() in driver
    # record driver_run start_time
    driver_run_started_at = time.time()

    wait_for = [init_driver, transpile]

    run_task = driver_run.submit(
        job_info, driver, num_qubits, data, wait_for=wait_for
    )

    run_task_results = run_task.result()

    # record driver_run end_time
    driver_run_ended_at = time.time()
    driver_run_duration = driver_run_ended_at - driver_run_started_at
    driver_run_profiling = {
        "driver_run_started_at": driver_run_started_at,
        "driver_run_ended_at": driver_run_ended_at,
        "driver_run_duration": driver_run_duration,
    }
    return run_task_results, driver_run_profiling


def format_run_results(driver, job_id, data_index):
    """Format run results.

    Args:
        driver: driver
        job_id: job id
        data_index: data index

    Returns:
        formatted results
    """
    results = None
    ended_at = None
    job_status = None
    driver_results_fetch_mode = None

    if driver:
        driver_results_fetch_mode = driver.results_fetch_mode

    job_results = {
        "results": None,
        "metadata": {
            "results_fetch_mode": driver_results_fetch_mode,
            "status": None,
            "ended_at": None,
        },
        "error": None,
    }

    if driver_results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
        # sync mode: get results immediately
        results = driver.get_results(job_id, data_index)
        raw_results = driver.get_raw_results(job_id, data_index)
        job_status = Constant.JOB_STATUS_COMPLETED
        ended_at = Library.get_current_datetime().isoformat()
        machine_profiling = driver.get_machine_profiling(job_id, data_index)
    elif driver_results_fetch_mode == Constant.RESULTS_FETCH_MODE_ASYNC:
        # async mode: get results in the async set-job-results call
        job_status = Constant.JOB_STATUS_RUNNING

    job_results["results"] = results
    if raw_results:
        job_results["raw_results"] = raw_results
    job_results["metadata"]["status"] = job_status
    job_results["metadata"]["ended_at"] = ended_at
    job_results["machine_profiling"] = machine_profiling
    return job_results


def format_error_results(driver, err_cls, err_msg):
    """Format error results.

    Args:
        driver: driver
        err_cls: error class
        err_msg: error message

    Returns:
        formatted error results
    """
    driver_results_fetch_mode = None

    if driver:
        driver_results_fetch_mode = driver.results_fetch_mode

    job_results = {
        "results": None,
        "metadata": {
            "results_fetch_mode": driver_results_fetch_mode,
            "status": None,
            "ended_at": None,
        },
        "profiling": {},
        "error": None,
    }

    err = err_cls(err_msg)
    job_results["metadata"]["status"] = Constant.JOB_STATUS_FAILED
    job_results["metadata"]["ended_at"] = (
        Library.get_current_datetime().isoformat()
    )
    job_results["error"] = {
        "code": err.get_error_code(),
        "message": err.get_err_msgs(),
    }
    driver_name = "Unknown driver"
    if driver:
        driver_name = driver.name
    logger.error(f"{err.get_err_msgs()} [{driver_name}]")
    return job_results
