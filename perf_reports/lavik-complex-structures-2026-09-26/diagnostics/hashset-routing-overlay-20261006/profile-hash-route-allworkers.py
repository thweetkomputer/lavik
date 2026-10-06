"""Independent Hash/Set write diagnosis with explicit worker thread attachment."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

WORK = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('profile', '/mnt/dev/lavik-test-data-20261001/profile-lset-deep.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
run = profile.run
run.OPS.update({'hash': ('HSET',), 'set': ('SADD_SREM',)})

def measure(directory, kind, size, field, entries, keys, op, connections, seconds, threads):
    d = directory / f'diagnostic-c{connections}'
    d.mkdir()
    binary = profile.option('--binary')
    processes = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try: argv = (p / 'cmdline').read_bytes().split(b'\0')
        except (OSError, PermissionError): continue
        if argv[0] == os.fsencode(binary): processes.append(int(p.name))
    assert len(processes) == 1, processes
    pid, = processes
    tids = sorted(int(p.name) for p in (Path('/proc') / str(pid) / 'task').iterdir())
    run.save(d / 'threads.json', [{'tid': tid, 'comm': (Path('/proc') / str(pid) / 'task' / str(tid) / 'comm').read_text().strip()} for tid in tids])
    workers = [tid for tid in tids if (Path('/proc') / str(pid) / 'task' / str(tid) / 'comm').read_text().strip().startswith('lavik') and tid != pid]
    args_list = [['perf', 'record', '--no-buildid-cache', '--no-inherit', '-T',
                  '-e', 'task-clock', '-F', '99', '--call-graph', 'dwarf,16384',
                  '-t', str(tid), '-o', str(d / f'cpu-{tid}.perf'), '--', 'sleep', '25'] for tid in workers]
    run.save(d / 'profile-provenance.json', {'source_commit': profile.option('--source-commit'),
             'binary': binary, 'argv_by_tid': dict(zip(map(str, workers), args_list)), 'connections': connections,
             'time': time.time(),
             'population': 'recovered same-binary seed' if '--reuse-seeded-data' in sys.argv else 'fresh same-binary seed without restart',
             'note': 'Each worker recorded separately; not a throughput-comparison point. No perf recorder shares a worker counter.'})
    profile.metrics(d / 'before.prom')
    processes, logs = [], []
    try:
        for tid, args in zip(workers, args_list):
            log = (d / f'perf-{tid}.log').open('w'); logs.append(log)
            processes.append(subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT))
        profile.original_measure(d, kind, size, field, entries, keys, op, connections, 30, threads)
    finally:
        codes = [proc.wait(timeout=45) for proc in processes]
        for log in logs: log.close()
    assert all(rc == 0 for rc in codes), codes
    profile.metrics(d / 'after.prom')
    for tid in workers:
        file = d / f'cpu-{tid}.perf'
        with (d / f'stacks-{tid}.txt').open('w') as out:
            subprocess.run(['perf', 'script', '--no-inline', '-F', 'comm,pid,tid,time,period,event,ip,sym,dso', '-i', str(file)], stdout=out, check=True)
        with (d / f'self-{tid}.txt').open('w') as out:
            subprocess.run(['perf', 'report', '--stdio', '--no-inline', '--no-children', '--call-graph', 'none', '--sort', 'symbol', '--percent-limit', '0.1', '-i', str(file)], stdout=out, check=True)

run.measure = measure
run.main()
