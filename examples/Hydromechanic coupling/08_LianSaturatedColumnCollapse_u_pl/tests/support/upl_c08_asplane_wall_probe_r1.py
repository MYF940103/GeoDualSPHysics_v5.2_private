"""Sealed AS1-53/AS0-54 local bed-fit diagnostics; saved-state proxy, never a solver replay."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import upl_c08_plane_window_review_r1 as w
import upl_c08_wall_geometry_r1 as g
import upl_c08_wall_stress_decompose_r1 as s

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_asplane_wall_probe_r1';PREFIX=T/'figures'/TAG
FOLDERS={'AS1':T/'outputs/upl_c08_asplane_partial_r1','AS0':T/'outputs/upl_c08_plane_partial_r1'}
COUNTS={'AS1':(53,4212000),'AS0':(54,4216000)}
NORMALS=T/'outputs/upl_c08_asplane_window_GPU_r1/CfgInit_NormalsGhost.vtk'
NAMES=('J','normal_pressure_head','vx','vy','vz','sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_xz','sigma_yz')
GN=float(np.float32(-9.81));RHOW=1000.;need,read,stat=w.need,w.read,w.stat

def bind(entry):
    need(stat(Path(entry['path']))==entry,'Closed file changed: '+entry['path']);return entry
def csvout(suffix,rows):
    p=Path(str(PREFIX)+'_'+suffix+'.csv');need(rows,'Empty '+suffix+' table')
    with p.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return p
def stencil(tree,soil,centre):
    return [k for k in sorted(tree.query_ball_point(centre,g.SEARCH)) if np.float32(np.dot(centre-soil[k],centre-soil[k]))<=g.R2]

def sealed():
    before=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md')),*[stat(Path(m.__file__)) for m in (w,g,s)],stat(NORMALS)];sets={}
    for model,folder in FOLDERS.items():
        cp=L/(folder.name+'.check.json');c=read(cp);before.append(stat(cp))
        need(c['passed'] and c['original_saved_native_guards_passed'] and c['consumed_stats_unchanged'] and c['diagnostic_partial'] and not c['runtime_success_claimed'],'Closed saved-prefix native check required')
        need(Path(bind(c['native_completion'])['path']).samefile(folder/'completion.json'),'Completion binding differs');before.append(c['native_completion'])
        call=read(Path(bind(c['reader_call'])['path']));before.append(c['reader_call']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Actual unique reader exit differs')
        for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv'):before.append(bind(next(e for e in c['files'] if Path(e['path']).samefile(folder/leaf))))
        n,end=COUNTS[model];bundle=w.load(folder,n,end);a,d,clock,hist=bundle
        counts=dict(ledger_checks=5000*n,fixed_marker_checks=1800*n,P0_bits_checks=6800*n,rho_cache_bits_checks=5000*n,kappa_nondecreasing_from_PRE_checks=5000*n,nonempty_signed_intervals=n,plane_gap_checks=10000*n)
        need(all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original native safety/coverage differs')
        need(d['diagnostic_partial'] and not d['runtime_success_claimed'] and not d['completed_runtime_Run_csv_checked'] and not d['launch_plan_rewritten'] and d['original_launch_plan_samples']==60 and d['used_launch_plan_prefix_samples']==n and d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'Saved prefix/plane policy differs')
        if model=='AS1':
            before.append(bind(c['AS_metadata']));need(Path(c['AS_metadata']['path']).samefile(folder/'AS_metadata.json'),'AS metadata path differs');m=read(folder/'AS_metadata.json')
            need(m['passed'] and m['stage']=='upl_c08_asplane_partial_r1.AS' and m['expected_AS'] and m['samples']==m['AS_active_true_headers']==m['AS_policy_present_headers']==m['metadata_header_scans']==n and m['AS_policy_when_enabled']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(2.55)) and m['core_array_decode_passes']==1 and not m['core_numerical_guards_modified'] and not m['runtime_success_claimed'],'Original per-frame AS policy differs')
        sets[model]=bundle
    need(sets['AS1'][1]['source_actual_time_s']==sets['AS0'][1]['source_actual_time_s'],'Actual PRE clocks differ')
    b,norm,mk=g.normals_vtk(NORMALS);tol=1e-6*.04
    need(mk[828]==11 and norm[828,0]==0 and norm[828,2]>0 and abs(b[828,2]+.06)<=tol,'Actual828 bottom normal differs')
    walls=np.flatnonzero((np.arange(len(b))<1800)&(mk==11)&(norm[:,0]==0)&(norm[:,2]>0)&(np.abs(b[:,0]-b[828,0])<=.08+8*np.finfo(float).eps*max(1.,abs(b[828,0])))&((np.abs(b[:,2]+.02)<=tol)|(np.abs(b[:,2]+.06)<=tol)))
    need(828 in walls and len(walls)>1,'Actual two-row local bed selection is empty')
    for data,_,_,_ in sets.values():need(all(np.array_equal(x['Posd'][:1800],b[:1800]) for x in data),'Initialized actual B differs from native fixed positions')
    return sets,b[:,[0,2]],norm[:,[0,2]],mk,walls,before

def geometry(tree,soil,js,ids,centre,original):
    r,nearest=g.support(tree,soil,js,ids,centre,original);ix=stencil(tree,soil,centre)
    positive=[k for k in ix if g.cubic(float(np.dot(centre-soil[k],centre-soil[k])))[0]>0]
    design=np.column_stack((np.ones(len(positive)),(soil[positive]-centre)/float(g.H))) if positive else np.empty((0,3))
    sv=np.linalg.svd(design,compute_uv=False) if positive else np.empty(0);rank=int(np.linalg.matrix_rank(design)) if positive else 0
    r.update(positive_stencil_affine_rank=rank,sv0=float(sv[0]) if len(sv)>0 else 0.,sv1=float(sv[1]) if len(sv)>1 else 0.,sv2=float(sv[2]) if len(sv)>2 else 0.,source_J_saturated=bool(ix and np.all(np.isfinite(js[ix])) and np.all(js[ix]>g.SOLID0)),centre_x_m=float(centre[0]),centre_z_m=float(centre[1]),shift_to_original_GP_m=float(np.linalg.norm(centre-original)))
    return r,nearest,ix

def fields(tree,soil,js,ids,field,centre,GP,B,bn,geo,nearest,ix):
    """Same saved stencil and anchor, with explicit native-to-kernel tensor member mapping."""
    if not geo['geometry_gate']:return [],[]
    m=np.zeros((3,3));rhs=np.zeros((3,11));arhs=np.zeros((3,3));manufactured=np.column_stack((np.ones(len(soil)),1024+16*soil[:,0]-32*soil[:,1],-2048+8*soil[:,0]+64*soil[:,1]))
    for k in ix:
        d=centre-soil[k];wab,fac=g.cubic(float(np.dot(d,d)));row=g.VOL0*float(js[k])*np.array([wab,fac*d[0],fac*d[1]])
        m+=np.outer(row,np.r_[1.,d]);rhs+=np.outer(row,field[k]);arhs+=np.outer(row,manufactured[k])
    q=np.linalg.solve(m,rhs);v=field[nearest]-(centre-soil[nearest])@q[1:]+(centre-GP)@q[1:]
    out=v.copy();out[1]+=RHOW*GN*B[1];out[2:5]=-v[2:5];out[5:]+=bn@q[1:,5:]
    rows=[]
    for c,name in enumerate(NAMES):rows.append(dict(field=name,source_min=float(field[ix,c].min()),source_max=float(field[ix,c].max()),anchored_original_GP=float(v[c]),B_policy_value=float(out[c]),physical_gradient_x=float(-q[1,c]),physical_gradient_z=float(-q[2,c]),original_GP_finite=bool(math.isfinite(v[c])),B_policy_finite=bool(math.isfinite(out[c])),value_policy=('J mirrored from GP' if c==0 else 'absolute p restored at B' if c==1 else 'derivative image; native physical wall v stays0' if c<5 else 'NoSlip effective stress extrapolated to B')))
    qa=np.linalg.solve(m,arhs);aff=[];scale=max(1.,float(np.abs(manufactured[ix]).max()));budget=32768*np.finfo(float).eps*max(1.,geo['cond_hscaled_inf'])*scale
    for name,target in (('original_GP',GP),('physical_B',B)):
        actual=manufactured[nearest]-(centre-soil[nearest])@qa[1:]+(centre-target)@qa[1:];truth=np.array([1.,1024+16*target[0]-32*target[1],-2048+8*target[0]+64*target[1]])
        for c,basis in enumerate(('constant','linear_xz_a','linear_xz_b')):aff.append(dict(target=name,basis=basis,actual=float(actual[c]),truth=float(truth[c]),absolute_error=float(abs(actual[c]-truth[c])),existing_condition_scaled_roundoff_budget=budget))
    return rows,aff

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one offline diagnostic');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial products protected')
    sets,b,norm,mk,walls,before=sealed();rows=[];fieldrows=[];affrows=[];candidates=[];local=[];summaries=[];scatter={}
    xmin=float(b[walls,0].min()-2*float(g.RADIUS));xmax=float(b[walls,0].max()+2*float(g.RADIUS));zmin=float(b[walls,1].min()-float(g.RADIUS));zmax=float((b[walls]+norm[walls])[:,1].max()+2*float(g.RADIUS))
    for model,(data,done,clocks,history) in sets.items():
        for part,x in enumerate(data):
            ids=x['Idp'][1800:,0];soil=x['Posd'][1800:][:,[0,2]];js=x['PoroVolumeRatio'][1800:,0];tree=cKDTree(soil);kk=x['SigmaState_kk'][1800:];ij=x['SigmaState_ij'][1800:]
            # Saved ij=(xy,yz,xz); kernel state reader=(xy,xz,yz). No reinterpretation.
            field=np.column_stack((js,x['PorePress'][1800:,0].astype(float)-RHOW*GN*soil[:,1],x['Vel'][1800:].astype(float),kk,ij[:,[0,2,1]]))
            need(np.isfinite(field).all() and np.all(js>g.SOLID0),'Saved finite saturated fluid fields required');late=part>=len(data)-4;frame_rows=[];sources828={}
            for wall in walls:
                B=b[wall];bn=norm[wall];GP=B+bn;active=s.active_at_b(tree,soil,B);primary,nearest,ix=geometry(tree,soil,js,ids,GP,GP);attempts=[('primary',GP,primary,nearest,ix)]
                if not primary['geometry_gate'] and nearest is not None and np.any(GP-soil[nearest]!=0):
                    centre=soil[nearest].copy();r,k,jx=geometry(tree,soil,js,ids,centre,GP);attempts.append(('nearest_retry',centre,r,k,jx))
                if wall==828:sources828={name:set(int(ids[k]) for k in jx) for name,centre,r,k,jx in attempts}
                current=attempts[-1][2];nearestB=int(tree.query(B)[1]);shared=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-done['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),native_wall_ID=int(wall),mk=int(mk[wall]),B_x_m=float(B[0]),B_z_m=float(B[1]),normal_x_m=float(bn[0]),normal_z_m=float(bn[1]),GP_x_m=float(GP[0]),GP_z_m=float(GP[1]),B_active_proxy=active,nearest_B_soil_ID=int(ids[nearestB]),nearest_B_distance_m=float(np.linalg.norm(soil[nearestB]-B)),current_path=('OFF_not_applied' if not active else attempts[-1][0]),current_geometry_gate=current['geometry_gate'],current_Jfit_saturated=current['Jfit_saturated'])
                saved=np.r_[x['PoroVolumeRatio'][wall,0],x['PorePress'][wall,0],np.zeros(3),x['SigmaState_kk'][wall],x['SigmaState_ij'][wall,[0,2,1]]]
                for name,centre,r,k,jx in attempts:
                    row={**shared,'attempt':name,**r};rows.append(row);frame_rows.append(row);ff,aa=fields(tree,soil,js,ids,field,centre,GP,B,bn,r,k,jx)
                    for q in ff:q.update(shared,attempt=name,saved_B_comparable=(None if q['field'] in ('vx','vy','vz') else float(saved[NAMES.index(q['field'])])));fieldrows.append(q)
                    for q in aa:q.update(shared,attempt=name);affrows.append(q)
                if late and active and not current['geometry_gate']:
                    ordered=sorted(ix,key=lambda k:(float(np.dot(soil[k]-GP,soil[k]-GP)),int(ids[k])));first_geometry=False
                    for order,k in enumerate(ordered):
                        centre=soil[k];cached=next((a for a in attempts[1:] if np.array_equal(a[1],centre)),None);r,near,jx=(cached[2],cached[3],cached[4]) if cached else geometry(tree,soil,js,ids,centre,GP)
                        first=bool(r['geometry_gate'] and not first_geometry);first_geometry=first_geometry or r['geometry_gate']
                        stress,unused=s.fit(tree,soil,js,ids,np.column_stack((kk,ij)),centre,B) if r['geometry_gate'] else ({'geometry_gate':False},None)
                        row={**shared,'candidate_order':order,'candidate_native_ID':int(ids[k]),'distance2_to_original_GP':float(np.dot(centre-GP,centre-GP)),'reused_existing_nearest_fit':cached is not None,'first_geometry_qualified_in_fixed_order':first,**r,'stress_helper_geometry_gate':stress['geometry_gate']}
                        row.update({'candidate_sigma_B_'+name+'_Pa':float(stress['anchored_at_B'][c]) if stress['geometry_gate'] else None for c,name in enumerate(s.COMPONENTS)});candidates.append(row)
            summaries.append(dict(model=model,part=part,time_s=float(x['time']),active_walls=sum(r['B_active_proxy'] for r in frame_rows if r['attempt']=='primary'),current_geometry_failed=sum(r['B_active_proxy'] and not r['current_geometry_gate'] for r in frame_rows if r['attempt']=='primary'),current_Jfit_unsaturated=sum(r['B_active_proxy'] and r['current_geometry_gate'] and r['current_Jfit_saturated'] is False for r in frame_rows if r['attempt']=='primary')))
            mask=(soil[:,0]>=xmin)&(soil[:,0]<=xmax)&(soil[:,1]>=zmin)&(soil[:,1]<=zmax)
            if late:scatter[(model,part)]=(soil[mask],x['PorePress'][1800:,0][mask].astype(float),js[mask])
            keep=set(int(v) for v in ids[mask]) if late else set();keep.update((7014,828));keep.update(sources828.get('primary',set()));keep.update(sources828.get('nearest_retry',set()));allids=x['Idp'][:,0]
            for identity in sorted(keep):
                slot=int(np.searchsorted(allids,identity));need(allids[slot]==identity,'Tracked828/7014 or local ID missing');pos=x['Posd'][slot];vel=x['Vel'][slot];stress=np.r_[x['SigmaState_kk'][slot],x['SigmaState_ij'][slot]]
                q=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-done['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),native_ID=identity,role=('saved_ghost828_physical_velocity' if identity==828 else 'fixed_material7014' if identity==7014 else 'GP828_or_retry_source' if identity in sources828.get('primary',set())|sources828.get('nearest_retry',set()) else 'local_last4_soil'),in_plot_region=bool(xmin<=pos[0]<=xmax and zmin<=pos[2]<=zmax),source_in_original_GP828_stencil=identity in sources828.get('primary',set()),source_in_existing_retry828_stencil=identity in sources828.get('nearest_retry',set()),x_m=float(pos[0]),y_m=float(pos[1]),z_m=float(pos[2]),vx_m_s=float(vel[0]),vy_m_s=float(vel[1]),vz_m_s=float(vel[2]),p_Pa=float(x['PorePress'][slot,0]),kappa=float(x['Kplastic'][slot,0]),J=float(x['PoroVolumeRatio'][slot,0]))
                q.update({name+'_Pa':float(stress[c]) for c,name in enumerate(('sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz'))});local.append(q)
    files=[csvout('fits',rows),csvout('fields',fieldrows),csvout('affine',affrows),csvout('local',local)]
    if candidates:files.append(csvout('other_centres',candidates))
    for colfield,label,cmap in ((1,'Saved absolute p [Pa]','RdBu_r'),(2,'Saved J','viridis')):
        lo=min(float(v[colfield].min()) for v in scatter.values() if len(v[0]));hi=max(float(v[colfield].max()) for v in scatter.values() if len(v[0]));fig,axs=plt.subplots(2,4,figsize=(17,7),layout='constrained',sharex=True,sharey=True);image=None
        for ri,(model,bundle) in enumerate(sets.items()):
            for ci,part in enumerate(range(len(bundle[0])-4,len(bundle[0]))):
                ax=axs[ri,ci];pos,p,j=scatter[(model,part)];value=(p if colfield==1 else j);image=ax.scatter(pos[:,0],pos[:,1],c=value,s=14,cmap=cmap,vmin=lo,vmax=hi,linewidths=0);ax.scatter(b[walls,0],b[walls,1],marker='s',c='.4',s=18,label='actual B');GP=b[walls]+norm[walls];ax.scatter(GP[:,0],GP[:,1],marker='+',c='black',s=25,label='original GP')
                weak=[r for r in rows if r['model']==model and r['part']==part and r['attempt']=='primary' and r['B_active_proxy'] and not r['current_geometry_gate']];ax.scatter([r['GP_x_m'] for r in weak],[r['GP_z_m'] for r in weak],marker='x',c='red',s=55,label='current geometry failed')
                rr=[r for r in rows if r['model']==model and r['part']==part and r['attempt']=='nearest_retry'];ax.scatter([r['centre_x_m'] for r in rr],[r['centre_z_m'] for r in rr],marker='o',facecolors='none',edgecolors='purple',s=35,label='existing nearest retry');ax.annotate('828',b[828],xytext=(4,4),textcoords='offset points',fontsize=7)
                ax.axhline(0,c='black',lw=.6);ax.set(xlim=(xmin,xmax),ylim=(zmin,zmax),aspect='equal',xlabel='x [m]',ylabel='z [m]',title=model+' saved tau='+format(float(bundle[0][part]['time'])-bundle[1]['source_actual_time_s'],'.6f'));ax.grid(alpha=.2)
        axs[0,0].legend(fontsize=6);fig.colorbar(image,ax=axs.ravel().tolist(),label=label,shrink=.8);fig.suptitle('Actual local saved points and B/GP; one full local colour range, no smoothing/clipping; not failed-substage replay');path=Path(str(PREFIX)+('_pressure.png' if colfield==1 else '_J.png'));fig.savefig(path,dpi=165);plt.close(fig);files.append(path)
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed inputs changed')
    result=dict(stage=TAG,passed=True,wall_IDs=walls.tolist(),frames=COUNTS,fit_rows=len(rows),field_rows=len(fieldrows),affine_rows=len(affrows),other_centre_rows=len(candidates),saved_summaries=summaries,reported_failure=dict(stage=0,native_ID=828,step=4212817,step_start_s=10.532042500543135,last_saved_completed_step=4212000),kernel_h_float=float(g.H),radius2_float=g.R2,determinant_gate=1e-3,saturation_lower_J=g.SOLID0,candidate_policy='Last4 active/current-geometry-failed only; all original-GP same-R source centres in (distance2,nativeID) order; geometry and J reported separately; no J-based selection',native_tensor_ij='xy,yz,xz',kernel_tensor_tail='xy,xz,yz',affine_budget_is_existing_diagnostic_not_physical_gate=True,active_mask_is_proximity_proxy=True,stage1_C_total_Ace_and_failed_substage_not_available=True,GPU_packed_cell_order_FMA_replay=False,runtime_success_claimed=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(p) for p in files])
    with Path(str(PREFIX)+'.check.json').open('x',encoding='utf-8') as f:json.dump(g.clean(result),f,indent=2,allow_nan=False);f.write('\n')
    print('ASPLANE_WALL_PROBE_COMPLETED',str(PREFIX)+'.check.json',flush=True)

if __name__=='__main__':main()
