#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

cwd=$(dirname "${BASH_SOURCE[0]}")
abs_cwd=$(realpath ${cwd})
top_dir=$(realpath ${cwd}/..)

env_file=${cwd}/.env
if ! [ -f "${env_file}" ]; then
    echo "Error: can't find config file: '${env_file}'"
    exit 1
fi
source ${env_file}

# local variables
export QCOS_LOCAL_SRC_DIR="${top_dir}"
export SANDBOX_CONTAINER_NAME=qcos-sandbox
export SANDBOX_IMAGE_NAME=qcos-sandbox
export SANDBOX_IMAGE_VERSION=dev
if [ "${DEV,,}" = "true" ]; then
  export QCOS_IMAGE_NAME="${QCOS_IMAGE_NAME}-dev"
  export QCOS_IMAGE_VERSION="${QCOS_IMAGE_VERSION}"
  export QCOS_CONTAINER_NAME="${QCOS_CONTAINER_NAME}-dev"
fi
