"""Offline full301 C-quality-retry/HG review; no BI4 reader, solver or VTK."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_lstar_window_review_r1 as metric
import c08_h18_hg_failed99_review_r1 as sealed
import c08_h18_material_map_r1 as material

T,L,typed=metric.T,metric.L,metric.core
need,read,stat,bind=metric.need,metric.read,metric.stat,metric.bind
TAG='c08_h18_wall_c_retry_full3_review_r1'
RUN_TAG='c08_h18_wall_c_retry_full3_GPU_r2'
RUN=L/(RUN_TAG+'.run.json');NATIVE=L/(RUN_TAG+'.native_r1.check.json');EXPORTS=L/(RUN_TAG+'.native_r1.exports.json')
NOTE=T/'notes'/(TAG+'.md');CHECK=L/(TAG+'.check.json');PREFIX=T/'figures'/TAG
BASE=L/'c08_h18_as03n255_full3_review_r1.check.json';BASENAME='c08_h18_as03n255_full3_review_r1'
CASES=('Retained HG0','C-quality retry + HG')
SELECTED=(30,60,120,300);REQUESTS=(.3,.6,1.2,3.);DP=.04
# Mapping of scientifically identical global definitions; differences of these
# summaries are not pointwise301 field errors or half-step/theory errors.
COMMON={'p_Pa_RMS':'p_RMS_Pa','p_Pa_min':'p_min_Pa','p_Pa_max':'p_max_Pa','p_Pa_mean':'p_mean_Pa',
 'native_p_minus_fixedP0_Pa_RMS':'native_p_minus_fixedP0_RMS_Pa','speed_m_s_RMS':'velocity_RMS_m_s',
 'speed_m_s_max':'max_speed_m_s','kappa_max':'max_kappa','J_min':'min_J','J_max':'max_J','n_min':'min_n','n_max':'max_n',
 'rho_kg_m3_min':'min_rho','rho_kg_m3_max':'max_rho','k_m_s_min':'min_k_m_s','k_m_s_max':'max_k_m_s',
 'effective_stress_Frobenius_Pa_RMS':'effective_stress_Frobenius_RMS_Pa',
 'total_stress_Frobenius_Pa_RMS':'total_stress_Frobenius_RMS_Pa','x_front_m':'front_x_m',
 'NN_over_dp_min':'NN_min_over_dp','NN_over_dp_q05':'NN_q05_over_dp','NN_over_dp_q95':'NN_q95_over_dp',
 'unique_pairs_incident_lt_0p7dp':'pairs_r_lt_0p7dp','mixture_kinetic_proxy_J_per_m':'current_mixture_KE_J_per_m',
 'material_displacement_RMS_mm':'material_displacement_RMS_mm'}


def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def take(path,consumed):consumed.append(stat(path));return read(path)
def bound(ref,consumed):bind(ref);consumed.append(ref);return Path(ref['path'])


def inputs(consumed):
    run=take(RUN,consumed);native=take(NATIVE,consumed);exports=take(EXPORTS,consumed)
    need(run['passed'] and run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==0
         and run['solver_identity_matches'] and run['actual_steps']==2600000 and run['saved_frames']==301
         and run['consumed_stats_unchanged'],'Actual completed full301 solver required')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','native_profile'):
        bound(run[key],consumed)
    need(native['passed'] and native['reader_invocations']==1 and native['original_safety_passed']
         and native['consumed_stats_unchanged'] and exports['passed'] and exports['original_unique_read']==stat(NATIVE)
         and exports['original_call']==native['actual_call'] and exports['header']==[6805,22,301]
         and exports['new_root_snapshot_after_reader_completion'] and exports['not_claimed_original_reader_receipt_seal'],
         'One genuine native read plus separately labelled root export snapshot required')
    for ref in (run['actual_call'],native['actual_call']):metric.owned(read(bound(ref,consumed)))
    sealed.sealed(native,RUN,consumed)
    nc=read(native['actual_call']['path']);reader=take(bound(native['reader_build'],consumed),consumed)
    need(reader['passed'] and Path(nc['program']).resolve()==bound(reader['program'],consumed).resolve(),
         'Actual unique reader executable binding differs')
    args=nc['arguments'];native_root=Path(native['native_completion']['path']).parent
    need(len(args)==8 and args[:3]==['--receiver','formal','psi0']
         and Path(args[3]).resolve()==(Path(run['output'])/'data').resolve()
         and Path(args[4]).resolve()==Path(run['source_pre_file']['path']).resolve()
         and Path(args[5]).resolve()==Path(run['planned_steps']['path']).resolve()
         and Path(args[6]).resolve()==Path(run['native_profile']['path']).resolve()
         and Path(args[7]).resolve()==native_root.resolve(),'Actual unique formal DATA/PRE/plan/profile/output binding differs')
    done=take(bound(native['native_completion'],consumed),consumed)
    need(done['passed'] and done['group']=='psi0' and done['samples']==301 and done['completed_steps']==2600000
         and done['actual_end_s']==12.999999999592434 and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805
         and done['soil_IDs']==5000 and done['ledger_checks']==1505000 and done['P0_bits_checks']==2048305
         and done['fixed_marker_checks']==543305 and done['nonempty_signed_intervals']==301
         and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
         and not done['native_rewritten'],'All original native coverage/clock/signed guards must pass')
    root=Path(native['native_completion']['path']).parent
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):sealed.sealed(exports,root/leaf,consumed,'files')
    bundle=typed.typed(root,6805,301,consumed);plan=table(bound(run['planned_steps'],consumed))
    need(len(plan)==301,'Whole original301 launch plan required')
    base=take(BASE,consumed);need(base['analysis_complete'] and base['consumed_stats_unchanged'],'Sealed HG0 full301 analysis required')
    old={}
    for key in ('history','material_geometry','snapshots'):
        path=T/'figures'/(BASENAME+'_'+key+'.csv');sealed.sealed(base,path,consumed,'files');old[key]=table(path)
    need(len(old['history'])==len(old['material_geometry'])==301 and len(old['snapshots'])==30000,'HG0 CSV coverage differs')
    for part,(clock,p,h) in enumerate(zip(bundle['clocks'],plan,old['history'])):
        need(int(clock['part'])==int(p['part'])==int(h['part'])==part and int(clock['completed_step'])==int(p['completed_step'])==int(h['completed_step'])
             and int(clock['saved_step'])==int(p['saved_step']) and metric.bits(clock['time_s'])==metric.bits(p['time_s'])==metric.bits(h['time_s'])
             and metric.bits(clock['dt_s'])==metric.bits(p['dt_s'])==metric.bits(.000005)
             and clock['dterror_interval_empty']=='0','All301 actual matched clocks/steps required; no interpolation')
    source=take(bound(run['source_native'],consumed),consumed)
    need(source['passed'] and source['certified_PRE'] and source['samples']==1001 and source['same_material_plastic_PRE'],'Original same-material PRE reference required')
    prior=take(L/'c08_h18_hg_cached_physical_r1.check.json',consumed)
    need(prior['passed'] and prior['consumed_stats_unchanged'],'Existing source-export seal required')
    sr=Path(run['source_native']['path']).parent
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):sealed.sealed(prior,sr/leaf,consumed)
    ref,cohorts=metric.previous.source_reference(typed.typed(sr,7060,1001,consumed),source)
    need(ref['time']==done['source_actual_time_s']==run['actual_source_time_s'],'Actual common source reference time differs')
    papercheck=take(L/'upl_c08_lian14_outline_r1.check.json',consumed)
    need(papercheck['passed'] and papercheck['analysis_completed'] and not papercheck['pressure_values_sampled'],'Existing descriptive Fig14 outline required')
    paper={}
    for key in ('outline','summary'):
        path=T/'figures'/('upl_c08_lian14_outline_r1_'+key+'.csv');sealed.sealed(papercheck,path,consumed,'outputs');paper[key]=table(path)
    phasepath=L/'c08_h18_wall_c_retry_full3_hg_review_r1.check.json';phase=take(phasepath,consumed)
    need(phase['passed'] and phase['analysis_complete'] and phase['source_run']==stat(RUN)
         and phase['source_native_check']==stat(NATIVE) and phase['native_exports_snapshot']==stat(EXPORTS)
         and phase['own_prefix']['shared_records']==4 and phase['own_prefix']['all22_and_time_payload_first4_exact']
         and phase['own_prefix']['all_first4_raw_clock_signed_rows_exact']
         and phase['HG']['reviewed_rows']==602 and phase['HG']['saved_phase_pairs']==301
         and phase['HG']['own_first8_HG_rows_exact'] and phase['HG']['policy_equal']
         and phase['HG']['all_original_saved_domain_clock_cache_lifecycle_gates'],
         'Separately completed own-prefix and602-phase HG review bound to this run required')
    return run,bundle,ref,cohorts,old,paper,stat(phasepath)


def grid(ref):
    initial=ref['initial'][:,(0,2)];xs,zs=np.unique(initial[:,0]),np.unique(initial[:,1]);g=np.full((50,100),-1,dtype=int)
    need(len(xs)==100 and len(zs)==50,'Original material100x50 grid required')
    for i,(x,z) in enumerate(zip(np.searchsorted(xs,initial[:,0]),np.searchsorted(zs,initial[:,1]))):need(g[z,x]==-1,'Duplicate initial material grid node');g[z,x]=i
    need((g>=0).all(),'All5000 material nodes required');cells=np.stack((g[:-1,:-1],g[:-1,1:],g[1:,1:],g[1:,:-1]),axis=-1).reshape(-1,4)
    local=initial[cells]-initial[cells][:,:1];a0=.5*np.sum(material.cross(local,np.roll(local,-1,axis=1)),axis=1)
    need(len(cells)==4851 and np.allclose(a0,DP**2,rtol=0,atol=1e-15),'Original positive4851 quad reference required');return cells,a0


def analyze(bundle,ref,old,paper):
    history,matched,spacing,spatial=[],[],[],[];snapshots={};last=None;cells,a0=grid(ref)
    oldsp={(int(q['part']),int(q['native_id'])):q for q in old['snapshots']}
    times=np.array([float(q['time_s']) for q in bundle['clocks']]);anchors={};tail={width:int(np.searchsorted(times,times[-1]-width)) for width in (1.,.5)}
    for part in range(301):
        frame=typed.core.read22(bundle,part);d=metric.frame_data(frame,ref,last)
        rows=metric.aggregate(CASES[1],part,bundle['clocks'][part],d,ref,last)
        for row in rows:
            mask=d['masks'][row['cohort']];row['saved_interval_material_motion_RMS_mm']=None if last is None or not mask.any() else float(1000*np.sqrt(np.mean(np.sum((d['pos'][mask]-last['pos'][mask])**2,axis=1))))
        history+=rows;allrow=rows[0];h=old['history'][part];clock=dict(part=part,actual_time_s=allrow['actual_time_s'],tau_s=allrow['tau_s'])
        pair=dict(**clock,completed_step=allrow['completed_step'])
        for key,bkey in COMMON.items():pair['new_'+key]=allrow[key];pair['HG0_'+key]=float(h[bkey]);pair['difference_of_'+key]=allrow[key]-float(h[bkey])
        for cohort,bkey in (('fixed_initial_top','top_material_settlement_mm'),('fixed_initial_bottom','bottom_material_settlement_mm')):
            val=next(q['settlement_from_PRE_mm_mean'] for q in rows if q['cohort']==cohort);pair['new_'+bkey]=val;pair['HG0_'+bkey]=float(h[bkey]);pair['difference_of_'+bkey]=val-float(h[bkey])
        ratio,tri,mixed,bow,_=material.measures(d['pos'][:,(0,2)],cells,a0);geom=old['material_geometry'][part]
        need(float(geom['time_s'])==clock['actual_time_s'],'Material-geometry actual clocks differ')
        shape=dict(**clock,min_area_ratio=float(ratio.min()),max_area_ratio=float(ratio.max()),nonpositive_area_cells=int((ratio<=0).sum()),chosen_diagonal_triangle_reversal=int(tri.sum()),mixed_turn_cells=int(mixed.sum()),self_cross_cells=int(bow.sum()),area_minus_meanJ_RMS=float(np.sqrt(np.mean((ratio-d['J'][cells].mean(axis=1))**2))))
        for key in ('NN_over_dp_min','NN_over_dp_q05','NN_over_dp_q95','unique_pairs_incident_lt_0p7dp','unique_pairs_incident_lt_0p5dp','unique_pairs_incident_lt_0p3dp'):shape[key]=allrow[key]
        for key in ('min_area_ratio','max_area_ratio','nonpositive_area_cells','self_cross_cells'):pair['new_'+key]=shape[key];pair['HG0_'+key]=float(geom[key])
        spacing.append(shape);matched.append(pair)
        if part in SELECTED:
            fixed=np.array(frame['Posd'][frame['Idp'][:,0]<2060]);need(fixed.shape==(1805,3),'Every selected fixed boundary retained');snapshots[part]=(d,fixed)
            for i,nid in enumerate(d['ids']):
                b=oldsp[(part,int(nid))];need(float(b['time_s'])==clock['actual_time_s'],'Selected5000-ID HG0 snapshot clocks differ')
                row=dict(**clock,completed_step=allrow['completed_step'],native_id=int(nid),x_m=float(d['pos'][i,0]),y_m=float(d['pos'][i,1]),z_m=float(d['pos'][i,2]),p_Pa=float(d['p'][i]),fixed_P0_Pa=float(ref['p0all'][1805+i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),n=float(d['n'][i]),V_m2=float(d['V'][i]),rho_kg_m3=float(d['rho'][i]),k_m_s=float(d['k'][i]),speed_m_s=float(d['speed'][i]),NN_over_dp=float(d['nn'][i]),nearest_material_id=int(d['ids'][d['neighbor'][i]]),dx_from_PRE_mm=float(1000*d['du'][i,0]),dz_from_PRE_mm=float(1000*d['du'][i,2]),HG0_x_m=float(b['x_m']),HG0_z_m=float(b['z_m']),HG0_p_Pa=float(b['p_Pa']),selected_same_ID_delta_p_Pa=float(d['p'][i])-float(b['p_Pa']),HG0_native_p_minus_fixedP0_Pa=float(b['native_p_minus_fixedP0_Pa']),HG0_kappa=float(b['kappa']),HG0_J=float(b['J']))
                for j,axis in enumerate(('x','y','z')):row['v'+axis+'_m_s']=float(d['v'][i,j])
                for j,axis in enumerate(('xx','yy','zz')):row['effective_'+axis+'_Pa']=float(d['kk'][i,j]);row['total_'+axis+'_Pa']=float(d['total'][i,j])
                for j,axis in enumerate(('xy','yz','xz')):row['effective_and_total_'+axis+'_Pa']=float(d['ij'][i,j])
                spatial.append(row)
        if part in set(tail.values())|{300}:anchors[part]=d
        last=d
    need(len(history)==1806 and len(matched)==len(spacing)==301 and len(spatial)==20000,'All301/5000/6cohort and four complete snapshots required')
    late=[];end=anchors[300]
    for width,start in tail.items():
        a=anchors[start];du=end['pos']-a['pos'];row=dict(requested_duration_s=width,start_part=start,end_part=300,actual_start_tau_s=times[start]-ref['time'],actual_end_tau_s=times[-1]-ref['time'],actual_duration_s=times[-1]-times[start],same_ID_movement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du**2,axis=1)))),same_ID_movement_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),top_material_settlement_change_mm=float(-1000*du[ref['top'],2].mean()),bottom_material_settlement_change_mm=float(-1000*du[ref['bottom'],2].mean()),start_speed_RMS_m_s=float(np.sqrt(np.mean(a['speed']**2))),end_speed_RMS_m_s=float(np.sqrt(np.mean(end['speed']**2))))
        for key in ('p','kappa','J','n','rho','k'):
            diff=end[key]-a[key];row[key+'_same_ID_RMS_change']=float(np.sqrt(np.mean(diff**2)));row[key+'_same_ID_maxabs_change']=float(np.abs(diff).max())
        ds=end['kk']-a['kk'];di=end['ij']-a['ij'];dt=end['total']-a['total']
        row['effective_stress_same_ID_Frobenius_RMS_change_Pa']=float(np.sqrt(np.mean(np.sum(ds**2,axis=1)+2*np.sum(di**2,axis=1))))
        row['total_stress_same_ID_Frobenius_RMS_change_Pa']=float(np.sqrt(np.mean(np.sum(dt**2,axis=1)+2*np.sum(di**2,axis=1))))
        late.append(row)
    return history,matched,spacing,spatial,late,snapshots


def paper_rows(spatial,paper):
    out=[]
    for request,part in zip(REQUESTS,SELECTED):
        selected=[q for q in spatial if q['part']==part];need(len(selected)==5000,'Every paper/extension selected material ID required')
        for case,pkey,xkey in ((CASES[0],'HG0_native_p_minus_fixedP0_Pa','HG0_x_m'),(CASES[1],'native_p_minus_fixedP0_Pa','x_m')):
            ex=np.array([q[pkey] for q in selected]);front=max(q[xkey] for q in selected)
            reference=next((q for q in paper['summary'] if float(q['requested_tau_s'])==request),None)
            out.append(dict(case=case,requested_tau_s=request,part=part,actual_tau_s=selected[0]['tau_s'],actual_minus_requested_s=selected[0]['tau_s']-request,native_IDs=5000,native_p_minus_fixedP0_min_Pa=float(ex.min()),native_p_minus_fixedP0_max_Pa=float(ex.max()),below_minus10kPa=int((ex<-10000).sum()),above_plus10kPa=int((ex>10000).sum()),below_fraction=float((ex<-10000).mean()),above_fraction=float((ex>10000).mean()),native_particle_center_front_m=front,paper_reference_available=reference is not None,paper_visible_front_m=float(reference['front_colored_extent_m']) if reference else None,center_minus_paper_visible_front_m=front-float(reference['front_colored_extent_m']) if reference else None,paper_raster_allowance_m=float(reference['front_digitization_allowance_m']) if reference else None,separate_center_representation_scale_m=.02,native_excess_is_established_paper_excess=False,difference_is_theory_error=False))
    return out


def plots(matched,spacing,spatial,paperrows,paper):
    files=[]
    groups=(('pressure_motion',(('p_Pa_RMS','Pressure RMS [kPa]',.001),('p_Pa_min','Minimum signed pressure [kPa]',.001),('p_Pa_max','Maximum pressure [kPa]',.001),('speed_m_s_RMS','Speed RMS [m/s]',1),('x_front_m','Particle-center front [m]',1),('top_material_settlement_mm','Initial top material settlement [mm]',1),('bottom_material_settlement_mm','Initial bottom material settlement [mm]',1),('mixture_kinetic_proxy_J_per_m','Mixture kinetic proxy [J/m]',1))),
            ('material_spacing',(('NN_over_dp_min','Minimum NN / dp',1),('NN_over_dp_q95','NN q95 / dp',1),('unique_pairs_incident_lt_0p7dp','Unique soil pairs <0.7dp',1),('nonpositive_area_cells','Nonpositive material chord areas',1),('J_min','Minimum stored J',1),('J_max','Maximum stored J',1),('kappa_max','Maximum kappa',1),('total_stress_Frobenius_Pa_RMS','Total stress Frobenius RMS [kPa]',.001))))
    for suffix,panels in groups:
        fig,axes=plt.subplots(4,2,figsize=(13,13),layout='constrained')
        for ax,(key,title,scale) in zip(axes.flat,panels):
            for prefix,label in (('HG0_',CASES[0]),('new_',CASES[1])):ax.plot([q['tau_s'] for q in matched],[q[prefix+key]*scale for q in matched],label=label)
            ax.set(title=title,xlabel='Actual time after release [s]');ax.grid(alpha=.2)
        axes[0,0].legend(fontsize=9);fig.suptitle('C08 psi0: actual full301 history; different operators, no half/theory error claim',fontsize=13)
        path=Path(str(PREFIX)+'_'+suffix+'.png');fig.savefig(path,dpi=165);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(2,3,figsize=(17,7.5),layout='constrained');norm=Normalize(-10,10,clip=False)
    for ri,(case,key,x,z) in enumerate(((CASES[0],'HG0_native_p_minus_fixedP0_Pa','HG0_x_m','HG0_z_m'),(CASES[1],'native_p_minus_fixedP0_Pa','x_m','z_m'))):
        for ci,part in enumerate(SELECTED[:3]):
            rows=[q for q in spatial if q['part']==part];ax=axes[ri,ci];p=next(q for q in paperrows if q['case']==case and q['part']==part)
            image=ax.scatter([q[x] for q in rows],[q[z] for q in rows],c=[q[key]*.001 for q in rows],s=4,cmap='jet',norm=norm,rasterized=True)
            ax.set(title=f'{case}; actual tau={rows[0]["tau_s"]:.9f}s\nBelow/above display range: {p["below_minus10kPa"]}/{p["above_plus10kPa"]}',xlim=(-.06,8.04),ylim=(-.06,2.18),xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal')
    fig.colorbar(image,ax=list(axes.flat),extend='both',label='Native float(p - fixed initial P0) [kPa]',shrink=.8)
    fig.suptitle('Lian Fig14 nominal .3/.6/1.2 s comparison display',fontsize=13);fig.supxlabel('Native p-P0 is not established as paper plastic excess. Jet-style approximation, fixed +/-10 kPa.\nAll values/over-range fractions retained; no smoothing, interpolation or exact paper-pressure error.',fontsize=9)
    path=Path(str(PREFIX)+'_paper_excess.png');fig.savefig(path,dpi=175);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(2,4,figsize=(18,8),layout='constrained');lo=min(q['NN_over_dp'] for q in spatial);hi=max(q['NN_over_dp'] for q in spatial);norm=Normalize(lo,hi)
    # HG0 NN fields were not exported in the old selected CSV; its raw morphology
    # is drawn with a single colour instead of inventing a spacing field.
    for ci,part in enumerate(SELECTED):
        rows=[q for q in spatial if q['part']==part]
        axes[0,ci].scatter([q['HG0_x_m'] for q in rows],[q['HG0_z_m'] for q in rows],s=3,c='C0',rasterized=True)
        image=axes[1,ci].scatter([q['x_m'] for q in rows],[q['z_m'] for q in rows],c=[q['NN_over_dp'] for q in rows],s=4,cmap='viridis',norm=norm,rasterized=True)
        for ri,case in enumerate(CASES):axes[ri,ci].set(title=f'{case}; actual tau={rows[0]["tau_s"]:.9f}s',xlim=(-.06,max(8.04,max(q['x_m'] for q in spatial)+.04)),ylim=(-.06,2.18),xlabel='x [m]',ylabel='z [m]');axes[ri,ci].set_aspect('equal')
    fig.colorbar(image,ax=list(axes[1]),label='New candidate: true3D soil NN / dp',shrink=.8);fig.suptitle('Raw morphology and new-candidate spacing; 3s is a model extension, no Fig14 reference',fontsize=13)
    path=Path(str(PREFIX)+'_morphology_NN.png');fig.savefig(path,dpi=170);plt.close(fig);files.append(path)
    fig,axes=plt.subplots(1,3,figsize=(17,4.6),layout='constrained')
    for ax,request,part in zip(axes,REQUESTS[:3],SELECTED[:3]):
        rows=[q for q in spatial if q['part']==part]
        for label,x,z,color in ((CASES[0],'HG0_x_m','HG0_z_m','C0'),(CASES[1],'x_m','z_m','C1')):ax.scatter([q[x] for q in rows],[q[z] for q in rows],s=3,c=color,alpha=.55,label=label,rasterized=True)
        edge=[q for q in paper['outline'] if float(q['requested_tau_s'])==request];ax.scatter([float(q['x_m']) for q in edge],[float(q['z_m']) for q in edge],s=3,c='k',label='Paper visible bulk edge',rasterized=True)
        ax.set(title=f'Fig14 nominal {request:g}s; actual tau={rows[0]["tau_s"]:.9f}s',xlim=(-.06,8.04),ylim=(-.06,2.18),xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal');ax.legend(fontsize=8)
    fig.supxlabel('Raster reading scale about +/-0.036m and separate particle-center representation scale .02m.\nNo outline/time fit, pressure digitization or exact theory-error claim.',fontsize=9)
    path=Path(str(PREFIX)+'_paper_outline.png');fig.savefig(path,dpi=175);plt.close(fig);files.append(path)
    return files


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Separate root offline execution authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing full/partial analysis protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(metric.__file__),Path(metric.previous.__file__),Path(typed.__file__),Path(typed.core.__file__),Path(material.__file__),Path(sealed.__file__))]
    result=dict(stage=TAG,passed=False,analysis_complete=False,physical_acceptance=False,solver_invocations=0,native_decodes=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        run,bundle,ref,cohorts,old,paper,prefix=inputs(consumed)
        history,matched,spacing,spatial,late,snapshots=analyze(bundle,ref,old,paper);pr=paper_rows(spatial,paper)
        summary=[]
        for label,prefixlabel in zip(CASES,('HG0_','new_')):
            row=dict(case=label,actual_end_tau_s=matched[-1]['tau_s'],loop_TSimul_s=float(run['summary']['TSimul']) if prefixlabel=='new_' else None,observed_timing_not_controlled_benchmark=True)
            for key in COMMON:row['final_'+key]=matched[-1][prefixlabel+key]
            for key,select in (('p_Pa_min',min),('p_Pa_max',max),('speed_m_s_max',max),('kappa_max',max),('NN_over_dp_min',min)):
                observed=select(matched,key=lambda q:q[prefixlabel+key]);row['observed_'+key]=observed[prefixlabel+key];row['observed_'+key+'_tau_s']=observed['tau_s'];row['observed_'+key+'_part']=observed['part']
            summary.append(row)
        files=[]
        for suffix,rows in (('history',history),('cohorts',cohorts),('matched',matched),('spacing',spacing),('spatial',spatial),('paper',pr),('late',late),('summary',summary)):
            path=Path(str(PREFIX)+'_'+suffix+'.csv');metric.write(path,rows);files.append(path)
        files+=plots(matched,spacing,spatial,pr,paper)
        need(all(stat(q['path'])==q for q in consumed),'Consumed immutable evidence changed during offline analysis')
        result.update(passed=True,analysis_complete=True,consumed_stats_unchanged=True,actual_samples=301,soil_IDs=5000,
            new_native_frames_read_once=301,old_HG0_native_frames_read=0,source_reference_frames_read=[0,1000],
            original_native_guards_unchanged=True,dedicated_HG_review=prefix,own_prefix_recomputed_here=False,history_rows=len(history),matched_rows=len(matched),
            spacing_rows=len(spacing),spatial_rows=len(spatial),cohort_rows=len(cohorts),selected_parts=list(SELECTED),
            selected_actual_tau_s=[next(q['tau_s'] for q in matched if q['part']==part) for part in SELECTED],
            fixed_initial_material_top_bottom=True,material_quads=4851,local_D2min_computed=False,
            material_chord_geometry_is_native_J=False,NN_is_tensile_instability_proof=False,
            native_p_minus_fixedP0_is_established_paper_excess=False,paper_pressure_values_digitized=False,
            pressure_palette='jet-style approximation',paper_display_kPa=[-10,10],paper3s_reference=False,
            all_overrange_values_and_fractions_retained=True,matched301_summary_differences_are_pointwise_errors=False,
            storage_is_fluid_mass=False,mixture_kinetic_proxy_is_full_coupled_energy=False,
            reaction_J_Darcy_closed=False,half_or_theory_acceptance=False,HG_correctness_proven=False,
            root_export_snapshot_is_original_reader_receipt_seal=False,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    need(result['passed'],result.get('first_failure','Offline review failed; preserve partial outputs'))


if __name__=='__main__':main()
