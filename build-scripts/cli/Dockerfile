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
ARG DOCKER_USER_QCOS
ARG PYTHON_SRC_MIRROR

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

COPY ./ ${BUILD_CONTEXT}
WORKDIR /root

RUN set -e && \
# copy qcos dir
    build_date=`date` && \
    if [ "${DEV,,}" != "false" ]; then mkdir -p /root/qcos-project; fi && \
    if [ "${DEV,,}" != "false" ]; then cp -rf ${BUILD_CONTEXT}/bin/qcos-cli.py /usr/bin/qcos-cli; fi && \
# config system
    /bin/cp ${BUILD_CONTEXT}/build-scripts/cli/entrypoint.sh / && \
    chmod +x /entrypoint.sh && \
    echo "LANG=C.UTF-8" > /etc/locale.conf && \
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then mkdir -p /tmp/yum.repos.d/; mv /etc/yum.repos.d/*.repo /tmp/yum.repos.d/; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
# install basic rpms
    yum install --nobest -y hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils sudo make gcc wget \
      sqlite-devel bzip2-devel zlib-devel openssl-devel ncurses-devel gdbm-devel readline-devel tk-devel libffi-devel libuuid-devel libnsl2-devel \
      python3 python3-pip python3-requests python3-devel && \
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
      echo ${python_src_file}; \
      echo ${python_build_dir}; \
      echo ${PYTHON_SRC_MIRROR}; \
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
# install python basic requirements
    ${PIPBIN} install --no-cache-dir tomlkit && \
    if [ "${PIPBIN}" != "/usr/bin/pip3" ]; then \
      pip3 install --no-cache-dir tomlkit ; \
    fi \
    && \
# Install isolated venv
    venv_dir=/var/lib/qcos/venv/qcos-cli && \
    ${PYTHONBIN} -m venv /var/lib/qcos/venv/qcos-cli && \
# install python requirements
    cd ${BUILD_CONTEXT}/build-scripts/cli/ && \
    ${BUILD_CONTEXT}/requirements/export-requirements.py ./pyproject.toml ./requirements.txt && \
    source ${venv_dir}/bin/activate ; \
    pip3 install --no-cache-dir -r ./requirements.txt ; \
    deactivate && \
# install qcos wheel package
    if [ "${DEV,,}" = "false" ]; then \
      # install qcos wheel package in production mode
      source ${venv_dir}/bin/activate ; \
      pip3 install --no-cache-dir ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl ; \
      deactivate ; \
      ls -al ${venv_dir}/share/ ; \
      cp -rf ${venv_dir}/share/wy_qcos_client/samples /root/ ; \
    else \
      # install qcos resource files in dev mode
      cp -rf ${BUILD_CONTEXT}/samples /root/ ; \
    fi && \
# create symbolic link for python3
    ln -sf /usr/bin/python3 /usr/bin/python && \
# generate ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# Active venv: qcos
    echo "source ${venv_dir}/bin/activate" >> /root/.bashrc && \
# write build info
    commit_id=$(cat "${BUILD_CONTEXT}/latest-commit-id.txt" 2>/dev/null || echo "") && \
    echo -e "QCOS-cli build info\nversion: ${QCOS_IMAGE_VERSION}\ncommit id: ${commit_id}\nbuild time: ${build_date}\n" > /root/build-info.txt && \
# cleanup build-context
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; mv /tmp/yum.repos.d/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then rm -rf /root/.pip; fi && \
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

RUN useradd -u 1000 -g root -m qcos && \
    echo "qcos ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/qcos
USER ${DOCKER_USER_QCOS}
WORKDIR /root
ENTRYPOINT ["/entrypoint.sh"]
