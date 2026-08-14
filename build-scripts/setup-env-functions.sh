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

# create temp docker-compose file and set readonly: false
create_temp_docker_compose_file() {
  local src_file="$1"
  local dst_file="$2"
  local new_name=".${src_file##*/}"
  local new_path="${src_file%/*}/${new_name}"
  cp -f ${src_file} ${dst_file}
  if grep -E 'read_only:\s*([Tt][Rr][Uu][Ee])' ${dst_file} > /dev/null; then
    sed -i 's/read_only:\s*[Tt][Rr][Uu][Ee]/read_only: false/' ${dst_file}
  fi
}
