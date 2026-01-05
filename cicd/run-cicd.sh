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

# run cicd

set -e

cwd=$(dirname "${BASH_SOURCE[0]}")
top_dir=$(realpath ${cwd}/..)

echo "Run code-linter ..."
${top_dir}/cicd/code-linter.sh
echo

echo "Run code-style ..."
${top_dir}/cicd/code-formatter.sh
echo

echo "Run UT ..."
${top_dir}/cicd/run-tests.sh -u
echo

echo "Run coverage ..."
${top_dir}/cicd/run-tests.sh -c

echo "CICD pipeline completed successfully"

