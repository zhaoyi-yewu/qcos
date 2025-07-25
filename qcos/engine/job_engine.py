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

from prefect import flow, task
from loguru import logger

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst

# 配置 Loguru
# pylint: disable=duplicate-code
logger.add(
    Constant.PREFECT_JOB_LOG_PATH,
    rotation=Constant.PREFECT_JOB_LOG_ROTATION,
    retention=Constant.PREFECT_JOB_LOG_RETENTION,
    format=Constant.PREFECT_JOB_LOG_FORMAT
)


@task(persist_result=False)
def init_driver(driver_info):
    """
    Init driver from driver_info

    :param driver_info: driver info
    :return: driver
    """

    try:
        driver_module = importlib.import_module(driver_info["module_name"])
        driver_class = getattr(driver_module, driver_info["class_name"])
        driver = driver_class()
        driver.extra_configs = driver_info.get("extra_configs", {})
        # validate and copy extra_configs to qpu_configs
        success, err_msg = driver.validate_driver_configs()
        # error handling
        if not success:
            logger.error(err_msg)
            raise ValueError(err_msg)
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
def init_transpiler(transpiler_class_info, transpiler_info):
    """
    Init transpiler instance

    :param transpiler_class_info: transpiler class info
    :param transpiler_info: transpiler info
    :return: transpiler
    """

    try:
        transpiler_module = importlib.import_module(
            transpiler_class_info["module_name"])
        transpiler_class = getattr(transpiler_module,
                                   transpiler_class_info["class_name"])
        transpiler = transpiler_class()
        if transpiler_info:
            transpiler.update_transpiler_info(transpiler_info)
        return {"transpiler": transpiler, "error": None}
    except Exception as e:
        return {"transpiler": None, "error": ValueError(str(e))}


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
def qasm_parser(job_data, transpiler):
    """
    qasm_parser

    :param job_data: job data
    :param transpiler: transpiler
    :return parsed gate list
    """

    num_qubits = -1
    try:
        raw_qasm = job_data['source_code'][0]
        logger.info(f"raw_qasm:\n{raw_qasm}")
        parsed_gates = transpiler.parse(raw_qasm)
        num_qubits = transpiler.num_qubits
        logger.info(f"final parsed gates: {parsed_gates}")
        return {"parsed_gates": parsed_gates, "num_qubits": num_qubits,
                "error": None}
    except Exception as e:
        return {"parsed_gates": None, "num_qubits": num_qubits,
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
        results = None
        job_status = None
        end_date = None
        data_type = driver.get_default_data_type()
        if dry_run:
            logger.info(
                f"dry_run: job_id: {job_id}, num_qubits: {num_qubits}, "
                f"data: {data}, data_type: {data_type}, shots: {shots}")
            driver.dry_run(job_id, num_qubits, data, data_type=data_type,
                           shots=shots)
        else:
            logger.info(
                f"run: job_id: {job_id}, num_qubits: {num_qubits}, "
                f"data: {data}, data_type: {data_type}, shots: {shots}")
            driver.run(job_id, num_qubits, data, data_type=data_type,
                       shots=shots)
        if driver.results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
            # sync mode: get results immediately
            results = driver.get_results(job_id)
            job_status = Constant.JOB_STATUS_COMPLETED
            end_date = Library.get_current_datetime()
        # async mode: get results in the async set-job-results call
        elif driver.results_fetch_mode == Constant.RESULTS_FETCH_MODE_ASYNC:
            results = None
            job_status = Constant.JOB_STATUS_RUNNING
        return {
            "results": results,
            "metadata": {
                "results_fetch_mode": driver.results_fetch_mode,
                "status": job_status,
                "end_date": end_date
            },
            "error": None,
        }
    except Exception as e:
        return {"results": None, "metadata": {}, "error": ValueError(str(e))}


def job_callback(flow, flow_run, state):
    """
    Job callback

    :param flow: flow
    :param flow_run: flow run
    :param state: flow state
    """
    job_id = flow_run.name  # use name as job uuid
    parameters = flow_run.parameters
    results = flow_run.state.result()
    is_job_callback = False
    results_fetch_mode_sync = False
    callbacks = Library.get_nested_dict_value(
        parameters, "job_info", "data", "callbacks", default=None)
    if callbacks:
        is_job_callback = True
    for result in results:
        results_fetch_mode = Library.get_nested_dict_value(
            result, "metadata", "results_fetch_mode", default=None)
        if results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
            results_fetch_mode_sync = True
            break
    if is_job_callback and results_fetch_mode_sync:
        # if job_info contains callback list and driver is in sync mode
        # do callback
        success, err_msg = Library.run_callbacks(job_id, results, callbacks)
        if not success:
            logger.error(err_msg)


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

    transpile_results = None
    num_qubits = -1
    profiling_driver_transpiler_start = 0
    profiling_driver_transpiler_end = 0
    profiling_driver_run_start = 0
    profiling_driver_run_end = 0
    job_results = {"metadata": {}, "profiling": {}, "results": None}
    job_data = job_info["data"]
    job_id = job_data["job_id"]
    profiling_types = job_data.get("profiling", [])
    profiling_types = [] if profiling_types is None else profiling_types
    logger.info(f"Processing work flow: job_engine. "
                f"job_id: {job_id}, job_info: {job_info}")

    # init driver
    future_driver = init_driver.submit(job_info["driver"])
    driver_task_result = future_driver.result()
    if driver_task_result["error"]:
        raise driver_task_result["error"]
    driver = driver_task_result["driver"]

    if driver.enable_transpiler:
        # init transpiler
        future_transpiler = init_transpiler.submit(
            job_info["transpiler"],
            job_data.get("transpiler_info", None))
        transpiler_task_result = future_transpiler.result()
        if transpiler_task_result["error"]:
            raise transpiler_task_result["error"]
        transpiler = transpiler_task_result["transpiler"]

        parse_task = qasm_parser.submit(
            job_data, transpiler,
            wait_for=[init_driver, init_transpiler])
        parse_task_result = parse_task.result()
        num_qubits = parse_task_result.get("num_qubits", -1)
        job_results["num_qubits"] = num_qubits

        # record transpiling start_time
        if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
                Constant.PROFILING_TYPE_ALL in profiling_types):
            profiling_driver_transpiler_start = time.time()

        # transpile codes
        transpile_task_results = transpile.submit(
            parse_task_result.get("parsed_gates", None), driver, transpiler,
            wait_for=[init_driver, init_transpiler, qasm_parser])

        # record transpiling end_time
        if (Constant.PROFILING_TYPE_DRIVER_TRANSPILE in profiling_types or
                Constant.PROFILING_TYPE_ALL in profiling_types):
            profiling_driver_transpiler_end = time.time()

        # error handling
        _transpile_task_results = transpile_task_results.result()
        err_msg = _transpile_task_results.get("error", None)
        if err_msg:
            raise err_msg
        transpile_results = _transpile_task_results["transpile_results"]

    # call run() in driver
    run_driver_task_result = None
    # record driver_run start_time
    if (Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_driver_run_start = time.time()

    if driver.enable_transpiler:
        run_driver_task_result = run_driver.submit(
            job_info, driver, num_qubits, transpile_results,
            wait_for=[transpile])
    else:
        run_driver_task_result = run_driver.submit(
            job_info, driver, num_qubits, job_data,
            wait_for=[init_driver])

    # record driver_run end_time
    if (Constant.PROFILING_TYPE_DRIVER_RUN in profiling_types or
            Constant.PROFILING_TYPE_ALL in profiling_types):
        profiling_driver_run_end = time.time()

    # get results
    task_result = run_driver_task_result.result()

    # error handling
    error = task_result["error"]
    if error:
        raise error
    job_results["results"] = task_result["results"]
    job_results["metadata"] = task_result["metadata"]

    # calculate profiling
    if profiling_driver_transpiler_start and profiling_driver_transpiler_end:
        job_results["profiling"]["profiling_transpiler"] = \
            profiling_driver_transpiler_end - profiling_driver_transpiler_start
    if profiling_driver_run_start and profiling_driver_run_end:
        job_results["profiling"]["profiling_driver_run"] = \
            profiling_driver_run_end - profiling_driver_run_start

    # construct results
    results = [job_results]
    return results
