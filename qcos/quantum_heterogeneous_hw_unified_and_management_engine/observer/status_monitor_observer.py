#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-10
# ------------------------


from .hardware_observer import HardwareObserver
from typing import Any, Dict
from qcos.log.qcos_log import QCOSLogger


qcos_logger = QCOSLogger()


class StatusMonitorObserver(HardwareObserver):
    """
    状态监控观察者类
    """

    def update(self, hw_name: str, status: Dict[str, Any]):
        """
        更新状态信息

        参数:
        hw_name (str): 硬件名称
        status (Dict[str, Any]): 状态信息
        """
        qcos_logger.debug(f"Status update for {hw_name}: {status}")
