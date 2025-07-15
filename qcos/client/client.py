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

import logging
import requests

from jsonrpcclient import Ok, parse, request

from qcos.common import errors
from qcos.common.config import Config
from qcos.common.constant import Constant, HttpMethod
from qcos.common.library import Library

logger = logging.getLogger(__name__)


class Client:
    """
    QCOS client api
    """
    verbose = False

    def __init__(self,
                 api_listen_ip=Config.API_SERVER_LISTEN_IP,
                 api_port=Config.API_SERVER_PORT):
        api_version = "v1"
        endpoint_url = f"http://{api_listen_ip}:{api_port}/{api_version}"
        self.job_url = f"{endpoint_url}/job"
        self.system_url = f"{endpoint_url}/system"

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
        status_code = None
        reason = None
        text = None
        result = None
        jsonrpc_data = request(method_name, params={"body": data})
        try:
            status_code, reason, text, result = Library.call_http_api(
                url, method=HttpMethod.POST, json=jsonrpc_data,
                params=params, func_name=method_name, debug=Client.verbose)
        except requests.exceptions.ConnectionError as ce:
            status_code = -1
            reason = f"Connection error: {str(ce)}"
        except Exception as e:
            status_code = -1
            reason = str(e)
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

    # [System]
    def ping(self, message):
        """
        Ping-pong to verify the availability of the system

        :param message: Ping message
        :return: Pong message
        """
        method_name = "ping"

        # construct data and call json rpc
        data = {
            "message": message
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.system_url, method_name, data)
        return status_code, reason, text, result

    def version(self):
        """
        Get system version

        :return: Version
        """
        method_name = "version"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.system_url, method_name, None)
        return status_code, reason, text, result

    # [Job]
    def submit_job(
            self,
            source_code, *,
            code_type=Constant.CODE_TYPE_QASM,
            job_id=None,
            job_type=Constant.JOB_TYPE_ESTIMATION,
            job_sched_policy=Constant.JOB_SCHED_POLICY_TIME_PRECEDENCE,
            job_priority=Constant.DEFAULT_JOB_PRIORITY,
            description=None,
            shots=Constant.DEFAULT_SHOTS,
            backend=Constant.DRIVER_DUMMY,
            transpiler=Constant.TRANSPILER_CMSS,
            optimization_level=Constant.DEFAULT_OPTIMIZATION_LEVEL,
            profiling=None,
            callbacks=None,
            dry_run=False):
        """
        Submit new job

        :param source_code: source code
        :param code_type: code type
        :param job_id: job uuid
        :param job_type: job type
        :param job_sched_policy: job scheduling policy
        :param job_priority: job priority
        :param description: job description
        :param shots: shots
        :param backend: backend
        :param transpiler: transpiler
        :param optimization_level: optimization level
        :param profiling: profiling types
        :param callbacks: callbacks
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
            "profiling": profiling,
            "callbacks": callbacks,
            "dry_run": dry_run
        }
        if job_id:
            data["job_id"] = str(job_id)
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

    def set_job_results(self, job_id, results):
        """
        Set job results

        :param job_id: job ID
        :param results: job results
        :return: jobs
        """
        method_name = "set_job_results"

        # Validate argument: job_id
        Client.handle_invalid_arguments(
            Library.validate_values_uuid(job_id, "job_id"))

        # construct data and call json rpc
        data = {
            "job_id": job_id,
            "results": results
        }
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data)
        return status_code, reason, text, result
