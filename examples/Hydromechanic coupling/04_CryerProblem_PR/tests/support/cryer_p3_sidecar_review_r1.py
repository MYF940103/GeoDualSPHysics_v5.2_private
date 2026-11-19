"""Read sealed Cryer P3 solver sidecars only. Preserve the original BI4 and clocks."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

T=Path(__file__).resolve().parents[1]
SOIL=37173
DT=2.0**-19
DRAIN=2.0**-7
ROUNDS=('endpoint1','endpoint2','endpoint3')
PHASES=('pre','cor',*ROUNDS)
PN='pn_Pa'
PREV='previous_Pa'
Q='endpoint_q_actual_float_Pa'
PRED='prediction_double_Pa'
RAW='raw_final_float_Pa'
BC='validated_BC_value_float_Pa'
FINAL='final_field_float_Pa'
DIAG='S_1_per_m_s'
RESIDUAL='Rgamma_Pa_per_m_s'
FIELDS=(PN,PREV,PRED,'half_actual_float_Pa','Jn','Jhalf','Jfull','theta_half_for_J_1_per_s','source_drained')
RS='UplTpiP3GpuR1'
TS='UplTpiP3DtR1'

def need(ok, msg):
    if not bool(np.all(ok)):
        raise ValueError(msg)

def exact(a,b,msg,dtype=np.float64):
    x,y=np.broadcast_arrays(np.asarray(a,dtype=dtype),np.asarray(b,dtype=dtype))
    bits=np.uint32 if dtype==np.float32 else np.uint64
    need(x.view(bits)==y.view(bits), msg)

def table(p,**kwargs):
    return pd.read_csv(p,float_precision='round_trip',dtype=np.float64,**kwargs)

def doc(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def inspect(folder, steps):
    path=lambda stem:folder/stem
    step=doc(path(TS+'.summary.json'))
    run=doc(path(RS+'.summary.json'))
    sp=doc(path(TS+'.policy.json'))
    rp=doc(path(RS+'.policy.json'))
    need(run['completed'] and step['completed'] and step['updates']==steps and run['commits']==steps,'terminal summary or requested cap')
    need(sp['dt_policy']=='M0_Eq40_Rh1' and sp['R_h']==1 and sp['backend']=='GPU'
         and rp['alpha']==.5 and rp['beta']==0 and rp['endpoint_defect_rounds']==3 and rp['soil_count']==SOIL,'method binding')
    states=table(path(TS+'.csv'))
    body=table(path(RS+'.body.csv'))
    count=len(states)
    need(count==len(body)==step['saved_intervals_including_initial'],'save count')
    expect=np.arange(count)
    need(states.part==expect,'dt part indices')
    need(body.part==expect,'body part indices')
    need((states.completed_updates%1==0)&(states.completed_updates>=0),'completed step indices')
    n=states.completed_updates.to_numpy(dtype=np.int64)
    saved=states.actual_save_time_s.to_numpy()
    exact(saved,n*DT,'dyadic actual clocks')
    exact(body.time_s,saved,'body/dt clocks')
    need(n[0]==0 and n[-1]==steps and np.all(np.diff(n)>0),'save sequence or cap')
    need(states.saved_step==np.maximum(n-1,0),'zero-based native metadata')
    need(states.dt_s==DT,'fixed dt')
    exact(run['actual_end'],saved[-1],'actual end')
    exact(step['actual_end_s'],saved[-1],'dt final')
    delta=np.diff(n,prepend=0)
    need(states.interval_empty==(n==0),'initial empty interval')
    for phase in PHASES:
        need(states['total_'+phase]==n,'phase total '+phase)
        need(states['interval_'+phase]==delta,'phase nonempty intervals '+phase)
        need(step[phase]==steps,'terminal phase '+phase)
    for name,mult in [('pre_calls',1),('cor_calls',1),('J_calls',1),('endpoint_calls',3),('endpoint_writes',3),
                      ('provisional_validations',2),('endpoint_transitions',2),('provisional_row_D2D_copies',2),
                      ('core_field_bit_checks',21*SOIL),('HG_readonly_snapshot_checks',0)]:
        need(run[name]==steps*mult,'terminal pressure '+name)
    need(run['initial_provisional_row_D2D_copies']==2,'cold provisional initialization')
    bound='min_selected_bound_s'
    err='max_dt_minus_bound_s'
    scales=['min_force_CFL_s','min_skeleton_wave_AV_CFL_s','min_Rh_hydro_s']
    all_scales=[*scales,'min_legacy_Kw_wave_CFL_reference_s','min_HG_limit_reference_s']
    need(np.isfinite(states.to_numpy()).all(),'non-finite dt audit')
    for k in [*all_scales,bound]:need(states.loc[0,k]==np.finfo(float).max,'initial dt sentinel '+k)
    need(states.loc[0,err]==-np.finfo(float).max,'initial signed sentinel')
    z=states.iloc[1:]
    need(z[all_scales].to_numpy()>0,'positive scales')
    exact(z[bound],z[scales].min(axis=1),'active Eq40/Rh1 interval minimum')
    exact(z[err],DT-z[bound].to_numpy(),'signed interval maximum')
    need(z[err]<=0,'fixed dt exceeded method bound')
    for k in [*all_scales,bound]:exact(step[k],z[k].min(),'global bound '+k)
    exact(step[err],z[err].max(),'global signed error')
    center=doc(T/'logs/cryer_radial_layout_r1.check.json')['native_identity']['center_ids']
    full=steps<=64
    ids=np.arange(8,37181) if full else np.array(center)
    need(rp['output_all_ids']==full and len(ids)==(SOIL if full else 18),'native material sampling policy')
    need(body.body_checked==SOIL,'body audit checked count')
    need(body.exported_per_round==len(ids),'body audit export counts')
    need(run['saved_records_per_round']==len(ids)*count,'terminal export row count')
    readers=[iter(table(path(f'{RS}.round{rr}.csv'),chunksize=len(ids))) for rr in (1,2,3)]
    observed_projected=[0]*3
    try:
        for idx,completed in enumerate(n):
            source=max(int(completed)-1,0)*DT
            label=f'part {idx}, completed {completed}: '
            frame=[]
            for rr,reader in enumerate(readers,1):
                d=next(reader)
                need(d.native_id.to_numpy()==ids,label+'native ID order')
                need(np.isfinite(d.to_numpy()).all(),label+'finite observations')
                for col,val in [('part',idx),('round',rr),('completed_step',completed),
                                ('source_step_zero_based',max(completed-1,0)),('commits',completed),
                                ('endpoint_calls',3*completed),('core_field_bit_checks',21*SOIL*completed),
                                ('hg_snapshot_checks',0),('has_endpoint_observation',int(completed>0)),
                                ('final_field_is_previous_step',int(rr<3 and completed>0))]:
                    need(d[col]==val,label+col)
                exact(d.actual_save_time_s,saved[idx],label+'save clock')
                exact(d.source_time_s,source,label+'source clock')
                exact(d.dt_s,DT,label+'step')
                for key in ['source_drained','endpoint_drained','commit_drained']:
                    need(d[key].isin([0.,1.]),label+key)
                    if completed<=4096:need(d[key]==0,label+'closed drainage '+key)
                if not completed:
                    need(d[[PN,PREV,Q,PRED,RAW,FINAL,BC,DIAG,RESIDUAL]].to_numpy()==0,label+'cold pressure')
                    need(d[['Jn','Jhalf','Jfull']].to_numpy()==1,label+'initial J')
                else:
                    source_mask=d.source_drained.to_numpy(dtype=bool)
                    end_mask=d.endpoint_drained.to_numpy(dtype=bool)
                    commit_mask=d.commit_drained.to_numpy(dtype=bool)
                    exact(d.loc[source_mask,PN],0.,label+'drained predictor source p_n',np.float32)
                    q=d[Q].to_numpy()
                    predicted=d[PN].to_numpy()+.5*(d[PN].to_numpy()-d[PREV].to_numpy())
                    exact(d[PRED],predicted,label+'alpha extrapolation')
                    expected_half=np.where(source_mask,0.,predicted).astype(np.float32)
                    # Source BC both rounds of the old mechanical step uses original t_n.
                    exact(d['half_actual_float_Pa'],expected_half,label+'half pressure',np.float32)
                    if rr==1:
                        # Guess uses the full geometry and current surface set.
                        free_guess=predicted.astype(np.float32)
                        if source<DRAIN or not full:
                            need(~end_mask if not full else True,label+'center materials remain interior')
                            exact(q,free_guess,label+'first endpoint pressure',np.float32)
                        else:
                            need((q==free_guess)|(q==0),label+'first endpoint pressure or boundary projection')
                    else:exact(q,frame[-1][BC],label+'actual provisional q',np.float32)
                    need(d.loc[~end_mask,DIAG]>0,label+'positive diagonal')
                    need(d.loc[end_mask,[DIAG,RESIDUAL]].to_numpy()==0,label+'drained row')
                    raw=np.zeros(len(ids),dtype=np.float64)
                    raw[~end_mask]=q[~end_mask]+d[RESIDUAL].to_numpy()[~end_mask]/d[DIAG].to_numpy()[~end_mask]
                    exact(d[RAW],raw,label+'q + R/S',np.float32)
                    bc=np.where(commit_mask,0,d[RAW].to_numpy())
                    exact(d[BC],bc,label+'committed boundary rule',np.float32)
                    if rr==3:exact(d[FINAL],bc,label+'final committed pressure',np.float32)
                    if frame:
                        for key in FIELDS:exact(d[key],frame[0][key],label+'frozen between rounds '+key)
                        if rr==2:exact(d[FINAL],frame[0][FINAL],label+'provisional final history')
                    observed_projected[rr-1]+=int(commit_mask.sum())
                frame.append(d)
            for a,b,key in [(1,0,'max_abs_p2_minus_p1_Pa'),(2,1,'max_abs_p3_minus_p2_Pa')]:
                m=np.max(np.abs(frame[a][BC].to_numpy()-frame[b][BC].to_numpy()))
                actual=body.loc[idx,key]
                need(np.isfinite(actual) and actual>=0,label+'finite body pressure change')
                if full:exact(actual,m,label+key)
                else:need(m<=actual,label+'center vs body '+key)
        extra=object()
        for r in readers:need(next(r,extra) is extra,'extra pressure rows')
    finally:
        for r in readers:r.close()
    return dict(passed=True,physical_acceptance=False,steps=steps,actual_end_s=float(saved[-1]),frames=count,
                pressure_rounds=3,dt_phases=5,source_time_policy='all five phases retain original t_n',
                completely_audited_saved_ids_per_round=len(ids),device_and_saved_body_receivers=SOIL,
                center_ids=None if full else center,inspected_pressure_rows=count*len(ids)*3,
                exported_commit_drained_counts=observed_projected,closed_through_completed_step=4096,
                actual_post_open_frames=int(sum(n>4096)),min_selected_bound_s=float(z[bound].min()),
                max_dt_minus_selected_bound_s=float(z[err].max()),
                min_legacy_Kw_wave_reference_s=float(z.min_legacy_Kw_wave_CFL_reference_s.min()),
                body_max_abs_p2_minus_p1_Pa=float(body.max_abs_p2_minus_p1_Pa.max()),
                body_max_abs_p3_minus_p2_Pa=float(body.max_abs_p3_minus_p2_Pa.max()),
                long_file_sampling='Original 18 center IDs; all-receiver cross-round checks performed in solver. Surface identity/zero pressure requires independent BI4 review.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('steps',type=int)
    parser.add_argument('receipt',type=Path)
    args=parser.parse_args()
    if args.receipt.exists():raise FileExistsError(args.receipt)
    try:
        result=inspect(args.output,args.steps)
    except Exception as exc:
        result={'passed':False,'error':repr(exc)}
    result['directory']=str(args.output.resolve())
    with args.receipt.open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(result,ensure_ascii=False))
    sys.exit(0 if result['passed'] else 1)

