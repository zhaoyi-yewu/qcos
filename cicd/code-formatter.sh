#!/bin/sh
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

# Format codes automatically
# Prerequisite:
# pip3 install ruff

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Python code formatter"
  echo ""
  echo "  -f, --fix             Format codes"
  echo "  -d, --dir             Target dir"
  echo "  -h, --help            Print this usage message"
  echo ""
}

target_dir="${TOP_DIR}/src"
opts=$(getopt -o fd:h --long fix,dir:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

fix=false

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -d | --dir )  target_dir="$2"; shift 2;;
    -f | --fix )  fix=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check and format codes
echo "Code format start ..."
if [ "${fix}" = false ]; then
  echo "Check dir: ${target_dir} (ruff)"
  ruff format --preview --check --diff ${target_dir}
else
  echo "Fixing code format in dir: ${target_dir} (ruff)"
  ruff format --preview ${target_dir}
fi
