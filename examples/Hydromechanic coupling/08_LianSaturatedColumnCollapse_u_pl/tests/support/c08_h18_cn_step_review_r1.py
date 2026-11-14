"""One offline review of the completed finite-Kw CN component, never a solver."""
import argparse, csv, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1]
TAG='c08_h18_cn_step_review_r1'

def need(ok, message):
    if not ok: raise RuntimeError(message)

def stat(p):
    p=Path(p).resolve();s=p.stat()
    return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def table(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--execution-authorized',action='store_true')
    need(a.parse_args().execution_authorized,'Independent root review required')
    src=T/'outputs/c08_h18_cn_step_r1';old=T/'outputs/c08_h18_late_step_r1_p300'
    out=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json')
    need(not out.exists() and not check.exists(),'Existing derived outputs protected')
    cp=T/'logs/c08_h18_cn_step_r1.check.json';op=T/'logs/c08_h18_late_step_r1_p300.check.json'
    cc,oc=read(cp),read(op)
    need(cc['passed'] and oc['passed'] and cc['consumed_stats_unchanged'] and oc['consumed_stats_unchanged'], 'Completed single-step receipts required')
    bound=[stat(cp),stat(op),stat(__file__)]
    for c in [cc,oc]:
        for k in ['completion','actual_call','build']:
            need(stat(c[k]['path'])==c[k],'Bound receipt changed');bound.append(c[k])
        call=read(c['actual_call']['path'])
        need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Owned component failed')
    done=read(cc['completion']['path'])
    need(done['physical_steps']==1 and done['extra_OFF_trajectories']==0 and done['pressure_CN_interventions']==1
         and done['source_part']==300 and done['completed_step']==2600001,'One declared intervention required')
    for e in cc['outputs']+oc['outputs']:
        need(stat(e['path'])==e,'Bound component output changed');bound.append(e)
    names=['stages.csv','midpoint_rows.csv','pressure.csv','balance.csv','constant_source.csv','coupled_CN.csv','material_shadow.csv']
    data={n:table(src/n) for n in names};baseline=table(old/'stages.csv')
    need([len(data[n]) for n in names]==[40000,5000,5000,5000,15000,6,10000],'Exact component coverage required')
    need(len(baseline)==35000,'Retained original control incomplete')
    by={(r['stage'],r['native_id']):r for r in data['stages.csv']};ref={(r['stage'],r['native_id']):r for r in baseline}
    need(len(by)==40000 and len(ref)==35000,'Repeated stage/ID')
    pairs=[]
    for stage in ['restored_n','force_n','half_before_divide','half_after_divide','force_h','raw_original_commit','completed_cap']:
        control='raw_full' if stage=='raw_original_commit' else stage
        keys=[k for k in baseline[0] if k!='stage' and (stage!='completed_cap' or k!='p_Pa')]
        for ident in range(2060,7060):
            x,y=by[stage,str(ident)],ref[control,str(ident)]
            need(all(x[k]==y[k] for k in keys),'Captured original field changed: '+stage+'/'+str(ident))
        pairs.append(dict(candidate_stage=stage,control_stage=control,IDs=5000,exact_CSV_fields=len(keys),all_equal=True,
                          excluded_pressure=stage=='completed_cap',not_full22_native_bitproof=True))
    p=data['pressure.csv'];ids=[int(r['native_id']) for r in p]
    need(len(set(ids))==5000 and set(ids)==set(range(2060,7060)),'All original soil IDs required')
    x=np.array([float(r['x_next']) for r in p]);z=np.array([float(r['z_next']) for r in p])
    delta=np.array([float(r['raw_change_Pa']) for r in p]);explicit=np.array([float(r['p_original_raw'])-float(r['p_n']) for r in p])
    candidate=np.array([float(r['p_CN_raw'])-float(r['p_n']) for r in p])
    for r in p:
        pn,ph,R,M,S,h=[float(r[k]) for k in ['p_n','p_h','R_h','M_h','S_h','dt_s']]
        s=S/M;den=1+.5*h*s;new=pn+h*(R+s*(ph-pn))/den
        need(math.isfinite(den) and den!=0 and den==float(r['CN_denominator']),'Actual midpoint denominator differs')
        need(float(np.float32(new))==float(r['p_CN_raw']),'Candidate float commit differs')
        need(abs(float(r['CN_float_cast_error_Pa']))<=float(r['CN_float_cast_budget_Pa']),'Original float budget failed')
        need(float(r['p_CN_raw'])-float(r['p_original_raw'])==float(r['raw_change_Pa']),'Recorded intervention differs')
        need(float(r['p_CN_after_cap'])==float(r['p_CN_raw']),'Unexpected cap needs separate review')
    for r in data['balance.csv']:
        need(abs(float(r['closure']))<=float(r['arithmetic_budget']),'Original declared balance budget failed')
    for r in data['constant_source.csv']:
        need(abs(float(r['error']))<=float(r['arithmetic_budget']),'Constant-source manufacture failed')
    out.mkdir();outputs=[]
    for name,rows in [('stage_comparison.csv',pairs),('pressure.csv',p),('midpoint_rows.csv',data['midpoint_rows.csv'])]:
        dest=out/name
        with dest.open('x',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        outputs.append(dest)
    summary=dict(changed_IDs=int(np.count_nonzero(delta)),pressure_change_RMS_Pa=float(np.sqrt(np.mean(delta**2))),
        pressure_change_mean_Pa=float(delta.mean()),pressure_change_maxabs_Pa=float(np.abs(delta).max()),
        original_increment_RMS_Pa=float(np.sqrt(np.mean(explicit**2))),candidate_increment_RMS_Pa=float(np.sqrt(np.mean(candidate**2))),
        negative_denominators=done['negative_finite_denominators'],constant_source_rows=15000,
        original_shared_capture_rows=35000,full22_equivalence_claimed=False,physical_acceptance=False)
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    lim=max(float(np.abs(delta).max()),np.finfo(float).tiny)
    sc=ax[0,0].scatter(x,z,c=delta,s=5,cmap='coolwarm',vmin=-lim,vmax=lim)
    ax[0,0].set(xlabel='x [m]',ylabel='z [m]',title='Candidate minus original raw pressure [Pa]');ax[0,0].set_aspect('equal');fig.colorbar(sc,ax=ax[0,0])
    ax[0,1].hist(delta,bins=41);ax[0,1].set(xlabel='Pressure change [Pa]',ylabel='Soil IDs',title='All5000 IDs; exact float commits')
    ax[1,0].scatter(explicit,candidate,s=3);lo=min(explicit.min(),candidate.min());hi=max(explicit.max(),candidate.max())
    ax[1,0].plot([lo,hi],[lo,hi],'k--',lw=.8);ax[1,0].set(xlabel='Original increment [Pa]',ylabel='CN increment [Pa]',title='One true-midpoint 5 us CPU step')
    ax[1,1].axis('off');ax[1,1].text(0,1,'RMS pressure change: %.8g Pa\nMaximum: %.8g Pa\nMean: %.8g Pa\nChanged IDs: %d/5000\n\nNo new OFF trajectory\nNo global implicit/TPI/beta\nNot a physical repair or full22 bit proof'%(
        summary['pressure_change_RMS_Pa'],summary['pressure_change_maxabs_Pa'],summary['pressure_change_mean_Pa'],summary['changed_IDs']),va='top',fontsize=11)
    fig.suptitle('Finite-Kw diagonal CN: isolated Part300 single step\nPressure intervention only; original boundary/material/geometry retained')
    dest=out/'comparison.png';fig.savefig(dest,dpi=170,bbox_inches='tight');plt.close(fig);outputs.append(dest)
    need(all(stat(e['path'])==e for e in bound),'Consumed evidence changed')
    with check.open('x',encoding='utf-8') as f:json.dump(dict(stage=TAG,analysis_complete=True,summary=summary,
        consumed=bound,consumed_stats_unchanged=True,outputs=[stat(q) for q in outputs],visual_QA_pending=True,
        solver_invocations=0,native_invocations=0,physical_acceptance=False,SHA_scans=0),f,indent=2,allow_nan=False)
    print(json.dumps(summary))

if __name__=='__main__':main()
