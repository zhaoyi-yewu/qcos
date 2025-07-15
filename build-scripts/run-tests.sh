#!/bin/bash
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
# run tests

set -u

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Run QCOS's test suite(s)"
    echo ""
    echo "  -p, --pep8                  Run PEP8 coding style check"
    echo "  -u, --unit-test             Run unit test"
    echo "  -c, --coverage              Run unit test and generate code coverage report"
    echo "  -h, --help                  Print this usage message"
    echo ""
}

opts=$(getopt -o fpuch --long pep8,unit-test,coverage,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

LANG=en_US.UTF-8
LANGUAGE=en_US:en
LC_ALL=C

pep8=false
unit_test=false
coverage=false
pep8_success=-1
unit_test_success=-1
coverage_success=-1
wrapper="sh -c"

while true; do
  case "$1" in
    -h | --help )      usage ; exit 0; shift ;;
    -p | --pep8 )      pep8=true;      shift ;;
    -u | --unit-test ) unit_test=true; shift ;;
    -c | --coverage )  coverage=true;  shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check user input options
if [ "$pep8" = false ] && [ "$unit_test" = false ] && [ "$coverage" = false ]; then
    echo -e "Error: Invalid arguments\n"
    usage
    exit 1
fi


function run_pep8 {
    echo "[Running flake8]"
    ${wrapper} "flake8"
    pep8_success=$?
    echo
}

function run_unit_test {
    echo "[Running unit test]"
    ${wrapper} "python3 -m pytest --disable-warnings -vv ${TOP_DIR}/tests/"
    unit_test_success=$?
    echo
}

function run_coverage {
    min_fail_rate=80
    echo "[Running code coverage test]"
    ${wrapper} "rm -rf ./.coverage ./coverage.xml"
    ${wrapper} "coverage3 run --omit '*/site-packages/*' -m pytest --disable-warnings -vv ${TOP_DIR}/tests/"
    ${wrapper} "coverage3 xml -o coverage.xml"
    ${wrapper} "coverage3 report --include='${TOP_DIR}/qcos/*' -m --fail-under=$min_fail_rate"
    coverage_success=$?
    ${wrapper} "coverage3 html --title='QCOS Coverage Report' --include='qcos/*' -d coverage_html"
    echo
}

function run_tests {
    if [ "$pep8" = true ]; then
        run_pep8
    fi
    if [ "$unit_test" = true ]; then
        run_unit_test
    fi
    if [ "$coverage" = true ]; then
        run_coverage
    fi
}

function print_report {
    failure=false
    pep8_result="N/A"
    unit_test_result="N/A"
    coverage_result="N/A"

    if [ $pep8_success -eq 0 ]; then
      pep8_result="SUCCESS"
    elif [ $pep8_success -gt 0 ]; then
      pep8_result="FAILURE"
      failure=true
    fi
    if [ $unit_test_success -eq 0 ]; then
      unit_test_result="SUCCESS"
    elif [ $unit_test_success -gt 0 ]; then
      unit_test_result="FAILURE"
      failure=true
    fi
    if [ $coverage_success -eq 0 ]; then
      coverage_result="SUCCESS"
    elif [ $coverage_success -gt 0 ]; then
      coverage_result="FAILURE"
      failure=true
    fi

    echo "[QCOS Test Results]"
    echo "Flask8 Python PEP8 coding style check: [$pep8_result]"
    echo "Unit test check                      : [$unit_test_result]"
    echo "Code coverage check                  : [$coverage_result]"

    if [ $failure = true ]; then
        exit 1
    fi
}

run_tests
print_report
