"""Failed n4 genuine66 saves versus n3 r6 first66; original90-plan failure, not a half/theory test."""
import argparse,json,struct
from pathlib import Path
import upl_c08_n3_full_compare_r1 as full
cluster=full.cluster
np,c,plt=cluster.np,cluster.c,cluster.plt
T=c.T;TAG='upl_c08_asn4_partial_compare_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');JOB='upl_c08_asn4_window_GPU_r1';STAGE='upl_c08_asn4_partial_r1'
FOCUS=(5944,5945,7017,6814);SNAPS=((.5,49),(.58,57),(.66,65))

def load_n4(old):
    rp=T/'logs'/(JOB+'.run.json');npth=T/'logs'/(JOB+'.native_partial_r1.json');r,n=c.read(rp),c.read(npth)
    c.need(not r['passed'] and not r['solver_completed'] and r['failed_stage']=='solver' and r['actual_exit']==r['actual_Win32_exit']==1 and r['consumed_stats_unchanged'] and r['ArtificialStress'] and r['ArtificialStressCoef']==.2 and r['ArtificialStressExp']==4. and r['keep_bed_overlap'] and r['expected_active_native_IDs']==6805,'Genuine failed epsilon.2/n4 solver required; not a normal90 completion')
    c.need(n['passed'] and n['partial'] and not n['runtime_success_claimed'] and not n['source_run_passed'] and n['source_solver_exit']==1 and n['original_saved_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1 and not n['failure_unsaved_state_reconstructed'] and n['failure_reported_step']==4265004 and n['first_engine_exception_text']==r['first_engine_exception_text'] and Path(c.bind(n['source_run'])['path']).samefile(rp),'Sealed unique n4 partial/native/source-run failure check required')
    native=Path(c.bind(n['completion'])['path']).parent;c.need(native.samefile(T/'outputs'/JOB/'native_partial_r1'),'Actual n4 native directory differs');d=c.read(native/'completion.json');m=c.read(c.bind(n['metadata'])['path']);call=c.read(c.bind(n['actual_call'])['path'])
    counts=dict(samples=66,completed_steps=4264000,new_updates=264000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
    c.need(d['passed'] and d['stage']==STAGE and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and not d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'] and d['partial'] and not d['runtime_success_claimed'] and d['completed_steps_are_last_saved'] and d['new_updates_are_to_last_saved'] and d['original_planned_samples']==90 and d['original_planned_end']==4360000 and d['used_launch_plan_prefix_samples']==66 and d['last_saved_step']==4263999 and not d['failure_unsaved_state_reconstructed'],'Original n4 numeric/clock coverage differs')
    c.need(d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and d['kept_bed_IDs']==[1800,1852,1904,1956,2008] and d['actual_retired_count']==255,'Original fixed-plane/keep5 scope differs')
    c.need(m['passed'] and m['stage']==STAGE+'.metadata' and m['partial'] and not m['runtime_success_claimed'] and m['profile']=='failed_window_partial' and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==m['ponding_policy_keys_absent_headers']==66 and m['original_planned_samples']==90 and m['original_planned_end']==4360000 and m['used_launch_plan_prefix_samples']==66 and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==4. and m['expected_ponding_policy']=='CompletedOnly','Actual n4 AS/CompletedOnly headers differ')
    c.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and Path(call['arguments'][-1]).samefile(native),'Actual n4 reader exit/output differs')
    before=[c.stat(rp),c.stat(npth),c.bind(n['source_run']),c.bind(n['completion']),c.bind(n['metadata']),c.bind(n['actual_call']),c.bind(n['original_solver_call']),c.bind(n['original_owner_admission'])]+[c.bind(r[k]) for k in ('program','source_build','source_pre_file','input_xml')]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):before.append(c.bind(next(q for q in n['outputs'] if Path(q['path']).samefile(native/leaf))))
    layout=c.table(native/'typed22_layout.csv');clocks=c.table(native/'clocks.csv');history=c.table(native/'history.csv');c.need(layout==old['layout'] and len(clocks)==len(history)==66 and (native/'typed22.bin').stat().st_size==12+66*old['dtype'].itemsize,'Original66 partial schema/payload/history extent differs')
    xml=c.ET.parse(r['input_xml']['path']).getroot();params={q.get('key'):q for q in xml.findall('execution/parameters/parameter')};expected=c.ET.parse(old['run']['input_xml']['path']).getroot();ep={q.get('key'):q for q in expected.findall('execution/parameters/parameter')}
    c.need(float(params['TimeMax'].get('value'))==10.9 and float(params['TimeOut'].get('value'))==.01 and float(params['ArtificialStressExp'].get('value'))==4.,'Actual n4 clock/exponent input differs');params['TimeMax'].set('value',ep['TimeMax'].get('value'));params['ArtificialStressExp'].set('value','2.55')
    c.need(tuple(c.physics(xml.find('execution/'+k)) for k in ('special','parameters'))==old['physics'] and r['program']==old['run']['program'] and r['source_build']==old['run']['source_build'] and r['source_pre_file']==old['run']['source_pre_file'] and d['source_actual_time_s']==old['done']['source_actual_time_s'],'Only declared exponent/window duration may differ; actual program/PRE must match')
    return dict(label='n4',epsilon=.2,exponent=4.,run=r,done=d,native=native,dtype=old['dtype'],layout=layout,clocks=clocks,history=history,before=before)

def point(frame,ctx,part,time,tau,step,identity,first,m):
    i=int(np.searchsorted(frame['Idp'][:,0],identity));c.need(int(frame['Idp'][i,0])==identity,'Fixed material focus ID missing');x=frame['Posd'][i];v=frame['Vel'][i].astype(float);key=(ctx['label'],identity)
    if part==0:first[key]=x.copy()
    du=1000*(x-first[key]);p=float(frame['PorePress'][i,0]);kk=frame['SigmaState_kk'][i];soilindex=identity-2060
    return dict(group=ctx['label'],AS_exponent=ctx['exponent'],part=part,time_s=time,tau_s=tau,completed_step=step,native_id=identity,x_m=float(x[0]),z_m=float(x[2]),dx_since_first_tau0p01_save_mm=float(du[0]),dz_since_first_tau0p01_save_mm=float(du[2]),vx_m_s=float(v[0]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)),p_Pa=p,kappa=float(frame['Kplastic'][i,0]),J=float(frame['PoroVolumeRatio'][i,0]),n=float(frame['PoroPorosity'][i,0]),k_m_s=float(frame['PoroHydraulicConductivity'][i,0]),total_xx_Pa=float(kk[0]-p),total_zz_Pa=float(kk[2]-p),theta_last_stage_s=float(frame['PoroThetaLastStage'][i,0]),FSType=int(frame['FSType'][i,0]),nearest_soil_id=int(m['ids'][m['near'][soilindex]]),rNN_over_dp=float(m['nn'][soilindex]))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read after actual saved-state native pass required; solver remains failed');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial comparison protected')
    old=full.load(full.SPECS[1]);new=load_n4(old);contexts=(old,new);before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(full.__file__),Path(cluster.__file__),Path(c.__file__))]+old['before']+new['before'];body=[];cohorts=[];points=[];pairs=[];pictures={};first={};files=[];snap_parts={p for _,p in SNAPS}
    with (old['native']/'typed22.bin').open('rb') as fa,(new['native']/'typed22.bin').open('rb') as fb:
        c.need(struct.unpack('<III',fa.read(12))==(6805,22,300) and struct.unpack('<III',fb.read(12))==(6805,22,66),'Original300/66 headers required; never rewritten')
        for part in range(66):
            frames=[];times=[]
            for ctx,stream in zip(contexts,(fa,fb)):
                raw=stream.read(ctx['dtype'].itemsize);c.need(len(raw)==ctx['dtype'].itemsize,'Incomplete genuine native record');frame=np.frombuffer(raw,dtype=ctx['dtype'],count=1)[0];time,tau,step=c.inspect(frame,ctx,part);frames.append(frame);times.append((time,tau,step));m=cluster.measures(frame);q=c.quantities(frame,ctx,part,tau,step);q.update(AS_exponent=ctx['exponent'],mean_kappa=float(m['kappa'].mean()),min_kappa=float(m['kappa'].min()),mean_J=float(m['J'].mean()),mean_n=float(m['n'].mean()),mean_conductivity_m_s=float(frame['PoroHydraulicConductivity'][frame['Idp'][:,0]>=2060,0].mean()));body.append(q);cohorts.extend(cluster.summarize(m,dict(group=ctx['label'],AS_exponent=ctx['exponent'],part=part,time_s=time,tau_s=tau,completed_step=step)))
                for identity in FOCUS:points.append(point(frame,ctx,part,time,tau,step,identity,first,m))
                if part in snap_parts:pictures[(ctx['label'],part)]=dict(ids=m['ids'].copy(),x=m['x'].copy(),fixed=m['fixed'].copy(),p=m['p'].copy(),kappa=m['kappa'].copy(),J=m['J'].copy(),nn=m['nn'].copy(),surface=m['surface'].copy(),time=time,tau=tau,step=step)
            c.need(times[0]==times[1] and frames[0]['PorePress0'].tobytes()==frames[1]['PorePress0'].tobytes(),'Actual clocks/steps or fixed native P0 differ; no interpolation')
            soil=frames[0]['Idp'][:,0]>=2060;dp=frames[1]['PorePress'][soil,0].astype(float)-frames[0]['PorePress'][soil,0].astype(float);dx=frames[1]['Posd'][soil]-frames[0]['Posd'][soil];pairs.append(dict(part=part,time_s=times[0][0],tau_s=times[0][1],completed_step=times[0][2],soil_IDs=5000,p_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),p_max_abs_difference_Pa=float(np.abs(dp).max()),material_XYZ_max_component_difference_mm=1000*float(np.abs(dx).max()),material_vector_max_difference_mm=1000*float(np.sqrt(np.max(np.sum(dx*dx,axis=1))))))
        c.need(fb.read(1)==b'' and fa.tell()==12+66*old['dtype'].itemsize,'Exact n4 extent and untouched n3 prefix extent required')
    morph=[]
    for requested,part in SNAPS:
        for ctx in contexts:
            q=pictures[(ctx['label'],part)]
            for i,identity in enumerate(q['ids']):morph.append(dict(group=ctx['label'],AS_exponent=ctx['exponent'],requested_near_tau_s=requested,part=part,time_s=q['time'],tau_s=q['tau'],completed_step=q['step'],native_id=int(identity),x_m=float(q['x'][i,0]),z_m=float(q['x'][i,1]),p_Pa=float(q['p'][i]),kappa=float(q['kappa'][i]),J=float(q['J'][i]),rNN_over_dp=float(q['nn'][i]),saved_FS23=int(q['surface'][i])))
    for leaf,rows in (('history',body),('cohorts',cohorts),('material_points',points),('parameter_differences',pairs),('morphology',morph)):
        path=Path(str(PREFIX)+'_'+leaf+'.csv');c.write(path,rows);files.append(path)
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    for ctx,color in zip(contexts,('C0','C1')):
        rows=[r for r in body if r['group']==ctx['label']];t=[r['tau_s'] for r in rows];label='n='+str(ctx['exponent']);ax=axes.ravel()
        for key,style in (('p_min_Pa','--'),('p_max_Pa',':'),('p_RMS_Pa','-')):ax[0].plot(t,[r[key]*.001 for r in rows],style,c=color,label=label+' '+key.split('_')[1])
        for key,style in (('mean_settlement_from_PRE_mm','-'),('displacement_RMS_from_PRE_mm','--')):ax[1].plot(t,[r[key] for r in rows],style,c=color,label=label+' '+('mean settlement' if style=='-' else 'displacement RMS'))
        for key,style in (('velocity_RMS_m_s','-'),('max_speed_m_s','--')):ax[2].plot(t,[r[key] for r in rows],style,c=color,label=label+' '+('RMS' if style=='-' else 'max'))
        for key,style in (('mean_kappa','-'),('max_kappa','--')):ax[3].plot(t,[r[key] for r in rows],style,c=color,label=label+' '+('mean' if style=='-' else 'max'))
        for i,lo,hi,scale in ((4,'min_J','max_J',1.),(5,'min_n','max_n',1.),(6,'min_k_m_s','max_k_m_s',1e4)):
            for key,style in ((lo,'--'),(hi,'-')):ax[i].plot(t,[r[key]*scale for r in rows],style,c=color,label=label+' '+('min' if style=='--' else 'max'))
        ax[7].plot(t,[r['total_stress_Frobenius_RMS_Pa']*.001 for r in rows],c=color,label=label)
        for key,style in (('front_particle_center_x_m','-'),('max_particle_center_z_m','--')):ax[8].plot(t,[r[key] for r in rows],style,c=color,label=label+' '+('front x' if style=='-' else 'max z'))
    axes[0,0].set_yscale('symlog',linthresh=.1)
    labels=(('Saved pressure; not dense extrema','p [kPa]'),('True PRE material reference','Displacement [mm]'),('Soil velocity','Speed [m/s]'),('Plastic history','kappa'),('Saved volume ratio','J'),('Saved porosity','n'),('Saved conductivity','k [1e-4 m/s]'),('Total-stress RMS','Stress [kPa]'),('Particle-center geometry','Coordinate [m]'))
    decorate(axes,labels,pairs);fig.suptitle('AS epsilon=.2, n3 versus failed n4 first66 saves; actual .01 s cadence; saved response, not full/theory/half acceptance');path=Path(str(PREFIX)+'_overview.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained');ax=axes.ravel()
    for ctx,color in zip(contexts,('C0','C1')):
        rr=[r for r in cohorts if r['group']==ctx['label'] and r['cohort']=='all_soil'];t=[r['tau_s'] for r in rr];label='n='+str(ctx['exponent'])
        for key,style in (('pair_both_in_cohort_lt_0p5dp','-'),('pair_both_in_cohort_lt_0p7dp','--')):ax[0].plot(t,[r[key] for r in rr],style,c=color,label=label+(' r<.5dp' if style=='-' else ' r<.7dp'))
        for i,base in ((1,'rNN_over_dp'),(2,'rNN_over_dp_sqrtJ_proxy')):
            for suffix,style in (('min','-'),('q05','--'),('median',':')):ax[i].plot(t,[r[base+'_'+suffix] for r in rr],style,c=color,label=label+' '+suffix)
    for ctx,style in zip(contexts,('-','--')):
        for identity,color in zip(FOCUS,('C0','C1','C2','C3')):
            rr=[r for r in points if r['group']==ctx['label'] and r['native_id']==identity];t=[r['tau_s'] for r in rr];label=str(identity)+' n'+str(ctx['exponent'])
            for i,key,scale in ((3,'p_Pa',.001),(4,'dx_since_first_tau0p01_save_mm',1.),(5,'dz_since_first_tau0p01_save_mm',1.),(6,'speed_m_s',1.),(7,'kappa',1.),(8,'J',1.)):ax[i].plot(t,[r[key]*scale for r in rr],style,c=color,label=label)
    ax[3].set_yscale('symlog',linthresh=.1);labels=(('Unique close soil pairs; descriptive','Count'),('Nearest-other spacing','rNN/dp'),('Isotropic spacing proxy, not F correction','rNN/(dp sqrt(J))'),('Fixed material pressure; saved samples','p [kPa]'),('Fixed material x motion since own first save','dx [mm]'),('Fixed material z motion since own first save','dz [mm]'),('Fixed material speed','Speed [m/s]'),('Fixed material plastic history','kappa'),('Fixed material volume ratio','J'));decorate(axes,labels,pairs);fig.suptitle('Fixed IDs 5944/5945/7017/6814 and spatial proxies; first save is tau .01, not PRE/t0; NN does not establish tensile causation');path=Path(str(PREFIX)+'_spacing_material.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(2,3,figsize=(14,8),sharex=True,sharey=True,layout='constrained');values=np.concatenate([q['kappa'] for q in pictures.values()]);norm=cluster.Normalize(float(values.min()),float(values.max()),clip=False);xy=np.concatenate([q['x'] for q in pictures.values()]);limits=(float(xy[:,0].min()-cluster.DP),float(xy[:,0].max()+cluster.DP),float(xy[:,1].min()-cluster.DP),float(xy[:,1].max()+cluster.DP))
    for row,ctx in enumerate(contexts):
        for col,(_,part) in enumerate(SNAPS):
            q=pictures[(ctx['label'],part)];a=axes[row,col];a.scatter(q['fixed'][:,0],q['fixed'][:,1],s=2,c='.75',marker='s',linewidths=0);image=a.scatter(q['x'][:,0],q['x'][:,1],c=q['kappa'],cmap='viridis',norm=norm,s=4,linewidths=0);a.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title='n=%g actual tau=%.12g s'%(ctx['exponent'],q['tau']));a.set_aspect('equal',adjustable='box')
    fig.colorbar(image,ax=axes.ravel().tolist(),label='Raw Kplastic kappa; shared full actual min/max',shrink=.8);fig.suptitle('Raw 5000-soil native coordinates, grey fixed markers; same display window, no interpolation/filtering/time fitting');path=Path(str(PREFIX)+'_morphology.png');fig.savefig(path);plt.close(fig);files.append(path)
    c.need(all(c.stat(q['path'])==q for q in before),'Consumed sealed native/helper/input binding changed');result=dict(stage=TAG,passed=True,analysis_completed=True,actual_common_frames=66,original_n3_header=[6805,22,300],original_n4_header=[6805,22,66],headers_not_rewritten=True,n3_records_read=66,n4_records_read=66,n4_runtime_success=False,n4_original_planned_frames=90,n4_original_planned_end=4360000,n4_failure_reported_step=4265004,reported_failure_step_not_native_state=True,unsaved_failure_reconstructed=False,typed_sequential_passes_each=1,all22_finite_and_ID_checks=True,soil_IDs_per_frame=5000,all_native_IDs_per_frame=6805,actual_clocks_steps_exact=True,P0_bits_equal=True,source_actual_time_s=old['done']['source_actual_time_s'],actual_tau_first_s=pairs[0]['tau_s'],actual_tau_last_s=pairs[-1]['tau_s'],focus_IDs=list(FOCUS),morphology_actual_parts=[p for _,p in SNAPS],PRE_mean_displacement_from_reader_history=True,focus_displacement_reference='own first saved tau .01, not PRE',parameter_comparison_not_half_or_theory=True,cross_parameter_5Pa_gate=False,NN_metrics_not_tensile_causation=True,dense_trace_read=False,saved_extrema_not_dense_peak=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,queue_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in files])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('ASN4_PARTIAL_COMPARISON_READY',CHECK,flush=True)

def decorate(axes,labels,pairs):
    for ax,(title,ylabel) in zip(axes.ravel(),labels):ax.set(title=title,ylabel=ylabel,xlabel='Actual tau from PRE [s]',xlim=(pairs[0]['tau_s'],pairs[-1]['tau_s']));ax.grid(alpha=.25);ax.legend(fontsize=6)

if __name__=='__main__':main()

