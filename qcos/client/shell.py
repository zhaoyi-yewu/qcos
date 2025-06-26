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

import argcomplete
import argparse
import json
import sys

from cliff.app import App
from cliff.command import Command
from cliff.commandmanager import CommandManager
from cliff.lister import Lister
from cliff.show import ShowOne

from .client import Client
from qcos.common import errors
from qcos.common.config import Config
from qcos.common.constant import Constant, HttpCode
from qcos.common.library import Library


VERSION = Config.VERSION
DESCRIPTION = "QCOS command line interface"


"""
# pylint: disable=line-too-long
QCOS commands:

[Job commands]
* Submit Job
1. 测试驱动
qcos-cli submit-job --shots 10 --backend DriverDummy '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'
2. 中科酷原-汉原1 中性原子驱动, 模拟运行(dry-run)
qcos-cli submit-job --shots 10 --dry-run --backend DriverHanyuan1 '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'
3. 中科酷原-汉原1 中性原子驱动, 真实运行
qcos-cli submit-job --shots 10 --backend DriverHanyuan1 '"OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nx q[0];\nx q[1];\nmeasure q -> c;\n"'

* Get job status
qcos-cli get-job-status 00000000-0000-4000-8000-000000000001

* Get job results
qcos-cli get-job-results 00000000-0000-4000-8000-000000000001

* Get all job list
qcos-cli get-jobs

* Cancel job
qcos-cli cancel-jobs 00000000-0000-4000-8000-000000000001
qcos-cli cancel-jobs all

* Delete job
qcos-cli delete-jobs 00000000-0000-4000-8000-000000000001
qcos-cli delete-jobs all
"""


class QcosShell(App):
    """
    QCOS shell
    """
    def __init__(self, description, version, command_manager):
        super().__init__(
            description=description,
            version=version,
            command_manager=command_manager,
            deferred_help=True
        )
        self.client = None

    def initialize_app(self, argv):
        super().initialize_app(argv)
        self.client = Client(api_listen_ip=self.options.api_host,
                             api_port=self.options.api_port)

    def build_option_parser(
            self, description, version, argparse_kwargs=None):
        """
        Return an argparse option parser for this application.

        Subclasses may override this method to extend
        the parser with more global options.

        :param description: full description of the application
        :param version: version number for the application
        :param argparse_kwargs: argparse keyword arguments
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
            "-v", "--verbose",
            action="count",
            dest="verbose_level",
            default=self.DEFAULT_VERBOSE_LEVEL,
            help="Increase verbosity of output and show tracebacks on"
                 " errors. You can repeat this option.")
        parser.add_argument(
            "--debug",
            default=False,
            action="store_true",
            help="Show tracebacks on errors.",
        )
        parser.add_argument(
            "-q", "--quiet",
            action="store_const",
            dest="verbose_level",
            const=0,
            help="Suppress output except warnings and errors.")
        parser.add_argument(
            "--log-file",
            action="store",
            default=None,
            help="Specify a file to log output. Disabled by default.",
        )
        parser.add_argument(
            "--api-host",
            dest="api_host",
            default="127.0.0.1",
            help=f"Specify api server address. "
                 f"Default: {Config.API_SERVER_LISTEN_IP}",
        )
        parser.add_argument(
            "--api-port",
            dest="api_port", type=int,
            default=Config.API_SERVER_PORT,
            help=f"Specify api server port. Default: {Config.API_SERVER_PORT}",
        )
        if self.deferred_help:
            parser.add_argument(
                "-h", "--help",
                dest="deferred_help",
                action="store_true",
                help="Show help message and exit.",
            )
        else:
            parser.add_argument(
                "-h", "--help",
                action=help.HelpAction,
                nargs=0,
                default=self,  # tricky
                help="Show help message and exit.",
            )
        return parser


class HelpAction(argparse.Action):
    """
    Print help message including sub-commands

    Provide a custom action so the -h and --help options
    to the main app will print a list of the commands.

    The commands are determined by checking the CommandManager
    instance, passed in as the "default" value for the action.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        outputs = []
        max_len = 0
        app = self.default
        parser.print_help(app.stdout)
        app.stdout.write(f"\nCommands for API v{app.api_version}:\n")
        command_manager = app.command_manager
        for name, ep in sorted(command_manager):
            factory = ep.load()
            cmd = factory(self, None)
            one_liner = cmd.get_description().split("\n")[0]
            outputs.append((name, one_liner))
            max_len = max(len(name), max_len)
        for (name, one_liner) in outputs:
            app.stdout.write(f"  {name.ljust(max_len)}  {one_liner}\n")
        sys.exit(0)


class CommandHelper:
    """
    Command helper
    """

    @staticmethod
    def handle_invalid_arguments(results):
        """
        Handle invalid arguments

        :param results: results
        """
        success, err_msg = results
        if success is False:
            raise errors.InvalidArguments("\n".join(err_msg))

    @staticmethod
    def check_results(resource, name, status_code, reason, jsonrpc_response):
        """
        Check results
        raise exception if failed

        :param resource: resource
        :param name: name
        :param status_code: status code
        :param reason: reason
        :param jsonrpc_response: json-rpc response
        """
        err_msg_list = []
        if status_code in [HttpCode.SUCCESS_OK]:
            try:
                jsonrpc_response_dict = json.loads(jsonrpc_response)
                success, parsed = Client.parse_jsonrpc_response(
                    jsonrpc_response_dict)
                if success:
                    return parsed.result
                code = parsed.code
                message = parsed.message
                if parsed.data:
                    err_msgs = parsed.data.get("errors", [])
                    for err_msg in err_msgs:
                        err_msg_list.append(
                            f"{message} ({code})\n{err_msg['msg']} "
                            f", loc: {', '.join(err_msg['loc'])}")
                    err_details = parsed.data.get("details", None)
                    if err_details:
                        err_msg_list.append(
                            f"ErrorMsg: {message} ({code}). "
                            f"Details: {err_details}")
                else:
                    err_msg_list.append(f"{message} ({code})")
            except Exception as e:
                err_msg_list.append(e)
        raise errors.GenericException(
            f"Failed to process {resource}: '{name}'. "
            f"[status_code: {status_code}]\n"
            f"{','.join(err_msg_list)}.\n")

    @staticmethod
    def get_table_list_data(list_values, header_list, ignore_header_list=None):
        """
        Get list of data for showing table in cli

        :param list_values: list of values
        :param header_list: headers for table
        :param ignore_header_list: headers to ignore
        :return: list of table data
        """
        keys = {}
        _headers = []
        headers = []
        all_values = []
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
                    values.append(v)
            all_values.append(tuple(values))
        results = (tuple(headers), tuple(all_values))
        return results

    @staticmethod
    def get_table_data(values):
        """
        Get data for showing table in cli

        :param values: values
        :return: table data
        """
        keys = []
        headers = []
        _values = []
        for k, v in values.items():
            headers.append(k.upper())
            keys.append(k)
        for key in keys:
            v = values.get(key, None)
            _values.append(v)
        results = (tuple(headers), tuple(_values))
        return results


class SubmitJob(Command):
    """
    Submit job
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("-D", "--dry-run", dest="dry_run",
                            action="store_true", help="Dry run")
        parser.add_argument("--code-type", dest="code_type",
                            default=Constant.CODE_TYPE_QASM2,
                            help=f"Code Types: "
                                 f"{','.join(Constant.CODE_TYPES)}")
        parser.add_argument("--job-type", dest="job_type",
                            default=f"{Constant.JOB_TYPE_ESTIMATION}",
                            help=f"Job type: {','.join(Constant.JOB_TYPES)}")
        parser.add_argument("--job-scheduling-policy",
                            dest="job_sched_policy",
                            default=f"{Constant.DEFAULT_JOB_SCHED_POLICY}",
                            help="Set job scheduling policy")
        parser.add_argument("--job-priority",
                            dest="job_priority", type=int,
                            default=f"{Constant.DEFAULT_JOB_PRIORITY}",
                            help="Set job priority")
        parser.add_argument("--description",
                            dest="description",
                            default=None,
                            help="Set job description")
        parser.add_argument("--shots", dest="shots", type=int,
                            default=Constant.DEFAULT_SHOTS, help="Shots")
        parser.add_argument("--backend", dest="backend",
                            default=f"{Constant.DRIVER_DUMMY}",
                            help="Set backend driver name")
        parser.add_argument("--transpiler", dest="transpiler",
                            default=f"{Constant.TRANSPILER_CMSS}",
                            help="Set transpiler name")
        parser.add_argument("--optimization-level",
                            dest="optimization_level", type=int,
                            default=Constant.DEFAULT_OPTIMIZATION_LEVEL,
                            help="Set optimization level")
        parser.add_argument("source_code", help="Source code")
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        """
        resource = "Job"
        dry_run = args.dry_run
        source_code = args.source_code
        code_type = args.code_type
        job_type = args.job_type
        job_sched_policy = args.job_sched_policy
        job_priority = args.job_priority
        description = args.description
        shots = args.shots
        backend = args.backend
        transpiler = args.transpiler
        optimization_level = args.optimization_level

        # validate and convert source_code
        source_code_obj = None
        try:
            source_code_obj = json.loads(source_code)
        except json.decoder.JSONDecodeError as error:
            source_code_obj = source_code
        if isinstance(source_code_obj, list):
            for content in source_code_obj:
                if not isinstance(content, str):
                    raise errors.InvalidArguments(
                        "Invalid source_code, required schema: list[str]")
        elif isinstance(source_code_obj, str):
            source_code_list = [source_code_obj]
        else:
            raise errors.InvalidArgumentsException(
                "Invalid source_code, required schema: list[str]")
        if not source_code_list:
            raise errors.InvalidArguments("Empty source_code is not allowed")

        # Validate argument: code_type
        CommandHelper.handle_invalid_arguments(Library.validate_values_enum(
            code_type, "code_type", Constant.CODE_TYPES))

        # Validate argument: job_type
        CommandHelper.handle_invalid_arguments(Library.validate_values_enum(
            job_type, "job_type", Constant.JOB_TYPES))

        # Validate argument: job_sched_policy
        CommandHelper.handle_invalid_arguments(Library.validate_values_enum(
            job_sched_policy, "job_sched_policy",
            Constant.JOB_SCHED_POLICIES))

        # Validate argument: job_priority
        CommandHelper.handle_invalid_arguments(Library.validate_values_range(
            job_priority, "job_priority",
            Constant.MIN_JOB_PRIORITY, Constant.MAX_JOB_PRIORITY))

        # Validate argument: job_priority
        CommandHelper.handle_invalid_arguments(Library.validate_values_length(
            description, "description",
            Constant.MIN_DESCRIPTION_LENGTH, Constant.MAX_DESCRIPTION_LENGTH,
            allow_empty=True))

        # Validate argument: shots
        CommandHelper.handle_invalid_arguments(Library.validate_values_range(
            shots, "shots",
            Constant.MIN_SHOTS, Constant.MAX_SHOTS))

        # Validate argument: transpiler
        CommandHelper.handle_invalid_arguments(Library.validate_values_enum(
            transpiler, "transpiler", Constant.TRANSPILER_TYPES))

        # Validate argument: optimization_level
        CommandHelper.handle_invalid_arguments(Library.validate_values_range(
            optimization_level, "optimization_level",
            Constant.MIN_OPTIMIZATION_LEVEL, Constant.MAX_OPTIMIZATION_LEVEL))

        # call api
        status_code, reason, text, result = self.app.client.submit_job(
            source_code_list,
            code_type=code_type,
            job_type=job_type,
            job_sched_policy=job_sched_policy,
            job_priority=job_priority,
            description=description,
            shots=shots,
            backend=backend,
            transpiler=transpiler,
            optimization_level=optimization_level,
            dry_run=dry_run)
        results = CommandHelper.check_results(
            resource, "submit_job", status_code, reason, text)
        print(f"Job ID: {results.get('job_id', None)}")


class GetJobStatus(ShowOne):
    """
    Get job status
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_id", type=str, help="Job ID")
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        :return: results of command
        """
        resource = "Job"
        job_id = args.job_id

        # Validate argument: job_id
        CommandHelper.handle_invalid_arguments(Library.validate_values_uuid(
            job_id, "job_id"))

        # call api
        status_code, reason, text, result = \
            self.app.client.get_job_status(job_id)
        json_results = CommandHelper.check_results(
            resource, "get_job_status", status_code, reason, text)
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class GetJobResults(ShowOne):
    """
    Get job results
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_id", type=str, help="Job ID")
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        :return: results of command
        """
        resource = "Job"
        job_id = args.job_id

        # Validate argument: job_id
        CommandHelper.handle_invalid_arguments(Library.validate_values_uuid(
            job_id, "job_id"))

        # call api
        status_code, reason, text, result = \
            self.app.client.get_job_results(job_id)
        json_results = CommandHelper.check_results(
            resource, "get_job_results", status_code, reason, text)
        table_values = CommandHelper.get_table_data(json_results)
        return table_values


class GetJobs(Lister):
    """
    Get jobs
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        """
        resource = "Job"
        header_list = ["job_id", "job_status", "backend", "job_type",
                       "shots", "creation_date"]

        # call api
        status_code, reason, text, result = self.app.client.get_jobs()
        json_results = CommandHelper.check_results(
            resource, "get_jobs", status_code, reason, text)
        table_values = CommandHelper.get_table_list_data(
            json_results, header_list)
        if not json_results:
            print("No jobs found")
        return table_values


class CancelJobs(Command):
    """
    Cancel job
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_ids", help="Job IDs")
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        """
        resource = "Job"
        job_ids = args.job_ids

        job_id_list = []
        if job_ids.lower() == "all":
            # get all job ids
            status_code, reason, text, result = self.app.client.get_jobs()
            json_results = CommandHelper.check_results(
                resource, "get_jobs", status_code, reason, text)
            if json_results:
                for job_info in json_results:
                    job_id = job_info["job_id"]
                    job_id_list.append(job_id)
        else:
            # parse job ids
            job_id_str_list = job_ids.split(",")
            for job_id in job_id_str_list:
                try:
                    job_id = job_id.strip()
                    # Validate argument: job_id
                    CommandHelper.handle_invalid_arguments(
                        Library.validate_values_uuid(
                            job_id, "job_id"))
                    job_id_list.append(job_id)
                except ValueError as e:
                    raise errors.InvalidArguments(
                        f"Invalid job_id: {job_id}.") from e

        # call api
        status_code, reason, text, result = \
            self.app.client.cancel_jobs(job_id_list)
        json_results = CommandHelper.check_results(
            resource, "cancel_job", status_code, reason, text)

        # print results
        jobs = []
        for result in json_results:
            jobs.append(result["job_id"])
        if jobs:
            print(f"The following {len(jobs)} "
                  f"jobs will be cancelled: {', '.join(map(str, jobs))}")
        else:
            print(f"No job: {job_ids} is found")


class DeleteJobs(Command):
    """
    Delete job
    """

    def get_parser(self, prog_name):
        """
        Get parser for this command

        :param prog_name: program name
        :return: parser
        """
        parser = super().get_parser(prog_name)
        parser.add_argument("job_ids", help="Job IDs")
        return parser

    def take_action(self, args):
        """
        Take action for command line arguments

        :param args: command line arguments
        """
        resource = "Job"
        job_ids = args.job_ids

        job_id_list = []
        if job_ids.lower() == "all":
            # get all job ids
            status_code, reason, text, result = self.app.client.get_jobs()
            json_results = CommandHelper.check_results(
                resource, "get_jobs", status_code, reason, text)
            if json_results:
                for job_info in json_results:
                    job_id = job_info["job_id"]
                    job_id_list.append(job_id)
        else:
            # parse job ids
            job_id_str_list = job_ids.split(",")
            for job_id in job_id_str_list:
                try:
                    job_id = job_id.strip()
                    # Validate argument: job_id
                    CommandHelper.handle_invalid_arguments(
                        Library.validate_values_uuid(
                            job_id, "job_id"))
                    job_id_list.append(job_id)
                except ValueError as e:
                    raise errors.InvalidArguments(
                        f"Invalid job_id: {job_id}") from e

        # call api
        status_code, reason, text, result = \
            self.app.client.delete_jobs(job_id_list)
        json_results = CommandHelper.check_results(
            resource, "delete_job", status_code, reason, text)

        # print results
        jobs = []
        for result in json_results:
            jobs.append(result["job_id"])
        if jobs:
            print(f"The following {len(jobs)} "
                  f"jobs will be deleted: {', '.join(map(str, jobs))}")
        else:
            print(f"No job: {job_ids} is found")


# Register commands
command_manager = CommandManager("qcos")
command_manager.add_command("submit-job", SubmitJob)
command_manager.add_command("get-job-status", GetJobStatus)
command_manager.add_command("get-job-results", GetJobResults)
command_manager.add_command("get-jobs", GetJobs)
command_manager.add_command("cancel-jobs", CancelJobs)
command_manager.add_command("delete-jobs", DeleteJobs)


def set_debug_option(args):
    """
    Set debug option
    """
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


# Application needs to be run with command line to parse.
def main(argv=sys.argv[1:]):
    """
    Main function

    :param argv: arguments
    """
    app = QcosShell(
        description=DESCRIPTION,
        version=VERSION,
        command_manager=command_manager
    )
    argcomplete.autocomplete(app.parser)  # enable auto-complete
    set_debug_option(argv)
    sys.exit(app.run(argv))
