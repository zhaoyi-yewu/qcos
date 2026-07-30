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

from wy_qcos.common.constant import Constant, HttpCode
from wy_qcos_client.client import Client
from wy_qcos.common.library import Library
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
    api_host = config.get("ST_API_SERVER", {}).get(
        "ST_API_SERVER_IP", Config.API_SERVER.API_SERVER_LISTEN_IP
    )
    api_port = config.get("ST_API_SERVER", {}).get(
        "ST_API_SERVER_PORT", Config.API_SERVER.API_SERVER_LISTEN_PORT
    )
    GLOBAL_CONFIGS["timeout"] = 150
    GLOBAL_CONFIGS["api_host"] = api_host
    GLOBAL_CONFIGS["api_port"] = api_port
    GLOBAL_CONFIGS["interval"] = 5
    GLOBAL_CONFIGS["password_salt"] = Config.VIRT.PASSWORD_SALT
    GLOBAL_CONFIGS["max_login_attempts"] = Config.USERS.MAX_LOGIN_ATTEMPTS
    _admin_password = config.get("USERS", {}).get("DEFAULT_ADMIN_PASSWORD", "")
    if Constant.ENCRYPTION_PREFIX in _admin_password:
        success, err_msg, decrypted_value = Library.decrypt_text(
            _admin_password,
            encryption_prefix=Constant.ENCRYPTION_PREFIX,
            fernet_key=Constant.DEFAULT_FERNET_KEY,
        )
        _admin_password = decrypted_value
    admin_user = "admin"
    admin_password = _admin_password or Constant.DEFAULT_ADMIN_PASSWORD
    GLOBAL_CONFIGS["admin_user"] = admin_user
    GLOBAL_CONFIGS["admin_password"] = admin_password

    # Authenticate with admin credentials at the beginning
    client = None
    admin_client = None
    virtual_instance_client = None

    # try login when auth_mode is unknown
    client, admin_client, virtual_instance_client = get_client(
        api_host, api_port, admin_user, admin_password
    )

    # set auth_mode to 'no' (admin)
    set_auth_mode(
        admin_client, virtual_instance_client, auth_mode=Constant.AUTH_MODE_NO
    )

    # login again to make sure all clients are authenticated
    client, admin_client, virtual_instance_client = get_client(
        api_host, api_port, admin_user, admin_password
    )

    GLOBAL_CONFIGS["client"] = client
    GLOBAL_CONFIGS["admin_client"] = admin_client
    GLOBAL_CONFIGS["virtual_instance_client"] = virtual_instance_client

    # load configs
    load_configs()

    # print configs for debug purpose when test fails
    print("\nGLOBAL_CONFIGS:")
    pprint.PrettyPrinter().pprint(GLOBAL_CONFIGS)


def get_client(api_host, api_port, admin_user, admin_password):
    """Get client object."""
    client = None
    admin_client = None
    virtual_instance_client = None
    try:
        client = Client(api_server_ip=api_host, api_server_port=api_port)
    except Exception:  # noqa: S110
        pass

    try:
        admin_client = Client(api_server_ip=api_host, api_server_port=api_port)
        login_result = StLibrary.login(
            admin_client, admin_user, str(admin_password)
        )
        token = login_result["access_token"]
        admin_client.set_token(token)
    except Exception:  # noqa: S110
        pass

    # Authenticate with virtual_instance credentials at the beginning
    # Create admin virtual instance ID with
    # device_names=["all"] and instance_id="all"
    try:
        virtual_instance_client = Client(
            api_server_ip=api_host, api_server_port=api_port
        )
        admin_device_names = ["all"]
        admin_instance_id = "all"
        success, err_msg, admin_vi_id = Library.encrypt_virtual_instance_id(
            admin_device_names,
            admin_instance_id,
            salt=Config.VIRT.PASSWORD_SALT,
            encode=True,
        )
        if success:
            virtual_instance_client.request_headers = {
                "x-qcos-virtual-instance-id": admin_vi_id,
            }
    except Exception:  # noqa: S110
        pass
    return client, admin_client, virtual_instance_client


def set_auth_mode(
    admin_client, virtual_instance_client, auth_mode=Constant.AUTH_MODE_NO
):
    """Set auth mode.

    Args:
        admin_client (Client): Admin client object.
        virtual_instance_client (Client): Virtual client object.
        auth_mode (str, optional): Auth mode. Defaults to "no".
    """
    status_code, reason, text, result = admin_client.set_user_mgmt(auth_mode)
    if status_code != HttpCode.SUCCESS_OK:
        raise Exception(status_code, reason, text)
    auth_results = json.loads(text)
    use_auth_virtual_instance = False
    error = auth_results.get("error", {})
    if error:
        if "Failed to auth" in error.get("message", ""):
            use_auth_virtual_instance = True
        else:
            raise Exception(status_code, reason, text)
    if use_auth_virtual_instance:
        status_code, reason, text, result = (
            virtual_instance_client.set_user_mgmt(auth_mode)
        )
        if status_code != HttpCode.SUCCESS_OK:
            raise Exception(status_code, reason, text)
        auth_results = json.loads(text)
        error = auth_results.get("error", {})
        if error:
            raise Exception(status_code, reason, text)


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
