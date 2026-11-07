"""Only sealed native data: localize history differences without inferring unobserved stages."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from basic_material_review_r1 import load,write
from basic_material_r1 import context,need,stat,save
_,t,*_=context('column');old,new=[load(t,'full',m) for m in ('old','new')];a,b=old['a'],new['a'];fix=old['fixed'];x0=a['state'][0];top=x0[:,2]==x0[:,2].max()
def inv(s):
    I=s[...,0]+s[...,1]+s[...,2];q=np.sqrt(((s[...,0]-s[...,1])**2+(s[...,1]-s[...,2])**2+(s[...,2]-s[...,0])**2)/6+np.sum(s[...,3:]**2,axis=-1));return I,q
rows=[]
for part,(time,v) in enumerate(zip(a['time'],a['state'])):
    j=int(np.argmin(abs(b['time']-time)));w=b['state'][j];d=w-v;i=int(np.argmax(abs(d[:,7])));io,qo=inv(v[i,8:]);inn,qn=inv(w[i,8:]);ds=d[:,8:14];frob=np.sum(ds[:,:3]**2,axis=1)+2*np.sum(ds[:,3:]**2,axis=1)
    rows.append(dict(old_part=part,new_nearest_part=j,old_actual_time_s=float(time),new_actual_time_s=float(b['time'][j]),time_gap_s=float(b['time'][j]-time),different_kappa_IDs=int(np.count_nonzero(d[:,7])),max_abs_kappa_gap=float(abs(d[i,7])),max_gap_original_ID=fix+i,max_gap_z0_m=float(x0[i,2]),old_kappa_at_max_gap=float(v[i,7]),new_kappa_at_max_gap=float(w[i,7]),old_I_at_max_gap_Pa=float(io),old_q_at_max_gap_Pa=float(qo),new_I_at_max_gap_Pa=float(inn),new_q_at_max_gap_Pa=float(qn),old_top15_mean_kappa=float(v[top,7].mean()),new_top15_mean_kappa=float(w[top,7].mean()),sigma_Frobenius_RMS_gap_Pa=float(np.sqrt(frob.mean())),top_material_settlement_gap_m=float(-d[top,2].mean())))
v=a['state'][-1];w=b['state'][-1];d=w-v;io,qo=inv(v[:,8:]);inn,qn=inv(w[:,8:]);layers=[dict(id=fix+i,x0_m=float(x0[i,0]),z0_m=float(x0[i,2]),old_kappa=float(v[i,7]),new_kappa=float(w[i,7]),new_minus_old_kappa=float(d[i,7]),old_I_Pa=float(io[i]),old_q_Pa=float(qo[i]),new_I_Pa=float(inn[i]),new_q_Pa=float(qn[i])) for i in range(len(v))]
prefix='basic_material_kappa_r1';paths=[t/'figures'/(prefix+s) for s in ('.png','_history.csv','_final.csv')];check=t/'logs'/(prefix+'.review.json');need(not any(p.exists() for p in [*paths,check]),'Fresh localization artifacts required');write(paths[1],rows);write(paths[2],layers)
fig,ax=plt.subplots(1,3,figsize=(14,4.4),layout='constrained');tm=a['time'];ax[0].plot(tm,[r['old_top15_mean_kappa'] for r in rows],label='old top15 mean');ax[0].plot(tm,[r['new_top15_mean_kappa'] for r in rows],label='new top15 mean');ax[0].set(xlabel='actual time (s)',ylabel='saved kappa',title='Local offset already visible at first 0.1 s save');ax[0].legend(fontsize=8)
ax[1].scatter(d[:,7],x0[:,2],s=8);ax[1].set(xlabel='new - old kappa at final states',ylabel='original z (m)',title='All750 original soil IDs; strongest at top')
ax[2].plot(tm,[r['sigma_Frobenius_RMS_gap_Pa'] for r in rows],color='tab:green');ax[2].set(xlabel='old actual time (s)',ylabel='stress Frobenius RMS gap (Pa)',title='Stress and settlement remain close');other=ax[2].twinx();other.plot(tm,[1e6*r['top_material_settlement_gap_m'] for r in rows],color='tab:red');other.set_ylabel('top settlement gap (micrometre)',color='tab:red')
for aa in ax:aa.grid(alpha=.25)
fig.suptitle('Same-input CPU1 basic case: nearest actual saved states, no interpolation\nNo stage trial/status is stored: saved compressive stress cannot certify or exclude earlier apex/tension repair',fontsize=10);fig.savefig(paths[0],dpi=160);plt.close(fig)
first=next(r for r in rows if r['different_kappa_IDs']);deps=old['source']+new['source'];need(all(stat(e['path'])==e for e in deps),'Sealed native inputs changed');save(check,dict(passed=True,first_observed_difference=first,first_appearance_interval_s=[0,float(first['old_actual_time_s'])],final_max_abs_kappa_gap=max(abs(d[:,7])),final_top15_max_abs_kappa_gap=max(abs(d[top,7])),final_other735_max_abs_kappa_gap=max(abs(d[~top,7])),final_exact_zero_stress_old=int(np.count_nonzero((io==0)&(qo==0))),final_exact_zero_stress_new=int(np.count_nonzero((inn==0)&(qn==0))),actual_branch_or_trial_observed=False,no_new_solver=True,interpolation=False,physical_cause_proved=False,visual_QA_pending=True,consumed=deps,consumed_stats_unchanged=True,files=[stat(p) for p in paths],SHA_scans=0));print('KAPPA_LOCALIZATION_COMPLETE',paths[0])
