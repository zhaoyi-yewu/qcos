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

ARG CONTAINER_BASE_IMAGE
FROM ${CONTAINER_BASE_IMAGE}

ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME
ARG QCOS_WEBUI_IMAGE_VERSION
ARG DEV
ARG NPM_MIRROR
ARG DOCKER_USER_QCOS

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
# copy qcos-webui dir
    app_dir=/root/qcos-webui && \
    build_date=`date` && \
    mkdir -p ${app_dir} && \
    cd ${app_dir} && \
    cp -rf ${BUILD_CONTEXT}/webui/* ${app_dir} && \
# config system
    /bin/cp ${BUILD_CONTEXT}/build-scripts/webui/config/nginx.conf /root/ && \
    /bin/cp ${BUILD_CONTEXT}/build-scripts/webui/entrypoint.sh / && \
    chmod +x /entrypoint.sh && \
# copy yum repos and create dirs
    rm -rf /etc/yum.repos.d/*.repo && \
    cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/ && \
# install basic rpms
    yum install -y hostname iputils iproute telnet net-tools openssl \
      util-linux vim sudo npm nginx && \
# install npm packages
    rm -rf ${app_dir}/dist ${app_dir}/node_modules ${app_dir}/package-lock.json && \
    npm cache clean --force && \
    if [ -n "${NPM_MIRROR}" ]; then npm config set registry ${NPM_MIRROR}; fi && \
    # install packages: dev build needs devDependencies
    # (e.g. @vue/cli-service for npm run dev)
    if [ "${DEV,,}" = "true" ]; then \
      npm install --no-audit --verbose; \
    else \
      npm install --no-audit && \
      npm run build:prod && \
      cp -rf ${app_dir}/dist/ /apps && \
      rm -rf ${app_dir}; \
    fi && \
# cleanup build-context
    echo -e "QCOS webui build info\nversion: ${QCOS_WEBUI_IMAGE_VERSION}\nBuild time: ${build_date}\n" > /root/build-info.txt && \
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

RUN useradd -u 1000 -g root -m qcos && \
    echo "qcos ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/qcos
USER ${DOCKER_USER_QCOS}
ENTRYPOINT ["/entrypoint.sh"]
