"""Audit retained actual C++ paths against the independent differential reference."""
import csv,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from upl_material_path_review_r1 import values,derivs,yieldf,smt,need,write_json,SQ3
T=Path(__file__).resolve().parents[1];TAG='upl_material_path_r1';P=T/'outputs'/TAG
CHECK=T/'logs'/f'{TAG}.analysis.json';FIG=T/'figures'/f'{TAG}.png';CSV=T/'figures'/f'{TAG}.csv'
need(not any(p.exists() for p in (CHECK,FIG,CSV)),'Existing analysis evidence protected')
run=json.loads((T/'logs'/f'{TAG}.check.json').read_text());need(run['passed'],'Actual material target must pass first')
for e in run['outputs']:need(smt(e['path'])==e,'Retained native output identity changed')
reference_check=json.loads((P/'reference_audit_r1.json').read_text());need(reference_check['passed'],'Independent reference audit required')
mm={m['model']:m for m in json.loads((P/'models.json').read_text())}
refs={}
with (P/'reference.csv').open(newline='',encoding='utf-8') as f:
    for r in csv.DictReader(f):refs[(r['model'],int(r['N']),int(r['step']))]=[float(r[x]) for x in ('I_Pa','q_Pa','kappa','plastic_work_Pa','external_work_Pa')]
groups=defaultdict(list);checked=0;maxyieldgap=maxstrain=maxhistory=0.
with (P/'native.csv').open(newline='',encoding='utf-8') as f:
    for r in csv.DictReader(f):
        name,method,N,step=r['model'],r['method'],int(r['N']),int(r['step']);m=mm[name]
        need(r['advanced']=='1' and r['path_valid']=='1','No failed/skipped path may enter analysis')
        qref=refs[(name,N,step)];Iref,qrefv,kref=qref[:3]
        s=np.array([float(r[f'new_{x}']) for x in ('xx','yy','zz','xy','yz','xz')]);I=float(s[:3].sum());q=math.sqrt(((s[0]-s[1])**2+(s[1]-s[2])**2+(s[2]-s[0])**2)/6+float(s[3:]@s[3:]))
        k=float(r['saved_kappa']);need(float(np.float32(k))==k,'Actual persistent history must retain its float storage')
        target=np.array([Iref/3+qrefv,Iref/3-qrefv,Iref/3,0,0,0]);error=float(np.max(np.abs(s-target)))
        yf=yieldf(m,I,q,k);yieldgap=abs(yf-float(r['yield_new_saved_ref_Pa']));maxyieldgap=max(maxyieldgap,yieldgap)
        closure=max(abs(float(r[f'strain_closure_{x}'])) for x in ('xx','yy','zz'));maxstrain=max(maxstrain,closure)
        need(yieldgap<=1e-6 and closure<=1e-12,'Independent yield/elastic-plastic strain closure failed')
        history_gap=None
        if r['continuous_known']=='1':
            history_gap=abs(float(r['local_continuous_kappa'])-float(r['old_kappa'])-float(r['plastic_dev_increment']));maxhistory=max(maxhistory,history_gap)
            need(history_gap<=1e-12,'Claimed continuous history does not equal actual deviatoric plastic increment')
        # Discrete BE work identity is audited separately from continuum reference
        # work. The nonnegative elastic increment term is not a root residual.
        old=np.array([float(r[f'old_{x}']) for x in ('xx','yy','zz','xy','yz','xz')]);dp=np.array([float(r[f'plastic_{x}']) for x in ('xx','yy','zz','xy','yz','xz')])
        product=lambda a,b:float(a[:3]@b[:3]+2*a[3:]@b[3:])
        de=float(r['delta_diag']);Wext=(s[0]-s[1])*de;Wp=product(s,dp)
        oldI=old[:3].sum();oldq2=((old[0]-old[1])**2+(old[1]-old[2])**2+(old[2]-old[0])**2)/6+float(old[3:]@old[3:])
        dWe=(q*q-oldq2)/(2*m['G'])+(I*I-oldI*oldI)/(18*m['K'])
        ds=s-old;dsI=ds[:3].sum();dsq2=((ds[0]-ds[1])**2+(ds[1]-ds[2])**2+(ds[2]-ds[0])**2)/6+float(ds[3:]@ds[3:])
        elastic_increment=dsq2/(2*m['G'])+dsI*dsI/(18*m['K']);workgap=abs(Wext-Wp-dWe-elastic_increment)
        need(workgap<=1e-7,'Discrete work/elastic-energy identity failed')
        groups[(name,method,N)].append(dict(step=step,I=I,q=q,k=k,reference_I=Iref,reference_q=qrefv,reference_kappa=kref,stress_error_Pa=error,kappa_error=abs(k-kref),yield_Pa=yf,history_dev_gap=k-float(r['plastic_dev_accumulated']),strain=closure,work_identity_Pa=workgap,Wp=Wp,plastic_vol=float(r['plastic_vol_accumulated']),progress=step/(3*N)))
        checked+=1
need(checked==22680 and len(groups)==252,'All declared material path records required')
metrics=[]
for (name,method,N),rows in groups.items():
    need(len(rows)==3*N and [r['step'] for r in rows]==list(range(1,3*N+1)),'Complete ordered material path required')
    metrics.append(dict(model=name,method=method,N_per_segment=N,max_stress_path_error_Pa=max(x['stress_error_Pa'] for x in rows),max_kappa_path_error=max(x['kappa_error'] for x in rows),max_positive_yield_Pa=max(0.,max(x['yield_Pa'] for x in rows)),max_absolute_history_minus_actual_accumulated_dev=max(abs(x['history_dev_gap']) for x in rows),max_strain_closure=max(x['strain'] for x in rows),max_discrete_work_identity_Pa=max(x['work_identity_Pa'] for x in rows),end_I_Pa=rows[-1]['I'],end_q_Pa=rows[-1]['q'],end_kappa=rows[-1]['k'],end_reference_kappa=rows[-1]['reference_kappa'],plastic_work_BE_Pa=sum(x['Wp'] for x in rows)))
with CSV.open('x',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
label={'candidate_general':'Consistent endpoint; saved float kappa','linearized_dev':'Taylor; same deviatoric kappa','legacy_actual':'Actual legacy softening function'}
style={'candidate_general':('#1565c0','o'),'linearized_dev':('#00897b','s'),'legacy_actual':('#d35400','^')}
fig,ax=plt.subplots(2,2,figsize=(14,9),constrained_layout=True)
name='DP_PS_-5_combined';N=64
ref=groups[(name,'candidate_general',N)];x=[r['progress'] for r in ref]
ax[0,0].plot(x,[r['reference_q']/1000 for r in ref],'k--',lw=2,label='Independent differential reference')
ax[0,1].plot(x,[r['reference_kappa'] for r in ref],'k--',lw=2,label='Independent differential reference')
for method in label:
    r=groups[(name,method,N)];color,marker=style[method]
    ax[0,0].plot(x,[z['q']/1000 for z in r],color=color,marker=marker,markevery=16,ms=4,lw=1,label=label[method])
    ax[0,1].plot(x,[z['k'] for z in r],color=color,marker=marker,markevery=16,ms=4,lw=1,label=label[method])
    for j,key in enumerate(('max_stress_path_error_Pa','max_kappa_path_error')):
        worst=[max(r[key] for r in metrics if r['method']==method and r['N_per_segment']==n and not r['model'].endswith('_constant')) for n in (8,16,32,64)]
        ax[1,j].loglog((8,16,32,64),worst,color=color,marker=marker,label=label[method])
ax[0,0].set(title='Combined softening, DP_PS, psi0=-5 deg',xlabel='Strain-path progress',ylabel='q = sqrt(J2) [kPa]')
ax[0,1].set(title='Same path: persistent plastic history',xlabel='Strain-path progress',ylabel='Saved kappa')
ax[1,0].set(title='Worst path error: 12 evolving-law models',xlabel='Material increments per strain segment',ylabel='Maximum stress-component error [Pa]')
ax[1,1].set(title='Worst history error: 12 evolving-law models',xlabel='Material increments per strain segment',ylabel='Maximum kappa error')
for a in ax.flat:a.grid(True,which='both',alpha=.25);a.legend(fontsize=8)
fig.suptitle('Material integration audit (not a spatial/physical validation)\nLegacy sft uses a different history norm and has no dilation-decay input',fontsize=12)
fig.savefig(FIG,dpi=160);plt.close(fig)
samples=[r for r in metrics if r['N_per_segment']==64 and r['model'] in ('DP_PS_-5_combined','DP_PS_2.5_combined','DP_PS_2.5_coh','DP_PS_2.5_phi','DP_PS_2.5_psi')]
report=dict(stage=TAG+'.analysis',passed=True,all_rows=checked,path_groups=len(groups),independent_yield_expression_gap_Pa=maxyieldgap,max_strain_closure=maxstrain,max_continuous_history_closure=maxhistory,reference_checks=reference_check,selected_results_N64=samples,legacy_semantics='Actual ConsRelationEPsft_fast even for constant-law degeneracy; not the production basic/soft dispatch. No sf input. Includes historical full norm, plus consistency denominator, old-surface projection and float/1.732 coefficient effects.',candidate_semantics='Actual C++ general softening entry; 3 fits and regular compressive paths only. No apex/tension/phi0 claim.',physical_acceptance=False,whole_run_speed_claim=False,SHA_scans=0,artifacts=[smt(CSV),smt(FIG)],source=smt(__file__),retained_native=smt(P/'native.csv'))
write_json(CHECK,report)
print(json.dumps({k:report[k] for k in ('passed','all_rows','path_groups','independent_yield_expression_gap_Pa','max_strain_closure','max_continuous_history_closure','selected_results_N64')},indent=2))
