from pathlib import Path
import json,subprocess,sys
W=Path(__file__).parent
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock=acquire_host('queue8m-analysis-and-final-audit')
assert not (R/'spdk-ready.json').exists()
assert 'ALL_QUEUEOPT_PAIRS_AND_PERF_COMPLETE' in (W/'pairs.log').read_text()
subprocess.run(['python3',str(W/'analyze.py')],check=True)
subprocess.run(['python3',str(W/'summarize-perf.py')],check=True)
code='import sys,json;sys.path.insert(0,'+repr(str(R))+');import spdk_host;spdk_host.no_servers();spdk_host.assert_driver("nvme");print(json.dumps(spdk_host.checked_kernel_devices()))'
devices=json.loads(subprocess.check_output(['sudo','-n','python3','-c',code],text=True))
state={'no_servers':True,'drivers':'nvme','devices':devices,'hugepages':Path('/proc/sys/vm/nr_hugepages').read_text().strip(),'unsafe_noiommu':Path('/sys/module/vfio/parameters/enable_unsafe_noiommu_mode').read_text().strip()}
assert state['hugepages']=='0' and state['unsafe_noiommu']=='N'
(W/'host-final.json').write_text(json.dumps(state,indent=2)+'\n')
print('ALL_QUEUE8M_ANALYSIS_COMPLETE',flush=True)
