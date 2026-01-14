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

# Python docs linter
# Prerequisite:
# pip3 install doc8 mdformat

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Python docs linter (Markdown(md) / reStructuredText(rst) files)"
  echo ""
  echo "  -f, --fix             Fix docs errors (markdown file only)"
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
echo "Docs linter start ..."

MD_FILES=$(find ${TOP_DIR} \
  -not -path "*/build-scripts/*" \
  -not -path "*/samples/*" \
  -not -path "*/.pytest_cache/*" \
  -type f -name "*.md" \
)
if [ "${fix}" = false ]; then
  echo "Checking MD (Markdown) files:"
  for file in ${MD_FILES}; do
    if ! mdformat --check "${file}" &>/dev/null; then
      echo "Format error in markdown file: ${file}, diff:"
      mdformat - < "${file}" | diff -u "${file}" -
    fi
  done

  echo "Checking RST (reStructuredText) files:"
  # doc8 configs are included in pyproject.toml
  doc8
else
  echo "Fixing format of MD (markdown) files:"
  for file in ${MD_FILES}; do
    mdformat "${file}"
  done
fi
