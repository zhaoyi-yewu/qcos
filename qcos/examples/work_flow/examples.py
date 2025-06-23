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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT
# WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import time

from prefect import flow, task


@task(persist_result=False)
def task1(job_info):
    print("[Task1]: " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    time.sleep(5)
    return "t1_r"


@task(persist_result=False)
def task2(job_info):
    print("[Task2]: " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    return "t2_r"


@task(persist_result=False)
def task3(job_info):
    print("[Task3]: " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    return "t3_r"


@flow(name="deploy_flow", persist_result=True)
def deploy_flow(job_info):
    # # init set
    # Variable.set("global_value", 10, overwrite=True)
    # # read
    # print("global value:" + str(Variable.get("global_value")))
    # # update
    # Variable.set("global_value", 20, overwrite=True)
    # print("global value after update:" + str(Variable.get("global_value")))
    # print("support json" + str(Variable.get("myjson", "{}")))
    print("test accept job info from client: ")
    print(job_info)
    t1 = task1.submit(job_info)
    t2 = task2.submit(job_info)
    # t3 must wait until t1 completed
    t3 = task3.submit(t1.result())
    result = [t1.result(), t2.result(), t3.result()]
    time.sleep(10)
    return result
