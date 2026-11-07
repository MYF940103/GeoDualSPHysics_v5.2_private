"""Normal KeepBedOverlap60 versus retained failed AS1/AS0 saved prefixes; offline only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
import upl_c08_bedkeep_short_review_r1 as short
import upl_c08_asplane_partial_review_r1 as partial
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_bedkeep_window_review_r1';PREFIX=T/'figures'/TAG;CHECK=L/(TAG+'.check.json')
RUN_TAG='upl_c08_bedkeep_window_GPU_r1';NEW=T/'outputs'/RUN_TAG/'native';NC=L/(RUN_TAG+'.native.json')
TRACK=(7010,7011,7014,4808,828);STEPS=(4040000,4120000,4196000,4212000,4216000,4240000)
need,read,stat=partial.need,partial.read,partial.stat;w=partial.w;prior=partial.prior;bind=partial.bind
STYLES={'AS0':('--','.55'),'AS1':('-.','C1'),'KeepBed':('-','C0')}

def csvout(leaf,rows):
    path=Path(str(PREFIX)+'_'+leaf+'.csv');need(rows,'Empty derived table')
    with path.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return path

def load_keep60(before):
    # Literal6805/60/4240000 profile derived from short.load_case; no mutable registry or generic N adaptation.
    n=6805;frames=60;end=4240000;c=read(NC);before.append(stat(NC));need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'] and c['expected_AS'] and c['keep_bed_overlap'] and c['expected_active_native_IDs']==n,'Closed explicit KeepBed6805 native required')
    r=read(Path(bind(c['source_run'])['path']));before.append(c['source_run']);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==end and r['saved_frames']==frames and r['target_backend']=='GPU' and r['ArtificialStress'] and r['consumed_stats_unchanged'] and r['keep_bed_overlap'] and r['expected_active_native_IDs']==n and r['expected_retired_wall_IDs']==255 and r['expected_kept_bed_IDs']==list(short.BED),'Actual normal KeepBed60 runtime required')
    call=read(Path(bind(r['actual_call'])['path']));before.append(r['actual_call']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['actual_solver_Win32_exit']==0 and not call['ownership_errors'],'Actual normal solver exits differ')
    for key in ('program','source_build','source_pre_file','input_xml'):before.append(bind(r[key]))
    b=read(Path(r['source_build']['path']));need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['release_geometry_policy']=='KeepBedOverlapReleaseOnly' and (b['program']['bytes'],b['program']['mtime_ns'])==(r['program']['bytes'],r['program']['mtime_ns']),'Current built program binding differs')
    need(Path(bind(c['completion'])['path']).samefile(NEW/'completion.json'),'Actual completion binding differs');before.append(c['completion']);actual=read(Path(bind(c['actual_call'])['path']));before.append(c['actual_call']);need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual unique reader exit differs')
    for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv'):before.append(bind(next(e for e in c['outputs'] if Path(e['path']).samefile(NEW/leaf))))
    mp=NEW/'bedkeep_metadata.json';need(c['AS_metadata']==c['bedkeep_metadata'] and Path(bind(c['bedkeep_metadata'])['path']).samefile(mp),'Combined typed metadata binding differs');before.append(c['bedkeep_metadata']);m=read(mp);d=read(NEW/'completion.json')
    expected=dict(samples=frames,completed_steps=end,typed_arrays=22,typed_bytes_per_particle=212,original_ID_domain=7060,actual_native_IDs_per_frame=n,soil_IDs=5000,ledger_checks=300000,fixed_marker_checks=108300,P0_bits_checks=408300,rho_cache_bits_checks=300000,kappa_nondecreasing_from_PRE_checks=300000,nonempty_signed_intervals=60,plane_gap_checks=600000)
    need(d['passed'] and all(d[k]==v for k,v in expected.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'],'Original normal native guards differ')
    need(d['geometry_tolerance_m']==w.TOL and d['min_soil_x_m']>=-w.TOL and d['min_soil_z_m']>=-w.TOL,'Original plane geometry guard differs')
    need(d['stage']=='upl_c08_bedkeep_native_r1' and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and not d['actual_retired_IDs_contiguous'] and d['kept_bed_IDs']==list(short.BED) and d['kept_bed_count']==5 and d['actual_fixed_IDs']==1805 and d['kept_bed_source_geometry_checks']==5 and 'retired_ID_count' not in d,'Original noncontiguous release/source-geometry coverage differs')
    need(m['passed'] and m['stage']=='upl_c08_bedkeep_native_r1.metadata' and m['keep_bed_overlap'] and m['original_target_count']==260 and m['actual_retired_count']==255 and m['kept_bed_IDs']==list(short.BED) and m['kept_bed_count']==5 and m['expected_AS'] and m['samples']==m['metadata_header_scans']==m['AS_active_true_headers']==m['keep_policy_headers']==60 and m['completed_steps']==end and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(2.55)) and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_original_numerical_budgets_changed'] and not m['PRE_arrays_reloaded_by_adapter'],'Original keep/AS header coverage differs')
    layout=short.table(NEW/'typed22_layout.csv');need(len(layout)==22,'Exactly22 fields required');fields=[('time','<f8')]
    for row,(name,kind,width) in zip(layout,short.SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,short.TYPES[kind].itemsize*width),'Original22 schema differs');fields.append((name,short.TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);need(dtype.itemsize==8+6805*212,'Explicit6805 record width differs')
    with (NEW/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,60),'Actual6805/22/60 header differs; no rewrite')
    need((NEW/'typed22.bin').stat().st_size==12+60*dtype.itemsize,'Full60 payload length differs');a=np.memmap(NEW/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(60,));clock=short.table(NEW/'clocks.csv');history=short.table(NEW/'history.csv');need(len(clock)==len(history)==60,'Full60 clocks/history required')
    ids=np.r_[np.sort(np.r_[np.arange(1800),short.BED]).astype('uint32'),np.arange(2060,7060,dtype='uint32')]
    for part,x in enumerate(a):need(np.array_equal(x['Idp'][:,0],ids) and float(clock[part]['time_s'])==x['time'] and int(clock[part]['completed_step'])==4000000+(part+1)*4000 and int(clock[part]['completed_step'])==int(clock[part]['saved_step'])+1 and int(clock[part]['native_IDs'])==6805 and clock[part]['dterror_interval_empty']=='0' and np.isfinite(float(clock[part]['signed_dterror_s'])) and float(clock[part]['signed_dterror_s'])<=1e-14,'Original IDs/clocks/signed intervals differ')
    return a,d,clock,history

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline review');need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing partial/complete review protected')
    sets,before,oldAS1,oldAS0=partial.sealed();before.extend(stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(short.__file__),Path(partial.__file__),T/'support/upl_c08_fsmask_r1.py'));sets['KeepBed']=load_keep60(before)
    need(len({b[1]['source_actual_time_s'] for b in sets.values()})==1,'Actual source PRE clocks differ');cohort,preids,pre,materials,itype,ptype=partial.full.layers(before);history=[];tracks=[];bedstates=[]
    for model,bundle in sets.items():
        data,d,clock,hist=bundle;rows=prior.summarize(model,bundle,[]);ids=data[0]['Idp'][:,0];slots={k:np.searchsorted(ids,v) for k,v in cohort.items()};ref={k:pre[np.searchsorted(preids,v),2] for k,v in cohort.items()};folder=NEW if model=='KeepBed' else (partial.NEW if model=='AS1' else partial.OLD);gaps=short.table(folder/'plane_gaps.csv');need(len(gaps)==len(data),'Original plane history incomplete')
        for part,x in enumerate(data):
            for name in cohort:need(np.array_equal(ids[slots[name]],cohort[name]),'Fixed material layer IDs missing');rows[part][name+'_settlement_PRE_VTK_mm']=float(np.mean(ref[name]-x['Posd'][slots[name],2])*1000)
            g=gaps[part];need(float(g['time_s'])==rows[part]['time_s'] and int(g['completed_step'])==rows[part]['completed_step'] and float(g['min_soil_x_m'])==rows[part]['min_x_m'] and float(g['min_soil_z_m'])==rows[part]['min_z_m'] and float(g['geometry_tolerance_m'])==w.TOL,'Original plane observations differ');sk,si=w.total(x)
            for identity in TRACK:
                k=int(np.searchsorted(ids,identity));need(ids[k]==identity,'Tracked original ID missing');vel=x['Vel'][k].astype(float);eff=np.r_[x['SigmaState_kk'][k],x['SigmaState_ij'][k]];tot=np.r_[sk[k],si[k]]
                row=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-d['source_actual_time_s'],completed_step=int(clock[part]['completed_step']),native_ID=identity,role='fixed_wall_ghost' if identity<2060 else 'soil_material',x_m=float(x['Posd'][k,0]),y_m=float(x['Posd'][k,1]),z_m=float(x['Posd'][k,2]),vx_m_s=float(vel[0]),vy_m_s=float(vel[1]),vz_m_s=float(vel[2]),speed_m_s=float(np.linalg.norm(vel)),FSType=int(x['FSType'][k,0]))
                for key,field in (('p_Pa','PorePress'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n_export_marker','PoroPorosity'),('rho_export_marker','PoroMixtureDensity'),('k_export_marker_m_s','PoroHydraulicConductivity')):row[key]=float(x[field][k,0])
                for c,name in enumerate(prior.COMPONENTS):row['sigmaeff_'+name+'_Pa']=float(eff[c]);row['total_sigma_'+name+'_Pa']=float(tot[c])
                tracks.append(row)
            if model=='KeepBed':
                for identity in short.BED:
                    k=int(np.searchsorted(ids,identity));need(ids[k]==identity,'Retained fixed native ID absent');bedstates.append(dict(part=part,time_s=float(x['time']),completed_step=int(clock[part]['completed_step']),native_ID=identity,x_m=float(x['Posd'][k,0]),y_m=float(x['Posd'][k,1]),z_m=float(x['Posd'][k,2]),p_Pa=float(x['PorePress'][k,0]),P0_Pa=float(x['PorePress0'][k,0]),J=float(x['PoroVolumeRatio'][k,0]),source_geometry_verified_by_native=True,post_normal_not_in_typed22=True))
        history.extend(rows)
    bystep={model:{int(q['completed_step']):i for i,q in enumerate(b[2])} for model,b in sets.items()};common=sorted(set.intersection(*(set(v) for v in bystep.values())));need(len(common)==53,'All53 three-way common actual steps required');matched=[]
    for oldmodel in ('AS0','AS1'):
        for step in common:
            i=bystep['KeepBed'][step];j=bystep[oldmodel][step];x=sets['KeepBed'][0][i];y=sets[oldmodel][0][j];sx=x['Idp'][:,0]>=2060;sy=y['Idp'][:,0]>=2060;gap=float(x['time'])-float(y['time']);need(abs(gap)<=1e-14 and np.array_equal(x['Idp'][sx],y['Idp'][sy]) and int(sx.sum())==int(sy.sum())==5000,'Actual shared time/soil IDs differ')
            dp=x['PorePress'][sx].astype(float)-y['PorePress'][sy].astype(float);du=(x['Posd'][sx]-y['Posd'][sy])*1000;xs,xt=w.total(x);ys,yt=w.total(y);ds=xs[sx]-ys[sy];dt=xt[sx]-yt[sy]
            row=dict(comparison='KeepBed-minus-'+oldmodel,completed_step=step,new_part=i,old_part=j,new_time_s=float(x['time']),old_time_s=float(y['time']),actual_time_difference_s=gap,tau_s=float(x['time'])-sets['KeepBed'][1]['source_actual_time_s'],pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZmax_difference_mm=float(np.abs(du).max()),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))))
            for key,field in (('velocity','Vel'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):row[key+'_max_abs_difference']=float(np.abs(x[field][sx].astype(float)-y[field][sy].astype(float)).max())
            matched.append(row)
    files=[csvout('history',history),csvout('material_tracks',tracks),csvout('matched53',matched),csvout('material_layers',materials),csvout('kept_bed_native',bedstates)]
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axs=plt.subplots(5,3,figsize=(16,16),layout='constrained');specs=(('p_RMS_Pa','All-soil pressure RMS [kPa]',.001),('p_min_Pa','All-soil pressure minimum [kPa]',.001),('p_max_Pa','All-soil pressure maximum [kPa]',.001),('mean_downward_settlement_native_PRE_mm','Mean material settlement: double native PRE [mm]',1),('top_settlement_PRE_VTK_mm','Fixed initial top: VTK PRE settlement [mm]',1),('bottom_settlement_PRE_VTK_mm','Fixed initial bottom: VTK PRE settlement [mm]',1),('total_stress_Frobenius_RMS_Pa','All-soil total stress RMS [kPa]',.001),('speed_RMS_m_s','All-soil speed RMS [m/s]',1),('speed_max_m_s','All-soil maximum speed [m/s]',1),('kappa_max','All-soil maximum plastic history',1))
    for ax,(key,title,scale) in zip(axs.flat,specs):
        for model,(style,color) in STYLES.items():
            rr=[r for r in history if r['model']==model];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,c=color,label=model)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for ax,key,title in zip(list(axs.flat)[10:14],('J','n','rho','k'),('J range','Porosity range','Physical density range [kg/m3]','Conductivity range [m/s]')):
        for model,(style,color) in STYLES.items():
            rr=[r for r in history if r['model']==model]
            for suffix in ('min','max'):ax.plot([r['tau_s'] for r in rr],[r[key+'_'+suffix] for r in rr],style,c=color,label=model+' '+suffix)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for model,(style,color) in STYLES.items():
        rr=[r for r in history if r['model']==model];axs[4,2].plot([r['tau_s'] for r in rr],[r['min_z_m']*1000 for r in rr],style,c=color,label=model+' minz')
    axs[4,2].axhline(-w.TOL*1000,c='red',lw=.7,label='Original tolerance');axs[4,2].set(title='Minimum soil z [mm]',xlabel='Actual time since PRE [s]')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Normal KeepBed60 and retained failed AS1/AS0 prefixes53/54; descriptive, not full3s acceptance');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,identity in zip(axs.flat,TRACK):
        for model,(style,color) in STYLES.items():
            rr=[r for r in tracks if r['model']==model and r['native_ID']==identity];ax.plot([r['tau_s'] for r in rr],[r['p_Pa']*.001 for r in rr],style,c=color,label=model)
        ax.set(title=('Reconstructed fixed wall ghost ' if identity==828 else 'Soil material ')+str(identity),xlabel='Actual time since PRE [s]',ylabel='Saved pressure [kPa]');ax.grid(alpha=.25);ax.legend(fontsize=7)
    axs[1,2].set_axis_off();axs[1,2].text(.05,.95,'828 is a fixed reconstructed ghost,\nnot an independently moving soil point.\nIts n/rho/k derived exports are zero markers.\nActual post-release boundary normals\nare not among the22 arrays.\nNo CfgInit normal is used as a post normal.',va='top',transform=axs[1,2].transAxes)
    path=Path(str(PREFIX)+'_tracked_pressure.png');fig.savefig(path);plt.close(fig);files.append(path)
    for field,label,cmap,scale in (('PorePress','Saved soil pressure [kPa]','RdBu_r',.001),('Kplastic','Saved soil plastic history','viridis',1)):
        limits=[(float(b[0][field][:,b[0][0]['Idp'][:,0]>=2060,0].min()),float(b[0][field][:,b[0][0]['Idp'][:,0]>=2060,0].max())) for b in sets.values()];lo=min(q[0] for q in limits)*scale;hi=max(q[1] for q in limits)*scale;fig,axs=plt.subplots(3,len(STEPS),figsize=(21,10),layout='constrained',sharex=True,sharey=True);points=[];mappable=None
        for row,(model,(data,d,clock,hist)) in enumerate(sets.items()):
            for col,step in enumerate(STEPS):
                ax=axs[row,col];part=bystep[model].get(step)
                if part is None:ax.text(.5,.5,'No saved state\nNo interpolation',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
                x=data[part];soil=x['Idp'][:,0]>=2060;pos=x['Posd'][soil];v=x[field][soil,0].astype(float);tau=float(x['time'])-d['source_actual_time_s'];mappable=ax.scatter(pos[:,0],pos[:,2],c=v*scale,s=2,cmap=cmap,vmin=lo,vmax=hi,linewidths=0);ax.set(title=model+' actual tau='+format(tau,'.6f'),xlabel='x [m]',ylabel='z [m]',aspect='equal');ax.axhline(0,c='black',lw=.5);ax.axvline(0,c='black',lw=.5)
                points.extend(dict(model=model,part=part,time_s=float(x['time']),tau_s=tau,completed_step=step,native_ID=int(identity),x_m=float(q[0]),z_m=float(q[2]),**{field:float(value)}) for identity,q,value in zip(x['Idp'][soil,0],pos,v))
        fig.colorbar(mappable,ax=axs.ravel().tolist(),label=label,shrink=.7);fig.suptitle('All5000 soil points; shared complete raw range over all167 saved states, no clipping/fitting/interpolation');path=Path(str(PREFIX)+'_morph_'+field+'.png');fig.savefig(path);plt.close(fig);files.extend((path,csvout('morph_'+field,points)))
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed inputs changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,new_normal_frames=60,retained_AS1_failed_prefix_frames=53,retained_AS0_failed_prefix_frames=54,three_way_actual_common_steps=53,descriptive_pair_rows=len(matched),new_normal_run_and_native_required=True,old_failed_runs_not_relabelled_success=True,all_full_histories_retained=True,unsaved_failure_state_reconstructed=False,original_geometry_tolerance_m=w.TOL,initial_top_material_IDs=cohort['top'].tolist(),initial_bottom_material_IDs=cohort['bottom'].tolist(),initial_VTK_storage=itype,PRE_VTK_storage=ptype,layer_baseline='Fixed initial material IDs and actual PRE VTK coordinates; VTK rounding retained',mean_settlement_baseline='Original native history double PRE',tracked_IDs=list(TRACK),native828_is_fixed_reconstructed_ghost_not_soil=True,kept_bed_source_geometry_checks_from_native=5,post_boundary_normals_not_exported_or_reconstructed_from_CfgInit=True,option_differences_descriptive_not_theory_error=True,no_interpolation_fitting_clipping_or_new_5Pa_gate=True,physical_acceptance=False,reaction_J_Darcy_closed=False,full_3s_admitted=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,visual_QA_pending=True,final_states={model:next(r for r in reversed(history) if r['model']==model) for model in sets},consumed=before,files=[stat(p) for p in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('BEDKEEP_WINDOW_OFFLINE_REVIEW_READY',CHECK,flush=True)

if __name__=='__main__':main()
