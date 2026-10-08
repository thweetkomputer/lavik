"""Independent per-thread perf diagnostics, never used as clean QPS points."""
from pathlib import Path
import os,json,subprocess,sys,time

def start(directory,stem):
 d=directory/(stem+'.perf');d.mkdir()
 binary=next(x.split('=',1)[1] for x in sys.argv if x.startswith('--binary='))
 pids=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:argv=(p/'cmdline').read_bytes().split(b'\0')
  except (OSError,PermissionError):continue
  if argv[0]==os.fsencode(binary):pids.append(int(p.name))
 assert len(pids)==1,pids
 pid=pids[0];threads=[{'tid':int(p.name),'comm':(p/'comm').read_text().strip()} for p in (Path('/proc')/str(pid)/'task').iterdir()]
 workers=[x['tid'] for x in threads if x['comm'].startswith('lavik') and x['tid']!=pid];assert len(workers)>=12
 args=[['perf','record','--no-buildid-cache','--no-inherit','-T','-e','task-clock','-F','99','--call-graph','dwarf,16384','-t',str(t),'-o',str(d/f'cpu-{t}.perf'),'--','sleep','25'] for t in workers]
 (d/'provenance.json').write_text(json.dumps({'binary':binary,'threads':threads,'argv_by_tid':dict(zip(map(str,workers),args)),'time':time.time()},indent=2))
 processes=[];logs=[]
 for t,a in zip(workers,args):
  f=(d/f'perf-{t}.log').open('w');logs.append(f);processes.append(subprocess.Popen(a,stdout=f,stderr=subprocess.STDOUT))
 def finish():
  codes=[p.wait(timeout=45) for p in processes]
  for f in logs:f.close()
  assert all(c==0 for c in codes),codes
  for t in workers:
   file=d/f'cpu-{t}.perf'
   with (d/f'self-{t}.txt').open('w') as out:
    subprocess.run(['perf','report','--stdio','--no-inline','--no-children','--call-graph','none','--sort','symbol','--percent-limit','0.1','-i',str(file)],stdout=out,stderr=subprocess.DEVNULL,check=True)
   with (d/f'stacks-{t}.txt').open('w') as out:
    subprocess.run(['perf','script','--inline','-F','comm,pid,tid,time,period,event,ip,sym,dso','-i',str(file)],stdout=out,stderr=subprocess.DEVNULL,check=True)
 return finish
