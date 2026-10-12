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

# Whitelist for config section names that are embedded into generated
# shell scripts; anything else is rejected at config load time
SAFE_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+")
# Command substitution vectors rejected in post_scripts entries: a
# backtick or "$(" would let a tampered config inject arbitrary commands
CMD_SUBSTITUTION_PATTERN = re.compile(r"`|\$\(")


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
            # reject section names with shell metacharacters early:
            # they are embedded into generated shell scripts later
            if not SAFE_NAME_PATTERN.fullmatch(str(driver_class)):
                raise Exception(
                    f"Invalid driver name: {driver_class!r}. Only "
                    "letters, digits, '-' and '_' are allowed."
                )
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


def validate_post_script(script):
    """Validate a post-install script entry from the driver config.

    Entries are shell command fragments by design, so only command
    substitution vectors are rejected: backticks and ``$(...)`` would
    let a tampered configuration file smuggle arbitrary commands into
    the generated shell script.

    Args:
        script: post script entry to validate

    Returns:
        script: the validated script string

    Raises:
        ValueError: when the entry is not a non-empty string or
            contains forbidden shell metacharacters
    """
    if not isinstance(script, str) or not script.strip():
        raise ValueError(
            f"Invalid post_scripts entry: {script!r}. Entries must be "
            "non-empty strings."
        )
    if CMD_SUBSTITUTION_PATTERN.search(script):
        raise ValueError(
            f"Invalid post_scripts entry: {script!r}. Command "
            "substitution (backticks or '$(') is not allowed."
        )
    return script


def build_post_scripts_block(driver_venv_dir, post_scripts):
    """Build shell commands to run post-install scripts in a venv.

    The venv path is escaped with ``shlex.quote()`` before being
    interpolated into the shell template, and every ``post_scripts``
    entry is validated by ``validate_post_script()``, so neither a
    crafted path nor a tampered config entry can inject arbitrary
    shell commands.

    The generated block activates the venv, changes into the venv
    directory so that relative paths inside ``post_scripts`` resolve
    against the venv root, then executes each script in order and
    finally deactivates the venv.

    Args:
        driver_venv_dir: absolute path to the venv directory
        post_scripts: list of shell script strings to run in order

    Returns:
        cmd: shell script string that runs the post scripts, or empty
             string when ``post_scripts`` is falsy
    """
    if not post_scripts:
        return ""
    # escape the venv path so shell metacharacters in it cannot
    # turn the generated script into command injection
    safe_venv = shlex.quote(driver_venv_dir)
    # dedent each script line and join to build the body
    body_lines = []
    for index, script in enumerate(post_scripts, start=1):
        validate_post_script(script)
        body_lines.append(f"  # post_scripts[{index}]: {script}")
        body_lines.append(f"  {script}")
    body = "\n".join(body_lines)
    cmd = f"""
        if [ -f {safe_venv}/bin/activate ]; then
          source {safe_venv}/bin/activate
          cd {safe_venv}
          echo -e "\\nRunning post_scripts in" {safe_venv}
{body}
          deactivate
        else
          echo -e "\\npost_scripts skipped: venv not found"
          echo -e "  path:" {safe_venv}
        fi
    """
    return cmd


def install_venv(configs, venv_base_dir, debug=True, dry_run=False):
    """Install venv.

    When a config section defines a ``post_scripts`` key (list of shell
    command strings), each command is executed in order inside the
    venv directory after the dependencies have been installed. Every
    path is escaped with ``shlex.quote()`` before it is embedded into
    the generated shell script.

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
        # escape the venv path so metacharacters in it cannot turn
        # the generated script into command injection
        safe_venv = shlex.quote(driver_venv_dir)
        copy_from = driver_info.get("copy_from", None)
        if copy_from:
            src_dir = f"{venv_base_dir}/{copy_from}"
            safe_src = shlex.quote(src_dir)
            cmd = f"""
            echo -e "\\nInstalling venv: {driver_class} - link"
            [ ! -L {safe_venv} ] && ln -s {safe_src} {safe_venv}
            """
            cmds.append(cmd)
        else:
            no_deps_option = driver_info.get("no_deps", False)
            # dependencies resolved from pyproject.toml sections
            deps_list = driver_info.get("deps", [])
            envs = driver_info.get("envs", [])
            # post-install scripts to run inside the venv directory
            post_scripts = driver_info.get("post_scripts", [])
            # write deps to a temporary requirements file inside the
            # venv dir so that poetry can install them via pip
            deps_req_file = f"{driver_venv_dir}/requirements.txt"
            safe_req_file = shlex.quote(deps_req_file)
            deps_file_content = "\n".join(deps_list)
            for env in envs:
                safe_env = shlex.quote(env)
                cmd = f"""
                set -e
                if which {safe_env} >/dev/null 2>&1; then
                  echo -e "\\nInstalling venv: {driver_class}"
                  {safe_env} -m venv {safe_venv}
                  source {safe_venv}/bin/activate
                  # write resolved dependencies to a requirements file
                  printf '%s\\n' {shlex.quote(deps_file_content)} > {safe_req_file}
                  # install dependencies via poetry-managed pip
                  pip3 install --no-cache-dir --prefer-binary {"--no-deps" if no_deps_option else ""} -r {safe_req_file}
                  deactivate
                else
                  echo -e "\\nInstalling venv: {driver_class} - skipped"
                  echo -e "\\nCan't find env:" {safe_env}
                fi
                """
                cmds.append(cmd)
            # run post_scripts after dependencies are installed
            post_cmd = build_post_scripts_block(driver_venv_dir, post_scripts)
            if post_cmd:
                cmds.append(post_cmd)
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
        parser.add_argument(
            "--name",
            dest="name",
            default=None,
            help="Only install venv for the specified config name "
                 "(e.g. DriverQuafu, DriverQutipSim). "
                 "Comma-separated list is supported.",
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

        # filter by --name if specified
        if args.name:
            name_list = [
                n.strip() for n in args.name.split(",")
                if n.strip()
            ]
            configs = OrderedDict(
                (k, v) for k, v in configs.items()
                if k in name_list
            )
            if not configs:
                all_names = list(
                    load_driver_env_file(
                        file_path, envs=envs
                    ).keys()
                )
                print(
                    f"Error: no config matched --name "
                    f"'{args.name}'. Available: "
                    f"{', '.join(all_names)}"
                )
                return 1

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
