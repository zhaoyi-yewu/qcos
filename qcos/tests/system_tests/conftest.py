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

import os
import pprint
import pytest
from pathlib import Path

from qcos.client.client import Client
from qcos.common.library import Library
from qcos.common.config import Config

GLOBAL_CONFIGS = {}
SAMPLES = {}


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="dev",
        help="Specify environment：dev, test, prod"
    )

    parser.addoption(
        "--config-path",
        dest="config_path",
        default="/etc/qcos/qcos-st.toml",
        help="Specify config file path"
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
    top_dir = Path(current_path).resolve().parent.parent.parent
    GLOBAL_CONFIGS["base_dir"] = str(top_dir)
    GLOBAL_CONFIGS["samples_dir"] = f"{top_dir}/samples"
    GLOBAL_CONFIGS["env"] = env
    api_server = config.get("API_SERVER", {})
    api_host = api_server.get("API_SERVER_IP", "127.0.0.1")
    api_port = api_server.get("API_SERVER_PORT", Config.API_SERVER_LISTEN_PORT)
    client = Client(api_listen_ip=api_host, api_port=api_port)
    GLOBAL_CONFIGS["client"] = client
    GLOBAL_CONFIGS["timeout"] = 30
    GLOBAL_CONFIGS["interval"] = 5
    load_configs()
    # print configs for debug purpose when test fails
    print("\nGLOBAL_CONFIGS:")
    pprint.PrettyPrinter().pprint(GLOBAL_CONFIGS)
    print("\nSamples:")
    pprint.PrettyPrinter().pprint(SAMPLES)


def load_configs():
    """
    Load configs
    """
    samples_dir = GLOBAL_CONFIGS["samples_dir"]
    SAMPLES["simple-qasm.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/simple-qasm.qasm")
    SAMPLES["simple-qasm-1-bit.qasm"] = Library.read_file(
        f"{samples_dir}/qasm/2.0/simple-qasm-1-bit.qasm")
