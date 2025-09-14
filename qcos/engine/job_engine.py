#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
from datetime import datetime
import importlib
import signal
import sys
import time
from typing import Any, List, Optional, Dict

from prefect import flow, task, pause_flow_run
from prefect.artifacts import (create_progress_artifact,
                               update_progress_artifact)
from prefect.input import RunInput
from loguru import logger

from qcos.common.config import Config
from qcos.common.constant import Constant
from qcos.common import errors
from qcos.common.library import Library
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst


# 配置 Loguru
# pylint: disable=duplicate-code
logger.add(
    Config.PREFECT_LOG_FILE,
    rotation=Constant.PREFECT_JOB_LOG_ROTATION,
    retention=Constant.PREFECT_JOB_LOG_RETENTION,
    format=Constant.PREFECT_JOB_LOG_FORMAT
)


class AggregationInput(RunInput):
    is_parent: bool
    sub_jobs: Optional[Dict] = None
    sub_results: Optional[List[Any]] = None


class SourceCodeInfo:
    aggregation_type: str
    src_code_list: List[Dict]


@task(persist_result=False)
def init_driver(driver_info, driver_options, device):
    """Init driver from driver_info

    Args:
        driver_info: driver info
        driver_options: driver options
        device: device info

    Returns:
        driver
    """

    try:
        driver_module = importlib.import_module(driver_info["module_name"])
        driver_class = getattr(driver_module, driver_info["class_name"])
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

        # copy cfgs to transpiler cfg inst
        if driver.enable_transpiler:
            transpiler_configs = device_configs.get("transpiler", None)
            trans_cfg_inst.set_max_qubits(driver.get_max_qubits())
            trans_cfg_inst.set_tech_type(driver.tech_type)
            trans_cfg_inst.set_driver_name(driver.get_name())
            if transpiler_configs:
                qpu_configs = transpiler_configs.get("qpu_configs", None)
                decomposition_rule = transpiler_configs.get(
                    "decomposition_rule", None)
                trans_cfg_inst.set_qpu_cfg(qpu_configs)
                trans_cfg_inst.set_decompose_rule(decomposition_rule)
        return {"driver": driver, "error": None}
    except Exception as e:
        return {"driver": None, "error": ValueError(str(e))}


@task(persist_result=False)
def init_transpiler(transpiler_class_info, transpiler_options):
    """Init transpiler instance

    Args:
        transpiler_class_info: transpiler class info
        transpiler_options: transpiler options

    Returns:
        transpiler
    """

    try:
        transpiler_module = importlib.import_module(
            transpiler_class_info["module_name"])
        transpiler_class = getattr(transpiler_module,
                                   transpiler_class_info["class_name"])
        transpiler = transpiler_class()
        if transpiler_options:
            transpiler.update_transpiler_options(transpiler_options)
        return {"transpiler": transpiler, "error": None}
    except Exception as e:
        return {"transpiler": None, "error": ValueError(str(e))}


@task
def task_monitor(monitor_info):
    driver = None
    last_job_progress = 0
    while monitor_info["running"]:
        if not driver:
            driver = monitor_info["driver"]
        if driver:
            job_progress = int(monitor_info["progress"] +
                               int(driver.get_progress() /
                                   monitor_info["source_code_count"]))
            if last_job_progress != job_progress:
                # update flow
                update_progress(monitor_info['artifact_id'], job_progress)
            last_job_progress = job_progress
        time.sleep(1)
    update_progress(monitor_info['artifact_id'], 100)


@task(persist_result=False)
def parse(src_code_dict, transpiler):
    """Parse task

    Args:
        src_code_dict: src_code_dict
        transpiler: transpiler

    Returns:
        parsed results
    """
    try:
        parsed_src_code = transpiler.parse(src_code_dict)
        logger.info(f"final parsed src code: {parsed_src_code}")
        return {"parsed_src_code": parsed_src_code,
                "error": None}
    except Exception as e:
        return {"parsed_src_code": None,
                "error": ValueError(str(e))}


@task(persist_result=False)
def transpile(parsed_gates, driver, transpiler):
    """Transpile task

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
            parsed_gates, supp_basis_gates)
        num_qubits = transpiler.total_qubits
        logger.info(f"final transpiled_result: {transpile_results}")
        return {"transpile_results": transpile_results,
                "mapping_dict": mapping_dict,
                "num_qubits": num_qubits,
                "error": None}
    except Exception as e:
        return {"transpile_results": None,
                "mapping_dict": None,
                "num_qubits": num_qubits,
                "error": ValueError(str(e))}


@task(persist_result=False)
def driver_run(job_info, driver, num_qubits, data):
    """Driver: run job

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
        if dry_run:
            logger.info(
                f"dry_run: job_id: {job_id}, num_qubits: {num_qubits}, "
                f"data: {data}, data_type: {data_type}, shots: {shots}")
            driver.dry_run(job_id, num_qubits, data,
                           data_type=data_type, shots=shots)
        else:
            logger.info(
                f"run: job_id: {job_id}, num_qubits: {num_qubits}, "
                f"data: {data}, data_type: {data_type}, shots: {shots}")
            driver.run(job_id, num_qubits, data,
                       data_type=data_type, shots=shots)

        return format_run_results(driver, job_id, data["index"])
    except Exception as e:
        return {"results": None, "metadata": {}, "error": ValueError(str(e))}


def driver_cancel(job_id, driver):
    """Driver: cancel job

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


async def job_callback(flow, flow_run, state):
    """Job callback

    Args:
        flow: flow
        flow_run: flow run
        state: flow state
    """
    job_id = flow_run.name  # use name as job uuid
    job_status = Constant.JOB_STATUS_COMPLETED
    is_failed = False
    flow_state_name = state.name.upper()
    parameters = flow_run.parameters
    results = flow_run.state.result()
    results_fetch_mode_sync = False
    callbacks = Library.get_nested_dict_value(
        parameters, "job_info", "data", "callbacks", default=None)
    backend = Library.get_nested_dict_value(
        parameters, "job_info", "data", "backend", default=None)
    if not callbacks:
        return

    if flow_state_name == Constant.PREFECT_STATE_CANCELLING:
        job_status = Constant.JOB_STATUS_CANCELLED
        results = None
        results_fetch_mode_sync = True

    if results:
        for result in results:
            results_fetch_mode = Library.get_nested_dict_value(
                result, "metadata", "results_fetch_mode", default=None)
            status = Library.get_nested_dict_value(
                result, "metadata", "status", default=None)
            if status != Constant.JOB_STATUS_COMPLETED:
                is_failed = True
            if results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
                results_fetch_mode_sync = True
    if callbacks and results_fetch_mode_sync:
        # if job_info contains callback list and driver is in sync mode
        # run async callback
        if is_failed:
            job_status = Constant.JOB_STATUS_FAILED

        data = {
            "job_id": job_id,
            "job_status": job_status,
            "backend": backend,
            "results": results
        }
        success, err_msg = await Library.async_run_callbacks(
            data, callbacks)
        if not success:
            logger.error(f"Callback Error: {err_msg}")


def register_signals(job_id, monitor):
    """Register signal handlers

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
        driver = monitor["driver"]
        driver_cancel(job_id, driver)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handle_sigterm)


def update_progress(artifact_id, progress):
    """Update progress

    Args:
        artifact_id: artifact id
        progress: progress
    """
    update_progress_artifact(
        artifact_id=artifact_id,
        progress=progress
    )


def create_src_code_info(job_data):
    """Create src code info

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
            src_code_map[job_id + "-" + str(src_code_index)] = (
                source_code)
            src_code_index += 1
            src_code_info.src_code_list.append(src_code_map)
    else:
        src_code_info.aggregation_type = job_data["circuit_aggregation"]
        src_code_info.src_code_list = []
        src_code_map = {}
        for source_code in source_code_list:
            if len(src_code_map) >= Constant.MAX_AGGREGATION_JOBS:
                src_code_info.src_code_list.append(
                    src_code_map)
                src_code_map.clear()
                continue
            src_code_map[job_id + "-" + str(src_code_index)] = (
                source_code)
            src_code_index += 1

        if len(src_code_map) != 0:
            src_code_info.src_code_list.append(src_code_map)
    return src_code_info


def update_src_code_info(src_code_info, aggregation_info):
    """Update src code info

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
    for key, value in aggregation_info.sub_jobs.items():
        if len(src_code_map) >= Constant.MAX_AGGREGATION_JOBS:
            src_code_info.src_code_list.append(
                src_code_map)
            src_code_map.clear()
            continue
        src_code = value["job_info"]["data"]["source_code"][0]
        src_code_map[key + "-0"] = src_code

    if len(src_code_map) != 0:
        src_code_info.src_code_list.append(src_code_map)
    return src_code_info


def get_src_code_cnt(src_code_info: SourceCodeInfo):
    """Get total src code count

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
    """Split dict

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
    """Get internal aggregated results

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

        aggregated_results.append(single_result)

    return aggregated_results


def get_external_aggregated_results(job_results, mapping_dict):
    """Get external aggregated results

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
        single_result = {"results": value,
                         "num_qubits": len(next(iter(value.keys()))),
                         "metadata": job_results["metadata"],
                         "profiling": job_results["profiling"]}
        # TODO(all) workaround code, need to improve it.
        end_time = single_result["metadata"]["end_date"]
        if isinstance(end_time, datetime):
            new_time = end_time.isoformat()
            single_result["metadata"]["end_date"] = new_time
        new_id = job_id.rsplit('-', 1)[0]
        sub_results[new_id] = single_result

    job_results["sub_results"] = sub_results
    return job_results


@flow(name="job_engine", persist_result=True,
      on_completion=[job_callback],
      on_failure=[job_callback],
      on_crashed=[job_callback],
      on_cancellation=[job_callback])
def job_flow(job_info):
    """Job flow

    Args:
        job_info: job info

    Returns:
        results
    """
    job_data = job_info["data"]
    job_id = job_data["job_id"]
    monitor_info = {
        "artifact_id": None,
        "running": True,
        "driver": None,
        "source_code_index": 0,
        "source_code_count": 0,
        "progress": -1
    }
    logger.info(f"Processing work flow: job_engine. "
                f"job_id: {job_id}, job_info: {job_info}")

    # register signals for job cancelling
    register_signals(job_id, monitor_info)

    # start task-monitor
    artifact_id = create_progress_artifact(progress=0.0, key=job_id)
    monitor_info["artifact_id"] = artifact_id
    flow_task_monitor(monitor_info)

    # handle aggregation jobs
    aggregation_info = None
    src_code_info = create_src_code_info(job_data)
    if src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL:
        # TODO(jidalong) handle timeout
        # circuit_aggregation(multi) tag flow run will automatically paused
        # here waiting for aggregation_info generated by task manager
        aggregation_info = pause_flow_run(
            wait_for_input=AggregationInput
        )
        logger.info(
            f"Process aggregation sub job, aggregation_info: "
            f"{aggregation_info}")

        # deal sub job
        if not aggregation_info.is_parent:
            monitor_info["source_code_count"] = 1
            monitor_info["progress"] = 100
            monitor_info["running"] = False
            return aggregation_info.sub_results
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
        monitor_info["progress"] = (percentage_base * source_code_index
                                    / source_code_count)
        job_results, driver, transpiler, mapping_dict = run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
            monitor_info)
        source_code_index += len(src_code_dict)

        # pylint: disable=line-too-long
        if src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_NONE:
            job_results_list.append(job_results)
        elif src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_EXTERNAL:
            aggregated_res = get_external_aggregated_results(job_results, mapping_dict)
            job_results_list.append(aggregated_res)
        else:
            aggregated_res = get_internal_aggregated_results(job_results, mapping_dict)
            job_results_list.extend(aggregated_res)
        # pylint: enable=line-too-long

    monitor_info["running"] = False
    return job_results_list


def run_code(source_code_index, src_code_dict, job_info,
             driver, transpiler, monitor_info):
    """Flow: run

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
    logger.info(f"Run source_code_index: {source_code_index}\n")

    transpile_results = None
    num_qubits = None
    job_data = job_info["data"]
    profiling_types = job_data.get("profiling", [])
    profiling_types = [] if profiling_types is None else profiling_types
    mapping_dict = None

    # init driver (init only once in a flow)
    if not driver:
        future_driver = init_driver.submit(job_info["driver"],
                                           job_data["driver_options"],
                                           job_info["device"])
        driver_task_result = future_driver.result()
        # init driver: error handling
        err_msg = driver_task_result.get("error", None)
        if err_msg:
            return format_error_results(
                None,
                errors.JobEngineDriverInitError,
                err_msg), driver, transpiler, mapping_dict
        driver = driver_task_result["driver"]
        logger.info(f"Init driver: {driver.name}")
        monitor_info["driver"] = driver

    # init transpiler (init only once in a flow)
    if not transpiler:
        if driver.enable_transpiler:
            future_transpiler = init_transpiler.submit(
                job_info["transpiler"],
                job_data.get("transpiler_options", None))
            transpiler_task_result = future_transpiler.result()
            # init transpiler: error handling
            err_msg = transpiler_task_result.get("error", None)
            if err_msg:
                return format_error_results(
                    driver,
                    errors.JobEngineTranspilerInitError,
                    err_msg), driver, transpiler, mapping_dict
            transpiler = transpiler_task_result["transpiler"]
            logger.info("Init transpiler: "
                        f"{transpiler.name} ({transpiler.alias_name})")

    job_results = {
        "results": None,
        "num_qubits": None,
        "metadata": None,
        "profiling": {},
        "sub_results": None
    }

    source_code = None
    if driver.enable_transpiler:
        # [flow_parse]
        parse_results, profiling_time = flow_parse(
            src_code_dict,
            transpiler,
            profiling_types
        )
        if profiling_time:
            job_results["profiling"][
                Constant.PROFILING_TYPE_DRIVER_PARSE] = profiling_time

        # parser: error handling
        err_msg = parse_results.get("error", None)
        if err_msg:
            job_results = format_error_results(driver,
                                               errors.JobEngineParseError,
                                               err_msg)
            return job_results, driver, transpiler, mapping_dict

        # [flow_transpile]
        transpile_task_results, profiling_time = flow_transpile(
            parse_results["parsed_src_code"],
            transpiler,
            driver,
            profiling_types
        )
        if profiling_time:
            job_results["profiling"][
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE] = profiling_time

        # transpile: error handling
        err_msg = transpile_task_results.get("error", None)
        mapping_dict = transpile_task_results.get("mapping_dict", None)
        if err_msg:
            job_results = format_error_results(driver,
                                               errors.JobEngineTranspileError,
                                               err_msg)
            return job_results, driver, transpiler, mapping_dict

        transpile_results = transpile_task_results.get("transpile_results", None) # pylint: disable=line-too-long
        num_qubits = transpile_task_results.get("num_qubits", None)
        if transpile_results is None or num_qubits is None:
            raise ValueError("unexpected transpile_results or num_qubits")
        job_results["num_qubits"] = num_qubits
    else:
        source_code = next(iter(src_code_dict.values()))

    if driver:
        # [flow_run_driver]
        data = {
            "index": source_code_index,
            "source_code": source_code,
            "transpile_results": transpile_results
        }
        run_results, profiling_time = flow_run_driver(
            job_info,
            num_qubits,
            driver,
            data,
            profiling_types
        )

        if profiling_time:
            job_results["profiling"][
                Constant.PROFILING_TYPE_DRIVER_RUN] = profiling_time

        # run: error handling
        err_msg = run_results.get("error", None)
        if err_msg:
            job_results = format_error_results(driver,
                                               errors.JobEngineDriverRunError,
                                               err_msg)
            return job_results, driver, transpiler, mapping_dict

        # prepare job_results
        job_results["results"] = run_results["results"]
        job_results["metadata"] = run_results["metadata"]

    return job_results, driver, transpiler, mapping_dict


def flow_parse(src_code_dict,
               transpiler,
               profiling_types):
    """Flow: parse

    Args:
        src_code_dict: src_code_dict
        transpiler: transpiler
        profiling_types: profiling types

    Returns:
        results, profiling_time
    """
    profiling_start = 0
    profiling_end = 0

    # record parse start_time
    if (Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_start = time.time()

    # parser
    parse_task = parse.submit(src_code_dict, transpiler,
        wait_for=[init_driver, init_transpiler])
    parse_task_result = parse_task.result()

    if (Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_end = time.time()

    profiling_time = profiling_end - profiling_start
    return parse_task_result, profiling_time


def flow_transpile(parsed_src_code,
                   transpiler,
                   driver,
                   profiling_types):
    """Flow: transpile

    Args:
        parsed_src_code: parsed_src_code
        transpiler: transpiler
        driver: driver
        profiling_types: profiling types

    Returns:
        results, profiling_time
    """
    profiling_start = 0
    profiling_end = 0

    # record transpile start_time
    if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_start = time.time()

    # transpile codes
    transpile_task = transpile.submit(
        parsed_src_code, driver, transpiler,
        wait_for=[init_driver, init_transpiler, parse])
    transpile_task_results = transpile_task.result()

    # record transpile end_time
    if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_end = time.time()
    profiling_time = profiling_end - profiling_start
    return transpile_task_results, profiling_time


def flow_task_monitor(monitor_info):
    """Flow: task monitor

    Args:
        monitor_info: monitor info
    """
    task_monitor.submit(monitor_info)


def flow_run_driver(job_info,
                    num_qubits,
                    driver,
                    data,
                    profiling_types):
    """Flow: run driver

    Args:
        job_info: job info
        num_qubits: number of qubits
        driver: driver
        data: data
        profiling_types: profiling types

    Returns:
        results, profiling_time
    """
    # call run() in driver
    profiling_start = 0
    profiling_end = 0

    # record driver_run start_time
    if (Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_start = time.time()

    wait_for = [init_driver]
    if driver.enable_transpiler:
        wait_for = [transpile]

    run_task = driver_run.submit(
        job_info, driver, num_qubits, data,
        wait_for=wait_for)

    run_task_results = run_task.result()

    # record driver_run end_time
    if (Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_end = time.time()

    profiling_time = profiling_end - profiling_start
    return run_task_results, profiling_time


def format_run_results(driver, job_id, data_index):
    """Format run results

    Args:
        driver: driver
        job_id: job id
        data_index: data index

    Returns:
        formatted results
    """
    results = None
    end_date = None
    job_status = None
    driver_results_fetch_mode = None

    if driver:
        driver_results_fetch_mode = driver.results_fetch_mode

    job_results = {
        "results": None,
        "metadata": {
            "results_fetch_mode": driver_results_fetch_mode,
            "status": None,
            "end_date": None
        },
        "error": None
    }

    if driver_results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
        # sync mode: get results immediately
        results = driver.get_results(job_id, data_index)
        job_status = Constant.JOB_STATUS_COMPLETED
        end_date = Library.get_current_datetime()
    elif driver_results_fetch_mode == Constant.RESULTS_FETCH_MODE_ASYNC:
        # async mode: get results in the async set-job-results call
        job_status = Constant.JOB_STATUS_RUNNING

    job_results["results"] = results
    job_results["metadata"]["status"] = job_status
    job_results["metadata"]["end_date"] = end_date

    return job_results


def format_error_results(driver, err_cls, err_msg):
    """Format error results

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
            "end_date": None
        },
        "error": None
    }

    err = err_cls(err_msg)
    job_results["metadata"]["status"] = Constant.JOB_STATUS_FAILED
    job_results["metadata"]["end_date"] = Library.get_current_datetime()
    job_results["error"] = {
        "code": err.get_error_code(),
        "message": err.get_err_msgs()
    }
    return job_results
