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
import re
import shlex
import shutil
import subprocess
import sys
import tomlkit
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from collections import OrderedDict
from pathlib import Path

TOP_DIR = Path(__file__).resolve().parent.parent


def load_pyproject_deps(pyproject_file, sections):
    """Load dependencies from a pyproject.toml file by section names.

    The special section name "main" resolves to ``[project.dependencies]``.
    Any other name is resolved against ``[project.optional-dependencies]``.

    Args:
        pyproject_file: absolute path to the pyproject.toml file
        sections: list of section names to load

    Returns:
        deps: list of dependency requirement strings
    """
    if not os.path.exists(pyproject_file):
        raise FileNotFoundError(
            f"pyproject file not found: {pyproject_file}")

    with open(pyproject_file, encoding="utf-8") as file:
        pyproject = tomlkit.load(file)

    project = pyproject.get("project", {})
    main_deps = project.get("dependencies", [])
    optional_deps = project.get("optional-dependencies", {})

    deps = []
    for section in sections:
        if section == "main":
            deps.extend(main_deps)
        elif section in optional_deps:
            deps.extend(optional_deps[section])
        else:
            raise Exception(
                f"Section '{section}' not found in "
                f"[project.optional-dependencies] of {pyproject_file}")
    return deps


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
            if "deps_sections" not in driver_info:
                raise Exception(
                    f"[{driver_class}] 'deps_sections' must be specified")
            if "envs" not in driver_info:
                raise Exception(
                    f"[{driver_class}] 'envs' must be specified")
            if envs:
                # override envs
                if driver_class == "pypy":
                    driver_info["envs"] = [envs["default_pypy3"]]
                else:
                    driver_info["envs"] = [envs["default_python3"]]
            # resolve pyproject file path, default to ../pyproject.toml
            # relative to the venv-configs.toml directory
            deps_pyproject_file = driver_info.get(
                "deps_pyproject_file", "../pyproject.toml")
            pyproject_abs_filepath = (
                driver_deps_file_path / deps_pyproject_file).resolve()
            driver_info["deps_pyproject_file"] = str(
                pyproject_abs_filepath)
            # load dependencies from pyproject.toml sections
            deps_sections = driver_info["deps_sections"]
            deps_list = load_pyproject_deps(
                str(pyproject_abs_filepath), deps_sections)
            driver_info["deps"] = deps_list
    except Exception as e:
        raise Exception(f"Error loading configuration: {e}")

    # delete envs from skip_env_list
    if skip_env_list:
        for env in skip_env_list:
            configs.pop(env, None)

    return configs


def run_command(command, check=True, capture_output=True, text=True):
    """Run command.

    When ``command`` is a list it is executed directly (shell=False).
    When ``command`` is a string it is executed via ``bash -c`` so that
    shell control structures (set -e, if/then, source, ...) are supported
    without relying on the default system shell.

    Args:
        command: command, a list of args or a shell script string
        check: check exit code
        capture_output: capture output
        text: print text

    Returns:
        command results
    """
    if isinstance(command, str):
        command = ["bash", "-c", command]
    try:
        results = subprocess.run(
            command,
            shell=False,
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
            no_deps_option = driver_info.get("no_deps", False)
            # dependencies resolved from pyproject.toml sections
            deps_list = driver_info.get("deps", [])
            envs = driver_info.get("envs", [])
            # write deps to a temporary requirements file inside the
            # venv dir so that poetry can install them via pip
            deps_req_file = f"{driver_venv_dir}/requirements.txt"
            deps_file_content = "\n".join(deps_list)
            for env in envs:
                cmd = f"""
                set -e
                if which {env} >/dev/null 2>&1; then
                  echo -e "\\nInstalling venv: {driver_class}"
                  {env} -m venv {driver_venv_dir}
                  source {driver_venv_dir}/bin/activate
                  # write resolved dependencies to a requirements file
                  printf '%s\\n' {shlex.quote(deps_file_content)} > {deps_req_file}
                  # install dependencies via poetry-managed pip
                  pip3 install --no-cache-dir --prefer-binary {"--no-deps" if no_deps_option else ""} -r {deps_req_file}
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


def export_requirements(configs, output_dir, no_version=False):
    """Export requirements-{SECTION}.txt files for each config section.

    Reuses the dependency lists already resolved by
    ``load_driver_env_file`` (stored under the ``deps`` key). Sections
    using ``copy_from`` inherit the dependency list of their source.

    Args:
        configs: ordered config dict returned by ``load_driver_env_file``
        output_dir: directory where requirements files are written
        no_version: strip version specifiers (e.g. ``==1.0.0``) from
            each dependency line when True

    Returns:
        exported_files: list of exported file paths
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported_files = []
    for section_name, driver_info in configs.items():
        if "copy_from" in driver_info:
            source = driver_info["copy_from"]
            deps_list = configs.get(source, {}).get("deps", [])
        else:
            deps_list = driver_info.get("deps", [])

        if no_version:
            stripped_deps = []
            for dep in deps_list:
                # keep only the package name, drop version specifiers
                # such as ==, >=, <=, ~=, >, <, !=
                name = re.split(r"[=<>!~]", dep, maxsplit=1)[0]
                stripped_deps.append(name.strip())
            deps_list = stripped_deps

        req_file = output_path / f"requirements-{section_name}.txt"
        with open(req_file, "w", encoding="utf-8") as file:
            file.write("\n".join(deps_list))
            if deps_list:
                file.write("\n")
        exported_files.append(str(req_file))

    return exported_files


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
        parser.add_argument(
            "--export-requirements",
            dest="export_requirements",
            action="store_true",
            help="Export requirements-{SECTION}.txt files for each "
                 "config section to the current directory",
        )
        parser.add_argument(
            "--no-version",
            dest="no_version",
            action="store_true",
            help="Strip version specifiers (e.g. ==1.0.0) when "
                 "exporting requirements files. Only effective with "
                 "--export-requirements",
        )

        # parse arguments
        args = parser.parse_args()
        file_path = args.file_path
        venv_base_dir = args.venv_base_dir
        default_python3 = args.default_python3
        default_pypy3 = args.default_pypy3
        skip_envs = args.skip_envs
        dry_run = args.dry_run
        export_requirements_flag = args.export_requirements
        no_version = args.no_version
        skip_env_list = None

        envs = {
            "default_python3": default_python3,
            "default_pypy3": default_pypy3
        }
        if skip_envs:
            skip_env_list = skip_envs.split(",")

        configs = load_driver_env_file(file_path,
                                       envs=envs,
                                       skip_env_list=skip_env_list)

        if export_requirements_flag:
            output_dir = "requirements"
            exported = export_requirements(configs, output_dir,
                                           no_version=no_version)
            print("[Exported requirements files]")
            for req_file in exported:
                print(f"  {req_file}")
            print(f"\nExported files are located at: ./{output_dir}/requirements-*.txt")
            return 0

        if not dry_run:
            os.makedirs(venv_base_dir, exist_ok=True)
            shutil.copy2(file_path, venv_base_dir)

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
