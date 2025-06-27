#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS,
#     WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json
import logging
import requests
import time

from jsonrpcclient import Ok, parse, request

from qcos.common import errors
from qcos.common.config import Config
from qcos.common.constant import Constant
from qcos.common.library import Library

logger = logging.getLogger(__name__)


class Client:
    """
    QCOS client api
    """
    default_headers = {"Content-Type": "application/json"}
    verbose = False

    def __init__(self,
                 api_listen_ip=Config.API_SERVER_LISTEN_IP,
                 api_port=Config.API_SERVER_PORT):
        api_version = "v1"
        endpoint_url = f"http://{api_listen_ip}:{api_port}/{api_version}"
        self.job_url = f"{endpoint_url}/job"

    @staticmethod
    def call_http_api(
            url, *,
            data=None, params=None, func_name=None,
            headers=default_headers, auth=None, verify_ssl=False,
            retry=1, timeout=2, success_http_code=[200]):
        """
        Call http api

        :param url: api url
        :param data: data for http body
        :param params: params for http url
        :param func_name: function name
        :param headers: http headers
        :param auth: http auth
        :param verify_ssl: if verify ssl certificate
        :param retry: times to retry if failed
        :param timeout: timeout in seconds
        :param success_http_code: success http status
        """
        if Client.verbose:
            print(f"Request [{func_name}]: {url}, HEADER: {headers}, "
                  f"PARAMS: {params}, DATA: {data}")
        r = None
        for i in range(1, retry + 1):
            if headers:
                r = requests.post(
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    auth=auth,
                    verify=verify_ssl,
                    timeout=2
                )
            else:
                r = requests.post(
                    url,
                    params=params,
                    data=data,
                    auth=auth,
                    verify=verify_ssl,
                    timeout=2)
            if r.status_code in success_http_code:
                break
            if retry > 1:
                time.sleep(timeout)
        return r.status_code, r.reason, r.text, r

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        """
        Print API response

        :param status_code: status code
        :param reason: reason
        :param text: text
        :param result: result text
        """
        if Client.verbose:
            print(f"Response: status_code: {status_code}, reason: {reason}, "
                  f"text: {text}, result: {result}")

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        """
        Call json-rpc

        :param url: json-rpc url
        :param method_name: json-rpc method
        :param data: json-rpc data
        :param params: json-rpc params
        """
        jsonrpc_data = request(method_name, params={"body": data})
        jsonrpc_data_json = json.dumps(jsonrpc_data)
        status_code, reason, text, result = Client.call_http_api(
            url, data=jsonrpc_data_json, params=params,
            func_name=method_name)
        Client.print_api_response(status_code, reason, text, result)
        return status_code, reason, text, result

    @staticmethod
    def parse_jsonrpc_response(jsonrpc_response):
        """
        Parse json-rpc response

        :param jsonrpc_response: json-rpc response
        """
        parsed = parse(jsonrpc_response)
        if isinstance(parsed, Ok):
            return True, parsed
        return False, parsed

    @staticmethod
    def handle_invalid_arguments(results):
        """
        Handle invalid arguments

        :param results: results
        """
        success, err_msg = results
        if success is False:
            raise errors.Exception("\n".join(err_msg))

    def submit_job(
            self,
            source_code, *,
            code_type=Constant.CODE_TYPE_QASM2,
            job_type=Constant.JOB_TYPE_ESTIMATION,
            job_sched_policy=Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE,
            job_priority=Constant.DEFAULT_JOB_PRIORITY,
            description=None,
            shots=Constant.DEFAULT_SHOTS,
            backend=Constant.DRIVER_DUMMY,
            transpiler=Constant.TRANSPILER_CMSS,
            optimization_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            benchmark=None,
            dry_run=False):
        """
        Submit new job

        :param source_code: source code
        :param code_type: code type
        :param job_type: job type
        :param job_sched_policy: job scheduling policy
        :param job_priority: job priority
        :param description: job description
        :param shots: shots
        :param backend: backend
        :param transpiler: transpiler
        :param optimization_level: optimization level
        :param benchmark: benchmark types
        :param dry_run: dry run
        :return: submit_job result
        """
        method_name = "submit_job"

        # construct data and call json rpc
        data = {
            "source_code": source_code,
            "code_type": code_type,
            "job_type": job_type,
            "job_sched_policy": job_sched_policy,
            "job_priority": job_priority,
            "description": description,
            "shots": shots,
            "backend": backend,
            "transpiler": transpiler,
            "optimization_level": optimization_level,
            "benchmark": benchmark,
            "dry_run": dry_run
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result

    def get_job_status(self, job_id):
        """
        Get job status

        :param job_id: job ID
        :return: job status
        """
        method_name = "get_job_status"

        # Validate argument: job_id
        Client.handle_invalid_arguments(Library.validate_values_uuid(
            job_id, "job_id"))

        # construct data and call json rpc
        data = {
            "job_id": job_id
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result

    def get_job_results(self, job_id):
        """
        Get job results

        :param job_id: job ID
        :return: job results
        """
        method_name = "get_job_results"

        # Validate argument: job_id
        Client.handle_invalid_arguments(Library.validate_values_uuid(
            job_id, "job_id"))

        # construct data and call json rpc
        data = {
            "job_id": job_id
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result

    def get_jobs(self):
        """
        Get job status

        :return: jobs
        """
        method_name = "get_jobs"

        # construct data and call json rpc
        data = {}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result

    def cancel_jobs(self, job_ids):
        """
        Cancel jobs

        :param job_ids: job IDs
        :return: jobs
        """
        method_name = "cancel_jobs"

        # Validate argument: job_id
        for job_id in job_ids:
            Client.handle_invalid_arguments(
                Library.validate_values_uuid(job_id, "job_id"))

        # construct data and call json rpc
        data = {
            "job_ids": job_ids
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result

    def delete_jobs(self, job_ids):
        """
        Delete jobs

        :param job_ids: job IDs
        :return: jobs
        """
        method_name = "delete_jobs"

        # Validate argument: job_id
        for job_id in job_ids:
            Client.handle_invalid_arguments(
                Library.validate_values_uuid(job_id, "job_id"))

        # construct data and call json rpc
        data = {
            "job_ids": job_ids
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result
