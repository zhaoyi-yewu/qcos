#!/bin/bash
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
# qcos cli shell
# build rpm package: python3-qcosclient
set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/../..)
OUTPUT_DIR=${BASE_DIR}/output
RPM_TOP_DIR=${OUTPUT_DIR}/rpmbuild
RPM_SPEC_DIR=${BASE_DIR}/rpm-specs

QCOS_CLI_VERSION=${CLI_PKG_VERSION:-1.0.0}
QCOS_CLI_DIST=${CLI_PKG_DIST:-.oe1}

# create qcos-client rpm package
# create rpmbuild dirs
mkdir -p ${RPM_TOP_DIR}/SOURCES ${RPM_TOP_DIR}/BUILD \
  ${RPM_TOP_DIR}/BUILDROOT ${RPM_TOP_DIR}/RPMS \
  ${RPM_TOP_DIR}/SPECS ${RPM_TOP_DIR}/SRPMS

# create source sdist file
cd ${TOP_DIR}
tar czvf ${RPM_TOP_DIR}/SOURCES/qcos-${QCOS_CLI_VERSION}.tar.gz --transform "s#^#qcos-${QCOS_CLI_VERSION}/#g" ./setup.py LICENSE qcos bin/qcos-cli.py

# build rpm package
rpmbuild -v --nodeps -ba ${RPM_SPEC_DIR}/qcos-client.spec \
  --define="_topdir ${RPM_TOP_DIR}" --define="version ${QCOS_CLI_VERSION}" \
  --define="dist ${QCOS_CLI_DIST}"

# print results
echo
echo "RPM file: "
ls ${RPM_TOP_DIR}/RPMS/noarch/*.rpm
cd ${BASE_DIR}
