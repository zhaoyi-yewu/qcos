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
ARG SANDBOX_IMAGE_VERSION
ARG NPM_MIRROR

LABEL stage=builder
LABEL build=${CONTAINER_NAME}
ENV TZ=Asia/Shanghai

MAINTAINER Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>

ADD ./.build-context/ ${BUILD_CONTEXT}
WORKDIR /root

RUN set -e && \
# init vars
    PYTHONBIN=/usr/bin/python3 \
    PIPBIN=/usr/bin/pip3 \
# copy qcos dir
    source ${BUILD_CONTEXT}/build-scripts/.env && \
    mkdir -p /tmp/requirements && \
    cp -rf ${BUILD_CONTEXT}/requirements/requirements*.txt /tmp/requirements/ && \
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
    mkdir -p /etc/qcos/ && \
    mkdir -p /etc/qcos-template/ && \
    mkdir -p /etc/qcos/ssl/ && \
    mkdir -p /var/run/qcos/ && \
    mkdir -p /var/log/qcos/ && \
# install basic rpms
    yum install -y hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils dos2unix wget gettext \
      texlive-gnu-freefont latexmk texlive texlive-xetex texlive-xecjk \
      texlive-ctex texlive-fncychap texlive-wrapfig texlive-capt-of \
      texlive-framed texlive-upquote texlive-needspace texlive-tabulary \
      texlive-lastpage texlive-tocloft texlive-supertabular \
      texlive-collection-langchinese google-noto-sans-sc-fonts \
      docker rpm-build make cmake gcc gcc-g++ rust cargo rsync \
      npm firefox java graphviz \
      python3 python3-pip python3-sphinx python3-requests python3-devel && \
# update fonts
    mktexlsr && \
    fc-cache -fv  && \
# create symbolic link for python3
    ln -sf /usr/bin/python3 /usr/bin/python && \
# install requirements for default python3
    ln -s /usr/bin/python3.11 /usr/bin/python3.11-qcos ; \
    ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
    ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
    ln -s /usr/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
    ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
    ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
    ln -s /usr/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
    ln -s /usr/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
    ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
# install driver deps
    ${PIPBIN} install --no-cache-dir -r /tmp/requirements/requirements.txt && \
    VENV_PATH=/var/lib/qcos/venv && \
    ${PYTHONBIN} ${BUILD_CONTEXT}/requirements/install-venvs.py --venv-dir ${VENV_PATH} && \
# install npm deps
    registry_url="" && \
    npm_cmd_args="" && \
    if [ -n "${NPM_MIRROR}" ]; then registry_url="--registry=${NPM_MIRROR}"; fi && \
    PUPPETEER_SKIP_DOWNLOAD=true npm install ${npm_cmd_args} ${registry_url} -g @mermaid-js/mermaid-cli plantuml && \
# config bash
    echo "source /var/lib/qcos/venv/sandbox/bin/activate" >> /root/.bashrc && \
# generate ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# cleanup build-context
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

WORKDIR /root
