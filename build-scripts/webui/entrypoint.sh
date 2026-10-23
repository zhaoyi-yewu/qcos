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

# create dirs
mkdir -p /etc/qcos/
mkdir -p /var/log/qcos/
# dir holding the generated nginx endpoints.conf. Kept outside
# /etc/nginx/default.d/ so the default.d/*.conf wildcard include in
# nginx.conf does not load it a second time (which would cause nginx
# to fail with "duplicate location" errors).
mkdir -p /etc/nginx/qcos/

# parse qcos-webui.toml and generate runtime artifacts (env, webui-config.json,
# nginx endpoints.conf); the script is copied into the image at build time
python3 /usr/local/bin/parse-webui-toml.py \
  --toml /etc/qcos/qcos-webui.toml \
  --env-out /tmp/webui.env \
  --json-out /apps/webui-config.json \
  --nginx-snippet-out /etc/nginx/qcos/endpoints.conf

source /tmp/webui.env

WEBUI_LISTEN_IP=${WEBUI_LISTEN_IP:-$LISTEN_IP}
WEBUI_LISTEN_PORT=${WEBUI_LISTEN_PORT:-$LISTEN_PORT}
WEBUI_ACCESS_LOG=${WEBUI_ACCESS_LOG:-/var/log/qcos/qcos-webui.log}
WEBUI_ERROR_LOG=${WEBUI_ERROR_LOG:-/var/log/qcos/qcos-webui-error.log}

# run QCOS
if [ "${DEV,,}" = "true" ]; then
  # run in development env
  cd /root/qcos-webui
  # Pick the vite entry script. Prefer the user-installed copy under
  # ./node_modules (e.g. after bind-mounting a source tree that contains a
  # full `npm install`); fall back to the image-bundled copy at
  # /root/node_modules which the Dockerfile installed during build.
  # We must invoke the absolute path of vite.js directly instead of
  # `npm run dev`: npm resolves ./node_modules/.bin/vite which internally
  # uses an absolute path to ./node_modules/vite/bin/vite.js, and that
  # absolute path is broken when the local node_modules exists but does
  # not actually contain the vite package. NODE_PATH does not help here
  # because Node treats the script path itself as a literal file path,
  # not a module name to resolve.
  if [ -f ./node_modules/vite/bin/vite.js ]; then
    VITE_BIN=./node_modules/vite/bin/vite.js
  else
    VITE_BIN=/root/node_modules/vite/bin/vite.js
  fi
  node "${VITE_BIN}" | tee /var/log/qcos/qcos-webui.log
  sleep infinity
else
  cd /apps
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
