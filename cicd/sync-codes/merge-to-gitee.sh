#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

# Merge from local to remote gitee git repo

set -e

commit_id=""

gitee_remote=gitee
gitee_remote_branch=develop
gitee_local_branch=gitee-develop

cmss_remote=origin
cmss_local_branch=gitee
cmss_local_merge_branch=gitee-merge

trap '
  if [ $? -ne 0 ]; then
    echo "Error detected, exiting ..."
  fi
' EXIT

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Merge to remote gitee repo"
    echo ""
    echo "  -c, --commit-id       Local commit ID (remote: ${cmss_remote}, remote_branch: ${cmss_local_branch})"
    echo "  -h, --help            Print this usage message"
    echo ""
}

opts=$(getopt -o c:h --long commit-id:,help -- "$@")
if [[ $? -ne 0 ]]; then
  exit 1
fi

eval set -- "$opts"

while true; do
  case "$1" in
    -h | --help )        usage ; exit 0; shift ;;
    -c | --commit-id )   commit_id="$2";   shift 2 ;;
    -- ) shift; break ;;
    * )         break ;;
  esac
done

# check user input
if [ -z "$commit_id" ]; then
    echo -e "Error: Invalid arguments (commit-id is required)\n"
    usage
    exit 1
fi

# Fetch codes from gitee
echo "[Fetch codes from ${gitee_remote}, branch: ${gitee_remote_branch}:${gitee_local_branch} ...]"
git checkout ${gitee_local_branch}
git pull --rebase ${gitee_remote} ${gitee_remote_branch}:${gitee_local_branch}
echo

# Fetch codes from cmss
echo "[Fetch codes from ${cmss_remote}, branch: ${cmss_local_branch} ...]"
git checkout ${cmss_local_branch}
git pull --rebase ${cmss_remote} ${cmss_local_branch}:${cmss_local_branch}
echo 

# Merge local branch: ${cmss_local_branch} to ${gitee_remote}:{gitee_local_branch}
echo "git checkout ${cmss_local_merge_branch}"
git checkout ${cmss_local_branch}
if git show-ref --verify --quiet refs/heads/"${cmss_local_merge_branch}"; then
    echo "git branch ${cmss_local_merge_branch} exists"
else
    git checkout -b ${cmss_local_merge_branch}
fi
git checkout ${cmss_local_merge_branch}
git reset --hard

# merge commit
git cherry-pick ${commit_id}

new_commit_id=`git log -1 | head -1 | awk '{print $2}'`
echo "new_commit_id: ${new_commit_id}"
echo

git-filter-repo --force \
  --commit-callback "
  if commit.original_id == b'${new_commit_id}':
    # modify email and author name
    decoded_email = commit.author_email.decode('utf-8')
    decoded_author_name = commit.author_name.decode('utf-8')
    if decoded_email.endswith('@cmss.chinamobile.com') and '_yewu@' not in decoded_email:
        new_email = decoded_email.replace('@cmss.chinamobile.com', '_yewu@cmss.chinamobile.com')
        encoded_new_email = new_email.encode('utf-8')
        commit.author_email = encoded_new_email
        new_author_name = f\"{decoded_author_name}_yewu\"
        encoded_new_author_name = new_author_name.encode('utf-8')
        commit.author_name = encoded_new_author_name

    # modify messages
    new_messages = []
    key_to_remove = set(['Jira:', 'Code Source From', '市场项目'])
    decoded_message = commit.message.decode('utf-8')
    messages = decoded_message.split('\n')
    for m in messages:
        add = True
        for key in key_to_remove:
            if key.lower() in m.lower():
                add = False
                break
        if add:
            new_messages.append(m.strip())
    new_message = '\n'.join(new_messages)
    new_message = re.sub(r'(\s*\n)+$', '', new_message)  # 去掉结尾的所有空行
    new_message = re.sub(r'\n\s*\n', '\n\n', new_message)  # 清理空行中的冗余空白字符
    new_message = re.sub(r'\n{3,}', '\n', new_message)  # 确保最多只保留 1 个连续空行，避免文本中出现过多冗余的空行
    encoded_new_message = new_message.encode('utf-8')
    commit.message = encoded_new_message
  "  \
  --refs ${cmss_local_merge_branch}

# print next step
echo "Run: git push ${gitee_remote} ${cmss_local_merge_branch}:${gitee_remote_branch}"

