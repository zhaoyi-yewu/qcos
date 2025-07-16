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

from prefect import flow, task, runtime
from loguru import logger

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_factory import TranspilerFactory

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
        return {"driver": driver, "error": None}
    except Exception as e:
        return {"driver": None, "error": ValueError(str(e))}


@task(persist_result=False)
def cmss_transpiler(job_info):
    """
    CMSS transpiler

    :param job_info: job info
    :return basis gate list
    """
    # load qpu configs

    num_qubits = -1
    try:
        factory = TranspilerFactory()
        transpiler = factory.get_transpiler_by_type(Constant.TRANSPILER_CMSS)
        raw_qasm = job_info['source_code'][0]
        logger.info(f"raw_qasm: {raw_qasm}")
        basis_gate_list = transpiler.transpile(raw_qasm)
        num_qubits = transpiler.num_qubits
        logger.info(f"final basis_gate_list: {basis_gate_list}")
        return {"basis_gate_list": basis_gate_list, "num_qubits": num_qubits,
                "error": None}
    except Exception as e:
        return {"basis_gate_list": None, "num_qubits": num_qubits,
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
        job_id = job_info["job_id"]
        shots = job_info["data"].get("shots", Constant.DEFAULT_SHOTS)
        dry_run = job_info["data"].get("dry_run", False)
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
    job_id = flow_run.id
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
    transpiler_profiling_start = 0
    transpiler_profiling_end = 0
    job_results = {"metadata": {}, "profiling": {}, "results": None}
    job_id = runtime.flow_run.id
    job_info["job_id"] = job_id
    data = job_info["data"]
    profiling_types = data.get("profiling", [])
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
        # choose transpiler
        if driver.transpiler == Constant.TRANSPILER_CMSS:
            if Constant.PROFILING_TYPE_TRANSPILER in profiling_types:
                transpiler_profiling_start = time.time()
            transpile_task_results = cmss_transpiler.submit(
                data, wait_for=[init_driver])
            if Constant.PROFILING_TYPE_TRANSPILER in profiling_types:
                transpiler_profiling_end = time.time()
            _transpile_task_results = transpile_task_results.result()
            num_qubits = _transpile_task_results.get("num_qubits", -1)
            job_results["num_qubits"] = num_qubits
            err_msg = _transpile_task_results.get("error", None)
            if err_msg:
                raise err_msg
            transpile_results = _transpile_task_results["basis_gate_list"]

    # call run() in driver
    run_driver_task_result = None
    if driver.enable_transpiler:
        run_driver_task_result = run_driver.submit(
            job_info, driver, num_qubits, transpile_results,
            wait_for=[cmss_transpiler])
    else:
        run_driver_task_result = run_driver.submit(
            job_info, driver, num_qubits, data,
            wait_for=[init_driver])
    task_result = run_driver_task_result.result()
    error = task_result["error"]
    if error:
        raise error
    job_results["results"] = task_result["results"]
    job_results["metadata"] = task_result["metadata"]

    # calculate profiling for transpiler
    if transpiler_profiling_start and transpiler_profiling_end:
        job_results["profiling"] = {
            "profiling_transpiler":
                transpiler_profiling_end - transpiler_profiling_start,
        }

    # construct results
    results = [job_results]
    return results
