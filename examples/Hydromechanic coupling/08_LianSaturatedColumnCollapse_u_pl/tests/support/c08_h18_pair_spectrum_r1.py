"""Offline tensile spectra of qualified failed90 saved close pairs; never a force replay."""
import argparse,json,re,struct
from pathlib import Path
import c08_h18_compare_r2 as old

np,T,need,path,stat,read,bind=old.np,old.T,old.need,old.path,old.stat,old.read,old.bind
TAG='c08_h18_pair_spectrum_r1';DP=.04

def load(check_path,consumed):
    q=read(check_path);need(q['stage']=='c08_h18_wend_partial_review_r1' and q['analysis_complete'] and q['saved_prefix_native_qualified'] and q['actual_saved_records']==90 and not q['receiver_complete'] and not q['whole_run_passed'] and not q['physical_acceptance'],'Require already qualified failed90 partial analysis, never whole-run acceptance')
    entry=bind(q['consumed'][0]);m=read(entry['path']);spec=m['case'];root=path(spec['native_dir']);prior={str(path(v['path'])):v for v in q['consumed']};needed=[root/n for n in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv')]+[path(spec[k]) for k in ('input_xml','material_csv')]
    for p in needed:need(str(p) in prior,'Prior analysis did not bind required export: '+str(p));consumed.append(bind(prior[str(p)]))
    consumed += [stat(check_path),entry];d=read(root/'completion.json');need(d['stage']=='c08_h18_wend_partial_native_r1.receiver' and d['saved_prefix_native_passed'] and not d['passed'] and d['samples']==90 and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22 and d['max_signed_dterror_s']<=1e-14,'Actual native prefix scope or original signed budget differs')
    layout=old.table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Original typed22 layout required')
    for row,(name,kind,width) in zip(layout,old.SCHEMA):need((row['array'],row['type'],int(row['components']))==(name,kind,width),'Literal native schema differs');fields.append((name,old.TYPES[kind],(6805,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,90),'Original failed90 header must remain unchanged')
    need(raw.stat().st_size==12+90*dtype.itemsize,'Original payload extent differs');clocks=old.table(root/'clocks.csv');need(len(clocks)==90,'Actual90 saved clocks required')
    expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)))
    return dict(root=root,done=d,count=90,nodes=6805,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(90,)),clocks=clocks),m

def analyze(bundle):
    histories=[];pairs=[];first=[];seen=set()
    for part in range(90):
        x=old.read22(bundle,part);soil=x['Idp'][:,0]>=2060;ids=x['Idp'][soil,0];pos=x['Posd'][soil];vel=x['Vel'][soil].astype(float);p=x['PorePress'][soil,0].astype(float);kap=x['Kplastic'][soil,0].astype(float);J=x['PoroVolumeRatio'][soil,0];fs=x['FSType'][soil,0];sk=x['SigmaState_kk'][soil];si=x['SigmaState_ij'][soil];s=np.zeros((5000,3,3))
        for k in range(3):s[:,k,k]=sk[:,k]-p
        s[:,0,1]=s[:,1,0]=si[:,0];s[:,1,2]=s[:,2,1]=si[:,1];s[:,0,2]=s[:,2,0]=si[:,2]
        eig,vec=np.linalg.eigh(s);positive=np.maximum(eig,0);tree=old.cKDTree(pos[:,[0,2]]);indices=sorted(tree.query_pairs(.7*DP));endpoint_lam=[];endpoint_dir=[];either_lam0=either_lam100=either_dir0=either_dir100=zero=0;unique=set();time=float(x['time']);tau=time-bundle['done']['source_actual_time_s']
        for i,j in indices:
            dr=pos[j]-pos[i];dr[1]=0.;distance=float(np.linalg.norm(dr))
            if not distance<.7*DP:continue
            n=dr/distance if distance>0 else None;directional=[None,None] if n is None else [float(np.sum(positive[k]*(vec[k].T@n)**2)) for k in (i,j)];lam=[float(eig[k,-1]) for k in (i,j)];unique.update((i,j));endpoint_lam+=lam;endpoint_dir += [v for v in directional if v is not None];zero+=int(n is None)
            either_lam0+=int(max(lam)>0);either_lam100+=int(max(lam)>100);either_dir0+=int(any(v is not None and v>0 for v in directional));either_dir100+=int(any(v is not None and v>100 for v in directional))
            row=dict(part=part,time_s=time,tau_s=tau,completed_step=int(bundle['clocks'][part]['completed_step']),id_i=int(ids[i]),id_j=int(ids[j]),distance_m=distance,distance_over_dp=distance/DP,direction_defined=n is not None,n_x=None if n is None else float(n[0]),n_z=None if n is None else float(n[2]))
            for suffix,k,direction in zip(('i','j'),(i,j),directional):
                values=dict(x_m=float(pos[k,0]),z_m=float(pos[k,2]),p_Pa=float(p[k]),kappa=float(kap[k]),J=float(J[k]),FSType=int(fs[k]),speed_m_s=float(np.linalg.norm(vel[k])),lambda_total_min_Pa=float(eig[k,0]),lambda_total_max_Pa=float(eig[k,-1]),sigma_yy_total_Pa=float(s[k,1,1]),direction_positive_part_Pa=direction,direction_signed_total_Pa=None if n is None else float(n@s[k]@n))
                row.update({name+'_'+suffix:value for name,value in values.items()})
            pairs.append(row);key=(row['id_i'],row['id_j'])
            if key not in seen:first.append(row.copy());seen.add(key)
        count=len(endpoint_lam)//2;lam=np.array(endpoint_lam);direction=np.array(endpoint_dir);speed=np.linalg.norm(vel,axis=1);nn=tree.query(pos[:,[0,2]],k=2)[0][:,1]
        row=dict(part=part,time_s=time,tau_s=tau,completed_step=int(bundle['clocks'][part]['completed_step']),pairs_r_lt_0p7dp=count,unique_close_endpoint_IDs=len(unique),endpoint_occurrences=2*count,zero_distance_pairs=zero,endpoint_lambda_gt0_fraction=None if not count else float(np.mean(lam>0)),endpoint_lambda_gt100Pa_fraction=None if not count else float(np.mean(lam>100)),direction_defined_endpoint_occurrences=len(direction),endpoint_direction_gt0_fraction=None if not len(direction) else float(np.mean(direction>0)),endpoint_direction_gt100Pa_fraction=None if not len(direction) else float(np.mean(direction>100)),pairs_either_lambda_gt0=either_lam0,pairs_either_lambda_gt100Pa=either_lam100,pairs_either_direction_gt0=either_dir0,pairs_either_direction_gt100Pa=either_dir100,body_lambda_gt0_IDs=int(np.count_nonzero(eig[:,-1]>0)),body_lambda_gt100Pa_IDs=int(np.count_nonzero(eig[:,-1]>100)),NN_min_over_dp=float(nn.min()/DP),NN_q05_over_dp=float(np.quantile(nn,.05)/DP))
        for name,v in (('p_Pa',p),('kappa',kap),('J',J),('speed_m_s',speed),('x_m',pos[:,0]),('z_m',pos[:,2])):
            lo,hi=int(np.argmin(v)),int(np.argmax(v));row.update({name+'_min':float(v[lo]),name+'_min_id':int(ids[lo]),name+'_max':float(v[hi]),name+'_max_id':int(ids[hi])})
        histories.append(row)
    return histories,pairs,first

def plot(history,prefix):
    fig,axes=old.plt.subplots(2,2,figsize=(12,8),layout='constrained');tau=[q['tau_s'] for q in history]
    for key,label in (('pairs_r_lt_0p7dp','All close pairs'),('pairs_either_lambda_gt100Pa','Either endpoint lambda_max >100 Pa'),('pairs_either_direction_gt100Pa','Either endpoint directional tensile part >100 Pa')):axes[0,0].plot(tau,[q[key] for q in history],label=label)
    for key,label in (('endpoint_lambda_gt0_fraction','lambda_max >0'),('endpoint_lambda_gt100Pa_fraction','lambda_max >100 Pa'),('endpoint_direction_gt0_fraction','directional >0'),('endpoint_direction_gt100Pa_fraction','directional >100 Pa')):axes[0,1].plot(tau,[q[key] for q in history],label=label)
    for key,label,scale in (('p_Pa_min','Minimum p [kPa]',.001),('p_Pa_max','Maximum p [kPa]',.001)):axes[1,0].plot(tau,[q[key]*scale for q in history],label=label)
    axes[1,1].plot(tau,[q['NN_min_over_dp'] for q in history],label='Minimum NN/dp');axes[1,1].plot(tau,[q['NN_q05_over_dp'] for q in history],label='5% NN/dp')
    for ax,title in zip(axes.flat,('Close-pair spectral eligibility','Close-endpoint occurrence fractions','Full-body absolute pressure extrema','Whole-body nearest spacing')):ax.set(title=title,xlabel='Actual saved time since release [s]');ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0,1].set_ylim(-.03,1.03);fig.suptitle('Saved-state AS eligibility: Sigma_total = Sigma_effective - p I\nDirectional positive part uses n=(dx,0,dz)/r; spectral eligibility is not force or causation');dest=Path(str(prefix)+'.png');fig.savefig(dest,dpi=180);old.plt.close(fig);return dest

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review-check',type=Path,required=True);p.add_argument('--tag',required=True);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized and re.fullmatch('[A-Za-z0-9_]+',args.tag),'Root-reviewed offline execution and safe fresh tag required');prefix=T/'figures'/args.tag;check=T/'logs'/(args.tag+'.check.json');need(not check.exists() and not list(prefix.parent.glob(args.tag+'*')),'Retained derived output is protected');consumed=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(old.__file__)];result=dict(stage=TAG,analysis_complete=False,whole_run_passed=False,physical_acceptance=False,causation_proven=False,consumed=consumed)
    try:
        bundle,manifest=load(args.review_check,consumed);history,pairs,first=analyze(bundle);files=[]
        for suffix,rows in (('history',history),('pairs',pairs),('first_occurrences',first)):
            if rows:dest=Path(str(prefix)+'_'+suffix+'.csv');old.write_csv(dest,rows);files.append(dest)
        files.append(plot(history,prefix));need(all(stat(q['path'])==q for q in consumed),'Consumed qualified export or prior review changed');earliest=[] if not first else [q for q in first if q['part']==first[0]['part']];result.update(analysis_complete=True,actual_saved_records=90,original_target_records=91,source_case=manifest['case']['tag'],actualAS=manifest['case']['actualAS'],earliest_saved_close_pairs=earliest,unique_pairs_ever_seen=len(first),pair_time_observations=len(pairs),final_saved_metrics=history[-1],all90_clock_signed_ID_array_checks_reused_and_read=True,close_threshold_dp=.7,tensile_thresholds_Pa=[0,100],thresholds_are_descriptive_not_new_gates=True,fraction_denominator='Endpoint occurrences in close pairs; repeated IDs count once per pair endpoint. Direction fractions exclude undefined zero-distance directions.',spectrum='Double total stress; 3D positive spectral part, not exact GPU float Jacobi or force-stage replay',out_of_plane_tension_alone_does_not_imply_positive_2D_direction_projection=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as e:result.update(first_failure=str(e),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
