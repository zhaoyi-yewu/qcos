#!/bin/bash
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

set -e

cwd=$(dirname "$0")
abs_cwd=$(realpath ${cwd})
build_scripts_dir=${abs_cwd}

source ${build_scripts_dir}/setup-env.sh
export QCOS_LOCAL_SRC_DIR="${top_dir}"

cd ${build_scripts_dir}
# start AI embedding service
docker_compose_file="./docker-compose-ai.yaml"
new_docker_compose_file="./.docker-compose-ai.yaml"
create_temp_docker_compose_file "${docker_compose_file}" "${new_docker_compose_file}"

docker-compose -f ${new_docker_compose_file} down
docker-compose -f ${new_docker_compose_file} up -d
