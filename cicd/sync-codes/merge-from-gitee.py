#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright© 2024-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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
Merge remote git branch to local branch

Prerequisite:
yum install -y git
pip3 install git git-filter-repo

1. Update repos
./merge-from-gitee.py -p

2. Merge from remote git branch to local branch
./merge-from-gitee.py -c {COMMIT_ID}
./merge-from-gitee.py -c 12345
OR
./merge-from-gitee.py -c "12345 23456 34567"
"""

import re
import subprocess
import sys

from argparse import ArgumentParser, RawDescriptionHelpFormatter

default_project_id = "R251166SC04"
default_jira_id = "#QSE-8888"
gitee_remote = "gitee"
gitee_remote_branch = "develop"
gitee_local_branch = "gitee-develop"
cmss_remote = "origin"
cmss_local_branch = "gitee"


class MergeException(Exception):
    """Merge Exception"""


def run_command(command, check=True, capture_output=True, text=True):
    """Run command

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


def pull_branches():
    """Pull branches"""
    fetch_from_gitee_cmds = [
        f"git checkout {gitee_local_branch}",
        f"git pull --rebase {gitee_remote} "
        f"{gitee_remote_branch}:{gitee_local_branch}",
    ]
    print(
        f"Fetch codes from {gitee_remote}, "
        f"branch: {gitee_remote_branch}:{gitee_local_branch} ..."
    )
    results = run_command(";".join(fetch_from_gitee_cmds))
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

    fetch_from_cmss_cmds = [
        f"git checkout {cmss_local_branch}",
        f"git pull --rebase {cmss_remote} "
        f"{cmss_local_branch}:{cmss_local_branch}",
    ]
    print(f"Fetch codes from {cmss_remote}, branch: {cmss_local_branch} ...")
    results = run_command(";".join(fetch_from_cmss_cmds))
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)


def merge_branches(commit_id):
    """Merge branches

    Args:
        commit_id: commit id
    """
    # Merge codes
    print("Merge branch")
    run_command(f"git checkout {cmss_local_branch}")

    # run git cherry-pick
    # get git logs
    commits = []
    if ".." in commit_id:
        cmd = f"git log --oneline --no-merges --format='%h' {commit_id}"
        results = run_command(cmd)
        commits = results.stdout.splitlines()[::-1]
    else:
        commits = commit_id.split()
    commits_count = len(commits)
    if commits_count == 0:
        raise MergeException("no commits found to merge")
    run_command(f"git cherry-pick -m 1 {' '.join(commits)}")

    # get latest commit id
    results = run_command(f"git log -{commits_count} --format='%H'")
    merged_commit_id_list = results.stdout.split()
    print(f"merged commit ids: {merged_commit_id_list}")
    if len(merged_commit_id_list) == 0:
        raise MergeException("no commits found to modify")
    merged_commit_id_str = "[b'" + "',b'".join(merged_commit_id_list) + "']"

    # build git-filter-repo command
    callback_script = f"""
    if commit.original_id in {merged_commit_id_str}:
        # Modify author's email and name
        decoded_email = commit.author_email.decode('utf-8')
        decoded_author_name = commit.author_name.decode('utf-8')
        if decoded_email.endswith('_yewu@cmss.chinamobile.com'):
            new_email = decoded_email.replace('_yewu@cmss.chinamobile.com', 
                '@cmss.chinamobile.com')
            encoded_new_email = new_email.encode('utf-8')
            commit.author_email = encoded_new_email
            new_author_name = decoded_author_name.replace('_yewu', '')
            encoded_new_author_name = new_author_name.encode('utf-8')
            commit.author_name = encoded_new_author_name

        # modify commit messages
        new_messages = []
        key_to_modify = {{
            'Jira': (False, '{default_jira_id}'),
            'Code Source From': (False, 'Others'),
            '市场项目编号（名称）': (False, '{default_project_id}')
        }}
        last_message = None
        decoded_message = commit.message.decode('utf-8')
        messages = decoded_message.split('\\n')
        for m in messages:
            for key in key_to_modify:
                if key in m:
                    key_to_modify[key] = (True, key_to_modify[key][1])
            if 'Signed-off-by:' in m and '_yewu@cmss.chinamobile.com' in m:
                m = m.replace('_yewu@cmss.chinamobile.com', 
                    '@cmss.chinamobile.com')
                last_message = m
                continue
            new_messages.append(m)
        for key in key_to_modify:
            if not key_to_modify[key][0]:
                value = key_to_modify[key][1]
                if key == 'Code Source From' and \
                        '@cmss.chinamobile.com' in decoded_email:
                    value = 'Self Code'
                message = f'{{key}}: {{value}}'
                new_messages.append(message.strip())
        if last_message:
            new_messages.append(f'\\n{{last_message.strip()}}')
        new_message = '\\n'.join(new_messages)
        commit.message = new_message.encode('utf-8')
    """
    # run git-filter-repo
    cmd = (
        f'git-filter-repo --force --commit-callback "{callback_script}" '
        f"--refs refs/heads/{cmss_local_branch}"
    )
    results = run_command(cmd)
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)


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
            "-p",
            "--pull",
            dest="pull",
            action="store_true",
            help="Pull remote_branch to local_branch",
        )
        parser.add_argument(
            "-c",
            "--commit-id",
            dest="commit_id",
            help=f"Local commit ID (remote: {cmss_remote}, "
            f"remote_branch: {cmss_local_branch})",
        )

        # parse arguments
        args = parser.parse_args()
        pull = args.pull
        commit_id = args.commit_id

        commit_id_pattern = r"^[0-9a-fA-F]{7,40}$"
        if commit_id:
            if " " in commit_id:
                for _commit_id in commit_id.split():
                    if not re.match(commit_id_pattern, _commit_id):
                        parser.error(
                            "Invalid commit ID format for --commit-id: "
                            f"{_commit_id}"
                        )
            if ".." in commit_id:
                for _commit_id in commit_id.split(".."):
                    if not re.match(commit_id_pattern, _commit_id):
                        parser.error(
                            "Invalid commit ID format for --commit-id: "
                            f"{_commit_id}"
                        )

        if pull and commit_id:
            parser.error("Cannot use --pull with --commit-id")

        if pull:
            print("Pull branches ...")
            pull_branches()

        if commit_id:
            print(f"Merge commits: {commit_id}")
            merge_branches(commit_id)
            print("Commits were merged successfully")

        if not pull and not commit_id:
            parser.error("You must specify either -p or -c")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except MergeException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    main()
