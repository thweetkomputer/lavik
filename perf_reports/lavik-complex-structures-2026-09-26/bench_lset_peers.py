#!/usr/bin/env python3
"""Match the large-key LSET main/PR workload for Redis, Valkey and Kvrocks.

Use run.py's server settings and memtier validation. Pre-encode shared RPUSH
operands exactly as in the Lavik run; each process receives a fresh dataset.
"""
import time
from concurrent.futures import ThreadPoolExecutor
import run

run.OPS['list'] = ('LSET',)

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

run.fill = fill
if __name__ == '__main__':
    run.main()
