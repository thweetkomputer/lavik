"""Seed only, or measure read-only Stream commands on an immutable population."""
import os,sys
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
seed='--seed-only' in sys.argv
if seed:sys.argv.remove('--seed-only')
run.OPS['stream']=() if seed else ('XRANGE',)
run.main()
