"""Compare only three passed actual-MFG12-row summaries; no component or native call."""
import argparse,csv,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import c08_h18_wend_matrix_r1 as m
T,L=m.T,m.L;TAG='c08_h18_paircbare_summary_r1';SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md')
CHECK=L/(TAG+'.check.json');CSV=T/'figures'/(TAG+'.csv');PNG=T/'figures'/(TAG+'.png')
SPECS=(('Original pair-C/Eta','c08_h18_joint_darcy_probe_r1'),('Receiver-C/bare','c08_h18_lstar_cpu_on_r1'),('Paired-C/bare','c08_h18_paircbare_cpu_r1'))
FIELDS=('H_hydro_affine','N_normal_quadratic','X_cross_cubic');ORACLES=('real_wall','analytic_ghost')
HEADER='part,time_s,tau_s,completed_step,field,oracle,rate_RMS_Pa_s,rate_absmax_Pa_s,legal_bed_count,legal_bed_RMS_Pa_s,legal_bed_absmax_Pa_s,interior_count,interior_RMS_Pa_s,FS_count,active_wall_J_minus1_absmax,dynamic_conductivity_gradient_speed_m_s'.split(',')
def owned(q):m.need(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q.get('ownership_failure')is None,'Actual passed component/build call required')
def load(label,tag,consumed):
    p=L/(tag+'.check.json');q=m.read(p);m.need(q['passed']and q['consumed_stats_unchanged']and q['physical_steps']==0,'Actual passed zero-step check required: '+tag)
    bs=m.bind(q['build']);b=m.read(bs['path']);m.need(b['passed']and b['consumed_stats_unchanged']and b['configuration']=='DebugCPU'and b['actual_link_objects']==87,'Passed current CPU87-object build required')
    cs=m.bind(q['actual_call']);c=m.read(cs['path']);owned(c);program=m.bind(b['program']);m.need(Path(c['program']).resolve()==Path(program['path']).resolve(),'Actual component/program differs');ds=m.bind(q['completion']);d=m.read(ds['path']);m.need(d['passed']and d['manufactured_rows']==60000 and d['summary_rows']==12 and d['actual_rate_float_bit_rows']==30000 and d['physical_steps']==d['material_return_calls']==d['filter_calls']==0,'Existing actual-MFG coverage required')
    candidates=[e for e in q['files']if Path(e['path']).name=='summary.csv'];m.need(len(candidates)==1,'One sealed summary required');summary=m.bind(candidates[0]);rows=m.table(summary['path']);m.need(len(rows)==12 and all(list(r)==HEADER for r in rows),'Exact12-row summary schema required')
    consumed.extend([m.stat(p),bs,cs,program,ds,summary,m.bind(b['source_archive'])])
    for e in b['calls']:e=m.bind(e);owned(m.read(e['path']));consumed.append(e)
    result={}
    for r in rows:
        key=(int(r['part']),r['field'],r['oracle']);m.need(key not in result and key[0]in(29,30)and key[1]in FIELDS and key[2]in ORACLES,'Closed unique summary key required');z={k:(r[k]if k in('field','oracle')else None if r[k]==''else int(r[k])if k in('part','completed_step','legal_bed_count','interior_count','FS_count')else float(r[k]))for k in HEADER};m.need(all(math.isfinite(v)for v in z.values()if isinstance(v,float)),'Nonfinite summary value');m.need(z['rate_RMS_Pa_s']>=0 and z['rate_absmax_Pa_s']>=0,'RMS/magnitude sign invalid')
        for prefix in('legal_bed','interior'):
            n=z[prefix+'_count'];value=z[prefix+'_RMS_Pa_s'];m.need(n is not None and n>=0 and n==int(n)and((n==0 and value is None)or(n>0 and value is not None and value>=0)),'Empty/positive cohort summary differs')
        result[key]=dict(case=label,**z)
    m.need(set(result)=={(part,f,o)for part in(29,30)for f in FIELDS for o in ORACLES},'All12actual groups required');return result,b['source_archive']
def plot(rows):
    fig,axs=plt.subplots(2,3,figsize=(14,7.8),sharey=True);fig.subplots_adjust(top=.82,bottom=.13,left=.08,right=.99,wspace=.13,hspace=.35);colors=('#555555','#2878B5','#D95F02');keys=('legal_bed_RMS_Pa_s','interior_RMS_Pa_s','rate_RMS_Pa_s');positive=[r[k]for r in rows for k in keys if r['oracle']=='real_wall'and r[k]is not None and r[k]>0];m.need(positive,'No positive real-wall RMS to plot on log axis');handles=[]
    for row,part in enumerate((29,30)):
        for col,field in enumerate(FIELDS):
            ax=axs[row,col];ax.set_yscale('log');ax.set_ylim(min(positive)*.6,max(positive)*1.7)
            for j,(label,_)in enumerate(SPECS):
                r=next(z for z in rows if(z['case'],int(z['part']),z['field'],z['oracle'])==(label,part,field,'real_wall'));x=np.arange(3)+(j-1)*.23;values=[r[k]for k in keys];bars=ax.bar(x,[v if v is not None and v>0 else np.nan for v in values],width=.22,color=colors[j],label=label)
                if row==col==0:handles.append(bars)
                for xx,v in zip(x,values):
                    if v is None or v==0:ax.text(xx,.02,'N/A'if v is None else'0',transform=ax.get_xaxis_transform(),rotation=90,ha='center',va='bottom',fontsize=7)
            ax.set_xticks(range(3),('Legal flat bed','Interior','All5000'));ax.set_title('P'+str(part)+' / '+field);ax.grid(True,axis='y',alpha=.25)
            if col==0:ax.set_ylabel('Zero-drive residual RMS [Pa/s]')
    fig.legend(handles,[x[0]for x in SPECS],loc='upper center',bbox_to_anchor=(.5,.925),ncol=3,frameon=False);fig.suptitle('Actual CPU manufactured joint-Darcy residuals: three spatial weights\nReal-wall API values only in figure; analytic-ghost expressions retained in CSV',y=.985);fig.text(.5,.025,'No time integration or physical acceptance. Continuous joint drive is zero; global side/FS fields need not define a legal IBVP.',ha='center',fontsize=9);fig.savefig(PNG,dpi=170);plt.close(fig)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');m.need(p.parse_args().execution_authorized,'Independent root offline-review authorization required');m.need(not CHECK.exists()and not CSV.exists()and not PNG.exists(),'Existing analysis/partial protected');consumed=[m.stat(q)for q in(SCRIPT,NOTE,Path(m.__file__))]
    try:
        tables=[];archives=[]
        for label,tag in SPECS:a,b=load(label,tag,consumed);tables.append(a);archives.append(b)
        m.need(all(a==archives[0]for a in archives),'Common current source archive required');rows=[]
        for part in(29,30):
            for field in FIELDS:
                for oracle in ORACLES:
                    group=[a[(part,field,oracle)]for a in tables];ref=group[0]
                    for r in group:m.need(all(r[k]==ref[k]for k in('time_s','tau_s','completed_step','legal_bed_count','interior_count','FS_count')),'Actual same-state/time/cohort-count summary join differs');rows.extend([r])
        m.need(len(rows)==36,'Exactly36source summary rows required');m.verify(consumed)
        with CSV.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
        plot(rows);m.verify(consumed);m.save(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,source_summary_rows=36,groups_per_scheme=12,actual_real_wall_groups=18,analytic_expression_groups=18,plotted_oracle='real_wall',all_three_cohorts_retained=True,all_rows_aligned_by_actual_time=True,empty_cohorts_not_zeroed=True,zero_log_values_not_floored=True,actual_manufactured_full_CSV_scans=0,common_bit_checks_repeated=0,new_component_invocations=0,new_native_invocations=0,new_solver_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[m.stat(CSV),m.stat(PNG)]))
    except Exception as e:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,new_component_invocations=0,new_native_invocations=0,new_solver_invocations=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
