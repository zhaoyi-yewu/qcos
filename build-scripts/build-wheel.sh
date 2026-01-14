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
# build wheel package

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
OUTPUT_DIR=${TOP_DIR}/build-scripts/output/dist

source ${BASE_DIR}/setup-env.sh

if [ -n "${PIP_MIRROR}" ]; then
  poetry source -C ${TOP_DIR} add --priority=primary pip_mirror "${PIP_MIRROR}"
fi

# clean env
rm -rf ${TOP_DIR}/build
rm -rf ${TOP_DIR}/src/wy_qcos.egg-info

# build
poetry build -C ${TOP_DIR} -o ${OUTPUT_DIR}
if [ -n "${PIP_MIRROR}" ]; then
  poetry source -C ${TOP_DIR} remove pip_mirror
fi
echo "Dist package dir: ${OUTPUT_DIR}"

