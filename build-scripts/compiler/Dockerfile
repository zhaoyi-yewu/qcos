# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------
#
# Dockerfile for the qcos-compiler cloud service.
#
# Builds a standalone, lightweight image that exposes the openqasm
# validation/compilation interface (POST /compiler/qasm/compile) for
# cloud platform integration (see cloud.md).
#
# Python is managed with pyenv + venv: pyenv installs a pinned CPython
# (3.12.13 by default) and a virtualenv is created from it for the
# service and its dependencies.
#
# Base image: openeuler/openeuler:24.03-lts (cloud.md section 7)
# Image name: qcos-compiler:latest (cloud.md section 7)

ARG CONTAINER_BASE_IMAGE=openeuler/openeuler:24.03-lts
FROM ${CONTAINER_BASE_IMAGE}

ARG BUILD_CONTEXT=/tmp/build-context
ARG WORK_DIR=/root
ARG DEV=true
ARG PIP_MIRROR
# pinned CPython version installed via pyenv (must satisfy
# pyproject.toml requires-python = ">=3.11,<3.13")
ARG PYTHON_VERSION=3.12.13
# optional: pyenv/python build mirror for offline or accelerated builds
ARG PYENV_MIRROR
ARG PYENV_GIT_URL=https://github.com/pyenv/pyenv.git

LABEL stage=qcos-compiler-builder
LABEL build=qcos-compiler
LABEL maintainer="Zhou Yunxiao <zhouyunxiao_yewu@cmss.chinamobile.com>"

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=qcos-compiler
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

# pyenv home and the virtualenv used by the service
ENV PYENV_ROOT=/opt/pyenv
ENV VENV_PATH=/opt/qcos-compiler-venv
ENV PATH=${PYENV_ROOT}/bin:${VENV_PATH}/bin:${PATH}

WORKDIR ${WORK_DIR}

COPY ./ ${BUILD_CONTEXT}

# Install runtime dependencies and the qcos package, then drop the
# build context to keep the image small.
RUN set -e && \
    mkdir -p /etc/qcos/ /var/log/qcos/ /var/run/qcos/ && \
# install build/runtime rpm packages required to compile CPython with
# pyenv and to run the service
    yum install --nobest -y \
      git wget curl ca-certificates \
      make gcc gcc-c++ \
      openssl-devel libffi-devel bzip2-devel xz-devel \
      zlib-devel readline-devel sqlite-devel ncurses-devel \
      gdbm-devel tk-devel libuuid-devel \
      glibc-langpack-en && \
    echo "LANG=C.UTF-8" > /etc/locale.conf && \
# config pip mirror if provided
    if [ -n "${PIP_MIRROR}" ]; then \
      pip config set global.index-url "${PIP_MIRROR}"; \
    fi && \
# install pyenv and the pinned CPython interpreter
    git clone ${PYENV_GIT_URL} ${PYENV_ROOT} && \
    if [ -n "${PYENV_MIRROR}" ]; then \
      export PYTHON_BUILD_MIRROR_URL="${PYENV_MIRROR}"; \
    fi && \
    ${PYENV_ROOT}/bin/pyenv install ${PYTHON_VERSION} && \
    ${PYENV_ROOT}/bin/pyenv global ${PYTHON_VERSION} && \
    PYENV_PYTHON=$(${PYENV_ROOT}/bin/pyenv prefix ${PYTHON_VERSION})/bin/python && \
    ${PYENV_PYTHON} --version && \
# create the service virtualenv from the pyenv interpreter
    ${PYENV_PYTHON} -m venv ${VENV_PATH} && \
    ${VENV_PATH}/bin/python --version && \
    if [ -n "${PIP_MIRROR}" ]; then \
      ${VENV_PATH}/bin/pip config set global.index-url "${PIP_MIRROR}"; \
    fi && \
    ${VENV_PATH}/bin/pip install --no-cache-dir --upgrade pip && \
    if [ "${DEV,,}" = "false" ]; then \
      # production mode: install the built wheel packages
      ${VENV_PATH}/bin/pip install --no-cache-dir \
        ${BUILD_CONTEXT}/pkg/wy_qcos-*.whl \
        ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl; \
    else \
      # dev mode: install from source with the project dependencies
      ${VENV_PATH}/bin/pip install --no-cache-dir -r \
        ${BUILD_CONTEXT}/requirements/requirements-transpiler-cmss.txt && \
      ${VENV_PATH}/bin/pip install --no-cache-dir -r \
        ${BUILD_CONTEXT}/requirements/requirements-qcos.txt || true; \
      ${VENV_PATH}/bin/pip install --no-cache-dir ${BUILD_CONTEXT}; \
    fi && \
# copy the compiler entrypoint
    cp -rf ${BUILD_CONTEXT}/bin/qcos-compiler.py /usr/bin/qcos-compiler && \
    chmod +x /usr/bin/qcos-compiler && \
# cleanup build toolchain to shrink the image (keep the venv and pyenv
# interpreter)
    yum remove -y gcc gcc-c++ make || true && \
    yum clean all && \
    rm -rf /var/cache/yum ${BUILD_CONTEXT}

EXPOSE 8080

# Run the compiler cloud service with the venv interpreter.
CMD ["/opt/qcos-compiler-venv/bin/python", "/usr/bin/qcos-compiler", "--host", "0.0.0.0", "--port", "8080"]
