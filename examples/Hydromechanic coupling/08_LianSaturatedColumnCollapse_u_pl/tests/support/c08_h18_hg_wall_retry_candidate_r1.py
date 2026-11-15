"""One offline wall-retry counterfactual over the already reviewed actual packet."""
import argparse
import inspect
import json
import math
from pathlib import Path
import struct
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_hg_wall_fault_review_r1 as fault

T=fault.T
TAG='c08_h18_hg_wall_retry_candidate_r1'
NOTE=T/'notes'/(TAG+'.md')
CHECK=T/'logs'/(TAG+'.check.json')
PREFIX=T/'figures'/TAG
ORIGINAL="        if complete and not geometry and not attempt and nearfinite and (nearx!=0 or nearz!=0):"
COUNTERFACTUAL="        if complete and ((not geometry) or (geometry and row['independent_C_det'] is not None and math.isfinite(row['independent_C_det']) and row['independent_C_det']<=0)) and not attempt and nearfinite and (nearx!=0 or nearz!=0):"
need,read,stat,bind=fault.need,fault.read,fault.stat,fault.bind


def same_values(a,b):
    need(set(a)==set(b),'Original and counterfactual first-pass keys differ')
    for key in a:
        x,y=a[key],b[key]
        if isinstance(x,(float,np.floating)):
            need(isinstance(y,(float,np.floating)) and struct.pack('<d',float(x))==struct.pack('<d',float(y)),
                 'Original first-pass scalar bits changed: '+key)
        else:need(x==y,'Original first-pass value changed: '+key)


def counterfactual():
    source=inspect.getsource(fault.recompute)
    need(source.count(ORIGINAL)==1,'Exactly one original terminal retry condition required')
    changed=source.replace(ORIGINAL,COUNTERFACTUAL,1)
    need(changed.count(COUNTERFACTUAL)==1 and changed.replace(COUNTERFACTUAL,ORIGINAL,1)==source,
         'The sole condition edit must reverse to all original function bytes')
    namespace=dict(vars(fault))  # Do not replace or mutate fault.recompute/module globals.
    exec(compile(changed,'<'+TAG+':one_condition_counterfactual>','exec'),namespace)
    return namespace['recompute'],dict(original_condition=ORIGINAL,counterfactual_condition=COUNTERFACTUAL,
        replacements=1,source_function_bytes=len(source.encode('utf-8')),inverse_restores_original_function_bytes=True,
        original_module_function_replaced=False,arithmetic_neighbor_order_and_thresholds_changed=False)


def plot(source,candidate,donors,arrays,fluid,target):
    shown=[('Original source',source[-1]),('Counterfactual retry',candidate[-1])]
    value=lambda row,key:np.nan if row[key] is None or not math.isfinite(float(row[key])) else float(row[key])
    fig,axes=plt.subplots(2,2,figsize=(13,8.7),layout='constrained')
    xyz=np.c_[arrays['Posxy'],arrays['Posz'][:,0]];B=xyz[target];mask=fluid&np.all(np.isfinite(xyz),axis=1)&(abs(xyz[:,0]-B[0])<.4)&(abs(xyz[:,2]-B[2])<.4)
    ax=axes[0,0];ax.scatter(xyz[mask,0],xyz[mask,2],s=10,c='.8',label='Captured fluid inputs')
    for ci,(label,row) in enumerate(shown):
        rr=[q for q in donors if q['method']==label and q['attempt']==row['attempt']]
        ax.scatter([q['actual_x'] for q in rr],[q['actual_z'] for q in rr],s=24,marker=('o','x')[ci],facecolors='none' if ci==0 else None,edgecolors='C0' if ci==0 else None,c=None if ci==0 else 'C1',label=label+' donors')
        ax.scatter([row['Gx']],[row['Gz']],marker='D',s=60,c='C'+str(ci),label=label+' fit G')
    ax.scatter([B[0]],[B[2]],c='k',marker='*',s=90,label='Actual captured wall B')
    ax.set(title='Original G first, one nearest recenter only',xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal');ax.legend(fontsize=8)
    names=[q[0]+'\n(attempt '+str(q[1]['attempt'])+')' for q in shown];x=np.arange(2)
    determinants=[abs(value(q[1],'independent_M_det')) for q in shown]
    axes[0,1].bar(x,[v if v>0 else np.nan for v in determinants],color=['C0','C1']);axes[0,1].axhline(.001,color='red',ls='--',label='Original geometry limit .001')
    axes[0,1].set(title='Independent moment determinant',ylabel='|det M|',yscale='log',xticks=x,xticklabels=names);axes[0,1].legend(fontsize=8)
    axes[1,0].bar(x-.16,[value(q[1],'independent_C_det') for q in shown],width=.32,label='det C')
    axes[1,0].bar(x+.16,[value(q[1],'independent_C_sym_eig_min') for q in shown],width=.32,label='min eig(sym C)')
    axes[1,0].axhline(0,color='k',lw=.8);axes[1,0].set(title='Original positive-C gate retained',xticks=x,xticklabels=names);axes[1,0].legend(fontsize=8)
    ax=axes[1,1];other=ax.twinx();a=ax.bar(x-.16,[value(q[1],'alpha_L1') for q in shown],width=.32,color='C0',label='Sum |alpha|');b=other.bar(x+.16,[value(q[1],'negative_alpha_count') for q in shown],width=.32,color='C1',label='Negative alpha count')
    ax.set(title='Independent anchored extrapolation weights',ylabel='Sum |alpha|',xticks=x,xticklabels=names);other.set_ylabel('Negative coefficients [count]');ax.legend([a,b],['Sum |alpha|','Negative alpha count'],fontsize=8)
    for ci,(_,row) in enumerate(shown):
        if not math.isfinite(value(row,'independent_C_det')):axes[1,0].text(ci,.95,'No finite fit',transform=axes[1,0].get_xaxis_transform(),ha='center',fontsize=8,color='red')
        if not math.isfinite(value(row,'alpha_L1')):axes[1,1].text(ci,.95,'No coefficients',transform=axes[1,1].get_xaxis_transform(),ha='center',fontsize=8,color='red')
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('Single-packet offline counterfactual: not a GPU register value or selected repair',fontsize=13)
    fig.supxlabel('Same actual captured inputs; unchanged .001 / finite / positive-C gates. Unavailable bars remain gaps.\nOriginal solver remains failed; no source, GPU, solver or native-reader changes.',fontsize=9)
    path=Path(str(PREFIX)+'_diagnostic.png');fig.savefig(path,dpi=180);plt.close(fig);return path


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root complete review and one offline execution authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing completed/partial outputs protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(fault.__file__),Path(fault.proxy.__file__))]
    result=dict(stage=TAG,analysis_passed=False,physical_acceptance=False,physical_repair_selected=False,
        original_solver_still_failed=True,actual_GPU_branch_confirmed=False,actual_GPU_M_C_registers=False,
        source_changed=False,solver_invocations=0,native_decodes=0,GPU_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        prior_path=T/'logs/c08_h18_hg_wall_fault_review_r1.check.json';prior=read(prior_path)
        need(prior['analysis_passed'] and prior['analysis_complete'] and prior['consumed_stats_unchanged'],'Existing original independent fault review required')
        refs=[q for q in prior['consumed'] if Path(q['path']).resolve()==Path(fault.__file__).resolve()]
        need(refs and all(q==refs[0] for q in refs) and stat(Path(fault.__file__))==refs[0],'Original reviewed function source changed')
        consumed.append(stat(prior_path))
        run,schema,meta,arrays,fluid,fixed,target,c,audit=fault.inputs(consumed)
        need(schema['stage']==1 and int(arrays['Idp'][target,0])==894 and schema['Nstep_actual_uint64']==2196678
             and meta['TimeStep']==10.983389999668779,'Only the actual reviewed stage1 wall894 packet is exposed')
        original,od,os=fault.recompute(arrays,fluid,target,c)
        need(len(original)==1 and original[0]['complete_geometry_accumulation'] and original[0]['independent_geometry_accepts']
             and original[0]['independent_C_det'] is not None and math.isfinite(original[0]['independent_C_det'])
             and original[0]['independent_C_det']<=0,'This actual packet must be the finite nonpositive-C first-pass case')
        fn,proof=counterfactual();candidate,cd,cs=fn(arrays,fluid,target,c)
        need(1<=len(candidate)<=2,'No third retry or fallback is admitted');same_values(original[0],candidate[0])
        first_donors=[q for q in cd if q['attempt']==0];need(len(od)==len(first_donors),'Original first-pass donor coverage differs')
        for a,b in zip(od,first_donors):same_values(a,b)
        attempt_rows=[dict(method=label,**q) for label,rr in [('Original source',original),('Counterfactual retry',candidate)] for q in rr]
        donor_rows=[dict(method=label,**q) for label,rr in [('Original source',od),('Counterfactual retry',cd)] for q in rr]
        files=[Path(str(PREFIX)+'_attempts.csv'),Path(str(PREFIX)+'_donors.csv')]
        fault.csv_write(files[0],attempt_rows);fault.csv_write(files[1],donor_rows,['method','attempt','no_donors_consumed'])
        files.append(plot(original,candidate,donor_rows,arrays,fluid,target))
        need(all(stat(q['path'])==q for q in consumed),'A bound packet/source changed')
        last=candidate[-1];det=last['independent_C_det'];accepted=bool(last['complete_geometry_accumulation'] and last['independent_geometry_accepts'] and det is not None and math.isfinite(det) and det>0 and last['candidate_reason']=='independent_original_C_gate_accepts')
        result.update(analysis_passed=True,analysis_complete=True,consumed_stats_unchanged=True,derivation=proof,
            original_attempts=len(original),counterfactual_attempts=len(candidate),original_first_pass_bits_equal=True,
            original_first_pass_donor_bits_equal=True,nonfinite_Cdet_retry_allowed=False,invalid_J_or_nonfinite_component_retry_added=False,
            original_geometry_and_positive_C_gates_unchanged=True,third_fallback_added=False,
            counterfactual_final_independent_gate_accepts=accepted,original_recomputation=os,counterfactual_recomputation=cs,
            independent_attempts=attempt_rows,donor_rows=len(donor_rows),visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf-8') as f:json.dump(fault.plain(result),f,ensure_ascii=False,indent=2,allow_nan=False)
    need(result['analysis_passed'],result.get('first_failure','Offline counterfactual incomplete; preserve partials'))


if __name__=='__main__':main()
