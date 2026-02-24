#!/bin/sh
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
source ${TOP_DIR}/build-scripts/setup-build-context.sh

SANDBOX_TOP_DIR=/root/qcos-project
TEMP_PKG_DIR=/tmp/qcos-pkgs

OUTPUT_QCOS_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-amd64-${QCOS_IMAGE_VERSION}.tar.xz
OUTPUT_QCOS_CLI_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-cli-amd64-${QCOS_IMAGE_VERSION}.tar.xz

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "QCOS container image builder"
    echo ""
    echo "  -s, --sandbox Build sandbox image"
    echo "  -q, --qcos    Build QCOS image"
    echo "  -c, --cli     Build QCOS cli image"
    echo "  -a, --all     Build all image"
    echo "  -h, --help    Print this usage message"
    echo ""
}

opts=$(getopt -o sqcah --long sandbox,qcos,cli,all,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

sandbox=false
qcos=false
cli=false
all=false

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -s | --sandbox ) sandbox=true;  shift ;;
    -q | --qcos )  qcos=true;  shift ;;
    -c | --cli )   cli=true;   shift ;;
    -a | --all )   all=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

if [ "${all}" = false -a "${sandbox}" = false -a "${qcos}" = false -a "${cli}" = false ]; then
  qcos=true
fi

function run_sandbox {
  echo -e "\nRun sandbox"
  # run sandbox
  docker-compose -f docker-compose-sandbox.yaml up -d
}

function build_cli {
  echo -e "\nBuilding wheel package: wy-qcos-client"
  OUTPUT_PKG_DIR=${top_dir}/build-scripts/cli/output
  WHEEL_PKG_DIST_DIR=${OUTPUT_PKG_DIR}/dist
  QCOS_CLI_WHEEL_PATH=${WHEEL_PKG_DIST_DIR}/wy_qcos_client-${QCOS_CLI_VERSION}-py3-none-any.whl

  # build qcos-cli wheel package
  docker exec ${SANDBOX_CONTAINER_NAME} sh -c "
  export QCOS_CLI_VERSION=${QCOS_CLI_VERSION} &&
  export QCOS_CLI_DIST=${QCOS_CLI_DIST} &&
  cd ${SANDBOX_TOP_DIR}/build-scripts/cli &&
  ./build-wheel.sh
  "

  # copy wheel package to TEMP_PKG_DIR
  cp -f ${QCOS_CLI_WHEEL_PATH} ${TEMP_PKG_DIR}
}

function build_cli_image {
  echo -e "\nBuilding docker image: qcos-cli"
  # build docker image: qcos-cli
  DOCKER_BUILDKIT=0 docker build -f ./cli/Dockerfile --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME}-cli \
    --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
    --build-arg DEV=${DEV} \
    -t ${QCOS_IMAGE_NAME}-cli:${QCOS_IMAGE_VERSION} .

  # save image
  echo -e "\nExport docker image: ${OUTPUT_QCOS_CLI_IMAGE_PATH}"
  docker save ${QCOS_IMAGE_NAME}-cli:${QCOS_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_QCOS_CLI_IMAGE_PATH}
}

function build_qcos {
  echo -e "\nBuilding wheel package: wy-qcos"
  OUTPUT_PKG_DIR=${top_dir}/build-scripts/output
  WHEEL_PKG_DIST_DIR=${OUTPUT_PKG_DIR}/dist
  QCOS_WHEEL_PATH=${WHEEL_PKG_DIST_DIR}/wy_qcos-${QCOS_VERSION}-py3-none-any.whl

  # build qcos-cli wheel package
  docker exec ${SANDBOX_CONTAINER_NAME} sh -c "
  cd ${SANDBOX_TOP_DIR}/build-scripts &&
  ./build-wheel.sh
  "

  # copy wheel package to TEMP_PKG_DIR
  cp -f ${QCOS_WHEEL_PATH} ${TEMP_PKG_DIR}
}

function build_sandbox_image {
  echo -e "\nBuilding docker image: sandbox"
  SANDBOX_CONTAINER_NAME=${QCOS_CONTAINER_NAME}-sandbox
  SANDBOX_IMAGE_NAME=${QCOS_IMAGE_NAME}-sandbox
  SANDBOX_IMAGE_VERSION=dev

  # build qcos building-system: sandbox
  DOCKER_BUILDKIT=0 docker build -f ./qcos/Dockerfile --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${SANDBOX_CONTAINER_NAME} \
    --build-arg SANDBOX_IMAGE_VERSION=${SANDBOX_IMAGE_VERSION} \
    --build-arg DEV=${DEV} \
    --build-arg NPM_MIRROR=${NPM_MIRROR} \
    --target sandbox-builder \
    -t ${SANDBOX_IMAGE_NAME}:${SANDBOX_IMAGE_VERSION} .
}

function build_qcos_image {
  echo -e "\nBuilding docker image: qcos"
  # build docker image: qcos
  DOCKER_BUILDKIT=0 docker build -f ./qcos/Dockerfile --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME} \
    --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
    --build-arg DEV=${DEV} \
    --target qcos-builder \
    -t ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} .

    # save image
    echo -e "\nExport docker image: ${OUTPUT_QCOS_IMAGE_PATH}"
    docker save ${QCOS_IMAGE_NAME}:${QCOS_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_QCOS_IMAGE_PATH}
}

function build_image {
  rm -rf ${TEMP_PKG_DIR}
  mkdir -p ${TEMP_PKG_DIR}

  if [ "${all}" = true ];then
    cli=true
    qcos=true
  fi
  if [ "${cli}" = true ];then
    if [ "${DEV,,}" = false ]; then
      run_sandbox
      build_cli
      cp -f ${TEMP_PKG_DIR}/* ${BUILD_CONTEXT}/pkg/
    fi
    build_cli_image
  fi

  if [ "${sandbox}" = true ];then
    build_sandbox_image
  fi

  if [ "${qcos}" = true ];then
    if [ "${DEV,,}" = false ]; then
      run_sandbox
      build_cli
      build_qcos
      cp -f ${TEMP_PKG_DIR}/* ${BUILD_CONTEXT}/pkg/
      rm -rf ${TEMP_PKG_DIR}
    fi
    build_qcos_image
  fi

  # print info of exported images
  echo
  if [ "${cli}" = true ];then
    echo -e "\nExported qcos-cli docker image: ${OUTPUT_QCOS_CLI_IMAGE_PATH}"
  fi
  if [ "${qcos}" = true ];then
    echo -e "\nExported qcos docker image: ${OUTPUT_QCOS_IMAGE_PATH}"
  fi
}

mkdir -p ${OUTPUT_IMAGE_DIR}
cd ${TOP_DIR}/build-scripts
build_image
