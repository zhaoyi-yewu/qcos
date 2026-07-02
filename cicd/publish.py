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

"""Publish artifacts (packages, docs, docker images).

publish.py packages [--dry-run]
publish.py docs [--dry-run]
publish.py images [---dry-run] [--docker-registry DOCKER_REGISTRY]
"""

import pathlib
import subprocess
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

current_file = pathlib.Path(__file__).resolve()
current_dir = current_file.parent
parent_dir = current_dir.parent
top_dir = str(parent_dir)


class PublishException(Exception):
    """Publish Exception."""


def get_config_value(file_path, key):
    """Get config file value.

    Args:
        file_path (str): file path
        key (str): key to read

    Returns:
        str: config value
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("#", ";")):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key == key:
                        return value
        return None
    except FileNotFoundError:
        print(f"Error：file: {file_path} is not found.")
        return None
    except Exception as e:
        print(f"Error：read error.\n{e}")
        return None


def run_command(
    command,
    shell=True,
    check=True,
    capture_output=True,
    text=True,
    cwd=None,
    env=None,
):
    """Run command.

    Args:
        command: command
        shell: If true, the command will be executed through the shell
        check: check exit code
        capture_output: capture output
        text: print text
        cwd: working directory
        env: environment variables

    Returns:
        command results
    """
    try:
        results = subprocess.run(
            command,
            shell=shell,
            check=check,
            capture_output=capture_output,
            text=text,
            cwd=cwd,
            env=env,
        )
        return results
    except subprocess.CalledProcessError as e:
        err_msgs = (
            f"Command failed: {command}\nError output:\n{e.stdout}\n{e.stderr}"
        )
        raise PublishException(err_msgs)


def publish_packages(qcos_version, repository="testpypi", dry_run=False):
    """Publish packages.

    Args:
        qcos_version: QCOS version
        repository: PYPI repository name
        dry_run: dry run
    """
    dry_run_str = "(dry-run)" if dry_run else ""
    print(f"Publishing packages {dry_run_str}...")

    qcos_dist_dir = f"{top_dir}/build-scripts/output/dist"
    qcos_client_dist_dir = f"{top_dir}/build-scripts/cli/output/dist"
    repository_args = "" if dry_run else f"--repository {repository}"
    action = "check" if dry_run else "upload"
    cmds = [
        # upload wy-qcos packages
        f"twine {action} {repository_args} "
        f"{qcos_dist_dir}/wy_qcos-{qcos_version}-py3*.whl "
        f"{qcos_dist_dir}/wy_qcos-{qcos_version}.tar.gz",
        # upload wy-qcos-client packages
        f"twine {action} {repository_args} "
        f"{qcos_client_dist_dir}/wy_qcos_client-{qcos_version}-py3*.whl "
        f"{qcos_client_dist_dir}/wy_qcos_client-{qcos_version}.tar.gz",
    ]
    results = run_command(";".join(cmds))
    print(results.stdout)
    ret_code = results.returncode
    if ret_code != 0:
        err_msg = f"Failed to run cmds: {cmds}. Reason: {results.stderr}"
        raise PublishException(err_msg)

    return


def publish_docs(dry_run=False):
    """Publish docs.

    Args:
        dry_run: dry run
    """
    dry_run_str = "(dry-run)" if dry_run else ""
    print(f"Publishing docs {dry_run_str}...")
    print("ReadTheDocs will build automatically")

    return


def publish_images(qcos_version, docker_registry=None, dry_run=False):
    """Publish images.

    Args:
        qcos_version: QCOS version
        docker_registry: docker registry to publish
        dry_run: dry run
    """
    image_version = qcos_version
    images = [f"qcos:{image_version}", f"qcos-cli:{image_version}"]
    target_images = []
    for image in images:
        target_image = image
        if docker_registry:
            target_image = f"{docker_registry}/{image}"
        target_images.append((image, target_image))

    dry_run_str = "(dry-run)" if dry_run else ""
    print(f"Publishing images {dry_run_str}...")
    print(f"docker_registry: {docker_registry}")
    print(f"source images: {images}")
    print(f"target images: {target_images}")

    cmds = []
    for image, target_image in target_images:
        if image != target_image:
            # remove existing target docker image
            cmds.append(f"docker rmi -f {target_image}")

        # tag docker image
        cmds.append(f"docker tag {image} {target_image}")

        # push image to registry
        cmds.append(f"docker push {target_image}")

    if dry_run:
        print("dry-run:")
        print("\n".join(cmds))
        return

    results = run_command(";".join(cmds))
    ret_code = results.returncode
    if ret_code != 0:
        err_msg = f"Failed to run cmds: {cmds}. Reason: {results.stderr}"
        raise PublishException(err_msg)

    return


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

        subparsers = parser.add_subparsers(
            dest="command",
            required=True,
            help="Subcommand to execute (packages/docs/images)",
        )

        # create sub-command: wheels
        parser_wheels = subparsers.add_parser(
            "packages", help="Publish Python packages"
        )
        parser_wheels.add_argument(
            "--dry-run",
            action="store_true",
            help="Run checks before publishing packages",
        )

        # create sub-command: docs
        parser_docs = subparsers.add_parser(
            "docs", help="Publish documentation"
        )
        parser_docs.add_argument(
            "--dry-run",
            action="store_true",
            help="Run checks before pbefore publishing docs",
        )

        # create sub-command: images
        parser_images = subparsers.add_parser(
            "images", help="Publish docker images"
        )
        parser_images.add_argument(
            "--dry-run",
            action="store_true",
            help="Run pre-publish checks before publishing images",
        )
        parser_images.add_argument(
            "--docker-registry",
            dest="docker_registry",
            help="Run checks before pbefore publishing images",
        )

        # parse arguments
        args = parser.parse_args()

        # read version config file
        config_file = f"{top_dir}/build-scripts/version"
        qcos_version = get_config_value(config_file, "QCOS_VERSION")
        if not qcos_version:
            raise PublishException(
                "Error: QCOS_VERSION not set in config file: {config_file}"
            )

        # execute sub-commands
        if args.command == "packages":
            # publish packages
            publish_packages(qcos_version, dry_run=args.dry_run)
        elif args.command == "docs":
            # publish documentation
            publish_docs(dry_run=args.dry_run)
        elif args.command == "images":
            # publish images
            publish_images(
                qcos_version,
                docker_registry=args.docker_registry,
                dry_run=args.dry_run,
            )

        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
