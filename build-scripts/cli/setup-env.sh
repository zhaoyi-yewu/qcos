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

BASE_DIR=$(dirname "${BASH_SOURCE[0]}")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/../..)
BUILD_SCRIPTS_DIR=${TOP_DIR}/build-scripts
OUTPUT_DIR=${BUILD_SCRIPTS_DIR}/output/dist

env_file=${BUILD_SCRIPTS_DIR}/.env
if ! [ -f "${env_file}" ]; then
    echo "Error: can't find config file: '${env_file}'"
    exit 1
fi
source ${env_file}
