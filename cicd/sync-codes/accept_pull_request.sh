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
gitee_access_token="${gitee_access_token:-}"
owner="WUYUEQbit"
repo="qcos"
api_base="https://gitee.com/api/v5/repos"

# ===== Check dependencies =====
for cmd in curl jq; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "错误：缺少依赖命令 $cmd，请先安装" >&2
        exit 1
    fi
done

# ===== Check environment variables =====
if [ -z "$gitee_access_token" ]; then
    echo "错误：未配置环境变量 gitee_access_token" >&2
    exit 1
fi

# ===== Helper: die =====
die() {
    echo "Fatal error: $1" >&2
    exit 2
}

# ===== get_pr_list_by_time =====
# 获取 PR 列表，输出 JSON 数组到 stdout
# 全局数组 _pr_numbers 和 _pr_info 在调用后填充
_pr_numbers=()
_pr_info=()

get_pr_list_by_time() {
    local state="${1:-open}"
    local sort="${2:-created}"
    local direction="${3:-asc}"

    local url="${api_base}/${owner}/${repo}/pulls"
    local response http_code body

    response=$(curl -s -w '\n%{http_code}' \
        -H "Content-Type: application/json;charset=UTF-8" \
        "${url}?access_token=${gitee_access_token}&state=${state}&sort=${sort}&direction=${direction}&per_page=100" \
        2>/dev/null) || die "获取PR列表失败: curl 请求出错"

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" != "200" ]; then
        echo "获取PR列表失败: HTTP ${http_code}, ${body}" >&2
        return 1
    fi

    local pr_count
    pr_count=$(echo "$body" | jq 'length')

    if [ "$pr_count" -eq 0 ] || [ "$pr_count" = "null" ]; then
        echo "未找到状态为 ${state} 的PR"
        return 1
    fi

    echo ""
    echo "=== 找到 ${pr_count} 个 ${state} 状态的PR（按${sort} ${direction}排序）==="

    # 清空全局数组
    _pr_numbers=()
    _pr_info=()

    local idx=0
    while IFS=$'\t' read -r number title created_at login; do
        [ -z "$number" ] && continue
        idx=$((idx + 1))
        echo "${idx}. PR#${number} | 标题: ${title} | 创建时间: ${created_at} | 作者: ${login}"
        _pr_numbers+=("$number")
        _pr_info+=("PR#${number} | 标题: ${title} | 创建时间: ${created_at} | 作者: ${login}")
    done < <(echo "$body" | jq -r \
        '.[] | [.number, .title, .created_at, .user.login] | @tsv')

    return 0
}

# ===== gitee_action =====
gitee_action() {
    local pr_number="$1"
    local action_type="$2"

    local base_url="${api_base}/${owner}/${repo}/pulls/${pr_number}"

    local url method data
    local response http_code body

    case "$action_type" in
        approve)
            url="${base_url}/review"
            method="POST"
            data='{"force": true}'
            ;;
        test)
            url="${base_url}/test"
            method="POST"
            data='{"force": true}'
            ;;
        merge)
            url="${base_url}/merge"
            method="PUT"
            data='{"merge_method": "merge"}'
            ;;
        *)
            echo "PR#${pr_number} 跳过不支持的操作: ${action_type}"
            return 0
            ;;
    esac

    response=$(curl -s -w '\n%{http_code}' \
        -X "$method" \
        -H "Content-Type: application/json;charset=UTF-8" \
        -d "$data" \
        "${url}?access_token=${gitee_access_token}" \
        2>/dev/null) || die "PR#${pr_number} 执行 ${action_type} 失败: curl 请求出错"

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "PR#${pr_number} 成功执行: ${action_type}"
    else
        if [ "$action_type" = "merge" ]; then
            echo "PR#${pr_number} 执行 ${action_type} 失败: ${http_code}, ${body}" >&2
            exit 1
        else
            echo "PR#${pr_number} 执行 ${action_type} 失败: ${http_code}, ${body}"
        fi
    fi
}

# ===== main =====
main() {
    # 1. 获取 open 状态的 PR 列表
    get_pr_list_by_time "open" "created" "asc"
    if [ $? -ne 0 ]; then
        exit 0
    fi

    if [ "${#_pr_numbers[@]}" -eq 0 ]; then
        echo "没有需要处理的 PR，退出"
        exit 0
    fi

    # 2. 按创建时间顺序合并 PR
    echo ""
    echo "=== 开始按创建时间顺序合并PR ==="

    for pr_number in "${_pr_numbers[@]}"; do
        echo ""
        echo "===== 处理 PR#${pr_number} ====="
        gitee_action "$pr_number" "approve"
        gitee_action "$pr_number" "test"
        gitee_action "$pr_number" "merge"
    done

    echo ""
    echo "===== 全部完成 ====="
}

main "$@"
