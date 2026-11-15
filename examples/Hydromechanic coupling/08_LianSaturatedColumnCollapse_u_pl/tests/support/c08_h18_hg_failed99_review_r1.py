"""Offline saved99 HG-failure review versus HG0 first99; never decode or solve."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_lstar_window_review_r1 as old

T, L, core = old.T, old.L, old.core
need, read, stat, bind = old.need, old.read, old.stat, old.bind
TAG = 'c08_h18_hg_failed99_review_r1'
NOTE, CHECK = T/'notes'/(TAG+'.md'), L/(TAG+'.check.json')
PREFIX = T/'figures'/TAG
CASES, SELECTED = ('HG0 retained', 'HG failed: saved prefix'), (89,93,98)
RUN = L/'c08_h18_hg_opt_full3_GPU_r1.run.json'
NATIVE = L/'c08_h18_hg_opt_full3_GPU_r1.native_failed99_r1.check.json'
BASE_RUN = L/'c08_h18_as03n255_full3_r1.run.json'
BASE_NATIVE = L/'c08_h18_as03n255_full3_native_r1.check.json'


def sealed(receipt, path, consumed, key='consumed'):
    refs=[q for q in receipt[key] if Path(q['path']).resolve()==path.resolve()]
    need(refs and all(q==refs[0] for q in refs),'Missing/ambiguous frozen native export: '+str(path))
    bind(refs[0]); consumed.append(refs[0])


def inputs(consumed):
    failed, fn, baseline, bn = map(read,(RUN,NATIVE,BASE_RUN,BASE_NATIVE))
    need(not failed['passed'] and not failed['solver_completed'] and failed['actual_exit']==failed['actual_Win32_exit']==1,
         'Original solver must remain a failed run')
    need(fn['diagnostic_passed'] and not fn['whole_run_passed'] and fn['reader_invocations']==1
         and fn['original_failed_run']==stat(RUN), 'One genuine partial99 native receipt required')
    need(baseline['passed'] and baseline['solver_completed'] and baseline['actual_steps']==2600000
         and baseline['saved_frames']==301 and bn['passed'] and bn['reader_invocations']==1,
         'Retained complete HG0 full301 control required')
    need(failed['source_pre_file']==baseline['source_pre_file'] and failed['source_native']==baseline['source_native'],
         'Same actual material PRE required')
    for check in (fn,bn):
        bind(check['actual_call']); old.owned(read(check['actual_call']['path'])); bind(check['native_completion'])
    nd, bd = read(fn['native_completion']['path']), read(bn['native_completion']['path'])
    need(not nd['passed'] and nd['partial'] and nd['diagnostic_complete'] and nd['saved_prefix_native_passed']
         and not nd['whole_run_native_passed'] and not nd['full_run_completed']
         and nd['samples']==99 and nd['last_saved_part']==98 and nd['completed_steps']==2196001
         and nd['original_plan_records']==301 and nd['original_target_completed_step']==2600000,
         'Partial saved-prefix flags/extent differ')
    need(bd['passed'] and bd['samples']==301 and bd['completed_steps']==2600000, 'Original full control extent differs')
    for d in (nd,bd):
        need(d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000
             and d['actual_fixed_IDs']==1805 and d['max_scalar_clock_error_s']<=1e-14
             and d['max_signed_dterror_s']<=1e-14 and not d['native_rewritten'], 'Original native guards differ')
    original_review_path=L/'c08_h18_as03n255_full3_review_r1.check.json'; original_review=read(original_review_path)
    need(original_review['analysis_complete'] and original_review['consumed_stats_unchanged'], 'Retained control export seal required')
    nr,br=Path(fn['native_completion']['path']).parent,Path(bn['native_completion']['path']).parent
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
        sealed(fn,nr/leaf,consumed,'files'); sealed(original_review,br/leaf,consumed)
    bundles=(core.typed(br,6805,301,consumed),core.typed(nr,6805,99,consumed))
    need((nr/'typed22_layout.csv').read_bytes()==(br/'typed22_layout.csv').read_bytes(),'Original22 layouts differ')
    plan=core.table(failed['planned_steps']['path'])
    need(len(plan)==301 and int(plan[-1]['completed_step'])==2600000,'Untouched full301 launch plan required')
    for i in range(99):
        a,b,p=bundles[0]['clocks'][i],bundles[1]['clocks'][i],plan[i]
        need(int(a['part'])==int(b['part'])==int(p['part'])==i
             and int(a['completed_step'])==int(b['completed_step'])==int(p['completed_step'])==2000001+2000*i
             and int(a['saved_step'])==int(b['saved_step'])==int(p['saved_step'])==2000000+2000*i
             and old.bits(a['time_s'])==old.bits(b['time_s'])==old.bits(p['time_s'])
             and old.bits(a['dt_s'])==old.bits(b['dt_s'])==old.bits(p['dt_s'])==old.bits(.000005)
             and a['dterror_interval_empty']==b['dterror_interval_empty']=='0', 'Actual99 join/clock/signed-interval extent differs')
    source=read(failed['source_native']['path']); need(source['passed'] and source['certified_PRE'] and source['samples']==1001,'Original complete PRE reference required')
    sr=Path(failed['source_native']['path']).parent
    physical_path=L/'c08_h18_hg_cached_physical_r1.check.json'; physical=read(physical_path)
    need(physical['passed'] and physical['consumed_stats_unchanged'],'Existing PRE first/final export seal required')
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):sealed(physical,sr/leaf,consumed)
    ref,_=old.previous.source_reference(core.typed(sr,7060,1001,consumed),source)
    need(ref['time']==nd['source_actual_time_s']==bd['source_actual_time_s'],'Actual PRE release time differs')
    consumed += [stat(q) for q in (RUN,NATIVE,BASE_RUN,BASE_NATIVE,original_review_path,physical_path)]
    consumed += [fn['native_completion'],bn['native_completion'],bind(failed['source_native']),bind(failed['planned_steps'])]
    return bundles,ref


def analyze(bundles,ref):
    history,matched,spatial,snapshots=[],[],[],{}
    last={q:None for q in CASES}
    for part in range(99):
        current={}
        for case,bundle in zip(CASES,bundles):
            f=core.core.read22(bundle,part); d=old.frame_data(f,ref,last[case])
            history += old.aggregate(case,part,bundle['clocks'][part],d,ref,last[case])
            current[case]=d; last[case]=d
            if part in SELECTED:
                fixed=np.array(f['Posd'][f['Idp'][:,0]<2060]); wall=np.array(f['Posd'][f['Idp'][:,0]==894])
                need(fixed.shape==(1805,3) and wall.shape==(1,3),'Original fixed/894 ID coverage required')
                snapshots[(case,part)]=(d,fixed,wall[0])
                for i,nid in enumerate(d['ids']):
                    row=dict(case=case,part=part,actual_time_s=float(bundle['clocks'][part]['time_s']),tau_s=float(bundle['clocks'][part]['time_s'])-ref['time'],native_id=int(nid),x_m=float(d['pos'][i,0]),y_m=float(d['pos'][i,1]),z_m=float(d['pos'][i,2]),p_Pa=float(d['p'][i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),NN_over_dp=float(d['nn'][i]),nearest_material_id=int(d['ids'][d['neighbor'][i]]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),n=float(d['n'][i]),rho_kg_m3=float(d['rho'][i]),k_m_s=float(d['k'][i]),speed_m_s=float(d['speed'][i]),dx_from_PRE_mm=float(1000*d['du'][i,0]),dz_from_PRE_mm=float(1000*d['du'][i,2]),initial_material_layer=int(ref['layer'][i]))
                    for j,axis in enumerate(('xx','yy','zz')):row['effective_'+axis+'_Pa']=float(d['kk'][i,j]);row['total_'+axis+'_Pa']=float(d['total'][i,j])
                    for j,axis in enumerate(('xy','yz','xz')):row['effective_'+axis+'_Pa']=row['total_'+axis+'_Pa']=float(d['ij'][i,j])
                    spatial.append(row)
        a,b=[current[q] for q in CASES];dp=b['p']-a['p'];du=b['pos']-a['pos'];ds=b['total']-a['total'];di=b['ij']-a['ij']
        row=dict(part=part,actual_time_s=float(bundles[1]['clocks'][part]['time_s']),tau_s=float(bundles[1]['clocks'][part]['time_s'])-ref['time'],delta_p_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),delta_p_absmax_Pa=float(np.abs(dp).max()),delta_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),delta_XYZ_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(di*di,axis=1)))))
        for label,d in zip(('HG0','HG'),(a,b)):
            mask=(abs(d['pos'][:,0]-4.9)<=4*old.H)&(d['pos'][:,2]>=-old.DP)&(d['pos'][:,2]<=4*old.H)
            row[label+'_wall894_box_nodes']=int(mask.sum())
            for key,values in (('p_min_Pa',d['p']),('NN_min_over_dp',d['nn']),('J_min',d['J'])):row[label+'_wall894_box_'+key]=float(values[mask].min()) if mask.any() else None
            row[label+'_wall894_box_kappa_max']=float(d['kappa'][mask].max()) if mask.any() else None
        matched.append(row)
    need(len(history)==1188 and len(matched)==99 and len(spatial)==30000,'All99/5000/6cohort observations required')
    return history,matched,spatial,snapshots


def plots(history,snapshots):
    fig,axes=plt.subplots(4,3,figsize=(15,13),layout='constrained')
    charts=(('p_Pa_RMS','Pressure RMS [kPa]',.001,'all'),('p_Pa_min','Minimum pressure [kPa]',.001,'all'),('p_Pa_max','Maximum pressure [kPa]',.001,'all'),('settlement_from_PRE_mm_mean','Initial top material settlement [mm]',1,'fixed_initial_top'),('settlement_from_PRE_mm_mean','Initial bottom material settlement [mm]',1,'fixed_initial_bottom'),('material_displacement_RMS_mm','Material displacement RMS [mm]',1,'all'),('speed_m_s_RMS','Speed RMS [m/s]',1,'all'),('total_stress_Frobenius_Pa_RMS','Total stress RMS [kPa]',.001,'all'),('kappa_max','Maximum kappa',1,'all'),('J_min','Minimum J',1,'all'),('NN_over_dp_min','Minimum soil NN / dp',1,'all'),('x_front_m','Particle-center front [m]',1,'all'))
    for ax,(key,title,scale,cohort) in zip(axes.flat,charts):
        for case in CASES:
            rows=[q for q in history if q['case']==case and q['cohort']==cohort];ax.plot([q['tau_s'] for q in rows],[q[key]*scale for q in rows],label=case)
        ax.set(title=title,xlabel='Actual time after release [s]');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('C08 saved prefix only: HG solver FAILED before 3 s; actual matched99 states',fontsize=13)
    path=Path(str(PREFIX)+'_history.png');fig.savefig(path,dpi=160);plt.close(fig);files=[path]
    for field,title,suffix,zoom in (('p','Raw total pressure [kPa]','p',False),('nn','Saved soil spacing near wall894 [dp]','wall894',True)):
        values=np.concatenate([d[field] for d,_,_ in snapshots.values()]);scale=.001 if field=='p' else 1.;norm=Normalize(float(values.min())*scale,float(values.max())*scale)
        allpos=np.concatenate([d['pos'] for d,_,_ in snapshots.values()]);fig,axes=plt.subplots(2,3,figsize=(16,8),layout='constrained')
        for ri,case in enumerate(CASES):
            for ci,part in enumerate(SELECTED):
                d,fixed,wall=snapshots[(case,part)];ax=axes[ri,ci];ax.scatter(fixed[:,0],fixed[:,2],s=2,c='.4',rasterized=True)
                image=ax.scatter(d['pos'][:,0],d['pos'][:,2],c=d[field]*scale,cmap='coolwarm' if field=='p' else 'viridis',norm=norm,s=5 if zoom else 3,rasterized=True)
                ax.scatter([wall[0]],[wall[2]],marker='*',s=70,c='red',edgecolors='black',linewidths=.5,label='Saved fixed ID894')
                clock=next(q for q in history if q['case']==case and q['part']==part and q['cohort']=='all')
                ax.set(title=case+f'; P{part}, tau={clock["tau_s"]:.9f}s',xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal');ax.grid(alpha=.15)
                ax.set_xlim((4.9-4*old.H,4.9+4*old.H) if zoom else (min(0.,float(allpos[:,0].min()))-.04,float(allpos[:,0].max())+.04))
                ax.set_ylim((-old.DP,4*old.H) if zoom else (min(0.,float(allpos[:,2].min()))-.04,float(allpos[:,2].max())+.04))
        fig.colorbar(image,ax=list(axes.flat),label=title,shrink=.85);fig.suptitle(title+'; full raw shared range, no smoothing or interpolation',fontsize=13)
        fig.supxlabel('Only real saved states; the later reported stage1 rejection has no reconstructed native arrays.',fontsize=9)
        path=Path(str(PREFIX)+'_'+suffix+'.png');fig.savefig(path,dpi=170);plt.close(fig);files.append(path)
    return files


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args();need(args.execution_authorized,'Root offline authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing complete/partial analysis protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(old.__file__),Path(core.__file__),Path(core.core.__file__),Path(old.previous.__file__))]
    result=dict(stage=TAG,passed=False,analysis_complete=False,candidate_solver_failed=True,full_run_completed=False,whole_run_passed=False,physical_acceptance=False,new_solver_invocations=0,new_native_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        bundles,ref=inputs(consumed);history,matched,spatial,snapshots=analyze(bundles,ref)
        files=[Path(str(PREFIX)+s) for s in ('_history.csv','_matched.csv','_spatial.csv')]
        for path,rows in zip(files,(history,matched,spatial)):old.write(path,rows)
        files+=plots(history,snapshots);need(all(stat(q['path'])==q for q in consumed),'Immutable input changed')
        last=[q for q in history if q['part']==98 and q['cohort']=='all']
        result.update(passed=True,analysis_complete=True,consumed_stats_unchanged=True,actual_candidate_frames=99,retained_control_frames_read=99,retained_control_original_frames=301,soil_IDs_per_frame=5000,typed_arrays=22,history_rows=len(history),matched_rows=99,spatial_rows=30000,selected_parts=SELECTED,actual_saved_end_s=last[-1]['actual_time_s'],last_saved_summary=last,source_reference_initial_and_PRE_only=True,no_interpolation=True,operator_difference_is_half_error=False,failed_Run_csv_absent=True,failed_TSimul_or_speedup_claimed=False,unsaved_state_reconstructed=False,HG_correctness_proven=False,paper_accuracy_accepted=False,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed;CHECK.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');need(result['passed'],result.get('first_failure','Offline failure; preserve partial outputs'))


if __name__=='__main__':main()
