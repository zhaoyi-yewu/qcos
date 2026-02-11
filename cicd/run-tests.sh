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
    echo "  -p, --pep8                        Run PEP8 coding style check"
    echo "  -u, --unit-test TEST_CASES        Run unit tests (QCOS)"
    echo "  -c, --coverage  TEST_CASES        Run unit tests and generate code coverage report (QCOS)"
    echo "  -j, --client-unit-test TEST_CASES Run unit tests (QCOS CLIENT)"
    echo "  -e, --client-coverage TEST_CASES  Run unit tests and generate code coverage report (QCOS CLIENT)"
    echo "  -s, --system-test TEST_CASES      Run system tests"
    echo "  -m, --pytest-mark MARK            Extra pytest mark"
    echo "  -h, --help                        Print this usage message"
    echo ""
    echo "  TEST_CASES: [all/default/smoke/slow/TEST_CASE]"
    echo ""
}

opts=$(getopt -o pu:c:j:e:s:m:h --long pep8,unit-test:,coverage:,client-unit-test:,client-coverage:,system-test:pytest-mark:,help -- "$@")
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
pytest_mark=""
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
    -m | --pytest-mark ) pytest_mark="$2"; shift 2;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check user input options
if [ "$pep8" = false ] && [ -z "$unit_test" ] && [ -z "$coverage" ] \
  && [ -z "$client_unit_test" ] && [ -z "$client_coverage" ] \
  && [ -z "$system_test" ]; then
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

function get_pytest_mark() {
  local arg_test_case="$1"
  shift
  local arg_pytest_mark="$*"
  local pytest_mark=""
  local extra_pytest_mark=""

  if [ -n "$arg_pytest_mark" ]; then
    extra_pytest_mark="and ($arg_pytest_mark)"
  fi

  local lower_args="${arg_test_case,,}"
  if [ "$lower_args" = "smoke" ]; then
    pytest_mark="-m 'smoke ${extra_pytest_mark}'"
  elif [ "$lower_args" = "slow" ]; then
    pytest_mark="-m 'slow ${extra_pytest_mark}'"
  elif [ "$lower_args" = "driver" ]; then
    pytest_mark="-m 'driver ${extra_pytest_mark}'"
  elif [ "$lower_args" = "default" ]; then
    pytest_mark="-m 'not smoke and not slow ${extra_pytest_mark}'"
  elif [ "$lower_args" = "all" ]; then
    if [ -n "$arg_pytest_mark" ]; then
      pytest_mark="-m '$arg_pytest_mark'"
    else
      pytest_mark=""
    fi
  else
    pytest_mark="skip"
  fi

  echo ${pytest_mark}
}

function run_unit_tests {
  echo "[Running unit tests (QCOS)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos/tests/unit_tests"
  local junit_report="--junitxml=${TOP_DIR}/cicd/report.xml"
  local pytest_mark=$(get_pytest_mark ${args})
  if [ "$pytest_mark" = "skip" ]; then
    test_case=$1
    pytest_mark=""
  fi

  echo "[pytest command]"
  echo "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  echo

  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  unit_test_success=$?
  echo
}

function run_client_unit_tests {
  echo "[Running unit tests (QCOS CLIENT)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos_client/tests/unit_tests"
  local junit_report="--junitxml=${TOP_DIR}/cicd/report.xml"
  local pytest_mark=$(get_pytest_mark ${args})
  if [ "$pytest_mark" = "skip" ]; then
    test_case=$1
    pytest_mark=""
  fi

  echo "[pytest command]"
  echo "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  echo

  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${junit_report} ${test_case}"
  client_unit_test_success=$?
  echo
}

function run_coverage {
  min_fail_rate=80
  echo "[Running code coverage test (QCOS)]"
  args=$*
  test_case="${TOP_DIR}/src/wy_qcos/tests/unit_tests"
  local pytest_mark=$(get_pytest_mark ${args})
  if [ "$pytest_mark" = "skip" ]; then
    test_case=$1
    pytest_mark=""
  fi

  echo "[pytest command]"
  echo "coverage3 run --data-file=${BASE_DIR}/.coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
  echo

  ${wrapper} "rm -rf ${BASE_DIR}/coverage ${BASE_DIR}/coverage.xml"
  ${wrapper} "coverage3 run --data-file=${BASE_DIR}/.coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
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
  local pytest_mark=$(get_pytest_mark ${args})
  if [ "$pytest_mark" = "skip" ]; then
    test_case=$1
    pytest_mark=""
  fi

  echo "[pytest command]"
  echo "coverage3 run --data-file=${BASE_DIR}/.client_coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
  echo

  ${wrapper} "rm -rf ${BASE_DIR}/coverage ${BASE_DIR}/client-coverage.xml"
  ${wrapper} "coverage3 run --data-file=${BASE_DIR}/.client_coverage --omit='*/site-packages/*' -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
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
  local pytest_mark=$(get_pytest_mark ${args})
  if [ "$pytest_mark" = "skip" ]; then
    test_case=$1
    pytest_mark=""
  fi

  echo "[pytest command]"
  echo "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
  echo

  ${wrapper} "python3 -m pytest -c ${pytest_ini} ${pytest_mark} ${test_case}"
  system_test_success=$?
  echo
}

function run_tests {
  if [ "$pep8" = true ]; then
    run_pep8
  fi
  if [ -n "$unit_test" ]; then
    run_unit_tests $unit_test $pytest_mark
  fi
  if [ -n "$coverage" ]; then
    run_coverage $coverage $pytest_mark
  fi
  if [ -n "$client_unit_test" ]; then
    run_client_unit_tests $client_unit_test $pytest_mark
  fi
  if [ -n "$client_coverage" ]; then
    run_client_coverage $client_coverage $pytest_mark
  fi
  if [ -n "$system_test" ]; then
    run_system_tests $system_test $pytest_mark
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
