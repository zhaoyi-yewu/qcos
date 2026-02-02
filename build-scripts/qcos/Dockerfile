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

ARG CONTAINER_BASE_IMAGE
FROM ${CONTAINER_BASE_IMAGE}

ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME
ARG QCOS_IMAGE_VERSION
ARG DEV

LABEL stage=builder
LABEL build=${CONTAINER_NAME}
ENV TZ=Asia/Shanghai

MAINTAINER Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>

COPY ./.build-context/ ${BUILD_CONTEXT}
WORKDIR /root

RUN \
# init vars
    PYTHONBIN=/usr/bin/python3 \
    PIPBIN=/usr/bin/pip3 \
    python_build_dir= \
    python_src_file= \
# copy qcos dir
    build_date=`date` && \
    source ${BUILD_CONTEXT}/build-scripts/.env && \
    mkdir -p /tmp/requirements && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-cli.py /usr/bin/qcos-cli && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-api.py /usr/bin/qcos-api && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-transpiler.py /usr/bin/qcos-transpiler && \
    cp -rf ${BUILD_CONTEXT}/requirements/requirements*.txt /tmp/requirements/ && \
# config system
    /bin/cp ${BUILD_CONTEXT}/build-scripts/qcos/entrypoint.sh / && \
    chmod +x /entrypoint.sh && \
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
    mkdir -p /etc/qcos/ && \
    mkdir -p /etc/qcos-template/ && \
    mkdir -p /etc/qcos/ssl/ && \
    mkdir -p /var/lib/qcos/ && \
    mkdir -p /var/run/qcos/ && \
    mkdir -p /var/log/qcos/ && \
# install basic rpms
    yum install -y hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils dos2unix wget rsync \
      libffi-devel sqlite-devel bzip2-devel ncurses-devel gdbm-devel xz-devel \
      tk-devel tcl-devel libuuid-devel yp-tools ypbind readline-devel \
      libyaml-devel zlib-devel \
      gettext openssl-devel make cmake gcc gcc-g++ rust cargo \
      python3 python3-pip python3-sphinx python3-requests python3-devel && \
# make python symbolic link
    ln -sf /usr/bin/python3 /usr/bin/python && \
# install requirements for default python3
    pip3 install --no-cache-dir -r /tmp/requirements/requirements.txt -r /tmp/requirements/requirements-test.txt && \
# compile python3 if required
    if [ -n "${PYTHON_SRC_MIRROR}" ]; then \
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
      ln -s /usr/local/python3.11/bin/python3.11 /usr/bin/python3.11-qcos ; \
      ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
      ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
      ln -s /usr/local/python3.11/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
      ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
      ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
      ln -s /usr/local/python3.11/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
      ln -s /usr/local/python3.11/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
      ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
      PYTHONBIN=/usr/bin/python3-qcos ; \
      PIPBIN=/usr/bin/pip3-qcos ; \
    else \
      ln -s /usr/bin/python3.11 /usr/bin/python3.11-qcos ; \
      ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
      ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
      ln -s /usr/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
      ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
      ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
      ln -s /usr/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
      ln -s /usr/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
      ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
    fi && \
# install pypy3 if required
    if [ -n "${PYPY3_BIN_MIRROR}" ]; then \
      mkdir -p /usr/local/pypy3 ; \
      pyp3_bin_file=$(basename ${PYPY3_BIN_MIRROR}) ; \
      wget -P /tmp/ ${PYPY3_BIN_MIRROR} ; \
      tar xjvf /tmp/${pyp3_bin_file} --strip-components=1 -C /usr/local/pypy3 ; \
      ln -s /usr/local/pypy3/bin/pypy3 /usr/bin/pypy3 ; \
      rm -rf ${pyp3_bin_file} ; \
    fi && \
# install driver deps
    ${PIPBIN} install --no-cache-dir -r /tmp/requirements/requirements.txt && \
    VENV_PATH=/var/lib/qcos/venv && \
    ${PYTHONBIN} ${BUILD_CONTEXT}/requirements/install-venvs.py --venv-dir ${VENV_PATH} && \
# create symbolic link for python3
    if [ "${DEV,,}" = "false" ]; then \
      # install qcos wheel package in production mode \
      DEFAULT_VENV_PATH=${VENV_PATH}/default ; \
      source ${DEFAULT_VENV_PATH}/bin/activate ; \
      pip3 install --no-cache-dir ${BUILD_CONTEXT}/pkg/wy_qcos-*.whl ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl;  \
      deactivate ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos_client/samples /root/ ; \
    else \
      # install qcos resource files in dev mode
      mkdir -p /root/qcos-project ; \
      cp -rf ${BUILD_CONTEXT}/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${BUILD_CONTEXT}/samples /root/ ; \
    fi && \
# generate ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# write build info
    commit_id=$(cat "${BUILD_CONTEXT}/latest-commit-id.txt" 2>/dev/null || echo "") && \
    echo -e "QCOS build info\nversion: ${QCOS_IMAGE_VERSION}\ncommit id: ${commit_id}\nbuild time: ${build_date}\n" > /root/build-info.txt && \
# config bash
    echo "source /var/lib/qcos/venv/default/bin/activate" >> /root/.bashrc && \
# cleanup build-context
    yum clean all && \
    if [ -n "${PYTHON_SRC_MIRROR}" ]; then \
      rm -rf ${python_build_dir} ${python_src_file} ; \
    fi && \
    rm -rf ${BUILD_CONTEXT}

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV QCOS_CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${QCOS_CONTAINER_NAME})[$(pwd)]$ "

WORKDIR /root
ENTRYPOINT ["/entrypoint.sh"]
