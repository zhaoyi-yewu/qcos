#!/bin/bash
# ----------------------------------------------------------------------
# Copyright© 2024-2026 China Mobile (SuZhou) Software Technology Co.,Ltd.
#
# qcos is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions
# of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#         http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# ----------------------------------------------------------------------

set -uo pipefail

# ===== Configuration =====
gitee_token="${gitee_token:-}"
target_owner="WUYUEQbit"
target_repo="qcos"
target_branch="develop"
source_owner="guo-zhufeng"
source_repo="qcos"
branch_prefix="commit-"

# ===== Check dependencies =====
for cmd in curl jq date; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "错误：缺少依赖命令 $cmd，请先安装" >&2
        exit 1
    fi
done

# ===== Check environment variables =====
if [ -z "$gitee_token" ]; then
    echo "错误：未配置环境变量 gitee_token" >&2
    exit 1
fi

# ===== Helper: die =====
die() {
    echo "Fatal error: $1" >&2
    exit 2
}

# ===== get_all_commit_branches =====
# 输出所有以 commit- 为前缀的分支名，每行一个
get_all_commit_branches() {
    local page=1
    while true; do
        local url="https://gitee.com/api/v5/repos/${source_owner}/${source_repo}/branches"
        local response http_code

        response=$(curl -s -w '\n%{http_code}' \
            -H "Authorization: token ${gitee_token}" \
            "${url}?page=${page}&per_page=100" 2>/dev/null)

        http_code=$(echo "$response" | tail -1)
        local body
        body=$(echo "$response" | sed '$d')

        if [ "$http_code" != "200" ] || [ "$(echo "$body" | jq 'length')" -eq 0 ]; then
            break
        fi

        # 提取以 commit- 为前缀的分支名
        echo "$body" | jq -r '.[].name' | grep "^${branch_prefix}"

        page=$((page + 1))
    done
}

# ===== get_branch_number_map =====
# 读取分支名列表（stdin），输出 "num<TAB>branch_name" 到全局数组
# 设置全局变量 _number_map_keys（有序）和 _max_num
declare -A _number_map=()
_max_num=0

get_branch_number_map() {
    _number_map=()
    _max_num=0

    while IFS= read -r branch; do
        [ -z "$branch" ] && continue
        local num_str="${branch#${branch_prefix}}"
        if [[ "$num_str" =~ ^[0-9]+$ ]]; then
            local num=$((10#$num_str))
            _number_map["$num"]="$branch"
            if [ "$num" -gt "$_max_num" ]; then
                _max_num="$num"
            fi
        fi
    done
}

# ===== get_latest_commit_message =====
# 获取分支最新 commit 的 message（第一行）和 sha 前7位
get_latest_commit_message() {
    local branch="$1"
    local url="https://gitee.com/api/v5/repos/${source_owner}/${source_repo}/branches/${branch}"

    local response http_code body
    response=$(curl -s -w '\n%{http_code}' \
        -H "Authorization: token ${gitee_token}" \
        "$url" 2>/dev/null)

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ]; then
        local message sha_short
        message=$(echo "$body" | jq -r '.commit.commit.message' | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        sha_short=$(echo "$body" | jq -r '.commit.sha' | cut -c1-7)
        echo "${message} (${sha_short})"
    else
        echo "${branch}"
    fi
}

# ===== create_pr =====
create_pr() {
    local branch="$1"
    local today
    today=$(date '+%Y-%m-%d')

    local commit_msg
    commit_msg=$(get_latest_commit_message "$branch")

    local pr_title="[Code synchronization] ${today} ${commit_msg}"

    local api="https://gitee.com/api/v5/repos/${target_owner}/${target_repo}/pulls"
    local json_data
    json_data=$(jq -n \
        --arg title "$pr_title" \
        --arg head "${source_owner}:${branch}" \
        --arg base "$target_branch" \
        --arg body "1. ${commit_msg}" \
        '{title: $title, head: $head, base: $base, body: $body}')

    local response http_code body
    response=$(curl -s -w '\n%{http_code}' \
        -X POST \
        -H "Authorization: token ${gitee_token}" \
        -H "Content-Type: application/json" \
        -d "$json_data" \
        "$api" 2>/dev/null)

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "201" ]; then
        local html_url
        html_url=$(echo "$body" | jq -r '.html_url')
        echo "${branch} → ${target_branch}"
        echo "标题：${pr_title}"
        echo "链接：${html_url}"
        echo ""
    else
        echo "${branch} 失败：${http_code} ${body}"
        echo ""
    fi
}

# ===== main =====
main() {
    echo "===== 开始批量创建 Gitee PR ====="

    local raw_branches
    raw_branches=$(get_all_commit_branches)

    if [ -z "$raw_branches" ]; then
        echo "未找到任何以 commit- 为前缀的分支，退出"
        return 0
    fi

    get_branch_number_map <<< "$raw_branches"

    if [ ${#_number_map[@]} -eq 0 ]; then
        echo "未找到含有效数字的 commit- 分支（如 commit-1），退出"
        return 0
    fi

    local num
    for ((num = 1; num <= _max_num; num++)); do
        if [ -n "${_number_map[$num]:-}" ]; then
            local branch="${_number_map[$num]}"
            echo "开始处理分支：${branch}（数字 ${num}）"
            create_pr "$branch"
        else
            echo "跳过缺失分支：${branch_prefix}${num}"
            echo ""
        fi
    done

    echo "===== 全部完成 ====="
    return 0
}

main "$@"
