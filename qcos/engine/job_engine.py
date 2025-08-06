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

import importlib
import time
from typing import Any, List, Optional, Dict

from prefect import flow, task, pause_flow_run
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


@task(persist_result=False)
def init_driver(driver_info, driver_options):
    """
    Init driver from driver_info

    :param driver_info: driver info
    :param driver_options: driver options
    :return: driver
    """

    try:
        driver_module = importlib.import_module(driver_info["module_name"])
        driver_class = getattr(driver_module, driver_info["class_name"])
        driver = driver_class()
        driver.extra_configs = driver_info.get("extra_configs", {})
        # update driver options
        if driver_options:
            driver.update_driver_options(driver_options)

        # validate and copy extra_configs to qpu_configs
        success, err_msg = driver.validate_driver_configs()
        # error handling
        if not success:
            logger.error(err_msg)
            return {"driver": driver, "error": err_msg}
        # copy cfgs to trans cfg inst
        trans_cfg_inst.set_qpu_cfg(driver.get_qpu_configs())
        trans_cfg_inst.set_max_qubits(driver.get_max_qubits())
        trans_cfg_inst.set_decompose_rule(driver.get_decomposition_rule())
        trans_cfg_inst.set_tech_type(driver.tech_type)
        trans_cfg_inst.set_driver_name(driver.get_name())
        return {"driver": driver, "error": None}
    except Exception as e:
        return {"driver": None, "error": ValueError(str(e))}


@task(persist_result=False)
def init_transpiler(transpiler_class_info, transpiler_options):
    """
    Init transpiler instance

    :param transpiler_class_info: transpiler class info
    :param transpiler_options: transpiler options
    :return: transpiler
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


@task(persist_result=False)
def parse(source_code, transpiler):
    """
    parse

    :param source_code: source code
    :param transpiler: transpiler
    :return parsed gate list
    """

    num_qubits = None
    try:
        logger.info(f"source_code:\n{source_code}")
        parsed_gates = transpiler.parse(source_code)
        num_qubits = transpiler.num_qubits
        logger.info(f"final parsed gates: {parsed_gates}")
        return {"parsed_gates": parsed_gates, "num_qubits": num_qubits,
                "error": None}
    except Exception as e:
        return {"parsed_gates": None, "num_qubits": num_qubits,
                "error": ValueError(str(e))}


@task(persist_result=False)
def transpile(parsed_gates, driver, transpiler):
    """
    transpile

    :param parsed_gates: parsed gates
    :param driver: driver
    :param transpiler: transpiler
    :return basis gate list
    """
    # load qpu configs

    num_qubits = -1
    try:
        supp_basis_gates = driver.get_supported_basis_gates()
        transpile_results = transpiler.transpile(
            parsed_gates, supp_basis_gates)
        num_qubits = transpiler.num_qubits
        logger.info(f"final transpiled_result: {transpile_results}")
        return {"transpile_results": transpile_results,
                "num_qubits": num_qubits, "error": None}
    except Exception as e:
        return {"transpile_results": None, "num_qubits": num_qubits,
                "error": ValueError(str(e))}


@task(persist_result=False)
def run_driver(job_info, driver, num_qubits, data):
    """
    Run the driver

    :param job_info: job info
    :param driver: driver
    :param num_qubits: number of qubits
    :param data: data
    :return results
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


async def job_callback(flow, flow_run, state):
    """
    Job callback

    :param flow: flow
    :param flow_run: flow run
    :param state: flow state
    """
    job_id = flow_run.name  # use name as job uuid
    is_failed = False
    parameters = flow_run.parameters
    results = flow_run.state.result()
    results_fetch_mode_sync = False
    callbacks = Library.get_nested_dict_value(
        parameters, "job_info", "data", "callbacks", default=None)
    backend = Library.get_nested_dict_value(
        parameters, "job_info", "data", "backend", default=None)
    if not callbacks:
        return
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
        job_status = Constant.JOB_STATUS_FAILED if is_failed \
            else Constant.JOB_STATUS_COMPLETED
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


@flow(name="job_engine", persist_result=True,
      on_completion=[job_callback],
      on_failure=[job_callback],
      on_crashed=[job_callback],
      on_cancellation=[job_callback])
def job_flow(job_info):
    """
    Job flow

    :param job_info: job info
    :return results
    """

    job_data = job_info["data"]
    job_id = job_data["job_id"]
    logger.info(f"Processing work flow: job_engine. "
                f"job_id: {job_id}, job_info: {job_info}")

    if job_data["enable_circuit_aggregation"]:
        # TODO(jidalong) handle timeout
        # enable_circuit_aggregation tag flow run will automatically paused
        # here waiting for aggregation_info generated by task manager
        aggregation_info = pause_flow_run(
            wait_for_input=AggregationInput
        )

        logger.info(
            f"Process aggregation sub job, aggregation_info: "
            f"{aggregation_info}")
        job_results = {"metadata": {}, "profiling": {}, "results": None,
                       "sub_results": None}

        # deal sub job
        if not aggregation_info.is_parent:
            return aggregation_info.sub_results

        # deal parent job
        sub_results = {}
        logger.info(
            f"Process aggregation parent job, sub job info: "
            f"{aggregation_info.sub_jobs}")
        # TODO(jidalong) quantum aggregation implementation
        job_results["sub_results"] = sub_results
        return job_results

    # run source codes
    job_results_list = []
    source_code_list = job_data["source_code"]
    source_code_index = 0
    driver = None
    transpiler = None
    for source_code in source_code_list:
        job_results, driver, transpiler = run_code(
            source_code_index, source_code, job_info, driver, transpiler)
        job_results_list.append(job_results)
        source_code_index += 1
    return job_results_list


def run_code(source_code_index, source_code, job_info, driver, transpiler):
    """
    Flow: run

    :param source_code_index: source code index
    :param source_code: source code
    :param job_info: job info
    :param driver: driver
    :param transpiler: transpiler
    :return job results
    """

    logger.info(f"Run source_code_index: {source_code_index}\n"
                f"source_code:\n {source_code}")

    transpiler = None
    transpile_results = None
    num_qubits = None
    job_data = job_info["data"]
    profiling_types = job_data.get("profiling", [])
    profiling_types = [] if profiling_types is None else profiling_types

    # init driver (init only once in a flow)
    if not driver:
        future_driver = init_driver.submit(job_info["driver"],
                                           job_data["driver_options"])
        driver_task_result = future_driver.result()
        # init driver: error handling
        err_msg = driver_task_result.get("error", None)
        if err_msg:
            return format_error_results(
                None,
                errors.JobEngineDriverInitError,
                err_msg), driver, transpiler
        driver = driver_task_result["driver"]

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
                    err_msg), driver, transpiler
            transpiler = transpiler_task_result["transpiler"]

    job_results = {
        "results": None,
        "num_qubits": None,
        "metadata": None,
        "profiling": {}
    }
    if driver.enable_transpiler:
        # [flow_parse]
        parse_results, profiling_time = flow_parse(
            source_code,
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
            return job_results, driver, transpiler

        num_qubits = parse_results.get("num_qubits", None)
        job_results["num_qubits"] = num_qubits

        # [flow_transpile]
        transpile_results, profiling_time = flow_transpile(
            parse_results["parsed_gates"],
            transpiler,
            driver,
            profiling_types
        )
        if profiling_time:
            job_results["profiling"][
                Constant.PROFILING_TYPE_DRIVER_TRANSPILE] = profiling_time

        # transpile: error handling
        err_msg = transpile_results.get("error", None)
        if err_msg:
            job_results = format_error_results(driver,
                                               errors.JobEngineTranspileError,
                                               err_msg)
            return job_results, driver, transpiler

        transpile_results = transpile_results["transpile_results"]

    if driver.enable:
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
            return job_results, driver, transpiler

        # prepare job_results
        job_results["results"] = run_results["results"]
        job_results["metadata"] = run_results["metadata"]

    return job_results, driver, transpiler


def flow_parse(source_code,
               transpiler,
               profiling_types):
    """
    Flow: parse

    :param source_code: source code
    :param transpiler: transpiler
    :param profiling_types: profiling types
    :return results, profiling_time
    """

    profiling_start = 0
    profiling_end = 0

    # record parse start_time
    if (Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_start = time.time()

    # parser
    parse_task = parse.submit(
        source_code, transpiler,
        wait_for=[init_driver, init_transpiler])
    parse_task_result = parse_task.result()

    if (Constant.PROFILING_TYPE_DRIVER_PARSE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_end = time.time()

    profiling_time = profiling_end - profiling_start
    return parse_task_result, profiling_time


def flow_transpile(parse_results,
                   transpiler,
                   driver,
                   profiling_types):
    """
    Flow: transpile

    :param parse_results: parse results
    :param transpiler: transpiler
    :param driver: driver
    :param profiling_types: profiling types
    :return results, profiling_time
    """

    profiling_start = 0
    profiling_end = 0
    # record transpile start_time
    if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_start = time.time()

    # transpile codes
    transpile_task = transpile.submit(
        parse_results, driver, transpiler,
        wait_for=[init_driver, init_transpiler, parse])
    transpile_task_results = transpile_task.result()

    # record transpile end_time
    if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_end = time.time()
    profiling_time = profiling_end - profiling_start
    return transpile_task_results, profiling_time


def flow_run_driver(job_info,
                    num_qubits,
                    driver,
                    data,
                    profiling_types):
    """
    Flow: run driver

    :param job_info: job info
    :param num_qubits: number of qubits
    :param driver: driver
    :param data: data
    :param profiling_types: profiling types
    :return results, profiling_time
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

    run_task = run_driver.submit(
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
    """
    Format run results

    :param driver: driver
    :param job_id: job id
    :param data_index: data index
    :return formatted results
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
    # async mode: get results in the async set-job-results call
    elif driver_results_fetch_mode == Constant.RESULTS_FETCH_MODE_ASYNC:
        job_status = Constant.JOB_STATUS_RUNNING

    job_results["results"] = results
    job_results["metadata"]["status"] = job_status
    job_results["metadata"]["end_date"] = end_date

    return job_results


def format_error_results(driver, err_cls, err_msg):
    """
    Format error results

    :param driver: driver
    :param err_cls: error class
    :param err_msg: error message
    :return: formatted error results
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
