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

echo "Creating K8s QCOS pods ..."

if [ ! -f .env ]; then
  echo "Can't find file .env"
  exit 1
fi

k8s_namespace="default"
export PREFECT_SERVER_PORT=${PREFECT_SERVER_PORT:-4200}
export QCOS_API_PORT=${QCOS_API_PORT:-4200}
export PREFECT_IMAGE_NAME=${PREFECT_IMAGE_NAME:-prefecthq/prefect}
export PREFECT_IMAGE_VERSION=${PREFECT_IMAGE_VERSION:-3.3.3-python3.13}
export QCOS_IMAGE_NAME=${QCOS_IMAGE_NAME:-qcos}
export QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION:-2025-06-01}

export $(grep -v '^#' .env | xargs)
envsubst < ./k8s-qcos-single.yaml | cat
# envsubst < ./k8s-qcos-single.yaml | kubectl apply -n ${k8s_namespace} -f -
