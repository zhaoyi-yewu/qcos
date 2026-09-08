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
Common library for cicd/sync-codes scripts.

Provides shared utility functions for GitLab, Gitee, Jira APIs,
and subprocess command execution.
"""

import base64
import json
import re
import requests
import shlex
import subprocess
import sys
from urllib.parse import quote


# ======================================================================
# Constants
# ======================================================================

# Gitee defaults
gitee_api_base = "https://gitee.com/api/v5/repos"
gitee_owner = "WUYUEQbit"
gitee_repo = "qcos"

# Jira defaults
jira_base_url = "http://jira.com"
jira_auth = "test:test"

# GitLab defaults
gitlab_base_url = "http://gitlab.com"
gitlab_project = "WuYueOs"


# ======================================================================
# Exceptions
# ======================================================================

class SyncException(Exception):
    """Sync Exception."""


# ======================================================================
# Subprocess utilities
# ======================================================================

def run_command(command, cwd=None, check=True,
                capture_output=True, text=True):
    """Run a shell command.

    Args:
        command: command, a list of args or a shell string
            (split via shlex for shell strings)
        cwd: working directory to run the command in
        check: check exit code
        capture_output: capture output
        text: print text

    Returns:
        command results (subprocess.CompletedProcess)

    Raises:
        subprocess.CalledProcessError: if command fails and check=True
    """
    if isinstance(command, str):
        command = shlex.split(command)
    try:
        results = subprocess.run(
            command,
            shell=False,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=text,
        )
        return results
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {command}", file=sys.stderr)
        print(f"Error output: {e.stderr}", file=sys.stderr)
        raise


# ======================================================================
# GitLab API
# ======================================================================

def gitlab_get(path, base_url, token, params=None, timeout=30):
    """Send a GET request to GitLab API v4.

    Args:
        path: API path after /api/v4/ (e.g. "projects/123/merge_requests")
        base_url: GitLab base URL
        token: GitLab private access token
        params: query parameters dict
        timeout: request timeout in seconds

    Returns:
        parsed JSON response

    Raises:
        SyncException: on request failure
    """
    api_url = f"{base_url.rstrip('/')}/api/v4/{path}"
    headers = {"PRIVATE-TOKEN": token}
    try:
        resp = requests.get(
            api_url, headers=headers, params=params, timeout=timeout
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"GitLab API request failed: {e}"
        ) from e
    return resp.json()


def gitlab_get_paginated(path, base_url, token, params=None,
                         per_page=100, max_pages=100):
    """Fetch all pages from a paginated GitLab API endpoint.

    Args:
        path: API path after /api/v4/
        base_url: GitLab base URL
        token: GitLab private access token
        params: additional query parameters
        per_page: items per page
        max_pages: maximum number of pages to fetch

    Returns:
        list: all items from all pages
    """
    all_items = []
    if params is None:
        params = {}
    for page in range(1, max_pages + 1):
        page_params = {**params, "per_page": per_page, "page": page}
        data = gitlab_get(path, base_url, token, page_params)
        if not data:
            break
        all_items.extend(data)
    return all_items


def get_merge_requests(
    base_url, token, project_id,
    state="opened", per_page=100, page=None
):
    """Fetch merge requests from GitLab by state.

    Args:
        base_url: GitLab base URL
        token: GitLab access token
        project_id: GitLab project ID (numeric or path)
        state: MR state filter (opened/merged/closed/all)
        per_page: number of items per page
        page: specific page number; if None, fetch all pages

    Returns:
        dict: {mr_iid: {title, author, web_url, state, commits}}
    """
    mr_dict = {}
    # URL-encode project_id if it contains "/" (e.g. "OCRI/WuYueOs")
    project_id_encoded = quote(str(project_id), safe="")
    path = f"projects/{project_id_encoded}/merge_requests"

    if page is not None:
        params = {"state": state, "per_page": per_page, "page": page}
        data = gitlab_get(path, base_url, token, params)
        mrs = data
    else:
        params = {"state": state}
        mrs = gitlab_get_paginated(
            path, base_url, token, params, per_page
        )

    for mr in mrs:
        iid = mr["iid"]
        mr_dict[iid] = {
            "title": mr.get("title", ""),
            "author": mr.get("author", {}).get("name", ""),
            "web_url": mr.get("web_url", ""),
            "state": mr.get("state", ""),
            "commits": {},
        }
    return mr_dict


def get_mr_commits(base_url, token, project_id, mr_iid):
    """Fetch commits for a specific merge request.

    Args:
        base_url: GitLab base URL
        token: GitLab access token
        project_id: GitLab project ID
        mr_iid: Merge request internal ID

    Returns:
        dict: {commit_short_id: {summary, description,
                author_name, jira_id}}
    """
    # URL-encode project_id if it contains "/" (e.g. "OCRI/WuYueOs")
    project_id_encoded = quote(str(project_id), safe="")
    path = (
        f"projects/{project_id_encoded}/merge_requests/"
        f"{mr_iid}/commits"
    )
    commits_data = gitlab_get_paginated(path, base_url, token)
    commits_dict = {}
    for commit in commits_data:
        short_id = commit.get("short_id", commit.get("id", "")[:8])
        title = commit.get("title", "")
        message = commit.get("message", "").strip()
        lines = message.split("\n")
        description = (
            "\n".join(lines[2:]).strip() if len(lines) > 2 else ""
        )
        jira_id = (
            extract_jira_id(message) or (None, None)
        )
        commits_dict[short_id] = {
            "summary": title,
            "description": description,
            "author": commit.get("author_name", ""),
            "author_email": commit.get("author_email", ""),
            "jira_id": jira_id,
        }
    return commits_dict


def fetch_mr_info(mr_iid, project, base_url, token):
    """Fetch merge request info from GitLab API.

    Args:
        mr_iid: merge request internal ID
        project: project path (e.g. WuYueOs)
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON dict of the merge request
    """
    project_encoded = quote(str(project), safe="")
    path = (
        f"projects/{project_encoded}/merge_requests/{mr_iid}"
    )
    return gitlab_get(path, base_url, token)


def fetch_mr_discussions(mr_iid, project, base_url, token):
    """Fetch merge request discussions from GitLab API.

    Args:
        mr_iid: merge request internal ID
        project: project path
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON list of discussions
    """
    project_encoded = quote(str(project), safe="")
    path = (
        f"projects/{project_encoded}/merge_requests/"
        f"{mr_iid}/discussions"
    )
    return gitlab_get(path, base_url, token)


def fetch_mr_pipelines(mr_iid, project, base_url, token):
    """Fetch pipelines associated with a merge request.

    Args:
        mr_iid: merge request internal ID
        project: project path
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON list of pipelines
    """
    project_encoded = quote(str(project), safe="")
    path = (
        f"projects/{project_encoded}/merge_requests/"
        f"{mr_iid}/pipelines"
    )
    return gitlab_get(path, base_url, token)


# ======================================================================
# Gitee API
# ======================================================================

def gitee_get(owner, repo, path, token, params=None, timeout=30):
    """Send a GET request to Gitee API v5.

    Args:
        owner: Gitee repo owner
        repo: Gitee repo name
        path: API path after /repos/{owner}/{repo}/
        token: Gitee access token
        params: query parameters dict
        timeout: request timeout

    Returns:
        parsed JSON response

    Raises:
        SyncException: on request failure
    """
    api_url = f"{gitee_api_base}/{owner}/{path}"
    if repo:
        api_url = f"{gitee_api_base}/{owner}/{repo}/{path}"
    headers = {"Authorization": f"token {token}"}
    if params is None:
        params = {}
    try:
        resp = requests.get(
            api_url, headers=headers, params=params, timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Gitee API request failed: {e}"
        ) from e
    return resp.json()


def gitee_post(owner, repo, path, token, data, timeout=30):
    """Send a POST request to Gitee API v5.

    Args:
        owner: Gitee repo owner
        repo: Gitee repo name
        path: API path after /repos/{owner}/{repo}/
        token: Gitee access token
        data: JSON body dict
        timeout: request timeout

    Returns:
        tuple: (status_code, response_json or text)

    Raises:
        SyncException: on request failure
    """
    api_url = f"{gitee_api_base}/{owner}/{path}"
    if repo:
        api_url = f"{gitee_api_base}/{owner}/{repo}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json;charset=UTF-8",
    }
    post_data = {**data}
    try:
        resp = requests.post(
            api_url, json=post_data, headers=headers, timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Gitee API POST failed: {e}"
        ) from e
    try:
        return resp.status_code, resp.json()
    except (json.JSONDecodeError, ValueError):
        return resp.status_code, resp.text


def gitee_patch(owner, repo, path, token, data, timeout=30):
    """Send a PATCH request to Gitee API v5.

    Args:
        owner: Gitee repo owner
        repo: Gitee repo name
        path: API path after /repos/{owner}/{repo}/
        token: Gitee access token
        data: JSON body dict
        timeout: request timeout

    Returns:
        tuple: (status_code, response_json or text)

    Raises:
        SyncException: on request failure
    """
    api_url = f"{gitee_api_base}/{owner}/{path}"
    if repo:
        api_url = f"{gitee_api_base}/{owner}/{repo}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json;charset=UTF-8",
    }
    patch_data = {**data}
    try:
        resp = requests.patch(
            api_url, json=patch_data, headers=headers, timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Gitee API PATCH failed: {e}"
        ) from e
    try:
        return resp.status_code, resp.json()
    except (json.JSONDecodeError, ValueError):
        return resp.status_code, resp.text


def gitee_put(owner, repo, path, token, data, timeout=30):
    """Send a PUT request to Gitee API v5.

    Args:
        owner: Gitee repo owner
        repo: Gitee repo name
        path: API path after /repos/{owner}/{repo}/
        token: Gitee access token
        data: JSON body dict
        timeout: request timeout

    Returns:
        tuple: (status_code, response_json or text)

    Raises:
        SyncException: on request failure
    """
    api_url = f"{gitee_api_base}/{owner}/{path}"
    if repo:
        api_url = f"{gitee_api_base}/{owner}/{repo}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json;charset=UTF-8",
    }
    put_data = {**data}
    try:
        resp = requests.put(
            api_url, json=put_data, headers=headers, timeout=timeout
        )
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Gitee API PUT failed: {e}"
        ) from e
    try:
        return resp.status_code, resp.json()
    except (json.JSONDecodeError, ValueError):
        return resp.status_code, resp.text


def get_gitee_issues_with_jira_labels(token, owner=None, repo=None):
    """Fetch Gitee community issues and extract Jira IDs from labels.

    Args:
        token: Gitee access token
        owner: Gitee repo owner (default: gitee_owner)
        repo: Gitee repo name (default: gitee_repo)

    Returns:
        dict: {jira_id: {number, title, state}}
    """
    if owner is None:
        owner = gitee_owner
    if repo is None:
        repo = gitee_repo

    gitee_jira_map = {}
    for page in range(1, 101):
        params = {"state": "open", "per_page": 100, "page": page}
        try:
            issues = gitee_get(owner, repo, "issues", token, params)
        except SyncException:
            break
        if not issues:
            break
        for issue in issues:
            labels = issue.get("labels", [])
            for label in labels:
                if isinstance(label, dict):
                    label_name = label.get("name", "")
                else:
                    label_name = str(label)
                if label_name.startswith("jira-"):
                    jira_id = label_name
                    gitee_jira_map[jira_id] = {
                        "number": issue.get("number"),
                        "title": issue.get("title", ""),
                        "state": issue.get("state", "open"),
                    }
    return gitee_jira_map


def create_gitee_issue(
    token, owner, repo, gitee_jira_id, title, body,
        gitee_user_name, jira_type, labels=None
):
    """Create a Gitee community issue with jira label.

    Args:
        token: Gitee access token
        owner: Gitee repo owner
        repo: Gitee repo name
        gitee_jira_id: Gitee jira id
        title: issue title
        body: issue body text
        gitee_user_name: Gitee user name
        jira_type: jira type
        labels: additional label names

    Returns:
        dict: created issue data or None on failure
    """
    if labels is None:
        labels = []
    labels.append(gitee_jira_id)
    assignee = None
    issue_type = None
    if jira_type == "任务":
        issue_type = "任务"
        assignee = gitee_user_name
    if jira_type == "需求":
        issue_type = "需求"
    if jira_type == "Bug":
        issue_type = "缺陷"
        assignee = gitee_user_name

    data = {
        "title": title,
        "body": body,
        "labels": ",".join(labels),
        "owner": owner,
        "repo": repo,
        "issue_type": issue_type,
        "assignee": assignee,
    }
    try:
        status, resp_data = gitee_post(
            owner, None, "issues", token, data
        )
    except SyncException as e:
        print(f"  Error creating Gitee issue for {gitee_jira_id}: {e}")
        return None
    if status == 201:
        print(f"  Created Gitee issue for {gitee_jira_id}: "
              f"#{resp_data.get('number')}")
        return resp_data
    print(f"  Failed to create Gitee issue for {gitee_jira_id}: "
          f"{status}")
    return None


def close_gitee_issue(token, owner, repo, issue_number):
    """Close a Gitee community issue.

    Args:
        token: Gitee access token
        owner: Gitee repo owner
        repo: Gitee repo name
        issue_number: Gitee issue number

    Returns:
        bool: True if successfully closed
    """
    data = {"state": "closed"}
    try:
        status, _ = gitee_patch(
            owner, repo, f"issues/{issue_number}", token, data
        )
    except SyncException as e:
        print(f"  Error closing Gitee issue #{issue_number}: {e}")
        return False
    if status == 200:
        print(f"  Closed Gitee issue #{issue_number}")
        return True
    print(f"  Failed to close Gitee issue #{issue_number}: "
          f"{status}")
    return False


def get_pr_list_by_time(
    token, owner=None, repo=None,
    state="open", sort="created", direction="asc"
):
    """Get the PR list in chronological order.

    Args:
        token: Gitee access token
        owner: Gitee repo owner
        repo: Gitee repo name
        state: PR state (open/closed/all)
        sort: sorting field
        direction: sort direction (asc/desc)

    Returns:
        list: PR list sorted by time
    """
    if owner is None:
        owner = gitee_owner
    if repo is None:
        repo = gitee_repo

    pr_list = []
    for page in range(1, 101):
        params = {
            "state": state,
            "sort": sort,
            "direction": direction,
            "per_page": 100,
            "page": page,
        }
        try:
            data = gitee_get(owner, repo, "pulls", token, params)
        except SyncException:
            break
        if not data:
            break
        pr_list.extend(data)
    return pr_list


def gitee_pr_action(
    token, owner, repo, pull_request_number, action_type
):
    """Perform actions on a Gitee PR.

    Args:
        token: Gitee access token
        owner: Gitee repo owner
        repo: Gitee repo name
        pull_request_number: PR number
        action_type: "approve" / "test" / "merge"

    Returns:
        bool: True if action succeeded
    """
    base_path = f"pulls/{pull_request_number}"
    data = {"force": True}

    if action_type == "approve":
        status, _ = gitee_post(
            owner, repo, f"{base_path}/review", token, data
        )
    elif action_type == "test":
        status, _ = gitee_post(
            owner, repo, f"{base_path}/test", token, data
        )
    elif action_type == "merge":
        merge_data = {"merge_method": "merge"}
        status, _ = gitee_put(
            owner, repo, f"{base_path}/merge", token, merge_data
        )
    else:
        print(f"PR#{pull_request_number} "
              f"unsupported action: {action_type}")
        return False

    if status in [200, 201]:
        print(f"PR#{pull_request_number} "
              f"success: {action_type}")
        return True
    print(f"PR#{pull_request_number} "
          f"failed: {action_type} (HTTP {status})")
    return False


# ======================================================================
# Jira API
# ======================================================================

def fetch_jira_issue(jira_id, base_url=None, auth=None):
    """Fetch a Jira issue via REST API.

    Args:
        jira_id: Jira issue key, e.g. QCOS-123
        base_url: Jira base URL (default: jira_base_url)
        auth: basic auth "user:pass" (default: jira_auth)

    Returns:
        dict: {key, summary, description, status} or None if 404

    Raises:
        SyncException: on request failure
    """
    if base_url is None:
        base_url = jira_base_url
    if auth is None:
        auth = jira_auth

    api_url = f"{base_url.rstrip('/')}/rest/api/2/issue/{jira_id}"
    auth_bytes = auth.encode("utf-8")
    auth_header = "Basic " + base64.b64encode(
        auth_bytes
    ).decode("utf-8")
    headers = {
        "Accept": "application/json",
        "Authorization": auth_header,
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(
            f"Failed to fetch Jira issue {jira_id}: {e}"
        ) from e
    try:
        data = resp.json()
    except json.JSONDecodeError as e:
        raise SyncException(
            f"Failed to parse Jira response for {jira_id}: {e}"
        ) from e
    fields = data.get("fields", {})
    status_obj = fields.get("status", {})
    reporter = data["fields"]["reporter"]
    return {
        "jira_id": jira_id,
        "jira_num": extract_jira_num(jira_id),
        "jira_type": fields["issuetype"]["name"], # '任务', '需求', 'Bug'
        "summary": fields.get("summary", ""),
        "description": fields.get("description", ""),
        "status": status_obj.get("name", "Unknown"),
        "reporter_name": reporter["name"],
        "reporter_email": reporter["emailAddress"],
    }


def is_jira_closed(jira_issue_data):
    """Check if a Jira issue is in a closed/resolved state.

    Args:
        jira_issue_data: dict from fetch_jira_issue

    Returns:
        bool: True if issue is closed/resolved
    """
    if not jira_issue_data:
        return False
    status = jira_issue_data.get("status", "").lower()
    closed_keywords = ["closed", "done", "resolved", "completed"]
    return any(kw in status for kw in closed_keywords)


# ======================================================================
# Text utilities
# ======================================================================

# regex to extract Jira ID from commit message
# matches "Jira: #QCOS-514", "Jira: QCOS-514", "Jira: #514", etc.
# group(1): optional project prefix (e.g. "QCOS-")
# group(2): numeric part (e.g. "514")
_jira_regex = re.compile(
    r"Jira:\s*#?([A-Za-z]+-)?(\d+)", re.IGNORECASE
)
# regex to extract Jira ID number from a Jira key
# matches "QCOS-434" -> "434", "434" -> "434"
_jira_num_regex = re.compile(r"(\d+)")


def extract_jira_id(commit_message):
    """Extract Jira ID from commit message in two formats.

    Matches patterns like:
    - "Jira: QCOS-514" -> "QCOS-514"
    - "Jira: #QCOS-514" -> "QCOS-514"

    Args:
        commit_message: full commit message string

    Returns:
        jira id key
    """
    match = _jira_regex.search(commit_message)
    if match:
        prefix = match.group(1) or ""
        number = match.group(2)
        full_key = f"{prefix}{number}".upper()
        return full_key
    return None


def extract_jira_num(jira_id):
    """Extract the numeric part from a Jira ID.

    Matches patterns like:
    - "QCOS-434" -> "434"
    - "434" -> "434"

    Args:
        jira_id: Jira ID string, e.g. "QCOS-434"

    Returns:
        str or None: Jira ID number (digits only) or None
    """
    match = _jira_num_regex.search(jira_id)
    if match:
        return match.group(1)
    return None


def get_gitee_developer_account(gitee_user_name, gitee_user_tokens):
    """Get gitee developer's account.

    Args:
        gitee_user_name: gitee user name
        gitee_user_tokens: gitee developer's tokens

    Returns:
        gitee user account
    """
    return gitee_user_tokens.get(gitee_user_name, None)
