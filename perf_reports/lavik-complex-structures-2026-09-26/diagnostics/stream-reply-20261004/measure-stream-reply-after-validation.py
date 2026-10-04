"""Run clean Stream grids only after the exact native binary passes tests."""
from pathlib import Path
import hashlib,json,subprocess,time
W=Path(__file__).parent
commit='1e87107e51d658944998ec74ff05b57d2e8f40c8'
pid=561940
proc=Path(f'/proc/{pid}/stat');identity=proc.read_text().split()[21]
print('WAIT_FOR_NATIVE_PRODUCTION_VALIDATION',pid,time.time(),flush=True)
while proc.exists():
    try:
        if proc.read_text().split()[21]!=identity:break
    except FileNotFoundError:break
    time.sleep(15)
proof=json.loads((W/'stream-reply-local-tests-passed.json').read_text())
assert proof['candidate']['commit']==commit and not proof['faults'] and not proof['build_testing']
v=json.loads((W/'stream-reply-versions.json').read_text())
assert v['candidate']==proof['candidate']
assert hashlib.sha256(Path(v['candidate']['binary']).read_bytes()).hexdigest()==v['candidate']['sha256']
completed=[]
for size,field,keys,profile in [(104857600,128,8,True),(65536,128,64,False),(104857600,1024,8,False),(65536,1024,64,False)]:
    assert json.loads((W/'versions.json').read_text())['candidate']==v['candidate']
    name=f'stream-reply-grid-{size}-{field}-k{keys}'
    print('START',name,time.time(),flush=True)
    args=['python3',str(W/'run-condition.py'),'stream',str(size),str(field),str(keys),'ordered','--version=candidate']
    if profile:args.append('--profile-full')
    with (W/(name+'.log')).open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['python3',str(W/'compare-stream-reply.py'),'stream',str(size),str(field),str(keys)],check=True)
    completed.append({'size':size,'field':field,'keys':keys,'comparison':f'stream-reply-comparison-stream-{size}-{field}-k{keys}.json'})
    (W/'stream-reply-initial-progress.json').write_text(json.dumps({'candidate':v['candidate'],'completed':completed,'note':'Single sweeps; inspect all QPS/p99 and errors. Paired repeats still required.'},indent=2)+'\n')
    print('COMPLETE',name,time.time(),flush=True)
subprocess.run(['python3',str(W/'analyze-stream-reply.py')],check=True)
print('ALL_STREAM_REPLY_INITIAL_MEASUREMENTS_COMPLETE',time.time(),flush=True)
