#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

SANDBOX_CONTAINER_NAME=qcos-sandbox
SANDBOX_IMAGE_NAME=qcos-sandbox
SANDBOX_IMAGE_VERSION=dev

# build qcos building-system
DOCKER_BUILDKIT=0 docker build -f ./sandbox/Dockerfile --no-cache --rm --network host \
  --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
  --build-arg CONTAINER_NAME=${SANDBOX_CONTAINER_NAME} \
  --build-arg SANDBOX_IMAGE_VERSION=${SANDBOX_IMAGE_VERSION} \
  --build-arg DEV=${DEV} \
  -t ${SANDBOX_IMAGE_NAME}:${SANDBOX_IMAGE_VERSION} .
