import sys,time
from pathlib import Path
ROOT=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0,str(ROOT))
import spdk_host
spdk_host.SETUP=Path('/mnt/dev/lavik-set-hash-20260929/bycorf/third_party/spdk/scripts/setup.sh')
if sys.argv[1]=='prepare':
    # RAID removal can be followed by transient device probing. Wait for two
    # verified idle snapshots; never relax ownership, mount or serial checks.
    spdk_host.no_servers()
    deadline=time.monotonic()+60
    stable=0
    while time.monotonic()<deadline:
        try:spdk_host.checked_kernel_devices();stable+=1
        except AssertionError:stable=0
        if stable==2:break
        time.sleep(2)
    assert stable==2, 'scratch devices did not become verifiably idle'
    spdk_host.prepare(discard=True)
elif sys.argv[1]=='resume':spdk_host.prepare(discard=False)
elif sys.argv[1]=='restore':spdk_host.restore()
else:raise ValueError(sys.argv)
