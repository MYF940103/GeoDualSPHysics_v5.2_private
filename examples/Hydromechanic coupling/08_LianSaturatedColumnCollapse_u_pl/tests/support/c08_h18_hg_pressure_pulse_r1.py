"""Read-only diagnostic of41 existing typed saves around the saved pressure pulse."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
import c08_h18_storage_review_r2 as typed
import c08_h18_lstar_window_review_r1 as metric
import c08_h18_hg_failed99_review_r1 as seal

T,L=typed.T,typed.L
need,read,stat,bind=typed.need,typed.read,typed.stat,typed.bind
TAG='c08_h18_hg_pressure_pulse_r1';RUN_TAG='c08_h18_wall_c_retry_full3_GPU_r2'
NOTE=T/'notes'/(TAG+'.md');CHECK=L/(TAG+'.check.json');PREFIX=T/'figures'/TAG
NATIVE=L/(RUN_TAG+'.native_r1.check.json');EXPORTS=L/(RUN_TAG+'.native_r1.exports.json')
PHYSICAL=L/'c08_h18_wall_c_retry_full3_review_r1.check.json'
PARTS=tuple(range(95,136));PULSE=112;DP=.04;H=float(np.float32(.072))


def table(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


def inputs(consumed):
    native,exports,physical=map(read,(NATIVE,EXPORTS,PHYSICAL));consumed.extend(stat(q) for q in (NATIVE,EXPORTS,PHYSICAL))
    need(native['passed'] and native['reader_invocations']==1 and native['original_safety_passed']
         and native['consumed_stats_unchanged'] and exports['passed'] and exports['original_unique_read']==stat(NATIVE)
         and exports['original_call']==native['actual_call'] and exports['header']==[6805,22,301]
         and exports['new_root_snapshot_after_reader_completion'] and exports['not_claimed_original_reader_receipt_seal']
         and physical['passed'] and physical['analysis_complete'] and physical['consumed_stats_unchanged'],
         'One completed native and the existing full physical review/export snapshot required')
    call=read(native['actual_call']['path']);typed.owned(call);consumed.append(bind(native['actual_call']))
    done=read(native['native_completion']['path']);consumed.append(bind(native['native_completion']))
    need(done['passed'] and done['samples']==301 and done['completed_steps']==2600000
         and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805
         and done['nonempty_signed_intervals']==301 and done['max_signed_dterror_s']<=1e-14
         and not done['native_rewritten'],'Original whole-run native guards must remain passed')
    root=Path(native['native_completion']['path']).parent
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):seal.sealed(exports,root/leaf,consumed,'files')
    bundle=typed.typed(root,6805,301,consumed)
    cohorts=T/'figures/c08_h18_wall_c_retry_full3_review_r1_cohorts.csv';seal.sealed(physical,cohorts,consumed,'files')
    rows=table(cohorts);need(len(rows)==5000 and [int(q['native_id']) for q in rows]==list(range(2060,7060)),
                            'All5000 original material cohorts required')
    bottom=np.array([q['fixed_initial_bottom_ID']=='True' for q in rows]);need(int(bottom.sum())==100,'Original fixed initial bottom100 IDs required')
    return bundle,bottom,float(done['source_actual_time_s'])


def data(frame):
    need(np.array_equal(frame['Idp'][1805:,0],np.arange(2060,7060)),'All5000 fixed soil identities required')
    p=frame['PorePress'][1805:,0].astype(float);pos=np.array(frame['Posd'][1805:]);v=frame['Vel'][1805:].astype(float)
    kk=np.array(frame['SigmaState_kk'][1805:]);ij=np.array(frame['SigmaState_ij'][1805:]);tensor=np.zeros((5000,3,3))
    for j in range(3):tensor[:,j,j]=kk[:,j]
    for j,(a,b) in enumerate(((0,1),(1,2),(0,2))):tensor[:,a,b]=tensor[:,b,a]=ij[:,j]
    effective=np.linalg.eigvalsh(tensor);total=effective-p[:,None]
    nn,neighbor,_,_=metric.near(pos)
    return dict(p=p,pos=pos,v=v,speed=np.linalg.norm(v,axis=1),nn=nn,neighbor=neighbor,
        J=np.array(frame['PoroVolumeRatio'][1805:,0]),n=np.array(frame['PoroPorosity'][1805:,0]),
        theta=np.array(frame['PoroThetaLastStage'][1805:,0]),kappa=frame['Kplastic'][1805:,0].astype(float),
        FS=frame['FSType'][1805:,0],PosDiv=frame['PosDiv'][1805:,0].astype(float),
        effective=effective,total=total,kk=kk,ij=ij,p0=frame['PorePress0'][1805:,0].astype(float),
        ex=frame['ExcessPorePress'][1805:,0].astype(float))


def row(d,i,part,clock,source_time,bottom):
    out=dict(part=part,completed_step=int(clock['completed_step']),actual_time_s=float(clock['time_s']),
        actual_tau_s=float(clock['time_s'])-source_time,signed_dterror_s=float(clock['signed_dterror_s']),native_id=i+2060,
        p_Pa=float(d['p'][i]),fixed_P0_Pa=float(d['p0'][i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),
        J=float(d['J'][i]),n=float(d['n'][i]),stored_theta_last_stage_s_inv=float(d['theta'][i]),
        kappa=float(d['kappa'][i]),FS_type=int(d['FS'][i]),FS23=bool(d['FS'][i] in (2,3)),
        PosDiv_saved=float(d['PosDiv'][i]),fixed_initial_bottom_ID=bool(bottom[i]),
        NN_over_dp=float(d['nn'][i]),nearest_soil_material_id=int(d['neighbor'][i])+2060,speed_m_s=float(d['speed'][i]))
    for j,a in enumerate(('x','y','z')):out[a+'_m']=float(d['pos'][i,j]);out['v'+a+'_m_s']=float(d['v'][i,j])
    for j,a in enumerate(('xx','yy','zz')):out['effective_'+a+'_Pa']=float(d['kk'][i,j]);out['total_'+a+'_Pa']=float(d['kk'][i,j]-d['p'][i])
    for j,a in enumerate(('xy','yz','xz')):out['effective_and_total_'+a+'_Pa']=float(d['ij'][i,j])
    for j in range(3):out['effective_principal_'+str(j)+'_Pa']=float(d['effective'][i,j]);out['total_principal_'+str(j)+'_Pa']=float(d['total'][i,j])
    return out


def analyze(bundle,bottom,source_time):
    # The one pulse record is retained and reused at its turn in the41-save loop.
    pulse_frame=typed.core.read22(bundle,PULSE);pulse=data(pulse_frame)
    minimum=int(np.argmin(pulse['p']));rank=np.argsort(pulse['p'],kind='stable')[:20]
    dist=np.linalg.norm(pulse['pos']-pulse['pos'][minimum],axis=1)
    nearest=np.argsort(dist,kind='stable');neighbors=[int(i) for i in nearest if i!=minimum][:12]
    bed=[int(i) for i in nearest if bottom[i]][:8]
    selected=sorted(set(map(int,rank))|set(neighbors)|set(bed)|{minimum})
    selection=[dict(native_id=i+2060,pulse_minimum=i==minimum,pulse_lowest20_rank=(int(np.flatnonzero(rank==i)[0])+1) if i in rank else None,
        nearest12_to_pulse_minimum=i in neighbors,nearest8_fixed_initial_bottom=i in bed,
        pulse_distance_to_minimum_m=float(dist[i]),fixed_initial_bottom_ID=bool(bottom[i]),selection_fixed_at_part=PULSE) for i in selected]
    full=[row(pulse,i,PULSE,bundle['clocks'][PULSE],source_time,bottom) for i in range(5000)]
    tracks,windows=[],[];last=None;previous_time=None
    for part in PARTS:
        frame=pulse_frame if part==PULSE else typed.core.read22(bundle,part);d=pulse if part==PULSE else data(frame)
        need((d['J']>0).all() and np.array_equal(d['p0'],pulse['p0']),'Positive native J and fixed P0 required')
        clock=bundle['clocks'][part];time=float(clock['time_s']);at=int(np.argmin(d['p']));fs=(d['FS']==2)|(d['FS']==3)
        windows.append(dict(part=part,completed_step=int(clock['completed_step']),actual_time_s=time,actual_tau_s=time-source_time,
            p_min_Pa=float(d['p'][at]),p_min_material_id=at+2060,p_max_Pa=float(d['p'].max()),p_RMS_Pa=float(np.sqrt(np.mean(d['p']**2))),
            negative_p_nodes=int((d['p']<0).sum()),FS23_nodes=int(fs.sum()),FS23_negative_p_nodes=int((fs&(d['p']<0)).sum()),
            fixed_bottom_p_min_Pa=float(d['p'][bottom].min()),J_min=float(d['J'].min()),J_max=float(d['J'].max()),
            kappa_max=float(d['kappa'].max()),speed_max_m_s=float(d['speed'].max()),NN_min_over_dp=float(d['nn'].min())))
        for i in selected:
            out=row(d,i,part,clock,source_time,bottom);dt=time-previous_time if last is not None else None
            out['actual_saved_interval_s']=dt
            out['delta_p_Pa']=float(d['p'][i]-last['p'][i]) if last is not None else None
            out['delta_lnJ']=float(np.log(d['J'][i])-np.log(last['J'][i])) if last is not None else None
            out['delta_p_per_saved_interval_Pa_s']=out['delta_p_Pa']/dt if last is not None else None
            out['delta_lnJ_per_saved_interval_s_inv']=out['delta_lnJ']/dt if last is not None else None
            out['mean_of_two_saved_last_stage_theta_s_inv']=float(.5*(d['theta'][i]+last['theta'][i])) if last is not None else None
            out['delta_lnJ_minus_endpoint_theta_trapezoid']=out['delta_lnJ']-out['mean_of_two_saved_last_stage_theta_s_inv']*dt if last is not None else None
            out['delta_kappa']=float(d['kappa'][i]-last['kappa'][i]) if last is not None else None
            out['FS_changed_since_previous_save']=bool(d['FS'][i]!=last['FS'][i]) if last is not None else None
            need(all(np.isfinite(v) for v in out.values() if isinstance(v,float)),'No nonfinite scientific value may be omitted')
            tracks.append(out)
        last=d;previous_time=time
    need(len(full)==5000 and len(windows)==41 and len(tracks)==41*len(selected),'Exact41 fixed-ID and all5000 pulse coverage required')
    return minimum+2060,full,selection,tracks,windows


def plots(minimum,full,selection,tracks,windows):
    focus=[q for q in tracks if q['native_id']==minimum];lowest={q['native_id'] for q in selection if q['pulse_lowest20_rank'] is not None}
    fig,axes=plt.subplots(3,2,figsize=(13,12),layout='constrained')
    axes[0,0].plot([q['actual_tau_s'] for q in windows],[q['p_min_Pa']*.001 for q in windows],label='All5000 minimum')
    axes[0,0].plot([q['actual_tau_s'] for q in windows],[q['p_RMS_Pa']*.001 for q in windows],label='All5000 RMS');axes[0,0].legend(fontsize=8)
    for nid in sorted(lowest):
        rr=[q for q in tracks if q['native_id']==nid];axes[0,1].plot([q['actual_tau_s'] for q in rr],[q['p_Pa']*.001 for q in rr],alpha=.45,lw=.8,color='grey')
    t=[q['actual_tau_s'] for q in focus];axes[0,1].plot(t,[q['p_Pa']*.001 for q in focus],color='C1',label=f'Fixed pulse-min ID{minimum}');axes[0,1].legend(fontsize=8)
    axes[1,0].plot(t[1:],[q['delta_lnJ_per_saved_interval_s_inv'] for q in focus[1:]],label='Delta lnJ / actual saved dt')
    axes[1,0].plot(t[1:],[q['mean_of_two_saved_last_stage_theta_s_inv'] for q in focus[1:]],label='Mean of two saved stage theta');axes[1,0].legend(fontsize=8)
    axes[1,1].plot(t,[q['J'] for q in focus],label='Native J');axes[1,1].legend(fontsize=8)
    for prefix,style in (('effective','-'),('total','--')):
        for j in (0,2):axes[2,0].plot(t,[q[prefix+'_principal_'+str(j)+'_Pa']*.001 for q in focus],style,label=prefix+(' min' if j==0 else ' max'))
    axes[2,0].legend(fontsize=8);axes[2,1].plot(t,[q['NN_over_dp'] for q in focus],label='Fixed ID NN/dp')
    axes[2,1].plot([q['actual_tau_s'] for q in windows],[q['NN_min_over_dp'] for q in windows],label='All5000 minimum NN/dp');axes[2,1].legend(fontsize=8)
    titles=('Whole-domain signed pressure [kPa]','Fixed lowest20 pressure histories [kPa]','Saved-interval volume-rate comparison [1/s]','Fixed pulse-min material J','Fixed pulse-min principal stresses [kPa]','True3D nonself soil spacing [dp]')
    for ax,title in zip(axes.flat,titles):ax.set(title=title,xlabel='Actual time after release [s]');ax.grid(alpha=.2)
    fig.suptitle('Existing saved pressure pulse:41 raw saves; no stage-causality claim',fontsize=13)
    path=Path(str(PREFIX)+'_history.png');fig.savefig(path,dpi=170);plt.close(fig);files=[path]
    center=next(q for q in full if q['native_id']==minimum);pp=np.array([q['p_Pa']*.001 for q in full]);norm=TwoSlopeNorm(vmin=float(pp.min()),vcenter=0,vmax=float(pp.max())) if pp.min()<0<pp.max() else Normalize(float(pp.min()),float(pp.max()))
    nnorm=Normalize(min(q['NN_over_dp'] for q in full),max(q['NN_over_dp'] for q in full));fig,axes=plt.subplots(1,3,figsize=(17,5),layout='constrained')
    for ax,field,n,color,title in ((axes[0],'p_Pa',norm,'coolwarm','All5000 raw pressure [kPa]'),(axes[1],'p_Pa',norm,'coolwarm','Local raw pressure [kPa]'),(axes[2],'NN_over_dp',nnorm,'viridis','Local true3D soil NN / dp')):
        image=ax.scatter([q['x_m'] for q in full],[q['z_m'] for q in full],c=[q[field]*(.001 if field=='p_Pa' else 1) for q in full],s=5,cmap=color,norm=n,rasterized=True)
        ax.scatter([center['x_m']],[center['z_m']],marker='*',s=90,c='yellow',edgecolors='black',linewidths=.7,label=f'Actual min ID{minimum}')
        ax.set(title=title,xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal');ax.legend(fontsize=8)
        if ax is not axes[0]:ax.set_xlim(center['x_m']-4*H,center['x_m']+4*H);ax.set_ylim(center['z_m']-4*H,center['z_m']+4*H)
        fig.colorbar(image,ax=ax,shrink=.75)
    fig.suptitle(f'Part112 actual tau={center["actual_tau_s"]:.12f}s; no smoothing or clipping of pressure values',fontsize=13)
    fig.supxlabel('The local display rectangle is not a material selection or acceptance threshold. All5000 raw values are exported.',fontsize=9)
    path=Path(str(PREFIX)+'_field.png');fig.savefig(path,dpi=175);plt.close(fig);files.append(path);return files


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Separate root offline execution authorization required')
    need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'_*')),'Existing complete/partial pulse artifacts protected')
    consumed=[stat(q) for q in (Path(__file__),NOTE,Path(typed.__file__),Path(typed.core.__file__),Path(metric.__file__),Path(seal.__file__))]
    result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,native_decoder_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        bundle,bottom,source_time=inputs(consumed);minimum,full,selection,tracks,windows=analyze(bundle,bottom,source_time)
        files=[]
        for suffix,rows in (('part112',full),('selection',selection),('tracks',tracks),('window',windows)):
            path=Path(str(PREFIX)+'_'+suffix+'.csv');metric.write(path,rows);files.append(path)
        files+=plots(minimum,full,selection,tracks,windows)
        need(all(stat(q['path'])==q for q in consumed),'Core sealed input changed during offline pulse review')
        at=next(q for q in full if q['native_id']==minimum)
        result.update(passed=True,analysis_complete=True,consumed_stats_unchanged=True,read_parts=list(PARTS),
            numerical_native_records_read=41,pulse_part=112,pulse_minimum=at,selected_IDs=[q['native_id'] for q in selection],
            fixed_lowest20_IDs=[q['native_id'] for q in selection if q['pulse_lowest20_rank'] is not None],
            selected_IDs_fixed_over_all41_states=True,part112_soil_rows=5000,track_rows=len(tracks),window_rows=41,
            no_nominal_clock_or_interpolation=True,all22_original_safety_via_completed_native=True,
            PosDiv_is_not_velocity_divergence=True,stored_stage_theta_is_not_interval_mean=True,
            saved_endpoint_trapezoid_is_stage_integral=False,Darcy_remainder_or_stage_cause_inferred=False,
            material_theory_values_assigned=False,negative_values_filtered=False,visual_QA_pending=True,files=[stat(q) for q in files])
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed
    with CHECK.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    need(result['passed'],result.get('first_failure','Offline pulse review failed; preserve partial outputs'))


if __name__=='__main__':main()
