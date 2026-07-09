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

#
# Merge local git branch to remote branch / Split commits to single branches
#
# Prerequisite:
#   yum install -y git
#
# 1. Initialize git repo (Init only once, no need to run in the next time)
#    mkdir WuYue
#    cd WuYue
#    git init
#    git remote add origin ssh://git@gitlab.cmss.com:2223/OCRI/WuYueOs.git
#    git remote add gitee git@gitee.com:WUYUEQbit/qcos.git
#    git checkout --orphan dev_gitee
#    git pull origin dev_gitee --allow-unrelated-histories
#    git branch --set-upstream-to=origin/dev_gitee dev_gitee
#
#    git checkout --orphan temp
#    git rm -rf .
#    git checkout --orphan gitee-develop
#    git pull gitee develop --allow-unrelated-histories
#    git branch --set-upstream-to=gitee/develop gitee-develop
#
# 2. One-click full sync (pull + diff + merge all new commits + push)
#    ./merge-to-gitee.sh -f -s "2025-11-01"
#
# 3. One-click sync specified commits (pull + merge + push)
#    ./merge-to-gitee.sh -f -c "12345 23456"
#
# 4. Split commits to single branches and push to Gitee
#    ./merge-to-gitee.sh -S -s "2025-11-01"  # Split commits since 2025-11-01
#    ./merge-to-gitee.sh -S -c "12345 23456"  # Split specified commits
#
# 5. Original commands are still available:
#    ./merge-to-gitee.sh -p                (pull only)
#    ./merge-to-gitee.sh -d                (diff only)
#    ./merge-to-gitee.sh -c {COMMIT_ID}    (merge only)
#

set -uo pipefail

# ===== Configuration =====
gitee_remote="gitee"
gitee_remote_branch="develop"
gitee_local_branch="gitee-develop"

cmss_remote="origin"
cmss_local_branch="dev_gitee"
cmss_local_merge_branch="gitee-merge"

# Empty tree object hash (used for root commits with no parent)
EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# ===== Temporary directory =====
WORK_TMPDIR="$(mktemp -d)"
trap 'rm -rf "$WORK_TMPDIR"' EXIT

# ===== Helper: die =====
die() {
    echo "Fatal error: $1" >&2
    exit 2
}

# ===== sort_commits_by_date =====
# 从 stdin 读取 commit hash（每行一个），按 committed_date 升序输出
sort_commits_by_date() {
    while read -r commit; do
        [ -z "$commit" ] && continue
        local cd
        cd=$(git log -1 --format='%cI' "$commit" 2>/dev/null || echo "0")
        printf '%s\t%s\n' "$cd" "$commit"
    done | sort | cut -f2
}

# ===== pull_branches =====
pull_branches() {
    git branch -D "$cmss_local_merge_branch" 2>/dev/null || true

    echo "Recreate branch: $cmss_local_merge_branch"
    if ! git checkout -b "$cmss_local_merge_branch" "$gitee_local_branch" 2>/dev/null; then
        git checkout "$cmss_local_merge_branch" \
            || die "Failed to checkout $cmss_local_merge_branch"
    fi

    echo "Fetch from $gitee_remote, branch: $gitee_remote_branch ..."
    {
        git reset --hard
        git cherry-pick --abort 2>/dev/null || true
        git checkout "$gitee_local_branch"
        git pull --rebase "$gitee_remote" \
            "${gitee_remote_branch}:${gitee_local_branch}"
    } || die "Failed to fetch from $gitee_remote"

    echo "Fetch codes from $cmss_remote, branch: $cmss_local_branch ..."
    {
        git checkout "$cmss_local_branch"
        git pull --rebase "$cmss_remote" \
            "${cmss_local_branch}:${cmss_local_branch}"
    } || die "Failed to fetch from $cmss_remote"
}

# ===== get_commits_dict =====
# Writes tab-separated lines to output_file:
#   content_hash  commit_hash  tree_hash  committed_date  authored_date  summary
get_commits_dict() {
    local branch_name="$1"
    local since_str="${2:-}"
    local output_file="$3"

    local since_opt=""
    if [ -n "$since_str" ]; then
        since_opt="--since=$since_str"
    fi

    : > "$output_file"

    while IFS=$'\t' read -r commit_hash tree_hash committed_date authored_date summary; do
        [ -z "$commit_hash" ] && continue

        # Get parent (or empty tree for root commits)
        local parent
        parent=$(git rev-parse "$commit_hash^" 2>/dev/null) || parent="$EMPTY_TREE"

        # Compute content hash = MD5 of full diff
        local content_hash
        content_hash=$(git diff "$parent" "$commit_hash" --no-color 2>/dev/null \
            | md5sum | cut -d' ' -f1)

        printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
            "$content_hash" "$commit_hash" "$tree_hash" \
            "$committed_date" "$authored_date" "$summary" >> "$output_file"
    done < <(git log --no-merges --topo-order \
                --format='%H%x09%T%x09%cI%x09%aI%x09%s' \
                $since_opt "$branch_name")
}

# ===== get_unsynced_commits =====
# Prints commit hashes (sorted by committed date) to stdout
get_unsynced_commits() {
    local since_str="${1:-}"
    local cmss_file="$WORK_TMPDIR/cmss_commits.txt"
    local gitee_file="$WORK_TMPDIR/gitee_commits.txt"

    get_commits_dict "$cmss_local_branch" "$since_str" "$cmss_file"
    get_commits_dict "$gitee_local_branch" "$since_str" "$gitee_file"

    # Extract content hashes (field 1), sorted for comm
    local cmss_hashes gitee_hashes
    cmss_hashes=$(cut -f1 "$cmss_file" | sort)
    gitee_hashes=$(cut -f1 "$gitee_file" | sort)

    # Find content hashes only in cmss
    local only_in_cmss
    only_in_cmss=$(comm -23 \
        <(printf '%s\n' "$cmss_hashes") \
        <(printf '%s\n' "$gitee_hashes"))

    if [ -z "$only_in_cmss" ]; then
        return
    fi

    # For each content hash only in cmss, get committed_date + commit_hash,
    # sort by committed_date, then output commit_hash
    while read -r chash; do
        [ -z "$chash" ] && continue
        awk -F'\t' -v target="$chash" \
            '$1 == target {print $4 "\t" $2}' "$cmss_file"
    done <<< "$only_in_cmss" | sort | cut -f2
}

# ===== diff_branches =====
diff_branches() {
    local since_str="${1:-}"
    local cmss_file="$WORK_TMPDIR/diff_cmss.txt"
    local gitee_file="$WORK_TMPDIR/diff_gitee.txt"

    get_commits_dict "$cmss_local_branch" "$since_str" "$cmss_file"
    get_commits_dict "$gitee_local_branch" "$since_str" "$gitee_file"

    local cmss_hashes gitee_hashes
    cmss_hashes=$(cut -f1 "$cmss_file" | sort)
    gitee_hashes=$(cut -f1 "$gitee_file" | sort)

    local only_in_cmss only_in_gitee
    only_in_cmss=$(comm -23 \
        <(printf '%s\n' "$cmss_hashes") \
        <(printf '%s\n' "$gitee_hashes"))
    only_in_gitee=$(comm -13 \
        <(printf '%s\n' "$cmss_hashes") \
        <(printf '%s\n' "$gitee_hashes"))

    # Print raw content hashes (matching Python: print(only_in_cmss))
    echo "$only_in_cmss"

    echo "========================================"
    echo "Commits in $cmss_local_branch but not in $gitee_local_branch"
    echo "========================================"
    if [ -n "$only_in_cmss" ]; then
        while read -r chash; do
            [ -z "$chash" ] && continue
            awk -F'\t' -v target="$chash" '
                $1 == target {
                    printf "%s\t[%s] cd: %s ad: %s %s\n", $4, $2, $4, $5, $6
                }' "$cmss_file"
        done <<< "$only_in_cmss" | sort -r | cut -f2-
    else
        echo "No"
    fi
    echo ""

    echo "========================================"
    echo "Commits in $gitee_local_branch but not in $cmss_local_branch"
    echo "========================================"
    if [ -n "$only_in_gitee" ]; then
        while read -r chash; do
            [ -z "$chash" ] && continue
            awk -F'\t' -v target="$chash" '
                $1 == target {
                    printf "%s\t[%s] cd: %s ad: %s %s\n", $4, $2, $4, $5, $6
                }' "$gitee_file"
        done <<< "$only_in_gitee" | sort -r | cut -f2-
    else
        echo "No"
    fi
    echo ""
}


# ===== sanitize_message =====
# Removes sensitive lines, replaces email domains, normalizes whitespace
sanitize_message() {
    local message="$1"

    printf '%s\n' "$message" | while IFS= read -r line || [ -n "$line" ]; do
        # Check if line should be removed (case-insensitive keyword match)
        if printf '%s' "$line" | grep -qiE \
            'jira:|code source from|市场项目|ai co-author:'; then
            continue
        fi

        # Replace email domain
        if printf '%s' "$line" | grep -q '@cmss.chinamobile.com' && \
           ! printf '%s' "$line" | grep -q '_yewu@'; then
            line=$(printf '%s' "$line" \
                | sed 's/@cmss.chinamobile.com/_yewu@cmss.chinamobile.com/g')
        fi

        # Strip leading/trailing whitespace from line
        line=$(printf '%s' "$line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

        printf '%s\n' "$line"
    done \
    | sed -e :a -e '/^$/{$d;N;ba}' \
    | awk 'BEGIN{p=0} /^$/{if(p)next;p=1;print;next} {p=0;print}'
}

# ===== sanitize_author (sets global new_email / new_name) =====
sanitize_author_inline() {
    local email="$1"
    local name="$2"
    new_email="$email"
    new_name="$name"
    if [[ "$email" == *@cmss.chinamobile.com ]] && \
       [[ "$email" != *_yewu@* ]]; then
        new_email="${email/@cmss.chinamobile.com/_yewu@cmss.chinamobile.com}"
        new_name="${name}_yewu"
    fi
}

# ===== amend_commit_with_sanitization (shared logic) =====
amend_commit_with_sanitization() {
    local author_email author_name message
    author_email=$(git log -1 --format=%ae)
    author_name=$(git log -1 --format=%an)
    message=$(git log -1 --format=%B)

    sanitize_author_inline "$author_email" "$author_name"

    local new_message
    new_message=$(sanitize_message "$message")

    # Amend with sanitized author
    git -c user.name="$new_name" -c user.email="$new_email" \
        commit --amend --no-edit \
        --author="$new_name <$new_email>"

    if [ "$new_message" != "$message" ]; then
        printf '%s\n' "$new_message" > "$WORK_TMPDIR/git_commit_msg.txt"
        git commit --amend --no-edit -F "$WORK_TMPDIR/git_commit_msg.txt"
    fi
}

# ===== create_single_commit_branch =====
# Sets _result_branch_name and _result_commit_hash on success
create_single_commit_branch() {
    local commit_hash="$1"
    local num="$2"
    local base_branch="$gitee_local_branch"
    local branch_name="commit-$num"

    if [ "$num" -gt 1 ]; then
        base_branch="commit-$((num - 1))"
    fi

    # 1. Delete existing branch
    git branch -D "$branch_name" 2>/dev/null || true
    # 2. Checkout base branch
    git checkout "$base_branch" || return 1
    # 3. Create new branch
    git checkout -b "$branch_name" || return 1
    # 4. Reset --hard
    git reset --hard
    # 5. Cherry-pick single commit
    git cherry-pick -m 1 "$commit_hash" || return 1

    # 6. Sanitize and amend
    amend_commit_with_sanitization || return 1

    local new_commit_hash
    new_commit_hash=$(git log -1 --format=%H)

    echo "Created branch [$branch_name] for commit" \
         "[$commit_hash] -> new commit [$new_commit_hash]"

    _result_branch_name="$branch_name"
    _result_commit_hash="$new_commit_hash"
}

# ===== push_single_branch =====
push_single_branch() {
    local branch_name="$1"
    if git push "$gitee_remote" "${branch_name}:${branch_name}"; then
        echo "Pushed branch [$branch_name] to Gitee success!"
    else
        die "Push branch [$branch_name] failed"
    fi
}

# ===== split_and_push_single_commits =====
split_and_push_single_commits() {
    local since_str="${1:-}"
    local commit_id="${2:-}"

    echo "==== Step 1: Pull latest code ===="
    pull_branches

    echo ""
    echo "==== Step 2: Determine commits to split ===="
    local target_commits=()
    if [ -n "$commit_id" ]; then
        if [[ "$commit_id" == *".."* ]]; then
            mapfile -t target_commits < <(
                git log --oneline --no-merges --format='%h' "$commit_id" | tac)
        else
            read -ra target_commits <<< "$commit_id"
        fi
        echo "Specified commits to split: ${target_commits[*]}"
    else
        mapfile -t target_commits < <(get_unsynced_commits "$since_str")
        if [ "${#target_commits[@]}" -eq 0 ]; then
            echo "No unsynced commits found, exit."
            return
        fi
        echo "Auto-found unsynced commits to split: ${target_commits[*]}"
    fi

    # 按 committed_date 升序排序，先推送时间早的 commit
    if [ "${#target_commits[@]}" -gt 0 ]; then
        mapfile -t target_commits < <(
            printf '%s\n' "${target_commits[@]}" | sort_commits_by_date)
        echo "Sorted commits by committed_date (ascending): ${target_commits[*]}"
    fi

    echo ""
    echo "==== Step 3: Split and push single commits ===="
    local total="${#target_commits[@]}"
    local i=0
    for commit in "${target_commits[@]}"; do
        i=$((i + 1))
        echo ""
        echo "Processing commit [$i/$total]: $commit"
        if create_single_commit_branch "$commit" "$i"; then
            push_single_branch "$_result_branch_name"
        else
            if [ -f ".git/CHERRY_PICK_HEAD" ] || \
               git diff --name-only --diff-filter=U 2>/dev/null | grep -q .; then
                git cherry-pick --abort 2>/dev/null || true
                die "Conflict detected during cherry-pick of commit [$commit], aborting script."
            fi
            echo "Failed to process commit [$commit] (non-conflict error), skipping..."
            git cherry-pick --abort 2>/dev/null || true
            continue
        fi
    done

    echo ""
    echo "==== Split and push all single commits completed! ===="
}


# ===== merge_branches =====
merge_branches() {
    local commit_id="$1"

    echo "Merge commits to branch: $cmss_local_merge_branch"

    # Checkout local merge branch
    git cherry-pick --abort 2>/dev/null || true
    git checkout "$cmss_local_merge_branch" \
        || die "Failed to checkout $cmss_local_merge_branch"

    # Analyze commits to merge
    local commits=()
    if [[ "$commit_id" == *".."* ]]; then
        mapfile -t commits < <(
            git log --oneline --no-merges --format='%h' "$commit_id" | tac)
    else
        read -ra commits <<< "$commit_id"
    fi

    # 按 committed_date 升序排序，先合并时间早的 commit
    if [ "${#commits[@]}" -gt 0 ]; then
        mapfile -t commits < <(
            printf '%s\n' "${commits[@]}" | sort_commits_by_date)
        echo "Sorted commits by committed_date (ascending): ${commits[*]}"
    fi

    local count="${#commits[@]}"
    if [ "$count" -eq 0 ]; then
        die "no commits found to merge"
    fi

    # Cherry-pick and amend for desensitization
    local merged_commit_ids=()
    local i=0
    for commit in "${commits[@]}"; do
        i=$((i + 1))
        echo "Processing commit [$i/$count]: $commit"
        git cherry-pick -m 1 "$commit" \
            || die "Failed to cherry-pick $commit"

        amend_commit_with_sanitization \
            || die "Failed to amend commit"

        local merged_commit
        merged_commit=$(git log -1 --format=%H)
        merged_commit_ids+=("$merged_commit")
    done

    echo "Successfully merged commits: ${merged_commit_ids[*]}"
}


# ===== push_to_gitee =====
push_to_gitee() {
    echo "Push to $gitee_remote/$gitee_remote_branch ..."
    if git push "$gitee_remote" \
        "${cmss_local_merge_branch}:${gitee_remote_branch}"; then
        echo "Push to gitee success!"
    else
        die "Push failed"
    fi
}

# ===== full_auto_sync =====
full_auto_sync() {
    local since_str="${1:-}"
    local commit_id="${2:-}"

    echo "==== Step 1: Pull latest code ===="
    pull_branches

    echo ""
    echo "==== Step 2: Determine commits to merge ===="
    local target_commits=""
    if [ -n "$commit_id" ]; then
        target_commits="$commit_id"
        echo "Specified commits to merge: $target_commits"
    else
        local unsynced
        unsynced=$(get_unsynced_commits "$since_str")
        if [ -z "$unsynced" ]; then
            echo "No unsynced commits found, exit."
            return
        fi
        target_commits=$(printf '%s' "$unsynced" | tr '\n' ' ' \
            | sed 's/[[:space:]]*$//')
        echo "Auto-found unsynced commits: $target_commits"
    fi

    echo ""
    echo "==== Step 3: Merge commits ===="
    merge_branches "$target_commits"

    echo ""
    echo "==== Step 4: Push to Gitee ===="
    push_to_gitee

    echo ""
    echo "==== One-click sync completed successfully! ===="
}

# ===== Usage =====
usage() {
    cat << 'EOF'
Merge local git branch to remote branch / Split commits to single branches

USAGE:
  ./merge-to-gitee.sh [OPTIONS]

OPTIONS:
  -p, --pull              Pull remote_branch to local_branch
  -d, --branch-diff       Find differences of commits in branches
  -c, --commit-id ID      Local commit ID(s) to merge
                          (space-separated, e.g. "12345 23456",
                           or range, e.g. "12345..23456")
  -s, --start-since DATE  Start date (git log --since format: 2025-10-01)
  -f, --full-sync         One-click full sync (pull + merge + push)
  -S, --split             Split commits to single branches and push to Gitee
  -h, --help              Show this help message

EXAMPLES:
  ./merge-to-gitee.sh -f -s "2025-11-01"
  ./merge-to-gitee.sh -f -c "12345 23456"
  ./merge-to-gitee.sh -S -s "2025-11-01"
  ./merge-to-gitee.sh -S -c "12345 23456"
  ./merge-to-gitee.sh -p
  ./merge-to-gitee.sh -d
  ./merge-to-gitee.sh -c "12345"
EOF
}

# ===== Main =====
main() {
    local pull=false
    local branch_diff=false
    local commit_id=""
    local start_since=""
    local full_sync=false
    local split=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -p|--pull)        pull=true; shift ;;
            -d|--branch-diff) branch_diff=true; shift ;;
            -c|--commit-id)   commit_id="$2"; shift 2 ;;
            -s|--start-since) start_since="$2"; shift 2 ;;
            -f|--full-sync)   full_sync=true; shift ;;
            -S|--split)       split=true; shift ;;
            -h|--help)        usage; exit 0 ;;
            *)
                echo "Unknown option: $1" >&2
                usage
                exit 1
                ;;
        esac
    done

    # Validate commit ID format
    local commit_id_pattern='^[0-9a-fA-F]{7,40}$'
    if [ -n "$commit_id" ]; then
        if [[ "$commit_id" == *" "* ]]; then
            for cid in $commit_id; do
                if [[ ! "$cid" =~ $commit_id_pattern ]] && \
                   [[ "$cid" != *".."* ]]; then
                    die "Invalid commit ID format: $cid"
                fi
            done
        fi
        if [[ "$commit_id" == *".."* ]]; then
            local left="${commit_id%%..*}"
            local right="${commit_id#*..}"
            for part in "$left" "$right"; do
                if [ -n "$part" ] && \
                   [[ ! "$part" =~ $commit_id_pattern ]]; then
                    die "Invalid commit ID format: $part"
                fi
            done
        fi
    fi

    # Check mutually exclusive options
    if [ "$full_sync" = true ] && [ "$split" = true ]; then
        die "Cannot use --full-sync with --split"
    fi
    if [ "$full_sync" = true ] && \
       { [ "$pull" = true ] || [ "$branch_diff" = true ]; }; then
        die "Cannot use --full-sync with --pull/--branch-diff"
    fi
    if [ "$split" = true ] && \
       { [ "$pull" = true ] || [ "$branch_diff" = true ]; }; then
        die "Cannot use --split with --pull/--branch-diff"
    fi

    # Dispatch: split mode
    if [ "$split" = true ]; then
        split_and_push_single_commits "$start_since" "$commit_id"
        exit 0
    fi

    # Dispatch: full sync mode
    if [ "$full_sync" = true ]; then
        full_auto_sync "$start_since" "$commit_id"
        exit 0
    fi

    # Remaining: individual mode
    if [ "$pull" = true ] && [ -n "$commit_id" ]; then
        die "Cannot use --pull with --commit-id"
    fi
    if [ "$branch_diff" = true ] && [ -n "$commit_id" ]; then
        die "Cannot use --branch-diff with --commit-id"
    fi

    if [ "$pull" = true ]; then
        echo "Pull branches ..."
        pull_branches
    fi

    if [ "$branch_diff" = true ]; then
        echo "Find the differences between branches ..."
        diff_branches "$start_since"
    fi

    if [ -n "$commit_id" ]; then
        echo "Merge commits: $commit_id"
        merge_branches "$commit_id"
        echo ""
        echo "Run: git push $gitee_remote" \
             "$cmss_local_merge_branch:$gitee_remote_branch"
    fi

    if [ "$pull" = false ] && [ "$branch_diff" = false ] && \
       [ -z "$commit_id" ]; then
        die "You must specify either -p, -d, -c, -f or -S"
    fi

    exit 0
}

main "$@"
