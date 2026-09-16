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

cwd=$(dirname "$0")
abs_cwd=$(realpath ${cwd})
build_scripts_dir=${abs_cwd}

source ${build_scripts_dir}/setup-env.sh
export QCOS_LOCAL_SRC_DIR="${top_dir}"

# copy config files
mkdir -p /etc/qcos/
mkdir -p /etc/qcos/prefect
mkdir -p /var/qcos/db
mkdir -p /var/qcos/db/postgresql
mkdir -p /var/qcos/backup/database
mkdir -p /etc/qcos/postgres
mkdir -p /var/prefect/

# copy postgresql config files
rm -rf /etc/qcos/prefect/profiles.toml
if [ ! -f /etc/qcos/postgres/postgresql.conf ]; then
  cp -r ${QCOS_LOCAL_SRC_DIR}/etc/postgres/postgresql.conf /etc/qcos/postgres/
fi

cd ${build_scripts_dir}

# start postgres sql
docker-compose -f docker-compose-postgres.yaml down
if [ "${DB_BACKEND,,}" = "postgres" ]; then
  docker-compose -f docker-compose-postgres.yaml up -d

  # wait for postgres to be fully initialized and ready
  echo "Waiting for PostgreSQL to be fully ready..."
  max_attempts=60
  attempt=0
  while [ $attempt -lt $max_attempts ]; do
    # first check if server is listening
    if docker exec postgres pg_isready -U postgres > /dev/null 2>&1; then
      # then verify database is actually responsive
      if docker exec postgres psql -U postgres -c "SELECT 1" > /dev/null 2>&1; then
        echo "PostgreSQL is fully initialized and ready"
        break
      fi
    fi
    attempt=$((attempt + 1))
    if [ $((attempt % 10)) -eq 0 ]; then
      echo "  Attempt $attempt/$max_attempts: PostgreSQL initializing..."
    fi
    sleep 1
  done

  if [ $attempt -eq $max_attempts ]; then
    echo "ERROR: PostgreSQL failed to fully initialize within $max_attempts seconds"
    echo "Try checking: docker logs postgres"
    docker logs postgres
    exit 1
  fi

  # Helper function to setup database user and permissions
  setup_db_user() {
    local user=$1
    local password=$2
    local db=$3

    docker exec postgres psql -U postgres -c "CREATE USER ${user} WITH PASSWORD '${password}' INHERIT;" 2>/dev/null || \
      echo "  Note: ${user} user may already exist"
    docker exec postgres psql -U postgres -c "CREATE DATABASE ${db} WITH OWNER ${user};" 2>/dev/null || \
      echo "  Note: ${db} database may already exist"
    docker exec postgres psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${db} TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "ALTER SCHEMA public OWNER TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "GRANT ALL PRIVILEGES ON SCHEMA public TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO ${user};" 2>/dev/null
    docker exec postgres psql -U postgres -d ${db} -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${user};" 2>/dev/null
  }

  # setup prefect
  echo "Setting up prefect user and database..."
  setup_db_user "prefect" "${PREFECT_DATABASE_PASSWORD}" "prefect"

  # setup qcos
  echo "Setting up qcos user and database..."
  setup_db_user "qcos" "${QCOS_DATABASE_PASSWORD}" "qcos"

  echo "PostgreSQL setup completed successfully"
fi

if [ "${DB_BACKEND,,}" = "sqlite" ]; then
  rm -rf /var/qcos/db/prefect.db-shm /var/qcos/db/prefect.db-wal
fi

# start qcos
echo "Creating QCOS dockers ..."

# start docker
if [ "${DEV,,}" = "false" ]; then
  # start qcos
  docker_compose_file="./docker-compose.yaml"
  new_docker_compose_file="./.docker-compose.yaml"
  create_temp_docker_compose_file "${docker_compose_file}" "${new_docker_compose_file}"

  docker-compose -f ${new_docker_compose_file} down
  docker-compose -f ${new_docker_compose_file} up -d
  echo "Run QCOS bash: docker exec -it qcos bash"
else
  # start qcos-dev
  docker_compose_file="./docker-compose-dev.yaml"
  new_docker_compose_file="./.docker-compose-dev.yaml"
  create_temp_docker_compose_file "${docker_compose_file}" "${new_docker_compose_file}"

  docker-compose -f ${new_docker_compose_file} down
  docker-compose -f ${new_docker_compose_file} up -d
  echo "Run QCOS bash: docker exec -it qcos-dev bash"
fi
