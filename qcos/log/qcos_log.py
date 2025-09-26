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


import os
import re
import logging
import logging.handlers
from logging.handlers import BaseRotatingHandler
import configparser
from datetime import datetime
import inspect


class QCOSLogger(object):
    '''
    Logger 类
    '''
    # 保存单例实例
    _instance = None

    def __new__(cls, *args, **kwargs):
        # 如果实例不存在,则创建一个新实例
        if not cls._instance:
            cls._instance = super(QCOSLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self, name='QCOS'):
        # 如果实例未初始化,则进行初始化
        if not hasattr(self, 'initialized'):
            self.name=name
            self.log_dir = None

            # 读取配置文件
            self.config = self._read_config()

            # 创建日志目录
            self._create_log_dir()

            # 创建日志记录器
            self.logger = logging.getLogger(name)
            self.logger.setLevel(logging.DEBUG)

            # 设置日志格式
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] %(message)s',
                '%Y-%m-%d %H:%M:%S')

            # 设置日志记录器的工厂方法,用于获取调用者的文件和行号信息
            #logging.setLogRecordFactory(self._log_record_factory)

            # 设置控制台处理器
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            # 设置文件处理器
            file_handler = FileRotatingHandler(
                file_name=self._get_log_file_path(),
                max_bytes=self.config['log_file_size'],
                backup_count=self.config['log_file_count']
            )

            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # 标记实例已初始化
            self.initialized = True
            print('QCOSLogger initialized')
        else:
            print('QCOSLogger already initialized')

    def _log_record_factory(self, *args, **kwargs):
        """
        自定义日志记录器工厂方法,用于获取调用者的文件和行号信息
        """

        record = logging.LogRecord(*args, **kwargs)
        # 获取调用日志函数的栈帧
        frame = inspect.currentframe()
        # 向上追溯两层栈帧，找到调用日志记录函数的地方
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
        if frame:
            record.filename = os.path.basename(frame.f_code.co_filename)
            record.lineno = frame.f_lineno
            record.funcName = frame.f_code.co_name
        return record

    def _read_config(self):
        """
        读取配置文件
        """

        # 获取当前文件的绝对路径，并构造配置文件的完整路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.normpath(
            os.path.join(current_dir, '../config/qcos_config.conf'))

        # 使用ConfigParser读取配置文件
        config = configparser.ConfigParser()
        with open(config_path, 'r', encoding='utf-8') as f:
            config.read_file(f)

        return {
            'log_dir': config.get('log', 'log_dir'),
            'log_file_size': config.getint('log', 'log_file_size'),
            'log_file_count': config.getint('log', 'log_file_count')
        }

    def _create_log_dir(self):
        """
        创建日志目录
        """

        # 获取当前文件的绝对路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        runtime_log_path = os.path.normpath(os.path.join(current_dir, '../'))

        # 并构造log文件的完整路径
        log_dir = self.config['log_dir']
        log_dir = os.path.join(runtime_log_path, log_dir)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        self.log_dir = log_dir

    def _get_log_file_path(self):
        """
        获取日志文件路径
        """

        # 构建runtime_log文件，以运行日期命名
        log_file_name = f'qcos_{datetime.now().strftime("%Y-%m-%d")}.log'
        return os.path.join(self.log_dir, log_file_name)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


class FileRotatingHandler(BaseRotatingHandler):
    """
    日志轮转处理器
    """

    def __init__(self, file_name, max_bytes=0, backup_count=0):
        """
        初始化FileRotatingHandler对象
        参数:
        filename (str): 日志文件名
        max_bytes (int): 允许最大的日志文件大小
        backup_count (int): 日志文件备份数
        """
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        BaseRotatingHandler.__init__(self, file_name, mode='a')

    def manage_log_rollover(self):
        """
        执行日志文件轮转
        """
        if self.stream:
            try:
                self.stream.close()
            except Exception:
                pass

        if self.backup_count > 0:
            base_dir = os.path.dirname(self.baseFilename)
            base_name = os.path.basename(self.baseFilename)
            # 获取日志目录下所有匹配的日志文件
            all_logs = [
                file for file in os.listdir(base_dir)
                if file != base_name and re.match(
                    fr'qcos_\d{{4}}-\d{{2}}-\d{{2}}(-\d+)?\.log', file)
            ]

            # 按日期和备份序号排序
            def extract_date_and_backup(file_name):
                # 提取日志日期
                match_data = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
                file_date = datetime.strptime(match_data.group(1), '%Y-%m-%d')\
                    if match_data else datetime.min
                # 提取备份序号
                match_backup = re.search(r'(\d{4}-\d{2}-\d{2}-\d+)', file_name)
                backup_num = (self.backup_count -
                              int(match_backup.group(1).split('-')[-1]))\
                              if match_backup else self.backup_count
                return file_date, backup_num

            all_logs.sort(key=extract_date_and_backup, reverse=True)

            # 删除超出数量限制的日志文件
            if len(all_logs) >= self.backup_count:
                for log_to_delete in all_logs[self.backup_count-1:]:
                    os.remove(os.path.join(base_dir, log_to_delete))

            # 执行日志轮转
            for i in range(self.backup_count - 1, 0, -1):
                # 轮转备份文件
                src_filename = self.rotation_filename(
                    f'{self._rename_base_filename(i)}')
                dst_filename = self.rotation_filename(
                    f'{self._rename_base_filename(i+1)}')
                if os.path.exists(src_filename):
                    if os.path.exists(dst_filename):
                        os.remove(dst_filename)
                    os.rename(src_filename, dst_filename)
            # 新备份文件的备份序号为1
            save_filename = self.rotation_filename(
                f'{self._rename_base_filename(1)}')
            if os.path.exists(save_filename):
                os.remove(save_filename)
            self.rotate(self.baseFilename, save_filename)
        self.stream = self._open()

    def _rename_base_filename(self, index):
        """
        修改日志文件名，加上备份序号
        参数:
        index (int): 备份序号
        返回:
        str: 加上备份序号的日志路径
        """
        base_dir = os.path.dirname(self.baseFilename)
        base_name = os.path.basename(self.baseFilename)
        # 分离文件名和扩展名
        file_name, extension = os.path.splitext(base_name)
        return f'{base_dir}/{file_name}-{index}{extension}'

    def should_rollover(self, record):
        """
        判断日志文件是否需要轮转
        参数:
        record (LogRecord): 记录信息
        返回:
        bool: 日志是否需要轮转
        """
        if self.max_bytes > 0:
            msg = f'{self.format(record)}\n'
            if os.stat(self.baseFilename)[6] + len(msg) >= self.max_bytes:
                return True
        return False

    def emit(self, record):
        """
        发送记录信息到文件
        参数:
        record (LogRecord): 记录信息
        """
        try:
            if self.should_rollover(record):
                self.manage_log_rollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)
