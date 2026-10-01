"""LSET with many independent keys; clean grid and separate CPU diagnostics."""
import importlib.util,os,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
# Share the benchmark runner while keeping profiling outside the clean grid.
spec = importlib.util.spec_from_file_location('lset_deep', Path(__file__).with_name('profile-lset-deep.py'))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
run, original_measure = profile.run, profile.original_measure
metrics, profile_only = profile.metrics, profile.profile_only

def measure(directory,kind,size,field,entries,keys,op,conns,seconds,threads):
    run.save(directory/'measurement-plan.json', {
        'clean_levels': [80, 320, 1280, 2560, 5120],
        'profile_levels_after_clean_grid': [] if os.getenv('LAVIK_LSET_NO_PERF') == '1' else [1280, 5120],
        'profile_strategy': 'after-entire-clean-grid-v1',
    })
    metrics(directory/f'c{conns}-clean-before.prom')
    original_measure(directory,kind,size,field,entries,keys,op,conns,seconds,threads)
    metrics(directory/f'c{conns}-clean-after.prom')
    if os.getenv('LAVIK_LSET_NO_PERF') != '1' and conns == 5120:
        for diagnostic_connections in (1280,5120):
            profile_only(directory,kind,size,field,entries,keys,op,diagnostic_connections,threads)

def fill(kind,field_bytes,entries,keys,pipeline,workers,target_bytes):
    assert kind=='list'
    begin=time.monotonic();values=tuple(run.value(i,field_bytes) for i in range(entries))
    step=run.seed_step(kind,field_bytes,target_bytes);templates=[]
    command_wire=run.resp('RPUSH').partition(b'\r\n')[2]
    for start in range(0,entries,step):
        operands=values[start:min(start+step,entries)]
        templates.append((f'*{len(operands)+2}\r\n'.encode()+command_wire,run.resp(*operands).partition(b'\r\n')[2]))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs=[pool.submit(run.fill_worker,kind,field_bytes,entries,range(i+1,keys+1,workers),pipeline,values,(),target_bytes,templates) for i in range(workers)]
        count=sum(j.result() for j in jobs)
    assert count==keys*((entries+step-1)//step)
    return {'seconds':time.monotonic()-begin,'commands':count,'entries_per_command':step,'client_encoding':'shared-list-operands-v1','command':'RPUSH'}
run.fill,run.measure=fill,measure
run.main()
