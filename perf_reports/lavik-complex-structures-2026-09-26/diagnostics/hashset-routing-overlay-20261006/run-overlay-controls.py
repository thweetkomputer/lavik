"""Report runner with reads after writes and an optional 64-target sensitivity control."""
import importlib.util,inspect,os,sys
from pathlib import Path
R=Path(os.environ['LAVIK_BENCH_ROOT'])
sys.path.insert(0,str(R))
spec=importlib.util.spec_from_file_location('report_runner',R/'run.py')
run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
wide=any('dispersed64' in arg for arg in __import__('sys').argv if arg.startswith('--tag='))
original=run.command_lines
source=inspect.getsource(original).replace('def command_lines(', 'def dispersed_commands(').replace('// 7 for i in range(8)', '// 63 for i in range(64)')
namespace=run.__dict__;exec(source,namespace);dispersed=namespace['dispersed_commands']
def command_lines(op,field_bytes,entries):
 op=op.removesuffix('_AFTER_WRITE')
 if not wide:return original(op,field_bytes,entries)
 if op=='SADD_SREM':
  return [f'{command} __key__ '+('t'+str(i).zfill(8)+'t'*(field_bytes-9)) for i in range(64) for command in ['SADD','SREM']]
 return dispersed(op,field_bytes,entries)
run.command_lines=command_lines
source=inspect.getsource(run.validate).replace('entries + 1','entries + 64')
if wide:exec(source,namespace)
run.OPS['hash']=('HGET','HSET','HGET_AFTER_WRITE')
run.OPS['set']=('SISMEMBER','SADD_SREM','SISMEMBER_AFTER_WRITE')
# 128 Set command arguments exceed Linux's per-argument limit when SSH
# transports them as one shell string. Stream that same quoted script over
# stdin; memtier still receives separate, unchanged command arguments.
_subprocess=run.subprocess
class SubprocessProxy:
 def __getattr__(self,name):return getattr(_subprocess,name)
 def run(self,argv,*args,**kwargs):
  if isinstance(argv,list) and 'ssh' in argv and isinstance(argv[-1],str) and len(argv[-1].encode())>100000:
   assert 'input' not in kwargs and 'stdin' not in kwargs
   return _subprocess.run(argv[:-1]+['bash','-s'],*args,input=(argv[-1]+'\n').encode(),**kwargs)
  return _subprocess.run(argv,*args,**kwargs)
run.subprocess=SubprocessProxy()
run.main()
