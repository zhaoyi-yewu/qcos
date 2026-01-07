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

# Check git changed files format
# Prerequisite:
# pip3 install ruff

set -e

# global variables
BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
ERROR=false
START_COMMIT_ID=""

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Files format check"
  echo ""
  echo "  -c, --start-commit-d  Start commit id. (files filtered by 'git diff --name-only --diff-filter=AM {START_COMMIT_ID}..HEAD')"
  echo "  -f, --fix             Format files"
  echo "  -h, --help            Print this usage message"
  echo ""
}

opts=$(getopt -o c:fh --long start-commit-id:,fix,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

FIX=false

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -c | --start-commit-id ) START_COMMIT_ID="$2"; shift 2 ;;
    -f | --fix )  FIX=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

cd "${TOP_DIR}"

if [ -z "${START_COMMIT_ID}" ]; then
  START_COMMIT_ID=$(git rev-list --merges -n 1 HEAD)
fi

# git commited files
COMMITTED_FILES=$(git diff --name-only --diff-filter=AM "${START_COMMIT_ID}..HEAD")
# git staged files
STAGED_FILES=$(git diff --name-only --cached --diff-filter=AM)
# git unstaged files
UNSTAGED_FILES=$(git diff --name-only --diff-filter=AM)
# git uncommitted files
UNCOMMITTED_FILES=$(echo -e "${STAGED_FILES}\n${UNSTAGED_FILES}" | sort | uniq)
# git all changed files
MR_CHANGED_FILES=$(echo -e "${COMMITTED_FILES}\n${UNCOMMITTED_FILES}" | sort | uniq)

# 1. CRLF check
CR_FILES=$(echo "${MR_CHANGED_FILES}" | xargs -r file | grep 'with CRLF' | awk '{gsub(/:/, "", $1); print $1}' || true)
if [ -z "${CR_FILES}" ]; then
  echo "1. Files (with CRLF) check [PASS]"
  echo "All files passed"
else
  if [ "${FIX}" = false ]; then
    echo "1. Files (with CRLF) [FAILED]"
    echo "The following files contain Windows-style CR line endings; please convert them to Linux-style LF format. (eg. dos2unix FILE_NAME)"
    echo "---files---"
    echo "${CR_FILES}"
    ERROR=true
  else
    echo "1. Fixing files (with CRLF)"
    dos2unix ${CR_FILES}
  fi
fi
echo ""

# 2. copyright years check
EXTENSIONS="\.py$|\.sh$"
CURRENT_YEAR=$(date +%Y)
CHANGED_FILES=$(echo "${MR_CHANGED_FILES}" | grep -E "${EXTENSIONS}" || true)
REGEX="Copyright© 2024-${CURRENT_YEAR} China Mobile \(SuZhou\)(?s).*?qcos is licensed under Mulan PSL v2"
INVALID_FILES=()
if [ -z "${CHANGED_FILES}" ]; then
  echo "2. Copyright check [PASSED]"
  echo "No files matched"
else
  for FILE in ${CHANGED_FILES}; do
	  if [ ! "${FILE}" ]; then
	    continue
	  fi
    if ! grep -Pzq "${REGEX}" "${FILE}"; then
      INVALID_FILES+=("${FILE}")
    fi
  done

  if [ ${#INVALID_FILES[@]} -gt 0 ]; then
    if [ "${FIX}" = false ]; then
      echo "2. Copyright check [FAILED]"
      echo "The following files need to match the Copyright regex: \"${REGEX}\""
      echo "-----------"
      echo "${#INVALID_FILES[@]} files:"
      for FILE in "${INVALID_FILES[@]}"; do
          echo "- ${FILE}"
      done
      ERROR=true
    else
      echo "2. Fixing Copyright check"
      MATCH_REGEX="Copyright© 2024-20[0-9]{2} China Mobile"
      REPLACE_STR="Copyright© 2024-${CURRENT_YEAR} China Mobile"
      for FILE in "${INVALID_FILES[@]}"; do
        sed -i -E "s/Copyright© 2024-20[0-9]{2} China Mobile/$REPLACE_STR/g" "${FILE}"
      done
    fi
  else
    echo "2. Copyright check [PASSED]"
    echo "All files passed"
  fi
fi

echo ""
if [ "${FIX}" = true ]; then
  echo "All files fixed"
else
  if [ "${ERROR}" = "true" ]; then
    echo "File check FAILED"
    exit 1
  else
    echo "File check PASSED"
    exit 0
  fi
fi
