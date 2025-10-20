#!/bin/bash
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

source ./setup-env.sh

# create temp src dir
CLI_SRC_DIR=${BASE_DIR}/.src
rm -rf ${CLI_SRC_DIR}
mkdir -p ${CLI_SRC_DIR}

# copy cli src files
mkdir -p ${CLI_SRC_DIR}/qcos
mkdir -p ${CLI_SRC_DIR}/qcos/common
cd ${CLI_SRC_DIR}
cp -rf ${BUILD_SCRIPTS_DIR}/cli/pyproject.toml ${CLI_SRC_DIR}/
cp -rf ${TOP_DIR}/LICENSE ${CLI_SRC_DIR}/
cp -rf ${TOP_DIR}/README.md ${CLI_SRC_DIR}/
cp -rf ${TOP_DIR}/qcos/__init__.py ${CLI_SRC_DIR}/qcos/
cp -rf ${TOP_DIR}/qcos/client ${CLI_SRC_DIR}/qcos/
cp -rf ${TOP_DIR}/qcos/common/__init__.py ${CLI_SRC_DIR}/qcos/common
cp -rf ${TOP_DIR}/qcos/common/args_schema.py ${CLI_SRC_DIR}/qcos/common
cp -rf ${TOP_DIR}/qcos/common/client_library.py ${CLI_SRC_DIR}/qcos/common
cp -rf ${TOP_DIR}/qcos/common/constant.py ${CLI_SRC_DIR}/qcos/common
cp -rf ${TOP_DIR}/qcos/common/errors.py ${CLI_SRC_DIR}/qcos/common

if [ -n "${PIP_MIRROR}" ]; then
  poetry source add --priority=primary pip_mirror "${PIP_MIRROR}"
else
  poetry source remove pip_mirror
fi
poetry -C ${CLI_SRC_DIR} build -o ${OUTPUT_DIR}
poetry -C ${CLI_SRC_DIR} source remove pip_mirror
echo "Dist package dir: ${OUTPUT_DIR}"

# clean up
rm -rf ${CLI_SRC_DIR}
cd -
