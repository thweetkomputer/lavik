"""LSET CPU stacks and storage-I/O deltas; diagnostic points only."""
import json, os, subprocess, sys, time, urllib.request
from pathlib import Path
sys.path.insert(0, os.environ.get('LAVIK_BENCH_ROOT', str(Path.cwd() / 'perf_reports/lavik-complex-structures-2026-09-26')))
import run
original_measure, original_server = run.measure, run.server
run.OPS['list'] = ('LSET',)

def option(name):
    return next(a.split('=',1)[1] for a in sys.argv if a.startswith(name+'='))

def server(product, directory, binary):
    argv, env = original_server(product, directory, binary)
    argv[argv.index('--metrics-port=0')] = '--metrics-port=9191'
    return argv, env

def metrics(path):
    with urllib.request.urlopen('http://'+run.HOST+':9191/metrics', timeout=30) as response:
        path.write_bytes(response.read())

def measure(directory, kind, size, field, entries, keys, op, conns, seconds, threads):
    metrics(directory / f'c{conns}-clean-before.prom')
    original_measure(directory,kind,size,field,entries,keys,op,conns,seconds,threads)
    metrics(directory / f'c{conns}-clean-after.prom')
    profile_only(directory, kind, size, field, entries, keys, op, conns, threads)

def profile_only(directory, kind, size, field, entries, keys, op, conns, threads):
    d=directory/f'diagnostic-c{conns}';d.mkdir()
    binary=option('--binary');pids=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:args=(p/'cmdline').read_bytes().split(b'\0')
        except (OSError,PermissionError):continue
        if args[0]==os.fsencode(binary):pids.append(int(p.name))
    assert len(pids)==1,pids
    pid=pids[0]
    run.save(d/'threads.json',[{'tid':int(p.name),'comm':(p/'comm').read_text().strip(),'status':(p/'status').read_text()} for p in (Path('/proc')/str(pid)/'task').iterdir()])
    args=['perf','record','--no-buildid-cache','-e','task-clock','-F','199','-g','--call-graph','dwarf,16384','-p',str(pid),'-o',str(d/'cpu.perf'),'--','sleep','25']
    run.save(d/'profile-provenance.json',{'source_commit':option('--source-commit'),'binary':binary,'argv':args,'connections':conns,'time':time.time(),'note':'Independent diagnostic; metrics enabled; warmed by prior LSET points, not comparable as a clean fresh-seed PR curve.'})
    metrics(d/'before.prom')
    with (d/'perf.log').open('w') as log:
        proc=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT)
        try:original_measure(d,kind,size,field,entries,keys,op,conns,30,threads)
        finally:rc=proc.wait(timeout=45)
    assert rc==0,rc
    metrics(d/'after.prom')
    for name,extra in [('self',['--no-children','--call-graph','none','--sort','symbol']),('inclusive',['--children','--call-graph','none','--sort','symbol']),('threads',['--no-children','--call-graph','none','--sort','pid,comm,symbol'])]:
        with (d/(name+'.txt')).open('w') as out:
            subprocess.run(['perf','report','--stdio','--no-inline','--percent-limit','0.1',*extra,'-i',str(d/'cpu.perf')],stdout=out,check=True)
run.measure,run.server=measure,server
if __name__ == '__main__':
    run.main()
