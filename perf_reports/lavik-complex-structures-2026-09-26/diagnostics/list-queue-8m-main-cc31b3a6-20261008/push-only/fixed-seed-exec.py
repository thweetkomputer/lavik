"""Benchmark-only launcher; pair routing seeds without modifying server binaries."""
from pathlib import Path
import hashlib,json,os,runpy,subprocess,sys,time
W=Path(__file__).parent
seed,versions_path,target,*arguments=sys.argv[1:]
assert len(seed)==32 and bytes.fromhex(seed).hex()==seed
versions=json.loads(Path(versions_path).read_text())
original_popen=subprocess.Popen
allowed={str(Path(v['binary']).resolve()):v for v in versions.values()}
shim=W/'fixed-digest-seed.so'
def sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
class SeededPopen(original_popen):
 def __init__(self,args,*a,**kw):
  is_server=isinstance(args,(list,tuple)) and '--storage=spdk' in args
  if not is_server:
   super().__init__(args,*a,**kw);return
  matches=[(i,str(arg)) for i,arg in enumerate(args) if str(arg) in allowed]
  assert len(matches)==1,args
  index,binary=matches[0];v=allowed[binary]
  assert sha(binary)==v['sha256']
  symbols=subprocess.check_output(['nm','--defined-only',binary],text=True)
  function=[];data=[]
  for line in symbols.splitlines():
   fields=line.split()
   if len(fields)!=3:continue
   address,kind,name=fields
   if name.startswith('_ZN5lavik7storage12_GLOBAL__N_117MutableDigestSeedEv') and '.cold' not in name:function.append(int(address,16))
   if name.startswith('_ZZN5lavik7storage12_GLOBAL__N_117MutableDigestSeedEvE4seed'):data.append(int(address,16))
  assert len(function)==len(data)==1,(function,data)
  env=dict(kw.get('env') or os.environ);assert not env.get('LD_PRELOAD')
  # Apply preload only to the server, not to prlimit/taskset/env themselves.
  args=list(args[:index])+['env','LD_PRELOAD='+str(shim),'LAVIK_BENCH_FIXED_DIGEST_SEED='+seed,f'LAVIK_BENCH_DIGEST_FUNCTION_OFFSET={function[0]:x}']+list(args[index:])
  kw['env']=env
  super().__init__(args,*a,**kw)
  deadline=time.monotonic()+15;verified=False
  try:
   while time.monotonic()<deadline and self.poll() is None:
    maps=Path(f'/proc/{self.pid}/maps').read_text().splitlines()
    base=[int(line.split()[0].split('-')[0],16) for line in maps if line.split()[-1]==binary and line.split()[2]=='00000000']
    if len(base)==1:
     with open(f'/proc/{self.pid}/mem','rb',buffering=0) as f:
      f.seek(base[0]+data[0]);actual=f.read(16)
     if actual==bytes.fromhex(seed):verified=True;break
    time.sleep(.01)
   assert verified,('seed verification failed',self.pid,self.poll())
   directory=Path(next(x.removeprefix('--log-dir=') for x in args if x.startswith('--log-dir='))).parent
   proof={'launcher_argv':args,'seed_hex':seed,'pid':self.pid,'verified_via_proc_mem':True,'binary':binary,'sha256':v['sha256'],'source_commit':v['commit'],'shim_sha256':sha(shim),'shim_source_sha256':sha(W/'fixed-digest-seed.c'),'launcher_sha256':sha(__file__),'function_offset':function[0],'seed_offset':data[0],'executable_base':base[0],'method':'Benchmark-only __libc_start_main shim initializes MutableDigestSeed before main; no request-path hook. Unchanged binary SHA checked. Same seed per pair; different seeds between rounds.'}
   with (directory/'fixed-digest-seed.json').open('x') as f:json.dump(proof,f,indent=2)
  except BaseException:
   self.terminate();self.wait(timeout=15);raise
subprocess.Popen=SeededPopen
sys.argv=[target,*arguments]
sys.path.insert(0,str(Path(target).parent))
runpy.run_path(target,run_name='__main__')
