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
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

import json
import logging
import requests
import time

from jsonrpcclient import Error, Ok, parse, request
from common.config import Config

logger = logging.getLogger(__name__)


class Client(object):
    """QCOS client api"""

    api_listen_ip = "100.78.171.22" #Config.API_SERVER_LISTEN_IP
    api_port = Config.API_SERVER_PORT
    api_version = "v1"
    endpoint_url = f"http://{api_listen_ip}:{api_port}/{api_version}"
    job_url = f"{endpoint_url}/job"
    default_headers = {"Content-Type": "application/json"}
    verbose = False

    @staticmethod
    def call_http_api(
            url, data=None, params=None, func_name=None,
            headers=default_headers, auth=None, verify_ssl=False,
            retry=1, timeout=2, success_http_code=[200]):
        if Client.verbose:
            print(f"Request [{func_name}]: {url}, HEADER: {headers}, "
                  f"PARAMS: {params}, DATA: {data}")
        r = None
        for i in range(1, retry + 1):
            if headers:
                r = requests.post(url, headers=headers, params=params,
                                  data=data, auth=auth, verify=verify_ssl)
            else:
                r = requests.post(url, params=params, data=data, auth=auth,
                                  verify=verify_ssl)
            if r.status_code in success_http_code:
                break
            if retry > 1:
                time.sleep(timeout)
        return r.status_code, r.reason, r.text, r

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        if Client.verbose:
            print(f"Response: status_code: {status_code}, reason: {reason}, "
                  f"text: {text}")

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        jsonrpc_data = request(method_name, params={"body": data})
        jsonrpc_data_json = json.dumps(jsonrpc_data)
        status_code, reason, text, result = Client.call_http_api(
            url, data=jsonrpc_data_json, params=params,
            func_name=method_name)
        Client.print_api_response(status_code, reason, text, result)
        return status_code, reason, text, result

    @staticmethod
    def parse_jsonrpc_response(jsonrpc_response):
        parsed = parse(jsonrpc_response)
        if isinstance(parsed, Ok):
            return True, parsed
        return False, parsed

    @staticmethod
    def submit_job(
            code_content, code_type, job_type, job_scheduling_policy,
            job_priority, shots, qubits, backend,
            transpiler, optimization_level):
        """Submit new job"""
        method_name = "submit_job"
        data = {
            "code_content": code_content,
            "code_type": code_type,
            "job_type": job_type,
            "job_scheduling_policy": job_scheduling_policy,
            "job_priority": job_priority,
            "shots": shots,
            "qubits": qubits,
            "backend": backend,
            "transpiler": transpiler,
            "optimization_level": optimization_level
        }
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result

    @staticmethod
    def get_job_status(job_id):
        """Get job status"""
        method_name = "get_job_status"
        data = {
            "job_id": job_id
        }
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result

    @staticmethod
    def get_job_results(job_id):
        """Get job results"""
        method_name = "get_job_results"
        data = {
            "job_id": job_id
        }
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result

    @staticmethod
    def get_jobs():
        """Get job status"""
        method_name = "get_jobs"
        data = {}
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result

    @staticmethod
    def cancel_job(job_id):
        """Cancel job"""
        method_name = "cancel_job"
        data = {
            "job_id": job_id
        }
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result

    @staticmethod
    def delete_job(job_ids):
        """Delete job"""
        method_name = "delete_job"
        data = {
            "job_ids": job_ids
        }
        status_code, reason, text, result = Client.call_json_rpc(
            Client.job_url, method_name, data)
        return status_code, reason, text, result
