#!/usr/bin/env python3
# Copyright (C) 2026 EloqData Inc.
# SPDX-License-Identifier: Apache-2.0
"""Render the validated 16-window YCSB matrix using the peer-report house style."""
import hashlib,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter,MultipleLocator
ROOT=Path(__file__).resolve().parent
COLORS={'hreplace':'#1473E6','aerospike':'#E97827'}
NAMES={'hreplace':'Lavik 0.1.0 · 12 workers + 4 IRQ CPUs','aerospike':'Aerospike 8.1.2.4 · default settings'}
ORDER=['aerospike','hreplace']

def frame(title,subtitle):
 fig=plt.figure(figsize=(16,11.7),facecolor='white')
 fig.text(.045,.955,title,fontsize=24,weight='bold',va='top')
 fig.text(.045,.91,subtitle,fontsize=14,color='#566573')
 fig.legend(handles=[Patch(facecolor=COLORS[s],edgecolor='white',hatch='..' if s=='aerospike' else '///',label=NAMES[s]) for s in ORDER],loc='upper center',bbox_to_anchor=(.52,.88),ncol=2,frameon=False,fontsize=12)
 return fig,[fig.add_axes([.09,.50,.875,.28]),fig.add_axes([.09,.115,.875,.28])]

def save(fig,name):
 fig.text(.045,.04,'100M fresh records per database · 10 × 128 B fields · six-NVMe RAID0 · kernel TCP · defrag enabled',fontsize=11.5,color='#566573')
 for ext in ['svg','png']:
  fig.savefig(ROOT/f'{name}.{ext}',dpi=150,metadata={'Date':None} if ext=='svg' else {})
 plt.close(fig)

def style(ax,title,labels,ylabel,top,qps=False):
 ax.set_title(title,loc='left',fontsize=18,weight='bold',pad=15)
 ax.set_axisbelow(True);ax.grid(axis='y',color='#DDE3E8',linewidth=.8)
 ax.spines[['top','right']].set_visible(False)
 for side in ['left','bottom']:ax.spines[side].set_color('#7B8794')
 ax.tick_params(axis='both',length=0,pad=10,labelsize=12,colors='#566573')
 ax.set_xticks(range(len(labels)),labels);ax.set_ylim(0,top)
 ax.set_xlim(-.6,len(labels)-.4);ax.set_ylabel(ylabel,fontsize=12,labelpad=12)
 if qps:ax.yaxis.set_major_formatter(FuncFormatter(lambda n,_:f'{n/1000:g}k'))

def main():
 plt.rcParams.update({'font.family':'DejaVu Sans','text.color':'#17202A','axes.labelcolor':'#17202A','svg.fonttype':'none','svg.hashsalt':'lavik010-ycsb20261013','hatch.linewidth':.8})
 data=json.loads((ROOT/'results.json').read_text());assert data['complete']
 totals={(r['mode'],r['workload'],r['target']):r for r in data['total_qps']}
 rows={(r['mode'],r['workload'],r['target'],r['operation']):r for r in data['rows']}
 assert len(totals)==16 and len(rows)==28
 fig,axes=frame('Lavik and Aerospike · YCSB throughput','256 client workers · 300 s/run · A/B/C/D-Uniform · one measured window per case')
 for ax,t in zip(axes,[100000,0]):
  top=math.ceil(max(r['qps'] for r in totals.values() if r['target']==t)/100000)*100000*1.12
  style(ax,'100K target' if t else 'Unlimited',list('ABC')+['D-Uniform'],'Successful operations/s',top,True)
  for i,m in enumerate(ORDER):
   vals=[totals[m,w,t]['qps'] for w in 'ABCD']
   bars=ax.bar([x+(i-.5)*.32 for x in range(4)],vals,width=.29,color=COLORS[m],edgecolor='white',hatch='..' if m=='aerospike' else '///')
   ax.bar_label(bars,labels=[f'{v/1000:.1f}k' for v in vals],padding=4,fontsize=11)
 save(fig,'ycsb-qps')
 ops=[('A','READ'),('A','UPDATE'),('B','READ'),('B','UPDATE'),('C','READ'),('D','READ'),('D','INSERT')]
 for metric,label in [('p99_ms','p99'),('p999_ms','p99.9'),('p9999_ms','p99.99')]:
  fig,axes=frame(f'{label} latency · Lavik and Aerospike','Complete-window operation HDR histograms · READ and write operations shown separately')
  top=max(r[metric] for r in rows.values())*1.15
  for ax,t in zip(axes,[100000,0]):
   style(ax,'100K target' if t else 'Unlimited',[w+'\n'+op for w,op in ops],label+' latency (ms)',top)
   for i,m in enumerate(ORDER):
    vals=[rows[m,w,t,op][metric] for w,op in ops]
    ax.bar([x+(i-.5)*.32 for x in range(len(ops))],vals,width=.29,color=COLORS[m],edgecolor='white',hatch='..' if m=='aerospike' else '///')
  save(fig,'ycsb-'+label.replace('.',''))
 (ROOT/'chart-SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(ROOT.iterdir()) if p.suffix in ['.svg','.png']))
 print('Validated 16 totals / 28 operation rows; rendered 4 figures as SVG and PNG.')
if __name__=='__main__':main()
