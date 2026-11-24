"""Plot the two deterministic cases from their model parameters."""
import csv
import io
from pathlib import Path
from zipfile import ZipFile
import matplotlib.pyplot as plt
from check_clearance import Trajectory

HERE = Path(__file__).resolve().parent
with ZipFile(HERE/'archived-results.zip') as archive:
    with archive.open('results/factorial.csv') as stream:
        rows = {int(r['case']):r for r in csv.DictReader(io.TextIOWrapper(stream))}
fig,axes = plt.subplots(1,2,figsize=(8.4,3.1),constrained_layout=True)
for ax, example, label in zip(axes, [2367,1437], ['Different braking caps','Equal caps, different onset rates']):
    row=rows[example]
    vf,vl,bf,bl,jf,jl,tau=(float(row[k]) for k in (
        'follower_speed_mps','leader_speed_mps','follower_decel_mps2','leader_decel_mps2',
        'follower_jerk_mps3','leader_jerk_mps3','follower_delay_s'))
    f=Trajectory(vf,bf,jf,tau);l=Trajectory(vl,bl,jl)
    end=max(f.times[-1],l.times[-1])
    times=[end*i/800 for i in range(801)]
    travel=[f.at(t)[0]-l.at(t)[0] for t in times]
    peak_t=float(row['maximizing_t_s']);peak=float(row['full_gap_m'])
    ax.axhline(0,color='#9aa4ae',lw=.7)
    ax.plot(times,travel,lw=2,color='#1d6178')
    ax.scatter([peak_t],[peak],s=22,c='#a34616',zorder=4)
    ax.scatter([end],[travel[-1]],s=22,facecolor='white',edgecolor='#1d6178',zorder=4)
    ax.annotate(f'{peak:.2f} m',(peak_t,peak),xytext=(0,6),textcoords='offset points',ha='center',fontsize=9)
    ax.set(title=label,xlabel='Time after start (s)',xlim=(-.03*end,1.04*end))
    ax.margins(y=.23);ax.spines[['right','top']].set_visible(False)
axes[0].set_ylabel('Follower minus leader travel (m)')
fig.savefig(HERE/'closure-witness.png',dpi=200,bbox_inches='tight')
