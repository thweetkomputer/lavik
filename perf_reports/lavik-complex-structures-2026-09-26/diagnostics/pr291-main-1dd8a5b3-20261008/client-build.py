from pathlib import Path
import sys,subprocess,json,hashlib,time
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock=acquire_host('pr291-benchmark-client-build')
W=Path(__file__).parent
subprocess.run(['g++','-std=c++20','-O3','-pthread',str(W/'random-client.cpp'),'-o',str(W/'random-client')],check=True)
subprocess.run(['scp','-q',str(W/'random-client'),'azureuser@172.16.0.5:/mnt/dev/random-client-pr291-20261008'],check=True)
remote=subprocess.check_output(['ssh','-o','BatchMode=yes','azureuser@172.16.0.5','sha256sum /mnt/dev/random-client-pr291-20261008 /mnt/dev/random-client-pr291-20261008.cpp'],text=True)
local={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [W/'random-client',W/'random-client.cpp']}
assert local['random-client']==remote.splitlines()[0].split()[0]
assert local['random-client.cpp']==remote.splitlines()[1].split()[0]
(W/'client-provenance.json').write_text(json.dumps({'local':local,'remote_sha256':remote,'compiler':subprocess.check_output(['g++','--version'],text=True)},indent=2)+'\n')
print('CLIENT_READY',time.time(),flush=True)
