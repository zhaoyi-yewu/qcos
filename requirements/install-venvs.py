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

"""
Install venv environments
"""

import os
import subprocess
import sys
import yaml
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path

TOP_DIR = Path(__file__).resolve().parent.parent


def load_yaml_file(file_path):
    """Load and validate YAML configuration file.

    Args:
        file_path: yaml file path

    Returns:
        configs: config data
    """

    driver_deps_file_path = Path(file_path).parent
    configs = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(
            f"Configuration file not found: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            raw_data = yaml.safe_load(file)
            configs = raw_data if raw_data is not None else {}

        for driver_class, driver_info in configs.items():
            deps_filepath = driver_info["deps_filepath"]
            deps_abs_filepath = (
                        driver_deps_file_path / deps_filepath).resolve()
            driver_info["deps_filepath"] = deps_abs_filepath
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"YAML parsing error: {e}")
    except Exception as e:
        raise Exception(f"Error loading configuration: {e}")

    return configs


def run_command(command, check=True, capture_output=True, text=True):
    """Run command.

    Args:
        command: command
        check: check exit code
        capture_output: capture output
        text: print text

    Returns:
        command results
    """
    try:
        results = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=capture_output,
            text=text,
        )
        return results
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}")
        print(f"Error output: {e.stderr}")
        raise


def install_venv(configs, venv_base_dir, debug=True):
    """Install venv.

    Args:
        configs: configs
        venv_base_dir: venv base dir
        debug: debug, print commands and results

    Returns:
        results
    """
    cmds = []
    for driver_class, driver_info in configs.items():
        driver_venv_dir = f"{venv_base_dir}/{driver_class}"
        deps_filepath = driver_info["deps_filepath"]
        envs = driver_info["envs"]
        for env in envs:
            cmds.append(f"echo -e '\nInstalling venv: {driver_class}'")
            cmds.append(f"{env} -m venv {driver_venv_dir}")
            cmds.append(f"source {driver_venv_dir}/bin/activate")
            cmds.append(f"pip3 --no-cache-dir install -r {deps_filepath}")
            cmds.append(f"deactivate")
    if debug:
        print("[Install venv for drivers]")
        print("\n".join(cmds))
    results = run_command(";".join(cmds), check=False)
    if debug:
        print(f"{results.stdout}\n{results.stderr}")

    return results.returncode


def main(argv=None):
    """main"""

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f"""{program_shortdesc}

USAGE
"""

    try:
        # config parser
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "-f",
            "--file",
            dest="file_path",
            default=f"{TOP_DIR}/requirements/venv-configs.yaml",
            help="Driver dependencies config file path",
        )
        parser.add_argument(
            "-V",
            "--venv-dir",
            dest="venv_base_dir",
            default="/var/lib/qcos/venv-driver",
            help="Driver venv base dir",
        )

        # parse arguments
        args = parser.parse_args()
        file_path = args.file_path
        venv_base_dir = args.venv_base_dir
        os.makedirs(venv_base_dir, exist_ok=True)

        configs = load_yaml_file(file_path)
        print(f"Configs: \n{configs}")
        ret_code = install_venv(configs, venv_base_dir, debug=True)
        err_code = ret_code

        return err_code
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
