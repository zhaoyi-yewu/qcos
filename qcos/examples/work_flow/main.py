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

import asyncio
import sys
from time import sleep

from prefect import get_client
from prefect.variables import VariableCreate

import sys
import examples
from qcos.common.constant import Constant
from qcos.task_manager import scheduler


async def create_variable():
    client = get_client()
    await client.create_variable(
        VariableCreate(name="my_variable_create_by_client",
                       value={"name": "z", "age": 2}))


if __name__ == "__main__":
    try:
        asyncio.run(create_variable())
        # 0.init create work pool,queue and start workers
        # auto run in scheduler

        # 1.deploy and run work flow
        id, err = scheduler.add(
            Constant.JOB_SCHED_POLICY_PRIORITY,
            {"flow_args": {"user": "test22"},
             "job_priority": 6,
             "deploy_name": "test123",
             "deploy_flow_func": examples.deploy_flow,
             "deploy_flow_path":
                 "../examples/work_flow/examples.py"})
        # 2.get results from flow run
        while True:
            results, state = scheduler.get_result_by_id(id)
            if not results:
                print(f"[Flow] state: {state}")
            else:
                print(f"[Flow] state: {state}, results: {results}")
            sleep(2)
    except Exception as e:
        print(f"{e}\n")
        sys.exit(1)
