from pathlib import Path
import csv,importlib.util,json,re,time
R=Path(__file__).resolve().parents[2]
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
    assert not v['qps'] and v['error']==errors[key]['error'];failures.append({'condition':plot.key(row),'series':label,'operation':key[0],'connections':key[1]})
 assert expected==len(table);observations+=expected
for name in ['README.md','README.zh-CN.md']:
 text=(R/name).read_text();images=re.findall(r'!\[[^]]*\]\(([^)]+)\)',text)
 assert len(images)==84 and len(set(images))==84
 for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)',text):
  if not link.startswith(('http:','https:','mailto:')):assert (R/link).exists(),link
 for image in images:assert (R/image).stat().st_size>10000
out={'time':time.time(),'target_main':m['target_main'],'fresh_conditions':sum(r['main']['fresh'] for r in m['plots']),'total_conditions':len(m['plots']),'observations':observations,'failed_observations':failures,'checks':['all plotted QPS/p99 match raw source','all selected connection grids are complete with failures explicitly retained','fresh source commits and binary hashes match manifest','fresh raw has validated cardinalities and clean exits','historical versions retain original identities','all README links and 84 figures exist']}
(R/'diagnostics'/('main-'+m['target_main'][:8]+'-20261004')/'report-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
