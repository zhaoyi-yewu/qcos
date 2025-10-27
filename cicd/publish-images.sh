#!/bin/sh
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
# Publish docker images to registry
set -e

# set configs
docker_registry="cicdcsy.harbor.cmss.com:18080/wuyue-platform/qcos/"
source_qcos_image=qcos:2025-06-01
source_qcos_cli_image=qcos-cli:2025-06-01

target_qcos_image=${docker_registry}${source_qcos_image}
target_qcos_cli_image=${docker_registry}${source_qcos_cli_image}

# tag docker image
docker rmi -f ${target_qcos_image}
docker rmi -f ${target_qcos_cli_image}
docker tag ${source_qcos_image} ${target_qcos_image}
docker tag ${source_qcos_cli_image} ${target_qcos_cli_image}

# push image to registry
docker push ${target_qcos_image}
docker push ${target_qcos_cli_image}
