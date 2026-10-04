from pathlib import Path
import hashlib,json,shutil,subprocess,os
W=Path(__file__).parent;S=Path('/mnt/dev/lavik-complex-next-20261004');B=S/'build-spdk';R=Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip()
assert subprocess.check_output(['git','diff','HEAD','--','src','include','app','CMakeLists.txt','raft'],cwd=S)==b''
binary=Path('/mnt/dev/lavik-benchmark-binaries')/('lavik-main-'+commit[:8]+'-20261004')
shutil.copyfile(B/'lavik',binary);binary.chmod(0o755)
bycorf=Path('/mnt/dev/lavik-set-hash-20260929/bycorf');runtime=subprocess.check_output(['git','rev-parse','HEAD'],cwd=bycorf,text=True).strip()
assert runtime==subprocess.check_output(['git','rev-parse','HEAD:bycorf'],cwd=S,text=True).strip()
assert subprocess.check_output(['git','diff','HEAD','--','src','include'],cwd=bycorf)==b''
v={'commit':commit,'binary':str(binary),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_repo':str(S),'bycorf_commit':runtime,'build':'RelWithDebInfo, native, LTO, GCC 13, SPDK, BUILD_TESTING=OFF, LAVIK_ENABLE_TEST_FAULTS=OFF','build_directory':str(B),'no_build_or_tests_during_measurements':True}
(W/'versions.json').write_text(json.dumps({'main':v},indent=2)+'\n')
d=R/'diagnostics'/('main-'+commit[:8]+'-20261004');d.mkdir(parents=True,exist_ok=True)
(d/'host-and-build.json').write_text(json.dumps({'build':v,'cpu':json.loads(subprocess.check_output(['lscpu','-J'],text=True)),'peer_measurements':'Historical raw records, not rerun in this round'},indent=2)+'\n')
shutil.copyfile(B/'CMakeCache.txt',d/'CMakeCache.txt')
for name in ['current-main.json','current-imports.json']:
 p=R/name;m=json.loads(p.read_text());m['build_proof']=str((d/'host-and-build.json').relative_to(R));p.write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps(v,indent=2))
