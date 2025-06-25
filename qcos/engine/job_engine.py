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

from prefect import flow, task, runtime

from qcos.common.constant import Constant
from qcos.transpiler.cmss.compiler import optimizer, decomposer
from qcos.transpiler.cmss.mapping.na_mapping import NASingleRoute


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
        return {"driver": driver, "error": None}
    except Exception as e:
        return {"driver": None, "error": ValueError(str(e))}



@task(persist_result=False)
def cmss_transpiler(job_info, driver):
    """
    CMSS transpiler

    :param job_info: job info
    :param driver: driver
    :return basis gate list
    """
    # load qpu configs
    try:
        qpu_configs = driver.get_qpu_configs()
        if not qpu_configs:
            err_msg = "Missing qpu_configs"
            logger.error(err_msg)
            raise ValueError(err_msg)

        # compile and mapping
        raw_qasm = job_info['source_code'][0]
        logger.debug(f"raw_qasm: {raw_qasm}")

        na_map = NASingleRoute(raw_qasm, qpu_configs)
        mapping_res = na_map.execute_with_order()
        logger.debug(f"initial mapping: {na_map.mapping}")
        logger.debug(f"after mapping: {mapping_res}")

        # decompose gates
        parsed_circuit = decomposer(mapping_res)

        # optimize circuit
        basis_gate_list = optimizer(parsed_circuit)
        logger.debug(f"final basis_gate_list: {basis_gate_list}")
        return {"basis_gate_list": basis_gate_list, "error": None}
    except Exception as e:
        return {"basis_gate_list": None, "error": ValueError(str(e))}


@task(persist_result=False)
def run_driver(job_info, driver, transpile_results):
    """
    Run the driver

    :param job_info: job info
    :param driver: driver
    :param transpile_results: transpile results
    :return results
    """
    try:
        job_id = job_info["job_id"]
        shots = job_info.get("shots", Constant.DEFAULT_SHOTS)
        results = None
        data_type = driver.get_default_data_type()
        driver.run(job_id, transpile_results, data_type=data_type, shots=shots)
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
    job_id = runtime.flow_run.id
    job_info["job_id"] = job_id
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
            transpile_task_result = cmss_transpiler.submit(
                job_info["data"], driver)
            if transpile_task_result.result()["error"]:
                raise transpile_task_result.result()["error"]
            transpile_results = transpile_task_result.result()["basis_gate_list"]

    # call run() in driver
    run_driver_task_result = run_driver.submit(job_info, driver, transpile_results)
    if run_driver_task_result.result()["error"]:
        raise run_driver_task_result.result()["error"]
    job_results=run_driver_task_result.result()["results"]

    # construct results
    results = [job_results]
    return results
