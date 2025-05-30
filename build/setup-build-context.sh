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

cwd=$(dirname "${BASH_SOURCE[0]}")
abs_cwd=$(realpath ${cwd})
top_dir=$(realpath ${cwd}/..)

env_file=${cwd}/.env
if ! [ -f ${env_file} ]; then
    echo "Error: can't find config file: '${env_file}'"
    exit 1
fi
source ${env_file}

# local variables
BUILD_CONTEXT=${abs_cwd}/.build-context

# create temp dir build-context
rm -rf ${BUILD_CONTEXT}
mkdir -p ${BUILD_CONTEXT}

# create yum repo file
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

if [ "${LOCAL_CICD}" = "True" ]; then
  cat > $BUILD_CONTEXT/pip.conf << EOM
[global]
index-url=${PIP_MIRROR}
trusted-host=$(echo "${PIP_MIRROR#*://}" | awk -F[/:] '{print $1}')
EOM
fi

# copy dirs/files to build-context
files=("src" "etc" "requirements.txt" "build/entrypoint.sh" "bin/qcos.py")
for file in "${files[@]}"; do
  src=${top_dir}/${file}
  dst=${BUILD_CONTEXT}/${file}
  mkdir -p $(dirname ${dst})
  rsync -r --delete ${src} ${dst}
done
