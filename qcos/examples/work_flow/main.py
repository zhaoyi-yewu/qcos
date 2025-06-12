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
from task_manager import task_manager

if __name__ == "__main__":
    try:
        # 1.create work pool,queue and start workers
        task_manager.start()
        # 2.deploy work flow
        d_id = task_manager.deploy_task_flow(
            "test", "deploy_flow",
            Constant.DEFAULT_JOB_SCHEDULING_POLICY,
            Constant.DEFAULT_JOB_PRIORITY,
            examples.deploy_flow,
            "../examples/work_flow/examples.py", )
        # 3.run deploy from flow
        r_id1 = task_manager.run_task_flow(d_id, {"user": "test"})
        # 4.get results from flow run
        while True:
            result, state = task_manager.get_task_flow_result(r_id1)
            if not result:
                print(f"[Flow] state: {state}")
            else:
                print(f"[Flow] state: {state}, result: {result}")
                break
            sleep(2)
    except Exception as e:
        print(f"{e}\n")
        exit(1)
