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

SETUP_ENV_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOP_DIR=$(cd "${SETUP_ENV_DIR}/../.." && pwd)
BUILD_SCRIPTS_DIR="${TOP_DIR}/build-scripts"
ENV_FILE="${SETUP_ENV_DIR}/.env"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Error: can't find config file: '${ENV_FILE}'"
  echo "Copy '${SETUP_ENV_DIR}/env.template' to '${ENV_FILE}' and configure it."
  exit 1
fi

set -a
source "${BUILD_SCRIPTS_DIR}/version"
source "${ENV_FILE}"
set +a

export TOP_DIR BUILD_SCRIPTS_DIR
export QCOS_LOCAL_SRC_DIR="${QCOS_LOCAL_SRC_DIR:-${TOP_DIR}}"
export QCOS_CONTAINER_NAME="${QCOS_CONTAINER_NAME:-qcos}"
export QCOS_BASE_CONTAINER_NAME="${QCOS_BASE_CONTAINER_NAME:-qcos-base}"
export QCOS_SANDBOX_CONTAINER_NAME="${QCOS_SANDBOX_CONTAINER_NAME:-qcos-sandbox}"
export SANDBOX_IMAGE_NAME="${SANDBOX_IMAGE_NAME:-qcos-sandbox}"
export SANDBOX_IMAGE_VERSION="${SANDBOX_IMAGE_VERSION:-dev}"
export BASE_IMAGE_NAME="${BASE_IMAGE_NAME:-qcos-base}"
export BASE_IMAGE_VERSION="${BASE_IMAGE_VERSION:-${QCOS_VERSION}}"

# Select production or development images and container names.
configure_runtime_mode() {
  local mode="$1"

  if [ "${mode}" = "dev" ]; then
    export DEV=True
    export QCOS_IMAGE_NAME="${QCOS_IMAGE_NAME}-dev"
    export QCOS_IMAGE_VERSION=dev
    export QCOS_CONTAINER_NAME="${QCOS_CONTAINER_NAME}-dev"
    export QCOS_WEBUI_IMAGE_NAME="${QCOS_WEBUI_IMAGE_NAME}-dev"
    export SANDBOX_IMAGE_VERSION=dev
  else
    export DEV=False
  fi
}

# Create a writable Compose copy while preserving the original file.
create_temp_docker_compose_file() {
  local src_file="$1"
  local dst_file="$2"

  cp -f "${src_file}" "${dst_file}"
  if grep -E 'read_only:\s*([Tt][Rr][Uu][Ee])' "${dst_file}" > /dev/null; then
    sed -i 's/read_only:\s*[Tt][Rr][Uu][Ee]/read_only: false/' "${dst_file}"
  fi
}
