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

FROM jenkins/jenkins:lts-jdk17

# 1. Change repository source and install basic tools (retaining previous compatibility fixes)
# Only install essential tools for building and testing: Python3, pip, rsync, etc.
RUN (sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list) \
    && apt-get update \
    && apt-get install -y python3 python3-pip python3-venv rsync gcc libffi-dev curl

# 2. Install Docker client
RUN apt-get install -y docker.io docker-compose \
    && rm -rf /var/lib/apt/lists/*

# 3.Switch to root user to install dependencies
USER root

# 4. Create non-root user and switch back for runtime
RUN groupadd -r qcos && useradd -r -g qcos qcos
USER qcos