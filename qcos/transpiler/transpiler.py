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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

from time import sleep
from prefect import flow, task
from qcos.transpiler.cmss.compiler import optimizer, decomposer
from qcos.transpiler.cmss.mapping.na_mapping import NASingleRoute
import logging


logger = logging.getLogger(__name__)

@task(persist_result=False)
def transpiler(job_info):
    raw_qasm = job_info['source_code'][0].replace('QASM2:', '', 1).strip()
    logger.info(raw_qasm)
    na_map = NASingleRoute(raw_qasm)
    mapping_res = na_map.execute_with_order()
    logger.info("initial mapping:")
    logger.info(na_map.mapping)
    logger.info("after mapping:")
    for opt in mapping_res:
        logger.info(opt)
    parsed_circuit = decomposer(mapping_res)
    opt_parsed_circuit = optimizer(parsed_circuit)
    for pst in opt_parsed_circuit:
        logger.info(pst)
    logger.info("transpiler ends.")
    return len(opt_parsed_circuit)


@flow(name="transpiler_flow", persist_result=True)
def transpiler_flow(job_info):
    logger.info("test accept job info from client: ")
    t1 = transpiler.submit(job_info)
    result = [t1.result()]
    sleep(10)
    return result
