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

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
source ${TOP_DIR}/build-scripts/setup-env.sh

# local variables
BUILD_CONTEXT=${abs_cwd}/.build-context

# create temp dir build-context
rm -rf ${BUILD_CONTEXT}
mkdir -p ${BUILD_CONTEXT}
mkdir -p ${BUILD_CONTEXT}/pkg

# create yum repo file
if [ -n "${YUM_MIRROR}" ]; then
  cat > ${BUILD_CONTEXT}/openEuler.repo << EOM
#generic-repos is licensed under the Mulan PSL v2.
#You can use this software according to the terms and conditions of the Mulan PSL v2.
#You may obtain a copy of Mulan PSL v2 at:
#    http://license.coscl.org.cn/MulanPSL2
#THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT, MERCHANTABILITY OR FIT FOR A PARTICULAR
#PURPOSE.
#See the Mulan PSL v2 for more details.

[OS]
name=OS
baseurl=${YUM_MIRROR}/OS/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/OS/\$basearch/RPM-GPG-KEY-openEuler

[everything]
name=everything
baseurl=${YUM_MIRROR}/everything/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/everything/\$basearch/RPM-GPG-KEY-openEuler

[EPOL]
name=EPOL
baseurl=${YUM_MIRROR}/EPOL/main/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/OS/\$basearch/RPM-GPG-KEY-openEuler

[debuginfo]
name=debuginfo
baseurl=${YUM_MIRROR}/debuginfo/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/debuginfo/\$basearch/RPM-GPG-KEY-openEuler

[update]
name=update
baseurl=${YUM_MIRROR}/update/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/OS/\$basearch/RPM-GPG-KEY-openEuler
EOM
fi

if [ -n "${PIP_MIRROR}" ]; then
  cat > ${BUILD_CONTEXT}/pip.conf << EOM
[global]
index-url=${PIP_MIRROR}
trusted-host=$(echo "${PIP_MIRROR#*://}" | awk -F[/:] '{print $1}')
EOM
fi

# get commit id and save to file
git_commit_id=$(git rev-parse HEAD 2>/dev/null || echo "")
echo ${git_commit_id} > ${top_dir}/latest-commit-id.txt

# copy dirs/files to build-context
# Use "|" as a delimiter. Left side is the path, right side is the specific exclude rules for this entry.
files=(
    "build-scripts/.env|"
    "latest-commit-id.txt|"
    "src|"
    "etc|"
    "LICENSE|"
    "pyproject.toml|"
    "requirements/|"
    "build-scripts/qcos/entrypoint.sh|"
    "build-scripts/cli/|"
    "bin/qcos-api.py|"
    "bin/qcos-cli.py|"
    "bin/qcos-transpiler.py|"
    "samples/|"
    "webui/|--exclude=node_modules/ --exclude=dist/ --exclude=build-scripts/ --exclude=build/"
    "build-scripts/webui/|"
)
for entry in "${files[@]}"; do
    # 1. Extract the file path and exclude rules
    file_path="${entry%%|*}"
    exclude_rules="${entry#*|}"

    # Fallback safety check: if no "|" is present, set exclude_rules to empty
    if [[ "$entry" != *"|"* ]]; then
        exclude_rules=""
    fi
    src="${top_dir}/${file_path}"
    dst="${BUILD_CONTEXT}/"
    if [[ ${file_path} == *"/"* ]]; then
        dst="${BUILD_CONTEXT}/${file_path}"
        # Double quotes prevent errors if the path contains spaces
        mkdir -p "$(dirname "${dst}")"
    fi
    # 2. Append the specific exclude_rules to the rsync command
    # If you have a global exclude_pattern, you can place it before or after ${exclude_rules}
    rsync -r ${exclude_pattern} ${exclude_rules} --delete "${src}" "${dst}"
done
