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
db_migration=false
no_exit=false

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Entrypoint of QCOS container"
    echo ""
    echo "  -w, --wait-for      Wait for url is ready"
    echo "  -m, --db-migration  Perform database migration before start qcos-api"
    echo "  -n, --no-exit       Don't exit when qcos-api process exits (default: false)"
    echo "  -h, --help          Print this usage message"
    echo ""
}

opts=$(getopt -o w:mnh --long wait-for:,db-migration,no-exit,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

while true; do
  case "$1" in
    -h | --help )     usage ; exit 0;    shift ;;
    -w | --wait-for ) wait_for_url="$2"; shift 2 ;;
    -m | --db-migration ) db_migration=true; shift ;;
    -n | --no-exit ) no_exit=true; shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# Create QCOS config file
qcos_template_base_dir=/etc/qcos-template
# qcos configs
qcos_config_file_path=/etc/qcos/qcos.toml
qcos_extra_config_file_dir=/etc/qcos/conf.d
qcos_template_config_file_path=${qcos_template_base_dir}/qcos.toml
# roles configs
qcos_roles_config_dir=/etc/qcos/roles
qcos_template_roles_config_dir=${qcos_template_base_dir}/roles
# st configs
qcos_st_config_file_path=/etc/qcos/qcos-st.toml
qcos_st_config_dir=/etc/qcos/st-conf.d
qcos_template_st_config_file_path=${qcos_template_base_dir}/qcos-st.toml
qcos_template_st_config_dir=${qcos_template_base_dir}/st-conf.d

mkdir -p /var/log/qcos
chmod 777 /var/log/qcos
mkdir -p /etc/qcos/
mkdir -p /etc/qcos/roles
mkdir -p /etc/qcos/ssl
mkdir -p ${qcos_extra_config_file_dir}
mkdir -p ${qcos_st_config_dir}

# load venv
venv_dir="/var/lib/qcos/venv/default"
venv_site_package_dir="${venv_dir}/lib/python3.11/site-packages"
source ${venv_dir}/bin/activate

# check if file /etc/qcos/qcos.conf exists and create it if not
if [ -f "${qcos_config_file_path}" ]; then
  echo "QCOS config file: ${qcos_config_file_path} exists, use it"
else
  echo "QCOS config file: ${qcos_config_file_path} not exists. auto generate ...."
  cp ${qcos_template_config_file_path} ${qcos_config_file_path}

  _DEBUG=${DEBUG:-false}
  _AUTH_MODE=${QCOS_AUTH_MODE:-no}
  python3 -c "
def config(conf):
    conf['DEFAULT']['DEBUG'] = ${_DEBUG^}
    conf['DEFAULT']['MAX_JOBS'] = ${MAX_JOBS:-10000}
    conf['DEFAULT']['MAX_QUEUED_JOBS'] = ${MAX_QUEUED_JOBS:-1000}
    conf['DEFAULT']['AUTH_MODE'] = '${_AUTH_MODE}'
    conf['VIRT']['MAX_JOBS_PER_VIRTUAL_INSTANCE'] = ${MAX_JOBS_PER_VIRTUAL_INSTANCE:-10}
    conf['VIRT']['PASSWORD_SALT'] = '${PASSWORD_SALT:-123456}'

    conf['API_SERVER']['API_WORKERS'] = ${API_WORKERS:-8}
    conf['API_SERVER']['API_SERVER_LISTEN_IP'] = '${API_SERVER_LISTEN_IP:-}'
    conf['API_SERVER']['API_SERVER_LISTEN_PORT'] = ${API_SERVER_LISTEN_PORT:-18400}

    conf['PREFECT']['PREFECT_API_URL'] = '${PREFECT_API_URL:-http://127.0.0.1:4200/api}'
    conf['PREFECT']['PREFECT_SERVER_DATABASE_CONNECTION_URL'] = '${PREFECT_SERVER_DATABASE_CONNECTION_URL:-sqlite+aiosqlite:///var/qcos/db/prefect.db}'
    conf['PREFECT']['PREFECT_WORKER_QUERY_SECONDS'] = ${PREFECT_WORKER_QUERY_SECONDS:-1}
    conf['PREFECT']['PREFECT_WORKER_PREFETCH_SECONDS'] = ${PREFECT_WORKER_PREFETCH_SECONDS:-1}
    conf['PREFECT']['PREFECT_WORKER_HEARTBEAT_SECONDS'] = ${PREFECT_WORKER_HEARTBEAT_SECONDS:-30}
    conf['PREFECT']['PREFECT_LOCAL_STORAGE_PATH'] = '${PREFECT_LOCAL_STORAGE_PATH:-/var/qcos/storage}'
    conf['PREFECT']['PREFECT_LOGGING_LEVEL'] = '${PREFECT_LOGGING_LEVEL:-INFO}'

    conf['REDIS']['REDIS_SERVER_IP'] = '${REDIS_SERVER_IP:-127.0.0.1}'
    conf['REDIS']['REDIS_SERVER_PORT'] = ${REDIS_SERVER_PORT:-6379}

    conf['DATABASE']['QCOS_DATABASE_CONNECTION_URL'] = '${QCOS_DATABASE_CONNECTION_URL:-fake}'

    conf['LOG']['API_LOG_FILE'] = '${API_LOG_FILE:-/var/log/qcos/qcos-api.log}'
    conf['LOG']['LOG_FORMAT'] = '%(asctime)s | %(levelname)s | %(module)s:%(lineno)s %(message)s'

    conf['DEVICES']['DEVICE_LIST'] = [${DEVICE_LIST:-\"dummy\", \"qutip_sim\"}]

###############
import tomlkit
from tomlkit import comment, nl
config_file='${qcos_config_file_path}'
with open(config_file, 'r', encoding='utf-8') as f:
    conf = tomlkit.load(f)
config(conf)
with open(config_file, 'w', encoding='utf-8') as f:
    tomlkit.dump(conf, f)
  "
fi

# check if dir /etc/qcos/roles exists and create it if not
echo "Sync QCOS role dir: ${qcos_roles_config_dir}"
rsync -av --ignore-existing ${qcos_template_roles_config_dir}/ ${qcos_roles_config_dir}/

# check if file /etc/qcos/qcos-st.conf exists and create it if not
echo "Sync QCOS ST config file: ${qcos_st_config_file_path} ..."
rsync -av --ignore-existing ${qcos_template_st_config_file_path} ${qcos_st_config_file_path}

# check if dir /etc/qcos/st-conf.d exists and create it if not
echo "Sync QCOS ST config dir: ${qcos_st_config_dir} ..."
rsync -av --ignore-existing ${qcos_template_st_config_dir}/ ${qcos_st_config_dir}/

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

# perform database migration if requested
if [ "${db_migration}" = true ]; then
  echo "Starting database migration..."

  # Get the init-db script
  INIT_DB_SCRIPT="/root/qcos-project/build-scripts/init-db.sh"
  DB_MIGRATION_DIR="/root/qcos-project/src/wy_qcos/db/migration"
  if [ "${DEV,,}" = "false" ]; then
    INIT_DB_SCRIPT="${venv_dir}/share/wy_qcos/scripts/init-db.sh"
    DB_MIGRATION_DIR="${venv_dir}/share/wy_qcos/src/wy_qcos/db/migration"
  fi

  # Verify init-db.sh exists
  if [ -f "${INIT_DB_SCRIPT}" ]; then
    # Execute database migration and capture output
    echo "Executing: ${INIT_DB_SCRIPT} --db-user postgres --db-qcos-password ****** -D ${DB_MIGRATION_DIR} -i -u"
    migration_output=$(bash "${INIT_DB_SCRIPT}" --db-user postgres --db-qcos-password "${QCOS_DATABASE_PASSWORD}" -D "${DB_MIGRATION_DIR}" -i -u 2>&1)
    migration_exit_code=$?

    if [ ${migration_exit_code} -eq 0 ]; then
      echo "Database migration completed successfully"
      echo "${migration_output}"
    else
      echo "ERROR: Database migration failed. Reason: ${migration_output}"
      # Continue anyway - qcos-api might still be able to start
    fi
  else
    echo "ERROR: Database init script not found: ${INIT_DB_SCRIPT}"
  fi
fi

# run QCOS under venv
local_cicd=${LOCAL_CICD:-False}
qcos_config_file_args="--config-file ${qcos_config_file_path} --config-dir ${qcos_extra_config_file_dir}"
if [ "${local_cicd,,}" = true ]; then
  qcos_config_file_args="--config-file ${qcos_config_file_path} --config-file ${qcos_st_config_file_path} --config-dir ${qcos_st_config_dir}"
fi

# run qcos-api with max attempts
MAX_ATTEMPTS=3
SLEEP_INTERVAL=10
count=0

while [ $count -lt ${MAX_ATTEMPTS} ]; do
  # Check if qcos-api is already running
  if [ -f "/var/run/qcos/qcos-api.pid" ]; then
    existing_pid=$(cat /var/run/qcos/qcos-api.pid)
    if kill -0 ${existing_pid} 2>/dev/null; then
      echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: qcos-api is already running (PID: ${existing_pid})"
      break
    fi
  fi

  # run qcos-api
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] Attempt $((count+1))/${MAX_ATTEMPTS}: Executing /usr/bin/qcos-api ${qcos_config_file_args}"
  /usr/bin/qcos-api ${qcos_config_file_args}
  if [ $? -eq 0 ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] qcos-api executed successfully!"
    break
  fi
  count=$((count+1))
  echo ${count} > /var/run/qcos/qcos-api-attempts.txt
  if [ $count -lt ${MAX_ATTEMPTS} ]; then
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] qcos-api execution failed, waiting ${SLEEP_INTERVAL} seconds to retry..."
    sleep ${SLEEP_INTERVAL}
  fi
done
if [ ${count} -ge ${MAX_ATTEMPTS} ]; then
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: qcos-api failed after ${MAX_ATTEMPTS} attempts (total $((MAX_ATTEMPTS * SLEEP_INTERVAL)) seconds)"
fi

if [ "${no_exit}" = true ]; then
  sleep infinity
fi
