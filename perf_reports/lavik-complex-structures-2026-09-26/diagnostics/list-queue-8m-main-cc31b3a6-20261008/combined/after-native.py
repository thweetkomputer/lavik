from pathlib import Path
import time,subprocess
W=Path(__file__).parent
while Path('/proc/1579600').exists():time.sleep(2)
assert 'ALL_QUEUEOPT_NATIVE_TESTS_PASS' in (W/'native-driver.log').read_text(), (W/'native-driver.log').read_text()[-2000:]
subprocess.run(['python3',str(W/'pairs.py')],check=True)
