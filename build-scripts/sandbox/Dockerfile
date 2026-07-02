# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# ----------------------------------------------------------------------

FROM qcos-base:dev AS sandbox-builder

ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME
ARG WORK_DIR=/root/qcos-project

ARG SANDBOX_IMAGE_VERSION
ARG NPM_MIRROR

LABEL stage=${CONTAINER_NAME}-builder
LABEL build=${CONTAINER_NAME}
LABEL maintainer="Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>"

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "
ENV QCOS_SANDBOX=true

# Install extra rpm packages for sandbox: LaTeX/fonts/Java/Graphics etc.
RUN set -e && \
    yum install --nobest -y rpm-build firefox java npm graphviz \
    texlive-gnu-freefont latexmk texlive texlive-xetex texlive-xecjk \
    texlive-ctex texlive-fncychap texlive-wrapfig texlive-capt-of \
    texlive-framed texlive-upquote texlive-needspace texlive-tabulary \
    texlive-lastpage texlive-tocloft texlive-supertabular \
    google-noto-sans-sc-fonts librsvg2-tools gtest-devel && \
    mktexlsr && fc-cache -fv && \
    # Install NPM packages: mermaid-cli, plantuml etc.
    registry_url="" && \
    npm_cmd_args="" && \
    if [ -n "${NPM_MIRROR}" ]; then registry_url="--registry=${NPM_MIRROR}"; fi && \
    PUPPETEER_SKIP_DOWNLOAD=true npm install ${npm_cmd_args} ${registry_url} -g @mermaid-js/mermaid-cli plantuml \
    && \
    # Active venv: sandbox
    echo "source /var/lib/qcos/venv/sandbox/bin/activate" >> /root/.bashrc && \
    # Write build date/commit-id/version into build-info file
    echo -e "\nSANDBOX build info\nversion: ${SANDBOX_IMAGE_VERSION}\n" >> /root/build-info.txt && \
    # cleanup
    yum clean all
