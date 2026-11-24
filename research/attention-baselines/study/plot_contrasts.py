"""Plot all seed-specific timing ratios for the 32-step slice of the archived CPU grid."""
from pathlib import Path
import csv
from statistics import median
import matplotlib.pyplot as plt

root=Path(__file__).resolve().parent
with (root/'outputs/historical-cases.csv').open() as f: rows=list(csv.DictReader(f))
fig, axes=plt.subplots(1,2,figsize=(8.0,3.6),sharey=True,constrained_layout=True)
for batch,ax in zip((1,4),axes):
    for label,num,color,offset in [('Dense all outputs','dense_all','#1a5775',-.06),
                                  ('Fused last query','last_query_recompute','#a43c11',.06)]:
        levels=[16,64,128,256]
        groups=[[float(r['ratio_of_medians']) for r in rows if r['numerator']==num and int(r['batch'])==batch
                 and int(r['prefix'])==p and int(r['decode'])==32] for p in levels]
        assert all(len(values)==3 for values in groups)
        xs=[i+offset for i in range(4)]
        ax.plot(xs,[median(g) for g in groups],color=color,marker='o',lw=1.4,ms=4,label=label)
        for x,g in zip(xs,groups):
            ax.scatter([x]*3,g,s=10,alpha=.55,facecolor=color,edgecolors='none')
    ax.set_title(f'Batch {batch}',loc='left',fontsize=11)
    ax.set_xticks(range(4),levels)
    ax.set_xlabel('Prefix positions')
    ax.set_yscale('log',base=2)
    ax.axhline(1,color='0.35',lw=.8,ls='--')
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='y',color='0.89',linewidth=.55)
axes[0].set_ylabel('Recomputation time / cached time')
axes[0].set_yticks([.5,1,2,4,8,16,32],['0.5','1','2','4','8','16','32'])
axes[0].legend(fontsize=8,loc='upper left',frameon=False)
fig.savefig(root/'outputs/archived-contrasts.png',dpi=200,facecolor='white')
