#!/bin/bash
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

# Remove dependency declarations before [project.scripts] in pyproject.toml.

set -euo pipefail

PYPROJECT_FILE="${1:-./pyproject.toml}"

if [[ ! -f "${PYPROJECT_FILE}" ]]; then
    echo "ERROR: File not found: ${PYPROJECT_FILE}" >&2
    exit 1
fi

if ! grep -q '^dependencies = \[$' "${PYPROJECT_FILE}"; then
    echo "ERROR: dependencies = [ was not found." >&2
    exit 1
fi

if ! grep -q '^\[project\.scripts\]$' "${PYPROJECT_FILE}"; then
    echo "ERROR: [project.scripts] was not found." >&2
    exit 1
fi

sed -i.bak '/^dependencies = \[$/,/^\[project\.scripts\]$/ {
    /^\[project\.scripts\]$/!d
}' "${PYPROJECT_FILE}"

echo "Updated: ${PYPROJECT_FILE}"
echo "Backup created: ${PYPROJECT_FILE}.bak"
