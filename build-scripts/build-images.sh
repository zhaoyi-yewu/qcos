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
BUILD_SCRIPTS_DIR=${TOP_DIR}/build-scripts
source ${BUILD_SCRIPTS_DIR}/setup-build-context.sh

TEMP_PKG_DIR=/tmp/qcos-pkgs

PYTHON_SRC_MIRROR=${PYTHON_SRC_MIRROR:-"https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz"}
PYPY3_BIN_MIRROR=${PYPY3_BIN_MIRROR:-"https://downloads.python.org/pypy/pypy3.11-v7.3.20-linux64.tar.bz2"}

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "QCOS container image builder"
    echo ""
    echo "  -b, --base    Build QCOS base image"
    echo "  -s, --sandbox Build sandbox image"
    echo "  -q, --qcos    Build QCOS image"
    echo "  -c, --cli     Build QCOS cli image"
    echo "  -a, --all     Build all images"
    echo "  -t, --tag     image tag/version"
    echo "  -n, --no-save Don't export/save images"
    echo "  -h, --help    Print this usage message"
    echo ""
}

opts=$(getopt -o bsqcat:nh --long base,sandbox,qcos,cli,all,tag:,no-save,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

base=false
sandbox=false
qcos=false
cli=false
all=false
save=true
build_wheel_in_sandbox=${BUILD_WHEEL_IN_SANDBOX:-false}

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -b | --base ) base=true;  shift ;;
    -s | --sandbox ) sandbox=true;  shift ;;
    -q | --qcos )  qcos=true;  shift ;;
    -c | --cli )   cli=true;   shift ;;
    -a | --all )   all=true;   shift ;;
    -t | --tag )   tag="$2";   shift 2;;
    -n | --no-save ) save=false;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

image_tag=${QCOS_IMAGE_VERSION}
if [ -n "${tag}" ]; then
  image_tag=${tag}
fi

QCOS_BASE_IMAGE_NAME=qcos-base
QCOS_BASE_IMAGE_VERSION=${tag:-dev}
OUTPUT_QCOS_BASE_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_BASE_IMAGE_NAME}-amd64-${QCOS_BASE_IMAGE_VERSION}.tar.xz
OUTPUT_SANDBOX_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-sandbox-amd64-${image_tag}.tar.xz
OUTPUT_QCOS_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-amd64-${image_tag}.tar.xz
OUTPUT_QCOS_CLI_IMAGE_PATH=${OUTPUT_IMAGE_DIR}/${QCOS_IMAGE_NAME}-cli-amd64-${image_tag}.tar.xz

if [ "${all}" = false -a "${base}" = false -a "${sandbox}" = false -a "${qcos}" = false -a "${cli}" = false ]; then
  qcos=true
fi

function check_docker_image {
    local image_name=$1
    if [ "$(docker image inspect "${image_name}" --format='exists' 2>/dev/null)" = "exists" ]; then
      return 0
    else
      return 1
    fi
}

function build_qcos_base_image {
  echo -e "\nBuilding docker image: qcos-base"
  QCOS_BASE_CONTAINER_NAME=qcos-base

  # build qcos building-system: qcos-base
  cd ${BUILD_SCRIPTS_DIR}
  cp -rf ./base/Dockerfile .build-context/
  DOCKER_BUILDKIT=0 docker build --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_BASE_CONTAINER_NAME} \
    --build-arg DEV=${DEV} \
    --build-arg PYTHON_SRC_MIRROR=${PYTHON_SRC_MIRROR} \
    --build-arg PYPY3_BIN_MIRROR=${PYPY3_BIN_MIRROR} \
    -t ${QCOS_BASE_IMAGE_NAME}:${QCOS_BASE_IMAGE_VERSION} .build-context

  # save image
  if [ "${save}" = true ];then
    echo -e "\nExporting docker image: ${OUTPUT_QCOS_BASE_IMAGE_PATH}"
    docker save ${QCOS_BASE_IMAGE_NAME}:${QCOS_BASE_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_QCOS_BASE_IMAGE_PATH}
  fi
}

function run_sandbox {
  echo -e "\nRun sandbox"
  # run sandbox
  docker-compose -f docker-compose-sandbox.yaml up -d
}

function build_sandbox_image {
  echo -e "\nBuilding docker image: sandbox"
  SANDBOX_CONTAINER_NAME=qcos-sandbox
  SANDBOX_IMAGE_NAME=qcos-sandbox
  SANDBOX_IMAGE_VERSION=dev

  # build qcos building-system: sandbox
  cd ${BUILD_SCRIPTS_DIR}
  cp -rf ./sandbox/Dockerfile .build-context/
  DOCKER_BUILDKIT=0 docker build --no-cache --rm --network host \
    --build-arg CONTAINER_NAME=${SANDBOX_CONTAINER_NAME} \
    --build-arg SANDBOX_IMAGE_VERSION=${SANDBOX_IMAGE_VERSION} \
    --build-arg NPM_MIRROR=${NPM_MIRROR} \
    -t ${SANDBOX_IMAGE_NAME}:${SANDBOX_IMAGE_VERSION} .build-context

  # save image
  if [ "${save}" = true ];then
    echo -e "\nExporting docker image: ${OUTPUT_SANDBOX_IMAGE_PATH}"
    docker save ${SANDBOX_IMAGE_NAME}:${SANDBOX_IMAGE_VERSION} | xz -c --fast -T 0 > ${OUTPUT_SANDBOX_IMAGE_PATH}
  fi
}

function build_qcos {
  echo -e "\nBuilding wheel package: wy-qcos"
  OUTPUT_PKG_DIR=${BUILD_SCRIPTS_DIR}/output
  WHEEL_PKG_DIST_DIR=${OUTPUT_PKG_DIR}/dist
  QCOS_WHEEL_PATH=${WHEEL_PKG_DIST_DIR}/wy_qcos-${QCOS_VERSION}-py3-none-any.whl

  # build qcos-cli wheel package
  if [ "${build_wheel_in_sandbox}" = false ];then
    cd ${BUILD_SCRIPTS_DIR}
    ./build-wheel.sh
  else
    docker exec ${SANDBOX_CONTAINER_NAME} sh -c "
    cd ${BUILD_SCRIPTS_DIR} &&
    ./build-wheel.sh
    "
  fi

  # copy wheel package to TEMP_PKG_DIR
  cp -f ${QCOS_WHEEL_PATH} ${TEMP_PKG_DIR}
}

function build_qcos_image {
  echo -e "\nBuilding docker image: qcos"
  # build docker image: qcos
  cd ${BUILD_SCRIPTS_DIR}
  cp -rf ./qcos/Dockerfile .build-context/
  DOCKER_BUILDKIT=0 docker build --no-cache --rm --network host \
    --build-arg CONTAINER_NAME=${QCOS_CONTAINER_NAME} \
    --build-arg QCOS_IMAGE_VERSION=${QCOS_IMAGE_VERSION} \
    --build-arg DEV=${DEV} \
    -t ${QCOS_IMAGE_NAME}:${image_tag} .build-context

  # save image
  if [ "${save}" = true ];then
    echo -e "\nExporting docker image: ${OUTPUT_QCOS_IMAGE_PATH}"
    docker save ${QCOS_IMAGE_NAME}:${image_tag} | xz -c --fast -T 0 > ${OUTPUT_QCOS_IMAGE_PATH}
  fi
}

function build_cli {
  echo -e "\nBuilding wheel package: wy-qcos-client"
  OUTPUT_PKG_DIR=${BUILD_SCRIPTS_DIR}/cli/output
  WHEEL_PKG_DIST_DIR=${OUTPUT_PKG_DIR}/dist
  QCOS_CLI_WHEEL_PATH=${WHEEL_PKG_DIST_DIR}/wy_qcos_client-${QCOS_CLI_VERSION}-py3-none-any.whl

  # build qcos-cli wheel package
  if [ "${build_wheel_in_sandbox}" = false ];then
    export QCOS_CLI_VERSION=${QCOS_CLI_VERSION}
    export QCOS_CLI_DIST=${QCOS_CLI_DIST}
    cd ${BUILD_SCRIPTS_DIR}/cli
    ./build-wheel.sh
  else
    docker exec ${SANDBOX_CONTAINER_NAME} sh -c "
    export QCOS_CLI_VERSION=${QCOS_CLI_VERSION} &&
    export QCOS_CLI_DIST=${QCOS_CLI_DIST} &&
    cd ${BUILD_SCRIPTS_DIR}/cli &&
    ./build-wheel.sh
    "
  fi

  # copy wheel package to TEMP_PKG_DIR
  cp -f ${QCOS_CLI_WHEEL_PATH} ${TEMP_PKG_DIR}
}

function build_cli_image {
  echo -e "\nBuilding docker image: qcos-cli"
  QCOS_CLI_CONTAINER_NAME=${QCOS_CONTAINER_NAME}-cli
  QCOS_CLI_IMAGE_NAME=${QCOS_IMAGE_NAME}-cli

  # build docker image: qcos-cli
  cd ${BUILD_SCRIPTS_DIR}
  cp -rf ./cli/Dockerfile .build-context/
  DOCKER_BUILDKIT=0 docker build --no-cache --rm --network host \
    --build-arg CONTAINER_BASE_IMAGE=${CONTAINER_BASE_IMAGE} \
    --build-arg CONTAINER_NAME=${QCOS_CLI_CONTAINER_NAME} \
    --build-arg QCOS_IMAGE_VERSION=${image_tag} \
    --build-arg DEV=${DEV} \
    -t ${QCOS_CLI_IMAGE_NAME}:${image_tag} .build-context

  # save image
  if [ "${save}" = true ];then
    echo -e "\nExporting docker image: ${OUTPUT_QCOS_CLI_IMAGE_PATH}"
    docker save ${QCOS_CLI_IMAGE_NAME}:${image_tag} | xz -c --fast -T 0 > ${OUTPUT_QCOS_CLI_IMAGE_PATH}
  fi
}

function build_image {
  rm -rf ${TEMP_PKG_DIR}
  mkdir -p ${TEMP_PKG_DIR}

  QCOS_BASE_IMAGE="${QCOS_BASE_IMAGE_NAME}:${QCOS_BASE_IMAGE_VERSION}"
  if [[ "${base}" != true && ( "${qcos}" = true || "${sandbox}" = true ) ]]; then
    if ! check_docker_image "${QCOS_BASE_IMAGE}"; then
      echo "Can't find container image: ${QCOS_BASE_IMAGE}, put it in building list"
      base=true
    fi
  fi

  if [ "${all}" = true ];then
    cli=true
    qcos=true
  fi

  if [ "${base}" = true ];then
    build_qcos_base_image
  fi

  if [ "${sandbox}" = true ];then
    build_sandbox_image
  fi

  if [ "${qcos}" = true ];then
    if [ "${DEV,,}" = false ]; then
      if [ "${build_wheel_in_sandbox}" = true ];then
        run_sandbox
      fi
      build_cli
      build_qcos
      cp -f ${TEMP_PKG_DIR}/* ${BUILD_CONTEXT}/pkg/
      rm -rf ${TEMP_PKG_DIR}
    fi
    build_qcos_image
  fi

  if [ "${cli}" = true ];then
    if [ "${DEV,,}" = false ]; then
      if [ "${build_wheel_in_sandbox}" = true ];then
        run_sandbox
      fi
      build_cli
      cp -f ${TEMP_PKG_DIR}/* ${BUILD_CONTEXT}/pkg/
    fi
    build_cli_image
  fi

  # print info of exported images
  echo
  if [ "${base}" = true ];then
    if [ "${save}" = true ];then
      echo -e "\nExported qcos-base docker image: ${OUTPUT_QCOS_BASE_IMAGE_PATH}"
    else
      echo -e "\nExported qcos-base docker image: skipped"
    fi
  fi
  if [ "${sandbox}" = true ];then
    if [ "${save}" = true ];then
      echo -e "\nExported qcos-sandbox docker image: ${OUTPUT_SANDBOX_IMAGE_PATH}"
    else
      echo -e "\nExported qcos-sandbox docker image: skipped"
    fi
  fi
  if [ "${cli}" = true ];then
    if [ "${save}" = true ];then
      echo -e "\nExported qcos-cli docker image: ${OUTPUT_QCOS_CLI_IMAGE_PATH}"
    else
      echo -e "\nExported qcos-cli docker image: skipped"
    fi
  fi
  if [ "${qcos}" = true ];then
    if [ "${save}" = true ];then
      echo -e "\nExported qcos docker image: ${OUTPUT_QCOS_IMAGE_PATH}"
    else
      echo -e "\nExported qcos docker image: skipped"
    fi
  fi
}

mkdir -p ${OUTPUT_IMAGE_DIR}
cd ${BUILD_SCRIPTS_DIR}
build_image
