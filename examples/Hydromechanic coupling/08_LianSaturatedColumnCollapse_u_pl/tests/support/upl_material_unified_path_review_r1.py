"""One offline review of the retained unified candidate paths; no rerun."""
import csv,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
from upl_material_path_review_r1 import values,yieldf,need,smt,write_json,SQ3
T=Path(__file__).resolve().parents[1];TAG='upl_material_unified_path_r1';P=T/'outputs'/TAG;OLD=T/'outputs/upl_material_path_r1'
CHECK=T/'logs'/f'{TAG}.review.json';TABLE=T/'figures'/f'{TAG}.csv'
need(not CHECK.exists() and not TABLE.exists(),'Existing analysis protected')
run=json.loads((T/'logs'/f'{TAG}.check.json').read_text());need(run['passed'],'Actual unified program completion required')
for e in run['outputs']:need(smt(e['path'])==e,'Bound unified native output changed')
models={x['model']:x for x in json.loads((OLD/'models.json').read_text())}
def key(r):return r['model'],int(r['N']),int(r['step'])
def load(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
old={key(r):r for r in load(OLD/'native.csv') if r['method']=='candidate_general'}
reference={key(r):r for r in load(OLD/'reference.csv')}
rows=load(P/'native.csv');need(len(rows)==len(old)==7560,'Complete candidate subset required')
need(len({key(r) for r in rows})==7560,'Unique actual material states required')
groups=defaultdict(list);maxstress=maxk=maxflow=maxhistory=maxstrain=maxsaved=0.
for r in rows:
    need(r['advanced']==r['path_valid']=='1' and r['status'] in ('Smooth','Elastic'),'Every declared smooth state must be accepted')
    k=key(r);b=old[k];ref=reference[k];m=models[k[0]]
    for f in ('model','method','N','step','segment','delta_diag','fit','K','G','phi_p','phi_r','n_p','coh_p','coh_r','n_c','psi0','sf','initial_I','initial_q'):need(r[f]==b[f],'Unchanged material input subset differs')
    s=np.array([float(r[f'new_{x}']) for x in ('xx','yy','zz','xy','yz','xz')]);bs=np.array([float(b[f'new_{x}']) for x in ('xx','yy','zz','xy','yz','xz')])
    gap=float(np.max(np.abs(s-bs)));kgap=abs(float(r['saved_kappa'])-float(b['saved_kappa']));maxstress=max(maxstress,gap);maxk=max(maxk,kgap)
    need(gap<=.01 and kgap<=1e-8,'Predeclared material merge regression bound failed')
    I=float(s[:3].sum());q=math.sqrt(((s[0]-s[1])**2+(s[1]-s[2])**2+(s[2]-s[0])**2)/6+float(s[3:]@s[3:]))
    kc=float(r['local_continuous_kappa']);lam=float(r['delta_lambda']);alpha,coh,beta=values(m,kc)
    trI=sum(float(r[f'trial_{x}']) for x in ('xx','yy','zz'))
    fg=abs((trI-I)-9*m['K']*beta*lam);maxflow=max(maxflow,fg)
    hg=abs(kc-float(r['old_kappa'])-float(r['plastic_dev_increment']));maxhistory=max(maxhistory,hg)
    sc=max(abs(float(r[f'strain_closure_{x}'])) for x in ('xx','yy','zz'));maxstrain=max(maxstrain,sc)
    need(fg<=1e-6 and hg<=1e-12 and sc<=1e-12,'Independent volumetric/deviatoric/strain closure failed')
    sf=float(r['saved_kappa']);need(float(np.float32(sf))==sf,'Float persistent kappa contract changed')
    yf=yieldf(m,I,q,sf);maxsaved=max(maxsaved,max(yf,0.))
    need(abs(yf-float(r['yield_new_saved_ref_Pa']))<=1e-6,'Independent coefficient/yield expression differs')
    ri,rq,rk=map(float,(ref['I_Pa'],ref['q_Pa'],ref['kappa']));target=np.array([ri/3+rq,ri/3-rq,ri/3,0,0,0])
    groups[(k[0],k[1])].append(dict(stress_ref=float(np.max(np.abs(s-target))),kappa_ref=abs(sf-rk),merge_stress=gap,merge_kappa=kgap,yield_positive=max(yf,0.)))
need(len(groups)==84,'All 84 material paths required')
metrics=[]
for (model,N),data in groups.items():
    need(len(data)==3*N,'Every strain segment retained')
    metrics.append(dict(model=model,N=N,max_stress_reference_error_Pa=max(x['stress_ref'] for x in data),max_kappa_reference_error=max(x['kappa_ref'] for x in data),max_merge_stress_difference_Pa=max(x['merge_stress'] for x in data),max_merge_kappa_difference=max(x['merge_kappa'] for x in data),max_saved_positive_yield_Pa=max(x['yield_positive'] for x in data)))
with TABLE.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
report=dict(stage=TAG+'.review',passed=True,actual_states=7560,complete_material_paths=84,max_merge_stress_difference_Pa=maxstress,max_merge_kappa_difference=maxk,max_volumetric_flow_residual_Pa=maxflow,max_continuous_history_closure=maxhistory,max_strain_closure=maxstrain,max_saved_positive_yield_Pa=maxsaved,metrics_N64=[x for x in metrics if x['N']==64],reference_not_rerun=True,physical_acceptance=False,production_changed=False,SHA_scans=0,table=smt(TABLE),source=smt(__file__),native=smt(P/'native.csv'))
write_json(CHECK,report);print(json.dumps({k:report[k] for k in ('passed','actual_states','complete_material_paths','max_merge_stress_difference_Pa','max_merge_kappa_difference','max_volumetric_flow_residual_Pa','max_continuous_history_closure','max_strain_closure')},indent=2))
