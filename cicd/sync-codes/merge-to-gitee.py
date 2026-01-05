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
Merge local git branch to remote branch

Prerequisite:
yum install -y git
pip3 install git git-filter-repo

1. Initialize git repo (Init only once, no need to run in the next time)
mkdir WuYue
cd WuYue
git init
git remote add origin ssh://git@gitlab.cmss.com:2223/OCRI/WuYueOs.git
git remote add gitee git@gitee.com:OpenWuYue/qcos.git
git checkout --orphan dev_gitee
git pull origin dev_gitee --allow-unrelated-histories
git branch --set-upstream-to=origin/gitee dev_gitee

git checkout --orphan temp
git rm -rf .
git checkout --orphan gitee-develop
git pull gitee develop --allow-unrelated-histories
git branch --set-upstream-to=gitee/develop gitee-develop

2. Update repos
./merge-to-gitee.py -p

3. find out cmss local commit id to merge
./merge-to-gitee.py -d
OR
./merge-to-gitee.py -d -s "2025-11-01"

4. merge commits to local merge branch
./merge-to-gitee.py -c {COMMIT_ID}
./merge-to-gitee.py -c 12345
OR
./merge-to-gitee.py -c "12345 23456 34567"

5. push local commits to remote
git push ${gitee_remote} ${cmss_local_merge_branch}:${gitee_remote_branch}
eg. git push gitee gitee-merge:develop
"""

import os
import re
import subprocess
import sys
from collections import OrderedDict

from argparse import ArgumentParser, RawDescriptionHelpFormatter

gitee_remote = "gitee"
gitee_remote_branch = "develop"
gitee_local_branch = "gitee-develop"

cmss_remote = "origin"
cmss_local_branch = "dev_gitee"
cmss_local_merge_branch = "gitee-merge"

gitee_branch_file = "/tmp/gitee_local_branch_commits"
cmss_branch_file = "/tmp/cmss_local_branch_commits"


class MergeException(Exception):
    """Merge Exception"""


def remove_temp_files():
    """Remove temp files"""
    print("Deleting temp files ...")
    temp_files = [
        cmss_branch_file,
        f"{cmss_branch_file}_hash",
        f"{cmss_branch_file}_unique",
        gitee_branch_file,
        f"{gitee_branch_file}_hash",
        f"{gitee_branch_file}_unique",
    ]
    for file in temp_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except MergeException as e:
                (print(f"Warning: Failed to remove {file}: {e}"))


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
    cmd = f"git branch -D {cmss_local_merge_branch}"
    results = run_command(cmd)
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

    delete_branch_cmds = [
        f"git branch -D {cmss_local_merge_branch} || true",
        f"git checkout -b {cmss_local_merge_branch} {gitee_local_branch}",
    ]
    print(f"Delete branches: {cmss_local_merge_branch}")
    results = run_command(";".join(delete_branch_cmds))
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

    fetch_from_gitee_cmds = [
        "git reset --hard",
        "git cherry-pick --abort || true",
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


def to_dict(commits_list):
    """To dictionary format

    Args:
        commits_list: commit list

    Returns:
        commits in dict format
    """
    commits_dict = OrderedDict()
    for commits_str in commits_list:
        if "]" in commits_str:
            commits_tokens = commits_str.split("]")
            date_messages = commits_tokens[1].strip()
            commits_dict[date_messages] = commits_str
    return commits_dict


def diff_branches(start_since):
    """Find differences between branches

    Args:
        start_since: start since
    """
    # get branches: cmss and gitee commits
    cmss_commits = format_commit(cmss_local_branch, start_since)
    gitee_commits = format_commit(gitee_local_branch, start_since)
    cmss_commits_list = cmss_commits.split("\n")
    gitee_commits_list = gitee_commits.split("\n")
    cmss_commits_dict = to_dict(cmss_commits_list)
    gitee_commits_dict = to_dict(gitee_commits_list)

    cmss_keys = set(cmss_commits_dict.keys())
    gitee_keys = set(gitee_commits_dict.keys())
    only_in_cmss = [k for k in cmss_keys if k not in gitee_keys]
    only_in_gitee = [k for k in gitee_keys if k not in cmss_keys]

    print("========================================")
    print(
        f"Commits that are in branch: {cmss_local_branch}, "
        f"but not in branch: '{gitee_local_branch}'"
    )
    print("========================================")
    if only_in_cmss:
        for k, message in cmss_commits_dict.items():
            if k in only_in_cmss:
                print(message)
    else:
        print("No")
    print("")

    print("========================================")
    print(
        f"Commits that are in branch: {gitee_local_branch}, "
        f"but not in branch: '{cmss_local_branch}'"
    )
    print("========================================")
    if only_in_gitee:
        for k, message in gitee_commits_dict.items():
            if k in only_in_gitee:
                print(message)
    else:
        print("No")
    print("")


def format_commit(local_branch, start_since):
    """Format commit

    Args:
        local_branch: local branch name
        start_since: start date

    Returns:
        formatted commits
    """
    since_str = ""
    if start_since:
        since_str = f'--since="{start_since}"'
    cmds = [
        f"""git log --no-merges --topo-order --pretty=format:'%H %at %ad %s' \
        --date=format:'%Y-%m-%d %H:%M:%S' {local_branch} {since_str} | \
        cut -d' ' -f1,3- |
        awk '{{hash=$1; $1=""; printf "[%s] %s \\n", hash, substr($0,2)}}'
        """
    ]
    results = run_command(";".join(cmds))
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)
    return results.stdout


def merge_branches(commit_id):
    """Merge branches

    Args:
        commit_id: commit id
    """
    print(f"create new branch and merge codes: {cmss_local_merge_branch}")

    # checkout local merge branch
    cmds = [
        "git reset --hard",
        "git cherry-pick --abort || true",
        f"git checkout {cmss_local_merge_branch}",
    ]
    results = run_command(";".join(cmds))
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

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
    filter_script = f"""
    if commit.original_id in {merged_commit_id_str}:
        # Modify author's email and name
        decoded_email = commit.author_email.decode('utf-8')
        decoded_author_name = commit.author_name.decode('utf-8')
        if decoded_email.endswith('@cmss.chinamobile.com') and \
                '_yewu@' not in decoded_email:
            new_email = decoded_email.replace('@cmss.chinamobile.com',
                '_yewu@cmss.chinamobile.com')
            encoded_new_email = new_email.encode('utf-8')
            commit.author_email = encoded_new_email
            new_author_name = f\\"{{decoded_author_name}}_yewu\\"
            encoded_new_author_name = new_author_name.encode('utf-8')
            commit.author_name = encoded_new_author_name

        # modify commit messages
        new_messages = []
        key_to_remove = set(['Jira:', 'Code Source From', '市场项目'])
        decoded_message = commit.message.decode('utf-8')
        messages = decoded_message.split('\\n')
        for m in messages:
            add = True
            for key in key_to_remove:
                if key.lower() in m.lower():
                    add = False
                    break
            if add:
                if '@cmss.chinamobile.com' in m and '_yewu@' not in m:
                    m = m.replace('@cmss.chinamobile.com',
                        '_yewu@cmss.chinamobile.com')
                new_messages.append(m.strip())
        new_message = '\\n'.join(new_messages)
        new_message = re.sub(r'(\\s*\\n)+$', '', new_message)
        new_message = re.sub(r'\\n\\s*\\n', '\\n\\n', new_message)
        new_message = re.sub(r'\\n{(3,)}', '\\n', new_message)
        encoded_new_message = new_message.encode('utf-8')
        commit.message = encoded_new_message
    """
    # run git-filter-repo
    cmd = (
        f'git-filter-repo --force  --commit-callback "{filter_script}" '
        f"--refs {cmss_local_merge_branch}"
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
            "-d",
            "--branch-diff",
            dest="branch_diff",
            action="store_true",
            help="Find differences of commits in branches",
        )
        parser.add_argument(
            "-c",
            "--commit-id",
            dest="commit_id",
            help=f"Local commit ID (remote: {cmss_remote}, "
            f"remote_branch: {cmss_local_branch})",
        )
        parser.add_argument(
            "-s",
            "--start-since",
            dest="start_since",
            help="Start date (git log '--since' "
            "format: 2025-10-01, 2 months ago)",
        )

        # parse arguments
        args = parser.parse_args()
        pull = args.pull
        branch_diff = args.branch_diff
        commit_id = args.commit_id
        start_since = args.start_since

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
        if branch_diff and commit_id:
            parser.error("Cannot use --branch-diff with --commit-id")

        if pull:
            print("Pull branches ...")
            pull_branches()

        if branch_diff:
            print("Find the differences between branches ...")
            diff_branches(start_since)

        if commit_id:
            print(f"Merge commits: {commit_id}")
            merge_branches(commit_id)

            # print git push
            print(
                f"\nRun: git push {gitee_remote} "
                f"{cmss_local_merge_branch}:{gitee_remote_branch}"
            )

        if not pull and not branch_diff and not commit_id:
            parser.error("You must specify either -p, -b or -c")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except MergeException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
