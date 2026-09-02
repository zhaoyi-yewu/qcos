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
Merge local git branch to remote branch / Split commits to single branches

Prerequisite:
yum install -y git
pip3 install --break-system-packages git-filter-repo GitPython

1. Initialize git repo (Init only once, no need to run in the next time)
mkdir WuYue
cd WuYue
git init
git remote add origin ssh://git@gitlab.cmss.com:2223/OCRI/WuYueOs.git
git remote add gitee git@gitee.com:OpenWuYue/qcos.git
git checkout --orphan dev_gitee
git pull origin dev_gitee --allow-unrelated-histories
git branch --set-upstream-to=origin/dev_gitee dev_gitee

git checkout --orphan temp
git rm -rf .
git checkout --orphan gitee-develop
git pull gitee develop --allow-unrelated-histories
git branch --set-upstream-to=gitee/develop gitee-develop

2. One-click full sync (pull + diff + merge all new commits + push)
./merge-to-gitee.py -f -s "2025-11-01"
./merge-to-gitee.py -f -s "2025-11-01" --skip-commit 12345 23456  # skip commits

3. One-click sync specified commits (pull + merge + push)
./merge-to-gitee.py -f -c "12345 23456"

4. Split commits to single branches and push to Gitee
./merge-to-gitee.py -S -s "2025-11-01"  # Split commits since 2025-11-01
./merge-to-gitee.py -S -c "12345 23456"  # Split specified commits
./merge-to-gitee.py -S -s "2025-11-01" --dry-run  # Dry-run, no push

5. Original commands are still available:
./merge-to-gitee.py -p (pull only)
./merge-to-gitee.py -d (diff only)
./merge-to-gitee.py -c {COMMIT_ID} (merge only)

6. Cleanup branches (delete local/remote feature branches):
./merge-to-gitee.py --delete-local-branches
./merge-to-gitee.py --delete-remote-branches
./merge-to-gitee.py -S -s "2025-11-01" --delete-local-branches --delete-remote-branches
"""

import hashlib
import re
import shlex
import subprocess
import sys
from collections import OrderedDict

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from git import Repo

gitee_remote = "gitee"
gitee_remote_branch = "develop"
gitee_local_branch = "gitee-develop"

cmss_remote = "origin"
cmss_local_branch = "dev_gitee"
cmss_local_merge_branch = "gitee-merge"

branch_prefix = "feature_new-"


class MergeException(Exception):
    """Merge Exception."""


def run_command(command, check=True, capture_output=True, text=True):
    """Run command.

    Args:
        command: command, a list of args or a shell string (split via shlex)
        check: check exit code
        capture_output: capture output
        text: print text

    Returns:
        command results
    """
    if isinstance(command, str):
        command = shlex.split(command)
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


def pull_branches():
    """Pull branches."""
    run_command(
        ["git", "branch", "-D", cmss_local_merge_branch], check=False
    )

    print(f"Recreate branch: {cmss_local_merge_branch}")
    results = run_command(
        [
            "git", "checkout", "-b", cmss_local_merge_branch,
            gitee_local_branch,
        ],
        check=False,
    )
    if results.returncode != 0:
        results = run_command(
            ["git", "checkout", cmss_local_merge_branch]
        )
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

    fetch_from_gitee_cmds = [
        ["git", "reset", "--hard"],
        ["git", "cherry-pick", "--abort"],
        ["git", "checkout", gitee_local_branch],
        [
            "git", "pull", "--rebase", gitee_remote,
            f"{gitee_remote_branch}:{gitee_local_branch}",
        ],
    ]
    print(f"Fetch from {gitee_remote}, branch: {gitee_remote_branch} ...")
    last_result = None
    for idx, cmd in enumerate(fetch_from_gitee_cmds):
        # cherry-pick --abort may fail; ignore its errors
        if idx == 1:
            last_result = run_command(cmd, check=False)
        else:
            last_result = run_command(cmd)
    ret_code = last_result.returncode
    if ret_code != 0:
        raise MergeException(last_result.stderr)

    fetch_from_cmss_cmds = [
        ["git", "checkout", cmss_local_branch],
        [
            "git", "pull", "--rebase", cmss_remote,
            f"{cmss_local_branch}:{cmss_local_branch}",
        ],
    ]
    print(f"Fetch codes from {cmss_remote}, branch: {cmss_local_branch} ...")
    last_result = None
    for cmd in fetch_from_cmss_cmds:
        last_result = run_command(cmd)
    ret_code = last_result.returncode
    if ret_code != 0:
        raise MergeException(last_result.stderr)


def get_commits_dict(branch_name, since_str=None, repo_path="."):
    """Get git commits dict.

    Args:
        branch_name (str): branch name
        since_str (str): since_str
        repo_path (str): repo path

    Returns:
        commit dict
    """

    commits_dict = OrderedDict()

    # init git repo object
    repo = Repo(repo_path)

    # fill options: no_merges, topo_order
    options = {
        "no_merges": True,
        "topo_order": True,
    }

    # fill options: since
    if since_str:
        options["since"] = since_str

    # list all commit logs
    for commit in repo.iter_commits(branch_name, **options):
        # get commit info
        commit_hash = commit.hexsha  # %H (Commit Hash)
        tree_hash = commit.tree.hexsha  # %T (Tree Hash)
        committed_datetime = commit.committed_datetime
        authored_datetime = commit.authored_datetime
        commit_summary = commit.summary  # %s (Subject/Message)

        # calculate commit content hash
        parent = commit.parents[0] if commit.parents else None
        diffs = commit.diff(parent, create_patch=True)
        full_diff_text = b""
        for d in diffs:
            full_diff_text += d.diff  # data type is bytes
        content_hash = hashlib.md5(full_diff_text).hexdigest()

        # store commit info
        if (
            content_hash
            and commit_hash
            and tree_hash
            and committed_datetime
            and authored_datetime
            and commit_summary
        ):
            commits_dict[content_hash] = {
                "commit_hash": commit_hash,
                "content_hash": content_hash,
                "tree_hash": tree_hash,
                "committed_datetime": committed_datetime,
                "authored_datetime": authored_datetime,
                "commit_summary": commit_summary,
            }
    return commits_dict


def get_unsynced_commits(start_since=None, skip_commits=None):
    """Get unsynced commits from cmss to gitee.

    Args:
        start_since: start since date
        skip_commits: commit IDs to skip

    Returns:
        unsynced commit list
    """
    cmss_commits_dict = get_commits_dict(cmss_local_branch, start_since)
    gitee_commits_dict = get_commits_dict(gitee_local_branch, start_since)

    # Remove skipped commits from cmss_commits_dict
    if skip_commits:
        skip_set = set(skip_commits)
        keys_to_remove = []
        for content_key, commit_info in cmss_commits_dict.items():
            commit_hash = commit_info["commit_hash"]
            if any(commit_hash.startswith(s) for s in skip_set):
                keys_to_remove.append(content_key)
        for key in keys_to_remove:
            del cmss_commits_dict[key]

    cmss_keys = set(cmss_commits_dict.keys())
    gitee_keys = set(gitee_commits_dict.keys())
    only_in_cmss = [k for k in cmss_keys if k not in gitee_keys]

    unsynced_commits = []
    if only_in_cmss:
        for k, commit_info in cmss_commits_dict.items():
            if k in only_in_cmss:
                unsynced_commits.append(
                    (commit_info["commit_hash"],
                     commit_info["commit_summary"])
                )
    unsynced_commits.reverse()
    unsynced_commits.sort(key=lambda x: cmss_commits_dict[
        next(k for k, v in cmss_commits_dict.items()
             if v["commit_hash"] == x[0])
    ]["committed_datetime"])
    return unsynced_commits


def diff_branches(start_since):
    """Find differences between branches.

    Args:
        start_since: start since
    """
    # get branches: cmss and gitee commits
    cmss_commits_dict = get_commits_dict(cmss_local_branch, start_since)
    gitee_commits_dict = get_commits_dict(gitee_local_branch, start_since)

    cmss_keys = set(cmss_commits_dict.keys())
    gitee_keys = set(gitee_commits_dict.keys())

    only_in_cmss = [k for k in cmss_keys if k not in gitee_keys]
    print(only_in_cmss)
    only_in_gitee = [k for k in gitee_keys if k not in cmss_keys]

    print("========================================")
    print(f"Commits in {cmss_local_branch} but not in {gitee_local_branch}")
    print("========================================")
    if only_in_cmss:
        for k, commit_info in cmss_commits_dict.items():
            if k in only_in_cmss:
                print(
                    f"[{commit_info['commit_hash']}] "
                    f"cd: {str(commit_info['committed_datetime'])} "
                    f"ad: {str(commit_info['authored_datetime'])} "
                    f"{commit_info['commit_summary']}"
                )
    else:
        print("No")
    print("")

    print("========================================")
    print(f"Commits in {gitee_local_branch} but not in {cmss_local_branch}")
    print("========================================")
    if only_in_gitee:
        for k, commit_info in gitee_commits_dict.items():
            if k in only_in_gitee:
                print(
                    f"[{commit_info['commit_hash']}] "
                    f"cd: {str(commit_info['committed_datetime'])} "
                    f"ad: {str(commit_info['authored_datetime'])} "
                    f"{commit_info['commit_summary']}"
                )
    else:
        print("No")
    print("")


def sanitize_author(email, name):
    """Anonymize submitter information.

    Args:
        email: author email
        name: author name

    Returns:
        Desensitized tuple
    """
    new_email = email
    new_name = name
    if email.endswith("@cmss.chinamobile.com") and "_yewu@" not in email:
        new_email = email.replace(
            "@cmss.chinamobile.com", "_yewu@cmss.chinamobile.com"
        )
        new_name = f"{name}_yewu"
    return new_email, new_name


def sanitize_message(message):
    """Sanitize the submitted information.

    Args:
        message: commit message

    Returns:
        Desensitized commit message
    """
    key_to_remove = {"Jira:", "Code Source From", "市场项目", "AI Co-author:"}
    new_messages = []
    for line in message.split("\n"):
        # Check whether contains keywords that need to be removed
        should_remove = False
        for key in key_to_remove:
            if key.lower() in line.lower():
                should_remove = True
                break
        if should_remove:
            continue
        # Replace email domain
        if "@cmss.chinamobile.com" in line and "_yewu@" not in line:
            line = line.replace(
                "@cmss.chinamobile.com", "_yewu@cmss.chinamobile.com"
            )
        new_messages.append(line.strip())

    new_message = "\n".join(new_messages)
    new_message = re.sub(r"(\s*\n)+$", "", new_message)
    new_message = re.sub(r"\n\s*\n", "\n\n", new_message)
    new_message = re.sub(r"\n{3,}", "\n", new_message)
    return new_message


def create_single_commit_branch(
        commit_hash,
        num,
        base_branch=gitee_local_branch
):
    """Create separate branch for a single commit
    and desensitize the commit information

    Args:
        commit_hash: Commit ID to split
        num: commit number
        base_branch: base branch

    Returns:
        New branch name, masked commit ID
    """
    # generate branch name
    branch_name = f"{branch_prefix}{num}"
    if num > 1:
        base_branch = f"{branch_prefix}{num - 1}"

    # 1. Delete existing branch with the same name
    run_command(["git", "branch", "-D", branch_name], check=False)
    # 2. Create a new branch based on the base branch
    run_command(["git", "checkout", base_branch])
    run_command(["git", "checkout", "-b", branch_name])
    # 3. Clear the current branch
    run_command(["git", "reset", "--hard"])
    # 4. Cherry-pick single commit
    run_command(["git", "cherry-pick", commit_hash])

    # 5. Submit desensitized information
    author_email = run_command(
        ["git", "log", "-1", "--format=%ae"]
    ).stdout.strip()
    author_name = run_command(
        ["git", "log", "-1", "--format=%an"]
    ).stdout.strip()
    message = run_command(
        ["git", "log", "-1", "--format=%B"]
    ).stdout.strip()

    new_email, new_name = sanitize_author(author_email, author_name)
    new_message = sanitize_message(message)

    # 6. Rewrite commit message
    amend_cmd = [
        "git",
        "-c", f"user.name={new_name}",
        "-c", f"user.email={new_email}",
        "commit", "--amend", "--no-edit",
        f"--author={new_name} <{new_email}>",
    ]
    run_command(amend_cmd)

    if new_message != message:
        msg_file = "/tmp/git_commit_msg.txt"
        with open(msg_file, "w", encoding="utf-8") as f:
            f.write(new_message)
        run_command(
            ["git", "commit", "--amend", "--no-edit", "-F", msg_file]
        )

    new_commit_hash = run_command(
        ["git", "log", "-1", "--format=%H"]
    ).stdout.strip()
    print(
        f"Created branch [{branch_name}] for commit"
        f" [{commit_hash}] -> new commit [{new_commit_hash}]"
    )
    return branch_name, new_commit_hash


def push_single_branch(branch_name):
    """Push single branch to gitee

    Args:
        branch_name: branch name
    """
    push_cmd = [
        "git", "push", gitee_remote, f"{branch_name}:{branch_name}",
    ]
    results = run_command(push_cmd)
    if results.returncode == 0:
        print(f"Pushed branch [{branch_name}] to Gitee success!")
    else:
        raise MergeException(
            f"Push branch [{branch_name}] failed: {results.stderr}"
        )


def cleanup_branches(del_local, del_remote):
    """Delete local/remote branches matching branch_prefix.

    Args:
        del_local: If True, delete local branches with branch_prefix
        del_remote: If True, delete remote branches with branch_prefix
    """
    if del_local:
        print("\n==== Cleanup: delete local branches ====")
        # checkout base branch to avoid deleting current branch
        run_command(
            ["git", "checkout", gitee_local_branch], check=False
        )
        results = run_command(
            ["git", "branch", "--format=%(refname:short)"]
        )
        branches = results.stdout.splitlines()
        for b in branches:
            b = b.strip()
            if b and b.startswith(branch_prefix):
                run_command(
                    ["git", "branch", "-D", b], check=False
                )
                print(f"Deleted local branch: {b}")

    if del_remote:
        print(
            f"\n==== Cleanup: delete remote branches"
            f" on {gitee_remote} ===="
        )
        results = run_command(
            ["git", "ls-remote", "--heads", gitee_remote]
        )
        for line in results.stdout.splitlines():
            # format: <sha>\trefs/heads/<branch>
            parts = line.split("\trefs/heads/", 1)
            if len(parts) == 2:
                b = parts[1].strip()
                if b and b.startswith(branch_prefix):
                    run_command(
                        ["git", "push", gitee_remote,
                         "--delete", b],
                        check=False,
                    )
                    print(f"Deleted remote branch: {b}")


def split_and_push_single_commits(start_since=None, commit_id=None,
                                   skip_commits=None, dry_run=False):
    """Split submission into an independent branch and push to Gitee

    Args:
        start_since: Time Range
        commit_id: Specify the commit ID to split
        skip_commits: Commit IDs to skip when auto-finding unsynced commits
        dry_run: If True, create branches but do not push to Gitee
    """
    print("==== Step 1: Pull latest code ====")
    pull_branches()

    print("\n==== Step 2: Determine commits to split ====")
    target_commits = []
    if commit_id:
        if ".." in commit_id:
            cmd = [
                "git", "log", "--oneline", "--no-merges",
                "--format=%h", commit_id,
            ]
            results = run_command(cmd)
            target_commits = results.stdout.splitlines()[::-1]
        else:
            target_commits = commit_id.split()
        print(f"Specified commits to split: {target_commits}")
    else:
        unsynced_commits = get_unsynced_commits(start_since, skip_commits)
        if not unsynced_commits:
            print("No unsynced commits found, exit.")
            return
        target_commits = [c[0] for c in unsynced_commits]
        print("Auto-found unsynced commits to split:")
        for commit_hash, commit_summary in unsynced_commits:
            print(f"  [{commit_hash}] {commit_summary}")

    print("\n==== Step 3: Split and push single commits ====")
    if dry_run:
        print("[Dry-run mode] Branches will be created but NOT pushed.")
    for i, commit in enumerate(target_commits, 1):
        print(f"\nProcessing commit [{i}/{len(target_commits)}]: {commit}")
        try:
            branch_name, new_commit = create_single_commit_branch(commit, i)
            if dry_run:
                print(f"[Dry-run] Skip pushing branch [{branch_name}]")
            else:
                push_single_branch(branch_name)
        except Exception as e:
            print(f"Failed to process commit [{commit}]: {e}")
            continue

    print("\n==== Split and push all single commits completed! ====")


def merge_branches(commit_id):
    """Merge branches

    Args:
        commit_id: commit ID

    Returns:
        merged commit ids
    """
    print(f"Merge commits to branch: {cmss_local_merge_branch}")

    # checkout local merge branch
    run_command(["git", "cherry-pick", "--abort"], check=False)
    results = run_command(["git", "checkout", cmss_local_merge_branch])
    ret_code = results.returncode
    if ret_code != 0:
        raise MergeException(results.stderr)

    # Analyze the list of commits to be merged
    commits = []
    if ".." in commit_id:
        cmd = [
            "git", "log", "--oneline", "--no-merges",
            "--format=%h", commit_id,
        ]
        results = run_command(cmd)
        commits = results.stdout.splitlines()[::-1]
    else:
        commits = commit_id.split()
    commits_count = len(commits)
    if commits_count == 0:
        raise MergeException("no commits found to merge")

    # cherry-pick and amend for desensitization
    merged_commit_ids = []
    for i, commit in enumerate(commits, 1):
        print(f"Processing commit [{i}/{commits_count}]: {commit}")
        run_command(["git", "cherry-pick", "-m", "1", commit])

        # Read the author and message information of the current HEAD
        author_email = run_command(
            ["git", "log", "-1", "--format=%ae"]
        ).stdout.strip()
        author_name = run_command(
            ["git", "log", "-1", "--format=%an"]
        ).stdout.strip()
        message = run_command(
            ["git", "log", "-1", "--format=%B"]
        ).stdout.strip()

        new_email, new_name = sanitize_author(author_email, author_name)
        new_message = sanitize_message(message)

        # amend current commit
        amend_cmd = [
            "git",
            "-c", f"user.name={new_name}",
            "-c", f"user.email={new_email}",
            "commit", "--amend", "--no-edit",
            f"--author={new_name} <{new_email}>",
        ]
        run_command(amend_cmd)

        if new_message != message:
            msg_file = "/tmp/git_commit_msg.txt"
            with open(msg_file, "w", encoding="utf-8") as f:
                f.write(new_message)
            run_command(
                ["git", "commit", "--amend", "--no-edit", "-F", msg_file]
            )

        merged_commit = run_command(
            ["git", "log", "-1", "--format=%H"]
        ).stdout.strip()
        merged_commit_ids.append(merged_commit)

    print(f"Successfully merged commits: {merged_commit_ids}")
    return merged_commit_ids


def push_to_gitee():
    """Push merged branch to gitee."""
    print(f"Push to {gitee_remote}/{gitee_remote_branch} ...")
    push_cmd = [
        "git", "push", gitee_remote,
        f"{cmss_local_merge_branch}:{gitee_remote_branch}",
    ]
    results = run_command(push_cmd)
    if results.returncode == 0:
        print("Push to gitee success!")
    else:
        raise MergeException(f"Push failed: {results.stderr}")


def full_auto_sync(start_since=None, commit_id=None, skip_commits=None):
    """auto push to Gitee

    Args:
        start_since: Time Range
        commit_id: commit ID
        skip_commits: Commit IDs to skip when auto-finding unsynced commits
    """
    print("==== Step 1: Pull latest code ====")
    pull_branches()

    print("\n==== Step 2: Determine commits to merge ====")
    if commit_id:
        target_commits = commit_id
        print(f"Specified commits to merge: {target_commits}")
    else:
        unsynced_commits = get_unsynced_commits(start_since, skip_commits)
        if not unsynced_commits:
            print("No unsynced commits found, exit.")
            return
        target_commits = " ".join(c[0] for c in unsynced_commits)
        print("Auto-found unsynced commits:")
        for commit_hash, commit_summary in unsynced_commits:
            print(f"  [{commit_hash}] {commit_summary}")

    print("\n==== Step 3: Merge commits ====")
    merge_branches(target_commits)

    print("\n==== Step 4: Push to Gitee ====")
    push_to_gitee()

    print("\n==== One-click sync completed successfully! ====")


def main(argv=None):
    """main"""

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f"{program_shortdesc}\nUSAGE"

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
            help="Pull remote_branch to local_branch"
        )
        parser.add_argument(
            "-d",
            "--branch-diff",
            dest="branch_diff",
            action="store_true",
            help="Find differences of commits in branches"
        )
        parser.add_argument(
            "-c",
            "--commit-id",
            dest="commit_id",
            help="Local commit ID to merge"
        )
        parser.add_argument(
            "-s",
            "--start-since",
            dest="start_since",
            help="Start date (git log '--since' format: 2025-10-01)"
        )
        parser.add_argument(
            "-f",
            "--full-sync",
            dest="full_sync",
            action="store_true",
            help="One-click full sync (pull+merge+push)"
        )
        parser.add_argument(
            "-S",
            "--split",
            dest="split",
            action="store_true",
            help="Split commits to single branches and push to Gitee"
        )
        parser.add_argument(
            "--skip-commits",
            dest="skip_commits",
            nargs="+",
            metavar="COMMITS",
            help="Commit IDs to skip when auto-finding unsynced commits"
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Dry-run mode: create branches but do not push to Gitee"
        )
        parser.add_argument(
            "--delete-local-branches",
            dest="delete_local_branches",
            action="store_true",
            help="Delete all local branches matching branch_prefix"
        )
        parser.add_argument(
            "--delete-remote-branches",
            dest="delete_remote_branches",
            action="store_true",
            help="Delete all remote branches matching branch_prefix"
        )

        # parse arguments
        args = parser.parse_args()
        pull = args.pull
        branch_diff = args.branch_diff
        commit_id = args.commit_id
        start_since = args.start_since
        full_sync = args.full_sync
        split = args.split
        skip_commits = args.skip_commits
        dry_run = args.dry_run
        del_local = args.delete_local_branches
        del_remote = args.delete_remote_branches

        commit_id_pattern = r"^[0-9a-fA-F]{7,40}$"
        if commit_id:
            if " " in commit_id:
                for _commit_id in commit_id.split():
                    if (
                        not re.match(commit_id_pattern, _commit_id)
                        and ".." not in _commit_id
                    ):
                        parser.error(f"Invalid commit ID format: {_commit_id}")
            if ".." in commit_id:
                for _commit_id in commit_id.split(".."):
                    if not re.match(commit_id_pattern, _commit_id):
                        parser.error(f"Invalid commit ID format: {_commit_id}")

        if skip_commits:
            for _skip_id in skip_commits:
                if not re.match(commit_id_pattern, _skip_id):
                    parser.error(
                        f"Invalid skip commit ID format: {_skip_id}"
                    )

        if full_sync and split:
            parser.error("Cannot use --full-sync with --split")
        if full_sync and (pull or branch_diff):
            parser.error("Cannot use --full-sync with --pull/--branch-diff")
        if split and (pull or branch_diff):
            parser.error("Cannot use --split with --pull/--branch-diff")

        if split:
            if del_local or del_remote:
                cleanup_branches(del_local, del_remote)
            split_and_push_single_commits(start_since, commit_id,
                                          skip_commits, dry_run)
            return 0

        if full_sync:
            if del_local or del_remote:
                cleanup_branches(del_local, del_remote)
            full_auto_sync(start_since, commit_id, skip_commits)
            return 0
        else:
            if pull and commit_id:
                parser.error("Cannot use --pull with --commit-id")
            if branch_diff and commit_id:
                parser.error("Cannot use --branch-diff with --commit-id")

            if del_local or del_remote:
                cleanup_branches(del_local, del_remote)

            if pull:
                print("Pull branches ...")
                pull_branches()

            if branch_diff:
                print("Find the differences between branches ...")
                diff_branches(start_since)

            if commit_id:
                print(f"Merge commits: {commit_id}")
                merge_branches(commit_id)
                print(
                    f"\nRun: git push {gitee_remote}"
                    f" {cmss_local_merge_branch}:{gitee_remote_branch}"
                )
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except MergeException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
