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

import time

from prefect import flow, task


@task(persist_result=False)
def task1(user: str):
    print("[Task1] by " + user + ": " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    time.sleep(5)
    return "t1_r"


@task(persist_result=False)
def task2(user: str):
    print("[Task2] by " + user + ": " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    return "t2_r"


@task(persist_result=False)
def task3(user: str):
    print("[Task3] by " + user + ": " +
          time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    return "t3_r"


@flow(name="deploy_flow", persist_result=True)
def deploy_flow(user: str):
    t1 = task1.submit(user)
    t2 = task2.submit(user)
    # t3 must wait until t1 completed
    t3 = task3.submit(t1.result())
    result = [t1.result(), t2.result(), t3.result()]
    time.sleep(10)
    return result
