"""Continue the authorized experiment once the native build and tests pass."""
from pathlib import Path
import subprocess
import time

W = Path(__file__).parent
pid = int((W / 'native.pid').read_text())
while True:
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except FileNotFoundError:
        break
    if state == 'Z':
        break
    time.sleep(10)
assert 'ALL_PR289_NATIVE_TESTS_PASS' in (W / 'native-driver.log').read_text()
for name in ['prepare-client', 'benchmark']:
    print('START', name, time.time(), flush=True)
    with (W / (name + '.log')).open('w') as log:
        subprocess.run(['python3', str(W / (name + '.py'))], stdout=log, stderr=subprocess.STDOUT, check=True)
    print('PASS', name, time.time(), flush=True)
