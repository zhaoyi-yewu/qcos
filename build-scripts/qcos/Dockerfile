# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# ----------------------------------------------------------------------
# Global ARG
ARG CONTAINER_BASE_IMAGE
ARG BUILD_CONTEXT=/tmp/build-context
ARG CONTAINER_NAME

# ====== STAGE 1: base-builder ======
FROM ${CONTAINER_BASE_IMAGE} AS base
LABEL stage=base-builder
LABEL build=${CONTAINER_NAME}

ARG BUILD_CONTEXT
ARG CONTAINER_NAME

ENV TZ=Asia/Shanghai
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en

MAINTAINER Zhao Yi <zhaoyi_yewu@cmss.chinamobile.com>

WORKDIR /root

ADD ./.build-context/ ${BUILD_CONTEXT}

ENV PYTHONBIN=/usr/bin/python3
ENV PIPBIN=/usr/bin/pip3
ENV VENV_PATH=/var/lib/qcos/venv

# Load envionment variables
RUN source ${BUILD_CONTEXT}/build-scripts/.env
# create dirs
RUN mkdir -p /tmp/requirements \
    && mkdir -p /etc/qcos/ \
    && mkdir -p /etc/qcos-template/ \
    && mkdir -p /etc/qcos/ssl/ \
    && mkdir -p /var/lib/qcos/ \
    && mkdir -p /var/run/qcos/ \
    && mkdir -p /var/log/qcos/
# copy requirements
RUN cp -rf ${BUILD_CONTEXT}/requirements/requirements*.txt /tmp/requirements/
# config yum and pip repos
RUN if [ -f "${BUILD_CONTEXT}/openEuler.repo" ]; then rm -rf /etc/yum.repos.d/*.repo; cp ${BUILD_CONTEXT}/*.repo /etc/yum.repos.d/; fi \
    && if [ -f "${BUILD_CONTEXT}/pip.conf" ]; then mkdir -p /root/.pip; cp ${BUILD_CONTEXT}/pip.conf /root/.pip/pip.conf; fi
# install basic rpm packages
RUN yum install -y hostname openssh openssh-clients sshpass iputils iproute \
    telnet net-tools openssl util-linux vim findutils dos2unix wget rsync \
    gettext make cmake gcc gcc-g++ rust cargo \
    python3 python3-pip python3-sphinx python3-requests python3-devel \
    sqlite-devel bzip2-devel ncurses-devel gdbm-devel xz-devel \
    tk-devel tcl-devel libuuid-devel yp-tools ypbind readline-devel \
    libyaml-devel libffi-devel openssl-devel zlib-devel && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    yum clean all
# install python basic requirements
RUN pip3 install --no-cache-dir -r /tmp/requirements/requirements.txt
# Build customized Python if reuqired
RUN if [ -n "${PYTHON_SRC_MIRROR}" ]; then \
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
    else \
      # # create python-qcos symbolic links according to system-installed python
      ln -s /usr/bin/python3.11 /usr/bin/python3.11-qcos ; \
      ln -s /usr/bin/python3.11-qcos /usr/bin/python3-qcos ; \
      ln -s /usr/bin/python3-qcos /usr/bin/python-qcos ; \
      ln -s /usr/bin/pip3.11 /usr/bin/pip3.11-qcos ; \
      ln -s /usr/bin/pip3.11-qcos /usr/bin/pip3-qcos ; \
      ln -s /usr/bin/pip3-qcos /usr/bin/pip-qcos ; \
      ln -s /usr/bin/pydoc3.11 /usr/bin/pydoc3-qcos ; \
      ln -s /usr/bin/python3.11-config /usr/bin/python3.11-config-qcos ; \
      ln -s /usr/bin/python3.11-config-qcos /usr/bin/python3-config-qcos ; \
    fi
# Install pypy3 if required
RUN if [ -n "${PYPY3_BIN_MIRROR}" ]; then \
      mkdir -p /usr/local/pypy3 ; \
      pypy3_pkg_file=$(basename ${PYPY3_BIN_MIRROR}) ; \
      wget -P /tmp/ ${PYPY3_BIN_MIRROR} ; \
      tar xjvf /tmp/${pypy3_pkg_file} --strip-components=1 -C /usr/local/pypy3 ; \
      ln -s /usr/local/pypy3/bin/pypy3 /usr/bin/pypy3 ; \
      rm -rf /tmp/${pypy3_pkg_file} ; \
    fi
# Install islolated venv for drivers that requires extra packages
RUN ${PYTHONBIN} ${BUILD_CONTEXT}/requirements/install-venvs.py --venv-dir ${VENV_PATH} --default-python3 ${PYTHONBIN} --default-pypy pypy3
# Create ssh keys
RUN rm -rf /root/.ssh/id_rsa && \
    ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -N "" && \
    ssh-keygen -A

# ====== STAGE 2: qcos-builder ======
FROM base AS qcos-builder
LABEL stage=qcos-builder

ARG BUILD_CONTEXT
ARG CONTAINER_NAME
ARG QCOS_IMAGE_VERSION
ARG DEV
ARG PYTHON_SRC_MIRROR

ENV QCOS_CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${QCOS_CONTAINER_NAME})[$(pwd)]$ "

# Copy command line entrypoints
RUN cp -rf ${BUILD_CONTEXT}/bin/qcos-cli.py /usr/bin/qcos-cli \
    && cp -rf ${BUILD_CONTEXT}/bin/qcos-api.py /usr/bin/qcos-api \
    && cp -rf ${BUILD_CONTEXT}/bin/qcos-transpiler.py /usr/bin/qcos-transpiler \
    && chmod +x /usr/bin/qcos-cli /usr/bin/qcos-api /usr/bin/qcos-transpiler
# Copy docker entrypint
RUN /bin/cp ${BUILD_CONTEXT}/build-scripts/qcos/entrypoint.sh / && chmod +x /entrypoint.sh
# Install qcos/qcos-cli packages
RUN if [ "${DEV,,}" = "false" ]; then \
      # production mode: install qcos/qcos-cli wheel packages, and copy config/samples files only
      DEFAULT_VENV_PATH=/var/lib/qcos/venv/default ; \
      source ${DEFAULT_VENV_PATH}/bin/activate ; \
      pip3 install --no-cache-dir ${BUILD_CONTEXT}/pkg/wy_qcos-*.whl ${BUILD_CONTEXT}/pkg/wy_qcos_client-*.whl;  \
      deactivate ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${DEFAULT_VENV_PATH}/share/wy_qcos_client/samples /root/ ; \
    else \
      # dev mode: copy config/samples files only
      mkdir -p /root/qcos-project ; \
      cp -rf ${BUILD_CONTEXT}/etc/qcos/* /etc/qcos-template/ ; \
      cp -rf ${BUILD_CONTEXT}/samples /root/ ; \
    fi
# Active venv: qcos
RUN echo "source /var/lib/qcos/venv/default/bin/activate" >> /root/.bashrc
RUN rm -rf ${VENV_PATH}/sandbox
# Write build date/commit-id/version into build-info file
RUN build_date=`date` && \
    commit_id=$(cat "${BUILD_CONTEXT}/latest-commit-id.txt" 2>/dev/null || echo "") && \
    echo -e "QCOS build info\nversion: ${QCOS_IMAGE_VERSION}\ncommit id: ${commit_id}\nbuild time: ${build_date}\n" > /root/build-info.txt

# ====== STAGE 3: sandbox-builder ======
FROM qcos-builder AS sandbox-builder
LABEL stage=sandbox-builder

ARG BUILD_CONTEXT
ARG CONTAINER_NAME
ARG SANDBOX_IMAGE_VERSION
ARG NPM_MIRROR

ENV QCOS_CONTAINER_NAME=${CONTAINER_NAME}
ENV PS1="(\${QCOS_CONTAINER_NAME}-sandbox)[$(pwd)]$ "

# Install extra rpm packages for sandbox: LaTeX/fonts/Java/Graphics etc.
RUN yum install -y rpm-build firefox java graphviz \
    texlive-gnu-freefont latexmk texlive texlive-xetex texlive-xecjk \
    texlive-ctex texlive-fncychap texlive-wrapfig texlive-capt-of \
    texlive-framed texlive-upquote texlive-needspace texlive-tabulary \
    texlive-lastpage texlive-tocloft texlive-supertabular \
    google-noto-sans-sc-fonts docker npm && \
    mktexlsr && fc-cache -fv && \
    yum clean all
# Install NPM packages: mermaid-cli, plantuml etc.
RUN registry_url="" && \
    npm_cmd_args="" && \
    if [ -n "${NPM_MIRROR}" ]; then registry_url="--registry=${NPM_MIRROR}"; fi && \
    PUPPETEER_SKIP_DOWNLOAD=true npm install ${npm_cmd_args} ${registry_url} -g @mermaid-js/mermaid-cli plantuml
# Active venv: sandbox
RUN echo "source /var/lib/qcos/venv/sandbox/bin/activate" >> /root/.bashrc
# Write build date/commit-id/version into build-info file
RUN echo -e "\nSANDBOX build info\nversion: ${SANDBOX_IMAGE_VERSION}\n" >> /root/build-info.txt
