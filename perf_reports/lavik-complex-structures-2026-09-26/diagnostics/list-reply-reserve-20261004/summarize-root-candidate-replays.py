"""Validate completed candidate-only long-key replays; never derive a censored speedup."""
from pathlib import Path
import argparse,hashlib,json,statistics
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--input',type=Path,default=Path(__file__).parent/'grouped-verified-root-candidate-replays.json')
p.add_argument('--baseline',type=Path,default=Path(__file__).parent/'grouped-verified-root-replays.json')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();v=json.loads(a.input.read_text());baseline=json.loads(a.baseline.read_text())
assert v['versions']==baseline['versions']
assert v['original_sha256']==baseline['original_sha256']=='b4e0113cf9b7dcbe03175c5e5665be8589ebef9dbc9c2847adc3cd3010b956ae'
assert v['versions']['candidate']['source_head']==v['versions']['candidate']['built_revision']=='28d7cca498655e02f46407adb65335219b10ee6b'
assert v['versions']['candidate']['binary_sha256']=='3b3dbc5482bf6586b0f06e00d92a6c5e589f58528b13105d01ea3b8a226e5090'
assert v['versions']['candidate']['test_sha256']==v['versions']['main']['test_sha256']
assert len(baseline['rows'])==1 and not baseline['rows'][0]['success']
failed=baseline['rows'][0];assert failed['version']=='main' and failed['error']=="TimeoutError('timed out')"
assert failed['failed_phase']['command']=='GET' and failed['failed_phase']['key_bytes']==9437184
assert failed['failed_phase']['received_payload_bytes']==0
assert len(v['rows'])==3 and {x['round'] for x in v['rows']}=={1,2,3}
assert len({x['image'] for x in v['rows']})==3
expected=[('STRLEN',5009,':9437184\r\n',0),('GET',5009,'$9437184\r\n',9437184)]*3
expected += [('GET',6291456,'$1048576\r\n',1048576),('GET',9437184,'$6291456\r\n',6291456)]
expected += [('SET',5009,'+OK\r\n',0),('STRLEN',5009,':5\r\n',0)]*3
expected += [('SET',6291456,'+OK\r\n',0),('SET',9437184,'+OK\r\n',0)]
def io(text):return {k:int(n) for k,n in (line.split(':',1) for line in text.splitlines())}
rows=[]
for row in sorted(v['rows'],key=lambda x:x['round']):
    assert row['version']=='candidate' and row['success'] and row['server_exit']==0 and 'error' not in row
    argv=row['argv'];assert argv[0]==v['versions']['candidate']['binary']
    assert argv[argv.index('--threads')+1]=='2'
    assert argv[argv.index('--data-file')+1]==row['image']
    assert len(row['operations'])==len(expected)==16
    entries=[]
    for op,(command,key_bytes,header,payload) in zip(row['operations'],expected):
        assert (op['command'],op['key_bytes'],op['header'],op['received_payload_bytes'])==(command,key_bytes,header,payload)
        assert 0<=op['send_seconds']<=op['header_seconds']<=op['seconds']<60
        before,after=io(op['proc_io_before']),io(op['proc_io_after'])
        delta={key:after[key]-before[key] for key in ['read_bytes','write_bytes']}
        assert all(n>=0 for n in delta.values())
        entries.append({k:op[k] for k in ['command','key_bytes','received_payload_bytes','send_seconds','header_seconds','seconds']}|{'process_io_delta':delta})
    rows.append({'round':row['round'],'server_exit':0,'operations':entries})
gets=[op for row in rows for op in row['operations'] if op['command']=='GET' and op['key_bytes']==9437184]
result={'input_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),
        'failed_baseline_sha256':hashlib.sha256(a.baseline.read_bytes()).hexdigest(),
        'original_image_sha256':v['original_sha256'],'candidate':v['versions']['candidate'],
        'method':v['method'],'rounds':rows,
        'nine_mib_key_get':{'seconds':[x['seconds'] for x in gets],
                            'median_seconds':statistics.median(x['seconds'] for x in gets),
                            'read_bytes':[x['process_io_delta']['read_bytes'] for x in gets],
                            'payload_bytes_verified_each':6291456},
        'limitations':'Three candidate-only replays, not paired throughput runs. Original baseline timeout remains censored and unchanged; no exact speedup/QPS ratio. Existing driver checks every GET payload byte, five SET acknowledgements and three subsequent STRLEN results; it does not restart after overwrites or read back the large-key replacement values. Process IO includes background work; no new candidate perf capture. Ordinary short-key native controls remain required.'}
a.output.write_text(json.dumps(result,indent=2)+'\n')
print('validated3candidate rounds,48 operations,15 full GET payloads;9MiBkeyGET',result['nine_mib_key_get'])
