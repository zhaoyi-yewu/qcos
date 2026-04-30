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

import os
import sys
import requests
from datetime import datetime

gitee_token = os.getenv("gitee_token")
target_owner = "OpenWuYue"
target_repo = "qcos"
target_branch = "develop"
source_owner = ""
source_repo = "qcos"
branch_prefix = "commit-"

required_envs = {
    "gitee_token": gitee_token,

}
missing_envs = [k for k, v in required_envs.items() if not v]
if missing_envs:
    print(f"错误：未配置环境变量 {', '.join(missing_envs)}")
    exit(1)

headers = {"Authorization": f"token {gitee_token}"}


def get_all_commit_branches():
    """Get branches

    Returns:
        branch name list
    """
    branches = []
    page = 1
    while True:
        # Gitee API get branch
        url = (
            f"https://gitee.com/api/v5/repos/"
            f"{source_owner}/{source_repo}/branches"
        )
        params = {"page": page, "per_page": 100}

        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200 or len(res.json()) == 0:
            break

        # Select branches that start with commit-
        for branch in res.json():
            name = branch["name"]
            if name.startswith(branch_prefix):
                branches.append(name)
        page += 1
    return branches

def get_latest_commit_message(branch):
    """Get latest commit message.

    Args:
        branch: branch

    Returns:
        branch name
    """
    url = (
        f"https://gitee.com/api/v5/repos/"
        f"{source_owner}/{source_repo}/branches/{branch}"
    )
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            commit = res.json()["commit"]
            message = commit["commit"]["message"].split("\n")[0].strip()
            sha_short = commit["sha"][:7]
            return f"{message} ({sha_short})"
        return f"{branch}"
    except Exception:
        return f"{branch}"

def create_pr(branch):
    """Create pull request.

    Args:
        branch: branch
    """
    today = datetime.now().strftime("%Y-%m-%d")
    commit_msg = get_latest_commit_message(branch)
    pr_title = f"[Code synchronization] {today} {commit_msg}"

    api = (
        f"https://gitee.com/api/v5/repos/{target_owner}/{target_repo}/pulls"
    )
    data = {
        "title": pr_title,
        "head": f"{source_owner}:{branch}",
        "base": target_branch,
        "body": f"1. {commit_msg}"
    }

    res = requests.post(api, json=data, headers=headers)
    if res.status_code == 201:
        print(f"{branch} → {target_branch}")
        print(f"标题：{pr_title}")
        print(f"链接：{res.json()['html_url']}\n")
    else:
        print(f"{branch} 失败：{res.status_code} {res.text}\n")

def main():
    print("===== 开始批量创建 Gitee PR =====")
    branches = get_all_commit_branches()
    for branch in branches:
        create_pr(branch)
    print("===== 全部完成 =====")
    return 0

if __name__ == "__main__":
    sys.exit(main())
