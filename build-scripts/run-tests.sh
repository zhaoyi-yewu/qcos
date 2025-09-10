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
    echo "  -p, --pep8            Run PEP8 coding style check"
    echo "  -u, --unit-test       Run unit tests"
    echo "  -c, --coverage        Run unit tests and generate code coverage report"
    echo "  -s, --system-test     Run system tests"
    echo "  -h, --help            Print this usage message"
    echo ""
}

opts=$(getopt -o fpucsh --long pep8,unit-test,coverage,system-test,help -- "$@")
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
system_test=false
pep8_success=-1
unit_test_success=-1
coverage_success=-1
system_test_success=-1
wrapper="sh -c"

while true; do
  case "$1" in
    -h | --help )        usage ; exit 0; shift ;;
    -p | --pep8 )        pep8=true;      shift ;;
    -u | --unit-test )   unit_test=true; shift ;;
    -c | --coverage )    coverage=true;  shift ;;
    -s | --system-test ) system_test=true;  shift ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check user input options
if [ "$pep8" = false ] && [ "$unit_test" = false ] && [ "$coverage" = false ] && [ "$system_test" = false ]; then
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

function run_unit_tests {
    echo "[Running unit tests]"
    ${wrapper} "python3 -m pytest --disable-warnings -vv ${TOP_DIR}/qcos/tests/unit_tests"
    unit_test_success=$?
    echo
}

function run_coverage {
    min_fail_rate=80
    echo "[Running code coverage test]"
    ${wrapper} "rm -rf ./.coverage ./coverage.xml"
    ${wrapper} "coverage3 run --omit '*/site-packages/*' -m pytest --disable-warnings -vv ${TOP_DIR}/qcos/tests/unit_tests"
    ${wrapper} "coverage3 xml -o coverage.xml"
    ${wrapper} "coverage3 report --include='${TOP_DIR}/qcos/*' --omit='${TOP_DIR}/qcos/tests/*' -m --fail-under=$min_fail_rate"
    coverage_success=$?
    ${wrapper} "coverage3 html --title='QCOS Coverage Report' --include='${TOP_DIR}/qcos/*' --omit='${TOP_DIR}/qcos/tests/*' -d coverage_html"
    echo
}

function run_system_tests {
    echo "[Running system tests]"
    ${wrapper} "python3 -m pytest --disable-warnings -vv ${TOP_DIR}/qcos/tests/system_tests"
    system_test_success=$?
    echo
}

function run_tests {
    if [ "$pep8" = true ]; then
        run_pep8
    fi
    if [ "$unit_test" = true ]; then
        run_unit_tests
    fi
    if [ "$coverage" = true ]; then
        run_coverage
    fi
    if [ "$system_test" = true ]; then
        run_system_tests
    fi
}

function print_report {
    failure=false
    pep8_result="N/A"
    unit_test_result="N/A"
    coverage_result="N/A"
    system_test_result="N/A"

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
    if [ $system_test_success -eq 0 ]; then
      system_test_result="SUCCESS"
    elif [ $system_test_success -gt 0 ]; then
      system_test_result="FAILURE"
      failure=true
    fi

    echo "[QCOS Test Results]"
    echo "Flask8 Python PEP8 coding style check: [$pep8_result]"
    echo "Unit tests check                     : [$unit_test_result]"
    echo "Code coverage check                  : [$coverage_result]"
    echo "System tests check                   : [$system_test_result]"

    if [ $failure = true ]; then
        exit 1
    fi
}

run_tests
print_report
