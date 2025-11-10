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

set -e

source ./setup-env.sh

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
baseurl=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/OS/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/OS/\$basearch/RPM-GPG-KEY-openEuler

[everything]
name=everything
baseurl=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/everything/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/everything/\$basearch/RPM-GPG-KEY-openEuler

[EPOL]
name=EPOL
baseurl=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/EPOL/main/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/OS/\$basearch/RPM-GPG-KEY-openEuler

[debuginfo]
name=debuginfo
baseurl=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/debuginfo/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/debuginfo/\$basearch/RPM-GPG-KEY-openEuler

[update]
name=update
baseurl=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/update/\$basearch/
enabled=1
gpgcheck=1
gpgkey=${YUM_MIRROR}/openeuler/openEuler-24.03-LTS/OS/\$basearch/RPM-GPG-KEY-openEuler
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
files=("latest-commit-id.txt" "qcos" "etc" "requirements.txt" \
       "requirements-test.txt" "build-scripts/qcos/entrypoint.sh" \
       "build-scripts/cli/entrypoint.sh" "bin/qcos-api.py" "bin/qcos-cli.py" \
       "build-scripts/cli/requirements.txt" "requirements-driver.txt" \
       "bin/qcos-transpiler.py" \
       "samples/")
for file_path in "${files[@]}"; do
  src=${top_dir}/${file_path}
  dst=${BUILD_CONTEXT}/
  if [[ ${file_path} == *"/"* ]]; then
    # if $file is files
    dst=${BUILD_CONTEXT}/${file_path}
    mkdir -p $(dirname ${dst})
  fi
  rsync -r --delete ${src} ${dst}
done
