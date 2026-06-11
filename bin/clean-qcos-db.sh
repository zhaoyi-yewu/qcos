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

function usage {
  echo "Usage: $0 [OPTION] ..."
  echo "Clean qcos database"
  echo ""
  echo "  -f, --force    Force to clean"
  echo "  -h, --help     Print this usage message"
  echo ""
}

opts=$(getopt -o fh --long force,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

force=false

while true; do
  case "$1" in
    -h | --help )  usage ; exit 0; shift ;;
    -f | --force ) force=true;   shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

if [ "${force}" = false ]; then
    echo "WARNING: This will delete all database files in /var/qcos/db/ and /var/qcos/storage/"
    echo "Type 'YES' to confirm deletion:"
    read confirmation

    if [ "$confirmation" != "YES" ]; then
        echo "Operation cancelled."
        exit 1
    fi
fi

echo "Deleting data..."
rm -rf /var/qcos/db/*
rm -rf /var/qcos/storage/*
rm -rf /var/qcos/db/postgresql/
echo "Data cleared successfully."
