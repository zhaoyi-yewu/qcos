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

import asyncio
import copy
from datetime import datetime
import importlib
import numpy as np
import signal
import sys
import time
from typing import Any

from prefect import flow, task, pause_flow_run
from prefect.artifacts import (
    create_progress_artifact,
    update_progress_artifact,
)
from prefect.context import get_run_context
from prefect.input import RunInput
from loguru import logger

from wy_qcos.common.config import Config
from wy_qcos.common.constant import Constant
from wy_qcos.common import errors
from wy_qcos.common.library import Library
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
from wy_qcos.transpiler.cmss.compiler.parser import compile
from wy_qcos.transpiler.cmss.wirecut.cut_wire import (
    generate_all_variant_subcircuits_for_execute,
    reconstruct_probability_distribution_wire_cut,
)


def init_logger():
    # Config Loguru
    # pylint: disable=duplicate-code
    logger.add(
        Config.PREFECT_LOG_FILE,
        level="DEBUG" if Config.DEBUG else "INFO",
        rotation=f"{Config.LOG_ROTATE_MAX_SIZE_MB} MB",
        compression="gz" if Config.LOG_ROTATE_COMPRESSION else None,
        retention=Config.LOG_ROTATE_BACKUP_COUNT,
        format=Constant.PREFECT_JOB_LOG_FORMAT,
    )


class AggregationInput(RunInput):
    is_parent: bool
    sub_jobs: dict | None = None
    sub_results: list[Any] | None = None


class SourceCodeInfo:
    aggregation_type: str
    src_code_list: list[dict]


@task(persist_result=False)
def init_driver(driver_class_info, driver_options, device, job_info):
    """Init driver from driver_class_info.

    Args:
        driver_class_info: driver class info
        driver_options: driver options
        device: device info
        job_info: job info

    Returns:
        driver
    """
    job_data = job_info["data"]
    try:
        driver_module = importlib.import_module(
            driver_class_info["module_name"]
        )
        driver_class = getattr(driver_module, driver_class_info["class_name"])
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

        # init job
        remote_transpiler_configs = None
        if not job_data.get("dry_run", False):
            remote_transpiler_configs = driver.fetch_configs()

        # copy cfgs to transpiler cfg inst
        if driver.enable_transpiler:
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
    try:
        transpiler_module = importlib.import_module(
            transpiler_class_info["module_name"]
        )
        transpiler_class = getattr(
            transpiler_module, transpiler_class_info["class_name"]
        )
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
                # update flow
                update_progress(monitor_info["artifact_id"], job_progress)
            last_job_progress = job_progress
        time.sleep(1)
    update_progress(monitor_info["artifact_id"], 100)


@task(persist_result=False)
def parse(src_code_dict, transpiler):
    """Parse task.

    Args:
        src_code_dict: src_code_dict
        transpiler: transpiler

    Returns:
        parsed results
    """
    try:
        parsed_src_code = transpiler.parse(src_code_dict)
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
        if dry_run:
            driver.dry_run(
                job_id, num_qubits, data, data_type=data_type, shots=shots
            )
        else:
            driver.run(
                job_id, num_qubits, data, data_type=data_type, shots=shots
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
        driver = monitor["driver"]
        driver_cancel(job_id, driver)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_sigterm)


def update_progress(artifact_id, progress):
    """Update progress.

    Args:
        artifact_id: artifact id
        progress: progress
    """
    update_progress_artifact(artifact_id=artifact_id, progress=progress)


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
    for key, value in aggregation_info.sub_jobs.items():
        if len(src_code_map) >= Constant.MAX_AGGREGATION_JOBS:
            src_code_info.src_code_list.append(src_code_map)
            src_code_map.clear()
            continue
        src_code = value["job_info"]["data"]["source_code"][0]
        src_code_map[key + "-0"] = src_code

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
            "results": value,
            "num_qubits": len(next(iter(value.keys()))),
            "metadata": job_results["metadata"],
            "profiling": job_results["profiling"],
        }
        # TODO(all) workaround code, need to improve it.
        end_time = single_result["metadata"]["end_date"]
        if isinstance(end_time, datetime):
            new_time = end_time.isoformat()
            single_result["metadata"]["end_date"] = new_time
        new_id = job_id.rsplit("-", 1)[0]
        sub_results[new_id] = single_result

    job_results["sub_results"] = sub_results
    return job_results


@flow(
    persist_result=True,
    on_failure=[Library.job_callback],
    on_crashed=[Library.job_callback],
    on_cancellation=[Library.job_callback],
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
    job_data = job_info["data"]
    job_id = job_data["job_id"]
    profiling_code_start = 0
    callbacks = job_data.get("callbacks", None)
    monitor_info = {
        "artifact_id": None,
        "running": True,
        "driver": None,
        "source_code_index": 0,
        "source_code_count": 0,
        "progress": -1,
    }

    # init logger
    init_logger()
    logger.info(
        f"Processing work flow: job_engine. "
        f"job_id: {job_id}, job_info: {job_info}"
    )

    # register signals for job cancelling
    register_signals(job_id, monitor_info)

    # record parse start_time
    profiling_types = job_data.get("profiling", [])
    if profiling_types and (
        Constant.PROFILING_TYPE_CODE in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_code_start = time.time()

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
        aggregation_info = pause_flow_run(wait_for_input=AggregationInput)
        logger.info(
            f"Process aggregation sub job, aggregation_info: "
            f"{aggregation_info}"
        )

        # handle sub job
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
        if profiling_types and (
            Constant.PROFILING_TYPE_CODE in profiling_types
            or Constant.PROFILING_TYPE_ALL in profiling_types
        ):
            profiling_code_end = time.time()
            profiling_code_duration = profiling_code_end - profiling_code_start
            job_results["profiling"][Constant.PROFILING_TYPE_CODE] = (
                profiling_code_duration
            )

        # handle job aggregation
        if src_code_info.aggregation_type == Constant.AGGREGATION_TYPE_NONE:
            job_results_list.append(job_results)
        elif (
            src_code_info.aggregation_type
            == Constant.AGGREGATION_TYPE_EXTERNAL
        ):
            aggregated_res = get_external_aggregated_results(
                job_results, mapping_dict
            )
            job_results_list.append(aggregated_res)
        else:
            aggregated_res = get_internal_aggregated_results(
                job_results, mapping_dict
            )
            job_results_list.extend(aggregated_res)

    # handle completed/failed callbacks
    if callbacks:
        context = get_run_context()
        run_job_callback(context, job_results_list)

    # set monitor_info
    monitor_info["running"] = False

    return job_results_list


def _run_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
    monitor_info,
):
    """Flow: run.

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

    job_results = {
        "results": None,
        "num_qubits": None,
        "metadata": {"status": Constant.JOB_STATUS_RUNNING},
        "profiling": {},
        "sub_results": None,
    }

    source_code = None
    if driver.enable_transpiler:
        # [flow_parse]
        parse_results, profiling_time = flow_parse(
            src_code_dict, transpiler, profiling_types
        )
        if profiling_time:
            job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_PARSE] = (
                profiling_time
            )

        # parser: error handling
        err_msg = parse_results.get("error", None)
        if err_msg:
            job_results = format_error_results(
                driver, errors.JobEngineParseError, err_msg
            )
            return job_results, driver, transpiler, mapping_dict

        # [flow_transpile]
        transpile_task_results, profiling_time = flow_transpile(
            parse_results["parsed_src_code"],
            transpiler,
            driver,
            profiling_types,
        )
        if profiling_time:
            job_results["profiling"][
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE
            ] = profiling_time

        # transpile: error handling
        err_msg = transpile_task_results.get("error", None)
        mapping_dict = transpile_task_results.get("mapping_dict", None)
        if err_msg:
            job_results = format_error_results(
                driver, errors.JobEngineTranspileError, err_msg
            )
            return job_results, driver, transpiler, mapping_dict

        transpile_results = transpile_task_results.get(
            "transpile_results", None
        )
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
            "transpile_results": transpile_results,
        }

        run_results, profiling_time = flow_run_driver(
            job_info, num_qubits, driver, data, profiling_types
        )

        if profiling_time:
            job_results["profiling"][Constant.PROFILING_TYPE_DRIVER_RUN] = (
                profiling_time
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
        if driver.enable_transpiler:
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
            None,
            monitor_info,
        )
    elif code_type in Constant.CODE_TYPES_ALL_QASM:
        job_results, driver, transpiler, mapping_dict = run_circuit_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
            monitor_info,
        )
    return job_results, driver, transpiler, mapping_dict


def run_qubo_code(
    source_code_index,
    src_code_dict,
    job_info,
    driver,
    transpiler,
    monitor_info,
):
    """Run qubo code.

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
            monitor_info,
        )
    # No need to subqubo and precision reduction
    elif total_spins_num == len(qubo_matrix) + 1:
        job_results, driver, transpiler, mapping_dict = _run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            None,
            monitor_info,
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
            None,
            monitor_info,
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
    monitor_info,
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
                monitor_info,
            )
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
    monitor_info,
):
    """Run circuit code.

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
    job_id = job_info["data"]["job_id"]
    max_qubits = driver.get_max_qubits()
    enable_wirecut = driver.get_enable_wirecut()
    logger.info(f"driver max qubits: {max_qubits}")
    src_code = src_code_dict[f"{job_id}-{source_code_index}"]
    try:
        num_qubits, _ = compile(src_code)
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
    if num_qubits > max_qubits:
        if not enable_wirecut:
            driver_name = driver.get_name()
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
        job_results, driver, transpiler, mapping_dict = (
            run_circuit_cutting_code(
                source_code_index,
                src_code_dict,
                num_qubits,
                job_info,
                driver,
                transpiler,
                monitor_info,
            )
        )
    else:
        job_results, driver, transpiler, mapping_dict = _run_code(
            source_code_index,
            src_code_dict,
            job_info,
            driver,
            transpiler,
            monitor_info,
        )
    return job_results, driver, transpiler, mapping_dict


def run_circuit_cutting_code(
    source_code_index,
    src_code_dict,
    num_qubits,
    job_info,
    driver,
    transpiler,
    monitor_info,
):
    """Run circuit cutting code.

    Args:
        source_code_index: source code index
        src_code_dict: src code dictionary
        num_qubits: number of qubits
        job_info: job info
        driver: driver
        transpiler: transpiler
        monitor_info: monitor info

    Returns:
        job results
    """
    job_id = job_info["data"]["job_id"]
    src_code = src_code_dict[f"{job_id}-{source_code_index}"]
    max_qubits = driver.get_max_qubits()
    is_complete_reconstruction = False
    # Step 1: Generate all subcircuits
    try:
        _, subcircuits, cut_wire = (
            generate_all_variant_subcircuits_for_execute(
                max_subcircuit_width=max_qubits,
                qasm=src_code,
                max_memory=2 ** (num_qubits),
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
    sub_results = []
    for i in range(len(subcircuits)):
        src_sub_code_dict = {}
        sub_source_code_index = f"{str(source_code_index)}-{str(i)}"
        src_sub_code_dict[job_id + sub_source_code_index] = subcircuits[i]
        job_results, driver, transpiler, mapping_dict = _run_code(
            sub_source_code_index,
            src_sub_code_dict,
            job_info,
            driver,
            transpiler,
            monitor_info,
        )
        if job_results["metadata"]["status"] != "COMPLETED":
            return job_results, driver, transpiler, mapping_dict
        if (
            job_results["metadata"]["status"] == "COMPLETED"
            and job_results["results"] is not None
        ):
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


def flow_parse(src_code_dict, transpiler, profiling_types):
    """Flow: parse.

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
    if (
        Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_start = time.time()

    # parser
    parse_task = parse.submit(
        src_code_dict, transpiler, wait_for=[init_driver, init_transpiler]
    )
    parse_task_result = parse_task.result()

    if (
        Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_end = time.time()

    profiling_time = profiling_end - profiling_start
    return parse_task_result, profiling_time


def flow_transpile(parsed_src_code, transpiler, driver, profiling_types):
    """Flow: transpile.

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
    if (
        Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_start = time.time()

    # transpile codes
    transpile_task = transpile.submit(
        parsed_src_code,
        driver,
        transpiler,
        wait_for=[init_driver, init_transpiler, parse],
    )
    transpile_task_results = transpile_task.result()

    # record transpile end_time
    if (
        Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_end = time.time()
    profiling_time = profiling_end - profiling_start
    return transpile_task_results, profiling_time


def flow_task_monitor(monitor_info):
    """Flow: task monitor.

    Args:
        monitor_info: monitor info
    """
    task_monitor.submit(monitor_info)


def flow_run_driver(job_info, num_qubits, driver, data, profiling_types):
    """Flow: run driver.

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
    if (
        Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_start = time.time()

    wait_for = [init_driver]
    if driver.enable_transpiler:
        wait_for = [transpile]

    run_task = driver_run.submit(
        job_info, driver, num_qubits, data, wait_for=wait_for
    )

    run_task_results = run_task.result()

    # record driver_run end_time
    if (
        Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types
        or Constant.PROFILING_TYPE_ALL in profiling_types
    ):
        profiling_end = time.time()

    profiling_time = profiling_end - profiling_start
    return run_task_results, profiling_time


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
            "end_date": None,
        },
        "error": None,
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
            "end_date": None,
        },
        "profiling": {},
        "error": None,
    }

    err = err_cls(err_msg)
    job_results["metadata"]["status"] = Constant.JOB_STATUS_FAILED
    job_results["metadata"]["end_date"] = Library.get_current_datetime()
    job_results["error"] = {
        "code": err.get_error_code(),
        "message": err.get_err_msgs(),
    }
    return job_results


def run_job_callback(context, job_results_list):
    """Run job_callback.

    Args:
        context: context
        job_results_list: list of job results
    """
    current_flow = context.flow
    current_flow_run = context.flow_run
    current_flow_state = current_flow_run.state
    _job_results_list = asyncio.run(
        Library.job_callback(
            current_flow,
            current_flow_run,
            current_flow_state,
            results=job_results_list,
        )
    )
    return _job_results_list
