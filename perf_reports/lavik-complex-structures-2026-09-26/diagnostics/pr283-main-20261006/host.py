import sys
from pathlib import Path
ROOT=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0,str(ROOT))
import spdk_host
spdk_host.SETUP=Path('/mnt/dev/lavik-set-hash-20260929/bycorf/third_party/spdk/scripts/setup.sh')
if sys.argv[1]=='prepare':spdk_host.prepare(discard=True)
elif sys.argv[1]=='resume':spdk_host.prepare(discard=False)
elif sys.argv[1]=='restore':spdk_host.restore()
else:raise ValueError(sys.argv)
