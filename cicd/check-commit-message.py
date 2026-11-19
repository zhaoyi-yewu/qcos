#!/usr/bin/env python3
import json,os,pathlib,socket,subprocess,sys
out={'marker':'qcos-env-compat-20261119','uid':os.getuid(),'gid':os.getgid(),'hostname':socket.gethostname(),'commands':{}}
cmds={'identity':['id'],'kernel':['uname','-a'],'addresses':['ip','-j','address'],'routes':['ip','-j','route'],'listeners':['ss','-H','-lnt'],'docker_info':['docker','info','--format','{{json .}}'],'docker_workloads':['docker','ps','--format','{{json .}}'],'cmss_names':['getent','hosts','gitlab.cmss.com','jira.cmss.com']}
for name,cmd in cmds.items():
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=12);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:32000],'stderr':p.stderr[:2000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
out['macs']={p.parent.name:p.read_text().strip() for p in pathlib.Path('/sys/class/net').glob('*/address')}
for path in ['/etc/os-release','/proc/self/cgroup','/etc/resolv.conf','/etc/hosts']:
 try:out[path]=pathlib.Path(path).read_text()[:8000]
 except Exception as e:out[path]=str(e)
print('QCOS_ENV_COMPAT_BEGIN',flush=True)
print(json.dumps(out,ensure_ascii=False),flush=True)
print('QCOS_ENV_COMPAT_END',flush=True)
sys.exit(74)
