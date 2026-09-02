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
Sync code reviews - fetch GitLab MR status, author and discussions.

This script calls the GitLab REST API to retrieve a merge request's
state, author, and all discussion comments (including reviewer,
comment body, and code file/line info).

Prerequisite:
pip3 install --break-system-packages requests

Examples:
./sync-code-reviews.py 1155 --token "token" --url "http://gitlab.com" --project WuYueOs
"""

import sys
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from urllib.parse import quote

import requests

# default gitlab base url
gitlab_base_url = "http://gitlab.com"

# default project path
gitlab_project = "WuYueOs"

# default private token
gitlab_token = ""


class SyncException(Exception):
    """Sync Exception."""


def fetch_mr_info(mr_iid, project, base_url, token):
    """Fetch merge request info from GitLab API.

    Args:
        mr_iid: merge request internal ID, e.g. 1155
        project: project path, e.g. WuYueOs
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON dict of the merge request
    """
    project_encoded = quote(project, safe="")
    api_url = (
        f"{base_url}/api/v4/projects/"
        f"{project_encoded}/merge_requests/{mr_iid}"
    )
    headers = {"PRIVATE-TOKEN": token}
    print(f"Fetching MR info: {project}!{mr_iid} from {base_url}")
    try:
        response = requests.get(
            api_url, headers=headers, timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(f"Request failed: {e}") from e
    return response.json()


def fetch_mr_discussions(mr_iid, project, base_url, token):
    """Fetch merge request discussions from GitLab API.

    Args:
        mr_iid: merge request internal ID, e.g. 1155
        project: project path, e.g. WuYueOs
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON list of discussions
    """
    project_encoded = quote(project, safe="")
    api_url = (
        f"{base_url}/api/v4/projects/"
        f"{project_encoded}/merge_requests/{mr_iid}/discussions"
    )
    headers = {"PRIVATE-TOKEN": token}
    print(f"Fetching MR discussions: {project}!{mr_iid}")
    try:
        response = requests.get(
            api_url, headers=headers, timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(f"Request failed: {e}") from e
    return response.json()


def fetch_mr_pipelines(mr_iid, project, base_url, token):
    """Fetch pipelines associated with a merge request.

    Args:
        mr_iid: merge request internal ID, e.g. 1155
        project: project path, e.g. WuYueOs
        base_url: GitLab base URL
        token: private access token

    Returns:
        parsed JSON list of pipelines
    """
    project_encoded = quote(project, safe="")
    api_url = (
        f"{base_url}/api/v4/projects/"
        f"{project_encoded}/merge_requests/{mr_iid}/pipelines"
    )
    headers = {"PRIVATE-TOKEN": token}
    print(f"Fetching MR pipelines: {project}!{mr_iid}")
    try:
        response = requests.get(
            api_url, headers=headers, timeout=30
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SyncException(f"Request failed: {e}") from e
    return response.json()


def parse_mr_info(mr_data):
    """Extract state and author from MR data.

    Args:
        mr_data: parsed JSON dict of the merge request

    Returns:
        dict with mr_iid, title, state, author_name,
        author_username, source_branch, target_branch
    """
    author = mr_data.get("author", {})
    return {
        "mr_iid": mr_data.get("iid", "UNKNOWN"),
        "title": mr_data.get("title", ""),
        "state": mr_data.get("state", ""),
        "author_name": author.get("name", ""),
        "author_username": author.get("username", ""),
        "source_branch": mr_data.get("source_branch", ""),
        "target_branch": mr_data.get("target_branch", ""),
        "created_at": mr_data.get("created_at", ""),
        "merged_at": mr_data.get("merged_at", ""),
    }


def parse_discussions(discussions):
    """Extract comment info from discussions.

    For each note, extract reviewer, body, and code file/line
    info if available (from the position field).

    Args:
        discussions: parsed JSON list of discussions

    Returns:
        list of comment dicts
    """
    comments = []
    for discussion in discussions:
        notes = discussion.get("notes", [])
        for note in notes:
            author = note.get("author", {})
            position = note.get("position")
            comments.append({
                "discussion_id": discussion.get("id", ""),
                "note_id": note.get("id", ""),
                "author_name": author.get("name", ""),
                "author_username": author.get("username", ""),
                "body": note.get("body", ""),
                "system": note.get("system", False),
                "created_at": note.get("created_at", ""),
                "position": position,
            })
    return comments


def parse_pipelines(pipelines):
    """Extract pipeline info from pipeline list.

    Args:
        pipelines: parsed JSON list of pipelines

    Returns:
        list of pipeline dicts with pipeline_id,
        commit_id, status, ref, web_url
    """
    result = []
    for pipeline in pipelines:
        result.append({
            "pipeline_id": pipeline.get("id", ""),
            "commit_id": pipeline.get("sha", ""),
            "status": pipeline.get("status", ""),
            "ref": pipeline.get("ref", ""),
            "web_url": pipeline.get("web_url", ""),
        })
    return result


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
            "mr_iid",
            type=int,
            help="Merge request IID, e.g. 1155",
        )
        parser.add_argument(
            "--project",
            dest="project",
            default=gitlab_project,
            help=f"Project path (default: {gitlab_project})",
        )
        parser.add_argument(
            "--url",
            dest="base_url",
            default=gitlab_base_url,
            help=f"GitLab base URL (default: {gitlab_base_url})",
        )
        parser.add_argument(
            "--token",
            dest="token",
            default=gitlab_token,
            help="GitLab private access token",
        )

        args = parser.parse_args()
        mr_iid = args.mr_iid
        project = args.project
        base_url = args.base_url
        token = args.token

        print("==== Fetch GitLab MR code reviews ====")
        print(f"MR IID:  {mr_iid}")
        print(f"Project: {project}")
        print(f"URL:     {base_url}")

        mr_data = fetch_mr_info(
            mr_iid, project, base_url, token
        )
        mr_info = parse_mr_info(mr_data)

        discussions = fetch_mr_discussions(
            mr_iid, project, base_url, token
        )
        comments = parse_discussions(discussions)

        pipelines = fetch_mr_pipelines(
            mr_iid, project, base_url, token
        )
        pipeline_infos = parse_pipelines(pipelines)

        print("\n========================================")
        print(f"MR:        {mr_info['mr_iid']}")
        print(f"Title:     {mr_info['title']}")
        print(f"State:     {mr_info['state']}")
        print(f"Author:    {mr_info['author_name']}"
              f" (@{mr_info['author_username']})")
        print(f"Branch:    {mr_info['source_branch']}"
              f" -> {mr_info['target_branch']}")
        print(f"Created:   {mr_info['created_at']}")
        if mr_info["merged_at"]:
            print(f"Merged:    {mr_info['merged_at']}")
        print("========================================")

        print(f"\nPipelines ({len(pipeline_infos)} total):")
        print("----------------------------------------")
        for p in pipeline_infos:
            print(f"  Pipeline ID: {p['pipeline_id']}")
            print(f"  Commit ID:   {p['commit_id']}")
            print(f"  Status:      {p['status']}")
            print(f"  Ref:         {p['ref']}")
            print()
        print("========================================")

        user_comments = [c for c in comments if not c["system"]]
        print(f"\nComments ({len(user_comments)} total):")
        print("----------------------------------------")
        for i, c in enumerate(user_comments, 1):
            print(f"\n{i}. @{c['author_username']}"
                  f" ({c['author_name']})")
            print(f"   Time: {c['created_at']}")
            if c["position"]:
                print(f"   File: {c['position']}")
            print(f"   Body: {c['body']}")
        print("\n========================================")
        return 0
    except KeyboardInterrupt:
        print("\nUser interrupt", file=sys.stderr)
        return 0
    except SyncException as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
