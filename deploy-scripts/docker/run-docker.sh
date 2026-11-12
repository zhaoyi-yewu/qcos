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

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

usage() {
  cat << EOF
Usage: $0 <start|stop> <prod|dev|ai|metrics|prefect|base|webui|sandbox|all>

Targets:
  prod      Start/stop PostgreSQL, QCOS, Prefect, Redis and QCOS CLI.
  dev       Start/stop the development QCOS and QCOS CLI containers.
  ai        Start/stop the AI embedding service.
  metrics   Start/stop the metrics and logging services.
  prefect   Start/stop the standalone Prefect development container.
  base      Start/stop the QCOS base container.
  webui     Start/stop WebUI; DEV in .env selects the image variant.
  sandbox   Start/stop the QCOS sandbox container.
  all       Start: production QCOS/CLI, WebUI, AI and metrics.
            Stop: every Compose target, including development containers.
EOF
}

if [ "$#" -eq 1 ] && [[ "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

if [ "$#" -ne 2 ]; then
  usage
  exit 1
fi

ACTION="$1"
TARGET="$2"

if [[ "${ACTION}" != "start" && "${ACTION}" != "stop" ]]; then
  echo "Error: unsupported action '${ACTION}'"
  usage
  exit 1
fi

case "${TARGET}" in
  prod | dev | ai | metrics | prefect | base | webui | sandbox | all) ;;
  *)
    echo "Error: unsupported target '${TARGET}'"
    usage
    exit 1
    ;;
esac

# shellcheck source=deploy-scripts/docker/setup-env.sh
source "${SCRIPT_DIR}/setup-env.sh"

case "${TARGET}" in
  prod | all)
    configure_runtime_mode prod
    ;;
  dev)
    configure_runtime_mode dev
    ;;
  *)
    if [ "${DEV,,}" = "true" ]; then
      configure_runtime_mode dev
    else
      configure_runtime_mode prod
    fi
    ;;
esac

if command -v docker > /dev/null 2>&1 && docker compose version > /dev/null 2>&1; then
  DOCKER_COMPOSE=(docker compose)
elif command -v docker-compose > /dev/null 2>&1; then
  DOCKER_COMPOSE=(docker-compose)
else
  echo "Error: either 'docker compose' or 'docker-compose' is required"
  exit 1
fi

run_compose() {
  local compose_file="$1"
  shift

  (
    cd "${BUILD_SCRIPTS_DIR}"
    "${DOCKER_COMPOSE[@]}" -f "${compose_file}" "$@"
  )
}

resolve_compose_file() {
  local file_name="$1"
  local use_temp="${2:-true}"

  if [ "${use_temp}" = "true" ]; then
    create_temp_docker_compose_file \
      "${BUILD_SCRIPTS_DIR}/${file_name}" \
      "${BUILD_SCRIPTS_DIR}/.${file_name}"
    RESOLVED_COMPOSE_FILE=".${file_name}"
  else
    RESOLVED_COMPOSE_FILE="${file_name}"
  fi
}

compose_start() {
  local file_name="$1"
  local use_temp="${2:-true}"

  resolve_compose_file "${file_name}" "${use_temp}"
  run_compose "${RESOLVED_COMPOSE_FILE}" down
  run_compose "${RESOLVED_COMPOSE_FILE}" up -d
}

compose_stop() {
  local file_name="$1"
  local use_temp="${2:-true}"

  resolve_compose_file "${file_name}" "${use_temp}"
  run_compose "${RESOLVED_COMPOSE_FILE}" down
}

prepare_qcos_directories() {
  mkdir -p \
    /etc/qcos/prefect \
    /etc/qcos/postgres/initdb \
    /var/qcos/db/postgresql \
    /var/qcos/backup/database \
    /var/prefect

  rm -f /etc/qcos/prefect/profiles.toml
  if [ ! -f /etc/qcos/prefect/logging.yml ]; then
    cp "${TOP_DIR}/etc/prefect/logging.yml" /etc/qcos/prefect/
  fi
  if [ ! -f /etc/qcos/postgres/postgresql.conf ]; then
    cp "${TOP_DIR}/etc/postgres/postgresql.conf" /etc/qcos/postgres/
  fi
  cp -f "${TOP_DIR}"/etc/postgres/initdb/*.sql /etc/qcos/postgres/initdb/
}

setup_db_user() {
  local user="$1"
  local password="$2"
  local database="$3"

  docker exec postgres psql -U postgres \
    -c "CREATE USER ${user} WITH PASSWORD '${password}' INHERIT;" \
    2> /dev/null || echo "  Note: ${user} user may already exist"
  docker exec postgres psql -U postgres \
    -c "CREATE DATABASE ${database} WITH OWNER ${user};" \
    2> /dev/null || echo "  Note: ${database} database may already exist"
  docker exec postgres psql -U postgres \
    -c "GRANT ALL PRIVILEGES ON DATABASE ${database} TO ${user};" \
    2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "ALTER SCHEMA public OWNER TO ${user};" 2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "GRANT ALL PRIVILEGES ON SCHEMA public TO ${user};" 2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${user};" \
    2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${user};" \
    2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO ${user};" 2> /dev/null
  docker exec postgres psql -U postgres -d "${database}" \
    -c "GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${user};" 2> /dev/null
}

wait_for_postgres() {
  local max_attempts=60
  local attempt=0

  echo "Waiting for PostgreSQL to be fully ready..."
  while [ "${attempt}" -lt "${max_attempts}" ]; do
    if docker exec postgres pg_isready -U postgres > /dev/null 2>&1; then
      if docker exec postgres psql -U postgres -c "SELECT 1" > /dev/null 2>&1; then
        echo "PostgreSQL is fully initialized and ready"
        return 0
      fi
    fi
    attempt=$((attempt + 1))
    if [ $((attempt % 10)) -eq 0 ]; then
      echo "  Attempt ${attempt}/${max_attempts}: PostgreSQL initializing..."
    fi
    sleep 1
  done

  echo "Error: PostgreSQL failed to initialize within ${max_attempts} seconds"
  echo "Try checking: docker logs postgres"
  return 1
}

setup_postgres() {
  wait_for_postgres

  echo "Setting up Prefect user and database..."
  setup_db_user prefect "${PREFECT_DATABASE_PASSWORD}" prefect
  echo "Setting up QCOS user and database..."
  setup_db_user qcos "${QCOS_DATABASE_PASSWORD}" qcos

  echo "Initializing pgvector extension..."
  docker exec postgres psql -U postgres -d qcos \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" 2> /dev/null || \
    echo "  Note: pgvector extension may already exist or image does not include it"
  echo "PostgreSQL setup completed successfully"
}

start_database() {
  case "${DB_BACKEND,,}" in
    postgres)
      compose_stop docker-compose-postgres.yaml false
      resolve_compose_file docker-compose-postgres.yaml false
      run_compose "${RESOLVED_COMPOSE_FILE}" up -d
      setup_postgres
      ;;
    sqlite)
      compose_stop docker-compose-postgres.yaml false
      rm -f /var/qcos/db/prefect.db-shm /var/qcos/db/prefect.db-wal
      ;;
    *)
      echo "Error: DB_BACKEND must be either 'postgres' or 'sqlite'"
      return 1
      ;;
  esac
}

start_qcos() {
  local mode="$1"
  local compose_file="docker-compose.yaml"
  local cli_compose_file="docker-compose-cli.yaml"
  local container_name=qcos

  if [ "${mode}" = "dev" ]; then
    compose_file="docker-compose-dev.yaml"
    cli_compose_file="docker-compose-dev-cli.yaml"
    container_name=qcos-dev
  fi

  prepare_qcos_directories
  start_database

  echo "Creating QCOS ${mode} dockers..."
  compose_start "${compose_file}"
  compose_start "${cli_compose_file}"
  echo "Run QCOS bash: docker exec -it ${container_name} bash"
  echo "Run QCOS CLI bash: docker exec -it ${container_name}-cli bash"
}

stop_qcos() {
  local mode="$1"
  local compose_file="docker-compose.yaml"
  local cli_compose_file="docker-compose-cli.yaml"

  if [ "${mode}" = "dev" ]; then
    compose_file="docker-compose-dev.yaml"
    cli_compose_file="docker-compose-dev-cli.yaml"
  fi

  echo "Stopping QCOS ${mode} dockers..."
  compose_stop "${cli_compose_file}"
  compose_stop "${compose_file}"
}

render_config_file() {
  local file_path="$1"

  if ! command -v envsubst > /dev/null 2>&1; then
    echo "Error: 'envsubst' is required to render ${file_path}"
    return 1
  fi
  envsubst < "${file_path}" > "${file_path}.tmp"
  mv "${file_path}.tmp" "${file_path}"
}

prepare_metrics_configuration() {
  if [ ! -d /etc/qcos/prometheus ]; then
    mkdir -p /etc/qcos/prometheus
    cp -rf "${TOP_DIR}/etc/prometheus/." /etc/qcos/prometheus/
    export ALERT_MANAGER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${ALERTMANAGER_LISTEN_PORT}"
    export QCOS_METRICS_TARGETS="${QCOS_SERVER_IP}:${METRICS_SERVER_LISTEN_PORT}"
    export PROMETHEUS_TARGETS="${METRICS_SERVER_ACCESS_IP}:${PROMETHEUS_LISTEN_PORT}"
    export NODE_EXPORTER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${NODE_EXPORTER_LISTEN_PORT:-9100}"
    export PROCESS_EXPORTER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${PROCESS_EXPORTER_LISTEN_PORT:-9256}"
    render_config_file /etc/qcos/prometheus/prometheus.yml
  fi

  if [ ! -d /etc/qcos/process-exporter ]; then
    mkdir -p /etc/qcos/process-exporter
    cp -rf "${TOP_DIR}/etc/process-exporter/." /etc/qcos/process-exporter/
  fi

  if [ ! -d /etc/qcos/grafana ]; then
    mkdir -p /etc/qcos/grafana
    cp -rf "${TOP_DIR}/etc/grafana/." /etc/qcos/grafana/
    export DATA_SOURCE="http://${METRICS_SERVER_ACCESS_IP}:${PROMETHEUS_LISTEN_PORT}"
    render_config_file /etc/qcos/grafana/provisioning/datasources/prometheus.yml
  fi

  if [ ! -d /etc/qcos/alertmanager ]; then
    mkdir -p /etc/qcos/alertmanager
    cp -rf "${TOP_DIR}/etc/alertmanager/." /etc/qcos/alertmanager/
    if [ -n "${SMTP_HOST:-}" ] && [ -n "${ALERT_RECEIVE_EMAIL:-}" ]; then
      export SMTP_HOST SMTP_PORT SMTP_FROM SMTP_AUTH_USER SMTP_AUTH_PASSWORD
      export ALERT_RECEIVE_EMAIL
      render_config_file /etc/qcos/alertmanager/alertmanager.yml
    fi
  fi

  if [ ! -d /etc/qcos/victorialogs ]; then
    mkdir -p /etc/qcos/victorialogs
  fi

  if [ ! -d /etc/qcos/fluent-bit ]; then
    mkdir -p /etc/qcos/fluent-bit
    cp -rf "${TOP_DIR}/etc/fluent-bit/." /etc/qcos/fluent-bit/
    export VICTORIALOGS_LISTEN_PORT="${VICTORIALOGS_LISTEN_PORT:-9428}"
    render_config_file /etc/qcos/fluent-bit/fluent-bit.conf
  fi
}

start_metrics() {
  prepare_metrics_configuration
  echo "Creating QCOS metrics dockers..."
  compose_start docker-compose-metrics.yaml
}

start_prefect() {
  prepare_qcos_directories
  echo "Creating Prefect docker..."
  compose_start docker-compose-prefect.yaml false
  echo "Run Prefect bash: docker exec -it prefect-server bash"
}

start_webui() {
  local compose_file=docker-compose-webui.yaml
  local container_name=qcos-webui

  if [ "${DEV,,}" = "true" ]; then
    compose_file=docker-compose-webui-dev.yaml
    container_name=qcos-webui-dev
  fi

  echo "Creating QCOS WebUI docker..."
  compose_start "${compose_file}"
  echo "Run WebUI bash: docker exec -it ${container_name} bash"
}

start_base() {
  echo "Creating QCOS base docker (${QCOS_BASE_CONTAINER_NAME})..."
  compose_start docker-compose-base.yaml
  echo "Run QCOS base bash: docker exec -it ${QCOS_BASE_CONTAINER_NAME} bash"
}

start_sandbox() {
  echo "Creating QCOS sandbox docker (${QCOS_SANDBOX_CONTAINER_NAME})..."
  compose_start docker-compose-sandbox.yaml
  echo "Run QCOS sandbox bash: docker exec -it ${QCOS_SANDBOX_CONTAINER_NAME} bash"
}

start_target() {
  case "$1" in
    prod | dev)
      start_qcos "$1"
      ;;
    ai)
      echo "Creating QCOS AI embedding docker..."
      compose_start docker-compose-ai.yaml
      ;;
    metrics)
      start_metrics
      ;;
    prefect)
      start_prefect
      ;;
    base)
      start_base
      ;;
    webui)
      start_webui
      ;;
    sandbox)
      start_sandbox
      ;;
    all)
      start_qcos prod
      start_target ai
      start_metrics
      DEV=False
      start_webui
      ;;
  esac
}

stop_target() {
  case "$1" in
    prod | dev)
      stop_qcos "$1"
      compose_stop docker-compose-postgres.yaml false
      ;;
    ai)
      compose_stop docker-compose-ai.yaml
      ;;
    metrics)
      compose_stop docker-compose-metrics.yaml
      ;;
    prefect)
      compose_stop docker-compose-prefect.yaml false
      ;;
    base)
      compose_stop docker-compose-base.yaml
      ;;
    webui)
      if [ "${DEV,,}" = "true" ]; then
        compose_stop docker-compose-webui-dev.yaml
      else
        compose_stop docker-compose-webui.yaml
      fi
      ;;
    sandbox)
      compose_stop docker-compose-sandbox.yaml
      ;;
    all)
      compose_stop docker-compose-webui.yaml
      compose_stop docker-compose-webui-dev.yaml
      compose_stop docker-compose-metrics.yaml
      compose_stop docker-compose-ai.yaml
      compose_stop docker-compose-base.yaml
      compose_stop docker-compose-sandbox.yaml
      compose_stop docker-compose-prefect.yaml false
      stop_qcos dev
      stop_qcos prod
      compose_stop docker-compose-postgres.yaml false
      ;;
  esac
}

if [ "${ACTION}" = "start" ]; then
  start_target "${TARGET}"
else
  stop_target "${TARGET}"
fi
