# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# ----------------------------------------------------------------------

FROM qcos-base:dev AS qcos-builder

ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME
ARG WORK_DIR=/root
ARG DEV

ARG QCOS_IMAGE_VERSION

LABEL stage=${CONTAINER_NAME}-builder
LABEL build=${CONTAINER_NAME}
LABEL maintainer="Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>"

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

COPY ./ ${BUILD_CONTEXT}

# Copy command line entrypoints
RUN set -e && \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-cli.py /usr/bin/qcos-cli &&  \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-api.py /usr/bin/qcos-api &&  \
    cp -rf ${BUILD_CONTEXT}/bin/qcos-transpiler.py /usr/bin/qcos-transpiler &&  \
    chmod +x /usr/bin/qcos-cli /usr/bin/qcos-api /usr/bin/qcos-transpiler &&  \
    # config yum and pip repos
    if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi \
    && if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi \
    && \
# Copy docker entrypoint
    /bin/cp ${BUILD_CONTEXT}/build-scripts/qcos/entrypoint.sh / && chmod +x /entrypoint.sh && \
# Install qcos/qcos-cli packages
    if [ "${DEV,,}" = "false" ]; then \
      # production mode: install qcos/qcos-cli wheel packages, and copy config/samples files only
      DEFAULT_VENV_PATH=/var/lib/qcos/venv/default ; \
      source ${DEFAULT_VENV_PATH}/bin/activate ; \
      pip3 install --no-cache-dir ${BUILD_CONTEXT}/pkg/wy_qcos-*.whl ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl;  \
      deactivate ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos_client/samples /root/ ; \
    else \
      # dev mode: copy config/samples files only
      WORK_DIR=/root/qcos-project ; \
      mkdir -p /root/qcos-project ; \
      cp -rf ${BUILD_CONTEXT}/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${BUILD_CONTEXT}/samples /root/ ; \
    fi \
    && \
# Active venv: qcos
    echo "source /var/lib/qcos/venv/default/bin/activate" >> /root/.bashrc && \
    rm -rf ${VENV_PATH}/sandbox && \
# Write build date/commit-id/version into build-info file
    build_date=`date` && \
    commit_id=$(cat "${BUILD_CONTEXT}/latest-commit-id.txt" 2>/dev/null || echo "") && \
    echo -e "QCOS build info\nversion: ${QCOS_IMAGE_VERSION}\ncommit id: ${commit_id}\nbuild time: ${build_date}\n" > /root/build-info.txt && \
# cleanup
    yum clean all && \
    rm -rf ${BUILD_CONTEXT}

WORKDIR ${WORK_DIR}
ENTRYPOINT ["/entrypoint.sh"]
