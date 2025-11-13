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
# run K8s qcos

set -e

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Run QCOS with K8s"
    echo ""
    echo "  -c, --config  Config file"
    echo "  -h, --help    Print this usage message"
    echo ""
}

opts=$(getopt -o c:h --long config:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

config_file="k8s-env"

while true; do
  case "$1" in
    -h | --help )     usage ; exit 0; shift ;;
    -c | --config )   config_file="$2";   shift 2 ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

config_file=$(readlink -f ${config_file})
if [ ! -f "${config_file}" ]; then
  echo "Can't find file: ${config_file}. Please make a copy from k8s-env.template"
  exit 1
fi

source "${config_file}"
echo "Creating K8s QCOS pods, namespace: ${QCOS_NAMESPACE} (${config_file}) ..."
echo "Note: you must create PVCs(${K8S_CODE_DATA_PVC}, ${K8S_DATABASE_PVC}) before running this script"

envsubst < ./k8s-device-config-${QCOS_NAMESPACE}.yaml | kubectl apply -n ${QCOS_NAMESPACE} -f -
envsubst < ./k8s-qcos-api-single-mode.yaml | kubectl apply -n ${QCOS_NAMESPACE} -f -
