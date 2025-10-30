#!/bin/sh
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

set -e

echo "Creating K8s QCOS cli pod ..."

if [ ! -f k8s-env ]; then
  echo "Can't find file: k8s-env. Please copy from k8s-env.template"
  exit 1
fi

export $(grep -v '^#' k8s-env | xargs)
envsubst < ./k8s-qcos-cli.yaml | kubectl apply -n ${QCOS_NAMESPACE} -f -
