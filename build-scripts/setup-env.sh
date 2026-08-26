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
source ${BASE_DIR}/setup-env-functions.sh

# if CICD WORKSPACE exists
cicd_build_scripts_dir=""
if [ -n "${WORKSPACE}" ]; then
    cicd_build_scripts_dir="${WORKSPACE}/build-scripts"
fi
cwd="${cicd_build_scripts_dir:-$(pwd)}"
abs_cwd=$(realpath ${cwd})
top_dir=$(realpath ${cwd}/..)

env_file=${cwd}/.env
if ! [ -f "${env_file}" ]; then
    echo "Error: can't find config file: '${env_file}'"
    exit 1
fi
source ${cwd}/version

# Expand all environment variables in .env file
# First source .env to get the raw values
source ${env_file}

# Then expand all variables that contain nested variable references
# by re-exporting them with eval echo
while IFS='=' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue

    # Get current value of this variable from the environment
    current_value=$(eval echo "\${${key}}")

    # If it's different from the source, it means it has variables to expand
    if [[ -n "$current_value" ]]; then
        # Export the expanded value
        export "${key}=${current_value}"
    fi
done < "${env_file}"

# local variables
if [ -z "${QCOS_LOCAL_SRC_DIR}" ]; then
  export QCOS_LOCAL_SRC_DIR="${top_dir}"
fi

export QCOS_IMAGE_NAME="${QCOS_IMAGE_NAME}"
export QCOS_IMAGE_VERSION="${QCOS_IMAGE_VERSION}"
export QCOS_CONTAINER_NAME="${QCOS_CONTAINER_NAME}"
export SANDBOX_CONTAINER_NAME=qcos-sandbox
export SANDBOX_IMAGE_NAME=qcos-sandbox
export SANDBOX_IMAGE_VERSION=${SANDBOX_IMAGE_VERSION:-dev}
if [ "${DEV,,}" = "true" ]; then
  export QCOS_IMAGE_NAME="${QCOS_IMAGE_NAME}-dev"
  export QCOS_IMAGE_VERSION="dev"
  export QCOS_CONTAINER_NAME="${QCOS_CONTAINER_NAME}-dev"
  export SANDBOX_IMAGE_VERSION="dev"
  export QCOS_WEBUI_IMAGE_NAME="${QCOS_WEBUI_IMAGE_NAME}-dev"
fi
