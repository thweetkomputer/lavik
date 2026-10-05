"""Measure only ZSCORE or ZINCRBY, or seed without running measured commands."""
import os,sys
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
seed='--seed-only' in sys.argv
write='--write-only' in sys.argv
assert not (seed and write)
for flag in ['--seed-only','--write-only']:
 if flag in sys.argv:sys.argv.remove(flag)
run.OPS['zset']=() if seed else ('ZINCRBY',) if write else ('ZSCORE',)
run.main()
