"""At most four genuine saved records; evaluate n3/n4 pair signs on each same frozen geometry."""
import argparse,csv,json,struct
from pathlib import Path
import upl_c08_asn4_partial_compare_r1 as comp
import upl_c08_as_pair_sign_r1 as pair
np,c=pair.np,comp.c
T=c.T;TAG='upl_c08_asn34_pair_shadow_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');EVALUATED=(3.,4.)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read before one offline shadow evaluation required');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial pair-shadow output protected')
    reviewed=c.read(comp.CHECK);c.need(reviewed['passed'] and reviewed['analysis_completed'] and reviewed['actual_common_frames']==66 and reviewed['actual_clocks_steps_exact'] and reviewed['P0_bits_equal'] and reviewed['original_n3_header']==[6805,22,300] and reviewed['original_n4_header']==[6805,22,66] and not reviewed['n4_runtime_success'] and not reviewed['unsaved_failure_reconstructed'],'Passed actual300/66 partial comparison required')
    old=comp.full.load(comp.full.SPECS[1]);new=comp.load_n4(old);contexts=(old,new);cp=Path(str(comp.PREFIX)+'_cohorts.csv');cohortentry=pair.entry(reviewed['files'],cp);cached=pair.table(cp);before=[c.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),comp.CHECK,Path(pair.__file__),Path(comp.full.__file__),Path(comp.cluster.__file__),Path(c.__file__))]+[pair.entry(reviewed['consumed'],Path(comp.__file__)),cohortentry]+old['before']+new['before'];pairs=[];summaries=[];selections=[];records=0;source_counts={};matched={}
    c.need(pair.N==6805 and pair.DP==.04 and pair.HDP==1.2 and pair.EPSILON==.2,'Original pair-shadow fixed material/kernel constants differ')
    for ctx,original_count,source_name in ((old,300,'n3_r6_full300'),(new,66,'n4_failed_partial66')):
        label=ctx['label'];rows=[r for r in cached if r['group']==label and r['cohort']=='all_soil'];c.need(len(rows)==66 and {int(r['part']) for r in rows}==set(range(66)) and all(int(r['soil_count'])==5000 for r in rows),'Exact all5000 common66 cached geometry required')
        for r in rows:
            clock=ctx['clocks'][int(r['part'])];c.need(float(r['time_s'])==float(clock['time_s']) and float(r['tau_s'])==float(clock['tau_from_actual_release_s']) and int(r['completed_step'])==int(clock['completed_step']),'Cached actual common-window clock differs')
        minimum=min(rows,key=lambda r:(float(r['rNN_over_dp_min']),int(r['part'])));last=next(r for r in rows if int(r['part'])==65);selected={}
        for reason,r in (('common66_window_min_NN',minimum),('actual_tau_0p66',last)):selected.setdefault(int(r['part']),dict(row=r,reasons=[]))['reasons'].append(reason)
        source_counts[source_name]=len(selected)
        with (ctx['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,original_count),'Original300/66 file header differs; never rewritten')
            for part,selection in sorted(selected.items()):
                f.seek(12+part*ctx['dtype'].itemsize);record=np.fromfile(f,dtype=ctx['dtype'],count=1);c.need(len(record)==1,'Selected literal native record incomplete');frame=record[0];time,tau,step=c.inspect(frame,ctx,part);records+=1;r=selection['row'];c.need(time==float(r['time_s']) and tau==float(r['tau_s']) and step==int(r['completed_step']),'Actual selected payload/cache clock differs');matched.setdefault(part,[]).append((time,tau,step))
                ids=frame['Idp'][:,0];slots=np.flatnonzero(ids>=2060);x=frame['Posd'][slots];c.need(np.array_equal(ids[slots],np.arange(2060,7060)) and np.all(x[:,1]==0.),'All5000 original2D soil IDs required');close=pair.cKDTree(x[:,(0,2)]).query_pairs(.7*pair.DP,output_type='ndarray');dist=np.linalg.norm(x[close[:,0]]-x[close[:,1]],axis=1);keep=dist<.7*pair.DP;close,dist=close[keep],dist[keep]
                c.need(np.all(dist>0.) and len(close)==int(r['pair_both_in_cohort_lt_0p7dp']),'Coincident pair or cached close-pair coverage differs')
                if len(close):c.need(abs(float(dist.min()/pair.DP)-float(r['rNN_over_dp_min']))<=64*np.finfo(float).eps,'Close-pair minimum differs from the retained geometry cache')
                else:c.need(float(r['rNN_over_dp_min'])>=.7,'Empty close-pair list contradicts retained minimum spacing')
                # Same native-double positive spectral part as pair.main; tensor/cubic/sign are reused.
                tensors=pair.tensor(frame,slots);c.need(np.isfinite(tensors).all(),'Finite native total stress required');eig,Q=np.linalg.eigh(tensors);positive=(Q*np.maximum(eig,0.)[:,None,:])@Q.transpose(0,2,1);evaluations={exponent:[] for exponent in EVALUATED}
                selection_text=';'.join(selection['reasons']);selections.append(dict(snapshot_source=source_name,snapshot_AS_exp=ctx['exponent'],part=part,time_s=time,tau_s=tau,completed_step=step,selection=selection_text,close_pair_count=len(close)))
                for ij,distance in sorted(zip(close,dist),key=lambda item:(float(item[1]),int(ids[slots[item[0][0]]]),int(ids[slots[item[0][1]]]))):
                    i,j=map(int,ij);si,sj=slots[i],slots[j];direction=(x[i]-x[j])/distance;s=float(distance/pair.DP);ratio=pair.cubic(s/pair.HDP)/pair.cubic(1./pair.HDP);raw=float(direction@(tensors[i]+tensors[j])@direction);pn=float(direction@(positive[i]+positive[j])@direction);drdt=float((frame['Vel'][si].astype(float)-frame['Vel'][sj].astype(float))@direction);scale=max(1.,float(np.max(np.abs(eig[i])))+float(np.max(np.abs(eig[j]))))
                    for exponent in EVALUATED:
                        F=pair.EPSILON*ratio**exponent;art=-F*pn;net=raw+art;resolution=32*np.finfo(np.float32).eps*(1.+F)*scale
                        row=dict(snapshot_source=source_name,snapshot_AS_exp=ctx['exponent'],evaluated_exp=exponent,AS_epsilon=pair.EPSILON,part=part,time_s=time,tau_s=tau,completed_step=step,selection=selection_text,id_i=int(ids[si]),id_j=int(ids[sj]),r_over_dp=s,nx=float(direction[0]),nz=float(direction[2]),separation_rate_m_s=drdt,kernel_ratio=ratio,F_includes_epsilon=F,total_normal_Pa=raw,positive_spectrum_normal_Pa=pn,AS_normal_Pa=art,net_normal_Pa=net,float_scale_screening_Pa=float(resolution),total_sign=pair.sign(raw,resolution),AS_sign=pair.sign(art,resolution),net_sign=pair.sign(net,resolution),min_abs_total_eigenvalue_Pa=float(min(np.min(abs(eig[i])),np.min(abs(eig[j])))),positive_rank_i=int(np.count_nonzero(eig[i]>0)),positive_rank_j=int(np.count_nonzero(eig[j]>0)))
                        for suffix,slot in (('i',si),('j',sj)):
                            for key,k in (('x',0),('y',1),('z',2)):row[key+'_'+suffix+'_m']=float(frame['Posd'][slot,k])
                            for key,k in (('vx',0),('vy',1),('vz',2)):row[key+'_'+suffix+'_m_s']=float(frame['Vel'][slot,k])
                            for field,key in (('Kplastic','kappa'),('PorePress','p_Pa'),('PorePress0','P0_Pa'),('ExcessPorePress','native_excess_Pa'),('PoroVolumeRatio','J'),('FSType','FS')):row[key+'_'+suffix]=float(frame[field][slot,0])
                        c.need(all(np.isfinite(v) for v in row.values() if isinstance(v,(int,float))),'Nonfinite pair shadow arithmetic');evaluations[exponent].append(row);pairs.append(row)
                for exponent,rr in evaluations.items():
                    m=rr[0] if rr else None;summaries.append(dict(snapshot_source=source_name,snapshot_AS_exp=ctx['exponent'],evaluated_exp=exponent,part=part,time_s=time,tau_s=tau,completed_step=step,selection=selection_text,close_pair_count=len(rr),min_pair_ids=','.join(str(m[k]) for k in ('id_i','id_j')) if m else '',min_r_over_dp=m['r_over_dp'] if m else None,min_pair_total_normal_Pa=m['total_normal_Pa'] if m else None,min_pair_AS_normal_Pa=m['AS_normal_Pa'] if m else None,min_pair_net_normal_Pa=m['net_normal_Pa'] if m else None,min_pair_net_sign=m['net_sign'] if m else 'no_pair',net_attractive_pairs=sum(q['net_sign']=='attractive_shadow' for q in rr),net_repulsive_pairs=sum(q['net_sign']=='repulsive_shadow' for q in rr),net_near_zero_pairs=sum(q['net_sign']=='near_zero_unresolved' for q in rr),closing_pairs=sum(q['separation_rate_m_s']<0 for q in rr)))
    c.need(records<=4 and all(v<=2 for v in source_counts.values()) and all(len(v)==1 or v[0]==v[1] for v in matched.values()),'Maximum4 deduplicated records/exact shared selected clocks required');c.need(all(c.stat(v['path'])==v for v in before),'Closed comparison/cache/native/helper input changed')
    pp=Path(str(PREFIX)+'_pairs.csv');sp=Path(str(PREFIX)+'_frames.csv')
    if pairs:pair.write(pp,pairs)
    else:
        with pp.open('x',encoding='utf-8',newline='') as f:csv.writer(f).writerow(('snapshot_source','snapshot_AS_exp','evaluated_exp','part','id_i','id_j','r_over_dp','total_normal_Pa','AS_normal_Pa','net_normal_Pa','separation_rate_m_s'))
    pair.write(sp,summaries);result=dict(stage=TAG,passed=True,analysis_completed=True,common_saved_window_parts=[0,65],selection_scope='minimum over all5000 soil IDs and common66 saved states, not n3 remaining3s',selected_native_records_read=records,unique_records_per_source=source_counts,selected_snapshots=selections,original_headers_preserved={'n3':[6805,22,300],'n4':[6805,22,66]},evaluated_exponents=list(EVALUATED),same_geometry_both_exponents=True,snapshot_source_distinct_from_evaluated_exp=True,trajectory_reintegrated=False,n4_runtime_success=False,n4_failure_reported_step=4265004,unsaved_failure_reconstructed=False,AS_epsilon_in_F_once=True,double_eigen_frozen_shadow=True,GPU_float_bit_replay=False,float_screen_not_certified_GPU_error_bound=True,positive_net_normal_means_attractive=True,negative_separation_rate_means_closing=True,pore_pressure_sign_preserved=True,no_C_correction=True,pair_force_magnitude_computed=False,whole_stencil_or_temporal_causation_claimed=False,dense_trace_read=False,full_native_window_scan=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[c.stat(pp),c.stat(sp)])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('ASN34_PAIR_SHADOW_READY',CHECK,'records',records,'pair_evaluations',len(pairs),flush=True)
if __name__=='__main__':main()
