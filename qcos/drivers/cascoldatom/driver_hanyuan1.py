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
from loguru import logger
import time
from schema import Optional, Or

import requests
from jsonrpcclient import request

from qcos.common.constant import Constant, HttpMethod
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

    verbose = False

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
        self._final_response = None
        self.server_host = None
        self.server_port = None
        self.base_url = None

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
        ip_address = extra_configs.get("ip_address", "100.78.62.2")
        port = extra_configs.get("port", 18402)

        # 1、初始化任务连接
        self.init_task(ip_address, port)

        # 2、提交任务
        success, reason, text, result = (
            self.submit_task(job_id, num_qubits, data, data_type, shots))
        if not success:
            logger.error(f"任务提交真机失败: {reason}")
            results = {"error": f"任务提交真机失败: {reason}"}
            self.set_results(job_id, results=results)
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        # 3、等待任务返回结果
        success, err_msg, _ = Library.loop_with_timeout(
            self.check_task_result, 180, 5, job_id)
        if not success:
            logger.error(f"等待任务完成失败 [{job_id}]: {err_msg}")
            results = {"error": f"等待任务完成失败: {err_msg}"}
            self.set_results(job_id, results=results)
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return

        if self._final_response is None:
            logger.error("未获取到最终任务结果")
            results = {"error": "未获取到最终任务结果"}
            self.set_results(job_id, results=results)
            self.set_status(self.DRIVER_STATUS_ONLINE)
            return
        else:
            raw_results = self._final_response.get("result")
            if raw_results is None:
                logger.warning("服务器返回的结果为空，使用默认结果")
                results = {"服务器返回的结果为空"}
            else:
                results = raw_results.get("result")

        self.set_results(job_id, results=results)
        self.set_status(self.DRIVER_STATUS_ONLINE)

    def init_task(self, ip_address: str, port: int):
        """
        初始化任务：初始化rpc调用url

        :param ip_address: 服务器IP地址
        :param port: 服务器端口
        """
        self.server_host = ip_address
        self.server_port = port

        api_version = "v1"
        self.base_url = f"http://{ip_address}:{port}/api/{api_version}/job"

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        """
        Print API response

        :param status_code: 状态码
        :param reason: 原因
        :param text: 响应内容
        :param result: 响应结果
        """
        if DriverHanyuan1.verbose:
            print(f"Response: status_code: {status_code}, reason: {reason}, "
                  f"text: {text}, result: {result}")

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        """
        调用JSON-RPC方法

        :param url: JSON-RPC URL
        :param method_name: 方法名
        :param data: 数据
        :param params: 参数
        :return: 响应结果
        """
        status_code = None
        reason = None
        text = None
        result = None
        try:
            jsonrpc_data = request(method_name, params={"body": data})

            status_code, reason, text, response_obj = Library.call_http_api(
                url, method=HttpMethod.POST, json=jsonrpc_data,
                params=params, func_name=method_name,
                debug=DriverHanyuan1.verbose)

            # 解析Response对象获取JSON数据
            if response_obj and hasattr(response_obj, 'json'):
                try:
                    result = response_obj.json()
                except Exception as e:
                    logger.warning(f"解析JSON响应失败: {e}")
                    result = None
            else:
                result = None

        except requests.exceptions.ConnectionError as ce:
            status_code = -1
            reason = f"Connection error: {str(ce)}"
        except Exception as e:
            status_code = -1
            reason = str(e)
        DriverHanyuan1.print_api_response(status_code, reason, text, result)
        return status_code, reason, text, result

    def submit_task(self, job_id: str, num_qubits: int, data: list,
                    data_type: str, shots: int) -> tuple:
        """
        提交任务执行

        :param job_id: 任务ID
        :param num_qubits: 量子比特数量
        :param data: 数据
        :param data_type: 数据类型
        :param shots: 执行次数
        :return: (success, reason, text, result)
        """
        try:
            # 处理数据格式
            gate_list = data.get('basis_gate_list', data) \
                if isinstance(data, dict) else data

            processed_data = []
            for gate in gate_list:
                gate_dict = {
                    "name": gate.name.upper(),
                    "targets": gate.targets,
                    "arg_value": gate.arg_value
                }
                processed_data.append(gate_dict)

            # 构造请求数据
            request_data = {
                "job_id": job_id,
                "data": processed_data,
                "data_type": data_type,
                "shots": shots,
                "qubit_num": num_qubits,
                "timestamp": time.time()
            }

            method_name = "submit_task"
            status_code, reason, text, result = self.call_json_rpc(
                self.base_url, method_name, request_data)

            # 检查JSON-RPC响应
            if status_code == 200 and result:
                if isinstance(result, dict):
                    if "error" in result:
                        logger.error(f"JSON-RPC错误: {result['error']}")
                        return False, "JSON-RPC错误", text, result
                    elif "result" in result:
                        return True, reason, text, result
                    else:
                        logger.warning(f"未知的JSON-RPC响应格式: {result}")
                        return False, "未知的JSON-RPC响应格式", text, result
                else:
                    logger.warning(f"响应格式不是字典: {type(result)}")
                    return False, "响应格式错误", text, result
            else:
                return False, reason, text, result

        except Exception as e:
            logger.error(f"提交任务时出错: {e}")
            return False, str(e), None, None

    def check_task_result(self, job_id: str) -> bool:
        """
        检查任务返回结果

        :param job_id: 任务ID
        :return: 任务是否完成
        """
        try:
            # 构造请求数据
            request_data = {
                "job_id": job_id
            }

            method_name = "query_task_result"
            status_code, reason, text, result = self.call_json_rpc(
                self.base_url, method_name, request_data)

            if status_code is None:
                logger.error(f"查询任务结果失败: {reason}")
                return False

            if status_code == 200 and result:
                # 检查JSON-RPC响应是否成功
                if isinstance(result, dict):
                    if "error" in result:
                        logger.error(f"JSON-RPC错误: {result['error']}")
                        return False
                    elif "result" in result:
                        # 检查任务状态
                        task_response = result["result"]
                        if isinstance(task_response, dict):
                            status = task_response.get("status")
                            if status == "completed":
                                # 任务完成，保存结果
                                self._final_response = result
                                return True
                            elif status == "running":
                                # 任务正在执行中，继续等待
                                logger.info(f"任务 {job_id} 正在执行中，继续等待...")
                                return False
                            elif status == "failed":
                                # 任务失败
                                logger.error(f"任务 {job_id} 执行失败: {task_response.get('message', '未知错误')}")
                                logger.error(f"任务 {job_id} 执行失败: "
                                    f"{task_response.get('message', '未知错误')}")
                                self._final_response = result
                                return True
                            elif status == "not_found":
                                # 任务未找到
                                logger.info(f"任务 {job_id} 未找到")
                                return False
                            else:
                                logger.warning(f"未知的任务状态: {status}")
                                return False
                        else:
                            logger.warning(f"响应格式不是字典: {type(task_response)}")
                            return False
                    else:
                        logger.warning(f"未知的JSON-RPC响应格式: {result}")
                        return False
                else:
                    logger.warning(f"响应格式不是字典: {type(result)}")
                    return False
            else:
                logger.error(f"查询任务结果失败: {reason}")
                return False

        except Exception as e:
            logger.error(f"检查任务结果时出错: {e}")
            return False
