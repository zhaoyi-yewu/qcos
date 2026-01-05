#!/bin/bash
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
# QCOS documentations:  sphinix docs, api docs
# build docs: ./build-docs.sh

set -e

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)
DOCS_DIR=${TOP_DIR}/docs

# 1. create sphinx docs
SPHINX_DOCS_DIR=${DOCS_DIR}/sphinx
cd ${SPHINX_DOCS_DIR}
# create sphinx dist dir
make clean
rm -rf ./dist
rm -rf ./source/api
mkdir -p ./dist
mkdir ./source/api
# create sphinx api docs
sphinx-apidoc -H "QCOS API" -f -o ./source/api ${TOP_DIR}/qcos
# create sphinx docs
make html
# make singlehtml
make latexpdf

# copy pdf
mkdir -p ./dist/pdf
cp -rf ./dist/latex/qcos.pdf ./dist/pdf/qcos-full-docs.pdf

# 2. create openapi docs
# create openapi dist dir
OPENAPI_DOCS_DIR=${DOCS_DIR}/openapi-docs
cd ${OPENAPI_DOCS_DIR}
rm -rf ./dist
mkdir -p ./dist
# unpack js
tar xzvf ${OPENAPI_DOCS_DIR}/js.tar.gz -C ${OPENAPI_DOCS_DIR}/dist
# make openapi docs
./make-openapi-docs.py

# print results
echo -e "\n======DOCS OUTPUT======"
echo "Sphinx docs (html) : ${SPHINX_DOCS_DIR}/dist/html/index.html"
echo "Sphinx docs (latex): ${SPHINX_DOCS_DIR}/dist/latex/"
echo "Sphinx docs (pdf)  : ${SPHINX_DOCS_DIR}/dist/pdf/qcos-full-docs.pdf"
echo "OpenAPI docs (html): ${OPENAPI_DOCS_DIR}/dist/qcos-api-docs.html"

