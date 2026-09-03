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
"""

import os
import requests
import sys

gitee_access_token = os.getenv("GITEE_ACCESS_TOKEN")
owner = "WUYUEQbit"
repo = "qcos"
branch_prefix = "feature_new-"

required_envs = {
    "GITEE_ACCESS_TOKEN": gitee_access_token,

}
missing_envs = [k for k, v in required_envs.items() if not v]
if missing_envs:
    print(f"错误：未配置环境变量 {', '.join(missing_envs)}")
    exit(1)

api_base = "https://gitee.com/api/v5/repos"
headers = {"Content-Type": "application/json;charset=UTF-8"}
common_params = {"access_token": gitee_access_token}


def get_pr_list_by_time(
        state: str = "open",
        sort: str = "created",
        direction: str = "asc",
) -> list:
    """Get the PR list in chronological order

    Args:
        state: PR Status open/closed/all
        sort: Sorting field, default created
        direction: Sort direction, asc (earliest first)

    Returns:
        Sorted PR list
    """
    url = f"{api_base}/{owner}/{repo}/pulls"
    params = {
        **common_params,
        "state": state,
        "sort": sort,
        "direction": direction,
        "per_page": 100,  # The maximum number of PRs
    }

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        pr_list = response.json()

        if not pr_list:
            print(f"未找到状态为 {state} 的PR")
            return []

        print(
            f"\n=== 找到 {len(pr_list)} 个 {state} 状态的PR"
            f"（按{sort} {direction}排序）==="
        )
        for idx, pull_request in enumerate(pr_list, 1):
            create_time = pull_request["created_at"]
            print(
                f"{idx}. PR#{pull_request['number']} |"
                f" 标题: {pull_request['title']} |"
                f" 创建时间: {create_time} |"
                f" 作者: {pull_request['user']['login']}"
            )

        return pr_list
    except requests.exceptions.RequestException as e:
        print(f"获取PR列表失败: {str(e)}")
        return []


def gitee_action(pull_request_number: int, action_type: str):
    """Perform actions on the specified PR

    Args:
        pull_request_number: PR number to be operated
        action_type: operation type comment/approve/merge
    """
    params = {"access_token": gitee_access_token}
    base_url = f"{api_base}/{owner}/{repo}/pulls/{pull_request_number}"
    response = None

    if action_type == "approve":
        url = f"{base_url}/review"
        data = {"force": True}
        response = requests.post(
            url,
            params=params,
            json=data,
            headers=headers,
        )

    elif action_type == "test":
        url = f"{base_url}/test"
        data = {"force": True}
        response = requests.post(
            url,
            params=params,
            json=data,
            headers=headers,
        )

    elif action_type == "merge":
        url = f"{base_url}/merge"
        data = {
            "merge_method": "merge",
        }
        response = requests.put(
            url,
            params=params,
            json=data,
            headers=headers,
        )
    else:
        print(f"PR#{pull_request_number} 跳过不支持的操作: {action_type}")
        return

    if response:
        if response.status_code in [200, 201]:
            print(f"PR#{pull_request_number} 成功执行: {action_type}")
        else:
            if action_type == "merge":
                print(
                    f"PR#{pull_request_number} 执行 {action_type} 失败: "
                    f"{response.status_code}, {response.text}"
                )
                sys.exit()
    else:
        print(f"PR#{pull_request_number} 执行 {action_type} 无响应")


if __name__ == "__main__":
    # 1. Get open PRs
    open_prs = get_pr_list_by_time(
        state="open",
        sort="created",
        direction="asc",
    )
    if not open_prs:
        exit(0)

    # 2. Merge the earliest first (only PRs matching branch_prefix)
    print("\n=== 开始按创建时间顺序合并PR ===")
    print(f"仅处理源分支以 '{branch_prefix}' 开头的PR")
    for pr in open_prs:
        pr_number = pr["number"]
        source_branch = ""
        head = pr.get("head") or {}
        if isinstance(head, dict):
            source_branch = head.get("ref", "")
        if not source_branch.startswith(branch_prefix):
            print(
                f"\n===== 跳过 PR#{pr_number}"
                f"（源分支 '{source_branch}'"
                f" 不匹配前缀 '{branch_prefix}'）====="
            )
            continue
        print(f"\n===== 处理 PR#{pr_number} =====")
        gitee_action(pr_number, "approve")
        gitee_action(pr_number, "test")
        gitee_action(pr_number, "merge")
