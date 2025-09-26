#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Ming Liu at 2024-08-20
# ------------------------


import requests
import json
from qcos.log.qcos_log import QCOSLogger


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class AutoTestRequestStrategy:
    """
    自动化测试ST请求策略的基类
    """

    def execute(self, url, data=None):
        """
           执行请求策略的抽象方法
           :param url: 请求URL
           :param data: 请求数据
           :return: 请求响应
        """

        raise NotImplementedError("Each strategy must implement an execute method")


class SystemTestResultStrategy(AutoTestRequestStrategy):
    """
    传送结果策略
    """
    def execute(self, url, data=None):
        url = f"{url}/autotest"
        headers = {
            'Content-Type': 'application/json',
            'X-Request-From': 'QCOS'
        }
        response = requests.post(url, data=json.dumps(data), headers=headers)
        return response.status_code
