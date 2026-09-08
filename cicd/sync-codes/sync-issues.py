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
Sync Jira issues from GitLab MRs to Gitee community issues.

This script:
1. Reads all open MRs from a GitLab project
2. Extracts commit info (summary, description, author, Jira ID)
3. Fetches Jira issue details for each Jira ID found
4. Reads Gitee community issues with jira-* labels
5. Creates community issues for Jira IDs not yet in Gitee
6. Closes community issues when the corresponding Jira is closed

Prerequisite:
pip3 install --break-system-packages requests

Environment variables (defaults, overridable by CLI args):
- GITLAB_URL: GitLab base URL
- GITLAB_TOKEN: GitLab access token
- GITLAB_PROJECT_ID: GitLab project ID
- JIRA_BASE_URL: Jira base URL
- JIRA_AUTH: Jira basic auth "user:pass"
- GITEE_ACCESS_TOKEN: Gitee API token

Examples:
./sync-issues.py
./sync-issues.py --gitlab-url http://gitlab.com --gitlab-token "xxxxxxxxxx" --gitlab-project-id WuYueOs --jira-url "http://jira.com" --jira-auth "test:test" --gitee-access-token "xxxxxxxxx" --gitee-user-tokens '{"test": {"gitee_token": "abc123", "user_name": "test"}}'
./sync-issues.py --dry-run
"""

import json
import os
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import library as lib


# defaults from environment
default_gitee_access_token = os.getenv("GITEE_ACCESS_TOKEN", "")
default_gitee_user_accounts = os.getenv("GITEE_USER_ACCOUNTS", "")

default_gitlab_url = os.getenv("GITLAB_URL", "")
default_gitlab_token = os.getenv("GITLAB_TOKEN", "")
default_gitlab_project_id = os.getenv("GITLAB_PROJECT_ID", "")
default_jira_url = os.getenv("JIRA_BASE_URL", lib.jira_base_url)
default_jira_auth = os.getenv("JIRA_AUTH", lib.jira_auth)


def main(argv=None):
    """main"""
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip().split("\n")[0]
    program_license = f"{program_shortdesc}\nUSAGE"

    try:
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--gitlab-url",
            dest="gitlab_url",
            default=default_gitlab_url,
            help=f"GitLab base URL (env: GITLAB_URL, "
                 f"default: {default_gitlab_url})",
        )
        parser.add_argument(
            "--gitlab-token",
            dest="gitlab_token",
            default=default_gitlab_token,
            help="GitLab access token (env: GITLAB_TOKEN)",
        )
        parser.add_argument(
            "--gitlab-project-id",
            dest="gitlab_project_id",
            default=default_gitlab_project_id,
            help="GitLab project ID (env: GITLAB_PROJECT_ID)",
        )
        parser.add_argument(
            "--jira-url",
            dest="jira_url",
            default=default_jira_url,
            help=f"Jira base URL (env: JIRA_BASE_URL, "
                 f"default: {default_jira_url})",
        )
        parser.add_argument(
            "--jira-auth",
            dest="jira_auth",
            default=default_jira_auth,
            help='Jira basic auth "user:pass" '
                 f"(env: JIRA_AUTH, default: {default_jira_auth})",
        )
        parser.add_argument(
            "--gitee-access-token",
            dest="gitee_access_token",
            default=default_gitee_access_token,
            help="Gitee API access token "
                 "(env: GITEE_ACCESS_TOKEN)",
        )
        parser.add_argument(
            "--gitee-user-accounts",
            dest="gitee_user_accounts",
            default=default_gitee_user_accounts,
            help='JSON string mapping Gitee accounts. '
                 'Format: \'{"JIRA_USER_NAME": '
                 '{"gitee_user_name": "GITEE_USER_NAME", '
                 '"gitee_user_token": "GITEE_USER_TOKEN"}\'',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry-run mode: show what would be done without "
                 "creating/closing issues",
        )

        args = parser.parse_args()

        # validate required args
        if not args.gitlab_url:
            print("Error: --gitlab-url is required "
                  "(or set GITLAB_URL env var)")
            return 2
        if not args.gitlab_token:
            print("Error: --gitlab-token is required "
                  "(or set GITLAB_TOKEN env var)")
            return 2
        if not args.gitlab_project_id:
            print("Error: --gitlab-project-id is required "
                  "(or set GITLAB_PROJECT_ID env var)")
            return 2
        if not args.gitee_user_accounts:
            print("Error: --gitee-user-accounts is required "
                  "(or set GITEE_USER_ACCOUNTS env var)")
            return 2
        gitee_access_token = args.gitee_access_token
        gitee_user_accounts = None
        try:
            gitee_user_accounts = json.loads(args.gitee_user_accounts)
        except Exception:
            print("Error: --gitee-user-accounts is not a valid JSON")
            return 2

        print("==== Sync Issues Configuration ====")
        print(f"GitLab URL:     {args.gitlab_url}")
        print(f"GitLab Project: {args.gitlab_project_id}")
        print(f"Jira URL:       {args.jira_url}")
        print(f"Gitee Owner:    {lib.gitee_owner}/{lib.gitee_repo}")
        print(f"Dry-run:        {args.dry_run}")
        print("==================================\n")

        # Step 1: Read all open MRs from GitLab
        print(">>> Step 1: Fetching open MRs from GitLab...")
        mr_dict = lib.get_merge_requests(
            args.gitlab_url, args.gitlab_token, args.gitlab_project_id
        )
        print(f"    Found {len(mr_dict)} open MR(s)")

        # Step 2: Read commits for each MR
        print("\n>>> Step 2: Fetching commits for each MR...")
        for mr_iid in mr_dict:
            print(f"    MR !{mr_iid}: "
                  f"{mr_dict[mr_iid]['title']}")
            commits = lib.get_mr_commits(
                args.gitlab_url, args.gitlab_token,
                args.gitlab_project_id, mr_iid
            )
            mr_dict[mr_iid]["commits"] = commits
            print(f"      {len(commits)} commit(s)")

        # Step 3: Collect all unique Jira IDs from commits
        jira_ids = set()
        for mr_iid, mr_info in mr_dict.items():
            for commit_id, commit_info in mr_info["commits"].items():
                jira_id = commit_info["jira_id"]
                author = commit_info["author"]
                summary = commit_info["summary"]
                if jira_id:
                    jira_ids.add(jira_id)
                    print(f"    MR !{mr_iid} commit {commit_id}: Jira ID = {jira_id}, author: {author}, summary: {summary}",)
        if not jira_ids:
            print("    No Jira IDs found in any commit messages.")
            print("\n==== Done ====")
            return 0
        print(f"    Total unique Jira IDs: {len(jira_ids)}")

        # Step 4: Fetch Jira issue details
        print("\n>>> Step 4: Fetching Jira issue details...")
        jira_dict = {}
        for jira_id in jira_ids:
            issue_data = lib.fetch_jira_issue(
                jira_id, args.jira_url, args.jira_auth
            )
            if issue_data:
                jira_dict[jira_id] = issue_data
                print(f"    {jira_id}: status={issue_data['status']}, "
                      f"summary={issue_data['summary'][:50]}")
            else:
                print(f"    {jira_id}: NOT FOUND")

        # Step 5: Read Gitee community issues with jira labels
        print("\n>>> Step 5: Fetching Gitee community issues...")
        gitee_jira_map = lib.get_gitee_issues_with_jira_labels(
            gitee_access_token
        )
        print(f"    Found {len(gitee_jira_map)} "
              f"community issue(s) with Jira labels")

        # Step 6: Sync - create missing issues, close closed ones
        print("\n>>> Step 6: Syncing issues...")
        for jira_id in jira_ids:
            jira_info = jira_dict.get(jira_id)
            jira_num = jira_info.get("jira_num")
            jira_closed = lib.is_jira_closed(jira_info)
            reporter_name = jira_info["reporter_name"]
            jira_user_name = f"{reporter_name}"
            jira_user_email = f"{reporter_name}_yewu@cmss.chinamobile.com"
            gitee_developer_account = lib.get_gitee_developer_account(
                jira_user_name, gitee_user_accounts)
            if not jira_num:
                print(f"    Invalid jira_num from jira_id: {jira_id}")
                continue
            if not gitee_developer_account:
                print(f"    Invalid gitee developer account: {jira_user_name}")
                continue
            gitee_developer_token = gitee_developer_account.get("gitee_token", None)
            if not gitee_developer_token:
                print(f"    Invalid gitee developer token from user: {jira_user_name}")
                continue
            gitee_user_name = gitee_developer_account.get("gitee_user_name", None)
            gitee_jira_id = f"jira-{jira_num}"
            jira_type = jira_info.get("jira_type")
            gitee_issue = gitee_jira_map.get(gitee_jira_id)

            if gitee_issue:
                # Community issue already exists
                if jira_closed and not args.dry_run:
                    print(f"    {jira_id}: Jira closed, "
                          f"closing Gitee issue "
                          f"#{gitee_issue['number']}")
                    lib.close_gitee_issue(
                        gitee_access_token,
                        lib.gitee_owner, lib.gitee_repo,
                        gitee_issue["number"],
                    )
                elif jira_closed and args.dry_run:
                    print(f"    {jira_id}: [DRY-RUN] Would close "
                          f"Gitee issue "
                          f"#{gitee_issue['number']}")
                else:
                    print(f"    {jira_id}: Already exists as "
                          f"Gitee issue "
                          f"#{gitee_issue['number']}, "
                          f"Jira still open")
            else:
                # Community issue does not exist, create it
                if not jira_info:
                    print(f"    {jira_id}: Jira issue not found, "
                          f"skipping")
                    continue
                if jira_closed:
                    print(f"    {jira_id}: Jira already closed, "
                          f"skipping creation")
                    continue
                title = f"{jira_info['summary']}"
                body = f"{jira_info['description'] or 'N/A'}"
                if not args.dry_run:
                    print(f"    {jira_id}: Creating Gitee issue...")
                    lib.create_gitee_issue(
                        gitee_developer_token,
                        lib.gitee_owner, lib.gitee_repo,
                        gitee_jira_id, title, body,
                        gitee_user_name, jira_type,
                    )
                else:
                    print(f"    {jira_id}: [DRY-RUN] Would create "
                          f"Gitee issue: {title}")

        # Step 7: Check for closed Jira issues with open community issues
        print("\n>>> Step 7: Checking for closed Jira issues "
              "with open community issues...")
        for jira_id, gitee_issue in gitee_jira_map.items():
            if jira_id not in jira_ids:
                jira_info = lib.fetch_jira_issue(
                    jira_id, args.jira_url, args.jira_auth
                )
                if jira_info and lib.is_jira_closed(jira_info):
                    if not args.dry_run:
                        print(f"    {jira_id}: Jira closed, "
                              f"closing Gitee issue "
                              f"#{gitee_issue['number']}")
                        lib.close_gitee_issue(
                            gitee_developer_token,
                            lib.gitee_owner, lib.gitee_repo,
                            gitee_issue["number"],
                        )
                    else:
                        print(f"    {jira_id}: [DRY-RUN] Would close "
                              f"Gitee issue "
                              f"#{gitee_issue['number']}")

        print("\n==== Sync Complete ====")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except lib.SyncException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
