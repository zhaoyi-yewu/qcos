#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
# run K8s qcos-cli

set -e

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Run QCOS cli with K8s"
    echo ""
    echo "  -e, --env-file  Environment file"
    echo "  -h, --help      Print this usage message"
    echo ""
}

opts=$(getopt -o e:h --long env-file:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

env_file="k8s-env"

while true; do
  case "$1" in
    -h | --help )     usage ; exit 0; shift ;;
    -e | --env-file ) env_file="$2";   shift 2 ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

env_file=$(readlink -f ${env_file})
if [ ! -f "${env_file}" ]; then
  echo "Can't find env file: ${env_file}. Please make a copy from k8s-env.template"
  exit 1
fi

source "${env_file}"
echo "Creating K8s QCOS cli pods, namespace: ${QCOS_NAMESPACE} (${env_file}) ..."
envsubst < ./k8s-qcos-cli.yaml | kubectl apply -n ${QCOS_NAMESPACE} -f -
