"""One frozen-geometry shift proposal per saved state; no state transport or solver."""
import argparse,json,math,struct
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_clustering_r1 as cluster
import upl_c08_wall_geometry_r1 as kernel

c=cluster.c;T=c.T;TAG='upl_c08_shift_frozen_r1';PREFIX=T/'figures'/TAG
DP=.04;H=float(np.float32(.048));R=float(np.float32(2*np.float32(H)));R2=float(np.float32(np.float32(R)*np.float32(R)))
DT=.0000025;COEF=-2.;CAP=float(np.float32(.1*DP));V0=float(np.float32(3.316))/2072.5;MASS=float(np.float32(3.316));GAMMA=1000*9.80665
TARGETS=((.30,4120000),(.66,4264000),(1.2,4480000),(3.,5200000))

def write(path,rows):pd.DataFrame(rows).to_csv(path,index=False,mode='x',float_format='%.17g')
def qstats(values):
    a=np.asarray(values,dtype=float)
    return dict(min=float(a.min()),median=float(np.median(a)),RMS=float(np.sqrt(np.mean(a*a))),max=float(a.max())) if len(a) else dict.fromkeys(('min','median','RMS','max'))

def cloud(frame):
    ids=frame['Idp'][:,0];soil=ids>=2060;xall=frame['Posd'][:,[0,2]].copy();x=xall[soil];fixed=xall[~soil];J=frame['PoroVolumeRatio'][:,0];rho=frame['native_Rhop'][:,0].astype(float)
    c.need(len(x)==5000 and len(fixed)==1805 and np.array_equal(ids[soil],np.arange(2060,7060)),'Original5000 material soil IDs required')
    c.need(np.all(J>1-float(np.float32(.35))) and np.all(rho>0),'Native valid J/rho required; fixed derived-volume zeros are not volumes')
    V=V0*J;c.need(np.array_equal(V[soil],frame['PoroCurrentVolume'][soil,0]),'Actual V0J soil ledger differs')
    speed=np.linalg.norm(frame['Vel'][soil].astype(float),axis=1);surface=np.isin(frame['FSType'][soil,0],(2,3));c.need(surface.any(),'Nonempty native FS2/3 required')
    tree=cKDTree(xall);stree=cKDTree(x);frozen_fs=cKDTree(x[surface]).query(x,workers=1)[0]<=R;frozen_wall=cKDTree(fixed).query(x,workers=1)[0]<=R
    degree=stree.query_ball_point(x,1.5*DP,return_length=True,workers=1)-1;weights=(V,MASS/rho);grads=np.zeros((2,5000,2));Dpos=np.zeros((2,5000));fixed_hits=np.zeros(5000,dtype=int);fs_hits=np.zeros(5000,dtype=int);mineig=np.zeros(5000);condition=np.full(5000,np.nan)
    surf_all=np.zeros(len(ids),dtype=bool);surf_all[soil]=surface
    # Existing audited float Cubic factor; native coordinate differences stand in for unsaved packed PosCell.
    for i,slot in enumerate(np.flatnonzero(soil)):
        js=np.asarray(sorted(tree.query_ball_point(xall[slot],kernel.SEARCH)),dtype=int);d=(xall[slot]-xall[js]).astype(np.float32);rr=(d[:,0]*d[:,0]+d[:,1]*d[:,1]).astype(np.float32);keep=(rr<=R2)&(rr>=kernel.LOWER);js,d,rr=js[keep],d[keep],rr[keep]
        if not len(js):continue
        fac=np.asarray([kernel.cubic(float(v))[1] for v in rr],dtype=np.float32);grad=(d*fac[:,None]).astype(float);dd=d.astype(float);fixed_hits[i]=np.count_nonzero(ids[js]<2060);fs_hits[i]=np.count_nonzero(surf_all[js])
        for k,w in enumerate(weights):grads[k,i]=np.sum(w[js,None]*grad,axis=0);Dpos[k,i]=-np.sum(w[js]*np.einsum('ij,ij->i',dd,grad))
        moment=-np.einsum('i,ij,ik->jk',V[js],dd,grad);eig=np.linalg.eigvalsh((moment+moment.T)*.5);mineig[i]=eig[0]
        if eig[0]>0:condition[i]=eig[-1]/eig[0]
    frozen_low=(degree<4)|(mineig<=0)|~np.isfinite(condition)
    interior=~(surface|frozen_fs|frozen_wall|frozen_low|(fixed_hits>0)|(fs_hits>0))
    raw=(DT*COEF*H*speed[None,:,None]*grads).astype(np.float32);proposals=np.clip(raw,-CAP,CAP).astype(float)
    normal=frame['FSNormal'][soil][:,[0,2]].astype(float);length=np.linalg.norm(normal,axis=1);normal_valid=surface&(length>0);unit=np.zeros_like(normal);unit[normal_valid]=normal[normal_valid]/length[normal_valid,None]
    return dict(ids=ids[soil],x=x,surface=surface,normal_valid=normal_valid,unit=unit,interior=interior,proposals=proposals,Dpos=Dpos,speed=speed,J=J[soil],rho=rho[soil],fixed_hits=fixed_hits,fs_hits=fs_hits,degree=degree,mineig=mineig,condition=condition,frozen_low=frozen_low,frozen_fs=frozen_fs,frozen_wall=frozen_wall)

def geometry(x,mask,surface):
    tree=cKDTree(x);distance,index=tree.query(x,k=2,workers=1);selfidx=np.arange(len(x));nn=np.min(np.where(index!=selfidx[:,None],distance,np.inf),axis=1)
    pairs=tree.query_pairs(.7*DP,output_type='ndarray');sep=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1) if len(pairs) else np.empty(0);pairs=pairs[sep<.7*DP];sep=sep[sep<.7*DP]
    both=mask[pairs[:,0]]&mask[pairs[:,1]];gap=cKDTree(x[~surface]).query(x[surface],workers=1)[0] if np.any(~surface) else np.empty(0)
    out={('NN_over_dp_'+k):v for k,v in qstats(nn[mask]/DP).items()};out.update({('FS_to_nonFS_nearest_m_'+k):v for k,v in qstats(gap).items()})
    out.update(all_soil_pairs_lt0p5dp=int(np.count_nonzero(sep<.5*DP)),all_soil_pairs_lt0p7dp=len(pairs),cohort_both_pairs_lt0p5dp=int(np.count_nonzero(both&(sep<.5*DP))),cohort_both_pairs_lt0p7dp=int(both.sum()),min_soil_x_m=float(x[:,0].min()),min_soil_z_m=float(x[:,1].min()),soil_x_below0=int(np.count_nonzero(x[:,0]<0)),soil_z_below0=int(np.count_nonzero(x[:,1]<0)))
    return out

def summary(q,delta,mask,context,weight,scope):
    row=dict(**context,weight=weight,proposal_scope=scope,soil_count=5000,eligible_count=int(mask.sum()),nonzero_proposal_count=int(np.count_nonzero(np.linalg.norm(delta,axis=1)>0)),coordinate_changed_count=int(np.count_nonzero(np.any(q['x']+delta!=q['x'],axis=1))),frozen_surface_or_halo=int(np.count_nonzero(q['surface']|q['frozen_fs']|(q['fs_hits']>0))),frozen_fixed_band=int(np.count_nonzero(q['frozen_wall']|(q['fixed_hits']>0))),low_support_or_rank_count=int(q['frozen_low'].sum()),native_FS23=int(q['surface'].sum()),FS_normal_undefined_count=int(np.count_nonzero(q['surface']&~q['normal_valid'])))
    length=np.linalg.norm(delta,axis=1);normal=np.einsum('ij,ij->i',delta,q['unit'])[q['normal_valid']]
    for label,values in (('delta_norm_m',length[mask]),('FS_normal_delta_m',normal),('manufactured_hydrostatic_delta_p_Pa',-GAMMA*delta[mask,1]),('manufactured_unit_x_gradient_delta_J',delta[mask,0]),('manufactured_unit_x_isotropic_sigma_Frob_Pa',np.sqrt(3.)*np.abs(delta[mask,0])),('manufactured_unit_xz_gradient_delta_kappa',delta[mask,0]+delta[mask,1])):
        row.update({label+'_'+k:v for k,v in qstats(values).items()})
    row['constant_fields_delta_max']=0.
    for prefix,x in (('before',q['x']),('after_one_proposal',q['x']+delta)):row.update({prefix+'_'+k:v for k,v in geometry(x,mask,q['surface']).items()})
    return row

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();c.need(args.execution_authorized,'Root full-read before one frozen component required');c.need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial component preserved')
    result=dict(stage=TAG,passed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0);files=[];before=[]
    try:
        g=cluster.formal();c.need(float(kernel.H)==H and kernel.R2==R2 and kernel.VOL0==V0,'Audited Cubic constants differ')
        before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(cluster.__file__),c.stat(c.__file__),c.stat(kernel.__file__)]+g['before'];summaries=[];points=[];differences=[];selected=[]
        with (g['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,300),'Original full300 header required; no rewrite')
            for nominal,step in TARGETS:
                hits=[i for i,r in enumerate(g['clocks']) if int(r['completed_step'])==step];c.need(len(hits)==1,'Unique actual completed Step required for each requested state');part=hits[0];f.seek(12+part*g['dtype'].itemsize);raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short original selected record');frame=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,actualstep=c.inspect(frame,g,part);c.need(actualstep==step,'Selected actual clock/Step differs')
                context=dict(requested_nominal_tau_s=nominal,part=part,time_s=time,actual_tau_s=tau,completed_step=step);selected.append(context);q=cloud(frame)
                for wi,weight in enumerate(('V0J','legacy_m0_over_native_rho')):
                    delta=q['proposals'][wi];restricted=delta*q['interior'][:,None]
                    for scope,move,mask in (('all_soil_raw',delta,np.ones(5000,dtype=bool)),('qualified_interior_only',restricted,q['interior'])):summaries.append(summary(q,move,mask,context,weight,scope))
                    for i,identity in enumerate(q['ids']):
                        normal=float(delta[i]@q['unit'][i]) if q['normal_valid'][i] else None;points.append(dict(**context,weight=weight,native_id=int(identity),x_m=float(q['x'][i,0]),z_m=float(q['x'][i,1]),J=float(q['J'][i]),native_rho=float(q['rho'][i]),speed_m_s=float(q['speed'][i]),native_FS23=bool(q['surface'][i]),qualified_interior=bool(q['interior'][i]),fixed_stencil_neighbors=int(q['fixed_hits'][i]),FS23_stencil_neighbors=int(q['fs_hits'][i]),soil_degree_within1p5dp=int(q['degree'][i]),moment_min_eigenvalue=float(q['mineig'][i]),moment_condition=float(q['condition'][i]) if np.isfinite(q['condition'][i]) else None,raw_Dpos=float(q['Dpos'][wi,i]),raw_delta_x_m=float(delta[i,0]),raw_delta_z_m=float(delta[i,1]),raw_delta_norm_m=float(np.linalg.norm(delta[i])),raw_FS_normal_delta_m=normal,interior_delta_x_m=float(restricted[i,0]),interior_delta_z_m=float(restricted[i,1])))
                for label,mask in (('all_soil',np.ones(5000,dtype=bool)),('qualified_interior',q['interior'])):differences.append(dict(**context,cohort=label,count=int(mask.sum()),**{'proposal_difference_norm_m_'+k:v for k,v in qstats(np.linalg.norm(q['proposals'][0]-q['proposals'][1],axis=1)[mask]).items()}))
        for leaf,rows in (('summary',summaries),('proposals',points),('weight_difference',differences)):path=Path(str(PREFIX)+'_'+leaf+'.csv');write(path,rows);files.append(path)
        plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        for weight,color in (('V0J','C0'),('legacy_m0_over_native_rho','C1')):
            for scope,style in (('all_soil_raw','-'),('qualified_interior_only','--')):
                rows=[r for r in summaries if r['weight']==weight and r['proposal_scope']==scope];x=[r['actual_tau_s'] for r in rows];label=weight+' / '+scope
                for ax,key,scale in ((axes[0,0],'delta_norm_m_RMS',1000),(axes[0,1],'delta_norm_m_max',1000),(axes[1,1],'FS_normal_delta_m_RMS',1000)):ax.plot(x,[None if r[key] is None else r[key]*scale for r in rows],style,c=color,marker='o',label=label)
                axes[1,0].plot(x,[r['after_one_proposal_all_soil_pairs_lt0p7dp']-r['before_all_soil_pairs_lt0p7dp'] for r in rows],style,c=color,marker='o',label=label)
        for ax,title,ylabel in zip(axes.ravel(),('One-move cohort RMS','One-move cohort maximum','Change in all-soil r<.7dp pairs','Native FS normal-motion RMS'),('Proposed displacement [mm]','Proposed displacement [mm]','After minus before pairs','Proposed normal displacement [mm]')):ax.set(title=title,xlabel='Actual saved tau since certified PRE [s]',ylabel=ylabel);ax.grid(alpha=.25);ax.legend(fontsize=5)
        fig.suptitle('Independent single proposals at four frozen states; no iteration, state transport or physical advance');path=Path(str(PREFIX)+'.png');fig.savefig(path);plt.close(fig);files.append(path)
        c.need(all(c.stat(e['path'])==e for e in before),'Retained input/helper changed')
        result.update(passed=True,selected_actual_states=selected,actual_records_read=4,original_native_header=[6805,22,300],selected_all22_finite_ID_clock_checks=True,soil_IDs_per_state=5000,proposals_per_state_per_weight=1,applied_to_original_state=False,manufactured_fields_only_not_native_gradient_inference=True,ShiftCoef=COEF,dt_s=DT,KernelH_m=H,dp_m=DP,component_cap_m=CAP,ShiftTFS_for_raw_proposal=0,qualified_mask_frozen_before_proposal=True,low_support_definition='fewer than4 soil neighbours within1.5dp or nonpositive/invalid symmetric moment eigenvalue',full_soil_fixed_sources='all saved fixed J included; BoundMode and packed positions unavailable',interior_stencils_have_no_saved_fixed_or_FS23_sources=True,field_transport_not_implemented_or_accepted=True,visual_QA_pending=True)
    except Exception as error:result['first_failure']=str(error)
    result.update(consumed=before,files=[c.stat(p) for p in files if p.exists()]);check=Path(str(PREFIX)+'.check.json')
    with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
