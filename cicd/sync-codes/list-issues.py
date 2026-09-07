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
Sync Jira issues - fetch issue summary and description.

This script calls the Jira REST API via requests to retrieve an
issue's summary and description fields, then prints them in a
readable format.

Prerequisite:
pip3 install --break-system-packages requests

Examples:
./sync-issues.py QCOS-504
./sync-issues.py QCOS-504 --user "test:test --url "http://jira.com"
"""

import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import library as lib


def parse_issue(issue_data):
    """Extract summary and description from issue data.

    Args:
        issue_data: parsed JSON dict of the issue

    Returns:
        tuple of (issue_key, summary, description)
    """
    issue_key = issue_data.get("key", "UNKNOWN")
    fields = issue_data.get("fields", {})
    summary = fields.get("summary", "")
    description = fields.get("description", "")
    return issue_key, summary, description


def main(argv=None):
    """main"""
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_shortdesc = __doc__.strip()
    program_license = f"{program_shortdesc}\nUSAGE"

    try:
        parser = ArgumentParser(
            description=program_license,
            formatter_class=RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "jira_issue_id",
            help="Jira issue ID, e.g. QCOS-504",
        )
        parser.add_argument(
            "--jira-url",
            dest="base_url",
            default=lib.jira_base_url,
            help=f"Jira base URL (default: {lib.jira_base_url})",
        )
        parser.add_argument(
            "--jira-auth",
            dest="auth",
            default=lib.jira_auth,
            help='Basic auth credentials "user:pass" '
                 f"(default: {lib.jira_auth})",
        )

        args = parser.parse_args()
        issue_id = args.jira_issue_id
        base_url = args.base_url
        auth = args.auth

        print("==== Fetch Jira issue ====")
        print(f"Issue:   {issue_id}")
        print(f"URL:     {base_url}")

        issue_data = lib.fetch_jira_issue(issue_id, base_url, auth)
        issue_key = issue_data["key"]
        summary = issue_data["summary"]
        description = issue_data["description"]

        print("\n========================================")
        print(f"Issue Key:    {issue_key}")
        print("========================================")
        print(f"Summary:      {summary}")
        print("----------------------------------------")
        print("Description:")
        print(description)
        print("========================================")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except lib.SyncException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
