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
./sync-issues.py QIS-504
./sync-issues.py QIS-504 --user "test:test --url "http://jira.com"
"""

import base64
import json
import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import requests

# default jira base url
jira_base_url = "http://jira.com"

# default basic auth credentials (username:password)
jira_auth = "test:test"


class SyncException(Exception):
    """Sync Exception."""


def fetch_issue(issue_id, base_url, auth):
    """Fetch a Jira issue via requests and return parsed JSON.

    Args:
        issue_id: Jira issue key, e.g. QIS-504
        base_url: Jira base URL
        auth: basic auth credentials "user:pass"

    Returns:
        parsed JSON dict of the issue
    """
    api_url = f"{base_url}/rest/api/2/issue/{issue_id}"
    # build Basic auth header from "user:pass"
    auth_bytes = auth.encode("utf-8")
    auth_header = "Basic " + base64.b64encode(auth_bytes).decode("utf-8")
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header,
    }
    print(f"Fetching issue: {issue_id} from {base_url}")
    try:
        response = requests.get(
            api_url, headers=headers, timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Request failed: {e}"
        ) from e
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        raise SyncException(
            f"Failed to parse JSON response: {e}\n"
            f"Raw output (first 500 chars): "
            f"{response.text[:500]}"
        ) from e
    return data


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
            "issue_id",
            help="Jira issue ID, e.g. QIS-504",
        )
        parser.add_argument(
            "--url",
            dest="base_url",
            default=jira_base_url,
            help=f"Jira base URL (default: {jira_base_url})",
        )
        parser.add_argument(
            "--user",
            dest="auth",
            default=jira_auth,
            help='Basic auth credentials "user:pass" '
                 f"(default: {jira_auth})",
        )

        args = parser.parse_args()
        issue_id = args.issue_id
        base_url = args.base_url
        auth = args.auth

        print("==== Fetch Jira issue ====")
        print(f"Issue:   {issue_id}")
        print(f"URL:     {base_url}")

        issue_data = fetch_issue(issue_id, base_url, auth)
        issue_key, summary, description = parse_issue(issue_data)

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
    except SyncException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
