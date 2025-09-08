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

ADD ./.build-context/ ${BUILD_CONTEXT}
WORKDIR /root

RUN \
# copy qcos dir
    build_date=`date` && \
    mkdir -p /root/qcos-project && \
    if [ "${DEV,,}" = "false" ]; then cp -rf ${BUILD_CONTEXT}/qcos/* /root/qcos-project/; fi && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-cli.py /usr/bin/qcos-cli && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-api.py /usr/bin/qcos-api && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-transpiler.py /usr/bin/qcos-transpiler && \
    cp -rf ${BUILD_CONTEXT}/requirements.txt /root/ && \
    cp -rf ${BUILD_CONTEXT}/test-requirements.txt /root/ && \
# config system
    /bin/cp ${BUILD_CONTEXT}/build-scripts/entrypoint.sh / && \
    chmod +x /entrypoint.sh && \
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
    mkdir -p /etc/qcos/ && \
    mkdir -p /etc/qcos-template/ && \
    mkdir -p /var/run/qcos/ && \
    mkdir -p /var/log/qcos/ && \
# install basic rpms
    yum install -y hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils  \
      make gcc rust cargo \
      python3 python3-pip python3-sphinx python3-requests python3-devel && \
# create symbolic link for python3
    ln -sf /usr/bin/python3 /usr/bin/python && \
# install python3 deps
    pip3 install --no-cache-dir --upgrade -r /root/requirements.txt -r /root/test-requirements.txt && \
# generate ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# copy config files \
    cp ${BUILD_CONTEXT}/etc/qcos/qcos*.toml /etc/qcos-template/ && \
# cleanup build-context
    echo -e "QCOS build info\nversion: ${QCOS_IMAGE_VERSION}\nBuild time: ${build_date}\n" > /root/build-info.txt && \
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV QCOS_CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${QCOS_CONTAINER_NAME})[$(pwd)]$ "

WORKDIR /root
ENTRYPOINT ["/entrypoint.sh"]
