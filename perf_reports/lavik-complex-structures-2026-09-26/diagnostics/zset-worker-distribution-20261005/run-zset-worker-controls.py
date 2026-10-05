"""Explicit worker-count diagnostic; baseline runner and key names stay fixed."""
from pathlib import Path
import hashlib,json,os,sys,time
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
workers=int(os.environ['LAVIK_WORKER_EXPERIMENT_COUNT'])
assert workers in (8,12)
original_server=run.server
original_measure=run.measure
binary=next(a.split('=',1)[1] for a in sys.argv if a.startswith('--binary='))
def server(product,directory,binary):
 assert product=='lavik'
 argv,env=original_server(product,directory,binary)
 assert argv.count('--threads=12')==1
 argv[argv.index('--threads=12')]='--threads='+str(workers)
 run.save(directory/'worker-experiment.json',{'workers':workers,'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'note':'Only --threads changes from the standard server command; fixed8keys. This is configuration diagnosis, not a source-code speedup or replacement for the12worker comparison.'})
 return argv,env
def cpu_snapshot():
 pids=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:args=(p/'cmdline').read_bytes().split(b'\0')
  except (OSError,PermissionError):continue
  if args and args[0]==os.fsencode(binary):pids.append(int(p.name))
 assert len(pids)==1,pids
 threads=[]
 for t in (Path('/proc')/str(pids[0])/'task').iterdir():
  fields=(t/'stat').read_text().rsplit(')',1)[1].split()
  threads.append({'tid':int(t.name),'comm':(t/'comm').read_text().strip(),'utime_ticks':int(fields[11]),'stime_ticks':int(fields[12]),'starttime_ticks':int(fields[19])})
 return {'pid':pids[0],'monotonic':time.monotonic(),'ticks_per_second':os.sysconf('SC_CLK_TCK'),'threads':threads}
def measure(directory,kind,size,field,entries,keys,op,connections,seconds,threads):
 assert kind=='zset' and keys==8
 stem=f'{kind}-{size}-{field}-{op.lower()}-c{connections}'
 run.save(directory/(stem+'.cpu-before.json'),cpu_snapshot())
 original_measure(directory,kind,size,field,entries,keys,op,connections,seconds,threads)
 run.save(directory/(stem+'.cpu-after.json'),cpu_snapshot())
run.server=server
run.measure=measure
run.main()
