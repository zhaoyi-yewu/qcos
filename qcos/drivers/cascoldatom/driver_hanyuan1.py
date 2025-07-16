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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import copy
import json
import socket
import threading
import time
from schema import Optional, Or

from loguru import logger

from qcos.common.constant import Constant
from qcos.common.library import Library
from qcos.drivers.driver_base import DriverBase

# 配置 Loguru
# pylint: disable=duplicate-code
logger.add(
    Constant.PREFECT_JOB_LOG_PATH,
    rotation=Constant.PREFECT_JOB_LOG_ROTATION,
    retention=Constant.PREFECT_JOB_LOG_RETENTION,
    format=Constant.PREFECT_JOB_LOG_FORMAT
)


class DriverHanyuan1(DriverBase):
    """
    中科酷原-汉原1 中性原子驱动
    Cascoldatom Hanyuan1 driver
    CA-NAQC-20Q-A1
    """

    def __init__(self):
        super().__init__()
        self.version = "0.0.1"
        self.enable_transpiler = True
        self.transpiler = Constant.TRANSPILER_CMSS
        self.tech_type = Constant.TECH_TYPE_NEUTRAL_ATOM
        self.layout_method = DriverBase.LAYOUT_METHOD_CMSS_NONE
        self.supported_transpiler_list = [Constant.TRANSPILER_CMSS]
        self.enable_circuit_merge = True
        self.max_qubits = 10
        self.client = None
        self._final_response = None

    def init_driver(self):
        """
        Init driver
        """
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def validate_driver_configs(self):
        """
        Validate driver configurations

        :return bool: True if successful, False otherwise
        :return err_msg: error message
        """
        # TODO(zhaoyi): load transpiler plugin, and implemented in transpiler
        success = True
        err_msg = None

        # check and load driver configs
        driver_config_schema = {
            "ip_address": str,
            "port": int,
            "qpu_configs": {
                "qubits": int,
                "storage_area": [str],
                "operate_area": [str],
                "coupler_map": {str: [str]},
                "readout_error": {str: Or(float, int)},
                Optional("coupler_error"): {str: Or(float, int)},
                Optional("closest"): {str: str}
            },
            Optional("decomposition_rule"): {
                str: {
                    "gates": [list],
                    Optional("params"): [str]
                }
            }
        }
        _success, err_msgs = Library.validate_schema(
            self.extra_configs, driver_config_schema)
        if not _success:
            _err_msg = "\n".join(err_msgs)
            err_msg = f"driver config file error: {_err_msg}"
            success = False
        else:
            # copy configs to self.qpu_configs
            self.qpu_configs = copy.deepcopy(
                self.extra_configs.get("qpu_configs", {}))
            # copy configs to self.decomposition_rule
            self.decomposition_rule = copy.deepcopy(
                self.extra_configs.get("decomposition_rule", {}))
        return success, err_msg

    def close_driver(self):
        """
        Close driver
        """
        self.set_status(self.DRIVER_STATUS_OFFLINE)

    def run(self, job_id, num_qubits, data, data_type, shots=1):
        """
        Run job

        :param job_id: job ID
        :param num_qubits: number of qubits
        :param data: data
        :param data_type: data type
        :param shots: shots
        """
        # pylint: disable=duplicate-code
        logger.info(f"job_id: {job_id}, shots: {shots}, "
                    f"num_qubits: {num_qubits}, "
                    f"data_type: {data_type}, data: {data}")
        self.set_status(self.DRIVER_STATUS_BUSY)

        extra_configs = self.get_extra_configs()
        ip_address = extra_configs.get("ip_address", "127.0.0.1")
        port = extra_configs.get("port", 18402)

        # 1、init_task(类实例化,connect)
        success = self.init_task(ip_address, port)
        if not success:
            logger.error("连接真机失败")
            results = {"error": "连接真机失败"}
            self.set_results(job_id, results=results)
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 2、submit_task
        success = self.submit_task(job_id, num_qubits, data, data_type, shots)
        if not success:
            logger.error("任务提交真机失败")
            results = {"error": "任务提交真机失败"}
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 3、等待task返回结果
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_result, 3600, 5, job_id)
        if not success:
            logger.error(f"等待任务完成失败 [{job_id}]: {err_msg}")
            results = {"error": f"等待任务完成失败: {err_msg}"}
            self.set_results(job_id, results=results)
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        if self._final_response is None:
            logger.error("未获取到最终任务结果")
            results = {"error": "未获取到最终任务结果"}
            self.set_results(job_id, results=results)
            self.close_task()
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 获取结果并确保符合API schema要求
        raw_results = self._final_response.get("result")
        if raw_results is None:
            logger.warning("服务器返回的结果为空，使用默认结果")
            results = {"status": "do failed", "data": []}
        else:
            # 确保结果是有效的类型（str, int, list, dict）
            if isinstance(raw_results, (str, int, list, dict)):
                results = raw_results
            else:
                logger.warning(
                    f"结果类型不符合要求: {type(raw_results)}，转换为字符串")
                results = str(raw_results)

        # 记录最终结果用于调试
        logger.info(f"最终结果: {results}")

        self.set_results(job_id, results=results)
        self.close_task()
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def init_task(self, ip_address: str, port: int) -> bool:
        """
        初始化任务：连接服务器，启动心跳检测线程

        :param ip_address: 服务器IP地址
        :param port: 服务器端口
        :return: 连接是否成功
        """
        try:
            self.client = HanyuanConnection(ip_address, port)
            return self.client.connect()
        except Exception as e:
            logger.error(f"初始化任务失败: {e}")
            return False

    def close_task(self):
        """
        关闭任务：断开服务器连接
        """
        if self.client:
            self.client.disconnect()
            self.client = None

    def submit_task(self, job_id: str, qubit_num: int, data, data_type: str,
                    shots: int) -> bool:
        """
        提交任务执行

        :param job_id: 任务ID
        :param qubit_num: 量子比特数量
        :param data: 数据
        :param data_type: 数据类型
        :param shots: 执行次数
        :return: 提交是否成功
        """
        try:
            logger.info(f"提交任务: job_id={job_id}, data_type={data_type}, "
                        f"shots={shots}")

            processed_data = []
            # 检查data的格式，如果是包含basis_gate_list的字典
            if isinstance(data, dict) and 'basis_gate_list' in data:
                gate_list = data['basis_gate_list']
                logger.info(
                    f"从data['basis_gate_list']中提取gate列表: {gate_list}")
            else:
                # 如果data本身就是gate列表
                gate_list = data
                logger.info(f"data本身就是gate列表: {gate_list}")

            for i, gate in enumerate(gate_list):
                logger.info(f"处理第{i + 1}个gate: {gate}")
                gate_dict = {
                    "name": gate.name.upper(),  # 转换为大写以保持一致性
                    "targets": gate.targets,
                    "arg_value": gate.arg_value
                }
                logger.info(f"转换后的gate_dict: {gate_dict}")
                processed_data.append(gate_dict)

            logger.info(f'processed_data: {processed_data}')
            message = {
                "job_id": job_id,
                "data_type": data_type,
                "qubit_num": qubit_num,
                "shots": shots,
                "data": processed_data,
                "timestamp": time.time()
            }

            # 发送任务
            success = self.client.send_message(message)
            if success:
                logger.info(f"任务 {job_id} 提交成功")
                return True
            else:
                logger.error(f"任务 {job_id} 提交失败")
                return False
        except Exception as e:
            logger.error(f"提交任务时出错: {e}")
            return False

    def check_task_result(self, job_id: str) -> bool:
        """
        检查任务返回结果

        :param job_id: 任务ID
        :return: 任务是否完成
        """
        try:
            if not self.client or not self.client.is_connection_alive():
                logger.error("连接已断开")
                return False

            # 接收响应
            response = self.client.receive_message()
            if response is None:
                # 没有收到响应，任务可能仍在执行
                logger.info(f"任务 {job_id} 仍在执行中...")
                return False

            # 检查响应格式
            if not isinstance(response, dict):
                logger.warning(f"收到非字典格式的响应: {type(response)}")
                return False

            # 检查是否包含结果
            if "result" in response:
                logger.info(f"任务 {job_id} 已完成")
                # 保存最终结果供后续使用
                self._final_response = response
                logger.info(f"任务 {job_id} 已完成，结果: {response}")
                return True
            elif "error" in response:
                logger.error(f"任务 {job_id} 执行出错: {response['error']}")
                # 即使出错也保存响应，避免无限等待
                self._final_response = response
                return True
            elif "status" in response:
                status = response.get("status")
                if status in ["completed", "finished", "done"]:
                    logger.info(f"任务 {job_id} 已完成，状态: {status}")
                    self._final_response = response
                    return True
                elif status in ["failed", "error"]:
                    logger.error(f"任务 {job_id} 执行失败，状态: {status}")
                    self._final_response = response
                    return True
                elif status == "not_found":
                    # 任务未找到，继续等待
                    logger.info(f"任务 {job_id} 未找到，继续等待...")
                    return False

            # 任务仍在执行中
            logger.info(f"任务 {job_id} 仍在执行中...")
            return False

        except Exception as e:
            logger.error(f"检查任务结果时出错: {e}")
            return False


class HanyuanConnection:
    """
    中科酷原-汉原1 中性原子驱动连接真机
    Cascoldatom Hanyuan1 connection
    """

    def __init__(self, server_host: str, server_port: int):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.is_connected = False
        self.heartbeat_thread = None
        self.heartbeat_running = False

    def connect(self) -> bool:
        """建立TCP连接"""
        try:
            logger.info(
                f"正在连接到服务器 {self.server_host}:{self.server_port}")

            # 创建TCP连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 设置连接超时
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(None)  # 重置为阻塞模式
            self.is_connected = True

            # 启动心跳线程
            self.heartbeat_running = True
            self.heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

            logger.info(
                f"已连接到服务器 {self.server_host}:{self.server_port}")
            return True
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """断开TCP连接"""
        # 停止心跳线程
        self.heartbeat_running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f"断开连接时出错: {e}")
            finally:
                self.is_connected = False
                logger.info("已断开服务器连接")

    def send_message(self, message: dict) -> bool:
        """发送消息到服务器"""
        if not self.is_connected or not self.socket:
            logger.error("未连接到服务器")
            return False

        try:
            data = json.dumps(message, ensure_ascii=False).encode('utf-8')
            self.socket.send(data + b'\n')
            logger.info(
                f"发送消息给 {self.server_host}:{self.server_port}: {message}")
            return True
        except Exception as e:
            logger.error(
                f"发送消息给 {self.server_host}:{self.server_port} 失败: {e}")
            return False

    def receive_message(self) -> dict:
        """接收服务器消息"""
        if not self.is_connected or not self.socket:
            logger.error("未连接到服务器")
            return None

        try:
            # self.socket.settimeout(5)  # 设置接收超时
            data = self.socket.recv(4096)
            if not data:
                logger.warning("服务器关闭了连接")
                self.is_connected = False
                return None

            # 解码数据
            decoded_data = data.decode('utf-8')

            # 尝试解析JSON，处理可能的多个JSON对象
            try:
                message = json.loads(decoded_data)
            except json.JSONDecodeError as e:
                # 如果解析失败，尝试找到第一个完整的JSON对象
                logger.info(f"JSON解析失败，尝试修复: {e}")

                # 查找第一个完整的JSON对象
                brace_count = 0
                start_pos = -1
                message = None

                for i, char in enumerate(decoded_data):
                    if char == '{':
                        if brace_count == 0:
                            start_pos = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_pos != -1:
                            # 找到完整的JSON对象
                            json_str = decoded_data[start_pos:i + 1]
                            try:
                                message = json.loads(json_str)
                                logger.debug(f"成功解析JSON对象: {json_str}")
                                break
                            except json.JSONDecodeError as parse_error:
                                logger.error(f"解析JSON对象失败: {parse_error}")
                                # 继续查找下一个JSON对象
                                start_pos = -1
                                continue

                if message is None:
                    # 没有找到完整的JSON对象
                    logger.warning("无法解析任何有效的JSON对象")
                    self.is_connected = False
                    return None

            logger.info(
                f"收到来自 {self.server_host}:{self.server_port}"
                f"的消息: {message}")

            # 处理心跳响应
            if message.get("type") == "heartbeat_ack":
                return None  # 心跳响应不返回给上层

            return message
        except Exception as e:
            logger.error(
                f"接收来自 {self.server_host}:{self.server_port} 的消息失败: {e}")
            # 接收消息失败可能表示连接断开
            self.is_connected = False
            return None

    def _heartbeat_loop(self):
        """心跳循环"""
        while self.heartbeat_running and self.is_connected:
            try:
                # 发送心跳消息
                heartbeat_msg = {
                    "type": "heartbeat",
                    "timestamp": time.time()
                }

                success = self.send_message(heartbeat_msg)
                if not success:
                    logger.warning("心跳发送失败")
                    self.is_connected = False
                    break

                # 等待心跳间隔
                time.sleep(30)

            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                self.is_connected = False
                break

    def is_connection_alive(self) -> bool:
        """检查连接是否仍然活跃"""
        if not self.is_connected or not self.socket:
            return False

        try:
            # 检查socket状态
            self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return True
        except Exception:
            self.is_connected = False
            return False
