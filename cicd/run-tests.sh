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
# run tests

set -u

BASE_DIR=$(dirname "$0")
BASE_DIR=$(readlink -f ${BASE_DIR})
TOP_DIR=$(readlink -f ${BASE_DIR}/..)

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Run QCOS's test suite(s)"
    echo ""
    echo "  -p, --pep8                             Run PEP8 coding style check"
    echo "  -u, --unit-test [all/TEST_CASE]        Run unit tests (QCOS)"
    echo "  -c, --coverage  [all/TEST_CASE]        Run unit tests and generate code coverage report (QCOS)"
    echo "  -j, --client-unit-test [all/TEST_CASE] Run unit tests (QCOS CLIENT)"
    echo "  -e, --client-coverage [all/TEST_CASE]  Run unit tests and generate code coverage report (QCOS CLIENT)"
    echo "  -s, --system-test [all/TEST_CASE]      Run system tests"
    echo "  -h, --help                             Print this usage message"
    echo ""
}

opts=$(getopt -o pu:c:j:e:s:h --long pep8,unit-test:,coverage:,client-unit-test:,client-coverage:,system-test:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

LANG=en_US.UTF-8
LANGUAGE=en_US:en
LC_ALL=C

pep8=false
unit_test=""
coverage=""
client_unit_test=""
client_coverage=""
system_test=""
pep8_success=-1
unit_test_success=-1
coverage_success=-1
client_unit_test_success=-1
client_coverage_success=-1
system_test_success=-1
wrapper="sh -c"
pytest_ini="${TOP_DIR}/src/wy_qcos/tests/pytest.ini"

while true; do
  case "$1" in
    -h | --help )        usage ; exit 0; shift ;;
    -p | --pep8 )        pep8=true;      shift ;;
    -u | --unit-test )   unit_test="$2"; shift 2;;
    -c | --coverage )    coverage="$2";  shift 2;;
    -j | --client-unit-test ) client_unit_test="$2"; shift 2;;
    -e | --client-coverage )  client_coverage="$2";  shift 2;;
    -s | --system-test ) system_test="$2"; shift 2;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check user input options
if [ "$pep8" = false ] && [ -e "$unit_test" ] && [ -e "$coverage" ] \
  && [ -e "$client_unit_test" ] && [ -e "$client_coverage" ] \
  && [ -e "$system_test" ]; then
  echo -e "Error: Invalid arguments\n"
  usage
  exit 1
fi


function run_pep8 {
  echo "[Running pep8 check]"
  ${wrapper} "${TOP_DIR}/cicd/code-formatter.sh"
  pep8_success=$?
  echo
}

function run_unit_tests {
  echo "[Running unit tests (QCOS)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos/tests/unit_tests"
  local pytest_mark=""
  local junit_report="--junitxml=${TOP_DIR}/cicd/report.xml"
  if [ "${args,,}" = "smoke" ]; then
    pytest_mark="-m 'smoke'"
  elif [ "${args,,}" = "slow" ]; then
    pytest_mark="-m 'slow'"
  elif [ "${args,,}" = "default" ]; then
    pytest_mark="-m 'not smoke and not slow'"
  elif [ "${args,,}" = "all" ]; then
    pytest_mark=""
  else
    test_case=${args}
  fi
  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  unit_test_success=$?
  echo
}

function run_client_unit_tests {
  echo "[Running unit tests (QCOS CLIENT)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos_client/tests/unit_tests"
  local pytest_mark=""
  local junit_report="--junitxml=${TOP_DIR}/cicd/report.xml"
  if [ "${args,,}" = "smoke" ]; then
    pytest_mark="-m 'smoke'"
  elif [ "${args,,}" = "slow" ]; then
    pytest_mark="-m 'slow'"
  elif [ "${args,,}" = "default" ]; then
    pytest_mark="-m 'not smoke and not slow'"
  elif [ "${args,,}" = "all" ]; then
    pytest_mark=""
  else
    test_case=${args}
  fi
  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  client_unit_test_success=$?
  echo
}

function run_coverage {
  min_fail_rate=80
  echo "[Running code coverage test (QCOS)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos/tests/unit_tests"
  if [ "${args,,}" != "all" ]; then
    test_case=${args}
  fi
  ${wrapper} "rm -rf ${BASE_DIR}/coverage ${BASE_DIR}/coverage.xml"
  ${wrapper} "coverage3 run --data-file=${BASE_DIR}/.coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${test_case}"
  ${wrapper} "coverage3 xml --data-file=${BASE_DIR}/.coverage -o ${BASE_DIR}/coverage.xml"
  ${wrapper} "coverage3 report --data-file=${BASE_DIR}/.coverage --include='${TOP_DIR}/src/wy_qcos/*' --omit='${TOP_DIR}/src/wy_qcos/tests/*' -m --fail-under=$min_fail_rate"
  coverage_success=$?
  ${wrapper} "coverage3 html --data-file=${BASE_DIR}/.coverage --title='QCOS Coverage Report' --include='${TOP_DIR}/src/wy_qcos/*' --omit='${TOP_DIR}/src/wy_qcos/tests/*' -d ${BASE_DIR}/coverage_html"
  echo
}

function run_client_coverage {
  min_fail_rate=80
  echo "[Running code coverage test (QCOS CLIENT)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos_client/tests/unit_tests"
  if [ "${args,,}" != "all" ]; then
    test_case=${args}
  fi
  ${wrapper} "rm -rf ${BASE_DIR}/coverage ${BASE_DIR}/client-coverage.xml"
  ${wrapper} "coverage3 run --data-file=${BASE_DIR}/.client_coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${test_case}"
  ${wrapper} "coverage3 xml --data-file=${BASE_DIR}/.client_coverage -o ${BASE_DIR}/client-coverage.xml"
  ${wrapper} "coverage3 report --data-file=${BASE_DIR}/.client_coverage --include='${TOP_DIR}/src/wy_qcos_client/*' --omit='${TOP_DIR}/src/wy_qcos_client/tests/*' -m --fail-under=$min_fail_rate"
  client_coverage_success=$?
  ${wrapper} "coverage3 html --data-file=${BASE_DIR}/.client_coverage --title='QCOS Client Coverage Report' --include='${TOP_DIR}/src/wy_qcos_client/*' --omit='${TOP_DIR}/src/wy_qcos_client/tests/*' -d ${BASE_DIR}/client_coverage_html"
  echo
}

function run_system_tests {
  echo "[Running system tests]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos/tests/system_tests"
  local pytest_mark=""
  if [ "${args,,}" = "smoke" ]; then
    pytest_mark="-m 'smoke'"
  elif [ "${args,,}" = "slow" ]; then
    pytest_mark="-m 'slow'"
  elif [ "${args,,}" = "default" ]; then
    pytest_mark="-m 'not smoke and not slow'"
  elif [ "${args,,}" = "all" ]; then
    pytest_mark=""
  else
    test_case=${args}
  fi
  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
  system_test_success=$?
  echo
}

function run_tests {
  if [ "$pep8" = true ]; then
    run_pep8
  fi
  if [ -n "$unit_test" ]; then
    run_unit_tests $unit_test
  fi
  if [ -n "$coverage" ]; then
    run_coverage $coverage
  fi
  if [ -n "$client_unit_test" ]; then
    run_client_unit_tests $client_unit_test
  fi
  if [ -n "$client_coverage" ]; then
    run_client_coverage $client_coverage
  fi
  if [ -n "$system_test" ]; then
    run_system_tests $system_test
  fi
}

function print_report {
  failure=false
  pep8_result="N/A"
  unit_test_result="N/A"
  coverage_result="N/A"
  client_unit_test_result="N/A"
  client_coverage_result="N/A"
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
  if [ $client_unit_test_success -eq 0 ]; then
    client_unit_test_result="SUCCESS"
  elif [ $client_unit_test_success -gt 0 ]; then
    client_unit_test_result="FAILURE"
    failure=true
  fi
  if [ $client_coverage_success -eq 0 ]; then
    client_coverage_result="SUCCESS"
  elif [ $client_coverage_success -gt 0 ]; then
    client_coverage_result="FAILURE"
    failure=true
  fi
  if [ $system_test_success -eq 0 ]; then
    system_test_result="SUCCESS"
  elif [ $system_test_success -gt 0 ]; then
    system_test_result="FAILURE"
    failure=true
  fi

  echo "[QCOS Test Results]"
  echo "Python PEP8 coding style check    : [$pep8_result]"
  echo "Unit tests check (QCOS)           : [$unit_test_result]"
  echo "Code coverage check (QCOS)        : [$coverage_result]"
  echo "Unit tests check (QCOS CLIENT)    : [$client_unit_test_result]"
  echo "Code coverage check  (QCOS CLIENT): [$client_coverage_result]"
  echo "System tests check                : [$system_test_result]"

  if [ $failure = true ]; then
    exit 1
  fi
}

# active venv if default venv exists
if [ -f "/var/lib/qcos/venv/default/bin/activate" ]; then
  source /var/lib/qcos/venv/default/bin/activate
fi
run_tests
print_report
