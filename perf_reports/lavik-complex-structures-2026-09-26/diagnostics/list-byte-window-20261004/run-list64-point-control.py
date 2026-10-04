import os,sys
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
run.OPS['list']=(os.environ['LAVIK_LIST_CONTROL_OP'],)
run.main()
