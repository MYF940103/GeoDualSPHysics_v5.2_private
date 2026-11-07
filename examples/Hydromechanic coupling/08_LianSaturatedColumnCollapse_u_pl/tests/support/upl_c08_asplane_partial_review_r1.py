"""Offline AS1 partial53 versus AS0 partial54; no solver, decoder or automatic follow-on."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json
from pathlib import Path
import numpy as np
import upl_c08_plane_window_review_r1 as w
import upl_c08_plane_partial_review_r1 as prior
import upl_c08_asplane_window_review_r1 as full
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_asplane_partial_review_r1';PREFIX=T/'figures'/TAG;CHECK=L/(TAG+'.check.json')
NEW=T/'outputs/upl_c08_asplane_partial_r1';OLD=T/'outputs/upl_c08_plane_partial_r1'
NC=L/'upl_c08_asplane_partial_r1.check.json';OC=L/'upl_c08_plane_partial_r1.check.json'
AUDIT=L/'upl_c08_asplane_failure_audit_r1.json';TRACK=(4808,4859,5809,5556,7010,7011);STEPS=(4040000,4120000,4196000,4212000)
need,read,stat=w.need,w.read,w.stat

def bind(entry):
    need(stat(Path(entry['path']))==entry,'Closed file changed: '+entry['path']);return entry

def csvout(name,rows):
    path=Path(str(PREFIX)+'_'+name+'.csv');need(rows,'Empty derived table')
    with path.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return path

def sealed():
    nc,oc=read(NC),read(OC);before=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(w.__file__),Path(prior.__file__),Path(full.__file__),T/'support/upl_c08_as_effect_r1.py',NC,OC,AUDIT)]
    for folder,receipt in ((NEW,nc),(OLD,oc)):
        need(receipt['passed'] and receipt['original_saved_native_guards_passed'] and receipt['consumed_stats_unchanged'] and not receipt['runtime_success_claimed'],'Both partial native checks must be sealed passed; neither solver passed')
        need(Path(bind(receipt['native_completion'])['path']).samefile(folder/'completion.json'),'Actual partial completion binding differs')
        for entry in receipt['consumed']+receipt['files']+[receipt['native_completion'],receipt['reader_call']]:before.append(bind(entry))
        actual=read(Path(receipt['reader_call']['path']));need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual owned partial reader did not exit zero')
    for tag in ('upl_c08_asplane_window_GPU_r1','upl_c08_plane_on_GPU_r1'):
        run,call=L/(tag+'.run.json'),L/(tag+'.call.json');r,c=read(run),read(call);before.extend((stat(run),stat(call)))
        need(not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==1 and c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==1 and not c['ownership_errors'],'Original unique failed solver/typed exits differ')
    audit=read(AUDIT);need(audit['audit_passed'] and not audit['solver_run_passed'] and audit['consumed_stats_unchanged'] and audit['actual_contiguous_PART_files']==53 and audit['failed_stage']==0 and audit['failed_native_id']==828 and audit['reported_step']==4212817,'Original AS1 failure audit differs')
    sets={'AS0':w.load(OLD,54,4216000),'AS1':w.load(NEW,53,4212000)}
    for model,(data,d,clock,hist) in sets.items():
        n=len(data);counts=dict(ledger_checks=5000*n,fixed_marker_checks=1800*n,P0_bits_checks=6800*n,rho_cache_bits_checks=5000*n,kappa_nondecreasing_from_PRE_checks=5000*n,nonempty_signed_intervals=n,plane_gap_checks=10000*n)
        need(all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original native coverage/safety/clock guards differ')
        need(d['diagnostic_partial'] and not d['runtime_success_claimed'] and not d['completed_runtime_Run_csv_checked'] and not d['launch_plan_rewritten'] and d['original_launch_plan_samples']==60 and d['original_launch_plan_end']==4240000 and d['used_launch_plan_prefix_samples']==n and d['saved_steps_checked_against_launch_plan'],'Failed saved prefixes must retain the original60-frame plan')
        need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['geometry_tolerance_m']==w.TOL,'Original fixed-plane policy/tolerance differs')
    need(sets['AS0'][1]['source_actual_time_s']==sets['AS1'][1]['source_actual_time_s'],'Actual certified PRE times differ')
    mpath=NEW/'AS_metadata.json';before.append(bind(nc['AS_metadata']));need(Path(nc['AS_metadata']['path']).samefile(mpath),'AS metadata path differs');m=read(mpath)
    need(m['passed'] and m['stage']=='upl_c08_asplane_partial_r1.AS' and m['NoPenOn_required'] and m['expected_AS'] is True and m['samples']==53 and m['completed_steps']==4212000 and m['AS_active_true_headers']==m['AS_policy_present_headers']==m['metadata_header_scans']==53 and m['AS_policy_when_enabled']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(2.55)) and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_numerical_guards_modified'] and not m['PRE_arrays_reloaded_by_adapter'],'Original AS1 header/adapter coverage differs')
    oldout=T/'outputs/upl_c08_plane_on_GPU_r1/Run.out';before.append(bind(next(e for e in oc['consumed'] if Path(e['path']).samefile(oldout))));need('ArtificialStress="None"' in oldout.read_text(encoding='utf-8-sig'),'AS0 executed policy differs')
    return sets,before,nc,oc

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline analysis');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial products protected')
    sets,before,nc,oc=sealed();cohort,preids,pre,materials,initial_type,pre_type=full.layers(before);history=[];tracks=[];matched=[]
    for model,bundle in sets.items():
        data,d,clock,hist=bundle;rows=prior.summarize(model,bundle,[]);ids=data[0]['Idp'][:,0];slots={k:np.searchsorted(ids,v) for k,v in cohort.items()};ref={k:pre[np.searchsorted(preids,v),2] for k,v in cohort.items()};folder=NEW if model=='AS1' else OLD
        with (folder/'plane_gaps.csv').open(encoding='utf-8',newline='') as f:gaps=list(csv.DictReader(f))
        need(len(gaps)==len(data),'Native plane observations incomplete')
        for part,x in enumerate(data):
            for name in cohort:need(np.array_equal(ids[slots[name]],cohort[name]),'Fixed initial material layer IDs missing');rows[part][name+'_settlement_PRE_VTK_mm']=float(np.mean(ref[name]-x['Posd'][slots[name],2])*1000)
            g=gaps[part];need(float(g['time_s'])==rows[part]['time_s'] and int(g['completed_step'])==rows[part]['completed_step'] and float(g['min_soil_x_m'])==rows[part]['min_x_m'] and float(g['min_soil_z_m'])==rows[part]['min_z_m'] and float(g['geometry_tolerance_m'])==w.TOL,'Original plane data do not match typed positions')
            sk,si=w.total(x)
            for identity in TRACK:
                k=int(np.searchsorted(ids,identity));need(ids[k]==identity,'Tracked material ID missing');vel=x['Vel'][k].astype(float);eff=np.r_[x['SigmaState_kk'][k],x['SigmaState_ij'][k]];tot=np.r_[sk[k],si[k]]
                row=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-d['source_actual_time_s'],completed_step=int(clock[part]['completed_step']),native_ID=identity,x_m=float(x['Posd'][k,0]),y_m=float(x['Posd'][k,1]),z_m=float(x['Posd'][k,2]),vx_m_s=float(vel[0]),vy_m_s=float(vel[1]),vz_m_s=float(vel[2]),speed_m_s=float(np.linalg.norm(vel)),FSType=int(x['FSType'][k,0]))
                for key,field in (('p_Pa','PorePress'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k_m_s','PoroHydraulicConductivity')):row[key]=float(x[field][k,0])
                for c,name in enumerate(prior.COMPONENTS):row['sigmaeff_'+name+'_Pa']=float(eff[c]);row['total_sigma_'+name+'_Pa']=float(tot[c])
                tracks.append(row)
        history.extend(rows)
    new,old=sets['AS1'],sets['AS0'];oldsteps={int(q['completed_step']):i for i,q in enumerate(old[2])};need(len(oldsteps)==54,'Duplicate original AS0 Step')
    for i,x in enumerate(new[0]):
        step=int(new[2][i]['completed_step']);need(step in oldsteps,'Actual shared Step absent; no interpolation');j=oldsteps[step];y=old[0][j];gap=float(x['time'])-float(y['time']);need(abs(gap)<=1e-14 and np.array_equal(x['Idp'],y['Idp']),'Actual matched time/IDs differ')
        soil=x['Idp'][:,0]>=2060;dp=x['PorePress'][soil].astype(float)-y['PorePress'][soil].astype(float);du=(x['Posd'][soil]-y['Posd'][soil])*1000;xs,xt=w.total(x);ys,yt=w.total(y);ds=xs[soil]-ys[soil];dt=xt[soil]-yt[soil];es=x['SigmaState_kk'][soil]-y['SigmaState_kk'][soil];et=x['SigmaState_ij'][soil]-y['SigmaState_ij'][soil]
        row=dict(completed_step=step,AS0_part=j,AS1_part=i,AS0_time_s=float(y['time']),AS1_time_s=float(x['time']),actual_time_difference_s=gap,tau_s=float(x['time'])-new[1]['source_actual_time_s'],pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZmax_difference_mm=float(np.abs(du).max()),effective_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(es*es,axis=1)+2*np.sum(et*et,axis=1)))),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))))
        for key,field in (('velocity','Vel'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):row[key+'_max_abs_difference']=float(np.max(np.abs(x[field][soil].astype(float)-y[field][soil].astype(float))))
        matched.append(row)
    need(len(matched)==53,'All53 actual common states required');files=[csvout('history',history),csvout('material_tracks',tracks),csvout('matched53',matched),csvout('material_layers',materials)]
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axs=plt.subplots(5,3,figsize=(16,16),layout='constrained')
    specs=[('p_RMS_Pa','Absolute pressure RMS [kPa]',.001),('p_min_Pa','Minimum absolute pressure [kPa]',.001),('p_max_Pa','Maximum absolute pressure [kPa]',.001),('top_settlement_PRE_VTK_mm','Fixed initial top settlement [mm]',1),('bottom_settlement_PRE_VTK_mm','Fixed initial bottom settlement [mm]',1),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS [kPa]',.001),('speed_RMS_m_s','Speed RMS [m/s]',1),('speed_max_m_s','Maximum speed [m/s]',1),('kappa_max','Maximum plastic history',1)]
    for ax,(key,title,scale) in zip(axs.flat,specs):
        for model,style,color in (('AS0','--','.45'),('AS1','-','C0')):
            rr=[r for r in history if r['model']==model];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,c=color,label=model)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for ax,key,title in zip(list(axs.flat)[9:13],('J','n','rho','k'),('Native J range','Native porosity range','Physical density range [kg/m3]','Conductivity range [m/s]')):
        for model,style in (('AS0','--'),('AS1','-')):
            rr=[r for r in history if r['model']==model]
            for suffix,color in (('min','C0'),('max','C1')):ax.plot([r['tau_s'] for r in rr],[r[key+'_'+suffix] for r in rr],style,c=color,label=model+' '+suffix)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for model,style in (('AS0','--'),('AS1','-')):
        rr=[r for r in history if r['model']==model];t=[r['tau_s'] for r in rr]
        for key,color in (('min_x_m','C0'),('min_z_m','C1')):axs[4,1].plot(t,[r[key]*1000 for r in rr],style,c=color,label=model+' '+key)
        for key,color in (('x_beyond_original_tol_count','C0'),('z_beyond_original_tol_count','C1')):axs[4,2].plot(t,[r[key] for r in rr],style,c=color,label=model+' '+key)
    axs[4,1].axhline(-w.TOL*1000,c='red',lw=.7,label='Original geometry tolerance');axs[4,1].set(title='Ideal plane minimum gaps [mm]',xlabel='Actual time since PRE [s]');axs[4,2].set(title='Material counts outside original tolerance',xlabel='Actual time since PRE [s]')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Two failed windows: AS1 saved53, AS0 saved54; full histories retained, no physical acceptance');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,identity in zip(axs.flat,TRACK):
        for model,style,color in (('AS0','--','.45'),('AS1','-','C0')):
            rr=[r for r in tracks if r['model']==model and r['native_ID']==identity];ax.plot([r['tau_s'] for r in rr],[r['p_Pa']*.001 for r in rr],style,c=color,label=model)
        ax.set(title='Fixed material '+str(identity),xlabel='Actual time since PRE [s]',ylabel='Native absolute p [kPa]');ax.grid(alpha=.25);ax.legend()
    path=Path(str(PREFIX)+'_material_pressure.png');fig.savefig(path);plt.close(fig);files.append(path)
    for field,label,cmap,scale in (('PorePress','Native absolute p [kPa]','RdBu_r',.001),('Kplastic','Native plastic history','viridis',1)):
        low=min(float(b[0][field][:,1800:,0].min()) for b in sets.values())*scale;high=max(float(b[0][field][:,1800:,0].max()) for b in sets.values())*scale;fig,axs=plt.subplots(2,len(STEPS),figsize=(17,7),layout='constrained',sharex=True,sharey=True);points=[];mappable=None
        for rindex,(model,(data,d,clock,h)) in enumerate(sets.items()):
            for col,step in enumerate(STEPS):
                hits=[i for i,q in enumerate(clock) if int(q['completed_step'])==step];need(len(hits)==1,'Selected actual saved Step absent/duplicated');part=hits[0];x=data[part];soil=x['Idp'][:,0]>=2060;pos=x['Posd'][soil];value=x[field][soil,0].astype(float);tau=float(x['time'])-d['source_actual_time_s'];ax=axs[rindex,col]
                mappable=ax.scatter(pos[:,0],pos[:,2],c=value*scale,s=2,cmap=cmap,vmin=low,vmax=high,linewidths=0);ax.set(title=model+' actual tau='+format(tau,'.6f'),xlabel='x [m]',ylabel='z [m]',aspect='equal');ax.axhline(0,c='black',lw=.5);ax.axvline(0,c='black',lw=.5)
                points.extend(dict(model=model,part=part,time_s=float(x['time']),tau_s=tau,completed_step=step,native_ID=int(identity),x_m=float(q[0]),z_m=float(q[2]),**{field:float(v)}) for identity,q,v in zip(x['Idp'][soil,0],pos,value))
        fig.colorbar(mappable,ax=axs.ravel().tolist(),label=label,shrink=.7);fig.suptitle('All5000 raw particles; complete shared raw range over54+53 states, no clipping/fitting/interpolation');path=Path(str(PREFIX)+'_morph_'+field+'.png');fig.savefig(path);plt.close(fig);files.extend((path,csvout('morph_'+field,points)))
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed inputs changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,AS0_frames=54,AS1_frames=53,actual_common_pairs=53,AS0_runtime_success_claimed=False,AS1_runtime_success_claimed=False,original60_frame_plans_preserved=True,unsaved_failure_state_reconstructed=False,AS1_failure=read(AUDIT)['first_failure_log'],AS0_failure=oc['actual_failure_line'],geometry_tolerance_m=w.TOL,NoPen_policy='FixedPlaneStageProjectionReleaseOnly',AS1_policy='ReleaseOnly',reaction_J_Darcy_closed=False,fixed_initial_top_IDs=cohort['top'].tolist(),fixed_initial_bottom_IDs=cohort['bottom'].tolist(),initial_VTK_storage=initial_type,PRE_VTK_storage=pre_type,layer_baseline='Actual source PartFluid0000 fixed IDs; PartFluid1000 PRE coordinates retain VTK rounding; saved post positions double',whole_soil_settlement_baseline='Original native history double PRE',tracked_material_IDs=list(TRACK),no_interpolation_smoothing_clipping_fitting=True,no_new_5Pa_or_half_or_theory_gate=True,option_difference_is_descriptive=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,final_AS0=next(r for r in reversed(history) if r['model']=='AS0'),final_AS1=next(r for r in reversed(history) if r['model']=='AS1'),consumed=before,files=[stat(p) for p in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('AS_PARTIAL_OFFLINE_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
