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

# Check git changed files format
# Prerequisite:
# pip3 install ruff

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

cd "${TOP_DIR}"

# 1. CRLF check
CRLF_FILES=$(git diff --name-only | xargs -r file | grep CRLF || true)
if [ -n "$CRLF_FILES" ]; then
  echo "1. CRLF check failed."
  echo "The following files contain Windows-style CRLF line endings; please convert them to Linux-style LF format. (eg. dos2unix FILE_NAME)"
  echo "---files---"
  echo "${CRLF_FILES}"
  exit 1
else
  echo "1. CRLF check passed"
  echo "${CRLF_FILES}"
fi
