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

import json
import logging
import os
import uuid

import jsonrpcclient
import requests

from .common import errors
from .common.client_library import ClientLibrary
from .common.constant import Constant, HttpCode, HttpHeaders, HttpMethod


logger = logging.getLogger(__name__)

# Sentinel default for update methods to distinguish "field omitted"
# (do not send) from "field explicitly None" (clear the field).
_UNSET = object()


class SSL:
    """SSL configs."""

    use_ssl = False
    cert_file = None
    key_file = None
    ca_file = None


class Client:
    """QCOS client api."""

    verbose = False
    timeout = 60
    # When True, the timeout was set via command line --timeout and the
    # QCOS_CLIENT_TIMEOUT env var must be ignored in call_json_rpc.
    timeout_from_cli = False

    def __init__(
        self,
        api_server_ip=Constant.DEFAULT_API_SERVER_LISTEN_IP,
        api_server_port=Constant.DEFAULT_API_SERVER_LISTEN_PORT,
        use_ssl=False,
        ssl_certfile=None,
        ssl_keyfile=None,
        ssl_cafile=None,
        timeout=60,
        timeout_from_cli=False,
    ):
        # Config
        Client.timeout = timeout
        Client.timeout_from_cli = timeout_from_cli

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
        self.auth_url = f"{endpoint_url}/auth"
        self.driver_url = f"{endpoint_url}/driver"
        self.device_url = f"{endpoint_url}/device"
        self.transpiler_url = f"{endpoint_url}/transpiler"
        self.job_url = f"{endpoint_url}/job"
        self.user_url = f"{endpoint_url}/user"
        self.project_url = f"{endpoint_url}/project"
        self.system_url = f"{endpoint_url}/system"
        self.metrics_url = f"{endpoint_url}/metrics"
        self.flavor_url = f"{endpoint_url}/flavor"
        self.device_group_url = f"{endpoint_url}/device_group"

        # JWT token storage
        self.access_token = None
        # Custom request headers for virtual instance auth
        self.request_headers = None

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

    def set_token(self, token):
        """Set JWT access token for subsequent requests.

        Args:
            token: JWT access token string
        """
        self.access_token = token

    def get_token(self):
        """Get current JWT token.

        Returns:
            Current JWT access token or None
        """
        return self.access_token

    def clear_token(self):
        """Clear stored JWT token."""
        self.access_token = None

    def call_json_rpc(
        self,
        url,
        method_name,
        body_data=None,
        filters=None,
        fields=None,
        params=None,
    ):
        """Call json-rpc.

        Args:
            url: json-rpc url
            method_name: json-rpc method
            body_data: json-rpc data (Default value = None)
            filters: json-rpc filters
            fields: json-rpc fields
            params: json-rpc params (Default value = None)
        """
        status_code = None
        reason = None
        text = None
        result = None
        headers = HttpHeaders.DEFAULT_JSON_HEADERS

        # config client timeout
        # Precedence: command line --timeout > QCOS_CLIENT_TIMEOUT env var
        # > Client.timeout default. When the timeout was explicitly set
        # via the command line, the env var is ignored entirely.
        timeout = Client.timeout
        if not Client.timeout_from_cli:
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

        # Add JWT token to headers if available
        access_token = os.environ.get(Constant.ENV_VAR_ACCESS_TOKEN, None)
        if self.access_token:
            access_token = self.access_token  # override access_token
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        # get qcos virtual instance id
        qcos_virtual_instance_id = os.environ.get(
            Constant.ENV_VAR_VIRTUAL_INSTANCE_ID, None
        )
        if qcos_virtual_instance_id:
            headers["x-qcos-virtual-instance-id"] = qcos_virtual_instance_id

        # Apply custom request headers if set
        if self.request_headers:
            headers.update(self.request_headers)

        # call http api
        data_params = {}
        if body_data:
            data_params["body"] = body_data
        if filters:
            data_params["filters"] = filters
        if fields:
            data_params["fields"] = fields
        jsonrpc_data = jsonrpcclient.request(method_name, params=data_params)
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
        parsed = jsonrpcclient.parse(jsonrpc_response)
        if isinstance(parsed, jsonrpcclient.Ok):
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
    def version(self, details=False):
        """Get all api versions and capabilities.

        Args:
            details: Whether to include detailed capabilities information

        Returns:
            Version
        """
        method_name = "version"

        # construct data and call json rpc
        status_code, reason, text, result = self.call_json_rpc(
            self.version_url, method_name, {"details": details}
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
        status_code, reason, text, result = self.call_json_rpc(
            self.driver_url, method_name, body_data=None
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
        status_code, reason, text, result = self.call_json_rpc(
            self.driver_url, method_name, data
        )
        return status_code, reason, text, result

    # [Device]
    def get_devices(self, details=False):
        """Get device list.

        Returns:
            Device list message
        """
        method_name = "get_devices"

        # construct data and call json rpc
        data = {"details": details}
        status_code, reason, text, result = self.call_json_rpc(
            self.device_url, method_name, data
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
            self.device_url, method_name, data
        )
        return status_code, reason, text, result

    def set_device_maintain_mode(self, device_name, mode):
        """Set device maintain mode.

        Args:
            device_name: device name
            mode: maintain mode: "on" or "off"

        Returns:
            status_code, reason, text, result
        """
        method_name = "set_device_maintain_mode"

        # construct data and call json rpc
        data = {"device_name": device_name, "mode": mode}

        # construct data and call json rpc
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
            self.transpiler_url, method_name, body_data=None
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, body_data=None
        )
        return status_code, reason, text, result

    def show_mem(self):
        """Show memory usage of the API server process.

        Returns:
            memory usage info
        """
        method_name = "show_mem"

        # construct data and call json rpc
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, body_data=None
        )
        return status_code, reason, text, result

    def gc_mem(self, *, generations=2):
        """Manually trigger garbage collection.

        Args:
            generations: gc generations to collect (0, 1, 2)

        Returns:
            gc collection result
        """
        method_name = "gc_mem"

        # construct data and call json rpc
        data = {"generations": generations}
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, data
        )
        return status_code, reason, text, result

    def trace_mem(self, *, action="snapshot", nframe=25, sort_count=False):
        """Trace memory allocations via tracemalloc.

        Args:
            action: action to perform (snapshot, stop, clear)
            nframe: number of top memory allocations to show
            sort_count: sort top allocations by count (descending)
                instead of by size. Sorting is performed server-side
                before applying the nframe limit.

        Returns:
            tracemalloc statistics
        """
        method_name = "trace_mem"

        # construct data and call json rpc
        data = {"action": action, "nframe": nframe, "sort_count": sort_count}
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, data
        )
        return status_code, reason, text, result

    def list_workers(self):
        """List all prefect workers with name and status.

        Returns:
            list of workers
        """
        method_name = "list_workers"

        # construct data and call json rpc
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, body_data=None
        )
        return status_code, reason, text, result

    def restart_worker(self, *, worker_name):
        """Restart a single prefect worker by worker name.

        Args:
            worker_name: worker name to restart

        Returns:
            restart worker result
        """
        method_name = "restart_worker"

        # construct data and call json rpc
        data = {"worker_name": worker_name}
        status_code, reason, text, result = self.call_json_rpc(
            self.system_url, method_name, data
        )
        return status_code, reason, text, result
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
        backend=None,
        driver_options=None,
        transpiler=Constant.TRANSPILER_CMSS,
        transpiler_options=None,
        profiling=None,
        callbacks=None,
        dry_run=False,
        qec_options=None,
        flavor_id=None,
        extra_specs=None,
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
            qec_options: qec options
            flavor_id: flavor UUID for auto scheduling
            extra_specs: extra scheduling specifications

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
            "driver_options": driver_options,
            "transpiler": transpiler,
            "transpiler_options": transpiler_options,
            "profiling": profiling,
            "callbacks": callbacks,
            "dry_run": dry_run,
            "qec_options": qec_options,
        }

        # backend: only set if specified (None triggers auto scheduling)
        if backend:
            data["backend"] = backend
        # flavor_id and extra_specs for auto scheduling
        if flavor_id:
            data["flavor_id"] = str(flavor_id)
        if extra_specs:
            data["extra_specs"] = extra_specs

        if job_id:
            data["job_id"] = str(job_id)
        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    # [Flavor]
    def create_flavor(
        self,
        name,
        *,
        project_id=None,
        description=None,
        is_public=True,
        min_qubits=None,
        max_qubits=None,
        gate_fidelity_1q_min=None,
        gate_fidelity_2q_min=None,
        extra_properties=None,
        device_groups,
    ):
        """Create a flavor (preset scheduling policy).

        Args:
            name: flavor name
            project_id: project UUID (optional, defaults to
                current user's project)
            description: flavor description
            is_public: whether the flavor is public
            min_qubits: minimum qubits
            max_qubits: maximum qubits
            gate_fidelity_1q_min: min 1q gate fidelity
            gate_fidelity_2q_min: min 2q gate fidelity
            extra_properties: extra properties dict
                (merged from --property)
            device_groups: list of device group UUIDs
                (required, at least one)

        Returns:
            create_flavor result
        """
        method_name = "create_flavor"
        data = {
            "name": name,
            "is_public": is_public,
            "extra_properties": extra_properties,
            "device_groups": [str(dg) for dg in device_groups],
        }
        if project_id is not None:
            data["project_id"] = str(project_id)
        if description:
            data["description"] = description
        if min_qubits is not None:
            data["min_qubits"] = min_qubits
        if max_qubits is not None:
            data["max_qubits"] = max_qubits
        if gate_fidelity_1q_min is not None:
            data["gate_fidelity_1q_min"] = gate_fidelity_1q_min
        if gate_fidelity_2q_min is not None:
            data["gate_fidelity_2q_min"] = gate_fidelity_2q_min
        status_code, reason, text, result = self.call_json_rpc(
            self.flavor_url, method_name, data
        )
        return status_code, reason, text, result

    def update_flavor(
        self,
        flavor_id,
        name=_UNSET,
        description=_UNSET,
        is_public=_UNSET,
        project_id=_UNSET,
        min_qubits=_UNSET,
        max_qubits=_UNSET,
        gate_fidelity_1q_min=_UNSET,
        gate_fidelity_2q_min=_UNSET,
        extra_properties=_UNSET,
        device_groups=_UNSET,
    ):
        """Update a flavor by ID.

        Fields default to _UNSET (omitted from the request). Pass
        None explicitly to clear a nullable field; pass a value to
        update it.

        Args:
            flavor_id: flavor UUID
            name: flavor name (None clears, _UNSET skips)
            description: flavor description (None clears, _UNSET skips)
            is_public: whether the flavor is public (_UNSET skips)
            project_id: project UUID (_UNSET skips)
            min_qubits: minimum qubits (None clears, _UNSET skips)
            max_qubits: maximum qubits (None clears, _UNSET skips)
            gate_fidelity_1q_min: min 1q gate fidelity
                (None clears, _UNSET skips)
            gate_fidelity_2q_min: min 2q gate fidelity
                (None clears, _UNSET skips)
            extra_properties: extra properties dict to merge
                (from --property, _UNSET skips)
            device_groups: list of device group UUIDs
                (None clears mappings, _UNSET keeps existing)

        Returns:
            update_flavor result
        """
        method_name = "update_flavor"
        data = {"flavor_id": str(flavor_id)}
        if name is not _UNSET:
            data["name"] = name
        if description is not _UNSET:
            data["description"] = description
        if is_public is not _UNSET:
            data["is_public"] = is_public
        if project_id is not _UNSET:
            data["project_id"] = (
                str(project_id) if project_id is not None else None
            )
        if min_qubits is not _UNSET:
            data["min_qubits"] = min_qubits
        if max_qubits is not _UNSET:
            data["max_qubits"] = max_qubits
        if gate_fidelity_1q_min is not _UNSET:
            data["gate_fidelity_1q_min"] = gate_fidelity_1q_min
        if gate_fidelity_2q_min is not _UNSET:
            data["gate_fidelity_2q_min"] = gate_fidelity_2q_min
        if extra_properties is not _UNSET:
            data["extra_properties"] = extra_properties
        if device_groups is not _UNSET:
            data["device_groups"] = (
                None
                if device_groups is None
                else [str(dg) for dg in device_groups]
            )
        status_code, reason, text, result = self.call_json_rpc(
            self.flavor_url, method_name, data
        )
        return status_code, reason, text, result

    def get_flavor(self, flavor_id):
        """Get a flavor by ID.

        Args:
            flavor_id: flavor UUID

        Returns:
            get_flavor result
        """
        method_name = "get_flavor"
        data = {"flavor_id": str(flavor_id)}
        status_code, reason, text, result = self.call_json_rpc(
            self.flavor_url, method_name, data
        )
        return status_code, reason, text, result

    def get_flavors(self, filters=None):
        """Get all flavors with optional filtering.

        Args:
            filters: Optional filter conditions dictionary,
                e.g. {"flavor_name": "g1.all"}

        Returns:
            get_flavors result
        """
        method_name = "get_flavors"
        data = {}
        if filters:
            data["filters"] = filters
        status_code, reason, text, result = self.call_json_rpc(
            self.flavor_url, method_name, data
        )
        return status_code, reason, text, result

    def delete_flavors(self, flavor_ids):
        """Delete multiple flavors by IDs (batch).

        Args:
            flavor_ids: list of flavor UUIDs

        Returns:
            delete_flavors result
        """
        method_name = "delete_flavors"
        data = {"flavor_ids": [str(fid) for fid in flavor_ids]}
        status_code, reason, text, result = self.call_json_rpc(
            self.flavor_url, method_name, data
        )
        return status_code, reason, text, result

    # [Device Group]
    def create_device_group(
        self,
        name,
        device_names,
        project_id=None,
        description=None,
        is_public=True,
    ):
        """Create a device group.

        Args:
            name: device group name
            project_id: project UUID (optional)
            description: device group description
            device_names: list of device names in this group (required)
            is_public: whether the group is public

        Returns:
            create_device_group result
        """
        method_name = "create_device_group"
        data = {
            "name": name,
            "is_public": is_public,
        }
        if project_id is not None:
            data["project_id"] = str(project_id)
        if description:
            data["description"] = description
        if device_names is not None:
            data["device_names"] = device_names
        status_code, reason, text, result = self.call_json_rpc(
            self.device_group_url, method_name, data
        )
        return status_code, reason, text, result

    def update_device_group(
        self,
        group_id,
        name=_UNSET,
        description=_UNSET,
        device_names=_UNSET,
        is_public=_UNSET,
        project_id=_UNSET,
    ):
        """Update a device group by ID.

        Fields default to _UNSET (omitted from the request). Pass
        None explicitly to clear a nullable field; pass a value to
        update it.

        Args:
            group_id: device group UUID
            name: device group name (None clears, _UNSET skips)
            description: device group description
                (None clears, _UNSET skips)
            device_names: list of device names in this group
                (None clears, _UNSET skips)
            is_public: whether the group is public (_UNSET skips)
            project_id: project UUID (_UNSET skips)

        Returns:
            update_device_group result
        """
        method_name = "update_device_group"
        data = {"group_id": str(group_id)}
        if name is not _UNSET:
            data["name"] = name
        if description is not _UNSET:
            data["description"] = description
        if device_names is not _UNSET:
            data["device_names"] = device_names
        if is_public is not _UNSET:
            data["is_public"] = is_public
        if project_id is not _UNSET:
            data["project_id"] = (
                str(project_id) if project_id is not None else None
            )
        status_code, reason, text, result = self.call_json_rpc(
            self.device_group_url, method_name, data
        )
        return status_code, reason, text, result

    def get_device_group(self, group_id):
        """Get a device group by ID.

        Args:
            group_id: device group UUID

        Returns:
            get_device_group result
        """
        method_name = "get_device_group"
        data = {"group_id": str(group_id)}
        status_code, reason, text, result = self.call_json_rpc(
            self.device_group_url, method_name, data
        )
        return status_code, reason, text, result

    def get_device_groups(self, filters=None):
        """Get all device groups with optional filtering.

        Args:
            filters: Optional filter conditions dictionary,
                e.g. {"group_name": "my-group"}

        Returns:
            get_device_groups result
        """
        method_name = "get_device_groups"
        data = {}
        if filters:
            data["filters"] = filters
        status_code, reason, text, result = self.call_json_rpc(
            self.device_group_url, method_name, data
        )
        return status_code, reason, text, result

    def delete_device_groups(self, group_ids):
        """Delete multiple device groups by IDs (batch).

        Args:
            group_ids: list of device group UUIDs

        Returns:
            delete_device_groups result
        """
        method_name = "delete_device_groups"
        data = {"group_ids": [str(gid) for gid in group_ids]}
        status_code, reason, text, result = self.call_json_rpc(
            self.device_group_url, method_name, data
        )
        return status_code, reason, text, result

    @staticmethod
    def resolve_device_group_id(client, group_identifier):
        """Resolve group_id from either UUID or group_name.

        If group_identifier is a valid UUID, return it directly.
        Otherwise, treat it as a group_name and fetch the
        group_id from server via get_device_groups().

        Args:
            client: The QCOS client instance
            group_identifier: Either a group UUID or group name

        Returns:
            The group UUID
        """
        try:
            uuid.UUID(group_identifier)
            return group_identifier
        except ValueError:
            status_code, reason, text, result = client.get_device_groups(
                filters={"group_name": group_identifier}
            )
            if status_code != HttpCode.SUCCESS_OK:
                raise errors.GenericException(
                    f"Failed to fetch device groups: {reason}"
                )

            groups_data = json.loads(text)
            if "result" in groups_data and groups_data["result"]:
                groups = groups_data["result"]
                if groups:
                    return groups[0].get("id")

            if "error" in groups_data and groups_data["error"]:
                error_info = groups_data["error"]
                err_msg = (
                    f"{error_info['message']}: "
                    f"{error_info.get('data', {}).get('details', '')}.\n"
                    "You may query by group uuid instead of "
                    "group name."
                )
                raise errors.GenericException(err_msg)

            raise errors.GenericException(
                f"Device group '{group_identifier}' not found"
            )

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
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def get_jobs(self, filters=None):
        """Get job status.

        Args:
            filters: filters

        Returns:
            job status
        """
        method_name = "get_jobs"

        # construct data and call json rpc
        data = {}
        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data, filters=filters
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
        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def delete_jobs(self, job_ids, force=False):
        """Delete jobs.

        Args:
            job_ids: job IDs
            force: force delete jobs regardless of status

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
        data = {"job_ids": job_ids, "force": force}
        status_code, reason, text, result = self.call_json_rpc(
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
        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    def update_job(
        self, job_id=None, job_name=None, description=None, job_priority=None
    ):
        """Update job.

        Args:
            job_id: job uuid
            job_name: job name (optional)
            description: job description (optional)
            job_priority: job priority. Values: 1-10, Default: 5.
                          Highest priority: 1, Lowest Priority: 10

        Returns:
            update_job result
        """
        method_name = "update_job"

        # construct data and call json rpc
        data = {}

        if job_id:
            data["job_id"] = str(job_id)
        if job_name:
            data["job_name"] = job_name
        if description:
            data["description"] = description
        if job_priority:
            data["job_priority"] = job_priority

        status_code, reason, text, result = self.call_json_rpc(
            self.job_url, method_name, data
        )
        return status_code, reason, text, result

    @staticmethod
    def resolve_flavor_id(client, flavor_identifier):
        """Resolve flavor_id from either UUID or flavor_name.

        If flavor_identifier is a valid UUID, return it directly.
        Otherwise, treat it as a flavor_name and fetch the
        flavor_id from server via get_flavors().

        Args:
            client: The QCOS client instance
            flavor_identifier: Either a flavor UUID or flavor name

        Returns:
            The flavor UUID
        """
        # Check if it's a valid UUID
        try:
            uuid.UUID(flavor_identifier)
            return flavor_identifier
        except ValueError:
            # Not a UUID, treat as flavor_name and fetch with filters
            status_code, reason, text, result = client.get_flavors(
                filters={"flavor_name": flavor_identifier}
            )
            if status_code != HttpCode.SUCCESS_OK:
                raise errors.GenericException(
                    f"Failed to fetch flavors: {reason}"
                )

            flavors_data = json.loads(text)
            if "result" in flavors_data and flavors_data["result"]:
                flavors = flavors_data["result"]
                # Should only have one or zero flavors due to filter
                if flavors:
                    return flavors[0].get("id")

            if "error" in flavors_data and flavors_data["error"]:
                error_info = flavors_data["error"]
                err_msg = (
                    f"{error_info['message']}: "
                    f"{error_info.get('data', {}).get('details', '')}.\n"
                    "You may query by flavor uuid instead of flavor name."
                )
                raise errors.GenericException(err_msg)

            raise errors.GenericException(
                f"Flavor '{flavor_identifier}' not found"
            )

    # [User]

    @staticmethod
    def resolve_user_id(client, user_identifier):
        """Resolve user_id from either UUID or user_name.

        If user_identifier is a valid UUID, return it directly.
        Otherwise, treat it as a user_name and fetch the user_id from server.

        Args:
            client: The QCOS client instance
            user_identifier: Either a user UUID or user name

        Returns:
            The user UUID
        """
        # Check if it's a valid UUID
        try:
            uuid.UUID(user_identifier)
            return user_identifier
        except ValueError:
            # Not a UUID, treat as user_name and fetch with filters
            status_code, reason, text, result = client.get_users(
                filters={"user_name": user_identifier}
            )
            if status_code != HttpCode.SUCCESS_OK:
                raise errors.GenericException(
                    f"Failed to fetch users: {reason}"
                )

            users_data = json.loads(text)
            # Parse the response to find user by name
            # Response format: {user_id: {user_data}, ...}
            if "result" in users_data and users_data["result"]:
                users_info = users_data["result"]
                # Should only have one or zero users due to filter
                # Get the first (and only) user_id key
                for user_id in users_info.keys():
                    return user_id

            if "error" in users_data and users_data["error"]:
                error_info = users_data["error"]
                err_msg = (
                    f"{error_info['message']}: "
                    f"{error_info.get('data', {}).get('details', '')}.\n"
                    "You may query by user uuid instead of user name."
                )
                raise errors.GenericException(err_msg)

            raise errors.GenericException(
                f"User '{user_identifier}' not found"
            )

    @staticmethod
    def resolve_role_id(client, role_identifier):
        """Resolve role_id from either UUID or role_name.

        If role_identifier is a valid UUID, return it directly.
        Otherwise, treat it as a role_name and fetch the role_id from server.

        Args:
            client: The QCOS client instance
            role_identifier: Either a role UUID or role name

        Returns:
            The role UUID
        """
        # Check if it's a valid UUID
        try:
            uuid.UUID(role_identifier)
            return role_identifier
        except ValueError:
            # Not a UUID, treat as role_name and fetch with filters
            status_code, reason, text, result = client.get_roles(
                filters={"role_name": role_identifier}
            )
            if status_code != HttpCode.SUCCESS_OK:
                raise errors.GenericException(
                    f"Failed to fetch roles: {reason}"
                )

            roles_data = json.loads(text)
            # Parse the response to find role by name
            # Response format: {role_id: {role_data}, ...}
            if "result" in roles_data and roles_data["result"]:
                roles_info = roles_data["result"]
                # Should only have one or zero roles due to filter
                # Get the first (and only) role_id key
                for role_id in roles_info.keys():
                    return role_id

            raise errors.GenericException(
                f"Role '{role_identifier}' not found"
            )

    def get_user_mgmt(self):
        """Get user management settings.

        Returns:
            status_code, reason, text, result
        """
        method_name = "get_user_mgmt"
        data = {}
        status_code, reason, text, result = self.call_json_rpc(
            self.user_url, method_name, data
        )
        return status_code, reason, text, result

    def set_user_mgmt(self, auth_mode):
        """Set user management authentication mode.

        Args:
            auth_mode: Authentication mode ('no', 'jwt', or 'virtual_instance')

        Returns:
            status_code, reason, text, result
        """
        method_name = "set_user_mgmt"
        data = {"auth_mode": auth_mode}
        status_code, reason, text, result = self.call_json_rpc(
            self.user_url, method_name, data
        )
        return status_code, reason, text, result

    def create_user(
        self,
        user_name,
        password,
        roles,
        description=None,
        password_expiry_days=None,
        is_enabled=True,
        is_locked=True,
        project_id=None,
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
        if project_id is not None:
            data["project_id"] = project_id
        return self.call_json_rpc(self.user_url, "create_user", data)

    def get_user(self, user_id):
        """Get user by ID.

        Args:
            user_id: User ID (UUID)
        """
        data = {"user_id": user_id}
        return self.call_json_rpc(self.user_url, "get_user", data)

    def update_user(
        self,
        user_id,
        roles=None,
        description=None,
        password_expiry_days=None,
        is_enabled=None,
        is_locked=None,
    ):
        """Update user by ID.

        Args:
            user_id: User ID (UUID)
            roles: List of role names to assign
            description: User description
            password_expiry_days: Number of days until password expires
            is_enabled: Whether user account is enabled
            is_locked: Whether user account is locked
        """
        data = {"user_id": user_id}
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
        return self.call_json_rpc(self.user_url, "update_user", data)

    def delete_user(self, user_id, force=False):
        """Delete user by ID.

        Args:
            user_id: User ID (UUID)
            force: Force delete user and cascade delete related resources
        """
        data = {"user_id": user_id, "force": force}
        return self.call_json_rpc(self.user_url, "delete_user", data)

    def get_users(self, filters=None):
        """Get users with optional filtering.

        Args:
            filters: Optional filter conditions dictionary
        """
        data = {}
        if filters:
            data["filters"] = filters
        return self.call_json_rpc(self.user_url, "get_users", data)

    def create_role(self, role_name, permissions, description=None):
        """Create role."""
        data = {"role_name": role_name, "permissions": permissions}
        if description:
            data["description"] = description
        return self.call_json_rpc(self.user_url, "create_role", data)

    def get_role(self, role_id):
        """Get role by ID.

        Args:
            role_id: Role ID (UUID)
        """
        data = {"role_id": role_id}
        return self.call_json_rpc(self.user_url, "get_role", data)

    def update_role(self, role_id, permissions=None, description=None):
        """Update role by ID.

        Args:
            role_id: Role ID (UUID)
            permissions: List of permission strings
            description: Role description
        """
        data = {"role_id": role_id}
        if permissions:
            data["permissions"] = permissions
        if description is not None:
            data["description"] = description
        return self.call_json_rpc(self.user_url, "update_role", data)

    def delete_role(self, role_id):
        """Delete role by ID.

        Args:
            role_id: Role ID (UUID)
        """
        data = {"role_id": role_id}
        return self.call_json_rpc(self.user_url, "delete_role", data)

    def get_roles(self, filters=None):
        """Get roles with optional filtering.

        Args:
            filters: Optional dict with filter conditions, e.g.
                {'role_name': 'admin'}
        """
        data = {}
        if filters:
            data["filters"] = filters
        return self.call_json_rpc(self.user_url, "get_roles", data)

    def change_password(self, user_id, old_password, new_password):
        """Change password for user by ID.

        Args:
            user_id: User ID (UUID)
            old_password: Current password
            new_password: New password to set
        """
        data = {
            "user_id": user_id,
            "old_password": old_password,
            "new_password": new_password,
        }
        return self.call_json_rpc(self.user_url, "change_password", data)

    def get_login_logs(
        self, user_id=None, user_name=None, limit=100, offset=0
    ):
        """Get login logs by user ID or user_name.

        Args:
            user_id: User ID (UUID) to filter logs (optional)
            user_name: User name to filter logs (optional)
            limit: Maximum number of logs to return (default: 100)
            offset: Number of logs to skip (default: 0)
        """
        data = {"limit": limit, "offset": offset}
        if user_id:
            data["user_id"] = user_id
        if user_name:
            data["user_name"] = user_name
        return self.call_json_rpc(self.user_url, "get_login_logs", data)

    def clear_login_logs(self, user_id=None, user_name=None):
        """Clear login logs (all or for a specific user).

        Args:
            user_id: User ID (UUID) to clear logs for (optional)
            user_name: User name to clear logs for (optional)

        Returns:
            Number of logs cleared
        """
        data = {}
        if user_id:
            data["user_id"] = user_id
        if user_name:
            data["user_name"] = user_name
        return self.call_json_rpc(self.user_url, "clear_login_logs", data)

    # [Project]
    def create_project(self, project_name, description=None):
        """Create project.

        Args:
            project_name: Project name
            description: Project description (optional)

        Returns:
            Create project response
        """
        data = {"project_name": project_name}
        if description is not None:
            data["description"] = description
        return self.call_json_rpc(self.project_url, "create_project", data)

    def get_project(self, project_id):
        """Get project by ID.

        Args:
            project_id: Project ID (UUID)
        """
        data = {"project_id": project_id}
        return self.call_json_rpc(self.project_url, "get_project", data)

    def get_projects(self, filters=None):
        """Get projects with optional filtering.

        Args:
            filters: Optional filter conditions dictionary,
                e.g. {"name": "default"}

        Returns:
            Dictionary of projects keyed by project ID
        """
        data = {}
        if filters:
            data["filters"] = filters
        return self.call_json_rpc(self.project_url, "get_projects", data)

    def update_project(self, project_id, project_name=None, description=None):
        """Update project by ID.

        Args:
            project_id: Project ID (UUID)
            project_name: New project name (optional)
            description: New project description (optional)
        """
        data = {"project_id": project_id}
        if project_name is not None:
            data["project_name"] = project_name
        if description is not None:
            data["description"] = description
        return self.call_json_rpc(self.project_url, "update_project", data)

    def delete_project(self, project_id):
        """Delete project by ID.

        Args:
            project_id: Project ID (UUID)
        """
        data = {"project_id": project_id}
        return self.call_json_rpc(self.project_url, "delete_project", data)

    # [Auth]
    def login(self, username, password):
        """User login to get JWT tokens.

        This method implements the standard JWT login pattern:
        - Sends username and password to the server
        - Receives access_token (short-lived) and refresh_token (long-lived)
        - Stores both tokens for subsequent requests

        Args:
            username: Username for authentication
            password: Password for authentication

        Returns:
            Login response with JWT access and refresh tokens
        """
        data = {"username": username, "password": password}
        status_code, reason, text, result = self.call_json_rpc(
            self.auth_url, "login", data
        )

        # Store tokens on successful login
        if status_code == HttpCode.SUCCESS_OK:
            try:
                if isinstance(result, dict):
                    access_token = result.get("access_token")
                    refresh_token = result.get("refresh_token")
                elif hasattr(result, "get"):
                    access_token = result.get("access_token")
                    refresh_token = result.get("refresh_token")
                else:
                    access_token = None
                    refresh_token = None

                if access_token:
                    self.set_token(access_token)
                    os.environ[Constant.ENV_VAR_ACCESS_TOKEN] = access_token

                if refresh_token:
                    os.environ["QCOS_REFRESH_TOKEN"] = refresh_token

            except Exception as e:
                logger.warning(
                    f"Failed to store tokens from login response: {e}"
                )

        return status_code, reason, text, result

    def logout(self):
        """User logout.

        Returns:
            Logout response
        """
        status_code, reason, text, result = self.call_json_rpc(
            self.auth_url, "logout", {}
        )
        if status_code == HttpCode.SUCCESS_OK:
            self.clear_token()
        return status_code, reason, text, result

    def refresh_token(self):
        """Refresh JWT token using refresh_token.

        This method implements the standard JWT refresh token pattern:
        - Sends the stored refresh_token to the server
        - Receives new access_token and refresh_token
        - Updates stored tokens

        Returns:
            Token refresh response with new JWT access and refresh tokens
        """
        # Get refresh token from environment or stored value
        refresh_token_value = os.environ.get("QCOS_REFRESH_TOKEN")
        if not refresh_token_value:
            return (
                401,
                "Unauthorized",
                "",
                {"error": "No refresh token available"},
            )

        status_code, reason, text, result = self.call_json_rpc(
            self.auth_url,
            "refresh_token",
            {"refresh_token": refresh_token_value},
        )

        if status_code == HttpCode.SUCCESS_OK:
            # Handle both dict and Response object
            if isinstance(result, dict):
                access_token = result.get("access_token")
                refresh_token_new = result.get("refresh_token")
            elif hasattr(result, "get"):
                access_token = result.get("access_token")
                refresh_token_new = result.get("refresh_token")
            else:
                access_token = None
                refresh_token_new = None

            if access_token:
                self.set_token(access_token)
                # Also update refresh token
                if refresh_token_new:
                    os.environ["QCOS_REFRESH_TOKEN"] = refresh_token_new

        return status_code, reason, text, result

    def get_me(self):
        """Get current authenticated user info.

        Returns:
            Current user information
        """
        return self.call_json_rpc(self.auth_url, "me", {})

    # [Metrics]
    def get_system_health(self):
        """Get system health status.

        Returns:
            System health status
        """
        method_name = "get_system_health"
        status_code, reason, text, result = self.call_json_rpc(
            self.metrics_url, method_name, body_data=None
        )
        return status_code, reason, text, result

    def get_api_stats(self):
        """Get API access statistics.

        Returns:
            API statistics
            including total requests, last hour and last day counts
        """
        method_name = "get_api_stats"
        status_code, reason, text, result = self.call_json_rpc(
            self.metrics_url, method_name, body_data=None
        )
        return status_code, reason, text, result

    def get_job_stats(self):
        """Get job statistics.

        Returns:
            Job statistics including total, success, failed, running, etc.
        """
        method_name = "get_job_stats"
        status_code, reason, text, result = self.call_json_rpc(
            self.metrics_url, method_name, body_data=None
        )
        return status_code, reason, text, result
