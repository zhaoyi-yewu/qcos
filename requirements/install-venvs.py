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

"""Install venv environments."""

import os
import shutil
import subprocess
import sys
import tomlkit
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import OrderedDict
from pathlib import Path

TOP_DIR = Path(__file__).resolve().parent.parent


def load_driver_env_file(config_file, envs=None, skip_env_list=None):
    """Load and validate driver env configuration file.

    Args:
        config_file: config file path
        envs: envs
        skip_env_list: env list to skip

    Returns:
        configs: config data
    """
    driver_deps_file_path = Path(config_file).parent
    _configs = {}
    configs = {}
    if not os.path.exists(config_file):
        raise FileNotFoundError(
            f"Configuration file not found: {config_file}")

    try:
        with open(config_file, encoding="utf-8") as file:
            _configs = tomlkit.load(file)

        # sort dict
        # dicts contain key: "copy_from" will put at the end of configs
        non_copy_items = []
        copy_items = []

        for key, value in _configs.items():
            if isinstance(value, dict) and "copy_from" in value:
                copy_from_value = value["copy_from"]
                if copy_from_value not in _configs:
                    raise Exception(
                        f"Invalid copy_from: {copy_from_value} in [{key}]")
                ref_driver_name = copy_from_value
                ref_driver = _configs[ref_driver_name]
                if "copy_from" in ref_driver:
                    raise Exception(
                        f"Invalid copy_from: {ref_driver_name} in [{key}]. "
                        f"Can't reference the driver: {ref_driver_name}"
                    )
                copy_items.append((key, value))
            else:
                non_copy_items.append((key, value))

        sorted_items = non_copy_items + copy_items
        configs = OrderedDict(sorted_items)
        for driver_class, driver_info in configs.items():
            if "copy_from" in driver_info:
                continue
            if "deps_filepaths" not in driver_info:
                raise Exception(
                    f"[{driver_class}] 'deps_filepaths' must be specified")
            if "envs" not in driver_info:
                raise Exception(
                    f"[{driver_class}] 'envs' must be specified")
            if envs:
                # override envs
                if driver_class == "pypy":
                    driver_info["envs"] = [envs["default_pypy3"]]
                else:
                    driver_info["envs"] = [envs["default_python3"]]
            deps_filepaths = driver_info["deps_filepaths"]
            deps_filepaths_list = []
            for deps_filepath in deps_filepaths:
                deps_abs_filepath = (
                            driver_deps_file_path / deps_filepath).resolve()
                deps_filepaths_list.append(str(deps_abs_filepath))
            driver_info["deps_filepaths"] = deps_filepaths_list
    except Exception as e:
        raise Exception(f"Error loading configuration: {e}")

    # delete envs from skip_env_list
    if skip_env_list:
        for env in skip_env_list:
            configs.pop(env, None)

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


def install_venv(configs, venv_base_dir, debug=True, dry_run=False):
    """Install venv.

    Args:
        configs: configs
        venv_base_dir: venv base dir
        debug: debug, print commands and results
        dry_run: dry run

    Returns:
        results
    """
    cmds = []
    for driver_class, driver_info in configs.items():
        driver_venv_dir = f"{venv_base_dir}/{driver_class}"
        copy_from = driver_info.get("copy_from", None)
        if copy_from:
            src_dir = f"{venv_base_dir}/{copy_from}"
            dst_dir = driver_venv_dir
            cmd = f"""
            echo -e "\\nInstalling venv: {driver_class} - link"
            [ ! -L "{dst_dir}" ] && ln -s {src_dir} {dst_dir}
            """
            cmds.append(cmd)
        else:
            no_deps_cmd = ""
            no_deps_option = driver_info.get("no_deps", False)
            if no_deps_option:
                no_deps_cmd = "--no-deps"
            deps_path_list = driver_info["deps_filepaths"]
            deps_path_args = f"-r {' -r '.join(deps_path_list)}"
            envs = driver_info.get("envs", [])
            for env in envs:
                cmd = f"""
                set -e
                if which {env} >/dev/null 2>&1; then
                  echo -e "\\nInstalling venv: {driver_class}"
                  {env} -m venv {driver_venv_dir}
                  source {driver_venv_dir}/bin/activate
                  pip3 install --no-cache-dir {no_deps_cmd} --prefer-binary {deps_path_args}
                  deactivate
                else
                  echo -e "\\nInstalling venv: {driver_class} - skipped"
                  echo -e "\\nCan't find env: {env}"
                fi
                """
                cmds.append(cmd)
    if debug:
        print("\n[Install venv for drivers]")
        print("\n".join(cmds))
    if dry_run:
        return 0
    results = run_command("\n".join(cmds), check=False)
    if debug:
        print(f"{results.stdout}\n{results.stderr}")

    return results.returncode


def main(argv=None):
    """Main function."""
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
            default=f"{TOP_DIR}/requirements/venv-configs.toml",
            help="Driver dependencies config file path",
        )
        parser.add_argument(
            "-V",
            "--venv-dir",
            dest="venv_base_dir",
            default="/var/lib/qcos/venv",
            help="Driver venv base dir",
        )
        parser.add_argument(
            "--default-python3",
            dest="default_python3",
            default="python3",
            help="Default python3",
        )
        parser.add_argument(
            "--default-pypy3",
            dest="default_pypy3",
            default="pypy3",
            help="Default pypy3",
        )
        parser.add_argument(
            "--skip-envs",
            dest="skip_envs",
            default=None,
            help="Envs to skip",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Dry run",
        )

        # parse arguments
        args = parser.parse_args()
        file_path = args.file_path
        venv_base_dir = args.venv_base_dir
        default_python3 = args.default_python3
        default_pypy3 = args.default_pypy3
        skip_envs = args.skip_envs
        dry_run = args.dry_run
        skip_env_list = None

        if not dry_run:
            os.makedirs(venv_base_dir, exist_ok=True)
            shutil.copy2(file_path, venv_base_dir)

        envs = {
            "default_python3": default_python3,
            "default_pypy3": default_pypy3
        }
        if skip_envs:
            skip_env_list = skip_envs.split(",")

        configs = load_driver_env_file(file_path,
                                       envs=envs,
                                       skip_env_list=skip_env_list)
        print(f"[Configs: \n{configs}]")
        ret_code = install_venv(configs, venv_base_dir,
                                debug=True, dry_run=dry_run)
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
