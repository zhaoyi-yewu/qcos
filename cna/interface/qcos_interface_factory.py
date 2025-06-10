#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


from qcos.interface.qcos_dqcosapi_handler_strategy import (
    DQcosHeartbeatStrategy, DQcosFetchWorkloadStrategy, DQcosFetchIsingWorkloadStrategy, DQcosConfirmWorkloadStrategy,
    DQcosReceiveWorkloadResultStrategy, DQcosFetchCancellationStrategy, DQcosReceiveCancellationResultStrategy)
from qcos.interface.qcos_xternalapi_handler_strategy import XternalFetchOpenqasmStrategy, XternalSaveOpenqasmStrategy
from qcos.interface.qcos_auto_strategy import SystemTestResultStrategy
from qcos.interface.qcos_isingapi_handler_strategy import (
    IsingTaskStrategy, IsingTaskBoardStrategy, IsingHardwareMonitorStrategy, IsingProjectStrategy,
    IsingLogManagerStrategy, IsingUserCenterStrategy, IsingMachineInfoAndSelfTestStrategy, IsingUserManageStrategy,
    IsingRoleManageStrategy)


class QCOSInterfaceFactory:
    """
    QCOS接口工厂类，用于创建不同类型的请求策略
    """

    def get_strategy(self, strategy_type):
        """
               获取指定类型的请求策略实例
               :param strategy_type: 请求策略类型
               :return: 请求策略实例
               :raises ValueError: 如果传入的 strategy_type 不受支持
        """

        if strategy_type == "dqcos_heartbeat":
            return DQcosHeartbeatStrategy()

        elif strategy_type == "dqcos_fetch_workload":
            return DQcosFetchWorkloadStrategy()

        elif strategy_type == "dqcos_fetch_Ising_workload":
            return DQcosFetchIsingWorkloadStrategy()

        elif strategy_type == "dqcos_confirm_workload":
            return DQcosConfirmWorkloadStrategy()

        elif strategy_type == "dqcos_receive_workload_result":
            return DQcosReceiveWorkloadResultStrategy()

        elif strategy_type == "dqcos_fetch_cancellation":
            return DQcosFetchCancellationStrategy()

        elif strategy_type == "dqcos_receive_cancellation_result":
            return DQcosReceiveCancellationResultStrategy()

        elif strategy_type == "system_test_result":
            return SystemTestResultStrategy()

        elif strategy_type == "xternal_fetch_openqasm":
            return XternalFetchOpenqasmStrategy()

        elif strategy_type == "xternal_save_openqasm":
            return XternalSaveOpenqasmStrategy()

        elif strategy_type == "ising_task":
            return IsingTaskStrategy()

        elif strategy_type == "ising_task_board":
            return IsingTaskBoardStrategy()

        elif strategy_type == "ising_hardware_monitor":
            return IsingHardwareMonitorStrategy()

        elif strategy_type == "ising_project":
            return IsingProjectStrategy()

        elif strategy_type == "ising_log":
            return IsingLogManagerStrategy()

        elif strategy_type == "ising_user_center":
            return IsingUserCenterStrategy()

        elif strategy_type == "ising_machine_info_and_self_test":
            return IsingMachineInfoAndSelfTestStrategy()

        elif strategy_type == "ising_user_manage":
            return IsingUserManageStrategy()

        elif strategy_type == "ising_role_manage":
            return IsingRoleManageStrategy()

        else:
            raise ValueError("Unknown strategy type!")
