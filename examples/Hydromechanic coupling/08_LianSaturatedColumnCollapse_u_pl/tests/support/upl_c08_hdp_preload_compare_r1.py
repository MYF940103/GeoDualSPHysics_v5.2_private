"""Offline comparison of two passed r3 PRE CSV diagnostics; no raw/native read or physical gate."""
import argparse,csv,json,math,os
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_hdp_preload_compare_r1';FIG=T/'figures';L=T/'logs'
SPECS=(('h12','h12_control','upl_c08_hdp12_preload_partial_r3',1.2),('h15','h15_failed','upl_c08_hdp15_preload_partial_r3',1.5))
need,read,stat,bind,save=e.need,e.read,e.stat,e.bind,e.save
def rows(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:r=csv.DictReader(f);data=list(r);return r.fieldnames,data
def number(r,k):return float(r[k])
def col(rs,k):return np.asarray([number(r,k) for r in rs])

def context(spec,before):
    label,profile,stem,hdp=spec;cp=L/(stem+'.check.json');q=read(cp);need(q['passed'] and q['original_saved_native_guards_passed'] and q['consumed_stats_unchanged'] and q['actual_solver_exit'] in (0,1),'Actual r3 saved-state check required: '+stem);dp=Path(bind(q['native_completion'])['path']);d=read(dp);n=d['samples'];need(d['passed'] and d['profile']==profile and d['partial'] and d['uncertified'] and not d['certified_PRE'] and not d['runtime_success_claimed'] and d['typed_arrays']==22 and d['native_IDs']==7060 and d['fixed_IDs']==2060 and d['soil_IDs']==5000 and d['ledger_checks']==d['rho_cache_bits_checks']==5000*n and d['P0_bits_checks']==d['kappa_zero_checks']==7060*n and d['fixed_marker_checks']==2060*n and d['noninitial_signed_intervals']==n-1 and d['max_ledger_relative_error']<=5e-13 and d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14,'Original r3 definite guard/count coverage differs')
    need((profile=='h15_failed' and n==52 and d['completed_steps']==204000) or (profile=='h12_control' and 1<=n<=53 and d['completed_steps']<=208000),'Outside the two explicit source windows');need(not d['saved_FS_pressure_sign_gate_applied'],'SavedFS sign must remain an observation, not a drained gate');entries={Path(v['path']).name:v for v in q['files']};data={};headers={};before.extend((stat(cp),stat(dp),bind(q['original_run']),bind(q['actual_program']),bind(q['actual_source_build']),bind(q['input_xml'])))
    for name in ('clocks.csv','summary.csv','layers.csv','snapshots.csv'):entry=bind(entries[name]);need(Path(entry['path']).parent==dp.parent,'CSV belongs to a different native result');headers[name],data[name]=rows(entry['path']);before.append(entry)
    clocks=data['clocks.csv'];need(len(clocks)==n and [int(v['part']) for v in clocks]==list(range(n)),'Actual CSV clock coverage differs');clock={int(v['part']):v for v in clocks};allrows=[v for v in data['summary.csv'] if v['initial_material_group']=='all'];need(len(allrows)==n and len(data['layers.csv'])==50*n,'All-soil/fifty-layer coverage differs')
    for name in ('summary.csv','layers.csv','snapshots.csv'):
        for r in data[name]:
            p=int(r['part']);need(p in clock and r['time_s']==clock[p]['time_s'] and r['completed_step']==clock[p]['completed_step'],'CSV actual time/Step differs from its native clock');need(all(math.isfinite(float(v)) for k,v in r.items() if k!='initial_material_group'),'Nonfinite derived CSV value')
    for p in range(n):
        a=[v for v in allrows if int(v['part'])==p];z=[v for v in data['layers.csv'] if int(v['part'])==p];need(len(a)==1 and int(a[0]['count'])==5000 and len(z)==50 and all(int(v['count'])==100 for v in z) and len({v['initial_z_m'] for v in z})==50,'Actual layer/material counts differ')
    snaps={}
    for r in data['snapshots.csv']:snaps.setdefault(int(r['part']),[]).append(r)
    for p,rs in snaps.items():need(p in (0,25,50,51) and sorted(int(v['native_id']) for v in rs)==list(range(2060,7060)),'Snapshot soil IDs differ')
    return dict(label=label,hdp=hdp,completion=d,check=stat(cp),program=q['actual_program'],build=q['actual_source_build'],headers=headers,data=data,all=sorted(allrows,key=lambda v:int(v['part'])),clocks=clock,snapshots=snaps)

def write_table(path,fields,records):
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one CSV-only analysis');check=L/(TAG+'.check.json');paths={k:FIG/(TAG+'_'+k+ext) for k,ext in (('history','.png'),('profiles_fields','.png'),('history_data','.csv'),('layers_data','.csv'),('fields_data','.csv'),('material7010_data','.csv'))};need(not check.exists() and not any(p.exists() for p in paths.values()),'Existing derived comparison protected');before=[stat(__file__),stat(T/'notes'/(TAG+'.md'))];result=dict(stage=TAG,passed=False,physical_acceptance=False,new_physical_gate=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,raw_payload_reads=0,SHA_scans=0)
    try:
        sets=[context(s,before) for s in SPECS];left,right=sets;need(left['program']==right['program'] and left['build']==right['build'],'Only same-runtime law2 fresh short controls are compared');need(left['headers']==right['headers'],'Actual r3 CSV schemas differ');common=sorted(set(left['clocks'])&set(right['clocks']));need(common==list(range(min(len(left['all']),len(right['all'])))) and len(common)>1,'No genuine contiguous post-initial common history')
        for p in common:need(left['clocks'][p]['time_s']==right['clocks'][p]['time_s'] and left['clocks'][p]['completed_step']==right['clocks'][p]['completed_step'],'Exact shared actual clock/Step differs; no near-time matching')
        need(all(left['completion'][k]==right['completion'][k] for k in ('phi_float_radians','DP_phi','DP_kc','DP_psi','fresh_trigger_active')),'Actual float material/DP coefficient control differs');shared_snap=sorted(set(left['snapshots'])&set(right['snapshots']));positive=[p for p in shared_snap if p>0];need(positive,'No common exported post-initial snapshot; do not invent one');selected=positive[-3:];shown=[positive[0],positive[-1]] if len(positive)>1 else [0,positive[0]]
        for l,r in zip(sorted(left['snapshots'][0],key=lambda q:int(q['native_id'])),sorted(right['snapshots'][0],key=lambda q:int(q['native_id']))):need(all(l[k]==r[k] for k in ('native_id','x0_m','z0_m','P0_Pa')),'Initial material coordinates/P0 differ between controls')
        for leaf,header in (('history_data','summary.csv'),('layers_data','layers.csv')):
            records=[]
            for s in sets:
                source=s['all'] if header=='summary.csv' else s['data'][header]
                records += [dict(profile=s['label'],hdp=s['hdp'],exact_common_clock=int(int(v['part']) in common),**v) for v in source]
            write_table(paths[leaf],['profile','hdp','exact_common_clock',*sets[0]['headers'][header]],records)
        fig,axes=plt.subplots(3,3,figsize=(16,11),constrained_layout=True);colors=('#1f77b4','#d95f02')
        configs=[('Saved DP f maximum [Pa]',('f_max_Pa',),1.),('Pore pressure [kPa]',('p_mean_Pa','p_RMS_Pa','p_max_Pa'),.001),('Speed [m/s]',('velocity_RMS_m_s','max_speed_m_s'),1.),('J - 1',('min_J','max_J'),1.),('Stress Frobenius RMS [kPa]',('sigma_eff_Frobenius_RMS_Pa','sigma_total_Frobenius_RMS_Pa'),.001),('Saved FS2/3 count',('saved_FS23','saved_FS23_positive','saved_FS23_negative'),1.),('Location of f maximum: x [m]',('f_max_x_m',),1.),('Location of f maximum: z [m]',('f_max_z_m',),1.)]
        for ax,(title,keys,scale) in zip(axes.flat,configs):
            for s,color in zip(sets,colors):
                for k,ls in zip(keys,('-','--',':')):v=col(s['all'],k);ax.plot(col(s['all'],'time_s'),(v-1 if title=='J - 1' else v*scale),ls,color=color,label='h/dp='+str(s['hdp'])+' '+k)
            ax.set_title(title);ax.set_xlabel('Actual source time [s]');ax.grid(alpha=.25);ax.legend(fontsize=6)
        axes[0,0].axhline(0,color='k',lw=.7,ls=':');ax=axes[2,2];material=[]
        for s,color in zip(sets,colors):
            rs=[next(v for v in s['snapshots'][p] if int(v['native_id'])==7010) for p in shared_snap];material += [dict(profile=s['label'],hdp=s['hdp'],**v) for v in rs]
            for key,ls in (('f_Pa','o-'),('p_Pa','s--')):ax.plot(col(rs,'time_s'),col(rs,key)*.001,ls,color=color,label=str(s['hdp'])+' '+key)
        write_table(paths['material7010_data'],['profile','hdp',*sets[0]['headers']['snapshots.csv']],material);ax.set(title='Fixed material ID 7010: saved p and f [kPa]',xlabel='Actual source time [s]');ax.grid(alpha=.25);ax.legend(fontsize=7);fig.suptitle('Fresh same-runtime PRE sensitivity; h1.5 failed after its last saved state. Saved yield/FS observations are not trial or equilibrium acceptance.');fig.savefig(paths['history'],dpi=180);plt.close(fig)
        fig,axes=plt.subplots(2,4,figsize=(18,9),constrained_layout=True)
        for ax,key,title,scale in zip(axes[0],('p_mean_Pa','f_max_Pa','velocity_RMS_m_s','min_J'),('Layer mean p [kPa]','Layer maximum saved f [Pa]','Layer velocity RMS [m/s]','Layer minimum J - 1'),(.001,1.,1.,1.)):
            for s,color in zip(sets,colors):
                for p,ls in zip(selected,(':','--','-')):rs=sorted([v for v in s['data']['layers.csv'] if int(v['part'])==p],key=lambda v:number(v,'initial_z_m'));values=col(rs,key);ax.plot(values-1 if key=='min_J' else values*scale,col(rs,'initial_z_m'),ls,color=color,label=str(s['hdp'])+' t='+format(float(s['clocks'][p]['time_s']),'.7g'))
            ax.set_title(title);ax.set_ylabel('Initial material z [m]');ax.grid(alpha=.25);ax.legend(fontsize=6)
        fields=[(s,p,s['snapshots'][p]) for p in shown for s in sets];values=np.concatenate([col(rs,'f_Pa') for _,_,rs in fields]);norm=Normalize(float(values.min()),float(values.max()));xmin=min(col(rs,'x_m').min() for _,_,rs in fields);xmax=max(col(rs,'x_m').max() for _,_,rs in fields);zmin=min(col(rs,'z_m').min() for _,_,rs in fields);zmax=max(col(rs,'z_m').max() for _,_,rs in fields);records=[]
        for ax,(s,p,rs) in zip(axes[1],fields):
            image=ax.scatter(col(rs,'x_m'),col(rs,'z_m'),c=col(rs,'f_Pa'),s=3,cmap='viridis',norm=norm);peak=max(rs,key=lambda v:number(v,'f_Pa'));ax.scatter(float(peak['x_m']),float(peak['z_m']),marker='*',s=65,facecolors='none',edgecolors='red');ax.set(xlim=(xmin,xmax),ylim=(zmin,zmax),xlabel='x [m]',ylabel='z [m]',title='h/dp='+str(s['hdp'])+' actual t='+format(float(s['clocks'][p]['time_s']),'.9g')+'; fmax ID '+peak['native_id']);ax.set_aspect('equal');records += [dict(profile=s['label'],hdp=s['hdp'],**v) for v in rs]
        fig.colorbar(image,ax=list(axes[1]),label='Saved-state f [Pa]; common full min/max');fig.suptitle('All 50 material layers and raw 5000-soil saved-state f; no smoothing/interpolation. Bands overlap; no unseen failed trial is reconstructed.');fig.savefig(paths['profiles_fields'],dpi=180);plt.close(fig);write_table(paths['fields_data'],['profile','hdp',*sets[0]['headers']['snapshots.csv']],records)
        need(all(stat(q['path'])==q for q in before),'Consumed passed CSV/receipt bindings changed');result.update(passed=True,consumed_stats_unchanged=True,exact_common_frames=len(common),common_last_actual_time_s=float(left['clocks'][common[-1]]['time_s']),source_frames={s['label']:len(s['all']) for s in sets},unmatched_actual_frames={s['label']:len(s['all'])-len(common) for s in sets},selected_profile_parts=selected,plotted_snapshot_parts=shown,actual_program=left['program'],material_coefficients={k:left['completion'][k] for k in ('phi_float_radians','DP_phi','DP_kc','DP_psi')},saved_FS_sign_gate_applied=False,half_or_theory_comparison=False,unsaved_failure_reconstructed=False)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,files=[stat(p) for p in paths.values() if p.exists()]);save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
