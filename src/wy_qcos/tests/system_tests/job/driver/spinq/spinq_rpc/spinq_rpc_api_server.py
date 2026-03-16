#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

# ruff: noqa: E402
# load driver venv
from wy_qcos.common.config import Config
from wy_qcos.common.library import Library

org_path = Library.set_driver_venv_path("DriverSpinQRpc", Config.VENV_DIR)

import enum
import logging
import json
import sys
import time
import zerorpc
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

from wy_qcos.common.library import Library

logger = logging.getLogger(__name__)
top_dir = Library.get_top_dir()


# SpinQ RPC Server simulator
rpc_listen_ip = "0.0.0.0"
rpc_listen_port = 4242
_shots = 0
PID_DIR = "/var/run/qcos"
PID_FILE = f"{PID_DIR}/driver-spinq-api-server.pid"

# config data (from toml file)
_config_data = None
_qubits_num = 57
_coupling_list = []
_qpu_configs = None

# tasks: task_id -> task_info
_tasks = {}  # task info, includes measures and shots


def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(config_file_path: str):
    """Load config files.

    Args:
        config_file_path: path to config file
    """
    global _config_data, _qubits_num, _coupling_list, _qpu_configs

    # find config file
    config_file = Path(config_file_path)
    if not config_file.exists():
        logger.warning(
            "Config file not found, using default values "
            "(25 qubits, simple coupling)"
        )
        raise FileNotFoundError(f"Config file not found: {config_file_path}")

    # read toml file
    success, err_msg, config_data = Library.read_toml_file(config_file_path)
    if not success:
        logger.warning(
            f"Failed to read config file: {err_msg}, using default values"
        )
        return None

    _config_data = config_data

    # get qpu_configs
    qpu_configs = (
        config_data.get("spinq_rpc", {})
        .get("transpiler", {})
        .get("qpu_configs", {})
    )

    # save qpu_configs in dict format
    _qpu_configs = qpu_configs.copy()
    logger.info(f"Loaded complete qpu_configs: {len(_qpu_configs)} keys")

    # get number of qubits
    _qubits_num = qpu_configs.get("qubits")
    if not _qubits_num:
        raise ValueError("qubits_num not found in config")
    logger.info(f"Loaded config: qubits_num={_qubits_num}")

    # get coupling_list from coupler_map
    coupler_map = qpu_configs.get("coupler_map")
    if not coupler_map:
        raise ValueError("coupler_map not found in config")
    _coupling_list = []

    # convert "Q0", "Q1" into numerical index
    def qubit_name_to_index(name):
        """Convert "Q0" into numerical index: 0."""
        if isinstance(name, str) and name.startswith("Q"):
            try:
                return int(name[1:])
            except ValueError:
                return None
        return None

    # iterate all coupling map and generate coupling list
    for coupler_name, qubit_pair in coupler_map.items():
        if isinstance(qubit_pair, list) and len(qubit_pair) == 2:
            q0_name, q1_name = qubit_pair[0], qubit_pair[1]
            q0_idx = qubit_name_to_index(q0_name)
            q1_idx = qubit_name_to_index(q1_name)

            if q0_idx is not None and q1_idx is not None:
                # append coupling pair to coupling list
                _coupling_list.append((q0_idx, q1_idx))
                _coupling_list.append((q1_idx, q0_idx))

    logger.info(f"Loaded {len(_coupling_list)} coupling pairs from config")
    return _config_data, _qubits_num, _coupling_list, _qpu_configs


class TaskStatus(enum.Enum):
    """Task status."""

    finished = 0
    failed = 1
    running = 2
    queueing = 3
    not_found = 4


def request_login(username, password):
    """Request login.

    Args:
        username: username
        password: password

    Returns:
        response
    """
    # check if qpu_configs is loaded
    if _qpu_configs is None:
        raise RuntimeError(
            "qpu_configs not loaded. Please ensure load_config() "
            "was called successfully before handling requests."
        )

    # load chip name from configs
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
        "coupling_list": _qpu_configs,
        "qpu_configs": _qpu_configs,
    }
    logger.info(
        f"[request_login|request] username: {username}, password: {password}"
    )
    time.sleep(1)
    json_response = json.dumps(response)
    logger.info(f"[request_login|response] {json_response}")
    return json_response


def request_logout(username, session_id):
    """Request logout.

    Args:
        username: username
        session_id: session_id
    """
    global _shots
    logger.info(
        f"[request_logout|request] username: {username}, "
        f"session_id: {session_id}"
    )
    _shots = 0


def push_task(task_name, task_gates, measures, task_desc, shots, session_id):
    """Push task.

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
    global _shots
    status = 0
    task_id = 1000
    response = (status, task_id)
    _shots = shots

    # store results, includes measures and shots
    _tasks[task_id] = {
        "task_name": task_name,
        "task_gates": task_gates,
        "measures": measures,  # store measures bits list
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
    """Get task status.

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
    """Get task result.

    Args:
        task_id: task_id
        session_id: session id

    Returns:
        response
    """
    # convert_results(_results["task_result"]) called in driver
    # convert_results expects: results["qubit_result"]
    # results format: {"task_result": {"qubit_result": {...}}}

    # get measures and shots from task
    task_info = _tasks.get(task_id)
    if not task_info:
        logger.warning(f"Task {task_id} not found, returning empty result")
        return {}
    measures = task_info.get("measures", [])
    shots = task_info.get("shots", 0)

    # generate results
    num_measures = len(measures)
    if num_measures > 0:
        qubit_result = Library.generate_binary_combinations(
            num_measures, shots
        )
    else:
        # if no measures, return empty results
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


def main(cmd_args=None):
    server = None
    try:
        # config parser
        parser = ArgumentParser(formatter_class=RawDescriptionHelpFormatter)
        default_config_file = f"{top_dir}/etc/qcos/st-conf.d/spinq_rpc.toml"
        parser.add_argument(
            "-c",
            "--config-file",
            dest="config_file",
            default=default_config_file,
            help="Config file",
        )
        # parse arguments
        args = parser.parse_args(args=cmd_args)
        config_file = args.config_file

        # init logging
        init_logging()

        # load configs
        load_config(config_file)

        # kill existing process
        Library.kill_pid(PID_FILE)
        time.sleep(2)  # wait for socket to be released
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

        # start SpinQ API service
        logger.info(f"SpinQ API Server simulator started on {bind_address}")
        logger.info("Press Ctrl+C to stop service ...")

        server.bind(bind_address)
        server.run()

        return 0

    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2
    finally:
        if server:
            logger.info("\nServer is stopped")
            server.close()
        try:
            Library.remove_pid_file(PID_FILE)
        except Exception as e:
            logger.warning(f"Failed to remove PID file: {e}")


if __name__ == "__main__":
    main()
