#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024 China Mobile(SuZhou) Software Technology Co.,Ltd. All rights reserved.
#
# The programs cannot be copied and/or distributed without the express
# permission of China Mobile(SuZhou) Software Technology Co.,Ltd.
# Create by Kaiyu Yuan at 2024-06
# ------------------------


from qcos.interface.qcos_interface_factory import QCOSInterfaceFactory
from qcos.log.qcos_log import QCOSLogger
import os
from qcos.interface.qcos_openqasm_int import openqasm_manager
from qcos.config.qcos_config_manager import qcos_configer


qcos_logger = QCOSLogger()


class QCOSInstance:
    def __init__(self, base_url, device_id, factory):
        """
            初始化QCOSInstance实例。

            :param base_url: 服务的基础URL。
            :param device_id: 设备的唯一标识符。
            :param factory: 工厂对象，用于根据策略类型获取策略实例。
        """

        self.base_url = base_url
        self.device_id = device_id
        self.factory = factory
        qcos_logger.info(f"[interface: qcos_int_instance] 创建QCOSInstance实例，服务地址： {self.base_url}")

    def send_request(self, strategy_type, data=None):
        """
            发送请求到服务器并执行相应的策略。

            :param strategy_type: 策略类型。
            :param data: 发送请求时附带的数据，默认为None。
            :return: 策略执行的结果。
        """

        qcos_logger.debug("[interface: qcos_int_instance] 发送服务请求")
        try:
            strategy = self.factory.get_strategy(strategy_type)
            qcos_logger.info(f"[interface: qcos_int_instance] 服务请求策略：{strategy_type}")
            if self.base_url == qcos_configer.get_dqcos_url():
                url = f"{self.base_url}/workload-broker/{self.device_id}"
            elif self.base_url == qcos_configer.get_autotest_url():
                url = self.base_url
            else:
                raise ValueError(f"URL {self.base_url} 错误！")
            return strategy.execute(url, data)
        except Exception as e:
            # 这里可以根据需要处理或重新抛出异常
            qcos_logger.error(f"发送服务请求失败: {e}")
            return None


class OpenqasmInstance:
    def __init__(self, base_path, factory):
        """
            初始化OpenqasmInstance实例。

            :param base_path: 服务的基础文件路径。
            :param factory: 工厂对象，用于根据策略类型获取策略实例。
        """

        self.base_path = base_path
        self.factory = factory
        qcos_logger.info(f"[interface: qcos_int_instance] 创建OpenQASMInstance实例，文件地址： {self.base_path}")

    def send_request(self, strategy_type, openqasm_struct=None):
        """
            发送请求到服务器并执行相应的策略。

            :param strategy_type: 策略类型。
            :param openqasm_struct: 附带的openqasm结构体，默认为None
            :return: 策略执行的结果。
        """

        qcos_logger.debug("[interface: qcos_int_instance] 发送xternal请求")
        try:
            strategy = self.factory.get_strategy(strategy_type)
            qcos_logger.info(f"[interface: qcos_int_instance] xternal请求策略：{strategy_type}")
            if os.path.exists(self.base_path):
                return strategy.execute(openqasm_struct)
            else:
                raise FileNotFoundError(f"文件 {self.base_path} 不存在。")
        except Exception as e:
            # 这里可以根据需要处理或重新抛出异常
            qcos_logger.error(f"发送xternal请求失败: {e}")
            return None


class IsingInstance:
    def __init__(self, base_url, factory):
        """
            初始化IsingInstance实例。

            :param base_url: 服务的基础URL。
            :param factory: 工厂对象，用于根据策略类型获取策略实例。
        """

        self.base_url = base_url
        self.factory = factory
        qcos_logger.info(f"[interface: qcos_int_instance] 创建IsingInstance实例，服务地址： {self.base_url}")

    def send_request(self, strategy_type, ising_task_type, data=None):
        """
            发送请求到服务器并执行相应的策略。

            :param strategy_type: 策略类型。
            :param ising_task_type: 具体请求类型
            :param data: 发送请求时附带的数据，默认为None。
            :return: 策略执行的结果。
        """

        qcos_logger.debug("[interface: qcos_int_instance] 发送ising服务请求")
        try:
            strategy = self.factory.get_strategy(strategy_type)
            qcos_logger.info(f"[interface: qcos_int_instance] 服务请求策略：{strategy_type}")
            if self.base_url:
                url = self.base_url
            else:
                raise ValueError(f"URL {self.base_url} 错误！")
            return strategy.execute(ising_task_type, url, data)
        except Exception as e:
            # 这里可以根据需要处理或重新抛出异常
            qcos_logger.error(f"发送服务请求失败: {e}")
            return None


qcos_dqcosapi_handler = QCOSInstance(qcos_configer.get_dqcos_url(), qcos_configer.get_device_id(), QCOSInterfaceFactory())
qcos_xternalapi_handler = OpenqasmInstance(openqasm_manager.original_openqasm_path, QCOSInterfaceFactory())
qcos_isingapi_handler = IsingInstance(qcos_configer.get_ising_machine_ip(), QCOSInterfaceFactory())
