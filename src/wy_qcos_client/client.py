#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
import os
import requests

from jsonrpcclient import Ok, parse, request

from .common import errors
from .common.client_library import ClientLibrary
from .common.constant import Constant, HttpHeaders, HttpMethod

logger = logging.getLogger(__name__)


class SSL:
    """SSL configs."""

    use_ssl = False
    cert_file = None
    key_file = None
    ca_file = None


class Client:
    """QCOS client api."""

    verbose = False
    timeout = 30

    def __init__(
        self,
        api_server_ip=Constant.DEFAULT_API_SERVER_LISTEN_IP,
        api_server_port=Constant.DEFAULT_API_SERVER_LISTEN_PORT,
        use_ssl=False,
        ssl_certfile=None,
        ssl_keyfile=None,
        ssl_cafile=None,
        timeout=30,
    ):
        # Config
        Client.timeout = timeout

        # SSL configs
        SSL.use_ssl = use_ssl
        SSL.cert_file = ssl_certfile
        SSL.key_file = ssl_keyfile
        SSL.ca_file = ssl_cafile

        # API endpoint configs
        api_version = Constant.DEFAULT_API_VERSION
        http_proto = "http"
        if use_ssl:
            http_proto = "https"
        base_endpoint_url = f"{http_proto}://{api_server_ip}:{api_server_port}"
        endpoint_url = f"{base_endpoint_url}/{api_version}"
        self.version_url = f"{base_endpoint_url}/version"
        self.driver_url = f"{endpoint_url}/driver"
        self.device_url = f"{endpoint_url}/device"
        self.transpiler_url = f"{endpoint_url}/transpiler"
        self.job_url = f"{endpoint_url}/job"
        self.user_url = f"{endpoint_url}/user"
        self.system_url = f"{endpoint_url}/system"

    @staticmethod
    def print_api_response(status_code, reason, text, result=None):
        """Print API response.

        Args:
            status_code: status code
            reason: reason
            text: text
            result: result text (Default value = None)
        """
        if Client.verbose:
            print(
                f"Response: status_code: {status_code}, reason: {reason}, "
                f"text: {text}, result: {result}"
            )

    @staticmethod
    def call_json_rpc(url, method_name, data=None, params=None):
        """Call json-rpc.

        Args:
            url: json-rpc url
            method_name: json-rpc method
            data: json-rpc data (Default value = None)
            params: json-rpc params (Default value = None)
        """
        status_code = None
        reason = None
        text = None
        result = None
        headers = HttpHeaders.DEFAULT_JSON_HEADERS

        # config client timeout
        timeout = Client.timeout
        try:
            qcos_client_timeout = os.environ.get("QCOS_CLIENT_TIMEOUT")
            if qcos_client_timeout:
                timeout = int(qcos_client_timeout)
        except Exception:
            return (
                -1,
                f"Invalid QCOS_CLIENT_TIMEOUT: {qcos_client_timeout}",
                text,
                result,
            )

        # get qcos virtual instance id
        qcos_virtual_instance_id = os.environ.get(
            "QCOS_VIRTUAL_INSTANCE_ID", None
        )
        if qcos_virtual_instance_id:
            headers["x-qcos-virtual-instance-id"] = qcos_virtual_instance_id

        # call http api
        jsonrpc_data = request(method_name, params={"body": data})
        try:
            status_code, reason, text, result = ClientLibrary.call_http_api(
                url,
                method=HttpMethod.POST,
                json=jsonrpc_data,
                params=params,
                func_name=method_name,
                headers=headers,
                use_ssl=SSL.use_ssl,
                verify_ssl=SSL.ca_file if SSL.ca_file else False,
                cert_file=SSL.cert_file,
                key_file=SSL.key_file,
                debug=Client.verbose,
                timeout=timeout,
            )
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
        """Parse json-rpc response.

        Args:
            jsonrpc_response: json-rpc response
        """
        parsed = parse(jsonrpc_response)
        if isinstance(parsed, Ok):
            return True, parsed
        return False, parsed

    @staticmethod
    def handle_invalid_arguments(results):
        """Handle invalid arguments.

        Args:
          results: results
        """
        success, err_msg = results
        if success is False:
            raise errors.InvalidArguments("\n".join(err_msg))

    # [version]
    def version(self):
        """Get all api versions and capabilities.

        Returns:
            Version
        """
        method_name = "version"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.version_url, method_name, {}
        )
        return status_code, reason, text, result

    # [Driver]
    def get_drivers(self):
        """Get driver list.

        Returns:
            Driver list message
        """
        method_name = "get_drivers"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.driver_url, method_name, data=None
        )
        return status_code, reason, text, result

    def get_driver(self, driver_name):
        """Get driver info.

        Args:
            driver_name: driver name

        Returns:
            driver info
        """
        method_name = "get_driver"

        # construct data and call json rpc
        data = {"name": driver_name}

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.driver_url, method_name, data
        )
        return status_code, reason, text, result

    # [Device]
    def get_devices(self):
        """Get device list.

        Returns:
            Device list message
        """
        method_name = "get_devices"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data=None
        )
        return status_code, reason, text, result

    def get_device(self, device_name, details=False):
        """Get device info.

        Args:
            device_name: device name
            details: need details information or not

        Returns:
            device info
        """
        method_name = "get_device"

        # construct data and call json rpc
        data = {"name": device_name, "details": details}

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    def calibrate_device(self, device_name, options=None):
        """Calibrate device.

        Args:
            device_name: device name
            options: calibration options
        """
        method_name = "calibrate_device"

        # construct data and call json rpc
        data = {
            "device_name": device_name,
            "method": method_name,
            "options": options,
        }

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    def get_calibrate_results(self, device_name):
        """Get calibrate results.

        Args:
            device_name: device name
        """
        method_name = "get_calibrate_results"

        # construct data and call json rpc
        data = {"device_name": device_name, "method": method_name}
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    def set_device_options(self, device_name, options=None):
        """Set device options.

        Args:
            device_name: device name
            options: device options
        """
        method_name = "set_device_options"

        # construct data and call json rpc
        data = {
            "device_name": device_name,
            "method": method_name,
            "options": options,
        }

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    def get_device_options(self, device_name):
        """Get device options.

        Args:
            device_name: device name

        Returns:
            status_code, reason, text, result
        """
        method_name = "get_device_options"

        # construct data and call json rpc
        data = {"device_name": device_name, "method": method_name}

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    # [Transpiler]
    def get_transpilers(self):
        """Get transpiler list.

        Returns:
            Transpiler list message
        """
        method_name = "get_transpilers"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.transpiler_url, method_name, data=None
        )
        return status_code, reason, text, result

    def get_transpiler(self, transpiler_name):
        """Get transpiler info.

        Args:
            transpiler_name: transpiler name

        Returns:
            transpiler info
        """
        method_name = "get_transpiler"

        # construct data and call json rpc
        data = {"name": transpiler_name}

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.transpiler_url, method_name, data
        )
        return status_code, reason, text, result

    # [System]
    def ping(self, message):
        """Ping-pong to verify the availability of the system.

        Args:
            message: Ping message

        Returns:
            Pong message
        """
        method_name = "ping"

        # construct data and call json rpc
        data = {"message": message}
        status_code, reason, text, result = Client.call_json_rpc(
            self.system_url, method_name, data
        )
        return status_code, reason, text, result

    def system_info(self):
        """Get system info.

        Returns:
            System info
        """
        method_name = "system_info"

        # construct data and call json rpc
        status_code, reason, text, result = Client.call_json_rpc(
            self.system_url, method_name, data=None
        )
        return status_code, reason, text, result

    # [Job]
    def submit_job(
        self,
        source_code,
        *,
        circuit_aggregation=None,
        code_type=Constant.CODE_TYPE_QASM,
        job_id=None,
        job_name=None,
        job_type=Constant.JOB_TYPE_SAMPLING,
        job_priority=Constant.DEFAULT_JOB_PRIORITY,
        description=None,
        shots=Constant.DEFAULT_SHOTS,
        backend=Constant.DRIVER_DUMMY,
        driver_options=None,
        transpiler=Constant.TRANSPILER_CMSS,
        transpiler_options=None,
        profiling=None,
        callbacks=None,
        dry_run=False,
    ):
        """Submit new job.

        Args:
            source_code: source code
            code_type: code type
            circuit_aggregation: circuit aggregation
            job_id: job uuid
            job_name: job name
            job_type: job type
            job_priority: job priority. Values: 1-10, Default: 5.
                          Highest priority: 1, Lowest Priority: 10
            description: job description
            shots: shots
            backend: backend name
            driver_options: driver options
            transpiler: transpiler name
            transpiler_options: transpiler options
            profiling: profiling types
            callbacks: callbacks
            dry_run: dry run

        Returns:
            submit_job result
        """
        method_name = "submit_job"

        # construct data and call json rpc
        data = {
            "source_code": source_code,
            "code_type": code_type,
            "circuit_aggregation": circuit_aggregation,
            "job_name": job_name,
            "job_type": job_type,
            "job_priority": job_priority,
            "description": description,
            "shots": shots,
            "backend": backend,
            "driver_options": driver_options,
            "transpiler": transpiler,
            "transpiler_options": transpiler_options,
            "profiling": profiling,
            "callbacks": callbacks,
            "dry_run": dry_run,
        }

        if job_id:
            data["job_id"] = str(job_id)
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def get_job_status(self, job_id):
        """Get job status.

        Args:
            job_id: job ID

        Returns:
            job status
        """
        method_name = "get_job_status"

        # Validate argument: job_id
        Client.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # construct data and call json rpc
        data = {"job_id": job_id}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def get_job_results(self, job_id):
        """Get job results.

        Args:
            job_id: job ID

        Returns:
            job results
        """
        method_name = "get_job_results"

        # Validate argument: job_id
        Client.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # construct data and call json rpc
        data = {"job_id": job_id}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def get_jobs(self):
        """Get job status.

        Returns:
             job status
        """
        method_name = "get_jobs"

        # construct data and call json rpc
        data = {}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def cancel_jobs(self, job_ids):
        """Cancel jobs.

        Args:
            job_ids: job IDs

        Returns:
            jobs
        """
        method_name = "cancel_jobs"

        # Validate argument: job_id
        for job_id in job_ids:
            Client.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(job_id, "job_id")
            )

        # construct data and call json rpc
        data = {"job_ids": job_ids}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def delete_jobs(self, job_ids):
        """Delete jobs.

        Args:
            job_ids: job IDs

        Returns:
            jobs
        """
        method_name = "delete_jobs"

        # Validate argument: job_id
        for job_id in job_ids:
            Client.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(job_id, "job_id")
            )

        # construct data and call json rpc
        data = {"job_ids": job_ids}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def set_job_results(self, job_id, new_results):
        """Set job results.

        Args:
            job_id: job ID
            new_results: new results list to set

        Returns:
            jobs
        """
        method_name = "set_job_results"

        # Validate argument: job_id
        Client.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # construct data and call json rpc
        data = {"job_id": job_id, "results": new_results}
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def update_job(
        self, job_id=None, job_priority=Constant.DEFAULT_JOB_PRIORITY
    ):
        """Update job.

        Args:
            job_id: job uuid
            job_priority: job priority. Values: 1-10, Default: 5.
                          Highest priority: 1, Lowest Priority: 10

        Returns:
            update_job result
        """
        method_name = "update_job"

        # construct data and call json rpc
        data = {"job_priority": job_priority}

        if job_id:
            data["job_id"] = str(job_id)
        status_code, reason, text, result = Client.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    # [User]
    def get_user_management_status(self):
        """Get user management status."""
        data = {}
        return Client.call_json_rpc(
            self.user_url, "get_user_management_status", data
        )

    def create_user(
        self,
        user_name,
        password,
        roles,
        description=None,
        password_expiry_days=None,
        is_enabled=True,
        is_locked=True,
    ):
        """Create user."""
        data = {
            "user_name": user_name,
            "password": password,
            "roles": roles,
            "is_enabled": is_enabled,
            "is_locked": is_locked,
        }
        if description:
            data["description"] = description
        if password_expiry_days is not None:
            data["password_expiry_days"] = password_expiry_days
        if is_enabled is not None:
            data["is_enabled"] = is_enabled
        if is_locked is not None:
            data["is_locked"] = is_locked
        return Client.call_json_rpc(self.user_url, "create_user", data)

    def get_user(self, user_name):
        """Get user."""
        data = {"user_name": user_name}
        return Client.call_json_rpc(self.user_url, "get_user", data)

    def update_user(
        self,
        user_name,
        roles=None,
        description=None,
        password_expiry_days=None,
        is_enabled=None,
        is_locked=None,
    ):
        """Update user."""
        data = {"user_name": user_name}
        if roles:
            data["roles"] = roles
        if description is not None:
            data["description"] = description
        if password_expiry_days is not None:
            data["password_expiry_days"] = password_expiry_days
        if is_enabled is not None:
            data["is_enabled"] = is_enabled
        if is_locked is not None:
            data["is_locked"] = is_locked
        return Client.call_json_rpc(self.user_url, "update_user", data)

    def delete_user(self, user_name):
        """Delete user."""
        data = {"user_name": user_name}
        return Client.call_json_rpc(self.user_url, "delete_user", data)

    def get_users(self):
        """Get users."""
        data = {}
        return Client.call_json_rpc(self.user_url, "get_users", data)

    def create_role(self, role_name, permissions, description=None):
        """Create role."""
        data = {"role_name": role_name, "permissions": permissions}
        if description:
            data["description"] = description
        return Client.call_json_rpc(self.user_url, "create_role", data)

    def get_role(self, role_name):
        """Get role."""
        data = {"role_name": role_name}
        return Client.call_json_rpc(self.user_url, "get_role", data)

    def update_role(self, role_name, permissions=None, description=None):
        """Update role."""
        data = {"role_name": role_name}
        if permissions:
            data["permissions"] = permissions
        if description is not None:
            data["description"] = description
        return Client.call_json_rpc(self.user_url, "update_role", data)

    def delete_role(self, role_name):
        """Delete role."""
        data = {"role_name": role_name}
        return Client.call_json_rpc(self.user_url, "delete_role", data)

    def get_roles(self):
        """Get roles."""
        data = {}
        return Client.call_json_rpc(self.user_url, "get_roles", data)

    def lock_user(self, user_name, action):
        """Lock or unlock user."""
        data = {"user_name": user_name, "action": action}
        return Client.call_json_rpc(self.user_url, "lock_user", data)

    def change_password(self, user_name, old_password, new_password):
        """Change password."""
        data = {
            "user_name": user_name,
            "old_password": old_password,
            "new_password": new_password,
        }
        return Client.call_json_rpc(self.user_url, "change_password", data)

    def get_login_logs(self, user_name=None, limit=100, offset=0):
        """Get login logs."""
        data = {"limit": limit, "offset": offset}
        if user_name:
            data["user_name"] = user_name
        return Client.call_json_rpc(self.user_url, "get_login_logs", data)
