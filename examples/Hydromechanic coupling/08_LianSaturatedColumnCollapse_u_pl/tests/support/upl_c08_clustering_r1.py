"""Saved-coordinate clustering proxies, not a tensile-cause or fracture acceptance test."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json,struct
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
import upl_c08_as05_compare_r1 as c

T=c.T;C=T.parent;TAG='upl_c08_clustering_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');DP=.04;R=2*float(np.float32(.048));KAPPA=float(np.float32(.1))

def formal():
    rp=T/'logs/upl_c08_formal_psi0_r5_r1.run.json';r=c.read(rp);pp=Path(r['output'])/'postprocess_r5.json';post=c.read(pp)
    c.need(r['passed'] and r['solver_completed'] and r['postprocess_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==5200000 and r['saved_frames']==300 and r['consumed_stats_unchanged'],'Sealed actual r5 full solver required')
    c.need(post['passed'] and post['native_completed'] and post['global_steps']==5200000 and post['saved_frames']==300 and post['AS_coefficient']==.2 and post['actual_native_IDs']==6805,'Sealed original r5 post/native scope differs')
    native=Path(c.bind(post['native_completion'])['path']).parent;d=c.read(native/'completion.json');m=c.read(c.bind(post['bedkeep_metadata'])['path']);call=c.read(c.bind(post['native_call'])['path'])
    c.need(call['passed'] and call['actual_exit']==call['actual_Win32_exit']==0,'Actual unique r5 native reader exit differs')
    counts=dict(samples=300,completed_steps=5200000,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=1500000,fixed_marker_checks=541500,P0_bits_checks=2041500,rho_cache_bits_checks=1500000,kappa_nondecreasing_from_PRE_checks=1500000,nonempty_signed_intervals=300,plane_gap_checks=3000000)
    c.need(d['passed'] and d['stage']=='upl_c08_bedkeep_formal_native_r1' and all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['saved_steps_checked_against_formal_profile'],'Original300-frame full native guards differ')
    c.need(m['passed'] and m['samples']==m['keep_policy_headers']==m['AS_active_true_headers']==300 and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_policy']=='ReleaseOnly','Original full keep/AS header scope differs')
    before=[c.stat(rp),c.stat(pp),c.bind(r['actual_call']),c.bind(post['native_call']),c.bind(post['native_completion']),c.bind(post['bedkeep_metadata']),c.bind(r['source_pre_file'])]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv','history.csv'):
        path=native/leaf;before.append(c.bind(next(e for e in call['outputs'] if Path(e['path']).samefile(path))))
    layout=c.table(native/'typed22_layout.csv');fields=[('time','<f8')];c.need(len(layout)==22,'Original full22 schema required')
    for row,(name,kind,width) in zip(layout,c.SCHEMA):
        c.need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,c.TYPES[kind].itemsize*width),'Full native layout changed');fields.append((name,c.TYPES[kind],(6805,width)))
    dtype=np.dtype(fields);c.need(dtype.itemsize==8+6805*212 and (native/'typed22.bin').stat().st_size==12+300*dtype.itemsize,'Actual full300 header/payload extent differs')
    clocks=c.table(native/'clocks.csv');history=c.table(native/'history.csv');c.need(len(clocks)==len(history)==300,'Actual full300 histories required')
    return dict(label='epsilon0p2_full_r5',epsilon=.2,native=native,dtype=dtype,done=d,clocks=clocks,history=history,before=before,run=r,frames=300,plot_parts=(22,65,119,299))

def quant(values):
    values=np.asarray(values);values=values[np.isfinite(values)]
    return [float(v) for v in np.quantile(values,(0,.05,.5,.95,1.))] if len(values) else [None]*5

def corr(x,y):
    if len(x)<2:return None
    x=x-x.mean();y=y-y.mean();den=np.sqrt(float(x@x)*float(y@y));return float(x@y/den) if den else None

def measures(frame):
    soil=frame['Idp'][:,0]>=2060;x=frame['Posd'][soil][:,[0,2]];fixed=frame['Posd'][~soil][:,[0,2]];ids=frame['Idp'][soil,0];c.need(len(x)==5000 and len(fixed)==1805 and np.array_equal(ids,np.arange(2060,7060)),'Original fixed soil/marker IDs differ')
    tree=cKDTree(x);dist,index=tree.query(x,k=3,workers=1);self_id=np.arange(5000);other=index!=self_id[:,None];order=np.argsort(np.where(other,dist,np.inf),axis=1)[:,:2];rr=np.take_along_axis(dist,order,axis=1);neighbors=np.take_along_axis(index,order,axis=1);r1,r2=rr[:,0],rr[:,1];ratio=np.divide(r1,r2,out=np.full(5000,np.nan),where=r2>0)
    nn=r1/DP;J=frame['PoroVolumeRatio'][soil,0];scaled=r1/(DP*np.sqrt(J));degree=tree.query_ball_point(x,1.5*DP,return_length=True,workers=1)-1
    pairs=tree.query_pairs(.7*DP,output_type='ndarray');separation=np.linalg.norm(x[pairs[:,0]]-x[pairs[:,1]],axis=1) if len(pairs) else np.empty(0);keep=separation<.7*DP;pairs=pairs[keep];separation=separation[keep]
    near=neighbors[:,0];mutual=np.flatnonzero((near[near]==self_id)&(self_id<near));mutual_pairs=np.column_stack((mutual,near[mutual]));isolated=(r1[mutual]<.7*DP)&(ratio[mutual]<.5)&(ratio[near[mutual]]<.5)
    fs=frame['FSType'][soil,0];surface=np.isin(fs,(2,3));c.need(surface.any(),'Original free-seepage native coverage empty');fsdist=cKDTree(x[surface]).query(x,workers=1)[0];walldist=cKDTree(fixed).query(x,workers=1)[0];bulk=(~surface)&(fsdist>=R)&(walldist>=R)
    pw=frame['PorePress'][soil,0].astype(float);kap=frame['Kplastic'][soil,0].astype(float);por=frame['PoroPorosity'][soil,0];sk=frame['SigmaState_kk'][soil]-pw[:,None];ij=frame['SigmaState_ij'][soil];S=np.zeros((5000,3,3));S[:,(0,1,2),(0,1,2)]=sk;S[:,0,1]=S[:,1,0]=ij[:,0];S[:,1,2]=S[:,2,1]=ij[:,1];S[:,0,2]=S[:,2,0]=ij[:,2];tensile=np.linalg.eigvalsh(S)[:,-1]
    return dict(ids=ids,x=x,fixed=fixed,nn=nn,scaled=scaled,r1r2=ratio,r2=r2,near=near,pairs=pairs,separation=separation,mutual_pairs=mutual_pairs,isolated=isolated,degree=degree,bulk=bulk,surface=surface,fsdist=fsdist,walldist=walldist,p=pw,J=J,n=por,kappa=kap,tensile=tensile)

def summarize(q,context):
    cohorts={'all_soil':np.ones(5000,dtype=bool),'kappa_ge_0p1f':q['kappa']>=KAPPA,'kappa_lt_0p1f':q['kappa']<KAPPA,'geometric_interior':q['bulk'],'FS23_or_within_kernelR':q['fsdist']<R,'within_kernelR_of_fixed_B':q['walldist']<R};rows=[]
    for label,mask in cohorts.items():
        count=int(mask.sum());r=dict(**context,cohort=label,soil_count=count)
        for prefix,values in (('rNN_over_dp',q['nn'][mask]),('rNN_over_dp_sqrtJ_proxy',q['scaled'][mask]),('r1_over_r2',q['r1r2'][mask])):
            r.update({prefix+'_'+key:value for key,value in zip(('min','q05','median','q95','max'),quant(values))})
        within=mask[q['pairs'][:,0]]&mask[q['pairs'][:,1]];mutual=q['mutual_pairs'];both=mask[mutual[:,0]]&mask[mutual[:,1]];close=mask&(q['nn']<.7);sparse=mask&(q['degree']<4)
        r.update(pair_both_in_cohort_lt_0p5dp=int(np.count_nonzero(within&(q['separation']<.5*DP))),pair_both_in_cohort_lt_0p7dp=int(within.sum()),nodes_with_any_neighbor_lt_0p7dp=int(close.sum()),mutual_nearest_pairs_both_in_cohort=int(both.sum()),mutual_isolated_close07_r1r2_lt05_pairs_both=int(np.count_nonzero(both&q['isolated'])),r2_zero_nodes=int(np.count_nonzero(mask&(q['r2']==0))),soil_neighbors_r1p5dp_lt4_nodes=int(sparse.sum()),geometric_interior_low_degree_nodes=int(np.count_nonzero(sparse&q['bulk'])),geometric_interior_rNN_gt1p5dp_nodes=int(np.count_nonzero(mask&q['bulk']&(q['nn']>1.5))),total_tensile_nodes=int(np.count_nonzero(mask&(q['tensile']>0))),negative_p_nodes=int(np.count_nonzero(mask&(q['p']<0))),close07_nodes_total_tensile_fraction=float(np.mean(q['tensile'][close]>0)) if close.any() else None)
        for name in ('p','J','n','kappa','tensile'):
            values=q[name][mask];r[name+'_mean']=float(values.mean()) if count else None;r[name+'_min']=float(values.min()) if count else None;r[name+'_max']=float(values.max()) if count else None;r['corr_rNN_dp_with_'+name]=corr(q['nn'][mask],values);r['corr_spacing_proxy_with_'+name]=corr(q['scaled'][mask],values)
        rows.append(r)
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read before one saved-state geometry diagnostic');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial clustering result protected')
    comparison=c.read(c.CHECK);c.need(comparison['passed'] and comparison['clock_and_steps_exact'] and comparison['actual_matched_samples']==66,'Sealed actual epsilon comparison required');first=formal();second=c.load(c.SPECS[1]);second.update(frames=66,plot_parts=(65,));prefix_path=T/'logs/upl_c08_stage_trace_window_GPU_r1.prefix_r1.check.json';prefix=c.read(prefix_path)
    c.need(prefix['passed'] and prefix['actual_common_frames']==66 and prefix['all22_and_actual_time_payload_byte_exact'] and prefix['signed_clock_header_and_rows_byte_exact'] and prefix['layout_byte_exact'] and prefix['consumed_stats_unchanged'] and prefix['new_original_header']==[6805,22,66] and prefix['old_original_header']==[6805,22,300] and not prefix['headers_rewritten'],'Genuine66/300 prefix proof required; no header/count substitution')
    c.need(any(Path(e['path']).samefile(first['native']/'typed22.bin') for e in prefix['consumed']),'Prefix proof does not bind this formal payload');c.need(first['run']['source_pre_file']==second['run']['source_pre_file'] and first['done']['source_actual_time_s']==second['done']['source_actual_time_s'],'Original same PRE/clock required')
    before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(prefix_path),c.stat(c.CHECK),c.bind(next(e for e in comparison['consumed'] if Path(e['path']).samefile(c.__file__)))]+[c.bind(e) for e in prefix['consumed']]+first['before']+second['before'];rows=[];pictures=[];processed=0
    for g in (first,second):
        with (g['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,g['frames']),'Actual native header must retain its own300/66 count')
            for part in range(g['frames']):
                raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Short native record');frame=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,step=c.inspect(frame,g,part);q=measures(frame);context=dict(group=g['label'],epsilon=g['epsilon'],part=part,time_s=time,tau_s=tau,completed_step=step);rows.extend(summarize(q,context));processed+=1
                if part in g['plot_parts']:pictures.append(dict(**context,**{key:q[key].copy() for key in ('x','fixed','nn','pairs','kappa','surface','bulk','degree')}))
            c.need(f.read(1)==b'','Extra bytes beyond genuine original frame count')
    csv=Path(str(PREFIX)+'_history.csv');c.write(csv,rows);c.need(len(pictures)==5 and processed==366,'Explicit300+66 state/5-plot accounting differs')
    plt.rcParams.update({'font.size':8,'figure.dpi':170});fig,axes=plt.subplots(2,3,figsize=(17,10),sharex=True,sharey=True,layout='constrained');nn=np.concatenate([q['nn'] for q in pictures]);xy=np.concatenate([q['x'] for q in pictures]);norm=Normalize(float(nn.min()),float(nn.max()),clip=False);limits=(float(xy[:,0].min()-2*DP),float(xy[:,0].max()+2*DP),float(xy[:,1].min()-2*DP),float(xy[:,1].max()+2*DP))
    for ax,q in zip(axes.ravel(),pictures):
        x=q['x'];fixed=q['fixed'];surface=q['surface'];high=q['kappa']>=KAPPA;interior_sparse=q['bulk']&(q['degree']<4);ax.scatter(fixed[:,0],fixed[:,1],s=3,c='.7',marker='s',linewidths=0,zorder=0)
        if len(q['pairs']):ax.add_collection(LineCollection(x[q['pairs']],colors='red',linewidths=.55,alpha=.65,zorder=2))
        for mask,marker in ((~surface,'o'),(surface,'^')):ax.scatter(x[mask,0],x[mask,1],c=q['nn'][mask],norm=norm,cmap='viridis',s=7,marker=marker,linewidths=0,zorder=1)
        ax.scatter(x[high,0],x[high,1],s=10,facecolors='none',edgecolors='.2',linewidths=.2,zorder=3);ax.scatter(x[interior_sparse,0],x[interior_sparse,1],s=22,marker='x',c='black',linewidths=.7,zorder=4);ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title='epsilon=%g, actual tau=%.12g s'%(q['epsilon'],q['tau']));ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.15)
    axes.ravel()[-1].axis('off');handles=[Line2D([],[],marker='^',ls='',c='.3',label='Native soil FS2/3'),Line2D([],[],marker='s',ls='',c='.7',label='Retained fixed markers'),Line2D([],[],c='red',label='Unique soil pairs r<.7dp'),Line2D([],[],marker='o',ls='',mfc='none',mec='.2',label='Current kappa>=.1f'),Line2D([],[],marker='x',ls='',c='black',label='Interior soil degree<4 within1.5dp')];axes.ravel()[-1].legend(handles=handles,loc='upper left',fontsize=8);fig.colorbar(plt.cm.ScalarMappable(norm=norm,cmap='viridis'),ax=axes.ravel()[:5].tolist(),label='Raw nearest-other distance / dp; complete five-state range',shrink=.7)
    fig.suptitle('Fixed5000 material IDs, full-domain ROI; raw neighbor geometry, no smoothing or cause claim\nCompression/shear/FS effects remain confounders; sparse proxy is not an identified internal crack')
    png=Path(str(PREFIX)+'_neighbors.png');fig.savefig(png);plt.close(fig);c.need(all(c.stat(e['path'])==e for e in before),'Sealed input/helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,actual_native_frames_processed=processed,epsilon0p2_full_frames=300,epsilon0p5_window_frames=66,epsilon0p2_duplicate_window_payload_read=False,epsilon0p2_first66_reused_from_genuine_passed_prefix=True,headers_or_counts_rewritten=False,soil_IDs_per_frame=5000,fixed_material_ROI='all original soil IDs2060..7059',typed22_all_selected_frames_finite_and_ID_checked=True,NN_coordinate_geometry='native double Posd xz',dp_m=DP,nearest_spacing_proxy='rNN/(dp*sqrt(J_i)); isotropic2D equal-thickness proxy, not deformation-gradient correction',r1r2_zero_denominator_reported_not_filled=True,mutual_isolated_pair_definition='mutual nearest, r1<.7dp, both r1/r2<.5; descriptive only',cohort_kappa_threshold_float=KAPPA,cohort_membership_evolves_with_saved_kappa=True,geometric_interior_definition='not FS2/3 and >=kernelR from native FS2/3 points and fixed B markers',kernel_R_m=R,low_connectivity_proxy='soil degree<4 within1.5dp; internal proxy only after geometric-interior mask',Delaunay_or_outer_hull_long_edges_not_used=True,FS_zone_does_not_distinguish_outer_and_new_internal_faces=True,total_tensile_measure='largest eigenvalue of native double sigmaeff - full p I; not GPU float AS eig bits',total_tension_negative_p_association_partly_algebraic=True,correlation_not_tensile_causation=True,thresholds_are_descriptive_not_physical_acceptance_gates=True,selected_neighbor_plot_states=[{k:q[k] for k in ('group','part','time_s','tau_s')} for q in pictures],plot_common_window_xz_m=list(limits),all_soil_points_displayed=True,physical_acceptance=False,dense_trace_read=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(csv),c.stat(png)])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('C08_CLUSTERING_DIAGNOSTIC_READY',CHECK,flush=True)

if __name__=='__main__':main()
