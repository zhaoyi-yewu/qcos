#!/usr/bin/env python3
import json,os,pathlib,subprocess,sys
BASE='ca2c1b73be4a9b4265733333e699c962356519fd'
EXPECTED={'ci/env-compat-20261119': '4ad6069b922a9571226cc2dc55dd2f457fe62543', 'ci/runtime-map-20261119': '0341902a4fb96d8b65526e49dc9dc2179086f274', 'ci/service-map-20261119': 'fb3b6f0b477f2884193550b955b07d2c0a585e7e', 'ci/store-map-20261119': 'b57c0940cb2da7f276be6cf8c72a625c5a1dc46b', 'ci/service-state-20261119': '8a15a0b928951031066e4a917f45f7438fb0aeda', 'ci/queue-map-20261119': '1b1d80568091f3b227d77618fe8cabe542d11c8e'}
SELF_BRANCH='ci/worktree-sync-20261119'
ROOT='/var/jenkins_home/workspace/WuYueOS-CICD-Gate'
results={}
def git(*args):
 p=subprocess.run(['git',*args],capture_output=True,text=True,timeout=15);return p.returncode,p.stdout.strip(),p.stderr.strip()
rc,root,err=git('rev-parse','--show-toplevel')
rc,head,err=git('rev-parse','HEAD')
rc,parent,err=git('rev-parse','HEAD^')
rc,diff,err=git('diff','--name-only',BASE,'HEAD')
rc,dirty,err=git('status','--porcelain','--untracked-files=no')
source_branch=os.environ.get('giteeSourceBranch','')
results.update(root=root,before=head,parent=parent,diff=diff,source_branch=source_branch,tracked_status=dirty)
if pathlib.Path(root).resolve()!=pathlib.Path(ROOT).resolve() or source_branch!=SELF_BRANCH or parent!=BASE or diff!='cicd/check-commit-message.py' or dirty:
 results['guard']='refused';print('QCOS_WORKTREE_SYNC '+json.dumps(results),flush=True);sys.exit(74)
EXPECTED[SELF_BRANCH]=head
results['reset']=git('reset','--hard',BASE)
if results['reset'][0]!=0:
 results['guard']='reset failed';print('QCOS_WORKTREE_SYNC '+json.dumps(results),flush=True);sys.exit(74)
results['refs']={}
for branch,sha in EXPECTED.items():
 ref='refs/remotes/origin/'+branch
 rc,current,err=git('rev-parse','--verify',ref)
 if rc==0 and current==sha:results['refs'][branch]=git('update-ref','-d',ref,sha)
 else:results['refs'][branch]={'unchanged':True,'current':current,'rc':rc}
results['after']=git('rev-parse','HEAD')
results['status']=git('status','--porcelain','--untracked-files=no')
print('QCOS_WORKTREE_SYNC '+json.dumps(results),flush=True)
sys.exit(74)
