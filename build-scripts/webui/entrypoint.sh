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

# set variables
export PS1="(${QCOS_WEBUI_CONTAINER_NAME})[$(pwd)]$ "

WEBUI_LISTEN_IP=${WEBUI_LISTEN_IP:-0.0.0.0}
WEBUI_LISTEN_PORT=${WEBUI_LISTEN_PORT:-18401}
WEBUI_ACCESS_LOG=${WEBUI_ACCESS_LOG:-/var/log/qcos/qcos-webui.log}
WEBUI_ERROR_LOG=${WEBUI_ERROR_LOG:-/var/log/qcos/qcos-webui-error.log}

# create dirs
mkdir -p /etc/qcos/
mkdir -p /var/log/qcos/

# run QCOS
if [ "${DEV,,}" = "true" ]; then
  # run in development env
  cd /root/qcos-webui
  npm run dev | tee /var/log/qcos/qcos-webui.log
  sleep infinity
else
  cd /app
  # run in production env
  cp -rf /root/nginx.conf /etc/nginx/.nginx.conf
  if [ -n "${WEBUI_LISTEN_IP}" ]; then
    sed -i "s/WEBUI_LISTEN_IP/${WEBUI_LISTEN_IP}/g" /etc/nginx/.nginx.conf
  fi
  if [ -n "${WEBUI_LISTEN_PORT}" ]; then
    sed -i "s/WEBUI_LISTEN_PORT/${WEBUI_LISTEN_PORT}/g" /etc/nginx/.nginx.conf
  fi
  if [ -n "${WEBUI_ACCESS_LOG}" ]; then
    sed -i "s|WEBUI_ACCESS_LOG|${WEBUI_ACCESS_LOG}|g" /etc/nginx/.nginx.conf
  fi
  if [ -n "${WEBUI_ERROR_LOG}" ]; then
    sed -i "s|WEBUI_ERROR_LOG|${WEBUI_ERROR_LOG}|g" /etc/nginx/.nginx.conf
  fi
  cp -rf /etc/nginx/.nginx.conf /etc/nginx/nginx.conf
  nginx -g "daemon off;"
fi
