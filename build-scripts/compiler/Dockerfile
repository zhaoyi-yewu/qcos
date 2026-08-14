# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF
# ANY KIND, EITHER EXPRESS OR IMPLIED.
# ----------------------------------------------------------------------

# Business image for the qcos-compiler cloud service.
#
# Single-stage build on top of qcos-compiler-base (./Dockerfile.base),
# which already carries the OS, pinned CPython and the dependency-filled
# venv. This image only adds: project source, the C++ transpiler
# extension (high_performance.so), the wy_qcos package, and the service
# entrypoint.
#
# Because the slow layers (OS, CPython, Python deps) live in the base
# image, a typical code/C++ change only rebuilds this business image.
#
# Domestic mirrors are still honored for any in-image pip installs.
#
# Build (after building the base image):
#   docker build -f build-scripts/compiler/Dockerfile \
#       -t qcos-compiler:1.5.0 .

ARG COMPILER_BASE_IMAGE=qcos-compiler-base:1.5.0
FROM ${COMPILER_BASE_IMAGE}

ARG BUILD_CONTEXT=/tmp/build-context
ARG PIP_MIRROR=https://pypi.tuna.tsinghua.edu.cn/simple

LABEL stage=qcos-compiler-builder
LABEL build=qcos-compiler
LABEL maintainer="Zhou Yunxiao <zhouyunxiao_yewu@cmss.chinamobile.com>"

ENV CONTAINER_NAME=qcos-compiler
ENV PS1="(\${CONTAINER_NAME})[$(pwd)]$ "

# WORKDIR (/root), VENV_PATH, PYENV_ROOT and PATH are inherited from the
# base image.

# Copy the whole project; .dockerignore keeps build artifacts and caches
# out so a stale host CMakeCache.txt cannot poison the in-image build.
COPY ./ ${BUILD_CONTEXT}

# Build the C++ transpiler extension (high_performance.so, which provides
# QuafuVerifier / VerifyParams) against the venv interpreter, then install
# the wy_qcos package (non-editable) and overlay the freshly built .so +
# .pyi stubs into the installed package dir so the venv picks them up.
RUN set -e && \
    export Python_EXECUTABLE=${VENV_PATH}/bin/python && \
    if [ -n "${PIP_MIRROR}" ]; then \
        ${VENV_PATH}/bin/pip config set global.index-url "${PIP_MIRROR}"; \
    fi && \
    bash ${BUILD_CONTEXT}/src_cpp/transpiler_cpp/build-cpp.sh release rebuild && \
    ${VENV_PATH}/bin/pip install --no-cache-dir ${BUILD_CONTEXT} && \
    VENV_TRANSPILER_DIR=$(${VENV_PATH}/bin/python -c \
      "import wy_qcos.transpiler, os; print(os.path.dirname(wy_qcos.transpiler.__file__))") && \
    cp -f ${BUILD_CONTEXT}/src/wy_qcos/transpiler/*.so ${VENV_TRANSPILER_DIR}/ && \
    (cp -f ${BUILD_CONTEXT}/src/wy_qcos/transpiler/*.pyi ${VENV_TRANSPILER_DIR}/ 2>/dev/null || true) && \
    ${VENV_PATH}/bin/python -c \
      "from wy_qcos.transpiler.high_performance import QuafuVerifier, VerifyParams; print('QuafuVerifier OK')"

# Copy the compiler entrypoint.
COPY bin/qcos-compiler.py /usr/bin/qcos-compiler
RUN chmod +x /usr/bin/qcos-compiler

# ---- least-privilege runtime user ---------------------------------------
# Pin a dedicated non-root account (uid/gid 10001, above the system range so
# it cannot collide with host system users) and run the service as it. The
# same pinned identity is used in build-scripts/qcos/Dockerfile and
# build-scripts/cli/Dockerfile so the qcos user maps to the same uid:gid
# across all three images and shared volumes stay accessible. Those images
# keep USER root (their entrypoints need it); only the compiler drops
# privileges, since it just reads the venv + entrypoint and binds a
# non-privileged port (8080). A writable HOME/WORKDIR is provided so
# libraries that cache under ~ do not fail at runtime.
RUN groupadd -r -g 10001 qcos && \
    useradd  -r -u 10001 -g qcos -m -d /home/qcos -s /sbin/nologin qcos && \
    chown -R qcos:qcos /etc/qcos /var/log/qcos /var/run/qcos /home/qcos

# Numeric form stays correct even if /etc/passwd is not resolvable at runtime.
USER 10001:10001
ENV HOME=/home/qcos
WORKDIR /home/qcos

EXPOSE 8080

# Run the compiler cloud service with the venv interpreter.
CMD ["/opt/qcos-compiler-venv/bin/python", "/usr/bin/qcos-compiler", "--host", "0.0.0.0", "--port", "8080"]
