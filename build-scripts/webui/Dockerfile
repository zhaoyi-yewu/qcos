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
# Node.js binary mirror (tar.xz dist) used to install a modern node
# runtime. The distro npm package ships node 12 which cannot run
# vite 6 (requires node >= 18, top-level await).
ARG NODE_BIN_MIRROR

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
    /bin/cp ${BUILD_CONTEXT}/build-scripts/webui/parse-webui-toml.py /usr/local/bin/ && \
    chmod +x /usr/local/bin/parse-webui-toml.py && \
    echo "LANG=C.UTF-8" > /etc/locale.conf && \
# copy yum repos and create dirs
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then mkdir -p /tmp/yum.repos.d/; mv /etc/yum.repos.d/*.repo /tmp/yum.repos.d/; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi && \
    if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi && \
# install basic rpms (nodejs is installed separately below because
# the distro npm package is too old for vite 6)
    yum install -y hostname iputils iproute telnet net-tools openssl \
      util-linux vim sudo npm nginx xz wget && \
# install modern nodejs >= 18: vite 6 uses top-level await which the
# distro node 12 cannot parse. Download the official binary tarball
# from NODE_BIN_MIRROR and put it ahead of PATH.
    if [ -n "${NODE_BIN_MIRROR}" ]; then \
      echo "Installing nodejs: ${NODE_BIN_MIRROR}" ; \
      node_tar_file=$(basename ${NODE_BIN_MIRROR}) ; \
      wget -q ${NODE_BIN_MIRROR} -O /tmp/${node_tar_file} && \
      tar xzf /tmp/${node_tar_file} -C /usr/local --strip-components=1 && \
      rm -f /tmp/${node_tar_file} && \
      node --version && \
      npm --version ; \
    fi \
    && \
# install npm packages
    rm -rf ${app_dir}/dist ${app_dir}/node_modules ${app_dir}/package-lock.json && \
    npm cache clean --force && \
    if [ -n "${NPM_MIRROR}" ]; then npm config set registry ${NPM_MIRROR}; fi && \
    # install packages: dev build needs devDependencies
    # (e.g. vite/eslint for npm run dev)
    if [ "${DEV,,}" = "true" ]; then \
      npm install --no-audit --verbose; \
      # dev mode: node_modules should installed in parent dir, not source dir
      mv ${app_dir}/node_modules ${app_dir}/.. ; \
    else \
      npm install --no-audit && \
      npm run build:prod && \
      cp -rf ${app_dir}/dist/ /apps && \
      rm -rf ${app_dir} && \
      cd /root; \
    fi && \
    if [ -n "${NPM_MIRROR}" ]; then npm config delete registry; fi && \
    npm cache clean --force && \
# cleanup build-context
    echo -e "QCOS webui build info\nversion: ${QCOS_WEBUI_IMAGE_VERSION}\nBuild time: ${build_date}\n" > /root/build-info.txt && \
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

RUN useradd -u 1000 -g root -m qcos && \
    echo "qcos ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/qcos
USER ${DOCKER_USER_QCOS}
ENTRYPOINT ["/entrypoint.sh"]
