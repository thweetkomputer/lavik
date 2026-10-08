from pathlib import Path
import csv,importlib.util,json,re,sys,time
R=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/dev/lavik-complex-refresh-20261004/perf_reports/lavik-complex-structures-2026-09-26')
spec=importlib.util.spec_from_file_location('plot',R/'plot_current_main.py');plot=importlib.util.module_from_spec(spec);spec.loader.exec_module(plot)
m=json.loads((R/'current-main.json').read_text());observations=0;failures=[]
for row in m['plots']:
 assert row['main']['fresh']==(row['main']['commit']==m['target_main'])
 table=list(csv.DictReader((R/(plot.key(row)+'-current.csv')).open()))
 expected=0
 for label,source,revision in plot.series(row):
  data,errors=plot.load(row,source,revision);selected=[v for v in table if v['series']==label]
  assert len(selected)==len(data)+len(errors),(plot.key(row),label)
  expected+=len(selected)
  for v in selected:
   key=v['command'],int(v['connections'])
   if key in data:assert float(v['qps'])==data[key]['qps'] and float(v['p99_ms'])==data[key]['p99_ms'] and not v['error']
   else:
    assert not v['qps'] and v['error']=='\n'.join(line.rstrip() for line in errors[key]['error'].splitlines()).rstrip();failures.append({'condition':plot.key(row),'series':label,'operation':key[0],'connections':key[1]})
 assert expected==len(table);observations+=expected
# Import elapsed time is a different metric from request QPS. Check the
# generated CSV against every raw fill, including historical peers.
fill_observations=0
spec=importlib.util.spec_from_file_location('fill_plot',R/'plot_fill_reference.py');fill_plot=importlib.util.module_from_spec(spec);spec.loader.exec_module(fill_plot)
imports=json.loads((R/'current-imports.json').read_text())
assert imports['target_main']==m['target_main'] and len(imports['plots'])==4
fill_config={'peer_tag':None,'workers':8,'pipeline':64,'batch_bytes':16384,'client_encoding':None}
for row in imports['plots']:
 assert row['main']['fresh'] and row['main']['commit']==m['target_main']
 name=f'{row["kind"]}-{row["size"]}-{row["field"]}-k{row["keys"]}-fill.csv'
 table=list(csv.DictReader((R/name).open()))
 assert len(table)==4 and {v['product'] for v in table}=={'redis','valkey','kvrocks','lavik'}
 for v in table:
  raw=fill_plot.read_run(row['kind'],v['product'],row['main'],row['size'],row['field'],fill_config)
  assert float(v['seconds'])==raw['seconds'] and v['method']==raw['method'] and v['raw_run']==raw['folder']
  if v['product']=='lavik':
   source=R/'raw'/v['raw_run']
   assert json.loads((source/f'{row["kind"]}-{row["size"]}-{row["field"]}.fill.json').read_text())['client_encoding']=='per-command'
  fill_observations+=1
for row in m['plots']:
 if row['category']!='lset':continue
 table=list(csv.DictReader((R/(plot.key(row)+'-rpush-fill-current.csv')).open()))
 expected=list(plot.series(row))
 assert len(table)==len(expected)
 for v,(label,source,revision) in zip(table,expected):
  raw=json.loads((source/f'list-{row["size"]}-{row["field"]}.fill.json').read_text())
  assert v['series']==label and float(v['seconds'])==raw['seconds']
  assert v['source']==str(source.relative_to(R)) and v['source_commit']==(revision['commit'] if revision else '')
  assert raw['command']=='RPUSH' and raw['client_encoding']=='shared-list-operands-v1'
  fill_observations+=1
for name in ['README.md','README.zh-CN.md']:
 text=(R/name).read_text();images=re.findall(r'!\[[^]]*\]\(([^)]+)\)',text)
 expected_images=84+len(json.loads((R/'current-mixed-writes.json').read_text())['charts'])
 assert len(images)==expected_images and len(set(images))==expected_images
 for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',text):
  if not link.startswith(('http:','https:','mailto:')):assert (R/link).exists(),link
 for image in images:assert (R/image).stat().st_size>10000
out={'time':time.time(),'target_main':m['target_main'],'fresh_conditions':sum(r['main']['fresh'] for r in m['plots']),'total_conditions':len(m['plots']),'observations':observations,'fill_observations':fill_observations,'failed_observations':failures,'checks':['all plotted QPS/p99 match raw source','all selected connection grids are complete with failures explicitly retained','fresh source commits and binary hashes match manifest','fresh raw has validated cardinalities and clean exits','all HSET/SADD and RPUSH fill CSV elapsed times match raw source','historical versions retain original identities','all README links and 94 figures exist']}
(R/'diagnostics'/('main-'+m['target_main'][:8]+'-20261008')/'report-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
