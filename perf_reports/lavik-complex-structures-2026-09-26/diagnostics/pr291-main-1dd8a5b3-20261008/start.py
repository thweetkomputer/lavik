from pathlib import Path
import time,subprocess,sys,hashlib,json
W=Path(__file__).parent
for file,marker in [('build-driver.log','PRODUCTION_PAIR_READY'),('client-build.log','CLIENT_READY')]:
 while marker not in (W/file).read_text():
  body=(W/file).read_text()
  if 'Traceback' in body:raise RuntimeError(body[-4000:])
  time.sleep(5)
sys.path.insert(0,'/mnt/dev/lavik-complex-iterations-20261004')
from host_execution_lock import acquire_host
lock=acquire_host('pr291-client-protocol-validation')
subprocess.run(['python3',str(W/'mock-client.py')],check=True)
lock.close()
R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
paths=[W/name for name in ['benchmark.py','run-random.py','host.py','private-tmp-exec.py','fixed-seed-exec.py','fixed-digest-seed.c','fixed-digest-seed.so','process_helpers.py','profile_capture.py','random-client.cpp','random-client','pairs.py']]+[R/name for name in ['run.py','spdk_host.py','run_with_memory_guard.py']]
(W/'harness-provenance.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},indent=2)+'\n')
subprocess.run(['python3',str(W/'pairs.py')],check=True)
