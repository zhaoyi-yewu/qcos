#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd.
# All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


import unittest
from qcos.interface.qcos_dqcosapi_handler_strategy import (
    DQcosHeartbeatStrategy,
    DQcosFetchWorkloadStrategy,
    DQcosFetchIsingWorkloadStrategy,
    DQcosConfirmWorkloadStrategy,
    DQcosReceiveWorkloadResultStrategy,
    DQcosFetchCancellationStrategy,
    DQcosReceiveCancellationResultStrategy)
from qcos.interface.qcos_auto_strategy import SystemTestResultStrategy
from qcos.interface.qcos_xternalapi_handler_strategy import (
    XternalFetchOpenqasmStrategy,
    XternalSaveOpenqasmStrategy)
# 确保你的QCOSInterfaceFactory类的路径正确
from qcos.interface.qcos_interface_factory import QCOSInterfaceFactory
from qcos.log.qcos_log import QCOSLogger
from qcos.interface.qcos_isingapi_handler_strategy import (
    IsingTaskStrategy,
    IsingTaskBoardStrategy,
    IsingHardwareMonitorStrategy,
    IsingProjectStrategy,
    IsingLogManagerStrategy,
    IsingUserCenterStrategy,
    IsingMachineInfoAndSelfTestStrategy,
    IsingUserManageStrategy,
    IsingRoleManageStrategy)


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class TestQCOSInterfaceFactory(unittest.TestCase):
    '''
    QCOSInterfaceFactory类的单元测试类
    本类提供了对QCOSInterfaceFactory类中get_strategy方法的测试，确保它能根据输入的策略类型正确返回相应的策略实例，
    并在策略类型不正确时抛出适当的异常
    '''

    def setUp(self):
        '''
        初始化测试环境
        '''
        self.factory = QCOSInterfaceFactory()

    def test_heartbeat_strategy(self):
        '''
        测试获取心跳请求策略
        '''

        qcos_logger.debug('开始测试心跳策略')

        # 获取心跳请求策略实例
        strategy = self.factory.get_strategy('dqcos_heartbeat')
        qcos_logger.debug(f'心跳策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosHeartbeatStrategy)
        qcos_logger.debug('心跳策略测试通过！')

    def test_fetch_workload_strategy(self):
        '''
        测试获取获取任务请求策略
        '''

        qcos_logger.debug('开始测试获取任务策略')

        # 获取获取任务请求策略实例
        strategy = self.factory.get_strategy('dqcos_fetch_workload')
        qcos_logger.debug(f'获取任务策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosFetchWorkloadStrategy)
        qcos_logger.debug('获取任务策略测试通过！')

    def test_fetch_ising_workload_strategy(self):
        '''
        获取获取任务请求策略实例
        :param strategy_type: 请求策略类型，此处为 'fetch_workload'
        :return: 获取任务请求策略实例
        :raises ValueError: 如果传入的 strategy_type 不受支持
        '''

        qcos_logger.debug('开始测试获取任务策略')

        # 获取获取任务请求策略实例
        strategy = self.factory.get_strategy('dqcos_fetch_Ising_workload')
        qcos_logger.debug(f'获取任务策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosFetchIsingWorkloadStrategy)
        qcos_logger.debug('获取任务策略测试通过！')

    def test_confirmation_strategy(self):
        '''
        测试获取任务确认请求策略
        '''

        qcos_logger.debug('开始测试任务确认策略...')

        # 获取任务确认请求策略实例
        strategy = self.factory.get_strategy('dqcos_confirm_workload')
        qcos_logger.debug(f'任务确认策略返回类型：：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosConfirmWorkloadStrategy)
        qcos_logger.debug('任务确认策略测试通过！')

    def test_fetch_cancellation_strategy(self):
        '''
        测试获取任务取消策略
        '''

        qcos_logger.debug('开始测试任务取消策略')

        # 获取任务取消策略实例
        strategy = self.factory.get_strategy('dqcos_fetch_cancellation')
        qcos_logger.debug(f'任务取消策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosFetchCancellationStrategy)
        qcos_logger.debug('测试任务取消策略通过!')

    def test_receive_cancellation_result_strategy(self):
        '''
        测试获取任务取消结果策略
        '''

        qcos_logger.debug('开始测试任务取消结果策略')

        # 获取任务取消结果策略实例
        strategy = self.factory.get_strategy(
            'dqcos_receive_cancellation_result')
        qcos_logger.debug(f'任务取消结果策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosReceiveCancellationResultStrategy)
        qcos_logger.debug('测试任务取消结果策略通过!')

    def test_receive_workload_result_strategy(self):
        '''
        测试获取任务结果上报策略
        '''

        qcos_logger.debug('开始测试任务结果上报策略')

        # 获取任务结果上报策略实例
        strategy = self.factory.get_strategy('dqcos_receive_workload_result')

        qcos_logger.debug(f'任务结果上报策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, DQcosReceiveWorkloadResultStrategy)
        qcos_logger.debug('测试任务结果上报策略通过！')

    def test_system_test_result_strategy(self):
        '''
        测试系统测试结果策略
        '''

        qcos_logger.debug('开始测试系统测试结果策略')

        # 系统测试结果策略实例
        strategy = self.factory.get_strategy('system_test_result')

        qcos_logger.debug(f'系统测试结果策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, SystemTestResultStrategy)
        qcos_logger.debug('系统测试结果策略通过！')

    def test_xternal_fetch_openqasm_strategy(self):
        '''
        测试xternal openqasm任务处理策略
        '''

        qcos_logger.debug('开始测试xternal openqasm任务处理策略')

        # xternal openqasm任务处理策略实例
        strategy = self.factory.get_strategy('xternal_fetch_openqasm')

        qcos_logger.debug(
            f'xternal openqasm任务处理策略返回类型：{
                type(strategy).__name__}')
        self.assertIsInstance(strategy, XternalFetchOpenqasmStrategy)
        qcos_logger.debug('xternal openqasm任务处理策略通过！')

    def test_xternal_save_openqasm_strategy(self):
        '''
        测试xternal openqasm任务保存策略实例
        '''

        qcos_logger.debug('开始测试xternal openqasm任务保存策略')

        # xternal openqasm任务保存策略实例
        strategy = self.factory.get_strategy('xternal_save_openqasm')

        qcos_logger.debug(
            f'xternal openqasm任务保存策略返回类型：{
                type(strategy).__name__}')
        self.assertIsInstance(strategy, XternalSaveOpenqasmStrategy)
        qcos_logger.debug('xternal openqasm任务保存策略通过！')

    def test_ising_task_strategy(self):
        '''
        测试ising任务策略
        '''

        qcos_logger.debug('开始测试ising任务策略')

        # ising任务策略实例
        strategy = self.factory.get_strategy('ising_task')

        qcos_logger.debug(f'ising任务策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingTaskStrategy)
        qcos_logger.debug('ising任务策略通过！')

    def test_ising_task_board_strategy(self):
        '''
        测试ising任务看板策略
        '''

        qcos_logger.debug('开始测试ising任务看板策略')

        # ising任务看板策略实例
        strategy = self.factory.get_strategy('ising_task_board')

        qcos_logger.debug(f'ising任务看板策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingTaskBoardStrategy)
        qcos_logger.debug('ising任务看板策略通过！')

    def test_ising_hardware_monitor_strategy(self):
        '''
        测试ising硬件监控策略
        '''

        qcos_logger.debug('开始测试ising硬件监控策略')

        # ising任务看板策略实例
        strategy = self.factory.get_strategy('ising_hardware_monitor')

        qcos_logger.debug(f'ising硬件监控策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingHardwareMonitorStrategy)
        qcos_logger.debug('ising硬件监控策略通过！')

    def test_ising_project_strategy(self):
        '''
        测试ising项目策略
        '''

        qcos_logger.debug('开始测试ising项目策略')

        # ising项目策略实例
        strategy = self.factory.get_strategy('ising_project')

        qcos_logger.debug(f'ising项目管理策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingProjectStrategy)
        qcos_logger.debug('ising项目管理策略通过！')

    def test_ising_log_manage_strategy(self):
        '''
        测试ising日志管理策略
        '''

        qcos_logger.debug('开始测试ising日志管理策略')

        # ising日志管理策略实例
        strategy = self.factory.get_strategy('ising_log')

        qcos_logger.debug(f'ising日志管理策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingLogManagerStrategy)
        qcos_logger.debug('ising日志管理策略通过！')

    def test_ising_user_center_strategy(self):
        '''
        测试ising个人中心策略
        '''

        qcos_logger.debug('开始测试ising个人中心策略')

        # ising个人中心策略实例
        strategy = self.factory.get_strategy('ising_user_center')

        qcos_logger.debug(f'ising个人中心策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingUserCenterStrategy)
        qcos_logger.debug('ising个人中心策略通过！')

    def test_ising_machine_info_and_self_test_strategy(self):
        '''
        测试ising真机信息&自检策略
        '''

        qcos_logger.debug('开始测试ising真机信息&自检策略')

        # ising真机信息&自检策略实例
        strategy = self.factory.get_strategy(
            'ising_machine_info_and_self_test')

        qcos_logger.debug(f'ising真机信息&自检策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingMachineInfoAndSelfTestStrategy)
        qcos_logger.debug('ising真机信息&自检策略通过！')

    def test_ising_user_manage_strategy(self):
        '''
        测试ising用户管理策略
        '''

        qcos_logger.debug('开始测试ising用户管理策略')

        # ising用户管理策略实例
        strategy = self.factory.get_strategy('ising_user_manage')

        qcos_logger.debug(f'ising用户管理策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingUserManageStrategy)
        qcos_logger.debug('ising用户管理策略通过！')

    def test_ising_role_manage_strategy(self):
        '''
        测试ising角色管理策略
        '''

        qcos_logger.debug('开始测试ising角色管理策略')

        # ising角色管理策略实例
        strategy = self.factory.get_strategy('ising_role_manage')

        qcos_logger.debug(f'ising角色管理策略返回类型：{type(strategy).__name__}')
        self.assertIsInstance(strategy, IsingRoleManageStrategy)
        qcos_logger.debug('ising角色管理策略通过！')

    def test_invalid_strategy(self):
        '''
        测试无效请求策略输入
        '''

        qcos_logger.debug('开始测试无效策略输入...')

        try:
            # 尝试获取不存在的请求策略实例
            self.factory.get_strategy('unknown')
        except ValueError as e:
            qcos_logger.debug('请求策略为无效类型： %s', e)
            self.assertTrue('Unknown strategy type' in str(e))

        qcos_logger.debug('无效策略输入测试通过！')


if __name__ == '__main__':
    unittest.main()
