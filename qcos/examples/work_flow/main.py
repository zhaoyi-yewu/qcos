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

import examples
from common.constant import Constant
from task_manager import scheduler

if __name__ == "__main__":
    try:
        # 0.init create work pool,queue and start workers
        # auto run in scheduler

        # 1.deploy and run work flow
        id, err = scheduler.add(
            Constant.JOB_SCHEDULING_POLICY_PRIORITY,
            {"flow_args": {"user": "test22"},
             "job_priority": 6,
             "deploy_name": "test123",
             "deploy_flow_func": examples.deploy_flow,
             "deploy_flow_path":
                 "../examples/work_flow/examples.py"})
        # 2.get results from flow run
        while True:
            result, state = scheduler.get_result_by_id(id)
            if not result:
                print(f"[Flow] state: {state}")
            else:
                print(f"[Flow] state: {state}, result: {result}")
            sleep(2)
    except Exception as e:
        print(f"{e}\n")
        exit(1)
