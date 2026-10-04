import os,sys
from pathlib import Path
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
run.OPS['stream']=('XADD_MAXLEN',)
run.main()
