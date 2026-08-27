# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# ----------------------------------------------------------------------

ARG CONTAINER_BASE_IMAGE
FROM ${CONTAINER_BASE_IMAGE}

ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME
ARG WORK_DIR=/root
ARG DEV

ARG PYTHON_SRC_MIRROR
ARG PYPY3_BIN_MIRROR
ARG DOCKER_COMPOSE_BIN_MIRROR

LABEL stage=${CONTAINER_NAME}-builder
LABEL build=${CONTAINER_NAME}
LABEL maintainer="Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>"

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

ENV PYTHONBIN=/usr/bin/python3
ENV PIPBIN=/usr/bin/pip3
ENV VENV_PATH=/var/lib/qcos/venv

WORKDIR ${WORK_DIR}

COPY ./ ${BUILD_CONTEXT}

# Load envionment variables
RUN set -e && \
# create dirs
    mkdir -p /tmp/requirements \
    && mkdir -p /etc/qcos/ \
    && mkdir -p /etc/qcos-template/ \
    && mkdir -p /etc/qcos/ssl/ \
    && mkdir -p /var/lib/qcos/ \
    && mkdir -p /var/run/qcos/ \
    && mkdir -p /var/log/qcos/ \
    && \
# copy requirements
    cp -rf ${BUILD_CONTEXT}/pyproject.toml ${BUILD_CONTEXT}/LICENSE /tmp/ \
    && \
# config yum and pip repos
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then mkdir -p /tmp/yum.repos.d/; mv /etc/yum.repos.d/*.repo /tmp/yum.repos.d/; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
# install basic rpm packages
    yum install --nobest -y glibc-langpack-en hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils dos2unix wget rsync jq patch \
      gettext make cmake gcc gcc-g++ rust cargo postgresql docker sudo unzip \
      python3 python3-pip python3-sphinx python3-requests python3-devel \
      sqlite-devel bzip2-devel ncurses-devel gdb gdbm-devel xz-devel boost-devel  \
      tk-devel tcl-devel libuuid-devel yp-tools ypbind readline-devel \
      libyaml-devel libffi-devel openssl-devel zlib-devel gtest-devel && \
    echo "LANG=C.UTF-8" > /etc/locale.conf && \
    ln -sf /usr/bin/python3 /usr/bin/python \
    && \
# install extra packages: docker-compose
    if [ -n "${DOCKER_COMPOSE_BIN_MIRROR}" ]; then \
      echo "Installing docker-compose: ${DOCKER_COMPOSE_BIN_MIRROR}" ; \
      wget -q ${DOCKER_COMPOSE_BIN_MIRROR} -O /usr/bin/docker-compose && \
      chmod 755 /usr/bin/docker-compose ; \
    fi \
    && \
# Build customized Python if required
    if [ "${PYTHON_SRC_MIRROR,,}" = "false" ]; then \
      echo "Building Python3 from source code: skipped" ; \
      # create python-qcos symbolic links according to system-installed python
      ln -s /usr/bin/python3.11 /usr/bin/python3.11-qcos ; \
      ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
      ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
      ln -s /usr/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
      ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
      ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
      ln -s /usr/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
      ln -s /usr/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
      ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
    else \
      echo "Building Python3 from source code: ${PYTHON_SRC_MIRROR}" ; \
      python_build_dir="/tmp/python-build" ; \
      rm -rf ${python_build_dir} ; \
      mkdir -p ${python_build_dir} ; \
      python_src_file=$(basename ${PYTHON_SRC_MIRROR}) ; \
      wget -P /tmp/ ${PYTHON_SRC_MIRROR} ; \
      tar xzvf /tmp/${python_src_file} --strip-components=1 -C ${python_build_dir} ; \
      cd ${python_build_dir} ; \
      ./configure \
        --prefix=/usr/local/python3.11 \
        --enable-optimizations \
        --enable-shared \
        --with-lto \
        --with-system-ffi \
        --with-openssl=/usr \
        CFLAGS="-O2 -fPIC" \
        LDFLAGS="-Wl,-rpath=/usr/local/python3.11/lib" ; \
      make -j $(nproc) ; \
      make altinstall ; \
      # create python-qcos symbolic links according to customized python
      ln -s /usr/local/python3.11/bin/python3.11 /usr/bin/python3.11-qcos ; \
      ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
      ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
      ln -s /usr/local/python3.11/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
      ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
      ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
      ln -s /usr/local/python3.11/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
      ln -s /usr/local/python3.11/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
      ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
      # Update PYTHONBIN/PIPBIN
      export PYTHONBIN=/usr/bin/python3-qcos ; \
      export PIPBIN=/usr/bin/pip3-qcos ; \
    fi \
    && \
# Install pypy3 if required
    if [ "${PYPY3_BIN_MIRROR,,}" = "false" ]; then \
      echo "PYPY3 installation: skipped" ; \
    else \
      echo "PYPY3 installation: ${PYPY3_BIN_MIRROR}" ; \
      mkdir -p /usr/local/pypy3 ; \
      pypy3_pkg_file=$(basename ${PYPY3_BIN_MIRROR}) ; \
      wget -P /tmp/ ${PYPY3_BIN_MIRROR} ; \
      tar xjvf /tmp/${pypy3_pkg_file} --strip-components=1 -C /usr/local/pypy3 ; \
      ln -s /usr/local/pypy3/bin/pypy3 /usr/bin/pypy3 ; \
      rm -rf /tmp/${pypy3_pkg_file} ; \
    fi \
    && \
# install python basic requirements
    ${PIPBIN} install --no-cache-dir tomlkit==0.15.1 && \
    if [ "${PIPBIN}" != "/usr/bin/pip3" ]; then \
      pip3 install --no-cache-dir tomlkit==0.15.1 ; \
    fi \
    && \
# install python requirements
    cd ${BUILD_CONTEXT}/ && \
    ${BUILD_CONTEXT}/requirements/export-requirements.py --extra base --no-deps ./pyproject.toml ./requirements.txt && \
    pip3 install --no-cache-dir -r ./requirements.txt && \
# Install isolated venv for drivers that requires extra packages
    ${PYTHONBIN} ${BUILD_CONTEXT}/requirements/install-venvs.py --venv-dir ${VENV_PATH} --default-python3 ${PYTHONBIN} --default-pypy pypy3 && \
# Create ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# cleanup
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; mv /tmp/yum.repos.d/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then rm -rf /root/.pip; fi && \
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

