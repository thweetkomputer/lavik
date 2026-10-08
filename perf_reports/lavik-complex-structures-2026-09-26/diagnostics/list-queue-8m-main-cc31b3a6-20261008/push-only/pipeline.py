from pathlib import Path
import subprocess,time
W=Path(__file__).parent;O=Path('/mnt/dev/lavik-rpush-lpop-20261008')
while Path('/proc/1594164').exists():time.sleep(2)
with (O/'analysis.log').open('w') as f:subprocess.run(['python3',str(O/'finalize.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
with (W/'native-driver.log').open('w') as f:subprocess.run(['python3',str(W/'validate-native.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
with (W/'pairs.log').open('w') as f:subprocess.run(['python3',str(W/'pairs.py')],stdout=f,stderr=subprocess.STDOUT,check=True)
