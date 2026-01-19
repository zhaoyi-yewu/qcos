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

import argcomplete
import argparse
import json
import os
import sys

from cliff import help
from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister
from cliff.show import ShowOne

from .client import Client
from .common import args_schema, errors
from .common.client_library import ClientLibrary
from .common.constant import Constant, HttpCode
from .common.qcos_version import QcosVersion

VERSION = QcosVersion.VERSION
DESCRIPTION = "QCOS command line interface"


class QcosShell(App):
    """QCOS shell."""

    CMD_GROUP_DEFAULT = "Default"
    CMD_GROUP_DRIVER = "Driver"
    CMD_GROUP_DEVICE = "Device"
    CMD_GROUP_TRANSPILER = "Transpiler"
    CMD_GROUP_JOB = "Job"
    CMD_GROUP_SYSTEM = "System"
    CMD_GROUP_VERSION = "Version"
    CMD_GROUPS = [
        CMD_GROUP_DEFAULT,
        CMD_GROUP_VERSION,
        CMD_GROUP_DRIVER,
        CMD_GROUP_DEVICE,
        CMD_GROUP_TRANSPILER,
        CMD_GROUP_SYSTEM,
        CMD_GROUP_JOB,
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
        if err:
            cmd.app.stderr.write(f"An error occurred: {err}\n")

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

        self.client = Client(
            api_server_ip=api_server_ip,
            api_server_port=api_server_port,
            use_ssl=use_ssl,
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            ssl_cafile=ssl_cafile,
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
    def get_table_data(values):
        """Get data for showing table in cli.

        Args:
            values: values

        Returns:
            table data
        """
        keys = []
        headers = []
        _values = []
        for k, v in values.items():
            if v is None:  # remove None values
                continue
            headers.append(k.upper())
            keys.append(k)
        for key in keys:
            v = values.get(key, None)
            _values.append(v)
        results = (tuple(headers), tuple(_values))
        return results


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
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group

        status_code, reason, text, result = self.app.client.version()
        json_results = CommandHelper.check_results(
            resource, "version", status_code, reason, text
        )
        caps = json_results["capabilities"]
        print(f"Server version: {json_results['version']}")
        print(f"API version: {json_results['api_version']}")
        print(
            f"Supported API versions: {json_results['supported_api_versions']}"
        )
        print(f"Platform version: {json_results['platform_version']}")
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
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        device_name = parsed_args.device_name

        status_code, reason, text, result = self.app.client.get_device(
            device_name
        )
        json_results = CommandHelper.check_results(
            resource, "get_device", status_code, reason, text
        )
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


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
            help="Set job priority",
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
        default_backend = Constant.DEVICE_DUMMY
        parser.add_argument(
            "--backend",
            dest="backend",
            default=default_backend,
            help=f"Set backend device name. eg: {default_backend}",
        )
        parser.add_argument(
            "--driver-options",
            dest="driver_options",
            type=str,
            default=None,
            help="Set driver options",
        )
        default_transpiler = Constant.TRANSPILER_CMSS
        parser.add_argument(
            "--transpiler",
            dest="transpiler",
            default=default_transpiler,
            help=f"Set transpiler name. eg. {default_transpiler}",
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
        driver_options = parsed_args.driver_options
        transpiler = parsed_args.transpiler
        transpiler_options = parsed_args.transpiler_options
        profiling = parsed_args.profiling
        callbacks = parsed_args.callbacks

        # request capabilities
        status_code, reason, text, result = self.app.client.version()
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
                ClientLibrary.validate_schema(
                    job_name, args_schema.NAME_SCHEMA, allow_none=True
                )
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
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        header_list = [
            "job_id",
            "job_name",
            "job_status",
            "progress",
            "backend",
            "job_type",
            "shots",
            "creation_date",
            "end_date",
        ]

        # call api
        status_code, reason, text, result = self.app.client.get_jobs()
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
                        f"Invalid job_id: {job_id}"
                    ) from e

        # call api
        status_code, reason, text, result = self.app.client.delete_jobs(
            job_id_list
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
        parser.add_argument(
            "--job-id", dest="job_id", type=str, help="Job uuid"
        )
        parser.add_argument(
            "--job-priority",
            dest="job_priority",
            type=int,
            default=f"{Constant.DEFAULT_JOB_PRIORITY}",
            help="Set job priority",
        )
        return parser

    def take_action(self, parsed_args):
        """Take action for command line arguments.

        Args:
            parsed_args: command line arguments
        """
        resource = self.group
        job_id = parsed_args.job_id
        job_priority = parsed_args.job_priority

        # Validate argument: job_id
        if job_id:
            CommandHelper.handle_invalid_arguments(
                ClientLibrary.validate_values_uuid(job_id, "job_id")
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

        # call api
        status_code, reason, text, result = self.app.client.update_job(
            job_id=job_id, job_priority=job_priority
        )
        json_results = CommandHelper.check_results(
            resource, "update_job", status_code, reason, text
        )

        # print results
        job = json_results["job_id"]
        if job:
            print(
                f"The following job {job} priority will be "
                f"updated to {job_priority}"
            )
        else:
            if not json_results:
                print("Job not found")


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


# Register commands
command_manager = CommandManager("qcos")
# version command
command_manager.add_command("version", Version)
# system command
command_manager.add_command("ping", Ping)
command_manager.add_command("system-info", SystemInfo)
# job command
command_manager.add_command("submit-job", SubmitJob)
command_manager.add_command("get-job-status", GetJobStatus)
command_manager.add_command("get-job-results", GetJobResults)
command_manager.add_command("list-jobs", GetJobs)
command_manager.add_command("cancel-jobs", CancelJobs)
command_manager.add_command("delete-jobs", DeleteJobs)
command_manager.add_command("set-job-results", SetJobResults)
command_manager.add_command("update-job", UpdateJob)
# driver command
command_manager.add_command("get-driver", GetDriver)
command_manager.add_command("list-drivers", GetDrivers)
# device command
command_manager.add_command("get-device", GetDevice)
command_manager.add_command("list-devices", GetDevices)
# transpiler command
command_manager.add_command("get-transpiler", GetTranspiler)
command_manager.add_command("list-transpilers", GetTranspilers)


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
