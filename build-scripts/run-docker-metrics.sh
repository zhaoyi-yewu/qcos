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

if [ ! -d /etc/qcos/prometheus ]; then
  mkdir -p /etc/qcos/prometheus
  cp -rf ${QCOS_LOCAL_SRC_DIR}/etc/prometheus/* /etc/qcos/prometheus

  export ALERT_MANAGER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${ALERTMANAGER_LISTEN_PORT}"
  export QCOS_METRICS_TARGETS="${QCOS_SERVER_IP}:${METRICS_SERVER_LISTEN_PORT}"
  export PROMETHEUS_TARGETS="${METRICS_SERVER_ACCESS_IP}:${PROMETHEUS_LISTEN_PORT}"
  export NODE_EXPORTER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${NODE_EXPORTER_LISTEN_PORT:-9100}"
  export PROCESS_EXPORTER_TARGETS="${METRICS_SERVER_ACCESS_IP}:${PROCESS_EXPORTER_LISTEN_PORT:-9256}"
  envsubst < /etc/qcos/prometheus/prometheus.yml > /etc/qcos/prometheus/prometheus.yml.tmp && mv /etc/qcos/prometheus/prometheus.yml.tmp /etc/qcos/prometheus/prometheus.yml
fi

if [ ! -d /etc/qcos/process-exporter ]; then
  mkdir -p /etc/qcos/process-exporter
  cp -rf ${QCOS_LOCAL_SRC_DIR}/etc/process-exporter/* /etc/qcos/process-exporter
fi

if [ ! -d /etc/qcos/grafana ]; then
  mkdir -p /etc/qcos/grafana
  cp -rf ${QCOS_LOCAL_SRC_DIR}/etc/grafana/* /etc/qcos/grafana

  export DATA_SOURCE=http://${METRICS_SERVER_ACCESS_IP}:${PROMETHEUS_LISTEN_PORT}
  envsubst < /etc/qcos/grafana/provisioning/datasources/prometheus.yml > /etc/qcos/grafana/provisioning/datasources/prometheus.yml.tmp && mv /etc/qcos/grafana/provisioning/datasources/prometheus.yml.tmp /etc/qcos/grafana/provisioning/datasources/prometheus.yml
fi

if [ ! -d /etc/qcos/alertmanager ]; then
  mkdir -p /etc/qcos/alertmanager
  cp -rf ${QCOS_LOCAL_SRC_DIR}/etc/alertmanager/* /etc/qcos/alertmanager
  if [ -n "${SMTP_HOST}" ] && [ -n "${ALERT_RECEIVE_EMAIL}" ]; then
    export SMTP_HOST SMTP_PORT SMTP_FROM SMTP_AUTH_USER SMTP_AUTH_PASSWORD ALERT_RECEIVE_EMAIL
    envsubst < /etc/qcos/alertmanager/alertmanager.yml > /etc/qcos/alertmanager/alertmanager.yml.tmp && mv /etc/qcos/alertmanager/alertmanager.yml.tmp /etc/qcos/alertmanager/alertmanager.yml
  fi
fi

if [ ! -d /etc/qcos/victorialogs ]; then
  mkdir -p /etc/qcos/victorialogs
fi

if [ ! -d /etc/qcos/fluent-bit ]; then
  mkdir -p /etc/qcos/fluent-bit
  cp -rf ${QCOS_LOCAL_SRC_DIR}/etc/fluent-bit/* /etc/qcos/fluent-bit
  export VICTORIALOGS_LISTEN_PORT=${VICTORIALOGS_LISTEN_PORT:-9428}
  envsubst < /etc/qcos/fluent-bit/fluent-bit.conf > /etc/qcos/fluent-bit/fluent-bit.conf.tmp && mv /etc/qcos/fluent-bit/fluent-bit.conf.tmp /etc/qcos/fluent-bit/fluent-bit.conf
fi

cd ${build_scripts_dir}
# start metrics
docker_compose_file="./docker-compose-metrics.yaml"
new_docker_compose_file="./.docker-compose-metrics.yaml"
create_temp_docker_compose_file "${docker_compose_file}" "${new_docker_compose_file}"

docker-compose -f ${new_docker_compose_file} down
docker-compose -f ${new_docker_compose_file} up -d
