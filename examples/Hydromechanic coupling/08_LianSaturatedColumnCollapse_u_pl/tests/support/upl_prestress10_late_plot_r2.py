"""Zoom the closed 8-10s CSV history; no solver, decoder, fitting or new gate."""
from pathlib import Path
from upl_plastic_periodic_pair_r1 import np,plt,need,js,stat,table,write
T=Path(__file__).resolve().parents[1]
P=T/'figures/upl_prestress10_equilibrium_review_r1'
OUT=T/'figures/upl_prestress10_late_r2'
check=Path(str(P)+'.check.json');source=Path(str(P)+'_history.csv')
need(js(check)['offline_analysis_completed'],'Closed full review required')
before=[stat(check),stat(source),stat(Path(__file__))]
paths=[Path(str(OUT)+s) for s in ('.png','.csv','.check.json')]
need(not any(p.exists() for p in paths),'Retained plot protected')
rows=[r for r in table(source) if float(r['actual_time_s'])>=8.]
allrows=[r for r in rows if r['initial_material_group']=='all']
t=np.array([float(r['actual_time_s']) for r in allrows])
fig,axs=plt.subplots(2,3,figsize=(13,7.6))
for ax,key,title,unit in zip((axs[0,0],axs[0,1],axs[1,0],axs[1,1],axs[1,2]),
 ('current_head_residual_RMS_Pa','p_mean_Pa','velocity_RMS_m_s','kinetic_J_per_m','total_zz_compression_mean_Pa'),
 ('Pressure minus fixed-H head','Actual pressure mean','Actual velocity RMS','Current-mixture kinetic energy','Mean total vertical compression'),
 ('RMS (Pa)','pressure (Pa)','velocity (m/s)','energy (J/m)','compression (Pa)')):
 ax.plot(t,[float(r[key]) for r in allrows]);ax.set(title=title,ylabel=unit)
 if key in ('velocity_RMS_m_s','kinetic_J_per_m'):ax.set_yscale('log')
 else:ax.ticklabel_format(axis='y',style='plain',useOffset=False)
for band in ('top_2h','bottom_2h'):
 r=[r for r in rows if r['initial_material_group']==band]
 u=np.array([float(q['material_settlement_mean_mm']) for q in r])
 axs[0,2].plot([float(q['actual_time_s']) for q in r],u-u[0],label=band)
axs[0,2].set(title='Additional material settlement',ylabel='additional downward displacement (mm)');axs[0,2].legend()
for ax in axs.flat:ax.set_xlabel('actual saved time (s)');ax.grid(alpha=.25)
fig.suptitle('Case08 completed preload: genuine saved 8-10s history',fontsize=13)
fig.tight_layout(rect=(0,.04,1,.95));fig.text(.5,.008,'Fixed H=2m is an initial reference plane. The remaining trends are retained; no equilibrium threshold or fitted reference.',ha='center',fontsize=8)
fig.savefig(paths[0],dpi=170);plt.close(fig);write(paths[1],rows)
need(all(stat(e['path'])==e for e in before),'Closed input changed')
with paths[2].open('x',encoding='utf-8') as f:
 import json
 json.dump(dict(completed=True,inputs=before,outputs=[stat(p) for p in paths[:2]],actual_start_s=float(t[0]),actual_end_s=float(t[-1]),physical_acceptance=False,SHA_scans=0),f,indent=2);f.write('\n')
