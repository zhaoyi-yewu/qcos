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
# qcos cli shell
# build rpm package: python3-qcosclient
set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
DOCS_DIR=${TOP_DIR}/docs

cd ${DOCS_DIR}
pwd
# create sphinx docs
make clean dirhtml html

# create openapi docs
./make-openapi-docs.py

# print results
echo -e "\n======DOCS OUTPUT======"
echo "Sphinx docs:  ${DOCS_DIR}/build/dirhtml/"
echo "OpenAPI docs: ${DOCS_DIR}/api-docs/"

