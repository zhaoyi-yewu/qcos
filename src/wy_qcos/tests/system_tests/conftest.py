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

import json
import os
import pprint
import pytest
from pathlib import Path

from wy_qcos.common.constant import Constant
from wy_qcos_client.client import Client
from wy_qcos.common.library import HttpCode, Library, _s
from wy_qcos.common.config import Config
from wy_qcos.tests.system_tests.common.library import StLibrary

GLOBAL_CONFIGS = {}
SAMPLES = {}


default_qcos_st_config_path = "/etc/qcos/qcos-st.toml"


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="Specify environment：dev, test, prod",
    )

    parser.addoption(
        "--config-path",
        dest="config_path",
        default=default_qcos_st_config_path,
        help="Specify config file path, default: "
        f"{default_qcos_st_config_path}",
    )


@pytest.fixture(scope="session")
def global_configs(request):
    env = request.config.getoption("--env")
    config_path = request.config.getoption("--config-path")
    success, err_msg, config = Library.read_toml_file(config_path)
    if not success:
        print("Can't find config file, default settings will be applied")
        config = {}

    current_path = os.path.dirname(__file__)
    top_dir = Path(current_path).resolve().parent.parent.parent.parent
    GLOBAL_CONFIGS["base_dir"] = str(top_dir)
    GLOBAL_CONFIGS["samples_dir"] = f"{top_dir}/samples"
    GLOBAL_CONFIGS["etc_dir"] = f"{top_dir}/etc"
    GLOBAL_CONFIGS["env"] = env
    api_server = config.get("ST_API_SERVER", {})
    api_host = api_server.get("ST_API_SERVER_IP", "127.0.0.1")
    api_port = api_server.get(
        "ST_API_SERVER_PORT", Config.API_SERVER_LISTEN_PORT
    )
    GLOBAL_CONFIGS["timeout"] = 150
    GLOBAL_CONFIGS["interval"] = 5
    GLOBAL_CONFIGS["max_login_attempts"] = Config.MAX_LOGIN_ATTEMPTS
    _admin_password = config["USERS"]["ADMIN_PASSWORD"]
    if Constant.ENCRYPTION_PREFIX in _admin_password:
        success, err_msg, decrypted_value = Library.decrypt_text(
            _admin_password,
            encryption_prefix=Constant.ENCRYPTION_PREFIX,
            fernet_key=Constant.DEFAULT_FERNET_KEY,
        )
        _admin_password = decrypted_value
    admin_user = "admin"
    admin_password = _admin_password or _s("123456")
    GLOBAL_CONFIGS["admin_user"] = admin_user
    GLOBAL_CONFIGS["admin_password"] = admin_password

    # Authenticate with admin credentials at the beginning
    client = Client(api_server_ip=api_host, api_server_port=api_port)
    admin_client = Client(api_server_ip=api_host, api_server_port=api_port)
    login_result = StLibrary.login(admin_client, admin_user, str(admin_password))
    token = login_result["access_token"]
    admin_client.set_token(token)
    GLOBAL_CONFIGS["client"] = client
    GLOBAL_CONFIGS["admin_client"] = admin_client

    # load configs
    load_configs()
    # print configs for debug purpose when test fails
    print("\nGLOBAL_CONFIGS:")
    pprint.PrettyPrinter().pprint(GLOBAL_CONFIGS)


def load_configs():
    """Load configs."""
    samples_dir = GLOBAL_CONFIGS["samples_dir"]
    SAMPLES["simple-qasm.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/simple-qasm.qasm"
    )
    SAMPLES["simple-qasm-1-bit.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/simple-qasm-1-bit.qasm"
    )
    SAMPLES["qasm3-1-bit.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/3.0/qasm3-1-bit.qasm"
    )
    SAMPLES["15_35.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/wirecut/15_35.qasm"
    )
    SAMPLES["simple-qubo.json"] = json.loads(
        Library.read_file(f"{samples_dir}/qubo/simple-qubo.json")
    )
    SAMPLES["qubo_102X102.json"] = json.loads(
        Library.read_file(f"{samples_dir}/qubo/qubo_102X102.json")
    )
