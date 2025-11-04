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

# Python code linter
# Prerequisite:
# pip3 install ruff mypy

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Python code linter"
  echo ""
  echo "  -f, --fix             Fix code errors"
  echo "  -h, --help            Print this usage message"
  echo ""
}

opts=$(getopt -o fh --long fix,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

fix=false

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -f | --fix )  fix=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check and fix errors
cd "${TOP_DIR}"
echo "Code check start ..."
if [ "${fix}" = false ]; then
  echo "Checking dir: qcos (pylint)"
  pylint qcos
  echo "Checking dir: qcos (ruff)"
  ruff check --preview qcos
  echo "Checking dir: qcos (mypy)"
  mypy qcos
else
  echo "Fix code errors in dir: qcos (ruff)"
  ruff check --fix qcos
fi
