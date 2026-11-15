"""Offline three-trajectory91-frame diagnostics; no decoder, API or solver invocation."""
import argparse,math
from itertools import combinations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator
import c08_h18_lstar_window_review_r1 as old
m,core,T,L=old.m,old.core,old.T,old.L
need,read,stat,bind,entry,owned,same,bits=old.need,old.read,old.stat,old.bind,old.entry,old.owned,old.same,old.bits
TAG='c08_h18_paircbare_window_review_r1';SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md');CHECK=L/(TAG+'.check.json');FIG=T/'figures'
RUN=L/'c08_h18_paircbare_window_GPU_r1.run.json';NATIVE=L/'c08_h18_paircbare_window_GPU_r1.native_r1.check.json'
CASES=(*old.CASES,'Private paired-C/bare');PARTS=(30,60,90);DP=.04

def inputs(consumed):
    lstar,original,lb,ob,ref,cohorts=old.inputs(consumed);run,native=read(RUN),read(NATIVE)
    need(run['passed']and run['solver_completed']and run['consumed_stats_unchanged']and run['configuration']=='Release'and run['mode']=='pair_C_bare'and run['actual_steps']==2180000 and run['new_updates']==180000 and run['saved_frames']==91,'Actual complete paired-C/bare window required')
    need(native['passed']and native['consumed_stats_unchanged']and native['reader_invocations']==1 and native['reader_program_completed']and native['native_completed']and entry(native,'source_run')==stat(RUN)and native['reader_build_reused']and not native['typed22_schema_changed'],'Unique actual paired-C/bare native receipt required')
    for q in(run,native):c=entry(q,'actual_call');owned(read(c['path']));consumed.append(c)
    consumed.extend(stat(q)for q in(RUN,NATIVE));consumed.extend(entry(run,k)for k in('program','source_build','source_capture','source_archive','private_physical_source','source_pre_file','source_native','planned_steps','input_xml','native_profile','Run_out','Run_csv'));consumed.extend(entry(native,k)for k in('native_completion','metadata','reader_build'))
    if 'normal_solver_exit_seal'in native:consumed.append(entry(native,'normal_solver_exit_seal'))
    need(all(run[k]==original[k]for k in('source_pre_file','source_native','planned_steps','source_archive')),'All three actual PRE/archive/91plan identities must agree')
    for k in('input_xml','native_profile'):need(Path(run[k]['path']).read_bytes()==Path(original[k]['path']).read_bytes(),'Original input/profile bytes differ: '+k)
    d=read(native['native_completion']['path']);old.coverage(d);root=Path(native['native_completion']['path']).parent;need(same(root.parent,run['output']),'Actual new native/output root differs')
    for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
        e=[q for q in native['files']if Path(q['path']).name==leaf];need(len(e)==1,'One current native export seal required');consumed.append(bind(e[0]))
    pb=core.typed(root,6805,91,consumed);need((root/'typed22_layout.csv').read_bytes()==(ob['root']/'typed22_layout.csv').read_bytes(),'All three actual22 layouts must agree');need(run['actual_source_time_s']==d['source_actual_time_s']==ref['time'],'Actual common source clock differs')
    plan=core.table(run['planned_steps']['path'])
    for i,(p,c)in enumerate(zip(plan,pb['clocks'])):
        a=ob['clocks'][i];need(int(c['part'])==int(a['part'])==int(p['part'])==i and int(c['completed_step'])==int(a['completed_step'])==int(p['completed_step'])and int(c['saved_step'])==int(a['saved_step'])==int(p['saved_step'])and bits(c['time_s'])==bits(a['time_s'])==bits(p['time_s'])and bits(c['dt_s'])==bits(a['dt_s'])==bits(p['dt_s'])==bits(5e-6)and float(c['signed_dterror_s'])<=1e-14 and c['dterror_interval_empty']=='0','Exact actual91-clock three-way join failed')
    return (original,lstar,run),(ob,lb,pb),ref,cohorts

def analyze(bundles,ref):
    history=[];matched=[];spatial=[];snapshots={};last={case:None for case in CASES}
    for part in range(91):
        current={}
        for case,bundle in zip(CASES,bundles):
            frame=core.core.read22(bundle,part);d=old.frame_data(frame,ref,last[case]);history.extend(old.aggregate(case,part,bundle['clocks'][part],d,ref,last[case]));current[case]=d;last[case]=d
            if part in PARTS:
                snapshots[(case,part)]=d
                for i,nid in enumerate(d['ids']):
                    r=dict(case=case,part=part,completed_step=int(bundle['clocks'][part]['completed_step']),actual_time_s=float(bundle['clocks'][part]['time_s']),tau_s=float(bundle['clocks'][part]['time_s'])-ref['time'],native_id=int(nid),x_m=float(d['pos'][i,0]),y_m=float(d['pos'][i,1]),z_m=float(d['pos'][i,2]),p_Pa=float(d['p'][i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),NN_over_dp=float(d['nn'][i]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),n=float(d['n'][i]),V_m2=float(d['V'][i]),rho_kg_m3=float(d['rho'][i]),k_m_s=float(d['k'][i]),speed_m_s=float(d['speed'][i]),effective_stress_Frobenius_Pa=float(d['effnorm'][i]),total_stress_Frobenius_Pa=float(d['totalnorm'][i]),dx_from_PRE_mm=float(1000*d['du'][i,0]),dz_from_PRE_mm=float(1000*d['du'][i,2]),initial_material_layer=int(ref['layer'][i]))
                    for j,axis in enumerate(('xx','yy','zz')):r['effective_'+axis+'_Pa']=float(d['kk'][i,j]);r['total_'+axis+'_Pa']=float(d['total'][i,j])
                    for j,axis in enumerate(('xy','yz','xz')):r['effective_'+axis+'_Pa']=r['total_'+axis+'_Pa']=float(d['ij'][i,j])
                    spatial.append(r)
        for refcase,newcase in combinations(CASES,2):
            a,b=current[refcase],current[newcase];dp=b['p']-a['p'];du=b['pos']-a['pos'];ds=b['total']-a['total'];di=b['ij']-a['ij'];matched.append(dict(reference=refcase,candidate=newcase,part=part,completed_step=int(bundles[0]['clocks'][part]['completed_step']),actual_time_s=float(bundles[0]['clocks'][part]['time_s']),tau_s=float(bundles[0]['clocks'][part]['time_s'])-ref['time'],delta_p_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),delta_p_absmax_Pa=float(np.abs(dp).max()),delta_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),delta_XYZ_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(di*di,axis=1)))),delta_J_absmax=float(np.abs(b['J']-a['J']).max()),delta_kappa_absmax=float(np.abs(b['kappa']-a['kappa']).max())))
    need(len(history)==1638 and len(matched)==273 and len(spatial)==45000,'All273actual states/5000 materials required');return history,matched,spatial,snapshots

def plots(history,snapshots):
    fig,axes=plt.subplots(4,3,figsize=(15,15),layout='constrained');panels=(('p_Pa_RMS','Pressure RMS [Pa]'),('p_Pa_min','Minimum signed pressure [Pa]'),('NN_over_dp_min','Minimum NN / dp'),('unique_pairs_incident_lt_0p5dp','Unique pairs <0.5dp'),('x_front_m','Front x [m]'),('speed_m_s_RMS','Velocity RMS [m/s]'),('storage_proxy_m2','Signed storage proxy [m²]'),('pressure_storage_quadratic_J_per_m','Pressure quadratic [J/m], not total energy'),('J_min','Minimum J'),('effective_stress_Frobenius_Pa_RMS','Effective stress Frobenius RMS [Pa]'),('total_stress_Frobenius_Pa_RMS','Total stress Frobenius RMS [Pa]'),('settlement_from_PRE_mm_mean','Fixed initial top settlement [mm]'))
    for ax,(key,title)in zip(axes.flat,panels):
        for case in CASES:
            rows=[r for r in history if r['case']==case and r['cohort']==('fixed_initial_top'if key=='settlement_from_PRE_mm_mean'else'all')];ax.plot([r['tau_s']for r in rows],[r[key]for r in rows],label=case)
        ax.set_title(title);ax.set_xlabel('Actual time after release [s]');ax.grid(True,alpha=.25);ax.xaxis.set_major_locator(MaxNLocator(nbins=6));ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    axes[0,0].legend(fontsize=8);fig.suptitle('Three bounded actual trajectories: all91 frames and all5000 material IDs each\nStorage/pressure quadratic are proxies; no physical acceptance');out=FIG/(TAG+'_history.png');fig.savefig(out,dpi=165);plt.close(fig);paths=[out]
    for field,cmap,title,unit in(('p','coolwarm','Native signed pressure','Pa'),('nn','viridis','True3D nearest-neighbor spacing','dp')):
        values=np.concatenate([d[field]for d in snapshots.values()]);pos=np.concatenate([d['pos']for d in snapshots.values()]);norm=Normalize(vmin=float(values.min()),vmax=float(values.max()));fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained')
        for row,case in enumerate(CASES):
            for col,part in enumerate(PARTS):
                d=snapshots[(case,part)];ax=axes[row,col];sc=ax.scatter(d['pos'][:,0],d['pos'][:,2],c=d[field],s=3,cmap=cmap,norm=norm,rasterized=True);ax.axhline(0,color='.2',lw=.6);ax.axvline(0,color='.2',lw=.6);ax.set_aspect('equal');ax.set_xlim(min(0,float(pos[:,0].min()))-DP,float(pos[:,0].max())+DP);ax.set_ylim(min(0,float(pos[:,2].min()))-DP,float(pos[:,2].max())+DP);clock=next(r for r in history if r['case']==case and r['part']==part and r['cohort']=='all');ax.set_title(case+'\nP'+str(part)+' actual τ='+format(clock['tau_s'],'.9g')+' s');ax.set_xlabel('x [m]');ax.set_ylabel('z [m]');ax.xaxis.set_major_locator(MaxNLocator(nbins=6));ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        fig.colorbar(sc,ax=axes.ravel().tolist(),label=title+' ['+unit+']',shrink=.85);fig.suptitle(title+': shared scale over all45000 selected actual points; no clipping/smoothing');out=FIG/(TAG+'_'+field+'.png');fig.savefig(out,dpi=165);plt.close(fig);paths.append(out)
    return paths

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Separate root offline authorization required');outputs=[FIG/(TAG+s)for s in('_history.csv','_matched.csv','_spatial.csv','_cohorts.csv','_timing.csv','_history.png','_p.png','_nn.png')];need(not CHECK.exists()and all(not p.exists()for p in outputs),'Existing complete/partial analysis protected');consumed=[stat(q)for q in(SCRIPT,NOTE,Path(old.__file__),Path(old.shared.__file__),Path(core.__file__),Path(core.core.__file__),Path(old.previous.__file__))]
    try:
        runs,bundles,ref,cohorts=inputs(consumed);history,matched,spatial,snapshots=analyze(bundles,ref);timing=[]
        for case,r in zip(CASES,runs):
            s=r['summary'];loop=float(s['TSimul']);need(math.isfinite(loop)and loop>0,'Finite positive observed loop time required');timing.append(dict(case=case,new_updates=180000,TSimul_s=loop,TTotal_s=float(s['TTotal']),Hardware=s['Hardware'],observed_new_updates_per_s=180000/loop,controlled_benchmark=False))
        old.shared.frozen(consumed)
        for path,rows in zip(outputs[:5],(history,matched,spatial,cohorts,timing)):old.write(path,rows)
        pictures=plots(history,snapshots);old.shared.frozen(consumed);m.save(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,actual_states=273,frames_per_case=91,soil_IDs_each=5000,history_rows=1638,matched_pair_rows=273,spatial_rows=45000,source_cohort_rows=5000,cohort_names=old.COHORTS,selected_parts=PARTS,source_reference_initial_and_PRE_only=True,all_frames_in_statistics=True,all_signed_points_retained=True,storage_is_fluid_mass=False,pressure_quadratic_is_total_energy=False,operator_proven_by_native=False,operator_spectrum_proven=False,actual_pressure_flux_budget_proven=False,old_reference_seals_are_original_decoder_exit=False,observed_timing_not_controlled_benchmark=True,new_component_invocations=0,new_API_calls=0,new_native_invocations=0,new_solver_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(q)for q in(*outputs[:5],*pictures)]))
    except Exception as e:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,new_component_invocations=0,new_native_invocations=0,new_solver_invocations=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
