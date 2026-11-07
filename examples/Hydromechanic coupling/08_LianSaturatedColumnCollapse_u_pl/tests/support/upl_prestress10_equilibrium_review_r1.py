"""Fresh completed 10s CPU preload: descriptive review only, never a solver/decoder."""
import argparse,json,struct
from pathlib import Path
from upl_plastic_periodic_pair_r1 import np,plt,SCHEMA,TYPES,need,js,stat,table,write,frob,bound

T=Path(__file__).resolve().parents[1]
N,FIXED,SOIL=7060,2060,5000
DT,H,DP,RHO,WATER,E=.0000025,2.,.04,2072.5,1000.,20.e6
G,NU,N0=map(lambda x:float(np.float32(x)),(9.81,.33,.35))
GW,GS,GT=WATER*G,(RHO-WATER)*G,RHO*G
K0=NU/(1.-NU);M=E*(1.-NU)/((1.+NU)*(1.-2.*NU))

def load(backend):
    need(backend=='CPU','Only the completed10s CPU preload is admitted');tag='upl_prestress10_CPU_r1';d=T/'outputs'/(tag+'_native_r1')
    receipt=T/'logs'/(tag+'_native_r1.check.json');c=js(receipt)
    need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'],'Completed original native guards required')
    consumed=[stat(Path(__file__)),stat(receipt)]+[bound(c[k]) for k in ('source_run','reader_call','reader_build','native_completion')]
    run=js(c['source_run']['path']);done=js(d/'completion.json');samples=done['samples']
    need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['consumed_stats_unchanged'],'Actual completed run receipt required')
    call=js(c['reader_call']['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual sole reader exit must be zero')
    need(done['passed'] and done['stage']=='upl_prestress10_native_r1' and done['input_run_tag']==tag and done['window']=='preload10' and done['gravitypreload_metadata_absent_verified'],'Only completed event-absent10s profile is admitted')
    need(done['total_native_IDs']==N and done['fixed_IDs']==FIXED and done['soil_IDs']==SOIL and done['typed_arrays']==22 and done['typed_bytes_per_particle']==212,'Native scope/layout differs')
    need(samples==run['saved_frames'] and samples>=2 and done['completed_steps']==run['actual_steps'] and run['actual_steps'] in (4000000,4000001),'Actual final Run steps/frame count differs')
    need(done['dt_s']==DT and done['all_ID_p0_float_bits_checks']==N*samples and done['soil_ledger_checks']==SOIL*samples and done['fixed_marker_checks']==FIXED*samples and done['soil_cache_float_bits_checks']==SOIL*samples,'Incomplete original baseline/ledger/fixed/cache coverage')
    need(done['soil_noninitial_kappa_monotonic_checks']==SOIL*(samples-1) and done['noninitial_signed_intervals']==samples-1 and len(done['saved_FS23_soil_checks_by_part'])==samples,'Original history/interval coverage differs')
    for k in ('all22_arrays_finite_and_ID_aligned','actual_scalar_clock_verified','no_exclusions','saved_FS23_soil_pressure_nonpositive','initial_effective_stress_zero','p0_is_fixed_initial_material_hydrostatic_baseline'):
        need(done[k],'Original completion guard missing: '+k)
    need(done['physical_acceptance'] is False,'Reader completion cannot be physical acceptance')
    files=[d/x for x in ('completion.json','typed22_layout.csv','typed22.bin','native_ids.csv','clocks.csv','history.csv')]
    consumed += [stat(p) for p in files]
    layout=table(files[1]);need(len(layout)==22,'Exactly22 layout records required')
    formats=[('<f8')];names=['time'];offsets=[0];off=8
    for row,(name,kind,nc) in zip(layout,SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,TYPES[kind].itemsize*nc),'Typed layout order/type/width differs')
        names.append(name);formats.append((TYPES[kind],(N,nc)) if nc>1 else (TYPES[kind],(N,)));offsets.append(off);off+=N*TYPES[kind].itemsize*nc
    need(off==8+N*212 and files[2].stat().st_size==12+samples*off,'Raw record/file size differs')
    with files[2].open('rb') as f:need(struct.unpack('<III',f.read(12))==(N,22,samples),'Raw native header differs')
    frames=np.memmap(files[2],mode='r',offset=12,shape=(samples,),dtype=np.dtype(dict(names=names,formats=formats,offsets=offsets,itemsize=off)))
    ids=table(files[3]);need(len(ids)==N and all(int(r['id'])==i and int(r['is_fixed'])==int(i<FIXED) for i,r in enumerate(ids)),'Complete original ID table required')
    x0=np.array([[float(r[k]) for k in ('x0','y0','z0')] for r in ids]);p0=np.array([float(r['initial_hydrostatic_p0_float_Pa']) for r in ids],dtype='<f4')
    need(np.array_equal(frames[0]['Posd'],x0),'Initial material coordinates differ')
    clocks=table(files[4]);need(len(clocks)==samples,'Actual clock record count differs');scalar=0.;previous=0
    for part,(a,c) in enumerate(zip(frames,clocks)):
        completed=int(c['completed_step']);saved=int(c['saved_step']);time=float(a['time'])
        need(int(c['part'])==part and (completed==0 and saved==0 if part==0 else completed>previous and saved==completed-1),'Actual native Step sequence differs')
        need(completed<=run['actual_steps'] and float(c['dt_s'])==DT,'Clock steps/locked dt differ')
        for _ in range(previous,completed):scalar+=DT
        previous=completed
        need(struct.pack('<d',time)==struct.pack('<d',float(c['time_s'])) and abs(time-scalar)<=1.e-14,'Actual scalar+=dt clock differs; no interpolation is permitted')
        err=float(c['signed_dterror_s']);need(np.isfinite(err) and err<=1.e-14 and (part==0 or int(c['dterror_interval_empty'])==0),'Original signed interval guard differs')
        need(np.array_equal(a['Idp'],np.arange(N)),'Native ID alignment differs')
        for name,_,_ in SCHEMA:need(np.isfinite(a[name]).all(),'Nonfinite actual typed array: '+name)
        need(np.array_equal(a['PorePress0'].view('<u4'),p0.view('<u4')),'Frozen material P0 changed')
        need(np.array_equal(a['Posd'][:FIXED],x0[:FIXED]),'Fixed geometry changed')
        fs=np.isin(a['FSType'][FIXED:],(2,3));need(int(fs.sum())==done['saved_FS23_soil_checks_by_part'][part] and fs.any() and np.all(a['PorePress'][FIXED:][fs]<=0),'Actual FS mask/pressure differs from original guard')
    need(previous==done['completed_steps'] and frames[-1]['time']==done['actual_end_s'] and abs(scalar-done['scalar_reference_end_s'])<=1.e-14 and abs(frames[-1]['time']-10.)<=DT+1.e-14,'Actual final native clock differs')
    z=x0[FIXED:,2];x=x0[FIXED:,0];row=np.rint((z-.5*DP)/DP).astype(int)
    need(np.array_equal(np.unique(row),np.arange(50)) and np.array_equal(np.bincount(row),np.full(50,100)) and np.max(np.abs(z-(.5*DP+DP*row)))<=64*np.finfo(float).eps*H,'Original50 material layers differ')
    twoh=2*float(np.float32(.048))
    bands=dict(all=np.arange(SOIL),top_2h=np.flatnonzero(z>=z.max()-twoh),bottom_2h=np.flatnonzero(z<=z.min()+twoh),left_2h=np.flatnonzero(x<=x.min()+twoh),right_2h=np.flatnonzero(x>=x.max()-twoh))
    need([len(v) for v in bands.values()]==done['initial_material_band_counts'],'Frozen material bands differ')
    return frames,x0[FIXED:],p0[FIXED:],row,bands,done,consumed

def fields(a,x0):
    p=a['PorePress'][FIXED:].astype(float);pos=a['Posd'][FIXED:];vel=a['Vel'][FIXED:].astype(float);s=a['SigmaState_kk'][FIXED:];shear=a['SigmaState_ij'][FIXED:]
    depth0=H-x0[:,2];depth=H-pos[:,2];pref0=GW*depth0;pref=GW*depth
    eff=np.column_stack((s,shear));total=eff.copy();total[:,:3]-=p[:,None]
    eref=np.zeros_like(eff);eref[:,2]=-GS*depth0;eref[:,0]=eref[:,1]=K0*eref[:,2]
    tref=eref.copy();tref[:,:3]-=pref0[:,None]
    return dict(p=p,p0=a['PorePress0'][FIXED:].astype(float),q=a['ExcessPorePress'][FIXED:].astype(float),head_residual=p-pref,depth0=depth0,depth=depth,pref0=pref0,pref=pref,
        eff=eff,total=total,eref=eref,tref=tref,u=(pos-x0)*1000.,uref=-1000*GS*(H*H-depth0*depth0)/(2*M),v=np.linalg.norm(vel,axis=1),velocity=vel,
        theta=a['PoroThetaLastStage'][FIXED:],mass=a['PoroMixtureDensity'][FIXED:]*a['PoroCurrentVolume'][FIXED:],kinetic=.5*a['PoroMixtureDensity'][FIXED:]*a['PoroCurrentVolume'][FIXED:]*np.sum(vel*vel,axis=1),
        J=a['PoroVolumeRatio'][FIXED:],n=a['PoroPorosity'][FIXED:],rho=a['PoroMixtureDensity'][FIXED:],k=a['PoroHydraulicConductivity'][FIXED:],kap=a['Kplastic'][FIXED:],fs=np.isin(a['FSType'][FIXED:],(2,3)))

def summary(f,i,part,time,label):
    mean=lambda k:float(np.mean(f[k][i]));rms=lambda v:float(np.sqrt(np.mean(v*v)));fs=i[f['fs'][i]]
    r=dict(part=part,actual_time_s=time,initial_material_group=label,count=len(i),initial_depth_mean_m=mean('depth0'),current_depth_mean_m=mean('depth'),p_mean_Pa=mean('p'),p_RMS_Pa=rms(f['p'][i]),p_min_Pa=float(f['p'][i].min()),p_max_Pa=float(f['p'][i].max()),
        p0_material_mean_Pa=mean('p0'),native_q_mean_Pa=mean('q'),native_q_RMS_Pa=rms(f['q'][i]),native_q_min_Pa=float(f['q'][i].min()),native_q_max_Pa=float(f['q'][i].max()),hydro_initial_mean_Pa=mean('pref0'),hydro_current_mean_Pa=mean('pref'),current_head_residual_mean_Pa=mean('head_residual'),current_head_residual_RMS_Pa=rms(f['head_residual'][i]),
        eff_zz_compression_mean_Pa=float(-np.mean(f['eff'][i,2])),total_zz_compression_mean_Pa=float(-np.mean(f['total'][i,2])),eff_zz_reference_compression_mean_Pa=float(-np.mean(f['eref'][i,2])),total_zz_reference_compression_mean_Pa=float(-np.mean(f['tref'][i,2])),eff_stress_Frob_RMS_Pa=rms(frob(f['eff'][i])),total_stress_Frob_RMS_Pa=rms(frob(f['total'][i])),eff_reference_residual_Frob_RMS_Pa=rms(frob(f['eff'][i]-f['eref'][i])),total_reference_residual_Frob_RMS_Pa=rms(frob(f['total'][i]-f['tref'][i])),
        material_settlement_mean_mm=float(-np.mean(f['u'][i,2])),material_XYZ_displacement_max_mm=float(np.linalg.norm(f['u'][i],axis=1).max()),settlement_reference_mean_mm=float(-np.mean(f['uref'][i])),velocity_RMS_m_s=rms(f['v'][i]),velocity_max_m_s=float(f['v'][i].max()))
    r.update(theta_mean_s_inv=mean('theta'),theta_RMS_s_inv=rms(f['theta'][i]),current_soil_mixture_mass_kg_per_m=float(np.sum(f['mass'][i])),kinetic_J_per_m=float(np.sum(f['kinetic'][i])),mean_vx_m_s=float(np.mean(f['velocity'][i,0])),mean_vy_m_s=float(np.mean(f['velocity'][i,1])),mean_vz_m_s=float(np.mean(f['velocity'][i,2])))
    for name in ('J','n','rho','k','kap'):
        for op,fun in (('mean',np.mean),('min',np.min),('max',np.max)):r[name+'_'+op]=float(fun(f[name][i]))
    r.update(FS23_count=len(fs),FS23_p_mean_Pa=float(np.mean(f['p'][fs])) if len(fs) else '',FS23_p_min_Pa=float(f['p'][fs].min()) if len(fs) else '',FS23_p_max_Pa=float(f['p'][fs].max()) if len(fs) else '',FS23_initial_p0_mean_Pa=float(np.mean(f['p0'][fs])) if len(fs) else '',FS23_current_hydro_head_mean_Pa=float(np.mean(f['pref'][fs])) if len(fs) else '')
    return r

def plots(paths,history,profiles,selected,backend):
    allrows=[r for r in history if r['initial_material_group']=='all'];t=np.array([r['actual_time_s'] for r in allrows]);fig,axes=plt.subplots(3,3,figsize=(14.5,11.))
    specs=[('p_mean_Pa','p mean',.001),('hydro_current_mean_Pa','fixed-H hydrostatic at current z',.001)]
    for key,label,scale in specs:axes[0,0].plot(t,[r[key]*scale for r in allrows],label=label)
    for key,label in (('native_q_RMS_Pa','RMS(p - fixed material p0)'),('current_head_residual_RMS_Pa','RMS(p - fixed-H hydrostatic at current z)')):axes[0,1].plot(t,[r[key]*.001 for r in allrows],label=label)
    for key,label,ls in (('eff_zz_compression_mean_Pa','effective','-'),('total_zz_compression_mean_Pa','total','-'),('eff_zz_reference_compression_mean_Pa','drained effective reference','--'),('total_zz_reference_compression_mean_Pa','self-weight total reference','--')):axes[0,2].plot(t,[r[key]*.001 for r in allrows],ls,label=label)
    for key,label in (('velocity_RMS_m_s','RMS'),('velocity_max_m_s','max')):axes[1,0].plot(t,[r[key] for r in allrows],label=label)
    for band in ('top_2h','bottom_2h'):
        rows=[r for r in history if r['initial_material_group']==band];line=axes[1,1].plot(t,[r['material_settlement_mean_mm'] for r in rows],label=band)[0]
        axes[1,1].plot(t,[r['settlement_reference_mean_mm'] for r in rows],'--',color=line.get_color(),label=band+' drained elastic reference')
    for key,base,scale,label in (('J_mean',1,100,'100(J mean - 1)'),('n_mean',N0,100,'porosity mean change (pp)'),('rho_mean',RHO,100/RHO,'density mean change (%)')):axes[1,2].plot(t,[(r[key]-base)*scale for r in allrows],label=label)
    axes[2,0].plot(t,[r['kap_max'] for r in allrows],label='max actual kappa');energy=axes[2,0].twinx();energy.plot(t,[r['kinetic_J_per_m'] for r in allrows],color='tab:orange',label='current-mi kinetic');energy.set_ylabel('kinetic energy (J/m)');energy.legend(fontsize=6.5,loc='upper right')
    for key,label,ls in (('FS23_p_mean_Pa','FS p mean','-'),('FS23_p_min_Pa','FS p min','-'),('FS23_p_max_Pa','FS p max','-'),('FS23_initial_p0_mean_Pa','same IDs initial p0','--'),('FS23_current_hydro_head_mean_Pa','same IDs fixed-H hydrostatic at current z','--')):axes[2,1].plot(t,[r[key] for r in allrows],ls,label=label)
    for key,label in (('current_head_residual_RMS_Pa','pressure - fixed-H hydrostatic at current z'),('eff_reference_residual_Frob_RMS_Pa','effective tensor - K0 reference'),('total_reference_residual_Frob_RMS_Pa','total tensor - self-weight reference')):axes[2,2].plot(t,[r[key]*.001 for r in allrows],label=label)
    titles=['Pressure and fixed-H hydrostatic reference','Two distinct pressure excess definitions','Vertical compression and weight references','Actual velocity','Fixed initial material settlement','Actual single-J state evolution','Plastic history / kinetic energy','Free-surface pressure / material p0 offset','Unfitted reference residuals']
    labels=['pressure (kPa)','pressure RMS (kPa)','compression (kPa)','velocity (m/s)','downward settlement (mm)','relative change (%) / porosity pp','kappa','pressure (Pa)','residual RMS (kPa)']
    for ax,title,ylabel in zip(axes.flat,titles,labels):ax.set(title=title,xlabel='actual saved time (s)',ylabel=ylabel);ax.grid(alpha=.22);ax.legend(fontsize=6.5)
    axes[2,0].legend(fontsize=6.5,loc='upper left')
    fig.suptitle('Case08 '+backend+': completed preload diagnostic, not equilibrium acceptance',fontsize=13);fig.tight_layout(rect=(0,.025,1,.96));fig.text(.5,.008,f"Reference unit weights: water {GW/1000:.6g}, submerged {GS/1000:.6g}, mixture {GT/1000:.6g} kN/m3.\nH=2 m is the initial fixed reference plane, not an inferred water table. Drained elastic/K0 diagnostic assumptions only.",ha='center',fontsize=8);fig.savefig(paths['png'],dpi=170);plt.close(fig)
    specs=(('p_mean_Pa','Pressure (kPa)',.001,'hydro_initial_mean_Pa'),('native_q_mean_Pa','p - fixed material p0 (kPa)',.001,None),('eff_zz_compression_mean_Pa','Effective vertical compression (kPa)',.001,'eff_zz_reference_compression_mean_Pa'),('total_zz_compression_mean_Pa','Total vertical compression (kPa)',.001,'total_zz_reference_compression_mean_Pa'),('material_settlement_mean_mm','Downward settlement (mm)',1.,'settlement_reference_mean_mm'),('velocity_RMS_m_s','Velocity RMS (m/s)',1.,None))
    for ledger in (False,True):
        fig,axs=plt.subplots(2,2,figsize=(11.5,9.)) if ledger else plt.subplots(2,3,figsize=(14.,9.))
        settings=tuple((k,label,1.,None) for k,label in (('J_mean','J'),('n_mean','porosity'),('rho_mean','mixture density (kg/m3)'),('kap_max','layer max kappa'))) if ledger else specs
        for ax,(key,label,scale,ref) in zip(axs.flat,settings):
            for part in selected:
                rows=[r for r in profiles if r['part']==part];ax.plot([r[key]*scale for r in rows],[r['initial_depth_mean_m'] for r in rows],label=f"{rows[0]['actual_time_s']:.8g} s")
            if ref:
                rows=[r for r in profiles if r['part']==0];ax.plot([r[ref]*scale for r in rows],[r['initial_depth_mean_m'] for r in rows],'k--',lw=1.8,label='drained reference')
            ax.set(xlabel=label,ylabel='initial material depth H - z0 (m)');ax.invert_yaxis();ax.grid(alpha=.22)
        axs.flat[0].legend(fontsize=7);fig.suptitle('Actual saved profiles; fixed initial material layers, no interpolation',fontsize=12);fig.tight_layout(rect=(0,.025,1,.96));fig.text(.5,.008,'Depth at current z and fixed-H hydrostatic values are separate CSV columns.\nH=2 m is the initial fixed reference plane, not an inferred water table or proof of equilibrium.',ha='center',fontsize=8);fig.savefig(paths['statepng' if ledger else 'profilespng'],dpi=170);plt.close(fig)

def retained5(history,bands,x0,consumed):
    prefix=T/'figures/upl_prestress_equilibrium_review_r1';check=Path(str(prefix)+'.check.json');hp=Path(str(prefix)+'_history.csv');vp=T/'logs/upl_prestress_equilibrium_review_r1.visual.json'
    old=js(check);visual=js(vp);need(old['offline_analysis_completed'] and old['backend_argument']=='CPU' and old['actual_completed_steps']==2000000 and old['material_layers']==50 and visual['three_PNGs_inspected'] and visual['independent_readonly_physical_review_agrees'],'Closed retained5s descriptive review required')
    nh=T/'outputs/upl_prestress_extended_CPU_r1_native_r1/history.csv';coords=T/'outputs/upl_prestress_extended_CPU_r1_native_r1/native_ids.csv'
    for p,entries in ((check,visual['source_outputs']),(hp,visual['source_outputs']),(nh,old['source_inputs']),(coords,old['source_inputs'])):
        matches=[e for e in entries if Path(e['path']).samefile(p)];need(len(matches)==1,'Unique sealed retained5s input required');consumed.append(bound(matches[0]))
    consumed.append(stat(vp));need(old['reference']['water_plane_H_m']==H and old['reference']['gravity_m_s2']==G and old['reference']['constrained_modulus_Pa']==M,'Retained restricted reference constants differ')
    ids=table(coords);need(len(ids)==N and all(int(r['id'])==i and int(r['is_fixed'])==int(i<FIXED) for i,r in enumerate(ids)) and np.array_equal(np.array([[float(r[k]) for k in ('x0','y0','z0')] for r in ids[FIXED:]]),x0),'Retained/current original soil IDs/coordinates differ')
    oldrows=table(hp);oldnative=table(nh);need(len(oldrows)==len(oldnative)==5*old['actual_saved_states'],'Retained5s band coverage differs');oldpart=old['actual_saved_states']-1
    endpoint={r['initial_material_group']:r for r in oldrows if int(r['part'])==oldpart};aux={r['initial_material_band']:r for r in oldnative if int(r['part'])==oldpart}
    newpart=max(r['part'] for r in history);current={r['initial_material_group']:r for r in history if r['part']==newpart};need(set(endpoint)==set(aux)==set(current)==set(bands),'Retained/current material groups differ')
    metrics=('p_mean_Pa','p_RMS_Pa','native_q_RMS_Pa','current_head_residual_RMS_Pa','eff_zz_compression_mean_Pa','total_zz_compression_mean_Pa','eff_stress_Frob_RMS_Pa','total_stress_Frob_RMS_Pa','material_settlement_mean_mm','velocity_RMS_m_s','velocity_max_m_s','J_mean','J_min','J_max','n_mean','rho_mean','rho_min','rho_max','kap_max','theta_RMS_s_inv','current_soil_mixture_mass_kg_per_m','kinetic_J_per_m')
    result=[]
    for label in bands:
        a=dict(endpoint[label]);b=current[label]
        for key in ('theta_RMS_s_inv','current_soil_mixture_mass_kg_per_m','kinetic_J_per_m'):a[key]=aux[label][key]
        need(int(a['count'])==int(aux[label]['count'])==b['count']==len(bands[label]) and float(a['actual_time_s'])==float(aux[label]['time_s'])==old['actual_end_s'],'Retained endpoint time/count differs')
        for metric in metrics:
            x,y=float(a[metric]),float(b[metric]);need(np.isfinite(x) and np.isfinite(y),'Nonfinite endpoint statistic')
            result.append(dict(initial_material_group=label,count=b['count'],metric=metric,retained5s_actual_part=oldpart,retained5s_actual_time_s=float(a['actual_time_s']),fresh10s_actual_part=newpart,fresh10s_actual_time_s=b['actual_time_s'],retained5s_value=x,fresh10s_value=y,fresh10s_minus_retained5s=y-x,comparison='separate fresh runs; different endpoint times; descriptive only'))
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--backend',required=True,choices=('CPU',));ap.add_argument('--prefix',type=Path,default=T/'figures/upl_prestress10_equilibrium_review_r1');args=ap.parse_args()
    prefix=args.prefix.resolve();need(prefix.parent==(T/'figures').resolve(),'Use a shallow tests/figures prefix')
    paths={k:Path(str(prefix)+suffix) for k,suffix in dict(history='_history.csv',profiles='_profiles.csv',late='_late.csv',comparison='_versus5s.csv',png='.png',profilespng='_profiles.png',statepng='_state_profiles.png',check='.check.json').items()}
    need(not any(p.exists() for p in paths.values()),'Existing analysis protected; no overwrite')
    frames,x0,p0,row,bands,done,consumed=load(args.backend);history=[];profiles=[]
    for part,a in enumerate(frames):
        f=fields(a,x0);time=float(a['time'])
        for label,i in bands.items():history.append(summary(f,i,part,time,label))
        for layer in range(50):profiles.append(summary(f,np.flatnonzero(row==layer),part,time,'layer_'+str(layer)))
    times=np.array(frames['time']);selected=sorted(set(int(np.argmin(abs(times-t))) for t in (0,.5,1,2,5,8,9,9.5,10)))
    late=[];last=fields(frames[-1],x0)
    for duration in (.5,1.):
        start=int(np.searchsorted(times,times[-1]-duration,side='left'));first=fields(frames[start],x0)
        for label,i in bands.items():
            hist=[r for r in history if r['initial_material_group']==label and r['part']>=start];dp=last['p'][i]-first['p'][i];ds=last['total'][i]-first['total'][i]
            late.append(dict(requested_late_window_s=duration,actual_start_part=start,actual_start_s=float(times[start]),actual_end_s=float(times[-1]),actual_duration_s=float(times[-1]-times[start]),actual_saved_states=len(hist),initial_material_group=label,count=len(i),endpoint_pressure_change_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),endpoint_pressure_change_max_Pa=float(np.abs(dp).max()),endpoint_total_stress_change_Frob_RMS_Pa=float(np.sqrt(np.mean(frob(ds)**2))),endpoint_material_XYZ_change_max_mm=float(np.linalg.norm(last['u'][i]-first['u'][i],axis=1).max()),endpoint_mean_downward_settlement_change_mm=float(-np.mean(last['u'][i,2]-first['u'][i,2])),endpoint_J_change_max=float(np.abs(last['J'][i]-first['J'][i]).max()),endpoint_kappa_increment_max=float((last['kap'][i]-first['kap'][i]).max()),saved_velocity_RMS_min_m_s=min(r['velocity_RMS_m_s'] for r in hist),saved_velocity_RMS_max_m_s=max(r['velocity_RMS_m_s'] for r in hist),saved_pressure_RMS_min_Pa=min(r['p_RMS_Pa'] for r in hist),saved_pressure_RMS_max_Pa=max(r['p_RMS_Pa'] for r in hist)))
            dv=last['velocity'][i]-first['velocity'][i];de=last['eff'][i]-first['eff'][i];duration_actual=float(times[-1]-times[start])
            late[-1].update(endpoint_effective_stress_change_Frob_RMS_Pa=float(np.sqrt(np.mean(frob(de)**2))),endpoint_velocity_vector_change_RMS_m_s=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1)))),endpoint_saved_velocity_finite_difference_RMS_m_s2=float(np.sqrt(np.mean(np.sum(dv*dv,axis=1))))/duration_actual,endpoint_rho_change_max_kg_m3=float(np.abs(last['rho'][i]-first['rho'][i]).max()),endpoint_n_change_max=float(np.abs(last['n'][i]-first['n'][i]).max()),endpoint_kinetic_change_J_per_m=float(np.sum(last['kinetic'][i])-np.sum(first['kinetic'][i])),saved_kinetic_min_J_per_m=min(r['kinetic_J_per_m'] for r in hist),saved_kinetic_max_J_per_m=max(r['kinetic_J_per_m'] for r in hist))
            for metric in ('native_q_RMS_Pa','current_head_residual_RMS_Pa','material_settlement_mean_mm','eff_stress_Frob_RMS_Pa','total_stress_Frob_RMS_Pa','theta_RMS_s_inv','J_mean','rho_mean','kap_max'):
                late[-1]['saved_'+metric+'_min']=min(r[metric] for r in hist);late[-1]['saved_'+metric+'_max']=max(r[metric] for r in hist)
    comparison=retained5(history,bands,x0,consumed)
    for key,rows in (('history',history),('profiles',profiles),('late',late),('comparison',comparison)):write(paths[key],rows)
    plots(paths,history,profiles,selected,args.backend)
    need(all(stat(e['path'])==e for e in consumed),'Consumed completed export/receipt changed')
    review=dict(stage='upl_prestress10_equilibrium_review_r1',offline_analysis_completed=True,backend_argument=args.backend,actual_saved_states=len(frames),actual_end_s=float(times[-1]),actual_completed_steps=done['completed_steps'],material_layers=50,history_rows=len(history),profile_rows=len(profiles),retained5s_descriptive_comparison_rows=len(comparison),retained5s_comparison_is_separate_fresh_runs_not_restart_or_matched_time_equivalence=True,saved_velocity_finite_difference_is_not_native_total_acceleration=True,selected_actual_profile_times_s=[float(times[i]) for i in selected],late_window_rows=late,
        reference=dict(gravity_m_s2=G,water_unit_weight_Pa_m=GW,initial_mixture_unit_weight_Pa_m=GT,submerged_unit_weight_Pa_m=GS,elastic_K0=K0,constrained_modulus_Pa=M,water_plane_H_m=H,description='Unfitted small-strain one-dimensional drained elastic/K0 reference at initial material depth; fixed-H hydrostatic head at current z is a separate diagnostic. H=2 m is the initial fixed reference plane, not an inferred current water table. No precise SPH, plastic or transient theory claim.'),
        physical_acceptance=False,equilibrium_acceptance=False,new_physical_gate_applied=False,half_or_reference_solve_requested=False,interpolation_or_fitting=False,pressure_or_native_data_modified=False,large_per_frame_per_ID_CSV_written=False,figure_visual_QA_pending=True,source_inputs=consumed,outputs=[stat(p) for k,p in paths.items() if k!='check'],SHA_scans=0)
    with paths['check'].open('x',encoding='utf-8') as f:json.dump(review,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(offline_analysis_completed=True,actual_saved_states=len(frames),actual_end_s=float(times[-1]),physical_acceptance=False,figures=[str(paths[k]) for k in ('png','profilespng','statepng')])),flush=True)

if __name__=='__main__':main()
