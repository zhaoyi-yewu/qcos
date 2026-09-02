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
Create Pull-Request

Prerequisite:
pip3 install --break-system-packages requests

Gitee API:
https://gitee.com/api/v5/swagger
"""


import argparse
import os
import requests
import sys


gitee_access_token = os.getenv("GITEE_ACCESS_TOKEN")
target_owner = "WUYUEQbit"
target_repo = "qcos"
target_branch = "develop"
source_owner = ""
source_repo = "qcos"
branch_prefix = "feature_new-"

required_envs = {
    "GITEE_ACCESS_TOKEN": gitee_access_token,
}
missing_envs = [k for k, v in required_envs.items() if not v]
if missing_envs:
    print(f"错误：未配置环境变量 {', '.join(missing_envs)}")
    exit(1)

headers = {"Authorization": f"token {gitee_access_token}"}


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

        # Select branches that start with feature_new-
        for branch in res.json():
            name = branch["name"]
            if name.startswith(branch_prefix):
                branches.append(name)
        page += 1
    return branches


def get_branch_number_map(branches):
    """
    Get Mapping of the branch list
    Args:
        branches: branch list
    Returns:
        number_map: Mapping from numbers to branch names
        max_num: the largest number
    """
    number_map = {}
    max_num = 0
    for branch in branches:
        num_str = branch.replace(branch_prefix, "")
        if num_str.isdigit():
            num = int(num_str)
            number_map[num] = branch
            if num > max_num:
                max_num = num
    return number_map, max_num


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
    commit_msg = get_latest_commit_message(branch)
    pr_title = f"{commit_msg}"

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
    global source_owner

    parser = argparse.ArgumentParser(
        description="Batch create Gitee Pull Requests"
    )
    parser.add_argument(
        "--source-owner",
        dest="source_owner",
        required=True,
        help="Source repository owner (Gitee user/org name)",
    )
    args = parser.parse_args()
    source_owner = args.source_owner

    print("===== 开始批量创建 Gitee PR =====")
    raw_branches = get_all_commit_branches()
    if not raw_branches:
        print(f"未找到任何以 {branch_prefix} 为前缀的分支，退出")
        return 0

    branch_num_map, max_num = get_branch_number_map(raw_branches)
    if not branch_num_map:
        print(f"未找到含有效数字的 {branch_prefix} 分支（如 {branch_prefix}-1），退出")
        return 0

    for num in range(1, max_num + 1):
        if num in branch_num_map:
            branch = branch_num_map[num]
            print(f"开始处理分支：{branch}（数字 {num}）")
            create_pr(branch)
        else:
            print(f"跳过缺失分支：{branch_prefix}{num}\n")

    print("===== 全部完成 =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
