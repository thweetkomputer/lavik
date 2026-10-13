#!/usr/bin/env python3
import json,os,pathlib,subprocess as sp,time,hashlib
import runner as b
import spdk_fresh as f
ROOT=b.R.parent
assert os.geteuid()==0
assert (ROOT/'PREPARED').exists(), 'Finish builds before formal measurement'
assert not (b.R/'EXPERIMENT.json').exists(), 'One-shot batch; inspect partial evidence before resuming'
for name in ['lavik','asd','redis-server','valkey-server']:
 assert sp.run(['pgrep','-x',name],stdout=sp.DEVNULL).returncode==1,name
b.ssh('test "$(systemctl show release010-ycsb-build -p ActiveState --value)" != active')
inv=json.loads(pathlib.Path('/mnt/dev/provisioning/bypass-hardware-reboot20261011.json').read_text())
assert {x['serial'] for x in inv['controllers']}==set(b.SERIALS.values())
assert b.out(['uname','-r'])=='6.17.0-1022-azure'
b.write(b.R/'EXPERIMENT.json',{'release':'v0.1.0','revision':'feb61224e414c5653fd09560e20c9d214db1e3ac','products':['lavik-spdk','redis-8.8.0','valkey-9.1.0'],'keys':10000000,'value_bytes':1024,'connections':b.CONNECTIONS,'duration_seconds':30,'defrag':'enabled throughout; 8 active/device; no sleeps','server_cpus':'0-15','client_cpus':'0-15','source_report':'lavik-v0.1.0-beta.1-spdk-vs-peers-2026-09-18','fresh_peer_results':True,'authorization':'User explicitly authorized resetting the six scratch NVMe devices on 2026-10-13.'})
b.snapshot(b.R/'host-before.json')
b.write(b.R/'inventory.json',inv)
env=dict(os.environ,PCI_ALLOWED=' '.join(x['pci'] for x in inv['controllers']),DRIVER_OVERRIDE='vfio-pci',HUGEMEM='8192')
with (b.R/'initial-driver-reset.log').open('w') as log:
 sp.run([f.SETUP,'reset'],env=env,stdout=log,stderr=sp.STDOUT,check=True)
pathlib.Path('/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages').write_text('0')
f.main(10000000)
b.memory('redis')
b.memory('valkey')
b.snapshot(b.R/'host-after.json')
(b.R/'COMPLETE').write_text(str(time.time())+'\n')
b.event('COMPLETE 110 fresh formal GET/SET points')
