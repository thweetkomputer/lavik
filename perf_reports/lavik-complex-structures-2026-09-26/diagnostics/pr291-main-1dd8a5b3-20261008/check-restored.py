"""Read-only final host audit, serialized after the benchmark exits."""
from pathlib import Path
import datetime
import json
import os
import subprocess
import sys

W = Path(__file__).resolve().parent
R = Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
assert 'ALL_PR291_QPS_PAIRS_COMPLETE' in (W / 'pairs-driver.log').read_text()
sys.path.insert(0, '/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock = acquire_host('pr291-final-host-audit')
sys.path.insert(0, str(R))
import spdk_host
spdk_host.no_servers()
assert not (R / 'spdk-ready.json').exists()
devices = spdk_host.checked_kernel_devices()
hugepages = spdk_host.HUGEPAGES.read_text().strip()
unsafe = spdk_host.UNSAFE.read_text().strip()
assert hugepages == '0' and unsafe == 'N'
drivers = {pci: (Path('/sys/bus/pci/devices') / pci / 'driver').resolve().name
           for pci in ['18a2:00:00.0', 'a3a1:00:00.0', '668e:00:00.0',
                       'cc2f:00:00.0', 'fa20:00:00.0', '53c3:00:00.0']}
assert set(drivers.values()) == {'nvme'}
ssh_prefix = ['sudo', '-u', 'azureuser'] if os.geteuid() == 0 else []
remote = subprocess.run([*ssh_prefix, 'ssh', '-o', 'BatchMode=yes', 'azureuser@172.16.0.5',
                         'sha256sum /mnt/dev/random-client-pr291-20261008 /mnt/dev/random-client-pr291-20261008.cpp'],
                        text=True, capture_output=True, check=True).stdout
assert remote == json.loads((W / 'client-provenance.json').read_text())['remote_sha256']
result = {'passed': True, 'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'no_servers': True, 'devices': devices, 'drivers': drivers,
          'hugepages': hugepages, 'unsafe_noiommu': unsafe, 'client_sha256_after': remote}
(W / 'host-restored.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
