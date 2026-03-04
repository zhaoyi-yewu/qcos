#!/bin/sh
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

cwd=$(dirname "${BASH_SOURCE[0]}")
abs_cwd=$(realpath ${cwd})
build_scripts_dir=${abs_cwd}

source ${build_scripts_dir}/setup-env.sh

export QCOS_LOCAL_SRC_DIR="${top_dir}"

echo "Creating QCOS dockers ..."

# copy config files
mkdir -p /etc/qcos/prefect
mkdir -p /var/qcos/db
mkdir -p /var/qcos/db/postgresql
rm -rf /etc/qcos/prefect/profiles.toml
mkdir -p /etc/qcos/postgres
cp -r ${QCOS_LOCAL_SRC_DIR}/build-scripts/postgres /etc/qcos/

cd ${build_scripts_dir}
docker-compose -f docker-compose-postgres.yaml down
if [ "${DB_BACKEND,,}" = "postgres" ]; then
  docker-compose -f docker-compose-postgres.yaml up -d
fi

if [ "${DEV,,}" = "false" ]; then
  docker-compose -f docker-compose.yaml down
  docker-compose -f docker-compose.yaml up -d
  echo "Run QCOS bash: docker exec -it qcos bash"
else
  docker-compose -f docker-compose-dev.yaml down
  docker-compose -f docker-compose-dev.yaml up -d
  echo "Run QCOS bash: docker exec -it qcos-dev bash"
fi
