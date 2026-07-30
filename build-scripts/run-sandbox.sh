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

name="qcos-sandbox"
file_name="docker-compose-sandbox.yaml"
file_path="${build_scripts_dir}/${file_name}"

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Run sandbox container"
    echo ""
    echo "  -n, --name      Container name. default: ${name}"
    echo "  -f, --file-path Docker compose file name. default: ${file_path}"
    echo "  -h, --help      Print this usage message"
    echo ""
}

opts=$(getopt -o n:f:h --long name:,file_path,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

while true; do
  case "$1" in
    -h | --help ) usage ; exit 0; shift ;;
    -n | --name ) name="$2";   shift 2;;
    -f | --file-path ) file_path="$2";   shift 2;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

echo "Creating QCOS sandbox dockers (${name}) ..."
cd ${build_scripts_dir}
docker_compose_file=${file_path}
new_docker_compose_file="${build_scripts_dir}/.docker-compose-sandbox.yaml"
create_temp_docker_compose_file ${docker_compose_file} "${new_docker_compose_file}"

export QCOS_SANDBOX_CONTAINER_NAME=${name}
docker-compose -f ${new_docker_compose_file} down
docker-compose -f ${new_docker_compose_file} up -d
echo "Run QCOS sandbox bash: docker exec -it ${name} bash"
