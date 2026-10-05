"""Seed, read or write ordinary short-key grouped controls with the shared runner."""
import os,sys
sys.path.insert(0,os.environ['LAVIK_BENCH_ROOT'])
import run
seed='--seed-only' in sys.argv;write='--write-only' in sys.argv
assert not (seed and write)
for flag in ['--seed-only','--write-only']:
 if flag in sys.argv:sys.argv.remove(flag)
run.OPS={kind:() if seed else (operations[1] if write else operations[0],) for kind,operations in run.OPS.items()}
run.main()
