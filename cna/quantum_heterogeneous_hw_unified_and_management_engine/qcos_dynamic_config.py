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


import configparser
import threading
import time
import os
from typing import Any, Callable, List
from qcos.log.qcos_log import QCOSLogger
from qcos.config.qcos_config_manager import qcos_configer


# 创建日志记录器实例
qcos_logger = QCOSLogger()


class DynamicConfig(object):
    '''
    动态配置管理类，监控配置文件变化并热加载配置
    '''

    def __init__(self, callback: Callable = None):
        '''
        初始化动态配置管理器

        参数:
        config_manager: 配置管理器实例（例如 qcos_configer）
        callback (Callable): 配置更新时的回调函数
        '''
        # 保存配置管理器实例
        self.config_manager = qcos_configer
        # 保存配置文件路径
        self.config_path = qcos_configer.get_config_file_absolute_path()
        # 保存回调函数
        self.callback = callback
        # 启动配置文件监控线程
        self.watch_config_changes()

    def load_config(self):
        '''
        加载配置文件

        返回:
        ConfigParser: 配置对象
        '''
        # 创建配置解析器对象
        config = configparser.ConfigParser()
        # 读取配置文件
        config.read(self.config_path, encoding='utf-8')
        return config

    def watch_config_changes(self):
        '''
        监视配置文件变化
        '''
        def _watch():
            try:
                last_mtime = os.path.getmtime(self.config_path)
            except FileNotFoundError:
                qcos_logger.error(f'配置文件未找到: {self.config_path}')
                return

            while not self.stop_event.is_set():
                time.sleep(10)
                try:
                    current_mtime = os.path.getmtime(self.config_path)
                    if current_mtime > last_mtime:
                        qcos_configer = self.load_config()
                        last_mtime = current_mtime
                        qcos_logger.debug('配置文件已更新，配置已重新加载！')
                        if self.callback:
                            self.callback()
                except FileNotFoundError:
                    qcos_logger.error(f'配置文件未找到: {self.config_path}')
                except Exception as e:
                    qcos_logger.error(f'监控配置文件时发生错误: {e}')

        self.stop_event = threading.Event()
        self.watch_thread = threading.Thread(target=_watch, daemon=True)
        self.watch_thread.start()

    def stop_watch(self):
        '''
        停止配置文件监控线程
        '''
        self.stop_event.set()
        self.watch_thread.join()


def on_config_change():
    '''
    当配置文件发生变化时的回调函数
    '''
    # 可以在此处理配置更新后的操作
    qcos_logger.debug(f'配置文件已更新，配置已重新加载！')


dynamic_config = DynamicConfig(on_config_change)
