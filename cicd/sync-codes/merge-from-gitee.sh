#!/bin/sh
# ----------------------------------------------------------------------
# Copyright© 2025-2025 China Mobile (SuZhou) Software Technology Co.,Ltd.
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

# Merge from remote gitee to local git repo

set -e

default_project_id="R251166SC04"
default_jira_id="#QSE-8888"
commit_id=""

gitee_remote=gitee
gitee_remote_branch=develop
gitee_local_branch=gitee-develop

cmss_remote=origin
cmss_local_branch=gitee

trap '
  if [ $? -ne 0 ]; then
    echo "Error detected, exiting ..."
  fi
' EXIT

function usage {
    echo "Usage: $0 [OPTION] ..."
    echo "Merge from remote gitee repo"
    echo ""
    echo "  -c, --commit-id       Remote commit ID (remote: ${gitee_remote}, remote_branch: ${gitee_remote_branch})"
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

# Merge ${gitee_remote}:{gitee_local_branch} to local branch: ${cmss_local_branch}
echo "git checkout ${cmss_local_branch}"
git checkout ${cmss_local_branch}

# merge commit
git cherry-pick ${commit_id}

new_commit_id=`git log -1  | head -1 |  awk '{print $2}'`
echo "new_commit_id: ${new_commit_id}"
echo

git-filter-repo --force \
  --commit-callback "
  if commit.original_id == b'${new_commit_id}':
    # modify email and author name
    decoded_email = commit.author_email.decode('utf-8')
    decoded_author_name = commit.author_name.decode('utf-8')
    if decoded_email.endswith('_yewu@cmss.chinamobile.com'):
        new_email = decoded_email.replace('_yewu@cmss.chinamobile.com', '@cmss.chinamobile.com')
        encoded_new_email = new_email.encode('utf-8')
        commit.author_email = encoded_new_email
        new_author_name = decoded_author_name.replace('_yewu', '')
        encoded_new_author_name = new_author_name.encode('utf-8')
        commit.author_name = encoded_new_author_name

    # modify messages
    new_messages = []
    key_to_modify = {
        'Jira': (False, '${default_jira_id}'),
        'Code Source From': (False, 'Others'),
        '市场项目编号（名称）': (False, '${default_project_id}')
    }
    decoded_message = commit.message.decode('utf-8')
    messages = decoded_message.split('\n')
    for m in messages:
        for key in key_to_modify:
            if key in m:
                key_to_modify[key][0] = True
        if 'Signed-off-by:' in m and '_yewu@cmss.chinamobile.com' in m:
            m = m.replace('_yewu@cmss.chinamobile.com', '@cmss.chinamobile.com')
        new_messages.append(m)
    for key in key_to_modify:
        if key_to_modify[key][0] is False:
            value = key_to_modify[key][1]
            if key =='Code Source From' and '@cmss.chinamobile.com' in decoded_email:
                value = 'Self Code'
            message = key + ': ' + value
            new_messages.append(message.strip())
    new_message = '\n'.join(new_messages)
    commit.message = new_message.encode('utf-8')
  "  \
  --refs ${cmss_local_branch}

# print next step
echo "Run: git push ${cmss_remote} ${cmss_local_branch}"

