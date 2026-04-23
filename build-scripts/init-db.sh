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

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
BUILD_SCRIPTS_DIR=${TOP_DIR}/build-scripts
set -a
source ${BUILD_SCRIPTS_DIR}/.env
set +a

DB_MIGRATION_DIR=${TOP_DIR}/src/wy_qcos/db/migration/

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Init and upgrade QCOS database"
  echo ""
  echo "  -i, --init           Init QCOS database"
  echo "  -u, --upgrade[=HEAD] Upgrade QCOS database to specified version (default: head)"
  echo "  -d, --downgrade[=BASE] Downgrade QCOS database to specified version (default: base)"
  echo "  -h, --help           Print this usage message"
  echo ""
  echo "Examples:"
  echo "  $0 -i                    # Initialize database"
  echo "  $0 -u                    # Upgrade to head (default)"
  echo "  $0 -u head               # Upgrade to head version"
  echo "  $0 -d                    # Downgrade to base (default)"
  echo "  $0 -d base               # Downgrade to base version"
  echo ""
}

opts=$(getopt -o iu::d:: --long init,upgrade::,downgrade::,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

init=false
upgrade=false
upgrade_target="head"
downgrade=false
downgrade_target="base"

while true; do
  case "$1" in
    -h | --help )    usage ; exit 0; shift ;;
    -i | --init )    init=true;   shift ;;
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
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# init database
function init_db {
  echo "Initializing database ..."
  psql_user="postgres"
  # 1. Create user if missing (Quiet mode)
  psql -U ${psql_user} -q -c "DO ' BEGIN IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = ''qcos'') THEN CREATE USER qcos WITH PASSWORD ''$PASS''; END IF; END ';" > /dev/null
  # 2. Create database if missing
  if ! psql -U ${psql_user} -tAc "SELECT 1 FROM pg_database WHERE datname='qcos'" | grep -q 1; then
    echo "Creating database 'qcos'..."
    psql -U ${psql_user} -q -c "CREATE DATABASE qcos OWNER qcos;"
  else
    echo "Database 'qcos' already exists."
  fi
  echo "Database initialization completed."
}

# upgrade database
function upgrade_db {
  local target="${1:-head}"
  cd ${DB_MIGRATION_DIR}
  pwd
  alembic upgrade ${target}
  echo "Database upgrade to '${target}' completed."
}

# downgrade database
function downgrade_db {
  local target="${1:-base}"
  cd ${DB_MIGRATION_DIR}
  pwd
  alembic downgrade ${target}
  echo "Database downgrade to '${target}' completed."
}

if [ "${init}" = false -a "${upgrade}" = false -a "${downgrade}" = false ]; then
  echo "[OPTION] must be specified"
  usage
  exit 1
fi

if [ "${init}" = true ]; then
  init_db
fi

# upgrade database
if [ "${upgrade}" = true ]; then
  upgrade_db "${upgrade_target}"
fi

# downgrade database
if [ "${downgrade}" = true ]; then
  downgrade_db "${downgrade_target}"
fi

echo "Completed"
