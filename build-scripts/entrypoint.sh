#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

export PS1="(${QCOS_CONTAINER_NAME})[$(pwd)]$ "

# Create QCOS config file
qcos_config_file_path=/etc/qcos/qcos.toml
qcos_extra_config_file_dir=/etc/qcos/conf.d

mkdir -p /etc/qcos/
mkdir -p ${qcos_extra_config_file_dir}
_DEBUG=${DEBUG:-false}

# check if file /etc/qcos/qcos.conf exists and create it if not
if [ -f "${qcos_config_file_path}" ]; then
  echo "QCOS config file: ${qcos_config_file_path} exists, use it"
else
  echo "QCOS config file: ${qcos_config_file_path} not exists. auto generate ...."
  cat << EOM > ${qcos_config_file_path}
[DEFAULT]
DEBUG = ${_DEBUG,,}
WORKERS = 8

[API_SERVER]
API_SERVER_LISTEN_IP = "${API_SERVER_LISTEN_IP:-0.0.0.0}"
API_SERVER_LISTEN_PORT = ${API_SERVER_LISTEN_PORT:-18400}
API_LOG_FILE = "${API_LOG_FILE:-/var/log/qcos/qcos-api.log}"
PREFECT_LOG_FILE = "${PREFECT_LOG_FILE:-/var/log/qcos/qcos-prefect.log}"

[DEVICES]
DEVICE_LIST = ["dummy", "hanyuan1", "tiangong100", "qiskit_aer_sim", "qiskit_qasm_sim"]
EOM
fi

# run QCOS
/usr/bin/qcos-api --config-file ${qcos_config_file_path} --config-dir ${qcos_extra_config_file_dir}
if [ "${DEV,,}" = "true" ]; then
  sleep infinity
fi
