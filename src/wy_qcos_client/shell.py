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

import argparse
import json
import logging
import os
import sys
from datetime import datetime

import argcomplete
from cliff import help
from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister
from cliff.show import ShowOne
from io import StringIO

from .client import Client, _UNSET
from .common import args_schema, errors
from .common.client_library import ClientLibrary
from .common.constant import Constant, HttpCode
from .common.qcos_version import QcosVersion


VERSION = QcosVersion.VERSION
DESCRIPTION = "QCOS command line interface"

logger = logging.getLogger(__name__)


class QcosShell(App):
    """QCOS shell."""

    CMD_GROUP_DEFAULT = "Default"
    CMD_GROUP_VERSION = "Version"
    CMD_GROUP_SYSTEM = "System"
    CMD_GROUP_AUTH = "Auth"
    CMD_GROUP_USER = "User"
    CMD_GROUP_PROJECT = "Project"
    CMD_GROUP_DRIVER = "Driver"
    CMD_GROUP_DEVICE = "Device"
    CMD_GROUP_TRANSPILER = "Transpiler"
    CMD_GROUP_JOB = "Job"
    CMD_GROUP_FLAVOR = "Flavor"
    CMD_GROUP_DEVICE_GROUP = "DeviceGroup"
    CMD_GROUP_METRICS = "Metrics"
    CMD_GROUPS = [
        CMD_GROUP_DEFAULT,
        CMD_GROUP_VERSION,
        CMD_GROUP_SYSTEM,
        CMD_GROUP_AUTH,
        CMD_GROUP_USER,
        CMD_GROUP_PROJECT,
        CMD_GROUP_DRIVER,
        CMD_GROUP_DEVICE,
        CMD_GROUP_DEVICE_GROUP,
        CMD_GROUP_TRANSPILER,
        CMD_GROUP_JOB,
        CMD_GROUP_FLAVOR,
        CMD_GROUP_METRICS,
    ]

    def __init__(self, description, version, command_manager):
        super().__init__(
            description=description,
            version=version,
            command_manager=command_manager,
            deferred_help=True,
        )
        self.client = None

    def clean_up(self, cmd, result, err):
        """Clean up after command execution."""
        super().clean_up(cmd, result, err)
        if hasattr(cmd, "extra_messages"):
            cmd.app.stdout.write(f"{cmd.extra_messages}\n")

    def initialize_app(self, argv):
        super().initialize_app(argv)
        api_server_ip = self.options.api_host
        api_server_port = self.options.api_port

        # check ssl configs
        use_ssl = self.options.use_ssl
        ssl_certfile = self.options.ssl_certfile
        ssl_keyfile = self.options.ssl_keyfile
        ssl_cafile = self.options.ssl_cafile
        if use_ssl:
            if ssl_certfile and not os.path.exists(ssl_certfile):
                raise errors.InvalidArguments(
                    f"Error: file not found: {ssl_certfile}"
                )
            if ssl_keyfile and not os.path.exists(ssl_keyfile):
                raise errors.InvalidArguments(
                    f"Error: file not found: {ssl_keyfile}"
                )
            if ssl_cafile and not os.path.exists(ssl_cafile):
                raise errors.InvalidArguments(
                    f"Error: file not found: {ssl_cafile}"
                )
            if not (ssl_certfile and ssl_keyfile):
                raise errors.InvalidArguments(
                    "Error: ssl_certfile and ssl_keyfile must be set when "
                    "use_ssl is enabled"
                )

        # Resolve client timeout with precedence:
        #   1. command line --timeout (user specified)
        #   2. env var QCOS_CLIENT_TIMEOUT
        #   3. default 60 seconds
        cli_timeout = self.options.timeout
        if cli_timeout is not None:
            timeout = cli_timeout
            timeout_from_cli = True
        else:
            env_timeout = os.environ.get("QCOS_CLIENT_TIMEOUT")
            if env_timeout:
                try:
                    timeout = int(env_timeout)
                except (TypeError, ValueError):
                    raise errors.InvalidArguments(
                        f"Invalid QCOS_CLIENT_TIMEOUT: {env_timeout}"
                    )
            else:
                timeout = 60
            timeout_from_cli = False

        self.client = Client(
            api_server_ip=api_server_ip,
            api_server_port=api_server_port,
            use_ssl=use_ssl,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            ssl_cafile=ssl_cafile,
            timeout=timeout,
            timeout_from_cli=timeout_from_cli,
        )
        # override cliff help.HelpAction
        help.HelpAction = HelpAction

    def build_option_parser(self, description, version, argparse_kwargs=None):
        """Return an argparse option parser for this application.

        Subclasses may override this method to extend
        the parser with more global options.

        Args:
            description: full description of the application
            version: version number for the application
            argparse_kwargs: argparse keyword arguments (Default value = None)
        """
        parser = argparse.ArgumentParser(
            description=description,
            add_help=False,
        )
        parser.add_argument(
            "--version",
            action="version",
            version=VERSION,
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            dest="verbose_level",
            default=self.DEFAULT_VERBOSE_LEVEL,
            help="Increase verbosity of output and show tracebacks on"
            " errors. You can repeat this option.",
        )
        parser.add_argument(
            "--debug",
            default=False,
            action="store_true",
            help="Show tracebacks on errors.",
        )
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_const",
            dest="verbose_level",
            const=0,
            help="Suppress output except warnings and errors.",
        )
        parser.add_argument(
            "--log-file",
            action="store",
            default=None,
            help="Specify a file to log output. Disabled by default.",
        )

        # API host configs
        default_api_server_ip = os.environ.get(
            "QCOS_SERVER_IP", Constant.DEFAULT_QCOS_SERVER_IP
        )
        if not default_api_server_ip:
            default_api_server_ip = Constant.DEFAULT_QCOS_SERVER_IP
        parser.add_argument(
            "--api-host",
            dest="api_host",
            default=default_api_server_ip,
            help=f"Specify api server address. "
            f"Default: {default_api_server_ip}",
        )
        default_api_server_port = os.environ.get(
            "QCOS_SERVER_PORT", Constant.DEFAULT_QCOS_SERVER_PORT
        )
        if not default_api_server_port:
            default_api_server_port = Constant.DEFAULT_QCOS_SERVER_PORT
        parser.add_argument(
            "--api-port",
            dest="api_port",
            type=int,
            default=int(default_api_server_port),
            help="Specify api server port. "
            f"Default: {default_api_server_port}",
        )

        # SSL configs
        env_use_ssl = os.environ.get("USE_SSL", "")
        default_use_ssl = env_use_ssl.lower() == "true"
        parser.add_argument(
            "--use-ssl",
            action="store_true",
            dest="use_ssl",
            default=default_use_ssl,
            help="Use SSL (https) connections",
        )
        default_ssl_certfile = os.environ.get(
            "SSL_CERTFILE", "/etc/qcos/ssl/ssl.crt"
        )
        parser.add_argument(
            "--ssl-certfile",
            dest="ssl_certfile",
            type=str,
            default=default_ssl_certfile,
            help=f"Specify SSL certfile. Default: {default_ssl_certfile}",
        )
        default_ssl_keyfile = os.environ.get(
            "SSL_KEYFILE", "/etc/qcos/ssl/ssl.key"
        )
        parser.add_argument(
            "--ssl-keyfile",
            dest="ssl_keyfile",
            type=str,
            default=default_ssl_keyfile,
            help=f"Specify SSL keyfile. Default: {default_ssl_keyfile}",
        )
        default_ssl_cafile = os.environ.get(
            "SSL_CAFILE", "/etc/qcos/ssl/cacert.pem"
        )
        parser.add_argument(
            "--ssl-cafile",
            dest="ssl_cafile",
            type=str,
            default=default_ssl_cafile,
            help=f"Specify SSL cafile. Default: {default_ssl_cafile}",
        )

        # Client timeout (seconds). default=None means user did not
        # specify it on the command line; in that case the env var
        # QCOS_CLIENT_TIMEOUT is consulted, falling back to 60s.
        parser.add_argument(
            "--timeout",
            dest="timeout",
            type=int,
            default=None,
            help="Request timeout in seconds. Overrides "
            "QCOS_CLIENT_TIMEOUT env var. Default: 60",
        )

        # Help
        parser.add_argument(
            "-h",
            "--help",
            dest="deferred_help",
            action="store_true",
            help="Show help message and exit.",
        )
        return parser


class HelpAction(argparse.Action):
    """Print help message including sub-commands.

    Provide a custom action so the -h and --help options
    to the main app will print a list of the commands.

    The commands are determined by checking the CommandManager
    instance, passed in as the "default" value for the action.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        grouped_cmds = {}
        max_len = 0
        app = self.default
        parser.print_help(app.stdout)
        app.stdout.write(
            f"\nCommands for API: /{Constant.DEFAULT_API_VERSION}:\n"
        )
        command_manager = app.command_manager
        for name, ep in sorted(command_manager):
            factory = ep.load()
            cmd = factory(self, None)
            one_liner = cmd.get_description().split("\n")[0]
            max_len = max(len(name), max_len)
            group = getattr(cmd, "group", QcosShell.CMD_GROUP_DEFAULT)
            if group not in grouped_cmds:
                grouped_cmds[group] = []
            grouped_cmds[group].append((name, one_liner.capitalize()))
        for cmd_group in QcosShell.CMD_GROUPS:
            app.stdout.write(f"  \033[33m[{cmd_group}]\033[39m\n")
            for name, one_liner in grouped_cmds[cmd_group]:
                name = f"\033[36m{name}\033[39m"
                app.stdout.write(f"  {name.ljust(max_len)}  {one_liner}\n")
            app.stdout.write("\n")
        raise help.HelpExit()


class CommandHelper:
    """Command helper."""

    @staticmethod
    def handle_invalid_arguments(results):
        """Handle invalid arguments.

        Args:
            results: results
        """
        success, err_msg = results
        if success is False:
            if isinstance(err_msg, str):
                err_msg = [err_msg]
            raise errors.InvalidArguments("\n".join(err_msg))

    @staticmethod
    def check_results(resource, name, status_code, reason, jsonrpc_response):
        """Check results.

        Args:
            resource: resource
            name: name
            status_code: status code
            reason: reason
            jsonrpc_response: json-rpc response
        """
        err_msg_list = []
        if status_code in [HttpCode.SUCCESS_OK]:
            try:
                jsonrpc_response_dict = json.loads(jsonrpc_response)
                success, parsed = Client.parse_jsonrpc_response(
                    jsonrpc_response_dict
                )
                if success:
                    return parsed.result
                code = parsed.code
                message = parsed.message
                if parsed.data:
                    err_msgs = parsed.data.get("errors", [])
                    for err_msg in err_msgs:
                        err_msg_list.append(
                            f"{message} ({code})\n{err_msg['msg']} "
                            f", loc: {', '.join(err_msg['loc'])}"
                        )
                    err_details = parsed.data.get("details", None)
                    if err_details:
                        err_msg_list.append(
                            f"ErrorMsg: {message} ({code}). "
                            f"Details: {err_details}"
                        )
                else:
                    err_msg_list.append(f"{message} ({code})")
            except Exception as e:
                err_msg_list.append(e)
        else:
            err_msg_list.append(reason)
        err_msgs = ""
        if err_msg_list:
            err_msgs = f"{', '.join(err_msg_list)}.\n"
        raise errors.GenericException(
            f"Failed to process {resource}: '{name}'. "
            f"[status_code: {status_code}]\n{err_msgs}"
        )

    @staticmethod
    def get_table_list_data(
        list_dict_values, header_list, is_dict=False, ignore_header_list=None
    ):
        """Get list of data for showing table in cli.

        Args:
            list_dict_values: list or dict of values
            header_list: headers for table
            is_dict: whether is dict or list values (Default value = False)
            ignore_header_list: headers to ignore (Default value = None)

        Returns:
            list of table data
        """
        keys = {}
        _headers = []
        headers = []
        all_values = []
        list_values = []
        if is_dict:
            for value in list_dict_values.values():
                list_values.append(value)
        else:
            list_values = list_dict_values

        if header_list:
            header_list = [s.lower() for s in header_list]
        if ignore_header_list:
            ignore_header_list = [s.lower() for s in ignore_header_list]

        for value in list_values:
            for k, v in value.items():
                add_element = True
                if header_list and k.lower() not in header_list:
                    add_element = False
                if ignore_header_list and k.lower() in ignore_header_list:
                    if add_element is True:
                        add_element = False
                if add_element:
                    header_name = k.upper()
                    _headers.append(header_name)
                    keys[header_name] = k
            break

        # make headers
        for header in header_list:
            header_name = header.upper()
            if header_name in _headers:
                headers.append(header_name)

        # make values
        for value in list_values:
            values = []
            for header in header_list:
                header_name = header.upper()
                if header_name in _headers:
                    v = value.get(keys[header_name], None)
                    if v is None:  # remove None values
                        v = ""
                    values.append(v)
            all_values.append(tuple(values))
        results = (tuple(headers), tuple(all_values))
        return results

    @staticmethod
    def get_table_data(values, keep_value_none=False):
        """Get data for showing table in cli.

        Args:
            values: values
            keep_value_none: keep value: None

        Returns:
            table data
        """
        keys = []
        headers = []
        _values = []
        for k, v in values.items():
            if not keep_value_none and v is None:  # remove None values
                continue
            headers.append(k.upper())
            keys.append(k)
        for key in keys:
            v = values.get(key, None)
            _values.append(v)
        results = (tuple(headers), tuple(_values))
        return results

    @staticmethod
    def check_device_existence(client, device_names, resource):
        """Check if devices exist, warn for non-existent ones.

        Args:
            client: QCOS client instance
            device_names: list of device names to check
            resource: resource name
        """
        if not device_names:
            return

        status_code, reason, text, result = client.get_devices()
        devices_results = CommandHelper.check_results(
            resource, "get_devices", status_code, reason, text
        )
        existing_names = devices_results.keys()
        for dn in device_names:
            if dn == "_all":
                continue
            if dn not in existing_names:
                logger.warning(
                    f"Warning: Device '{dn}' does not exist, "
                    f"adding to group anyway"
                )

    @staticmethod
    def resolve_device_group_names(client, device_group_ids):
        """Resolve device group IDs to names.

        Fetches all device groups once and builds an id->name map,
        then resolves each ID to its name (falls back to the ID
        itself if not found).

        Args:
            client: QCOS client instance
            device_group_ids: list of device group IDs

        Returns:
            list of device group names (falls back to ID if not found)
        """
        if not device_group_ids:
            return device_group_ids
        resource = QcosShell.CMD_GROUP_DEVICE_GROUP
        status_code, reason, text, result = client.get_device_groups()
        json_results = CommandHelper.check_results(
            resource, "get_device_groups", status_code, reason, text
        )
        name_map = {}
        if json_results:
            for group in json_results:
                group_id = str(group.get("id", ""))
                group_name = group.get("name", "")
                name_map[group_id] = group_name
        return [
            name_map.get(str(dg_id), str(dg_id)) for dg_id in device_group_ids
        ]

    @staticmethod
    def resolve_device_group_ids(client, device_group_identifiers):
        """Resolve device group identifiers (UUID or name) to IDs.

        Accepts a list where each item may be a UUID or a device
        group name. Each name is resolved individually via the
        server filter API (no full list fetch).

        Args:
            client: QCOS client instance
            device_group_identifiers: list of device group UUIDs
                or names

        Returns:
            list of device group IDs (UUID strings)

        Raises:
            errors.InvalidArguments: if a name cannot be resolved
        """
        if not device_group_identifiers:
            return device_group_identifiers
        resolved = []
        for identifier in device_group_identifiers:
            try:
                resolved.append(
                    Client.resolve_device_group_id(client, identifier)
                )
            except Exception as e:
                raise errors.InvalidArguments(
                    f"Invalid device group identifier: "
                    f"'{identifier}'. Must be a valid UUID or "
                    f"existing device group name."
                ) from e
        return resolved


# Version commands
class Version(Command):
    """Get server version."""

    group = QcosShell.CMD_GROUP_VERSION

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--details",
            action="store_true",
            help="include detailed capabilities information",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group

        status_code, reason, text, result = self.app.client.version(
            details=parsed_args.details
        )
        json_results = CommandHelper.check_results(
            resource, "version", status_code, reason, text
        )
        print(f"Server version: {json_results['version']}")
        print(f"API version: {json_results['api_version']}")
        print(
            f"Supported API versions: {json_results['supported_api_versions']}"
        )
        print(f"Platform version: {json_results['platform_version']}")
        print(f"Auth mode: {json_results['auth_mode']}")
        caps = json_results.get("capabilities", None)
        if caps:
            print("Capabilities:")
            print(f"  job_types: {', '.join(sorted(caps['job_types']))}")
            print(f"  profiling: {caps['profiling']}")
            print(f"  tech_types: {caps['tech_types']}")
            print(f"  drivers: {caps['drivers']}")
            print(f"  transpilers: {caps['transpilers']}")
            print(
                "  driver_transpiler_mappings: "
                f"{caps['driver_transpiler_mappings']}"
            )


# Driver commands
class GetDrivers(Lister):
    """Get driver list."""

    group = QcosShell.CMD_GROUP_DRIVER

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        header_list = [
            "name",
            "alias_name",
            "version",
            "tech_type",
            "max_qubits",
            "transpiler",
            "description",
        ]

        status_code, reason, text, result = self.app.client.get_drivers()
        json_results = CommandHelper.check_results(
            resource, "get_drivers", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            print("No drivers found")
        return table_values


class GetDriver(ShowOne):
    """Get driver info."""

    group = QcosShell.CMD_GROUP_DRIVER

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("driver_name", type=str, help="Driver name")
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        driver_name = parsed_args.driver_name

        status_code, reason, text, result = self.app.client.get_driver(
            driver_name
        )
        json_results = CommandHelper.check_results(
            resource, "get_driver", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


# Device commands
class GetDevices(Lister):
    """Get device list."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        header_list = [
            "name",
            "alias_name",
            "driver_name",
            "enable",
            "status",
            "description",
        ]

        status_code, reason, text, result = self.app.client.get_devices()
        json_results = CommandHelper.check_results(
            resource, "get_devices", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            print("No devices found")
        return table_values


class GetDevice(ShowOne):
    """Get device info."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("device_name", type=str, help="Device name")
        parser.add_argument(
            "--details",
            dest="details",
            action="store_true",
            default=False,
            help="Show detailed device information",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name
        details = parsed_args.details

        status_code, reason, text, result = self.app.client.get_device(
            device_name, details=details
        )
        json_results = CommandHelper.check_results(
            resource, "get_device", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class CalibrateDevice(Command):
    """Calibrate device."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("device_name", type=str, help="Device name")
        parser.add_argument(
            "--options",
            dest="options",
            type=str,
            default=None,
            help="Calibration options",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name
        options = parsed_args.options

        # Validate argument: options
        if options:
            try:
                options = json.loads(options)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: options"
                ) from exc

        status_code, reason, text, result = self.app.client.calibrate_device(
            device_name, options
        )
        CommandHelper.check_results(
            resource, "calibrate_device", status_code, reason, text
        )
        print(f"Send Device {device_name} calibrate cmd successfully")


class GetCalibrateResults(ShowOne):
    """Get calibrate results."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("device_name", type=str, help="Device name")
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name

        status_code, reason, text, result = (
            self.app.client.get_calibrate_results(device_name)
        )
        json_results = CommandHelper.check_results(
            resource, "get_calibrate_results", status_code, reason, text
        )
        if json_results is not None and json_results["details"] is not None:
            table_values = CommandHelper.get_table_data(
                json_results["details"]
            )
            return table_values
        else:
            print("json_results is None or json_results['details'] is None")


class SetDeviceOptions(Command):
    """Set device options."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("device_name", type=str, help="Device name")
        parser.add_argument(
            "--options",
            dest="options",
            type=str,
            default=None,
            help="Device options",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name
        options = parsed_args.options

        # Validate argument: options
        if options:
            try:
                options = json.loads(options)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: options"
                ) from exc

        status_code, reason, text, result = self.app.client.set_device_options(
            device_name, options
        )
        CommandHelper.check_results(
            resource, "set_device_options", status_code, reason, text
        )
        print(f"Device {device_name} options set successfully")


class GetDeviceOptions(ShowOne):
    """Get device options."""

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("device_name", type=str, help="Device name")
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name

        status_code, reason, text, result = self.app.client.get_device_options(
            device_name
        )
        json_results = CommandHelper.check_results(
            resource, "get_device_options", status_code, reason, text
        )
        if json_results is not None and json_results["details"] is not None:
            table_values = CommandHelper.get_table_data(
                json_results["details"]
            )
            return table_values
        else:
            print("json_results is None or json_results['details'] is None")


class SetDeviceMaintainMode(Command):
    """Set device maintain mode (on/off).

    Examples:
        qcos set-device-maintain-mode on --backend hanyuan1
        qcos set-device-maintain-mode off --backend hanyuan1
    """

    group = QcosShell.CMD_GROUP_DEVICE

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "mode",
            type=str,
            choices=["on", "off"],
            help="Maintain mode: on (set to maintain) or off (set to online)",
        )
        parser.add_argument(
            "--backend",
            dest="backend",
            type=str,
            required=True,
            help="Device name (backend)",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        mode = parsed_args.mode
        backend = parsed_args.backend

        status_code, reason, text, result = (
            self.app.client.set_device_maintain_mode(backend, mode)
        )
        json_results = CommandHelper.check_results(
            resource, "set_device_maintain_mode", status_code, reason, text
        )
        print(
            f"Device {json_results['name']} status "
            f"set to: {json_results['status']}"
        )


# Transpiler commands
class GetTranspilers(Lister):
    """Get transpiler list."""

    group = QcosShell.CMD_GROUP_TRANSPILER

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        header_list = [
            "name",
            "alias_name",
            "version",
            "enable",
            "supported_code_types",
        ]

        status_code, reason, text, result = self.app.client.get_transpilers()
        json_results = CommandHelper.check_results(
            resource, "get_transpilers", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            print("No transpilers found")
        return table_values


class GetTranspiler(ShowOne):
    """Get transpiler info."""

    group = QcosShell.CMD_GROUP_TRANSPILER

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "transpiler_name", type=str, help="Transpiler name"
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        transpiler_name = parsed_args.transpiler_name

        status_code, reason, text, result = self.app.client.get_transpiler(
            transpiler_name
        )
        json_results = CommandHelper.check_results(
            resource, "get_transpiler", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


# System commands
class Ping(Command):
    """Ping-pong to verify the availability of the system."""

    group = QcosShell.CMD_GROUP_SYSTEM

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "message", type=str, default="", help="Message to send"
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        message = parsed_args.message

        status_code, reason, text, result = self.app.client.ping(message)
        json_results = CommandHelper.check_results(
            resource, "ping", status_code, reason, text
        )
        print(f"Pong: {json_results['message']}")


class SystemInfo(ShowOne):
    """Show system information."""

    group = QcosShell.CMD_GROUP_SYSTEM

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group

        status_code, reason, text, result = self.app.client.system_info()
        json_results = CommandHelper.check_results(
            resource, "system_info", status_code, reason, text
        )
        print("System Info: ")
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class ShowMem(ShowOne):
    """Show memory usage of the API server process."""

    group = QcosShell.CMD_GROUP_SYSTEM

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group

        status_code, reason, text, result = self.app.client.show_mem()
        json_results = CommandHelper.check_results(
            resource, "show_mem", status_code, reason, text
        )
        # print timestamp (YYYY-MM-DD HH:MM:SS.xxx) before the report
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{now_str}]")
        print("Memory Usage: ")
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class GcMem(Command):
    """Manually trigger garbage collection."""

    group = QcosShell.CMD_GROUP_SYSTEM

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--generations",
            dest="generations",
            type=int,
            default=2,
            choices=[0, 1, 2],
            help="GC generations to collect (0, 1, 2). Default: 2",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        generations = parsed_args.generations

        status_code, reason, text, result = self.app.client.gc_mem(
            generations=generations
        )
        json_results = CommandHelper.check_results(
            resource, "gc_mem", status_code, reason, text
        )
        print("GC Result: ")
        print(
            f"Collected: {json_results['collected']}, "
            f"Uncollectable: {json_results['uncollectable']}"
        )
        print(
            f"Objects before: {json_results['count_before']}, "
            f"after: {json_results['count_after']}"
        )


class TraceMem(Lister):
    """Trace memory allocations via tracemalloc.

    Actions:
        snapshot: start tracing (if not active) and take a snapshot
        stop: stop tracemalloc tracing and release all traces
        clear: clear traces but keep tracing
    """

    group = QcosShell.CMD_GROUP_SYSTEM

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--action",
            dest="action",
            type=str,
            default="snapshot",
            choices=["snapshot", "stop", "clear"],
            help="Action: snapshot (default), stop, or clear",
        )
        parser.add_argument(
            "--nframe",
            dest="nframe",
            type=int,
            default=25,
            help="Number of top memory allocations to show "
            "(only for snapshot). Default: 25",
        )
        parser.add_argument(
            "--sort-count",
            dest="sort_count",
            action="store_true",
            default=False,
            help="Sort top memory allocations by count (descending). "
            "By default allocations are sorted by size.",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        action = parsed_args.action
        nframe = parsed_args.nframe
        sort_count = parsed_args.sort_count

        # Sorting by count (when --sort-count is set) is performed
        # server-side before the nframe limit is applied, so that the
        # top entries by count are returned instead of the top entries
        # by size truncated to nframe.
        status_code, reason, text, result = self.app.client.trace_mem(
            action=action, nframe=nframe, sort_count=sort_count
        )
        json_results = CommandHelper.check_results(
            resource, "trace_mem", status_code, reason, text
        )
        # print timestamp (YYYY-MM-DD HH:MM:SS.xxx) before the report
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{now_str}]")
        print("Tracemalloc: ")
        print(
            f"Tracing: {json_results['tracing']}, "
            f"Blocks: {json_results['traced_blocks']}"
        )
        print(
            f"Current: {json_results['current']} bytes, "
            f"Peak: {json_results['peak']} bytes"
        )
        # top_stats are already sorted server-side (by size by default,
        # or by count when --sort-count was requested).
        top_stats = json_results.get("top_stats", [])
        header_list = ["location", "size", "count"]
        table_values = CommandHelper.get_table_list_data(
            top_stats, header_list
        )
        return table_values


# Job commands
class SubmitJob(Command):
    """Submit job."""

    group = QcosShell.CMD_GROUP_JOB

    @staticmethod
    def validate_filepath(file_path):
        if not os.path.exists(file_path):
            raise argparse.ArgumentTypeError(
                f"Error: file: {file_path} does not exist"
            )
        return file_path

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--code-type",
            dest="code_type",
            choices=Constant.CODE_TYPES,
            default=Constant.CODE_TYPE_QASM,
            help=f"Code Types: {','.join(Constant.CODE_TYPES)}",
        )
        parser.add_argument(
            "--job-id", dest="job_id", type=str, help="Job uuid"
        )
        parser.add_argument(
            "--circuit-aggregation",
            dest="circuit_aggregation",
            choices=Constant.AGGREGATION_TYPES,
            help="Circuit aggregation: "
            f"{','.join(Constant.AGGREGATION_TYPES)}",
        )
        parser.add_argument(
            "-n",
            "--job-name",
            dest="job_name",
            type=str,
            default=None,
            help="Job name",
        )
        parser.add_argument(
            "--job-type",
            dest="job_type",
            default=f"{Constant.JOB_TYPE_SAMPLING}",
            choices=Constant.JOB_TYPES,
            help=f"Job type: {','.join(Constant.JOB_TYPES)}",
        )
        parser.add_argument(
            "--job-priority",
            dest="job_priority",
            type=int,
            default=f"{Constant.DEFAULT_JOB_PRIORITY}",
            help="Set job priority. Values: 1-10, Default: 5. "
            "Highest priority: 1, Lowest Priority: 10",
        )
        parser.add_argument(
            "--description",
            dest="description",
            default=None,
            help="Set job description",
        )
        parser.add_argument(
            "--shots",
            dest="shots",
            type=int,
            default=Constant.DEFAULT_SHOTS,
            help="Shots",
        )
        default_backend = None
        parser.add_argument(
            "--backend",
            dest="backend",
            default=default_backend,
            help="Set backend device name. Mutually exclusive with "
            "--flavor; if not specified, auto scheduling is "
            "triggered (requires --flavor)",
        )
        parser.add_argument(
            "--flavor",
            dest="flavor",
            type=str,
            default=None,
            help="Flavor ID (UUID) or flavor name for auto "
            "scheduling. Mutually exclusive with --backend. "
            "A flavor name is resolved to flavor_id before "
            "submitting the job",
        )
        parser.add_argument(
            "--extra-specs",
            dest="extra_specs",
            type=str,
            default=None,
            help="Extra scheduling specifications (JSON string). "
            "Only allowed together with --flavor, not with "
            "--backend",
        )
        parser.add_argument(
            "--driver-options",
            dest="driver_options",
            type=str,
            default=None,
            help="Set driver options",
        )
        parser.add_argument(
            "--transpiler",
            dest="transpiler",
            default=None,
            help="Set transpiler name.",
        )
        parser.add_argument(
            "--transpiler-options",
            dest="transpiler_options",
            type=str,
            default=None,
            help="Set transpiler options",
        )
        parser.add_argument(
            "--profiling",
            nargs="*",
            type=str,
            choices=Constant.PROFILING_TYPES,
            dest="profiling",
            help=f"Profiling types: {','.join(Constant.PROFILING_TYPES)}",
        )
        parser.add_argument(
            "--callbacks", dest="callbacks", type=str, help="Callbacks list"
        )
        parser.add_argument(
            "-D",
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Dry run",
        )
        parser.add_argument(
            "-f",
            "--source-code-file",
            dest="source_code_files",
            nargs="+",
            type=self.validate_filepath,
            required=True,
            help="Source code file, files can be specified multiple times",
        )
        parser.add_argument(
            "--qec-options",
            dest="qec_options",
            type=str,
            default=None,
            help="Set qec options",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_name = parsed_args.job_name
        dry_run = parsed_args.dry_run
        code_type = parsed_args.code_type
        job_id = parsed_args.job_id
        circuit_aggregation = parsed_args.circuit_aggregation
        job_type = parsed_args.job_type
        job_priority = parsed_args.job_priority
        description = parsed_args.description
        shots = parsed_args.shots
        backend = parsed_args.backend
        flavor = parsed_args.flavor
        extra_specs = parsed_args.extra_specs
        driver_options = parsed_args.driver_options
        transpiler = parsed_args.transpiler
        transpiler_options = parsed_args.transpiler_options
        profiling = parsed_args.profiling
        callbacks = parsed_args.callbacks
        qec_options = parsed_args.qec_options

        # Validate scheduling params: backend and flavor are
        # mutually exclusive; either one must be specified.
        # extra_specs is only allowed together with flavor.
        if backend and flavor:
            raise errors.InvalidArguments(
                "--backend and --flavor are mutually exclusive, "
                "please specify only one of them"
            )
        if backend and extra_specs:
            raise errors.InvalidArguments(
                "--extra-specs is only allowed together with "
                "--flavor, not with --backend"
            )
        if not backend and not flavor:
            raise errors.InvalidArguments(
                "Either --backend or --flavor must be specified"
            )

        # Parse extra_specs JSON
        extra_specs_json = None
        if extra_specs:
            try:
                extra_specs_json = json.loads(extra_specs)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: extra_specs"
                ) from exc

        # request capabilities
        status_code, reason, text, result = self.app.client.version(
            details=True
        )
        json_results = CommandHelper.check_results(
            resource, "version", status_code, reason, text
        )
        caps = json_results["capabilities"]
        supported_transpilers = caps["transpilers"]

        # Validate argument: code_type
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_enum(
                code_type, "code_type", Constant.CODE_TYPES
            )
        )

        # read source code files
        source_code_list = []
        if parsed_args.source_code_files:
            for source_code_file in parsed_args.source_code_files:
                success, err_msg, file_content = get_content_by_type(
                    code_type, source_code_file
                )
                if not success:
                    raise errors.InvalidArguments(err_msg)
                source_code_list.append(file_content)

        # Validate argument: source_code
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_schema(
                source_code_list, args_schema.SOURCE_CODE_SCHEMA
            )
        )

        if not source_code_list:
            raise errors.InvalidArguments(
                "Invalid argument: source_code_list is required"
            )

        # Validate argument: job_name
        if job_name:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_name(job_name)
            )

        # Validate argument: job_id
        if job_id:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(job_id, "job_id")
            )

        # Validate argument: job_type
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_enum(
                job_type, "job_type", Constant.JOB_TYPES
            )
        )

        # Validate argument: job_priority
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_range(
                job_priority,
                "job_priority",
                Constant.MIN_JOB_PRIORITY,
                Constant.MAX_JOB_PRIORITY,
            )
        )

        # Validate argument: description
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_length(
                description,
                "description",
                Constant.MIN_DESCRIPTION_LENGTH,
                Constant.MAX_DESCRIPTION_LENGTH,
                allow_none=True,
            )
        )

        # Validate argument: shots
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_range(
                shots, "shots", Constant.MIN_SHOTS, Constant.MAX_SHOTS
            )
        )

        # Validate argument: driver_options
        if driver_options:
            try:
                driver_options = json.loads(driver_options)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: driver_options"
                ) from exc
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_schema(
                    driver_options, args_schema.DRIVER_OPTIONS, allow_none=True
                )
            )

        # Validate argument: transpiler
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_enum(
                transpiler,
                "transpiler",
                supported_transpilers.keys(),
                allow_none=True,
            )
        )

        # Validate argument: transpiler_options
        if transpiler_options:
            try:
                transpiler_options = json.loads(transpiler_options)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: transpiler_options"
                ) from exc
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_schema(
                    transpiler_options,
                    args_schema.TRANSPILER_OPTIONS,
                    allow_none=True,
                )
            )

        # Validate argument: qec_options
        if qec_options:
            try:
                qec_options = json.loads(qec_options)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: qec_options"
                ) from exc
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_schema(
                    qec_options,
                    args_schema.QEC_OPTIONS,
                    allow_none=True,
                )
            )

        # Validate argument: callbacks
        callbacks_json = None
        if callbacks:
            try:
                callbacks_json = json.loads(callbacks)
            except json.decoder.JSONDecodeError as e:
                raise errors.InvalidArguments(
                    f"Invalid argument: callback. reason: {e}"
                )
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_schema(
                    callbacks_json, args_schema.CALLBACKS_SCHEMA
                )
            )

        # Resolve flavor identifier (UUID or name) to flavor_id.
        # flavor_id is the only form accepted by the submit_job API.
        flavor_id = None
        if flavor:
            flavor_id = Client.resolve_flavor_id(self.app.client, flavor)

        # call api
        status_code, reason, text, result = self.app.client.submit_job(
            source_code_list,
            code_type=code_type,
            job_id=job_id,
            circuit_aggregation=circuit_aggregation,
            job_name=job_name,
            job_type=job_type,
            job_priority=job_priority,
            description=description,
            shots=shots,
            backend=backend,
            driver_options=driver_options,
            transpiler=transpiler,
            transpiler_options=transpiler_options,
            profiling=profiling,
            callbacks=callbacks_json,
            dry_run=dry_run,
            qec_options=qec_options,
            flavor_id=flavor_id,
            extra_specs=extra_specs_json,
        )
        results = CommandHelper.check_results(
            resource, "submit_job", status_code, reason, text
        )
        print(f"Job ID: {results.get('job_id', None)}")


class GetJobStatus(ShowOne):
    """Get job status."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_id", type=str, help="Job ID")
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments

        Returns:
            results of command
        """
        resource = self.group
        job_id = parsed_args.job_id

        # Validate argument: job_id
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # call api
        status_code, reason, text, result = self.app.client.get_job_status(
            job_id
        )
        json_results = CommandHelper.check_results(
            resource, "get_job_status", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class GetJobResults(ShowOne):
    """Get job results."""

    group = QcosShell.CMD_GROUP_JOB

    def save_file(
        self,
        output_file: str,
        assume_override: bool,
        file_content: str,
        fmt_name: str,
    ):
        """Save job_results to file.

        Args:
            output_file: output file name
            assume_override: assume override
            file_content: file content
            fmt_name: fmt name
        """
        if os.path.isdir(output_file):
            raise errors.InvalidArguments(
                f"{output_file} is a directory, please specify a file path"
            )
        if os.path.exists(output_file) and not assume_override:
            confirm = input("File exists, need to override this file? (y/n) ")
            _confirm = confirm.lower().strip()
            if _confirm not in ("y", "yes"):
                print(
                    "File exists and do not override it, "
                    f"abort saving result to {output_file}."
                )
                return

        file_dir = os.path.dirname(os.path.abspath(output_file))
        if file_dir and not os.path.exists(file_dir):
            try:
                os.makedirs(file_dir, exist_ok=True)
            except Exception as e:
                raise errors.InvalidArguments(
                    f"Error: Failed to create directory {file_dir}: {e}"
                )

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(file_content)
        except Exception as e:
            raise errors.GenericException(f"Error: Write file failed: {e}")
        print(
            f"Job results (format: {fmt_name}) are output to file: "
            f"{output_file} successfully."
        )
        return

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_id", type=str, help="Job ID")
        parser.add_argument(
            "--output-file",
            dest="output_file",
            default=None,
            help="Output file",
        )
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="assume_override",
            action="store_true",
            help="Override the file",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments

        Returns:
            results of command
        """
        resource = self.group
        job_id = parsed_args.job_id
        output_file = parsed_args.output_file
        assume_override = parsed_args.assume_override

        # Validate argument: job_id
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # call api
        status_code, reason, text, result = self.app.client.get_job_results(
            job_id
        )
        json_results = CommandHelper.check_results(
            resource, "get_job_results", status_code, reason, text
        )

        _results = json_results.get("results", None)
        if _results:
            index = 0
            for _result in _results:
                for k, v in _result.items():
                    if k != "metadata":
                        key = f"{k} [{index}]"
                        json_results[key] = v
                index += 1

        table_values = CommandHelper.get_table_data(json_results)
        if table_values is None:
            raise errors.GenericException("Table values is None.")

        if output_file is not None:
            fmt_name = getattr(parsed_args, "formatter", "table")
            formatter = self._formatter_plugins[fmt_name].obj
            headers, rows = table_values
            buf = StringIO()
            formatter.emit_one(headers, rows, buf, parsed_args)
            file_content = buf.getvalue()
            self.save_file(
                output_file, assume_override, file_content, fmt_name
            )
            return (), ()

        return table_values


class GetJobs(Lister):
    """Get jobs."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--all-projects",
            dest="all_projects",
            action="store_true",
            help="All projects",
        )
        parser.add_argument(
            "--all-users",
            dest="all_users",
            action="store_true",
            help="All users from same projects",
        )
        parser.add_argument(
            "--project-id",
            dest="project_id",
            type=str,
            default=None,
            help="Filter by project ID",
        )
        parser.add_argument(
            "--user-id",
            dest="user_id",
            type=str,
            default=None,
            help="Filter by user ID",
        )
        parser.add_argument(
            "--job-ids",
            dest="job_ids",
            nargs="*",
            type=str,
            default=[],
            help="Filter by job IDs (space-separated)",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        header_list = [
            "project_id",
            "job_id",
            "job_name",
            "job_status",
            "progress",
            "backend",
            "job_type",
            "shots",
            "created_at",
            "started_at",
            "ended_at",
        ]

        # Validate arguments
        # Validate project_id if provided
        if parsed_args.project_id:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(
                    parsed_args.project_id, "project_id"
                )
            )

        # Validate user_id if provided
        if parsed_args.user_id:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(
                    parsed_args.user_id, "user_id"
                )
            )

        # Validate job_ids if provided
        if parsed_args.job_ids:
            for job_id in parsed_args.job_ids:
                CommandHelper.handle_invalid_arguments(
                    ClientLibrary.validate_values_uuid(job_id, "job_id")
                )

        # call api
        filters = {}
        if parsed_args.all_projects:
            filters["all_projects"] = parsed_args.all_projects
        if parsed_args.all_users:
            filters["all_users"] = parsed_args.all_users
        if parsed_args.project_id:
            filters["project_id"] = parsed_args.project_id
        if parsed_args.user_id:
            filters["user_id"] = parsed_args.user_id
        if parsed_args.job_ids:
            filters["job_ids"] = parsed_args.job_ids
        status_code, reason, text, result = self.app.client.get_jobs(
            filters=filters
        )
        json_results = CommandHelper.check_results(
            resource, "get_jobs", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=False
        )

        if json_results:
            self.extra_messages = f"Total jobs: {len(json_results)}\n"
        else:
            print("No jobs found")
        return table_values


class CancelJobs(Command):
    """Cancel jobs."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_ids", help="Job IDs")
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="assume_yes",
            action="store_true",
            help="Answer yes for all question",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_ids = parsed_args.job_ids
        assume_yes = parsed_args.assume_yes

        job_id_list = []
        if job_ids.lower() == "all":
            # get all job ids
            status_code, reason, text, result = self.app.client.get_jobs()
            json_results = CommandHelper.check_results(
                resource, "get_jobs", status_code, reason, text
            )
            if json_results:
                for job_info in json_results:
                    job_id = job_info["job_id"]
                    job_id_list.append(job_id)
            if not assume_yes:
                confirm = input("Are you sure to delete all jobs ? (y/n) ")
                _confirm = confirm.lower().strip()
                if _confirm not in ("y", "yes"):
                    print("User cancelled operation, abort!")
                    sys.exit(0)
        else:
            # parse job ids
            job_id_str_list = job_ids.split(",")
            for job_id in job_id_str_list:
                try:
                    job_id = job_id.strip()
                    # Validate argument: job_id
                    CommandHelper.handle_invalid_arguments(
                        ClientLibrary.validate_values_uuid(job_id, "job_id")
                    )
                    job_id_list.append(job_id)
                except ValueError as e:
                    raise errors.InvalidArguments(
                        f"Invalid job_id: {job_id}."
                    ) from e

        # call api
        status_code, reason, text, result = self.app.client.cancel_jobs(
            job_id_list
        )
        json_results = CommandHelper.check_results(
            resource, "cancel_job", status_code, reason, text
        )

        # print results
        jobs = []
        for result in json_results:
            jobs.append(result["job_id"])
        if jobs:
            print(
                f"The following {len(jobs)} "
                f"jobs will be cancelled: {', '.join(map(str, jobs))}"
            )
        else:
            if job_ids.lower() == "all":
                print("No jobs found")
            else:
                print(f"Jobs: {job_ids} are not found or non-cancelable")


class DeleteJobs(Command):
    """Delete jobs."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_ids", help="Job IDs")
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="assume_yes",
            action="store_true",
            help="Answer yes for all question",
        )
        parser.add_argument(
            "-f",
            "--force",
            default=False,
            dest="force",
            action="store_true",
            help="Force delete jobs regardless of status",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_ids = parsed_args.job_ids
        assume_yes = parsed_args.assume_yes
        force = parsed_args.force

        job_id_list = []
        if job_ids.lower() == "all":
            # get all job ids
            status_code, reason, text, result = self.app.client.get_jobs()
            json_results = CommandHelper.check_results(
                resource, "get_jobs", status_code, reason, text
            )
            if json_results:
                for job_info in json_results:
                    job_id = job_info["job_id"]
                    job_id_list.append(job_id)
            if not assume_yes:
                confirm = input("Are you sure to delete all jobs ? (y/n) ")
                _confirm = confirm.lower().strip()
                if _confirm not in ("y", "yes"):
                    print("User cancelled operation, abort!")
                    sys.exit(0)
        else:
            # parse job ids
            job_id_str_list = job_ids.split(",")
            for job_id in job_id_str_list:
                try:
                    job_id = job_id.strip()
                    # Validate argument: job_id
                    CommandHelper.handle_invalid_arguments(
                        ClientLibrary.validate_values_uuid(job_id, "job_id")
                    )
                    job_id_list.append(job_id)
                except ValueError as e:
                    raise errors.InvalidArguments(
                        f"Invalid job_id: {job_id}"
                    ) from e

        # call api
        status_code, reason, text, result = self.app.client.delete_jobs(
            job_id_list, force=force
        )
        json_results = CommandHelper.check_results(
            resource, "delete_job", status_code, reason, text
        )

        # print results
        jobs = []
        for result in json_results:
            jobs.append(result["job_id"])
        if jobs:
            print(
                f"The following {len(jobs)} "
                f"jobs will be deleted: {', '.join(map(str, jobs))}"
            )
        else:
            if job_ids.lower() == "all":
                print("No jobs found")
            else:
                print(f"Jobs: {job_ids} are not found or non-deletable")


class UpdateJob(Command):
    """Update job."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(dest="job_id", type=str, help="Job uuid")
        parser.add_argument(
            "--job-name",
            dest="job_name",
            type=str,
            default=None,
            help="Set job name",
        )
        parser.add_argument(
            "--description",
            dest="description",
            type=str,
            default=None,
            help="Set job description",
        )
        parser.add_argument(
            "--job-priority",
            dest="job_priority",
            type=int,
            default=None,
            help="Set job priority. Values: 1-10, Default: 5. "
            "Highest priority: 1, Lowest Priority: 10",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_id = parsed_args.job_id
        job_name = parsed_args.job_name
        description = parsed_args.description
        job_priority = parsed_args.job_priority

        # Validate argument: job_id
        if job_id:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(job_id, "job_id")
            )

        # Validate: at least one optional parameter must be set
        if not any([job_name, description, job_priority]):
            raise errors.InvalidArguments(
                "At least one optional parameter (--job-name, --description, "
                "--job-priority) must be set"
            )

        # Validate argument: job_name
        if job_name:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_name(job_name)
            )

        # Validate argument: description
        if description:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_length(
                    description,
                    "description",
                    Constant.MIN_DESCRIPTION_LENGTH,
                    Constant.MAX_DESCRIPTION_LENGTH,
                    allow_none=True,
                )
            )

        # Validate argument: job_priority
        if job_priority:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_range(
                    job_priority,
                    "job_priority",
                    Constant.MIN_JOB_PRIORITY,
                    Constant.MAX_JOB_PRIORITY,
                )
            )

        # call api
        status_code, reason, text, result = self.app.client.update_job(
            job_id=job_id,
            job_name=job_name,
            description=description,
            job_priority=job_priority,
        )
        CommandHelper.check_results(
            resource, "update_job", status_code, reason, text
        )
        print("Job updated successfully")


class SetJobResults(Command):
    """Set job results."""

    group = QcosShell.CMD_GROUP_JOB

    def get_parser(self, prog_name):
        """Get parser for this command.

        Args:
            prog_name: program name

        Returns:
            parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--results",
            dest="results",
            type=str,
            nargs="+",
            required=True,
            help="Job Results",
        )
        parser.add_argument("job_id", type=str, help="Job ID")
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_id = parsed_args.job_id
        results = parsed_args.results
        new_results_list = []

        # Validate argument: job_id
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_uuid(job_id, "job_id")
        )

        # convert results
        for result in results:
            try:
                new_results = json.loads(result)
                new_results_list.append(new_results)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    "Invalid argument: results"
                ) from exc

        # call api
        status_code, reason, text, result = self.app.client.set_job_results(
            job_id, new_results_list
        )
        CommandHelper.check_results(
            resource, "set_job_results", status_code, reason, text
        )


# User commands
class GetUserMgmt(ShowOne):
    """Get user management status."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        status_code, reason, text, result = self.app.client.get_user_mgmt()
        json_results = CommandHelper.check_results(
            resource, "get_user_mgmt", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class SetUserMgmt(Command):
    """Set user management authentication mode."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--auth-mode",
            dest="auth_mode",
            required=True,
            choices=["no", "jwt", "virtual_instance"],
            help="Authentication mode: no, jwt, or virtual_instance",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        auth_mode = parsed_args.auth_mode

        status_code, reason, text, result = self.app.client.set_user_mgmt(
            auth_mode
        )
        json_results = CommandHelper.check_results(
            resource, "set_user_mgmt", status_code, reason, text
        )
        print(f"Auth mode set to: {json_results.get('auth_mode')}")
        print(f"Message: {json_results.get('message')}")


class CreateUser(Command):
    """Create user."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("user_name", type=str, help="User name")
        parser.add_argument("password", type=str, help="Password")
        parser.add_argument(
            "--project-id",
            type=str,
            help="Project ID (UUID, optional, defaults to DEFAULT_PROJECT_ID)",
        )
        parser.add_argument(
            "--role-name",
            nargs="+",
            dest="role_names",
            default=None,
            help="Role names (can be specified multiple times)",
        )
        parser.add_argument("--description", type=str, help="Description")
        parser.add_argument(
            "--password-expiry-days",
            type=int,
            help="Password expiry days (optional, 0: never expired)",
        )
        parser.add_argument(
            "--disable",
            dest="disable_action",
            action="store_true",
            help="Disable user account upon creation",
        )
        parser.add_argument(
            "--lock",
            dest="lock_action",
            action="store_true",
            help="Lock user account upon creation",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        # Process role names: if none provided, use default "user"
        # Otherwise, collect all provided role names and remove duplicates
        role_names = parsed_args.role_names
        if not role_names:
            roles = ["user"]
        else:
            # Remove duplicates while preserving order
            roles = list(dict.fromkeys(role_names))

        # Determine is_enabled value based on enable/disable action
        is_enabled = True  # default to enabled
        if parsed_args.disable_action is True:
            is_enabled = False

        # Determine is_enabled value based on enable/disable action
        is_locked = False  # default to unlocked
        if parsed_args.lock_action is True:
            is_locked = True

        # Create user first
        status_code, reason, text, result = self.app.client.create_user(
            parsed_args.user_name,
            parsed_args.password,
            roles,
            parsed_args.description,
            parsed_args.password_expiry_days,
            is_enabled,
            is_locked,
            parsed_args.project_id,
        )
        json_results = CommandHelper.check_results(
            resource, "create_user", status_code, reason, text
        )
        print(f"User created: {json_results['user_name']}")
        print(f"User ID: {json_results['id']}")


class UpdateUser(Command):
    """Update user by ID or name.

    Can accept either a UUID or a user name as user_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the user by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "user_id", type=str, help="User ID (UUID) or user name"
        )
        parser.add_argument(
            "--role-name",
            nargs="+",
            dest="role_names",
            default=None,
            help="Role names (can be specified multiple times, default: user)",
        )
        parser.add_argument("--description", type=str, help="Description")
        parser.add_argument(
            "--password-expiry-days",
            type=int,
            help="Password expiry days (optional, 0: never expired)",
        )

        # Create mutually exclusive groups for enable/disable and lock/unlock
        enable_disable_group = parser.add_mutually_exclusive_group()
        enable_disable_group.add_argument(
            "--enable",
            dest="enable_action",
            action="store_const",
            const=True,
            default=None,
            help="Enable user account",
        )
        enable_disable_group.add_argument(
            "--disable",
            dest="disable_action",
            action="store_const",
            const=True,
            default=None,
            help="Disable user account",
        )

        lock_unlock_group = parser.add_mutually_exclusive_group()
        lock_unlock_group.add_argument(
            "--lock",
            dest="lock_action",
            action="store_const",
            const=True,
            default=None,
            help="Lock user account",
        )
        lock_unlock_group.add_argument(
            "--unlock",
            dest="unlock_action",
            action="store_const",
            const=True,
            default=None,
            help="Unlock user account",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        user_id = Client.resolve_user_id(self.app.client, parsed_args.user_id)

        # collect all provided role names and remove duplicates
        roles = None
        role_names = parsed_args.role_names
        if not role_names:
            roles = ["user"]
        else:
            # Remove duplicates while preserving order
            roles = list(dict.fromkeys(role_names))

        # Handle enable/disable action
        is_enabled = None
        if parsed_args.disable_action is True:
            is_enabled = False
        elif parsed_args.enable_action is True:
            is_enabled = True

        # Handle lock/unlock action
        is_locked = None
        if parsed_args.unlock_action is True:
            is_locked = False
        elif parsed_args.lock_action is True:
            is_locked = True

        # Prepare args and kwargs for update_user call
        args = [user_id]
        kwargs = {}
        if roles:
            kwargs["roles"] = roles
        if parsed_args.description is not None:
            kwargs["description"] = parsed_args.description
        if parsed_args.password_expiry_days is not None:
            kwargs["password_expiry_days"] = parsed_args.password_expiry_days
        if is_enabled is not None:
            kwargs["is_enabled"] = is_enabled
        else:
            kwargs["is_enabled"] = None
        if is_locked is not None:
            kwargs["is_locked"] = is_locked
        else:
            kwargs["is_locked"] = None

        status_code, reason, text, result = self.app.client.update_user(
            *args, **kwargs
        )
        CommandHelper.check_results(
            resource, "update_user", status_code, reason, text
        )
        if is_enabled is not None:
            action = "enabled" if is_enabled else "disabled"
            self.app.stdout.write(f"User {action}: {user_id}\n")
        if is_locked is not None:
            action = "locked" if is_locked else "unlocked"
            self.app.stdout.write(f"User {action}: {user_id}\n")
        self.app.stdout.write(f"User updated: {user_id}\n")


class GetUser(ShowOne):
    """Get user by ID or name.

    Can accept either a UUID or a user name as user_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the user by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "user_id",
            type=str,
            help="User ID (UUID) or user name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        user_id = Client.resolve_user_id(self.app.client, parsed_args.user_id)

        status_code, reason, text, result = self.app.client.get_user(user_id)
        json_results = CommandHelper.check_results(
            resource, "get_user", status_code, reason, text
        )

        # Format password_expiry_days: show "0 (never)" if 0
        if (
            "password_expiry_days" in json_results
            and json_results["password_expiry_days"] == 0
        ):
            expiry_days = "0 (never)"
            json_results["password_expiry_days"] = expiry_days

        # Format is_enabled: show "enabled" or "disabled"
        if "is_enabled" in json_results:
            json_results["is_enabled"] = (
                "enabled" if json_results["is_enabled"] else "disabled"
            )

        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class GetUsers(Lister):
    """Get users with optional filtering.

    Examples:
        list-users                      # List all users
        list-users --user-name admin    # Filter by user name
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--user-name",
            type=str,
            dest="user_name",
            help="Filter users by user name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        header_list = [
            "id",
            "user_name",
            "roles",
            "is_enabled",
            "is_locked",
            "password_expiry_days",
            "last_login",
            "description",
        ]

        # Build filters if user_name is provided
        filters = None
        if parsed_args.user_name:
            filters = {"user_name": parsed_args.user_name}

        status_code, reason, text, result = self.app.client.get_users(
            filters=filters
        )
        json_results = CommandHelper.check_results(
            resource, "get_users", status_code, reason, text
        )

        # Sort roles alphabetically for display and format other fields
        if json_results:
            for user_name, user_data in json_results.items():
                if "roles" in user_data and isinstance(
                    user_data["roles"], list
                ):
                    user_data["roles"] = sorted(user_data["roles"])
                # Format password_expiry_days: show "0 (never)" if 0
                if (
                    "password_expiry_days" in user_data
                    and user_data["password_expiry_days"] == 0
                ):
                    expiry_days = "0 (never)"
                    user_data["password_expiry_days"] = expiry_days
                # Format is_enabled: show "enabled" or "disabled"
                if "is_enabled" in user_data:
                    user_data["is_enabled"] = (
                        "enabled" if user_data["is_enabled"] else "disabled"
                    )

        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            self.app.stdout.write("No users found\n")
        return table_values


class DeleteUser(Command):
    """Delete user by ID or name.

    Can accept either a UUID or a user name as user_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the user by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "user_id", type=str, help="User ID (UUID) or user name"
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            dest="force",
            help="Force delete user and cascade delete related resources",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        user_id = Client.resolve_user_id(self.app.client, parsed_args.user_id)
        force = parsed_args.force
        status_code, reason, text, result = self.app.client.delete_user(
            user_id, force=force
        )
        CommandHelper.check_results(
            resource, "delete_user", status_code, reason, text
        )
        print(f"User deleted: {user_id}")


class CreateRole(Command):
    """Create role."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("role_name", type=str, help="Role name")
        parser.add_argument(
            "permissions",
            type=str,
            help="Permissions (JSON array, e.g., "
            '\'["api/path1", "api/path2"]\')',
        )
        parser.add_argument("--description", type=str, help="Role description")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        try:
            permissions = json.loads(parsed_args.permissions)
        except json.decoder.JSONDecodeError as exc:
            raise errors.InvalidArguments(
                f"Invalid permissions JSON format. "
                f'Expected: \'["path1", "path2"]\'. '
                f"Got: {parsed_args.permissions}"
            ) from exc
        status_code, reason, text, result = self.app.client.create_role(
            parsed_args.role_name, permissions, parsed_args.description
        )
        json_results = CommandHelper.check_results(
            resource, "create_role", status_code, reason, text
        )
        print(f"Role created: {json_results['role_name']}")
        print(f"Role ID: {json_results['id']}")


class GetRole(ShowOne):
    """Get role by ID or name.

    Can accept either a UUID or a role name as role_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the role by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "role_id",
            type=str,
            help="Role ID (UUID) or role name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        role_id = Client.resolve_role_id(self.app.client, parsed_args.role_id)

        status_code, reason, text, result = self.app.client.get_role(role_id)
        json_results = CommandHelper.check_results(
            resource, "get_role", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class UpdateRole(Command):
    """Update role by ID or name.

    Can accept either a UUID or a role name as role_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the role by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "role_id", type=str, help="Role ID (UUID) or role name"
        )
        parser.add_argument(
            "--permissions",
            type=str,
            dest="permissions",
            help="Permissions (JSON array, e.g., "
            '\'["api/path1", "api/path2"]\')',
        )
        parser.add_argument("--description", type=str, help="Role description")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        role_id = Client.resolve_role_id(self.app.client, parsed_args.role_id)
        permissions = None
        if parsed_args.permissions:
            try:
                permissions = json.loads(parsed_args.permissions)
            except json.decoder.JSONDecodeError as exc:
                raise errors.InvalidArguments(
                    f"Invalid permissions JSON format. "
                    f'Expected: \'["path1", "path2"]\'. '
                    f"Got: {parsed_args.permissions}"
                ) from exc
        status_code, reason, text, result = self.app.client.update_role(
            role_id, permissions, parsed_args.description
        )
        CommandHelper.check_results(
            resource, "update_role", status_code, reason, text
        )
        print(f"Role updated: {role_id}")


class DeleteRole(Command):
    """Delete role by ID or name.

    Can accept either a UUID or a role name as role_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the role by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "role_id", type=str, help="Role ID (UUID) or role name"
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        role_id = Client.resolve_role_id(self.app.client, parsed_args.role_id)

        status_code, reason, text, result = self.app.client.delete_role(
            role_id
        )
        CommandHelper.check_results(
            resource, "delete_role", status_code, reason, text
        )
        print(f"Role deleted: {role_id}")


class GetRoles(Lister):
    """Get roles with optional filtering.

    Examples:
        list-roles                      # List all roles
        list-roles --role-name admin    # Filter by role name
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--role-name",
            type=str,
            dest="role_name",
            help="Filter roles by role name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        header_list = ["id", "role_name", "permissions", "description"]

        # Build filters if role_name is provided
        filters = None
        if parsed_args.role_name:
            filters = {"role_name": parsed_args.role_name}

        status_code, reason, text, result = self.app.client.get_roles(
            filters=filters
        )
        json_results = CommandHelper.check_results(
            resource, "get_roles", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            self.app.stdout.write("No roles found\n")
        return table_values


class ChangePassword(Command):
    """Change password for user by ID or name.

    Can accept either a UUID or a user name as user_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the user by name.
    """

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "user_id", type=str, help="User ID (UUID) or user name"
        )
        parser.add_argument("old_password", type=str, help="Old password")
        parser.add_argument("new_password", type=str, help="New password")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        user_id = Client.resolve_user_id(self.app.client, parsed_args.user_id)
        status_code, reason, text, result = self.app.client.change_password(
            user_id,
            parsed_args.old_password,
            parsed_args.new_password,
        )
        CommandHelper.check_results(
            resource, "change_password", status_code, reason, text
        )
        print(f"Password changed for user: {user_id}")


class GetLoginLogs(Lister):
    """Get login logs by user ID or user name."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--user-id", type=str, default=None, help="User ID (UUID)"
        )
        parser.add_argument(
            "--user-name", type=str, default=None, help="User name"
        )
        parser.add_argument("--limit", type=int, default=100, help="Limit")
        parser.add_argument("--offset", type=int, default=0, help="Offset")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        user_id = parsed_args.user_id
        user_name = parsed_args.user_name

        # Validate that only one of user_id or user_name is provided
        if user_id is not None and user_name is not None:
            raise errors.InvalidArguments(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )

        header_list = [
            "user_name",
            "user_id",
            "project_id",
            "login_time",
            "ip_address",
            "login_status",
            "success",
            "failure_reason",
        ]

        # If --all is specified, set limit to a very large number
        limit = parsed_args.limit
        offset = parsed_args.offset

        status_code, reason, text, result = self.app.client.get_login_logs(
            user_id, user_name, limit, offset
        )
        json_results = CommandHelper.check_results(
            resource, "get_login_logs", status_code, reason, text
        )

        # Handle both list and dict formats for backward compatibility
        if isinstance(json_results, list):
            # Convert list to dict format for table display
            table_data = {}
            for i, log_entry in enumerate(json_results):
                table_data[f"Log {i + 1}"] = log_entry
            json_results = table_data

        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            self.app.stdout.write("No login logs found\n")
        return table_values


class ClearLoginLogs(Command):
    """Clear login logs (all or for a specific user)."""

    group = QcosShell.CMD_GROUP_USER

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--user-id",
            type=str,
            default=None,
            help="User ID (UUID) to clear logs for",
        )
        parser.add_argument(
            "--user-name",
            type=str,
            default=None,
            help="User name to clear logs for",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force clear without confirmation",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        user_id = parsed_args.user_id
        user_name = parsed_args.user_name
        force = parsed_args.force

        # Validate that only one of user_id or user_name is provided
        if user_id is not None and user_name is not None:
            raise errors.InvalidArguments(
                "Cannot specify both user_id and user_name. "
                "Please provide only one."
            )

        # Prepare message
        if user_id:
            msg = f"Clear login logs for user ID: {user_id}?"
        elif user_name:
            msg = f"Clear login logs for user: {user_name}?"
        else:
            msg = "Clear all login logs?"

        # Confirmation
        if not force:
            confirm = input(f"{msg} [y/N]: ")
            if confirm.lower() != "y":
                self.app.stdout.write("Operation cancelled\n")
                return None

        # Call with keyword arguments
        if user_id:
            status_code, reason, text, result = (
                self.app.client.clear_login_logs(user_id=user_id)
            )
        elif user_name:
            status_code, reason, text, result = (
                self.app.client.clear_login_logs(user_name=user_name)
            )
        else:
            status_code, reason, text, result = (
                self.app.client.clear_login_logs()
            )

        json_results = CommandHelper.check_results(
            resource, "clear_login_logs", status_code, reason, text
        )

        if json_results:
            self.app.stdout.write(
                f"Cleared {json_results.get('count', 0)} log(s)\n"
            )
            return json_results
        else:
            self.app.stdout.write("No logs to clear or operation failed\n")
            return None


# Project commands
class CreateProject(Command):
    """Create project."""

    group = QcosShell.CMD_GROUP_PROJECT

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("project_name", type=str, help="Project name")
        parser.add_argument(
            "--description",
            dest="description",
            type=str,
            default=None,
            help="Project description",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        # Validate argument: description
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_length(
                parsed_args.description,
                "description",
                Constant.MIN_DESCRIPTION_LENGTH,
                Constant.MAX_DESCRIPTION_LENGTH,
                allow_none=True,
            )
        )

        status_code, reason, text, result = self.app.client.create_project(
            parsed_args.project_name,
            parsed_args.description,
        )
        json_results = CommandHelper.check_results(
            resource, "create_project", status_code, reason, text
        )
        print(f"Project created: {json_results['name']}")
        print(f"Project ID: {json_results['id']}")


class UpdateProject(Command):
    """Update project by ID."""

    group = QcosShell.CMD_GROUP_PROJECT

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("project_id", type=str, help="Project ID (UUID)")
        parser.add_argument(
            "--name", type=str, dest="name", help="New project name"
        )
        parser.add_argument(
            "--description",
            dest="description",
            type=str,
            default=None,
            help="New project description",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        project_id = parsed_args.project_id
        name = parsed_args.name
        description = parsed_args.description

        # Validate argument: description
        CommandHelper.handle_invalid_arguments(
            ClientLibrary.validate_values_length(
                description,
                "description",
                Constant.MIN_DESCRIPTION_LENGTH,
                Constant.MAX_DESCRIPTION_LENGTH,
                allow_none=True,
            )
        )

        status_code, reason, text, result = self.app.client.update_project(
            project_id, name, description
        )
        CommandHelper.check_results(
            resource, "update_project", status_code, reason, text
        )
        print(f"Project updated: {parsed_args.project_id}")


class GetProject(ShowOne):
    """Get project by ID."""

    group = QcosShell.CMD_GROUP_PROJECT

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("project_id", type=str, help="Project ID (UUID)")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        status_code, reason, text, result = self.app.client.get_project(
            parsed_args.project_id
        )
        json_results = CommandHelper.check_results(
            resource, "get_project", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class DeleteProject(Command):
    """Delete project by ID."""

    group = QcosShell.CMD_GROUP_PROJECT

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("project_id", type=str, help="Project ID (UUID)")
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        status_code, reason, text, result = self.app.client.delete_project(
            parsed_args.project_id
        )
        CommandHelper.check_results(
            resource, "delete_project", status_code, reason, text
        )
        print(f"Project deleted: {parsed_args.project_id}")


class GetProjects(Lister):
    """Get projects with optional filtering.

    Examples:
        list-projects                       # List all projects
        list-projects --name default        # Filter by project name
    """

    group = QcosShell.CMD_GROUP_PROJECT

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--name", type=str, dest="name", help="Filter projects by name"
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        header_list = ["id", "name", "description", "created_at", "updated_at"]

        filters = None
        if parsed_args.name:
            filters = {"name": parsed_args.name}

        status_code, reason, text, result = self.app.client.get_projects(
            filters=filters
        )
        json_results = CommandHelper.check_results(
            resource, "get_projects", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list, is_dict=True
        )
        if not json_results:
            self.app.stdout.write("No projects found\n")
        return table_values


# Auth commands
class Login(Command):
    """User login to get JWT token."""

    group = QcosShell.CMD_GROUP_AUTH

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("username", type=str, help="Username")
        parser.add_argument("password", type=str, help="Password")
        parser.add_argument(
            "--access-token",
            action="store_true",
            help="Only print the access token",
        )
        parser.add_argument(
            "--refresh-token",
            action="store_true",
            help="Only print the refresh token",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        username = parsed_args.username
        password = parsed_args.password

        status_code, reason, text, result = self.app.client.login(
            username, password
        )
        json_results = CommandHelper.check_results(
            resource, "login", status_code, reason, text
        )
        access_token = json_results.get("access_token")
        refresh_token = json_results.get("refresh_token")

        if not access_token:
            raise argparse.ArgumentTypeError("Error: can't find access_token")
        if not refresh_token:
            raise argparse.ArgumentTypeError("Error: can't find refresh_token")

        self.app.client.set_token(access_token)

        if parsed_args.access_token:
            # Only print the access token
            print(access_token)
        elif parsed_args.refresh_token:
            # Only print the refresh token
            print(refresh_token)
        else:
            print(
                "Login successful.\n"
                f"Access token expires in "
                f"{json_results['expires_in']} seconds\n"
                f"Refresh token expires in "
                f"{json_results['refresh_expires_in']} seconds\n\n"
                "Set environment variables to take effect:\n"
                f"export {Constant.ENV_VAR_ACCESS_TOKEN}={access_token}\n"
                f"export {Constant.ENV_VAR_REFRESH_TOKEN}={refresh_token}"
            )


class Logout(Command):
    """User logout."""

    group = QcosShell.CMD_GROUP_AUTH

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        status_code, reason, text, result = self.app.client.logout()
        CommandHelper.check_results(
            resource, "logout", status_code, reason, text
        )
        print("Logout successful")


class RefreshToken(Command):
    """Refresh JWT token."""

    group = QcosShell.CMD_GROUP_AUTH

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--refresh-token",
            type=str,
            default=None,
            help="Specify refresh_token directly "
            "(overrides environment variable)",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        refresh_token_value = parsed_args.refresh_token or os.environ.get(
            "QCOS_REFRESH_TOKEN"
        )
        if not refresh_token_value:
            raise argparse.ArgumentTypeError(
                "Error: No refresh_token provided (use --refresh-token "
                "or set QCOS_REFRESH_TOKEN)"
            )
        status_code, reason, text, result = self.app.client.call_json_rpc(
            self.app.client.auth_url,
            "refresh_token",
            {"refresh_token": refresh_token_value},
        )
        json_results = CommandHelper.check_results(
            resource, "refresh_token", status_code, reason, text
        )
        access_token = json_results.get("access_token")
        refresh_token = json_results.get("refresh_token")
        if not access_token:
            raise argparse.ArgumentTypeError("Error: can't find access_token")
        self.app.client.set_token(access_token)
        print(
            f"Token refreshed.\n"
            f"Access token expires in "
            f"{json_results['expires_in']} seconds\n"
            f"Refresh token expires in "
            f"{json_results['refresh_expires_in']} seconds\n\n"
            "Set environment variables to take effect:\n"
            f"export {Constant.ENV_VAR_ACCESS_TOKEN}={access_token}\n"
            f"export {Constant.ENV_VAR_REFRESH_TOKEN}={refresh_token}"
        )


class Whoami(ShowOne):
    """Show current authenticated user information."""

    group = QcosShell.CMD_GROUP_AUTH

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        status_code, reason, text, result = self.app.client.get_me()
        json_results = CommandHelper.check_results(
            resource, "me", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


# Metrics commands
class GetSystemHealth(Lister):
    """Get system health status."""

    group = QcosShell.CMD_GROUP_METRICS

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        status_code, reason, text, result = self.app.client.get_system_health()
        json_results = CommandHelper.check_results(
            resource, "get_system_health", status_code, reason, text
        )

        if "component_status" not in json_results:
            raise errors.GenericException(
                "Invalid response format: 'component_status' field is missing"
            )

        header_list = ["SYSTEM", "STATUS"]

        stats_list = [
            {header_list[0]: key, header_list[1]: value}
            for key, value in json_results["component_status"].items()
        ]

        table_values = CommandHelper.get_table_list_data(
            stats_list, header_list, is_dict=False
        )

        overall_status = (
            "online"
            if json_results.get("system_healthy", False)
            else "offline"
        )
        print(f"\nOverall System Status: {overall_status}")
        print(
            f"Last Heartbeat: {json_results.get('heartbeat_timestamp', 'N/A')}"
        )
        print("\nComponent Details:")

        return table_values


class GetApiStats(Lister):
    """Get API access statistics."""

    group = QcosShell.CMD_GROUP_METRICS

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        status_code, reason, text, result = self.app.client.get_api_stats()

        json_results = CommandHelper.check_results(
            resource, "get_api_stats", status_code, reason, text
        )

        header_list = ["API_METRICS", "COUNT"]

        # Customize display field names

        stats_list = [
            {header_list[0]: key, header_list[1]: value}
            for key, value in json_results.items()
        ]

        table_values = CommandHelper.get_table_list_data(
            stats_list, header_list, is_dict=False
        )
        return table_values


class GetJobStats(Lister):
    """Get job statistics."""

    group = QcosShell.CMD_GROUP_METRICS

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        resource = self.group

        status_code, reason, text, result = self.app.client.get_job_stats()

        json_results = CommandHelper.check_results(
            resource, "get_job_stats", status_code, reason, text
        )
        header_list = ["JOB_METRICS", "COUNT"]

        stats_list = [
            {header_list[0]: key, header_list[1]: value}
            for key, value in json_results.items()
        ]

        table_values = CommandHelper.get_table_list_data(
            stats_list, header_list, is_dict=False
        )
        return table_values


# Flavor commands
class CreateFlavor(Command):
    """Create flavor (preset scheduling policy)."""

    group = QcosShell.CMD_GROUP_FLAVOR

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("name", type=str, help="Flavor name")
        parser.add_argument(
            "--project-id",
            dest="project_id",
            type=str,
            default=None,
            help="Project ID (UUID, optional, "
            "defaults to current user's project)",
        )
        parser.add_argument(
            "--description", type=str, help="Flavor description"
        )
        parser.add_argument(
            "--private",
            dest="is_public",
            action="store_false",
            default=True,
            help="Create as private flavor",
        )
        parser.add_argument(
            "--min-qubits",
            dest="min_qubits",
            type=int,
            default=None,
            help="Minimum qubits",
        )
        parser.add_argument(
            "--max-qubits",
            dest="max_qubits",
            type=int,
            default=None,
            help="Maximum qubits",
        )
        parser.add_argument(
            "--gate-fidelity-1q-min",
            dest="gate_fidelity_1q_min",
            type=float,
            default=None,
            help="Min 1q gate fidelity",
        )
        parser.add_argument(
            "--gate-fidelity-2q-min",
            dest="gate_fidelity_2q_min",
            type=float,
            default=None,
            help="Min 2q gate fidelity",
        )
        parser.add_argument(
            "--property",
            dest="property",
            nargs="+",
            type=str,
            default=None,
            help="Property in namespace:key=value format "
            "(can be specified multiple times, "
            "e.g. --property qc:test=1)",
        )
        parser.add_argument(
            "--device-groups",
            dest="device_groups",
            nargs="+",
            required=True,
            type=str,
            help="Device group names or UUIDs (at least one required)",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        name = parsed_args.name
        project_id = parsed_args.project_id
        description = parsed_args.description
        is_public = parsed_args.is_public
        min_qubits = parsed_args.min_qubits
        max_qubits = parsed_args.max_qubits
        gate_fidelity_1q_min = parsed_args.gate_fidelity_1q_min
        gate_fidelity_2q_min = parsed_args.gate_fidelity_2q_min
        property_list = parsed_args.property
        device_groups = parsed_args.device_groups

        # Resolve device group names to IDs
        device_groups = CommandHelper.resolve_device_group_ids(
            self.app.client, device_groups
        )

        # build extra_properties dict from --property
        # (namespace:key=value)
        extra_properties = {}
        if property_list:
            for item in property_list:
                if "=" not in item:
                    raise errors.InvalidArguments(
                        f"Invalid property format: '{item}'. "
                        "Must be 'namespace:key=value'. "
                        "(e.g. 'qc:devices=\"dummy,qutip_sim\"')"
                    )
                k, v = item.split("=", 1)
                k = k.strip()
                if ":" not in k:
                    raise errors.InvalidArguments(
                        f"Invalid property key: '{k}'. "
                        "Key must be in 'namespace:name' "
                        "format (e.g. 'qc:test=1')"
                    )
                extra_properties[k] = v.strip()

        status_code, reason, text, result = self.app.client.create_flavor(
            name=name,
            project_id=project_id,
            description=description,
            is_public=is_public,
            min_qubits=min_qubits,
            max_qubits=max_qubits,
            gate_fidelity_1q_min=gate_fidelity_1q_min,
            gate_fidelity_2q_min=gate_fidelity_2q_min,
            extra_properties=extra_properties if extra_properties else None,
            device_groups=device_groups,
        )
        results = CommandHelper.check_results(
            resource, "create_flavor", status_code, reason, text
        )
        print(f"Flavor created: {results.get('id', None)}")


class UpdateFlavor(Command):
    """Update flavor (preset scheduling policy).

    Can accept either a UUID or a flavor name as flavor_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the flavor by name.

    For nullable fields, use --<key> to update the value, or
    --<key>-unset to clear it. The two are mutually exclusive.
    """

    group = QcosShell.CMD_GROUP_FLAVOR

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "flavor_id", type=str, help="Flavor ID (UUID) or flavor name"
        )
        parser.add_argument("--name", type=str, help="Flavor name")
        parser.add_argument(
            "--public",
            dest="is_public",
            action="store_true",
            default=None,
            help="Set as public flavor",
        )
        parser.add_argument(
            "--private",
            dest="is_public",
            action="store_false",
            default=None,
            help="Set as private flavor",
        )
        parser.add_argument(
            "--project-id",
            dest="project_id",
            type=str,
            default=None,
            help="Project ID (UUID)",
        )
        # description: --description vs --description-unset
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--description",
            dest="description",
            type=str,
            default=None,
            help="Flavor description",
        )
        mx.add_argument(
            "--unset-description",
            dest="unset_description",
            action="store_true",
            default=False,
            help="Unset description field",
        )
        # min_qubits: --min-qubits vs --unset-min-qubits
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--min-qubits",
            dest="min_qubits",
            type=int,
            default=None,
            help="Minimum qubits",
        )
        mx.add_argument(
            "--unset-min-qubits",
            dest="unset_min_qubits",
            action="store_true",
            default=False,
            help="Unset min_qubits field",
        )
        # max_qubits: --max-qubits vs --unset-max-qubits
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--max-qubits",
            dest="max_qubits",
            type=int,
            default=None,
            help="Maximum qubits",
        )
        mx.add_argument(
            "--unset-max-qubits",
            dest="unset_max_qubits",
            action="store_true",
            default=False,
            help="Unset max_qubits field",
        )
        # gate_fidelity_1q_min
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--gate-fidelity-1q-min",
            dest="gate_fidelity_1q_min",
            type=float,
            default=None,
            help="Min 1q gate fidelity",
        )
        mx.add_argument(
            "--unset-gate-fidelity-1q-min",
            dest="unset_gate_fidelity_1q_min",
            action="store_true",
            default=False,
            help="Unset gate_fidelity_1q_min field",
        )
        # gate_fidelity_2q_min
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--gate-fidelity-2q-min",
            dest="gate_fidelity_2q_min",
            type=float,
            default=None,
            help="Min 2q gate fidelity",
        )
        mx.add_argument(
            "--unset-gate-fidelity-2q-min",
            dest="unset_gate_fidelity_2q_min",
            action="store_true",
            default=False,
            help="Unset gate_fidelity_2q_min field",
        )
        # extra_properties: --property vs --unset-extra-properties
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--property",
            dest="property",
            nargs="+",
            type=str,
            default=None,
            help="Property in namespace:key=value format "
            "(can be specified multiple times, will be merged, "
            "e.g. --property qc:test=1)",
        )
        mx.add_argument(
            "--unset-extra-properties",
            dest="unset_extra_properties",
            action="store_true",
            default=False,
            help="Unset all extra_properties",
        )
        # device_groups: --device-groups vs --unset-device-groups
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--device-groups",
            dest="device_groups",
            nargs="+",
            type=str,
            default=None,
            help="Device group names or UUIDs "
            "(replaces existing device group mappings)",
        )
        mx.add_argument(
            "--unset-device-groups",
            dest="unset_device_groups",
            action="store_true",
            default=False,
            help="Unset all device group mappings",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        flavor_id = Client.resolve_flavor_id(
            self.app.client, parsed_args.flavor_id
        )
        project_id = parsed_args.project_id

        # name and is_public are non-nullable: only update when
        # explicitly provided, otherwise omit (_UNSET).
        name = parsed_args.name if parsed_args.name is not None else _UNSET
        is_public = _UNSET
        if parsed_args.is_public is not None:
            is_public = parsed_args.is_public

        # description: update, unset, or omit
        description = _UNSET
        if parsed_args.unset_description:
            description = None
        elif parsed_args.description is not None:
            description = parsed_args.description

        # min_qubits: update, unset, or omit
        min_qubits = _UNSET
        if parsed_args.unset_min_qubits:
            min_qubits = None
        elif parsed_args.min_qubits is not None:
            min_qubits = parsed_args.min_qubits

        # max_qubits: update, unset, or omit
        max_qubits = _UNSET
        if parsed_args.unset_max_qubits:
            max_qubits = None
        elif parsed_args.max_qubits is not None:
            max_qubits = parsed_args.max_qubits

        # gate_fidelity_1q_min: update, unset, or omit
        gate_fidelity_1q_min = _UNSET
        if parsed_args.unset_gate_fidelity_1q_min:
            gate_fidelity_1q_min = None
        elif parsed_args.gate_fidelity_1q_min is not None:
            gate_fidelity_1q_min = parsed_args.gate_fidelity_1q_min

        # gate_fidelity_2q_min: update, unset, or omit
        gate_fidelity_2q_min = _UNSET
        if parsed_args.unset_gate_fidelity_2q_min:
            gate_fidelity_2q_min = None
        elif parsed_args.gate_fidelity_2q_min is not None:
            gate_fidelity_2q_min = parsed_args.gate_fidelity_2q_min

        # extra_properties: merge, unset, or omit
        extra_properties = _UNSET
        if parsed_args.unset_extra_properties:
            extra_properties = None
        elif parsed_args.property:
            extra_properties = {}
            for item in parsed_args.property:
                if "=" not in item:
                    raise errors.InvalidArguments(
                        f"Invalid property format: '{item}'. "
                        "Must be 'namespace:key=value'"
                    )
                k, v = item.split("=", 1)
                k = k.strip()
                if ":" not in k:
                    raise errors.InvalidArguments(
                        f"Invalid property key: '{k}'. "
                        "Key must be in 'namespace:name' format "
                        "(e.g. 'qc:test=1')"
                    )
                extra_properties[k] = v.strip()

        # device_groups: update, unset, or omit
        device_groups = _UNSET
        if parsed_args.unset_device_groups:
            device_groups = None
        elif parsed_args.device_groups is not None:
            device_groups = CommandHelper.resolve_device_group_ids(
                self.app.client, parsed_args.device_groups
            )

        status_code, reason, text, result = self.app.client.update_flavor(
            flavor_id=flavor_id,
            name=name,
            description=description,
            is_public=is_public,
            project_id=project_id,
            min_qubits=min_qubits,
            max_qubits=max_qubits,
            gate_fidelity_1q_min=gate_fidelity_1q_min,
            gate_fidelity_2q_min=gate_fidelity_2q_min,
            extra_properties=extra_properties,
            device_groups=device_groups,
        )
        results = CommandHelper.check_results(
            resource, "update_flavor", status_code, reason, text
        )
        print(f"Flavor updated: {results.get('id', None)}")


class GetFlavor(ShowOne):
    """Get flavor by ID or name.

    Can accept either a UUID or a flavor name as flavor_id parameter.
    If a valid UUID is provided, it will be used directly.
    Otherwise, the system will look up the flavor by name.
    """

    group = QcosShell.CMD_GROUP_FLAVOR

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "flavor_id",
            type=str,
            help="Flavor ID (UUID) or flavor name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        flavor_id = Client.resolve_flavor_id(
            self.app.client, parsed_args.flavor_id
        )

        status_code, reason, text, result = self.app.client.get_flavor(
            flavor_id
        )
        json_results = CommandHelper.check_results(
            resource, "get_flavor", status_code, reason, text
        )
        # Resolve device group IDs to names for display
        if json_results.get("device_groups"):
            json_results["device_groups"] = (
                CommandHelper.resolve_device_group_names(
                    self.app.client, json_results["device_groups"]
                )
            )
        table_values = CommandHelper.get_table_data(
            json_results, keep_value_none=True
        )
        return table_values


class GetFlavors(Lister):
    """Get flavor list."""

    group = QcosShell.CMD_GROUP_FLAVOR

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--flavor-ids",
            dest="flavor_ids",
            nargs="*",
            type=str,
            default=[],
            help="Filter by flavor IDs (space-separated UUIDs)",
        )
        parser.add_argument(
            "--flavor-name",
            dest="flavor_names",
            nargs="+",
            type=str,
            default=None,
            help="Filter by flavor name(s) (exact match, "
            "space-separated for multiple)",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        header_list = [
            "project_id",
            "id",
            "name",
            "description",
            "is_public",
            "min_qubits",
            "max_qubits",
            "gate_fidelity_1q_min",
            "gate_fidelity_2q_min",
            "device_groups",
            "extra_properties",
        ]

        filters = {}
        if parsed_args.flavor_ids:
            for flavor_id in parsed_args.flavor_ids:
                CommandHelper.handle_invalid_arguments(
                    ClientLibrary.validate_values_uuid(flavor_id, "flavor_ids")
                )
            filters["flavor_ids"] = parsed_args.flavor_ids
        if parsed_args.flavor_names:
            filters["flavor_names"] = parsed_args.flavor_names
        status_code, reason, text, result = self.app.client.get_flavors(
            filters=filters if filters else None
        )
        json_results = CommandHelper.check_results(
            resource, "get_flavors", status_code, reason, text
        )
        # Resolve device group IDs to names for display
        if json_results:
            for flavor in json_results:
                if flavor.get("device_groups"):
                    flavor["device_groups"] = (
                        CommandHelper.resolve_device_group_names(
                            self.app.client,
                            flavor["device_groups"],
                        )
                    )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list
        )
        if not json_results:
            print("No flavors found")
        return table_values


class DeleteFlavors(Command):
    """Delete flavors by IDs or names (batch).

    Accepts a comma-separated list of flavor IDs (UUIDs) or names,
    or the keyword 'all' to delete all flavors. For name inputs,
    each is resolved to an ID via the server before deletion.
    """

    group = QcosShell.CMD_GROUP_FLAVOR

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "flavor_ids",
            type=str,
            help=(
                "Flavor IDs or names to delete. "
                "Use comma-separated values for multiple, "
                "or 'all' to delete all flavors"
            ),
        )
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="assume_yes",
            action="store_true",
            help="Answer yes for all questions",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        flavor_ids_input = parsed_args.flavor_ids
        assume_yes = parsed_args.assume_yes

        flavor_id_list = []
        if flavor_ids_input.lower() == "all":
            # get all flavor ids
            status_code, reason, text, result = self.app.client.get_flavors()
            json_results = CommandHelper.check_results(
                resource, "get_flavors", status_code, reason, text
            )
            if json_results:
                for flavor_info in json_results:
                    flavor_id_list.append(flavor_info["id"])
            if not assume_yes:
                confirm = input("Are you sure to delete all flavors? (y/n) ")
                if confirm.lower().strip() not in ("y", "yes"):
                    print("User cancelled operation, abort!")
                    return
        else:
            # parse flavor ids/names
            id_str_list = flavor_ids_input.split(",")
            for item in id_str_list:
                item = item.strip()
                if not item:
                    continue
                flavor_id = Client.resolve_flavor_id(self.app.client, item)
                flavor_id_list.append(flavor_id)

        if not flavor_id_list:
            print("No flavors to delete")
            return

        if not assume_yes and flavor_ids_input.lower() != "all":
            confirm = input(
                f"Are you sure to delete {len(flavor_id_list)} "
                f"flavor(s)? (y/n) "
            )
            if confirm.lower().strip() not in ("y", "yes"):
                print("User cancelled operation, abort!")
                return

        status_code, reason, text, result = self.app.client.delete_flavors(
            flavor_id_list
        )
        json_results = CommandHelper.check_results(
            resource, "delete_flavors", status_code, reason, text
        )

        # print results
        success_count = 0
        fail_count = 0
        if json_results and isinstance(json_results, dict):
            results = json_results.get("results", [])
        elif json_results and isinstance(json_results, list):
            results = json_results
        else:
            results = []
        for r in results:
            fid = r.get("flavor_id", "unknown")
            if r.get("success"):
                success_count += 1
                print(f"Flavor {fid} deleted successfully")
            else:
                fail_count += 1
                print(
                    f"Flavor {fid} delete failed: "
                    f"{r.get('error', 'unknown error')}"
                )
        print(f"Total: {success_count} succeeded, {fail_count} failed")


# Device Group commands
class CreateDeviceGroup(Command):
    """Create device group for device classification."""

    group = QcosShell.CMD_GROUP_DEVICE_GROUP

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("name", type=str, help="Device group name")
        parser.add_argument(
            "--project-id",
            dest="project_id",
            type=str,
            default=None,
            help="Project ID (UUID, optional)",
        )
        parser.add_argument(
            "--description", type=str, help="Device group description"
        )
        parser.add_argument(
            "--private",
            dest="is_public",
            action="store_false",
            default=True,
            help="Create as private device group",
        )
        parser.add_argument(
            "--device",
            dest="device_names",
            nargs="+",
            type=str,
            default=None,
            help="Device names in this group "
            "(can be specified multiple times)",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        name = parsed_args.name
        project_id = parsed_args.project_id
        description = parsed_args.description
        is_public = parsed_args.is_public
        device_names = parsed_args.device_names
        # validate device names (at least one required)
        if not device_names:
            raise errors.InvalidArguments("At least one --device is required")
        for dn in device_names:
            # skip validation for special value _all
            if dn == "_all":
                continue
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_name(dn)
            )

        # check device existence (warn if not found)
        CommandHelper.check_device_existence(
            self.app.client, device_names, resource
        )

        status_code, reason, text, result = (
            self.app.client.create_device_group(
                name=name,
                project_id=project_id,
                description=description,
                device_names=device_names,
                is_public=is_public,
            )
        )
        results = CommandHelper.check_results(
            resource, "create_device_group", status_code, reason, text
        )
        print(f"Device group created: {results.get('id', None)}")


class UpdateDeviceGroup(Command):
    """Update device group by ID or name.

    For nullable fields, use --<key> to update the value, or
    --<key>-unset to clear it. The two are mutually exclusive.
    """

    group = QcosShell.CMD_GROUP_DEVICE_GROUP

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "group_id", type=str, help="Device group ID (UUID)"
        )
        parser.add_argument("--name", type=str, help="Device group name")
        parser.add_argument(
            "--public",
            dest="is_public",
            action="store_true",
            default=None,
            help="Set as public group",
        )
        parser.add_argument(
            "--private",
            dest="is_public",
            action="store_false",
            default=None,
            help="Set as private group",
        )
        parser.add_argument(
            "--project-id",
            dest="project_id",
            type=str,
            default=None,
            help="Project ID (UUID)",
        )
        # description: --description vs --unset-description
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--description",
            dest="description",
            type=str,
            default=None,
            help="Device group description",
        )
        mx.add_argument(
            "--unset-description",
            dest="unset_description",
            action="store_true",
            default=False,
            help="Unset description field",
        )
        # device_names: --device vs --unset-device
        mx = parser.add_mutually_exclusive_group()
        mx.add_argument(
            "--device",
            dest="device_names",
            nargs="+",
            type=str,
            default=None,
            help="Device names in this group "
            "(replaces existing list, "
            "can be specified multiple times)",
        )
        mx.add_argument(
            "--unset-device",
            dest="unset_device_names",
            action="store_true",
            default=False,
            help="Unset device names list",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        group_id = Client.resolve_device_group_id(
            self.app.client, parsed_args.group_id
        )
        project_id = parsed_args.project_id

        # name and is_public are non-nullable: only update when
        # explicitly provided, otherwise omit (_UNSET).
        name = parsed_args.name if parsed_args.name is not None else _UNSET
        is_public = _UNSET
        if parsed_args.is_public is not None:
            is_public = parsed_args.is_public

        # description: update, unset, or omit
        description = _UNSET
        if parsed_args.unset_description:
            description = None
        elif parsed_args.description is not None:
            description = parsed_args.description

        # device_names: update, unset, or omit
        device_names = _UNSET
        if parsed_args.unset_device_names:
            device_names = None
        elif parsed_args.device_names is not None:
            device_names = parsed_args.device_names
            # validate device names (skip _all)
            for dn in device_names:
                if dn == "_all":
                    continue
                CommandHelper.handle_invalid_arguments(
                    ClientLibrary.validate_name(dn)
                )
            # check device existence (warn if not found)
            CommandHelper.check_device_existence(
                self.app.client, device_names, resource
            )

        status_code, reason, text, result = (
            self.app.client.update_device_group(
                group_id=group_id,
                name=name,
                description=description,
                device_names=device_names,
                is_public=is_public,
                project_id=project_id,
            )
        )
        results = CommandHelper.check_results(
            resource, "update_device_group", status_code, reason, text
        )
        print(f"Device group updated: {results.get('id', None)}")


class GetDeviceGroup(ShowOne):
    """Get device group by ID."""

    group = QcosShell.CMD_GROUP_DEVICE_GROUP

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "group_id",
            type=str,
            help="Device group ID (UUID) or group name",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        group_id = Client.resolve_device_group_id(
            self.app.client, parsed_args.group_id
        )

        status_code, reason, text, result = self.app.client.get_device_group(
            group_id
        )
        json_results = CommandHelper.check_results(
            resource, "get_device_group", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(
            json_results, keep_value_none=True
        )
        return table_values


class GetDeviceGroups(Lister):
    """Get device group list."""

    group = QcosShell.CMD_GROUP_DEVICE_GROUP

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "--group-ids",
            dest="group_ids",
            nargs="*",
            type=str,
            default=[],
            help="Filter by device group IDs (space-separated UUIDs)",
        )
        parser.add_argument(
            "--group-name",
            dest="group_names",
            nargs="+",
            type=str,
            default=None,
            help="Filter by device group name(s) (exact match, "
            "space-separated for multiple)",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        header_list = [
            "project_id",
            "id",
            "name",
            "description",
            "device_names",
            "is_public",
        ]

        filters = {}
        if parsed_args.group_ids:
            for group_id in parsed_args.group_ids:
                CommandHelper.handle_invalid_arguments(
                    ClientLibrary.validate_values_uuid(group_id, "group_ids")
                )
            filters["group_ids"] = parsed_args.group_ids
        if parsed_args.group_names:
            filters["group_names"] = parsed_args.group_names
        status_code, reason, text, result = self.app.client.get_device_groups(
            filters=filters if filters else None
        )
        json_results = CommandHelper.check_results(
            resource, "get_device_groups", status_code, reason, text
        )
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list
        )
        if not json_results:
            print("No device groups found")
        return table_values


class DeleteDeviceGroups(Command):
    """Delete device groups by IDs or names (batch).

    Accepts a comma-separated list of device group IDs (UUIDs) or
    names, or the keyword 'all' to delete all device groups. For
    name inputs, each is resolved to an ID via the server before
    deletion.
    """

    group = QcosShell.CMD_GROUP_DEVICE_GROUP

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument(
            "group_ids",
            type=str,
            help=(
                "Device group IDs or names to delete. "
                "Use comma-separated values for multiple, "
                "or 'all' to delete all device groups"
            ),
        )
        parser.add_argument(
            "-y",
            "--yes",
            default=False,
            dest="assume_yes",
            action="store_true",
            help="Answer yes for all questions",
        )
        return parser

    def take_action(self, parsed_args):
        resource = self.group
        group_ids_input = parsed_args.group_ids
        assume_yes = parsed_args.assume_yes

        group_id_list = []
        if group_ids_input.lower() == "all":
            # get all device group ids
            status_code, reason, text, result = (
                self.app.client.get_device_groups()
            )
            json_results = CommandHelper.check_results(
                resource, "get_device_groups", status_code, reason, text
            )
            if json_results:
                for group_info in json_results:
                    group_id_list.append(group_info["id"])
            if not assume_yes:
                confirm = input(
                    "Are you sure to delete all device groups? (y/n) "
                )
                if confirm.lower().strip() not in ("y", "yes"):
                    print("User cancelled operation, abort!")
                    return
        else:
            # parse group ids/names
            id_str_list = group_ids_input.split(",")
            for item in id_str_list:
                item = item.strip()
                if not item:
                    continue
                group_id = Client.resolve_device_group_id(
                    self.app.client, item
                )
                group_id_list.append(group_id)

        if not group_id_list:
            print("No device groups to delete")
            return

        if not assume_yes and group_ids_input.lower() != "all":
            confirm = input(
                f"Are you sure to delete {len(group_id_list)} "
                f"device group(s)? (y/n) "
            )
            if confirm.lower().strip() not in ("y", "yes"):
                print("User cancelled operation, abort!")
                return

        status_code, reason, text, result = (
            self.app.client.delete_device_groups(group_id_list)
        )
        json_results = CommandHelper.check_results(
            resource, "delete_device_groups", status_code, reason, text
        )

        # print results
        success_count = 0
        fail_count = 0
        if json_results and isinstance(json_results, dict):
            results = json_results.get("results", [])
        elif json_results and isinstance(json_results, list):
            results = json_results
        else:
            results = []
        for r in results:
            gid = r.get("group_id", "unknown")
            if r.get("success"):
                success_count += 1
                print(f"Device group {gid} deleted successfully")
            else:
                fail_count += 1
                print(
                    f"Device group {gid} delete failed: "
                    f"{r.get('error', 'unknown error')}"
                )
        print(f"Total: {success_count} succeeded, {fail_count} failed")


# Register commands
command_manager = CommandManager("qcos")
# version command
command_manager.add_command("version", Version)
# auth command
command_manager.add_command("login", Login)
command_manager.add_command("logout", Logout)
command_manager.add_command("refresh-token", RefreshToken)
command_manager.add_command("whoami", Whoami)
# system command
command_manager.add_command("ping", Ping)
command_manager.add_command("system-info", SystemInfo)
command_manager.add_command("trace-mem", TraceMem)
command_manager.add_command("show-mem", ShowMem)
command_manager.add_command("gc-mem", GcMem)
# job command
command_manager.add_command("submit-job", SubmitJob)
command_manager.add_command("get-job-status", GetJobStatus)
command_manager.add_command("get-job-results", GetJobResults)
command_manager.add_command("list-jobs", GetJobs)
command_manager.add_command("cancel-jobs", CancelJobs)
command_manager.add_command("delete-jobs", DeleteJobs)
command_manager.add_command("set-job-results", SetJobResults)
command_manager.add_command("update-job", UpdateJob)
# flavor command
command_manager.add_command("create-flavor", CreateFlavor)
command_manager.add_command("update-flavor", UpdateFlavor)
command_manager.add_command("get-flavor", GetFlavor)
command_manager.add_command("list-flavors", GetFlavors)
command_manager.add_command("delete-flavors", DeleteFlavors)
# driver command
command_manager.add_command("get-driver", GetDriver)
command_manager.add_command("list-drivers", GetDrivers)
# device command
command_manager.add_command("get-device", GetDevice)
command_manager.add_command("calibrate-device", CalibrateDevice)
command_manager.add_command("get-calibrate-results", GetCalibrateResults)
command_manager.add_command("set-device-options", SetDeviceOptions)
command_manager.add_command("get-device-options", GetDeviceOptions)
command_manager.add_command("set-device-maintain-mode", SetDeviceMaintainMode)
command_manager.add_command("list-devices", GetDevices)
# device group command
command_manager.add_command("create-device-group", CreateDeviceGroup)
command_manager.add_command("update-device-group", UpdateDeviceGroup)
command_manager.add_command("get-device-group", GetDeviceGroup)
command_manager.add_command("list-device-groups", GetDeviceGroups)
command_manager.add_command("delete-device-groups", DeleteDeviceGroups)
# transpiler command
command_manager.add_command("get-transpiler", GetTranspiler)
command_manager.add_command("list-transpilers", GetTranspilers)
# project command
command_manager.add_command("create-project", CreateProject)
command_manager.add_command("get-project", GetProject)
command_manager.add_command("list-projects", GetProjects)
command_manager.add_command("update-project", UpdateProject)
command_manager.add_command("delete-project", DeleteProject)
# user command
command_manager.add_command("get-user-mgmt", GetUserMgmt)
command_manager.add_command("set-user-mgmt", SetUserMgmt)
command_manager.add_command("create-user", CreateUser)
command_manager.add_command("get-user", GetUser)
command_manager.add_command("list-users", GetUsers)
command_manager.add_command("update-user", UpdateUser)
command_manager.add_command("delete-user", DeleteUser)
command_manager.add_command("change-password", ChangePassword)
command_manager.add_command("list-login-logs", GetLoginLogs)
command_manager.add_command("clear-login-logs", ClearLoginLogs)
command_manager.add_command("create-role", CreateRole)
command_manager.add_command("get-role", GetRole)
command_manager.add_command("list-roles", GetRoles)
command_manager.add_command("update-role", UpdateRole)
command_manager.add_command("delete-role", DeleteRole)
# metrics command
command_manager.add_command("get-system-health", GetSystemHealth)
command_manager.add_command("get-api-stats", GetApiStats)
command_manager.add_command("get-job-stats", GetJobStats)


def set_debug_option(args):
    """Set debug option."""
    parser = argparse.ArgumentParser(description="", add_help=False)
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Show tracebacks on errors.",
    )
    namespace, _args = parser.parse_known_args(args)
    if namespace.debug:
        Client.verbose = True


# Source code file information
SOURCE_CODE_FILE_INFO = {
    Constant.CODE_TYPE_QASM: [
        {
            "file_type": Constant.FILE_TYPE_QASM,
            "reader": ClientLibrary.read_file,
            "parser": None,
        }
    ],
    Constant.CODE_TYPE_QASM2: [
        {
            "file_type": Constant.FILE_TYPE_QASM,
            "reader": ClientLibrary.read_file,
            "parser": None,
        }
    ],
    Constant.CODE_TYPE_QASM3: [
        {
            "file_type": Constant.FILE_TYPE_QASM,
            "reader": ClientLibrary.read_file,
            "parser": None,
        }
    ],
    Constant.CODE_TYPE_QUBO: [
        {
            "file_type": Constant.FILE_TYPE_JSON,
            "reader": ClientLibrary.read_file,
            "parser": json.loads,
        },
        {
            "file_type": Constant.FILE_TYPE_CSV,
            "reader": ClientLibrary.read_csv_file,
            "parser": json.loads,
        },
    ],
}


def get_content_by_type(code_type, file_path):
    """Get file content by file type.

    Args:
        code_type: code type
        file_path: file path

    Returns:
        file content
    """

    def get_file_types():
        """Get file types.

        Returns:
            file types
        """
        file_types = set()
        for _, code_type_info_list in SOURCE_CODE_FILE_INFO.items():
            for code_type_info in code_type_info_list:
                file_types.add(code_type_info["file_type"])
        return sorted(file_types)

    success = True
    err_msg = None
    code_type_info_list = SOURCE_CODE_FILE_INFO.get(code_type, None)
    if not code_type_info_list:
        success = False
        err_msg = (
            f"Unsupported code type: {code_type}. Valid code_types: "
            f"{', '.join(SOURCE_CODE_FILE_INFO.keys())}"
        )
        return success, err_msg, None
    file_name, file_ext = os.path.splitext(file_path)
    reader = None
    parser = None
    for code_type_info in code_type_info_list:
        file_type = code_type_info.get("file_type", "")
        if file_ext.lower() == file_type.lower():
            reader = code_type_info.get("reader", None)
            parser = code_type_info.get("parser", None)
            break
    if not reader:
        success = False
        err_msg = (
            f"Unsupported file extension: {file_ext}. "
            f"Valid code_types: {', '.join(get_file_types())}"
        )
        return success, err_msg, None
    file_content = reader(file_path)
    if parser:
        file_content = parser(file_content)
    return success, err_msg, file_content


# Application needs to be run with command line to parse.
def main():
    """Main function."""
    # arguments of cli
    argv = sys.argv[1:]
    app = QcosShell(
        description=DESCRIPTION,
        version=VERSION,
        command_manager=command_manager,
    )
    argcomplete.autocomplete(app.parser)  # enable auto-complete
    set_debug_option(argv)
    sys.exit(app.run(argv))
