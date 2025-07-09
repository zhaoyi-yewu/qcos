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
import logging
import time

from prefect import flow, task, runtime

from qcos.common.constant import Constant
from qcos.transpiler.common.transpiler_cfg import trans_cfg_inst
from qcos.transpiler.transpiler_factory import TranspilerFactory

logger = logging.getLogger(__name__)


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
        logger.debug(f"raw_qasm: {raw_qasm}")
        basis_gate_list = transpiler.transpile(raw_qasm)
        num_qubits = transpiler.num_qubits
        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return {"basis_gate_list": basis_gate_list, "num_qubits": num_qubits,
                "error": None}
    except Exception as e:
        return {"basis_gate_list": None, "num_qubits": num_qubits,
                "error": ValueError(str(e))}


@task(persist_result=False)
def run_driver(job_info, driver, data):
    """
    Run the driver

    :param job_info: job info
    :param driver: driver
    :param data: data
    :return results
    """
    try:
        job_id = job_info["job_id"]
        shots = job_info.get("shots", Constant.DEFAULT_SHOTS)
        dry_run = job_info["data"].get("dry_run", False)
        results = None
        data_type = driver.get_default_data_type()
        if dry_run:
            driver.dry_run(job_id, data, data_type=data_type,
                           shots=shots)
        else:
            driver.run(job_id, data, data_type=data_type,
                       shots=shots)
        if driver.results_fetch_mode == Constant.RESULTS_FETCH_MODE_SYNC:
            # sync mode: get results immediately
            results = driver.get_results(job_id)
        # async mode: get results in the next query call
        return {"results": results, "error": None}
    except Exception as e:
        return {"results": None, "error": ValueError(str(e))}


@flow(name="job_engine", persist_result=True)
def job_flow(job_info):
    """
    Job flow

    :param job_info: job info
    :return results
    """
    transpile_results = None
    num_qubits = -1
    transpiler_benchmark_start = 0
    transpiler_benchmark_end = 0
    job_results = {"metadata": {}, "benchmark": {}, "results": None}
    job_id = runtime.flow_run.id
    job_info["job_id"] = job_id
    data = job_info["data"]
    benchmark_types = data.get("benchmark", [])
    benchmark_types = [] if benchmark_types is None else benchmark_types
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
            if Constant.BENCHMARK_TYPE_TRANSPILER in benchmark_types:
                transpiler_benchmark_start = time.time()
            transpile_task_results = cmss_transpiler.submit(
                data, wait_for=[init_driver])
            if Constant.BENCHMARK_TYPE_TRANSPILER in benchmark_types:
                transpiler_benchmark_end = time.time()
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
            job_info, driver, transpile_results,
            wait_for=[cmss_transpiler])
    else:
        run_driver_task_result = run_driver.submit(
            job_info, driver, data,
            wait_for=[init_driver])
    error = run_driver_task_result.result()["error"]
    if error:
        raise error
    job_results["results"] = run_driver_task_result.result()["results"]

    # calculate benchmark for transpiler
    if transpiler_benchmark_start and transpiler_benchmark_end:
        job_results["benchmark"] = {
            "benchmark_transpiler":
                transpiler_benchmark_end - transpiler_benchmark_start,
        }

    # construct results
    results = [job_results]
    return results
