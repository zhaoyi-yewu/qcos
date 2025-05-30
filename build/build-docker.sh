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

source ./setup-build-context.sh
OUTPUT_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-amd64-${QCOS_IMAGE_VERSION}.tar.xz

# build docker image
DOCKER_BUILDKIT=0 docker build -f Dockerfile --no-cache --rm --network host \
  --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
  --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME} \
  --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
  -t ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} .

# export docker image
mkdir -p ${OUTPUT_IMAGE_DIR}
docker save ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_IMAGE_PATH}
