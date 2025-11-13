#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

import enum
import logging
import json
import time
import zerorpc
from pathlib import Path

from qcos.common.library import Library

logger = logging.getLogger(__name__)


# SpinQ RPC Server simulator
rpc_listen_ip = "0.0.0.0"
rpc_listen_port = 4242
_shots = 0
PID_DIR = "/var/run/qcos"
PID_FILE = f"{PID_DIR}/driver-spinq-api-server.pid"

# 配置数据（从 TOML 文件加载）
_config_data = None
_qubits_num = 57
_coupling_list = []
_qpu_configs = None  # 保存完整的 qpu_configs（字典格式）

# 任务存储：task_id -> task_info
_tasks = {}  # 存储任务信息，包括 measures 和 shots


def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config():
    """从 TOML 配置文件加载配置"""
    global _config_data, _qubits_num, _coupling_list, _qpu_configs

    # 查找第一个存在的配置文件
    config_file = Path("/etc/qcos/conf.d/spinq_rpc.toml")
    if not config_file.exists():
        logger.warning(
            "Config file not found, using default values "
            "(25 qubits, simple coupling)"
        )
        raise FileNotFoundError(f"Config file not found: {config_file}")

    # 读取 TOML 文件
    success, err_msg, config_data = Library.read_toml_file(str(config_file))
    if not success:
        logger.warning(
            f"Failed to read config file: {err_msg}, using default values"
        )
        return

    _config_data = config_data

    # 提取 qpu_configs
    qpu_configs = (
        config_data.get("spinq_rpc", {})
        .get("transpiler", {})
        .get("qpu_configs", {})
    )

    # 保存完整的 qpu_configs（字典格式）
    _qpu_configs = qpu_configs.copy()
    logger.info(f"Loaded complete qpu_configs: {len(_qpu_configs)} keys")

    # 获取 qubits 数量
    _qubits_num = qpu_configs.get("qubits")
    if not _qubits_num:
        raise ValueError("qubits_num not found in config")
    logger.info(f"Loaded config: qubits_num={_qubits_num}")

    # 从 coupler_map 生成 coupling_list
    coupler_map = qpu_configs.get("coupler_map")
    if not coupler_map:
        raise ValueError("coupler_map not found in config")
    _coupling_list = []

    # 将 "Q0", "Q1" 格式转换为数字索引
    def qubit_name_to_index(name):
        """将 "Q0" 格式转换为数字索引 0"""
        if isinstance(name, str) and name.startswith("Q"):
            try:
                return int(name[1:])
            except ValueError:
                return None
        return None

    # 遍历所有耦合器，生成耦合列表
    for coupler_name, qubit_pair in coupler_map.items():
        if isinstance(qubit_pair, list) and len(qubit_pair) == 2:
            q0_name, q1_name = qubit_pair[0], qubit_pair[1]
            q0_idx = qubit_name_to_index(q0_name)
            q1_idx = qubit_name_to_index(q1_name)

            if q0_idx is not None and q1_idx is not None:
                # 添加双向耦合
                _coupling_list.append((q0_idx, q1_idx))
                _coupling_list.append((q1_idx, q0_idx))

    logger.info(f"Loaded {len(_coupling_list)} coupling pairs from config")


class TaskStatus(enum.Enum):
    """Task status"""

    finished = 0
    failed = 1
    running = 2
    queueing = 3
    not_found = 4


def request_login(username, password):
    """Request login

    Args:
        username: username
        password: password

    Returns:
        response
    """
    # 检查配置是否已加载
    if _qpu_configs is None:
        raise RuntimeError(
            "qpu_configs not loaded. Please ensure load_config() "
            "was called successfully before handling requests."
        )

    # 从配置中获取芯片名称
    chip_name = "chip_name"
    if _config_data:
        chip_name = _config_data.get("spinq_rpc", {}).get(
            "alias_name", "SpinQ Superconducting QPU"
        )

    response = {
        "return_code": 0,
        "qubits_num": _qubits_num,
        "session_id": "1000000000000000000000000000000000000001",
        "chip_name": chip_name,
        "coupling_list": _coupling_list,
        "qpu_configs": _qpu_configs,  # 添加：返回完整的 qpu_configs（字典格式）
    }
    logger.info(
        f"[request_login|request] username: {username}, password: {password}"
    )
    time.sleep(1)
    json_response = json.dumps(response)
    logger.info(f"[request_login|response] {json_response}")
    return json_response


def request_logout(username, session_id):
    """Request logout

    Args:
        username: username
        session_id: session_id
    """
    logger.info(
        f"[request_logout|request] username: {username}, "
        f"session_id: {session_id}"
    )
    _shots = 0


def push_task(task_name, task_gates, measures, task_desc, shots, session_id):
    """Push task

    Args:
        task_name: task name
        task_gates: task gates
        measures: measures
        task_desc: task description
        shots: shots
        session_id: session id

    Returns:
        response
    """
    status = 0
    task_id = 1000
    response = (status, task_id)
    _shots = shots

    # 保存任务信息，包括 measures 和 shots
    _tasks[task_id] = {
        "task_name": task_name,
        "task_gates": task_gates,
        "measures": measures,  # 保存测量比特列表
        "task_desc": task_desc,
        "shots": shots,
        "session_id": session_id,
    }
    time.sleep(5)
    logger.info(
        f"[push_task|request] task_name: {task_name}, "
        f"task_gates: {task_gates}, measures: {measures}, "
        f"task_desc: {task_desc}, shots: {shots}, session_id: {session_id}"
    )
    logger.info(f"[push_task|response] {response}")
    return response


def get_task_status(task_id, session_id):
    """Get task status

    Args:
        task_id: task_id
        session_id: session id

    Returns:
        response
    """

    task_status = TaskStatus.finished.value
    response = task_status
    logger.info(
        f"[get_task_status|request] task_id: {task_id}, "
        f"session_id: {session_id}"
    )
    time.sleep(2)
    logger.info(f"[get_task_status|response] {response}")
    return response


def get_task_result(task_id, session_id):
    """Get task result

    Args:
        task_id: task_id
        session_id: session id

    Returns:
        response
    """
    # 返回格式需要与驱动期望一致：
    # driver 中调用 convert_results(_results["task_result"])
    # convert_results 期望 results["qubit_result"]
    # 所以返回格式应该是: {"task_result": {"qubit_result": {...}}}

    # 从任务信息中获取 measures 和 shots
    task_info = _tasks.get(task_id)
    if not task_info:
        logger.warning(f"Task {task_id} not found, returning empty result")
        return {}
    measures = task_info.get("measures", [])
    shots = task_info.get("shots", 0)

    # 根据 measures 的长度生成正确的结果
    num_measures = len(measures)
    if num_measures > 0:
        # 使用 Library.generate_binary_combinations 生成所有可能的二进制组合
        qubit_result = Library.generate_binary_combinations(
            num_measures, shots
        )
    else:
        # 如果没有 measures，返回空结果
        qubit_result = {}
        logger.warning(
            f"Task {task_id} has no measures, returning empty result"
        )
    response = {"task_result": {"qubit_result": qubit_result}}
    logger.info(
        f"[get_task_result|request] task_id: {task_id}, "
        f"session_id: {session_id}"
    )
    time.sleep(2)
    json_response = json.dumps(response)
    logger.info(f"[get_task_result|response] {json_response}")
    return json_response


def main():
    # init logging
    init_logging()

    # 加载配置文件
    load_config()

    # kill existing process
    Library.kill_pid(PID_FILE)
    Library.mkdir(PID_DIR)
    Library.create_pid_file(PID_FILE)

    service = {
        "request_login": request_login,
        "request_logout": request_logout,
        "push_task": push_task,
        "get_task_status": get_task_status,
        "get_task_result": get_task_result,
    }
    server = zerorpc.Server(service, heartbeat=5)
    bind_address = f"tcp://{rpc_listen_ip}:{rpc_listen_port}"

    # 启动服务
    logger.info(f"SpinQ API Server simulator started on {bind_address}")
    logger.info("Press Ctrl+C to stop service ...")
    try:
        server.bind(bind_address)
        server.run()
    except KeyboardInterrupt:
        logger.info("\nServer is stopped")


if __name__ == "__main__":
    main()
