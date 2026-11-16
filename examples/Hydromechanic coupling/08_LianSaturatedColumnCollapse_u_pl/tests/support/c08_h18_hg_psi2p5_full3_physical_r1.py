"""Single-group offline physical diagnostics of completed psi2p5 full3; never decode or solve."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
import c08_h18_lstar_window_review_r1 as metric
import c08_h18_hg_failed99_review_r1 as seals
import c08_h18_wall_c_retry_full3_review_r1 as geometry

T,L,typed=metric.T,metric.L,metric.core
need,read,stat,bind=metric.need,metric.read,metric.stat,metric.bind
TAG='c08_h18_hg_psi2p5_full3_physical_r1';RUN_TAG='c08_h18_hg_psi2p5_full3_r1';GROUP='psi2p5'
SOURCE='c08_h18_wend_branches_psi2p5_pre_r1';LABEL='psi=+2.5 deg, C-quality retry + HG'
RUN=L/(RUN_TAG+'.run.json');NATIVE=L/'c08_h18_hg_psi2p5_native_r1.check.json'
HG=L/'c08_h18_hg_psi2p5_full3_review_r1.check.json';NOTE=T/'notes'/(TAG+'.md')
CHECK=L/(TAG+'.check.json');PREFIX=T/'figures'/TAG
SELECTED=(1,30,50,60,120,300);PAPER15=(30,60,120);PAPER16=(1,50,120)
PAPER_MD=T.parents[3]/'src/papers/u-pw/Lian 2023 u-pl.md'
PAPER_PNG=T/'figures/c08_h18_lian2023_ref-21.png'
DP=.04;DT=.000005;H=float(np.float32(.072))


def bound(entry,consumed):
    value=bind(entry);consumed.append(value);return Path(value['path'])


def material(run,consumed):
    import xml.etree.ElementTree as ET
    root=ET.parse(bound(run['input_xml'],consumed)).getroot();soil=root.find('execution/special/soils')
    need(soil is not None,'Actual soil material XML missing')
    expected=dict(ModulusE=20e6,PRvs=.33,phi=25,phi_r=25,n_phi=0,coh=5000,coh_r=1000,n_coh=5,dlt=2.5,DilationDecay=.2)
    for key,value in expected.items():need(typed.core.f32(soil.find(key).get('value'))==typed.core.f32(value),'Outside this actual psi2p5 material: '+key)
    pairs=[(q.get('key'),q.get('value')) for q in root.findall('execution/parameters/parameter')];pars=dict(pairs)
    need(len(pars)==len(pairs) and all(float(pars[k])==v for k,v in dict(Kernel=2,DPCtes=3,DtFixed=DT,NoPenetration=1,ArtificialStress=1).items()),'Actual group kernel/step/mechanics differs')
    need(typed.core.f32(pars['ArtificialStressCoef'])==typed.core.f32(.3) and typed.core.f32(pars['ArtificialStressExp'])==typed.core.f32(2.55),'Actual AS.3/n2.55 differs')
    water=root.find('execution/special/hydromechanics/PoreWaterBulkModulus');need(water is not None and float(water.get('value'))==metric.KW==1e9,'Original pressure-storage diagnostic Kw differs')
    rows=typed.table(bound(run['native_profile'],consumed));profile={q['key']:q['value'] for q in rows}
    need(len(rows)==len(profile)==17 and profile['group']==GROUP,'Actual seventeen-key receiver material profile required')
    for key,value in {**expected,'Kernel':2,'DPCtes':3,'ArtificialStressCoef':.3,'ArtificialStressExp':2.55}.items():
        need(typed.core.f32(profile[key])==typed.core.f32(value),'Actual material profile differs: '+key)
    need(profile['fresh_trigger_active']=='0','Original fresh same-material trigger contract differs')


def inputs(consumed):
    run,native,hg=map(read,(RUN,NATIVE,HG));consumed.extend(stat(q) for q in (RUN,NATIVE,HG))
    need(run['stage']==RUN_TAG and run['group']==GROUP and run['passed'] and run['solver_completed']
         and run['actual_exit']==run['actual_Win32_exit']==0 and run['solver_identity_matches']
         and run['actual_steps']==2600000 and run['saved_frames']==301 and run['new_updates']==600000
         and run['consumed_stats_unchanged'],'Actual completed psi2p5 run required, not exit0 alone')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file','source_run','source_native','source_native_check','source_material_profile','source_physical_review','source_root_review'):
        bound(run[key],consumed)
    metric.owned(read(bound(run['actual_call'],consumed)));material(run,consumed)
    need(native['passed'] and native['original_safety_passed'] and native['reader_invocations']==1
         and native['consumed_stats_unchanged'] and native['run']==stat(RUN)
         and native['source_run']==run['source_run'],'One actual unique group-native receipt required')
    call=read(bound(native['actual_call'],consumed));metric.owned(call);reader=read(bound(native['reader_build'],consumed))
    need(reader['passed'] and Path(call['program']).resolve()==bound(reader['program'],consumed).resolve(),'Unique native program/build binding differs')
    done=read(bound(native['native_completion'],consumed));bound(native['metadata'],consumed)
    nr=Path(native['native_completion']['path']).parent
    need(nr==Path(run['output'])/'native_r1' and done['passed'] and done['group']==GROUP and done['samples']==301
         and done['completed_steps']==2600000 and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805
         and done['soil_IDs']==5000 and done['ledger_checks']==1505000 and done['P0_bits_checks']==2048305
         and done['fixed_marker_checks']==543305 and done['nonempty_signed_intervals']==301
         and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
         and not done['native_rewritten'],'All original301-frame native safety/count/clock gates required')
    args=call['arguments'];need(len(args)==8 and args[:3]==['--receiver','formal',GROUP]
         and Path(args[3]).resolve()==(Path(run['output'])/'data').resolve()
         and Path(args[4]).resolve()==Path(run['source_pre_file']['path']).resolve()
         and Path(args[5]).resolve()==Path(run['planned_steps']['path']).resolve()
         and Path(args[6]).resolve()==Path(run['native_profile']['path']).resolve()
         and Path(args[7]).resolve()==nr.resolve(),'Actual group DATA/PRE/plan/profile/output native binding differs')
    need(len(native['outputs'])==7,'Original seven native-export stat seals required')
    consumed.extend(bind(q) for q in native['outputs'])
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):seals.sealed(native,nr/leaf,consumed,'outputs')
    bundle=typed.typed(nr,6805,301,consumed);plan=typed.table(bound(run['planned_steps'],consumed));need(len(plan)==301,'Untouched full301 scalar plan required')
    for part,(c,p) in enumerate(zip(bundle['clocks'],plan)):
        need(int(c['part'])==int(p['part'])==part and int(c['completed_step'])==int(p['completed_step'])
             and int(c['saved_step'])==int(p['saved_step']) and metric.bits(c['time_s'])==metric.bits(p['time_s'])
             and metric.bits(c['dt_s'])==metric.bits(p['dt_s'])==metric.bits(DT) and c['dterror_interval_empty']=='0','Every actual saved group clock/signed interval must retain its original plan')
    source=read(run['source_native']['path']);sn=read(run['source_native_check']['path']);sr=read(run['source_run']['path'])
    need(sr['stage']==SOURCE and sr['group']==GROUP and sr['source_pre_file']==run['source_pre_file']
         and source['passed'] and source['certified_PRE'] and source['group']==GROUP and source['samples']==1001
         and source['same_material_plastic_PRE'] and sn['passed'] and sn['reader_invocations']==1
         and sn['source_run']==run['source_run'] and sn['completion']==run['source_native'],'Own actual same-material source required; psi0 PRE cannot substitute')
    sroot=Path(run['source_native']['path']).parent
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):seals.sealed(sn,sroot/leaf,consumed,'files')
    ref,cohorts=metric.previous.source_reference(typed.typed(sroot,7060,1001,consumed),source)
    for row in cohorts:row['group']=GROUP
    need(ref['time']==done['source_actual_time_s']==run['actual_source_time_s'],'Own actual source clock differs')
    need(hg['passed'] and hg['analysis_complete'] and hg['source_run']==stat(RUN) and hg['source_native_check']==stat(NATIVE)
         and hg['HG']['reviewed_rows']==602 and hg['HG']['saved_phase_pairs']==301
         and hg['HG']['Eold_bit_equal_pairs']==301 and hg['HG']['all_original_saved_domain_clock_cache_lifecycle_gates']
         and not hg['own_prefix_compared'],'Separate completed own-group HG602 review required; no psi0 prefix borrowed')
    return run,bundle,ref,cohorts


def spatial_rows(part,clock,d,ref):
    rows=[]
    for i,nid in enumerate(d['ids']):
        r=dict(group=GROUP,part=part,completed_step=int(clock['completed_step']),actual_time_s=float(clock['time_s']),tau_s=float(clock['time_s'])-ref['time'],
            native_id=int(nid),x_m=float(d['pos'][i,0]),y_m=float(d['pos'][i,1]),z_m=float(d['pos'][i,2]),p_Pa=float(d['p'][i]),
            fixed_P0_Pa=float(ref['p0all'][1805+i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),
            n=float(d['n'][i]),V_m2=float(d['V'][i]),rho_kg_m3=float(d['rho'][i]),k_m_s=float(d['k'][i]),speed_m_s=float(d['speed'][i]),
            NN_over_dp=float(d['nn'][i]),nearest_material_id=int(d['ids'][d['neighbor'][i]]),FS_type=int(d['fs'][i]),
            stored_theta_last_stage_s_inv=float(d['theta'][i]),PosDiv_saved=float(d['PosDiv'][i]),
            dx_from_PRE_mm=float(1000*d['du'][i,0]),dz_from_PRE_mm=float(1000*d['du'][i,2]),initial_material_layer=int(ref['layer'][i]))
        for j,axis in enumerate(('x','y','z')):r['v'+axis+'_m_s']=float(d['v'][i,j])
        for j,axis in enumerate(('xx','yy','zz')):r['effective_'+axis+'_Pa']=float(d['kk'][i,j]);r['total_'+axis+'_Pa']=float(d['total'][i,j])
        for j,axis in enumerate(('xy','yz','xz')):r['effective_and_total_'+axis+'_Pa']=float(d['ij'][i,j])
        rows.append(r)
    return rows


def analyze(bundle,ref):
    history,spacing,extrema,spatial=[],[],[],[];snapshots={};anchors={};last=None;worst=None;cells,a0=geometry.grid(ref)
    times=np.array([float(q['time_s']) for q in bundle['clocks']]);tail={width:int(np.searchsorted(times,times[-1]-width)) for width in (1.,.5)}
    for part in range(301):
        frame=typed.core.read22(bundle,part);d=metric.frame_data(frame,ref,last);d['theta']=np.array(frame['PoroThetaLastStage'][1805:,0]);d['PosDiv']=np.array(frame['PosDiv'][1805:,0])
        rows=metric.aggregate(LABEL,part,bundle['clocks'][part],d,ref,last)
        for row in rows:row['group']=GROUP
        history+=rows;allrow=rows[0]
        ratio,tri,mixed,bow,_=geometry.material.measures(d['pos'][:,(0,2)],cells,a0)
        shape=dict(group=GROUP,part=part,actual_time_s=allrow['actual_time_s'],tau_s=allrow['tau_s'],completed_step=allrow['completed_step'],
            min_area_ratio=float(ratio.min()),max_area_ratio=float(ratio.max()),nonpositive_area_cells=int((ratio<=0).sum()),
            chosen_diagonal_triangle_reversal=int(tri.sum()),mixed_turn_cells=int(mixed.sum()),self_cross_cells=int(bow.sum()),
            area_minus_meanJ_RMS=float(np.sqrt(np.mean((ratio-d['J'][cells].mean(axis=1))**2))),
            p_below_minus50kPa_nodes=int((d['p']<-50000).sum()),p_below_minus90kPa_nodes=int((d['p']<-90000).sum()))
        for key in ('NN_over_dp_min','NN_over_dp_q05','NN_over_dp_q95','unique_pairs_incident_lt_0p7dp','unique_pairs_incident_lt_0p5dp','unique_pairs_incident_lt_0p3dp'):shape[key]=allrow[key]
        spacing.append(shape)
        fields=(('p',d['p'],'Pa'),('native_p_minus_fixedP0',d['ex'],'Pa'),('speed',d['speed'],'m/s'),('kappa',d['kappa'],'1'),('J',d['J'],'1'),('n',d['n'],'1'),
                ('rho',d['rho'],'kg/m3'),('k',d['k'],'m/s'),('NN',d['nn'],'dp'),('effective_trace',d['kk'].sum(axis=1),'Pa'),('total_trace',d['total'].sum(axis=1),'Pa'))
        for name,values,unit in fields:
            for kind,i in (('min',int(values.argmin())),('max',int(values.argmax()))):
                extrema.append(dict(group=GROUP,part=part,actual_time_s=allrow['actual_time_s'],tau_s=allrow['tau_s'],field=name,extreme=kind,value=float(values[i]),unit=unit,
                    native_id=int(d['ids'][i]),x_m=float(d['pos'][i,0]),z_m=float(d['pos'][i,2]),FS_type=int(d['fs'][i]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),NN_over_dp=float(d['nn'][i])))
        if part in SELECTED:snapshots[part]=d;spatial+=spatial_rows(part,bundle['clocks'][part],d,ref)
        if worst is None or d['p'].min()<worst['d']['p'].min():worst=dict(part=part,d=d,clock=bundle['clocks'][part])
        if part in set(tail.values())|{300}:anchors[part]=d
        last=d
    need(len(history)==1806 and len(spacing)==301 and len(spatial)==30000 and len(extrema)==6622,'Exact301/5000/6cohort/extrema coverage required')
    late=[];end=anchors[300]
    for width,start in tail.items():
        a=anchors[start];du=end['pos']-a['pos'];row=dict(group=GROUP,requested_duration_s=width,start_part=start,end_part=300,actual_start_tau_s=times[start]-ref['time'],actual_end_tau_s=times[-1]-ref['time'],actual_duration_s=times[-1]-times[start],
            same_ID_movement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du**2,axis=1)))),same_ID_movement_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),
            top_material_settlement_change_mm=float(-1000*du[ref['top'],2].mean()),bottom_material_settlement_change_mm=float(-1000*du[ref['bottom'],2].mean()),
            start_speed_RMS_m_s=float(np.sqrt(np.mean(a['speed']**2))),end_speed_RMS_m_s=float(np.sqrt(np.mean(end['speed']**2))))
        for key in ('p','kappa','J','n','rho','k'):
            diff=end[key]-a[key];row[key+'_same_ID_RMS_change']=float(np.sqrt(np.mean(diff**2)));row[key+'_same_ID_maxabs_change']=float(np.abs(diff).max())
        ds=end['kk']-a['kk'];di=end['ij']-a['ij'];dt=end['total']-a['total']
        row['effective_stress_same_ID_Frobenius_RMS_change_Pa']=float(np.sqrt(np.mean(np.sum(ds**2,axis=1)+2*np.sum(di**2,axis=1))))
        row['total_stress_same_ID_Frobenius_RMS_change_Pa']=float(np.sqrt(np.mean(np.sum(dt**2,axis=1)+2*np.sum(di**2,axis=1))));late.append(row)
    pulse=spatial_rows(worst['part'],worst['clock'],worst['d'],ref)
    return history,spacing,extrema,spatial,late,snapshots,pulse


def paper_table(spatial):
    rows=[]
    for part in SELECTED:
        r=[q for q in spatial if q['part']==part];need(len(r)==5000,'All native materials at every display time required')
        p=np.array([q['p_Pa'] for q in r]);ex=np.array([q['native_p_minus_fixedP0_Pa'] for q in r]);kap=np.array([q['kappa'] for q in r])
        cap={30:.3,60:1.,120:2.}.get(part)
        rows.append(dict(group=GROUP,part=part,actual_time_s=r[0]['actual_time_s'],actual_tau_s=r[0]['tau_s'],nominal_tau_s=part*.01,actual_minus_nominal_s=r[0]['tau_s']-part*.01,
            Fig15_excess_reference=part in PAPER15,Fig16_total_pressure_reference=part in PAPER16,paper3s_reference=False,
            p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),native_p_minus_fixedP0_min_Pa=float(ex.min()),native_p_minus_fixedP0_max_Pa=float(ex.max()),
            excess_below_minus10kPa=int((ex<-10000).sum()),excess_above_plus10kPa=int((ex>10000).sum()),excess_below_fraction=float((ex<-10000).mean()),excess_above_fraction=float((ex>10000).mean()),
            total_below_minus10kPa=int((p<-10000).sum()),total_above_plus20kPa=int((p>20000).sum()),total_below_fraction=float((p<-10000).mean()),total_above_fraction=float((p>20000).mean()),
            native_kappa_min=float(kap.min()),native_kappa_max=float(kap.max()),paper_kappa_display_cap=cap,native_kappa_above_paper_display_count=int((kap>cap).sum()) if cap is not None else None,particle_center_front_m=max(q['x_m'] for q in r),
            paper_outline_digitized=False,paper_pressure_values_digitized=False,native_excess_is_established_paper_excess=False,native_kappa_is_reconstructed_paper_strain=False,difference_is_theory_error=False))
    return rows


def plots(history,spacing,spatial,paper,snapshots,pulse):
    files=[];whole=[q for q in history if q['cohort']=='all'];t=[q['tau_s'] for q in whole]
    charts=(('Signed pressure [kPa]',(('p_Pa_min',.001),('p_Pa_RMS',.001),('p_Pa_max',.001))),('Speed [m/s]',(('speed_m_s_RMS',1),('speed_m_s_max',1))),
        ('Stress Frobenius RMS [kPa]',(('effective_stress_Frobenius_Pa_RMS',.001),('total_stress_Frobenius_Pa_RMS',.001))),('Particle-center front [m]',(('x_front_m',1),)),
        ('Native kappa',(('kappa_max',1),)),('Native J',(('J_min',1),('J_max',1))),('Porosity',(('n_min',1),('n_max',1))),('Conductivity [m/s]',(('k_m_s_min',1),('k_m_s_max',1))),
        ('Mixture kinetic proxy [J/m]',(('mixture_kinetic_proxy_J_per_m',1),)),('Pressure quadratic proxy [J/m]',(('pressure_storage_quadratic_J_per_m',1),)),
        ('Signed pressure counts',(('negative_p_nodes',1),('FS23_nodes',1))),('Initial material settlement [mm]',()))
    fig,axes=plt.subplots(4,3,figsize=(15,13),layout='constrained')
    for ax,(title,series) in zip(axes.flat,charts):
        for key,scale in series:ax.plot(t,[q[key]*scale for q in whole],label=key)
        if not series:
            for cohort in ('fixed_initial_top','fixed_initial_bottom'):
                rr=[q for q in history if q['cohort']==cohort];ax.plot(t,[q['settlement_from_PRE_mm_mean'] for q in rr],label=cohort)
        ax.set(title=title,xlabel='Actual time after release [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.suptitle('C08 psi=+2.5 deg: all301 saves, all5000 material IDs; no fitted/theory acceptance')
    dest=Path(str(PREFIX)+'_history.png');fig.savefig(dest,dpi=165);plt.close(fig);files.append(dest)
    fig,axes=plt.subplots(3,3,figsize=(14,10),layout='constrained')
    panels=(('NN / dp',('NN_over_dp_min','NN_over_dp_q05','NN_over_dp_q95')),('Unique pairs, same declared cuts',('unique_pairs_incident_lt_0p7dp','unique_pairs_incident_lt_0p5dp','unique_pairs_incident_lt_0p3dp')),
        ('Nonpositive/invalid chord geometry [count]',('nonpositive_area_cells','self_cross_cells','chosen_diagonal_triangle_reversal','mixed_turn_cells')),('Chord area ratio',('min_area_ratio','max_area_ratio')),
        ('Area ratio minus mean native J [RMS]',('area_minus_meanJ_RMS',)),('Negative-pressure tail counts',('p_below_minus50kPa_nodes','p_below_minus90kPa_nodes')),
        ('Native J',('J_min','J_max')),('Native kappa',('kappa_max',)),('Material displacement RMS [mm]',('material_displacement_RMS_mm',)))
    for ax,(title,keys) in zip(axes.flat,panels):
        source=spacing if keys[0] in spacing[0] else whole
        for key in keys:ax.plot(t,[q[key] for q in source],label=key)
        ax.set(title=title,xlabel='Actual time after release [s]');ax.grid(alpha=.2);ax.legend(fontsize=6)
    fig.suptitle('Numerical quality observations; NN/negative-pressure counts are not new acceptance thresholds\nMaterial chords are not native J, exact strain, or tensile-instability proof')
    dest=Path(str(PREFIX)+'_spacing.png');fig.savefig(dest,dpi=165);plt.close(fig);files.append(dest)
    fig,axes=plt.subplots(2,3,figsize=(16,8),layout='constrained')
    for ci,(part,cap) in enumerate(zip(PAPER15,(.3,1.,2.))):
        d=snapshots[part];r=next(q for q in paper if q['part']==part)
        a=axes[0,ci];im=a.scatter(d['pos'][:,0],d['pos'][:,2],c=d['ex']*.001,s=4,cmap='jet',norm=Normalize(-10,10,clip=False),rasterized=True)
        a.set(title=f'Native p-fixed material P0; tau={r["actual_tau_s"]:.9f}s\nBelow/above display range: {r["excess_below_minus10kPa"]}/{r["excess_above_plus10kPa"]}')
        a=axes[1,ci];ki=a.scatter(d['pos'][:,0],d['pos'][:,2],c=d['kappa'],s=4,cmap='jet',norm=Normalize(0,cap,clip=False),rasterized=True)
        a.set(title=f'Native scalar kappa; display0..{cap:g}\nNative over-range count={int((d["kappa"]>cap).sum())}');fig.colorbar(ki,ax=a,extend='max',label='Native kappa (definition caveat)',shrink=.65)
    for ax in axes.flat:ax.set(xlabel='x [m]',ylabel='z [m]',xlim=(-.06,8.04),ylim=(-.06,2.18));ax.set_aspect('equal')
    fig.colorbar(im,ax=list(axes[0]),extend='both',label='Native float(p - fixed initial material P0) [kPa]',shrink=.65)
    fig.suptitle('Lian Fig15 display times: .3/.6/1.2s; source-relative actual times retained\nNative p-P0 and kappa are not reconstructed paper plastic excess/strain; no pressure/outline error claimed')
    dest=Path(str(PREFIX)+'_paper_fig15.png');fig.savefig(dest,dpi=175);plt.close(fig);files.append(dest)
    fig,axes=plt.subplots(1,3,figsize=(16,4),layout='constrained')
    for ax,part in zip(axes,PAPER16):
        d=snapshots[part];r=next(q for q in paper if q['part']==part);im=ax.scatter(d['pos'][:,0],d['pos'][:,2],c=d['p']*.001,s=4,cmap='jet',norm=Normalize(-10,20,clip=False),rasterized=True)
        ax.set(title=f'Actual tau={r["actual_tau_s"]:.9f}s\nBelow/above display: {r["total_below_minus10kPa"]}/{r["total_above_plus20kPa"]}',xlabel='x [m]',ylabel='z [m]',xlim=(-.06,8.04),ylim=(-.06,2.18));ax.set_aspect('equal')
    fig.colorbar(im,ax=list(axes),extend='both',label='Native total pore-water pressure [kPa]',shrink=.75)
    fig.suptitle('Lian Fig16 display times .01/.5/1.2s; native total p, not p-fixedP0\nNo Eq47 stabilization or exact paper-pressure/shape agreement is inferred')
    dest=Path(str(PREFIX)+'_paper_fig16.png');fig.savefig(dest,dpi=175);plt.close(fig);files.append(dest)
    fig,axes=plt.subplots(2,3,figsize=(16,8),layout='constrained');positions=np.concatenate([d['pos'] for d in snapshots.values()]);xmax=max(8.04,float(positions[:,0].max())+.04,max(q['x_m'] for q in pulse)+.04);zmax=max(2.18,float(positions[:,2].max())+.04,max(q['z_m'] for q in pulse)+.04)
    vals=np.concatenate([d['nn'] for d in snapshots.values()]);norm=Normalize(float(vals.min()),float(vals.max()))
    for ax,part in zip(list(axes.flat)[:4],(30,60,120,300)):
        d=snapshots[part];r=next(q for q in paper if q['part']==part);im=ax.scatter(d['pos'][:,0],d['pos'][:,2],c=d['nn'],s=4,cmap='viridis',norm=norm,rasterized=True)
        ax.set(title=f'True3D soil NN/dp; tau={r["actual_tau_s"]:.9f}s',xlabel='x [m]',ylabel='z [m]',xlim=(-.06,xmax),ylim=(-.06,zmax));ax.set_aspect('equal')
    fig.colorbar(im,ax=list(axes.flat)[:4],label='True3D nonself soil NN / dp',shrink=.65)
    point=min(pulse,key=lambda q:q['p_Pa']);p=np.array([q['p_Pa']*.001 for q in pulse]);pn=TwoSlopeNorm(vmin=float(p.min()),vcenter=0,vmax=float(p.max())) if p.min()<0<p.max() else Normalize(float(p.min()),float(p.max()))
    for ax,local in zip(list(axes.flat)[4:],(False,True)):
        im=ax.scatter([q['x_m'] for q in pulse],[q['z_m'] for q in pulse],c=p,s=5,cmap='coolwarm',norm=pn,rasterized=True);ax.scatter([point['x_m']],[point['z_m']],marker='*',s=80,c='yellow',edgecolors='black')
        ax.set(title=f'Global saved p minimum: ID{point["native_id"]}\nActual tau={point["tau_s"]:.9f}s',xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal')
        if local:ax.set_xlim(point['x_m']-4*H,point['x_m']+4*H);ax.set_ylim(point['z_m']-4*H,point['z_m']+4*H)
        else:ax.set_xlim(-.06,xmax);ax.set_ylim(-.06,zmax)
        fig.colorbar(im,ax=ax,label='Native signed p [kPa]',shrink=.65)
    fig.suptitle('Raw morphology/spacing and actual worst saved pressure; no smoothing, interpolation or p cutoff\nLocal rectangle is a view choice. 3s has no Fig15 pressure/shape reference.')
    dest=Path(str(PREFIX)+'_morphology_pulse.png');fig.savefig(dest,dpi=175);plt.close(fig);files.append(dest);return files


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Root full-read and separate offline authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Any complete/partial review is protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(metric.__file__),Path(metric.previous.__file__),Path(typed.__file__),Path(typed.core.__file__),Path(seals.__file__),Path(geometry.__file__),Path(geometry.material.__file__),PAPER_MD,PAPER_PNG)]
    result=dict(stage=TAG,passed=False,analysis_complete=False,physical_acceptance=False,solver_invocations=0,reader_invocations=0,VTK_invocations=0,GPU_actions=0,SHA_scans=0,automatic_next_job=False)
    try:
        run,bundle,ref,cohorts=inputs(consumed);history,spacing,extrema,spatial,late,snapshots,pulse=analyze(bundle,ref);paper=paper_table(spatial);files=[]
        for name,rows in (('history',history),('cohorts',cohorts),('spacing',spacing),('extrema',extrema),('spatial',spatial),('pulse',pulse),('late',late),('paper',paper)):
            dest=Path(str(PREFIX)+'_'+name+'.csv');metric.write(dest,rows);files.append(dest)
        files+=plots(history,spacing,spatial,paper,snapshots,pulse);need(all(stat(q['path'])==q for q in consumed),'Immutable native/source/reference binding changed')
        whole=[q for q in history if q['cohort']=='all'];point=min(pulse,key=lambda q:q['p_Pa'])
        result.update(passed=True,analysis_complete=True,group=GROUP,actual_samples=301,soil_IDs=5000,source_reference_frames_read=[0,1000],native_frames_read_once=301,
            original_native_guards_unchanged=True,dedicated_HG_review=stat(HG),HG_review_recomputed=False,own_prefix_compared=False,psi0_prefix_borrowed=False,HG0_comparison=False,old_psi0_payload_read=False,
            history_rows=len(history),spatial_rows=len(spatial),pulse_rows=len(pulse),extrema_rows=len(extrema),selected_parts=list(SELECTED),
            actual_end_tau_s=whole[-1]['tau_s'],final_all_material_summary=whole[-1],actual_global_saved_pressure_minimum=point,late_same_material_changes=late,
            all_saved_nonpositive_area_cells=sum(q['nonpositive_area_cells'] for q in spacing),all_saved_self_cross_cells=sum(q['self_cross_cells'] for q in spacing),
            whole_window_minimum_NN_over_dp=min(q['NN_over_dp_min'] for q in spacing),material_quads=4851,local_D2min_computed=False,material_chord_geometry_is_native_J=False,
            observed_loop_TSimul_s=float(run['summary']['TSimul']),controlled_benchmark=False,paper_Fig15_times=[.3,.6,1.2],paper_Fig16_times=[.01,.5,1.2],paper3s_reference=False,
            native_excess_is_established_paper_excess=False,native_kappa_is_reconstructed_paper_strain=False,paper_pressure_or_outline_digitized=False,all_pressure_signs_extrema_overrange_retained=True,
            all_current_FS23_negative_pressure_observations=sum(q['negative_p_nodes'] for q in history if q['cohort']=='current_FS23'),
            no_pressure_clipping_or_Darcy_cause_inferred=True,pressure_storage_is_fluid_mass=False,kinetic_proxy_is_complete_coupled_energy=False,reaction_J_Darcy_closed=False,
            half_or_theory_acceptance=False,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    need(result['passed'],result.get('first_failure','Offline physical review failed; preserve partials'))


if __name__=='__main__':main()
