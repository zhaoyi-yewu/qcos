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
qcos_config_file_path=/etc/qcos/qcos.conf
qcos_extra_config_file_dir=/etc/qcos/conf.d
mkdir -p /etc/qcos/
mkdir -p ${qcos_extra_config_file_dir}

# check if file /etc/qcos/qcos.conf exists and create it if not
if [ -f "${qcos_config_file_path}" ]; then
  echo "QCOS config file: ${qcos_config_file_path} exists, ignore it"
else
  echo "QCOS config file: ${qcos_config_file_path} not exists. auto generate ...."
  cat << EOM > ${qcos_config_file_path}
[DEFAULT]
debug = ${DEBUG:-False}

[API_SERVER]
api_server_listen_ip = ${API_SERVER_LISTEN_IP:-0.0.0.0}
api_server_port = ${API_SERVER_PORT:-18400}
api_log_file = ${API_LOG_FILE:-/var/log/qcos/qcos-api.log}
EOM
fi

# run QCOS
python3 /root/qcos/api_server.py --config-file ${qcos_config_file_path} --config-dir ${qcos_extra_config_file_dir}
sleep infinity
