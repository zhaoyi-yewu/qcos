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
SANDBOX_TOP_DIR=/root/qcos-project

OUTPUT_QCOS_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-amd64-${QCOS_IMAGE_VERSION}.tar.xz
OUTPUT_QCOS_CLI_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-cli-amd64-${QCOS_IMAGE_VERSION}.tar.xz

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "QCOS container image builder"
    echo ""
    echo "  -q, --qcos  Build QCOS image"
    echo "  -c, --cli   Build QCOS cli image"
    echo "  -a, --all   Build all image"
    echo "  -h, --help  Print this usage message"
    echo ""
}

opts=$(getopt -o qcah --long qcos,cli,all,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

qcos=false
cli=false
all=false

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -q | --qcos )  qcos=true;  shift ;;
    -c | --cli )   cli=true;   shift ;;
    -a | --all )   all=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

if [ "${all}" = false -a "${qcos}" = false -a "${cli}" = false ]; then
  qcos=true
fi

function build_cli {
  echo "Creating QCOS sandbox ..."
  OUTPUT_PKG_DIR=${top_dir}/build-scripts/output
  WHEEL_PKG_DIST_DIR=${OUTPUT_PKG_DIR}/dist
  QCOS_CLI_WHEEL_PATH=${WHEEL_PKG_DIST_DIR}/qcos_cli-${QCOS_CLI_VERSION}-py3-none-any.whl

  docker-compose -f docker-compose-sandbox.yaml up -d

  # build qcos-cli rpm file
  docker exec ${SANDBOX_CONTAINER_NAME} sh -c "
  export QCOS_CLI_VERSION=${QCOS_CLI_VERSION} &&
  export QCOS_CLI_DIST=${QCOS_CLI_DIST} &&
  cd ${SANDBOX_TOP_DIR}/build-scripts/cli &&
  ./build-wheel.sh
  "

  # copy rpm to BUILD_CONTEXT
  cp -f ${QCOS_CLI_WHEEL_PATH} ${BUILD_CONTEXT}/pkg/

  # build docker image: qcos-cli
  DOCKER_BUILDKIT=0 docker build -f ./cli/Dockerfile --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME}-cli \
    --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
    -t ${QCOS_IMAGE_NAME}-cli:${QCOS_IMAGE_VERSION} .

  # save image
  docker save ${QCOS_IMAGE_NAME}-cli:${QCOS_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_QCOS_CLI_IMAGE_PATH}
}

function build_qcos {
  # build docker image: qcos
  DOCKER_BUILDKIT=0 docker build -f ./qcos/Dockerfile --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME} \
    --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
    --build-arg DEV=${DEV} \
    -t ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} .

    # save image
    docker save ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_QCOS_IMAGE_PATH}
}

function build_image {
  if [ "${all}" = true ];then
    cli=true
    qcos=true
  fi
  if [ "${cli}" = true ];then
    build_cli
  fi
  if [ "${qcos}" = true ];then
    build_qcos
  fi

  # print info of exported images
  echo
  if [ "${cli}" = true ];then
    echo "Exported qcos-cli docker image: ${OUTPUT_QCOS_CLI_IMAGE_PATH}"
  fi
  if [ "${qcos}" = true ];then
    echo "Exported qcos docker image: ${OUTPUT_QCOS_IMAGE_PATH}"
  fi
}

mkdir -p ${OUTPUT_IMAGE_DIR}
build_image
