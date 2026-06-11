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

# run cicd

set -e

cwd=$(dirname "${BASH_SOURCE[0]}")
top_dir=$(realpath ${cwd}/..)

function usage {
    echo "Usage: $0"
}

if [ $# -gt 0 ]; then
    usage
    exit 1
fi

print_and_run() {
    local cmd="$*"
    echo "Run command: ${cmd}"
    ${cmd}
    local exit_code=$?
    echo
    return ${exit_code}
}

echo "* Run check-files ..."
print_and_run "${top_dir}/cicd/check-files.sh"

echo "* Run code-style ..."
print_and_run "${top_dir}/cicd/code-formatter.sh"

echo "* Run code-linter ..."
print_and_run "${top_dir}/cicd/code-linter.sh"

echo "* Run docstring-check ..."
print_and_run "${top_dir}/cicd/docstring-check.sh"

echo "* Run docs-linter ..."
print_and_run "${top_dir}/cicd/docs-linter.sh"

echo "* Run UT (QCOS) ..."
print_and_run "${top_dir}/cicd/run-tests.sh -u default"

echo "* Run coverage (QCOS) ..."
print_and_run "${top_dir}/cicd/run-tests.sh -c default"

echo "* Run UT (QCOS CLIENT) ..."
print_and_run "${top_dir}/cicd/run-tests.sh -j all"

echo "* Run coverage (QCOS CLIENT) ..."
print_and_run "${top_dir}/cicd/run-tests.sh -e all"

echo "CICD pipeline completed successfully"
