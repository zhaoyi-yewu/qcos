#!/bin/bash
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

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
BUILD_SCRIPTS_DIR=${TOP_DIR}/build-scripts

# configs
DB_USER="postgres"
DB_PASSWORD=""
DB_QCOS_PASSWORD=""
DB_HOST="localhost"
WHEEL_DB_MIGRATION_DIR="/usr/local/share/wy_qcos/db_migration"
DEV_DB_MIGRATION_DIR="${TOP_DIR}/src/wy_qcos/db/migration/"
DB_MIGRATION_DIR=${WHEEL_DB_MIGRATION_DIR}
if [ -d "${DEV_DB_MIGRATION_DIR}" ]; then
  DB_MIGRATION_DIR="${DEV_DB_MIGRATION_DIR}"
fi

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Init and upgrade QCOS database"
  echo ""
  echo "  -U, --db-user <user>          Database admin user (default: ${DB_USER})"
  echo "  -P, --db-password <pwd>       Database admin password"
  echo "  -q, --db-qcos-password <pwd>  Database QCOS password"
  echo "  -H, --db-host <host>          Database host"
  echo "  -i, --init            Init QCOS database"
  echo "  -u, --upgrade[=HEAD]  Upgrade QCOS database to specified version (default: head)"
  echo "  -d, --downgrade[=BASE] Downgrade QCOS database to specified version (default: base)"
  echo "  -l, --list            List all database migration history"
  echo "  -D, --dir <path>      Database migration directory (default: ${DB_MIGRATION_DIR})"
  echo "  -h, --help            Print this usage message"
  echo ""
  echo "Examples:"
  echo "  $0 -i                    # Initialize database"
  echo "  $0 -u                    # Upgrade to head (default)"
  echo "  $0 -u head               # Upgrade to head version"
  echo "  $0 -d                    # Downgrade to base (default)"
  echo "  $0 -d base               # Downgrade to base version"
  echo "  $0 -l                    # List all migration history"
  echo "  $0 -H localhost -U postgres -P pg_pass -q qcos_pass --dir /var/lib/qcos/venv/default/lib/python3.11/site-packages/wy_qcos/db/migration -i -u  # Specify db credentials and db migration directory"
  echo ""
}

opts=$(getopt -o H:U:P:q:iu::d::lD: --long db-host:,db-user:,db-password:,db-qcos-password:,init,upgrade::,downgrade::,list,dir:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

init=false
upgrade=false
upgrade_target="head"
downgrade=false
downgrade_target="base"
list=false
db_migration_dir="${DB_MIGRATION_DIR}"

while true; do
  case "$1" in
    -h | --help )    usage ; exit 0; shift ;;
    -i | --init )    init=true;   shift ;;
    -l | --list )    list=true;   shift ;;
    -u | --upgrade )
      upgrade=true
      if [ -n "$2" ]; then
        upgrade_target="$2"
        shift 2
      else
        shift
      fi
      ;;
    -d | --downgrade )
      downgrade=true
      if [ -n "$2" ]; then
        downgrade_target="$2"
        shift 2
      else
        shift
      fi
      ;;
    -D | --dir )
      db_migration_dir="$2"
      shift 2 ;;
    -H | --db-host )
      DB_HOST="$2"
      shift 2 ;;
    -U | --db-user )
      DB_USER="$2"
      shift 2 ;;
    -P | --db-password )
      DB_PASSWORD="$2"
      shift 2 ;;
    -q | --db-qcos-password )
      DB_QCOS_PASSWORD="$2"
      shift 2 ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# init database
function init_db {
  echo "Initializing database ..."
  db_host="${DB_HOST:-localhost}"
  psql_user="${DB_USER:-postgres}"
  psql_password="${DB_PASSWORD:-123456}"
  qcos_password="${DB_QCOS_PASSWORD:-123456}"

  # Export PGPASSWORD for non-interactive auth
  export PGPASSWORD="${psql_password}"

  # 1. Create user if missing
  echo "Creating database user 'qcos' if not exists..."
  create_user_output=$(psql -h "${db_host}" -U "${psql_user}" -q -c "DO ' BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = ''qcos'') THEN CREATE USER qcos WITH PASSWORD ''${qcos_password}''; END IF; END ';" 2>&1)
  create_user_exit_code=$?

  if [ ${create_user_exit_code} -ne 0 ]; then
    echo "ERROR: Failed to create database user 'qcos'. Reason: ${create_user_output}"
    unset PGPASSWORD
    return 1
  fi

  # 2. Create database if missing
  echo "Checking if database 'qcos' exists..."
  check_db_output=$(psql -h "${db_host}" -U "${psql_user}" -tAc "SELECT 1 FROM pg_database WHERE datname='qcos'" 2>&1)
  check_db_exit_code=$?

  if [ ${check_db_exit_code} -ne 0 ]; then
    echo "ERROR: Failed to check if database 'qcos' exists. Reason: ${check_db_output}"
    unset PGPASSWORD
    return 1
  fi

  if ! echo "${check_db_output}" | grep -q 1; then
    echo "Creating database 'qcos'..."
    create_db_output=$(psql -h "${db_host}" -U "${psql_user}" -q -c "CREATE DATABASE qcos OWNER qcos;" 2>&1)
    create_db_exit_code=$?

    if [ ${create_db_exit_code} -ne 0 ]; then
      echo "ERROR: Failed to create database 'qcos'. Reason: ${create_db_output}"
      unset PGPASSWORD
      return 1
    fi
  else
    echo "Database 'qcos' already exists."
  fi

  unset PGPASSWORD
  echo "Database initialization completed."
  return 0
}

# upgrade database
function upgrade_db {
  local target="${1:-head}"

  # Verify migration directory exists
  if [ ! -d "${db_migration_dir}" ]; then
    echo "ERROR: Migration directory not found: ${db_migration_dir}"
    return 1
  fi

  if [ ! -f "${db_migration_dir}/alembic.ini" ]; then
    echo "ERROR: alembic.ini not found in ${db_migration_dir}"
    return 1
  fi

  echo "Upgrading database to '${target}'..."
  cd "${db_migration_dir}"

  if ! alembic upgrade ${target}; then
    echo "ERROR: Database upgrade failed"
    return 1
  fi

  echo "Database upgrade to '${target}' completed."
  return 0
}

# downgrade database
function downgrade_db {
  local target="${1:-base}"

  # Verify migration directory exists
  if [ ! -d "${db_migration_dir}" ]; then
    echo "ERROR: Migration directory not found: ${db_migration_dir}"
    return 1
  fi

  if [ ! -f "${db_migration_dir}/alembic.ini" ]; then
    echo "ERROR: alembic.ini not found in ${db_migration_dir}"
    return 1
  fi

  echo "Downgrading database to '${target}'..."
  cd "${db_migration_dir}"

  if ! alembic downgrade ${target}; then
    echo "ERROR: Database downgrade failed"
    return 1
  fi

  echo "Database downgrade to '${target}' completed."
  return 0
}

# list database migration history
function list_history {
  echo "Database migration history:"
  cd ${db_migration_dir}
  alembic history
}

if [ "${init}" = false -a "${upgrade}" = false -a "${downgrade}" = false -a "${list}" = false ]; then
  echo "[OPTION] must be specified"
  usage
  exit 1
fi

if [ "${init}" = true ]; then
  if ! init_db; then
    echo "ERROR: Database initialization failed"
    exit 1
  fi
fi

# upgrade database
if [ "${upgrade}" = true ]; then
  if ! upgrade_db "${upgrade_target}"; then
    echo "ERROR: Database upgrade failed"
    exit 1
  fi
fi

# downgrade database
if [ "${downgrade}" = true ]; then
  if ! downgrade_db "${downgrade_target}"; then
    echo "ERROR: Database downgrade failed"
    exit 1
  fi
fi

# list migration history
if [ "${list}" = true ]; then
  if ! list_history; then
    echo "ERROR: Failed to list migration history"
    exit 1
  fi
fi

echo "Completed"
