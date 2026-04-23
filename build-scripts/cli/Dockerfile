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

LABEL stage=${CONTAINER_NAME}-builder
LABEL build=${CONTAINER_NAME}
LABEL maintainer="Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>"

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

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
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
# install basic rpms
    yum install -y hostname openssh openssh-clients sshpass iputils iproute \
      telnet net-tools openssl util-linux vim findutils \
      python3 python3-pip python3-requests python3-devel postgresql && \
    if [ "${DEV,,}" = "false" ]; then \
      # install qcos wheel package in production mode
      pip3 install ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl;  \
      cp -rf /usr/local/share/wy_qcos_client/samples /root/ ; \
    else \
      # install qcos resource files in dev mode
      cp -rf ${BUILD_CONTEXT}/samples /root/ ; \
    fi && \
# create symbolic link for python3
    ln -sf /usr/bin/python3 /usr/bin/python && \
# install python3 deps
    if [ "${DEV,,}" != "false" ]; then pip3 install --no-cache-dir --upgrade -r ${BUILD_CONTEXT}/build-scripts/cli/requirements.txt; fi && \
# generate ssh keys
    rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A && \
# write build info
    commit_id=$(cat "${BUILD_CONTEXT}/latest-commit-id.txt" 2>/dev/null || echo "") && \
    echo -e "QCOS-cli build info\nversion: ${QCOS_IMAGE_VERSION}\ncommit id: ${commit_id}\nbuild time: ${build_date}\n" > /root/build-info.txt && \
# cleanup build-context
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

WORKDIR /root
ENTRYPOINT ["/entrypoint.sh"]
