import importlib.util
from pathlib import Path
import sys
import urllib.request

root = Path('/mnt/dev/lavik-set-hash-20260929/perf_reports/lavik-complex-structures-2026-09-26')
sys.path.insert(0, str(root))
spec = importlib.util.spec_from_file_location('bench', root / 'run.py')
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)
original_server, original_measure = bench.server, bench.measure

def server(product, directory, binary):
    argv, env = original_server(product, directory, binary)
    assert '--metrics-port=0' in argv
    argv[argv.index('--metrics-port=0')] = '--metrics-port=39100'
    return argv, env

def snapshot(path):
    with urllib.request.urlopen('http://172.16.0.4:39100/metrics', timeout=20) as response:
        path.write_bytes(response.read())

def measure(directory, kind, size, field_bytes, entries, keys, op, conns, seconds, threads):
    stem=f'{kind}-{size}-{field_bytes}-{op.lower()}-c{conns}'
    snapshot(directory / (stem + '.metrics-before.txt'))
    original_measure(directory, kind, size, field_bytes, entries, keys, op, conns, seconds, threads)
    snapshot(directory / (stem + '.metrics-after.txt'))

bench.server, bench.measure = server, measure
bench.main()
