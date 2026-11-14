"""Reproduce retained AS.5 pair/stress and fixed-PRE affinity observations; never run physics."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[key]='1'
import argparse, json, struct
from pathlib import Path
import c08_h18_compare_r2 as old

np, cKDTree = old.np, old.cKDTree
T, L, F = old.T, old.T/'logs', old.T/'figures'
TAG='c08_as05_pair_audit_r1'
RR=T/'outputs/c08_h18_wend_psi0_a05_w09_r1/native_r1'
SR=T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
CHECK=L/(TAG+'.check.json')
NOTE=T/'notes'/(TAG+'.md')
FILES={q:F/(TAG+'_'+q+'.csv') for q in ('pair_observations','pair_onsets','affinity')}
DP=.04
H=float(np.float32(.072))
SUPPORT=2*H
QUANTILES=[0.,.05,.25,.5,.75,.95,1.]
need=old.need


def plain(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def save(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,default=plain,allow_nan=False);stream.write('\n')


def verify(consumed):
    need(all(old.stat(q['path'])==q for q in consumed),'Retained source/receiver consumed stats changed')


def mapped(root,n,count,consumed):
    consumed.extend(old.stat(root/q) for q in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv'))
    done=old.read(root/'completion.json');layout=old.table(root/'typed22_layout.csv');clocks=old.table(root/'clocks.csv')
    need(done['passed'] and done['samples']==count and done['typed_arrays']==22 and done['soil_IDs']==5000,'Retained native qualification differs')
    fields=[('time','<f8')]
    need(len(layout)==22 and len(clocks)==count,'Native22 layout/clock count differs')
    for row,(name,kind,width) in zip(layout,old.SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Native schema differs')
        fields.append((name,old.TYPES[kind],(n,width)))
    dtype=np.dtype(fields);raw=root/'typed22.bin'
    with raw.open('rb') as stream:need(struct.unpack('<III',stream.read(12))==(n,22,count),'Actual mapped header differs')
    need(raw.stat().st_size==12+count*dtype.itemsize,'Mapped payload extent differs')
    expected=np.arange(7060,dtype=np.uint32) if n==7060 else np.r_[np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)]
    return dict(root=root,done=done,count=count,nodes=n,expected=expected,clocks=clocks,
                frames=np.memmap(raw,dtype=dtype,mode='r',offset=12,shape=(count,)))


def pair_rows(bundle,tpre):
    states=[];observations=[];first={};minimum=None
    for part in range(91):
        x=old.read22(bundle,part);soil=slice(1805,None)
        pos=x['Posd'][soil].copy();p=x['PorePress'][soil,0].astype(float);kk=x['SigmaState_kk'][soil];ij=x['SigmaState_ij'][soil]
        # Actual GPU double export is kk=(xx,yy,zz), ij=(xy,yz,xz), including yy.
        need(np.all(ij[:,[0,1]]==0),'Retained2-D xy/yz stress components differ')
        sigma=np.zeros((5000,3,3));sigma[:,range(3),range(3)]=kk
        for k,(a,b) in enumerate(((0,1),(1,2),(0,2))):sigma[:,a,b]=sigma[:,b,a]=ij[:,k]
        effective=np.linalg.eigvalsh(sigma);total=effective-p[:,None]
        pairs=cKDTree(pos[:,[0,2]]).query_pairs(.7*DP,output_type='ndarray')
        if len(pairs):pairs=pairs[np.linalg.norm(pos[pairs[:,0]]-pos[pairs[:,1]],axis=1)<.7*DP]
        state=dict(part=part,time=float(x['time']),tau=float(x['time'])-tpre,pos=pos,p=p,effective=effective,total=total,
                   pairs=pairs,J=x['PoroVolumeRatio'][soil,0].copy(),kappa=x['Kplastic'][soil,0].astype(float),
                   fs=x['FSType'][soil,0].copy(),theta=x['PoroThetaLastStage'][soil,0].copy())
        if len(pairs):
            i,j=pairs.T;delta=pos[i]-pos[j];distance=np.linalg.norm(delta,axis=1);direction=delta/distance[:,None]
            axis=np.stack((np.einsum('ni,nij,nj->n',direction,sigma[i],direction)-p[i],
                           np.einsum('ni,nij,nj->n',direction,sigma[j],direction)-p[j]),axis=1)
            velocity=x['Vel'][soil].astype(float);rdot=np.einsum('ni,ni->n',direction,velocity[i]-velocity[j])
            for q,(a,b) in enumerate(pairs):
                a,b=int(a),int(b);edge=(a,b);isfirst=edge not in first
                if isfirst:first[edge]=(part,q)
                row=dict(part=part,time_s=state['time'],tau_s=state['tau'],ID_i=a+2060,ID_j=b+2060,
                         distance_over_dp=float(distance[q]/DP),first_saved_close=isfirst,
                         pair_axis_total_i_Pa=float(axis[q,0]),pair_axis_total_j_Pa=float(axis[q,1]),
                         pair_axis_total_mean_Pa=float(axis[q].mean()),distance_rate_m_s=float(rdot[q]))
                for suffix,at in (('i',a),('j',b)):
                    for name,value in (('x_m',pos[at,0]),('z_m',pos[at,2]),('p_Pa',p[at]),('J',state['J'][at]),
                                       ('kappa',state['kappa'][at]),('FSType',state['fs'][at]),('theta_last_stage',state['theta'][at])):
                        row[name+'_'+suffix]=float(value)
                    for k in range(3):
                        row['effective_principal'+str(k)+'_Pa_'+suffix]=float(effective[at,k])
                        row['total_principal'+str(k)+'_Pa_'+suffix]=float(total[at,k])
                observations.append(row)
                if minimum is None or distance[q]<minimum[0]:minimum=(float(distance[q]),part,a,b)
        states.append(state)
    need(len(first)==316 and len(observations)==3707,'Known retained pair coverage changed; do not retune')
    return states,observations,first,minimum


def qs(values):return np.quantile(np.asarray(values,dtype=float),QUANTILES).tolist()


def classifications(rows):
    result=dict(rows=len(rows))
    if not rows:return result
    predicates={
        'both_total_all_principals_nonpositive':lambda r:max(r['total_principal2_Pa_i'],r['total_principal2_Pa_j'])<=0,
        'both_total_max_principal_positive':lambda r:min(r['total_principal2_Pa_i'],r['total_principal2_Pa_j'])>0,
        'any_effective_max_principal_positive':lambda r:max(r['effective_principal2_Pa_i'],r['effective_principal2_Pa_j'])>0,
        'both_pair_axis_nonpositive':lambda r:max(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])<=0,
        'both_pair_axis_positive':lambda r:min(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])>0,
        'mean_pair_axis_positive':lambda r:r['pair_axis_total_mean_Pa']>0,
        'both_p_negative':lambda r:max(r['p_Pa_i'],r['p_Pa_j'])<0,
        'any_p_negative':lambda r:min(r['p_Pa_i'],r['p_Pa_j'])<0,
        'both_J_below1':lambda r:max(r['J_i'],r['J_j'])<1,
        'both_kappa_positive':lambda r:min(r['kappa_i'],r['kappa_j'])>0,
        'FS23_any':lambda r:r['FSType_i'] in (2,3) or r['FSType_j'] in (2,3),
        'existing_saved_bedplane_any':lambda r:min(r['z_m_i'],r['z_m_j'])<=4e-8,
        'currently_approaching':lambda r:r['distance_rate_m_s']<0}
    result.update({name:sum(predicate(r) for r in rows) for name,predicate in predicates.items()})
    result['endpoint_quantiles']={name:qs([r[name+'_'+suffix] for r in rows for suffix in ('i','j')]) for name in ('z_m','p_Pa','J','kappa')}
    return result


def affinity(states,first,minimum,pre):
    X=pre['Posd'][2060:][:,[0,2]].copy();V=pre['PoroCurrentVolume'][2060:,0].copy();Jpre=pre['PoroVolumeRatio'][2060:,0].copy()
    tree=cKDTree(X);awen=np.float32(.557/(H*H));clouds={};fits={}
    def cloud(i):
        if i in clouds:return clouds[i]
        ids=np.array(tree.query_ball_point(X[i],SUPPORT),dtype=int);xi=X[ids]-X[i];rr=np.einsum('ni,ni->n',xi,xi)
        keep=rr<=SUPPORT*SUPPORT;ids,xi,rr=ids[keep],xi[keep],rr[keep]
        q=np.sqrt(rr.astype(np.float32)).astype(np.float32)/np.float32(H);a=np.float32(1)-np.float32(.5)*q;a2=a*a
        wab=((awen*(q+q+np.float32(1)))*a2)*a2
        keep=wab>0;ids,xi=ids[keep],xi[keep];w=wab[keep].astype(float)*V[ids];M=xi.T@(w[:,None]*xi)
        need(np.isfinite(M).all() and np.linalg.det(M)>0,'Fixed PRE reference moment cannot be inverted')
        clouds[i]=(ids,xi,w,np.linalg.inv(M),float(np.sum(w*np.sum(xi*xi,axis=1))),float(np.linalg.cond(M)))
        return clouds[i]
    def fit(i,part):
        key=(i,part)
        if key in fits:return fits[key]
        ids,xi,w,invM,patch2,condition=cloud(i);pos=states[part]['pos'][:,[0,2]];dx=pos[ids]-pos[i]
        F=(dx.T@(w[:,None]*xi))@invM;res=dx-xi@F.T;res2=float(np.sum(w*np.einsum('ni,ni->n',res,res)))
        singular=np.linalg.svd(F,compute_uv=False);Jratio=float(states[part]['J'][i]/Jpre[i]);detF=float(np.linalg.det(F))
        row=dict(part=part,time_s=states[part]['time'],tau_s=states[part]['tau'],native_ID=i+2060,
                 Fxx=float(F[0,0]),Fxz=float(F[0,1]),Fzx=float(F[1,0]),Fzz=float(F[1,1]),
                 D2_min_weighted_mean_m2=res2/float(w.sum()),reference_patch_mean_square_m2=patch2/float(w.sum()),
                 D2_normalized=res2/patch2,detF=detF,J_over_JPRE=Jratio,detF_minus_Jratio=detF-Jratio,
                 singular_min=float(singular[-1]),singular_max=float(singular[0]),reference_positive_weight_neighbors=len(ids),
                 reference_M_condition=condition,J_PRE=float(Jpre[i]),J_native=float(states[part]['J'][i]),
                 kappa=float(states[part]['kappa'][i]),p_Pa=float(states[part]['p'][i]))
        fits[key]=(F,row);return fits[key]
    def edge(i,j,part):
        Fi,ri=fit(i,part);Fj,rj=fit(j,part);di=states[part]['pos'][i,[0,2]]-states[part]['pos'][j,[0,2]];xi=X[i]-X[j]
        predicted=.5*(Fi+Fj)@xi;initial=float(np.linalg.norm(xi));measured=float(np.linalg.norm(di));length=float(np.linalg.norm(predicted))
        need(initial>0 and length>0,'Degenerate pair geometry in retained diagnostic')
        row=dict(PRE_distance_over_dp=initial/DP,PRE_outside_2H=bool(initial>SUPPORT),affine_predicted_distance_over_dp=length/DP,
                 measured_over_affine_predicted=measured/length,vector_residual_over_PRE_distance=float(np.linalg.norm(di-predicted)/initial),
                 signed_length_residual_over_PRE_distance=(measured-length)/initial)
        for suffix,r in (('i',ri),('j',rj)):
            for key in ('D2_normalized','detF','J_over_JPRE','detF_minus_Jratio','singular_min','singular_max'):
                row[key+'_'+suffix]=r[key]
        return row
    onsets=[]
    # Original observations are merged by the caller; this list is solely finite-patch kinematics.
    for (i,j),(part,q) in first.items():onsets.append(dict(part=part,ID_i=i+2060,ID_j=j+2060,**edge(i,j,part)))
    tight=dict(part=minimum[1],ID_i=minimum[2]+2060,ID_j=minimum[3]+2060,**edge(minimum[2],minimum[3],minimum[1]))
    need(len(fits)==626,'Known unique onset-plus-tightest endpoint/time fit count differs')
    return onsets,[r for F,r in sorted(fits.values(),key=lambda item:(item[1]['part'],item[1]['native_ID']))],tight,clouds


def affinity_summary(rows):
    if not rows:return dict(edges=0)
    result=dict(edges=len(rows))
    for key in ('PRE_distance_over_dp','distance_over_dp','affine_predicted_distance_over_dp','measured_over_affine_predicted',
                'vector_residual_over_PRE_distance','signed_length_residual_over_PRE_distance'):
        result[key]=qs([r[key] for r in rows])
    for key in ('D2_normalized','detF','J_over_JPRE','detF_minus_Jratio','singular_min','singular_max'):
        result['endpoint_'+key]=qs([r[key+'_'+suffix] for r in rows for suffix in ('i','j')])
    result['endpoint_kappa']=qs([r['kappa_'+suffix] for r in rows for suffix in ('i','j')])
    result['endpoint_total_pair_axis_Pa']=qs([r['pair_axis_total_'+suffix+'_Pa'] for r in rows for suffix in ('i','j')])
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root full-read and one offline invocation')
    need(not CHECK.exists() and all(not q.exists() for q in FILES.values()),'Existing complete or partial audit protected')
    consumed=[old.stat(q) for q in (Path(__file__),NOTE,Path(old.__file__))]
    try:
        source=mapped(SR,7060,1001,consumed);receiver=mapped(RR,6805,91,consumed)
        need(source['done']['certified_PRE'] and not source['done']['partial'] and source['done']['completed_steps']==2000000
             and receiver['done']['completed_steps']==2180000 and source['done']['group']==receiver['done']['group']=='psi0'
             and source['done']['declared_Kernel_XML_CSV']==receiver['done']['declared_Kernel_XML_CSV']==2,'Actual retained source/full91 scope differs')
        consumed.append(old.stat(RR/'bedkeep_metadata.json'));metadata=old.read(RR/'bedkeep_metadata.json')
        need(metadata['passed'] and metadata['samples']==91 and metadata['AS_coefficient_float_reference']==float(np.float32(.5))
             and metadata['AS_exponent_float_reference']==float(np.float32(3.825)),'Actual retained AS.5/n3.825 metadata differs')
        pre=old.read22(source,1000);tpre=float(pre['time'])
        need(tpre==receiver['done']['source_actual_time_s'] and source['done']['H']==receiver['done']['H']==H,'Actual source PRE clock/H differ')
        states,observations,first,minimum=pair_rows(receiver,tpre)
        kin,fitrows,tight,clouds=affinity(states,first,minimum,pre)
        lookup={(r['part'],r['ID_i'],r['ID_j']):r for r in observations}
        onsets=[]
        for row in kin:
            combined=dict(lookup[row['part'],row['ID_i'],row['ID_j']],**{k:v for k,v in row.items() if k not in ('part','ID_i','ID_j')})
            i,j=combined['ID_i']-2060,combined['ID_j']-2060;p=combined['part']
            need(p>0,'Known retained first-close onset must follow a prior saved state')
            combined['kappa_increment_prev_saved_i']=float(states[p]['kappa'][i]-states[p-1]['kappa'][i])
            combined['kappa_increment_prev_saved_j']=float(states[p]['kappa'][j]-states[p-1]['kappa'][j]);onsets.append(combined)
        inside=[r for r in onsets if not r['PRE_outside_2H']];outside=[r for r in onsets if r['PRE_outside_2H']]
        tight=dict(lookup[tight['part'],tight['ID_i'],tight['ID_j']],**{k:v for k,v in tight.items() if k not in ('part','ID_i','ID_j')})
        examples=[r for r in onsets if r['part']==18]+[tight]+[r for r in onsets if r['part']==60]+outside
        conditioned={name:affinity_summary([r for r in inside if predicate(r)]) for name,predicate in {
            'both_axis_nonpositive':lambda r:max(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])<=0,
            'both_axis_positive':lambda r:min(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])>0,
            'mixed_axis_signs':lambda r:min(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])<=0<max(r['pair_axis_total_i_Pa'],r['pair_axis_total_j_Pa'])}.items()}
        verify(consumed)
        for key,rows in (('pair_observations',observations),('pair_onsets',onsets),('affinity',fitrows)):old.write_csv(FILES[key],rows)
        verify(consumed)
        save(CHECK,dict(stage=TAG,analysis_complete=True,physical_acceptance=False,source_actual_PRE_time_s=tpre,
            retained_receiver='c08_h18_wend_psi0_a05_w09_r1',actualAS=dict(coefficient=metadata['AS_coefficient_float_reference'],exponent=metadata['AS_exponent_float_reference']),
            samples=91,soil_materials=5000,close_radius_m=.7*DP,quantile_order=QUANTILES,
            tensor_order=dict(kk=['xx','yy','zz'],ij=['xy','yz','xz']),total_stress='effective - absolute PorePress * I; positive principal is tensile',
            pair_observation_classification=classifications(observations),first_onset_classification=classifications(onsets),
            unique_edges=len(first),unique_materials=len({i for pair in first for i in pair}) ,
            first_saved_negative_p=next(dict(part=s['part'],tau_s=s['tau'],count=int((s['p']<0).sum()),minimum_Pa=float(s['p'].min())) for s in states if (s['p']<0).any()),
            first_saved_total_positive_principal=next(dict(part=s['part'],tau_s=s['tau'],count=int((s['total'][:,-1]>0).sum())) for s in states if (s['total'][:,-1]>0).any()),
            H_actual_m=H,reference_support_m=SUPPORT,reference_weight='positive archived-formula Wendland W * native PRE current volume',
            F_scope='2x2 xz anchored-relative fixed-PRE-neighbor weighted LS',
            D2_normalization='sum(w*|dx-F*xi|^2) / sum(w*|xi|^2); self contributes zero to both',
            unique_endpoint_time_fits=len(fitrows),unique_fixed_reference_clouds=len(clouds),
            reference_neighbors_quantiles=qs([len(q[0]) for q in clouds.values()]),reference_M_condition_quantiles=qs([q[-1] for q in clouds.values()]),
            affinity_all_onsets=affinity_summary(onsets),affinity_PRE_neighbors=affinity_summary(inside),
            affinity_initially_outside_support=affinity_summary(outside),outside_support_examples=outside,
            affinity_by_true_total_axis_sign=conditioned,selected_examples=examples,
            files=[old.stat(q) for q in FILES.values()],consumed=consumed,consumed_stats_unchanged=True,
            limits=['Saved-state stress is not the unsaved clump-forming force or actual AS tensor.',
                    'FS is recomputed at save and need not equal an earlier RHS mask.',
                    'Finite PRE patches can span slip/shear discontinuities; F and D2 are smoothed kinematic diagnostics.',
                    'detF need not equal the local stage-integrated native J/J_PRE across a nonaffine finite patch.',
                    'Outside-support pairs are new material neighbors, not original reference bonds.',
                    'No instability, continuum-plasticity legitimacy, tensile-causation or physical acceptance gate is applied.'],
            solver_invocations=0,native_decodes=0,BI4_reads=0,SHA_scans=0,active_window_accesses=0))
    except Exception as error:
        if not CHECK.exists():save(CHECK,dict(stage=TAG,analysis_complete=False,first_failure=str(error),consumed=consumed,
            solver_invocations=0,native_decodes=0,BI4_reads=0,SHA_scans=0,physical_acceptance=False))
        raise


if __name__=='__main__':main()
