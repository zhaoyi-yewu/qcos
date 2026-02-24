#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

wait_for_url=""
function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Entrypoint of QCOS container"
    echo ""
    echo "  -w, --wait-for  Wait for url is ready"
    echo "  -h, --help      Print this usage message"
    echo ""
}

opts=$(getopt -o w:h --long wait-for:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

while true; do
  case "$1" in
    -h | --help )     usage ; exit 0;    shift ;;
    -w | --wait-for ) wait_for_url="$2"; shift 2 ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# Create QCOS config file
qcos_config_file_path=/etc/qcos/qcos.toml
qcos_extra_config_file_dir=/etc/qcos/conf.d
qcos_st_config_file_path=/etc/qcos/qcos-st.toml
qcos_template_base_dir=/etc/qcos-template
qcos_template_config_file_path=${qcos_template_base_dir}/qcos.toml
qcos_template_st_config_file_path=${qcos_template_base_dir}/qcos-st.toml

mkdir -p /etc/qcos/
mkdir -p /etc/qcos/ssl
mkdir -p ${qcos_extra_config_file_dir}

# check if file /etc/qcos/qcos.conf exists and create it if not
if [ -f "${qcos_config_file_path}" ]; then
  echo "QCOS config file: ${qcos_config_file_path} exists, use it"
else
  echo "QCOS config file: ${qcos_config_file_path} not exists. auto generate ...."
  cp ${qcos_template_config_file_path} ${qcos_config_file_path}

  _DEBUG=${DEBUG:-false}
  _ENABLE_VIRT=${ENABLE_VIRT:-false}
  python3 -c "
def config(doc):
    doc['DEFAULT']['DEBUG'] = ${_DEBUG^}
    doc['DEFAULT']['MAX_JOBS'] = ${MAX_JOBS:-10000}
    doc['DEFAULT']['MAX_QUEUED_JOBS'] = ${MAX_QUEUED_JOBS:-1000}

    doc['VIRT']['ENABLE_VIRT'] = ${_ENABLE_VIRT^}
    doc['VIRT']['MAX_JOBS_PER_VIRTUAL_INSTANCE'] = ${MAX_JOBS_PER_VIRTUAL_INSTANCE:-10}
    doc['VIRT']['PASSWORD_SALT'] = '${PASSWORD_SALT:-123456}'

    doc['API_SERVER']['API_WORKERS'] = ${API_WORKERS:-8}
    doc['API_SERVER']['API_SERVER_LISTEN_IP'] = '${API_SERVER_LISTEN_IP:-}'
    doc['API_SERVER']['API_SERVER_LISTEN_PORT'] = ${API_SERVER_LISTEN_PORT:-18400}

    doc['PREFECT']['PREFECT_API_URL'] = '${PREFECT_API_URL:-http://127.0.0.1:4200/api}'
    doc['PREFECT']['PREFECT_SERVER_DATABASE_CONNECTION_URL'] = '${PREFECT_SERVER_DATABASE_CONNECTION_URL:-sqlite+aiosqlite:///var/qcos/db/prefect.db}'
    doc['PREFECT']['PREFECT_WORKER_QUERY_SECONDS'] = ${PREFECT_WORKER_QUERY_SECONDS:-1}
    doc['PREFECT']['PREFECT_WORKER_PREFETCH_SECONDS'] = ${PREFECT_WORKER_PREFETCH_SECONDS:-1}
    doc['PREFECT']['PREFECT_WORKER_HEARTBEAT_SECONDS'] = ${PREFECT_WORKER_HEARTBEAT_SECONDS:-30}
    doc['PREFECT']['PREFECT_LOCAL_STORAGE_PATH'] = '${PREFECT_LOCAL_STORAGE_PATH:-/var/qcos/storage}'
    doc['PREFECT']['PREFECT_LOGGING_LEVEL'] = '${PREFECT_LOGGING_LEVEL:-INFO}'

    doc['REDIS']['REDIS_SERVER_IP'] = '${REDIS_SERVER_IP:-127.0.0.1}'
    doc['REDIS']['REDIS_SERVER_PORT'] = ${REDIS_SERVER_PORT:-6379}

    doc['LOG']['API_LOG_FILE'] = '${REDIS_SERVER_IP:-127.0.0.1}'
    doc['LOG']['JOB_ENGINE_LOG_FILE'] = '${JOB_ENGINE_LOG_FILE:-/var/log/qcos/qcos-engine.log}'
    doc['LOG']['DEVICE_MONITOR_LOG_FILE'] = '${DEVICE_MONITOR_LOG_FILE:-/var/log/qcos/device-monitor.log}'
    doc['LOG']['LOG_FORMAT'] = '%(asctime)s | %(levelname)s | %(module)s:%(lineno)s %(message)s'

    doc['DEVICES']['DEVICE_LIST'] = [${DEVICE_LIST:-\"dummy\", \"qutip_sim\"}]

###############
import tomlkit
from tomlkit import comment, nl
config_file='${qcos_config_file_path}'
with open(config_file, 'r', encoding='utf-8') as f:
    doc = tomlkit.load(f)
config(doc)
with open(config_file, 'w', encoding='utf-8') as f:
    tomlkit.dump(doc, f)
  "
fi

# check if file /etc/qcos/qcos-st.conf exists and create it if not
if [ -f "${qcos_st_config_file_path}" ]; then
  echo "QCOS ST config file: ${qcos_st_config_file_path} exists, use it"
else
  echo "QCOS ST config file: ${qcos_st_config_file_path} not exists. auto generate ...."
  cp -f ${qcos_template_st_config_file_path} ${qcos_st_config_file_path}
fi
echo "Prefect API URL: ${PREFECT_API_URL}"

# wait optional url is ready
if [ -n "${wait_for_url}" ]; then
  echo "Wait for url: ${wait_for_url}"
  until wget -q --spider ${wait_for_url}
  do echo "waiting for url ..."
    sleep 2
  done
  echo "url: ${wait_for_url} is ready"
fi

# run QCOS under venv
source /var/lib/qcos/venv/default/bin/activate
/usr/bin/qcos-api --config-file ${qcos_config_file_path} --config-dir ${qcos_extra_config_file_dir}
sleep infinity
