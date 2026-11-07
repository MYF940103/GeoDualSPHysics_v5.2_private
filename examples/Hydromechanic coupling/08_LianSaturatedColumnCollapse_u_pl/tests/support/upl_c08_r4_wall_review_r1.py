"""Read-only 43-frame r4 wall/contact review; saved states are not the failed CUDA substage."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,io,json,math,struct,time
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
import upl_c08_wall_geometry_r1 as g
import upl_c08_wall_stress_decompose_r1 as s

T=Path(__file__).resolve().parents[1];TAG='upl_c08_r4_wall_review_r1'
NATIVE=T/'outputs/upl_c08_r4_partial_r1';NATIVECHECK=T/'logs/upl_c08_r4_partial_r1.check.json'
NORMALS=NATIVE/'CfgInit_NormalsGhost.vtk';PREFIX=T/'figures'/TAG
SAMPLES=43;TARGET=823;TRACK=7010;COMPONENTS=s.COMPONENTS
SUFFIXES=('_history.csv','_contacts.csv','_walls.csv','_support.csv','_stress.csv','_centres.csv','_local.csv','_history.png','_local.png','.check.json')
CENTRE_FIELDS=('part','time_s','tau_s','wall_id','attempt','centre_owner_id','centre_x_m','centre_z_m','distance_to_original_GP_m','original_GP_sources','reused_retained_nearest',
               'nodes','det','cond_hscaled_inf','point_affine_rank','geometry_gate','Jfit','Jfit_saturated','qualified_geometry_J_sigma')+tuple('anchored_sigma_'+c+'_Pa' for c in COMPONENTS)

def write_csv(path,rows,fields=None):
    g.need(rows or fields,'Empty derived table without declared schema: '+str(path))
    buffer=io.StringIO(newline='');w=csv.DictWriter(buffer,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows);payload=buffer.getvalue().encode('utf-8')
    if path.exists():g.need(path.read_bytes()==payload,'Existing derived CSV differs; preserve it: '+str(path))
    else:
        with path.open('xb') as f:f.write(payload)

def load():
    paths=[NATIVECHECK,NATIVE/'completion.json',NATIVE/'typed22_layout.csv',NATIVE/'typed22.bin',NATIVE/'clocks.csv',NORMALS,
           Path(__file__),T/'support/upl_c08_wall_geometry_r1.py',T/'support/upl_c08_wall_stress_decompose_r1.py',T/'support/upl_c08_fsmask_r1.py']
    before=[g.stat(p) for p in paths];check=json.loads(paths[0].read_text(encoding='utf-8'));done=json.loads(paths[1].read_text(encoding='utf-8'))
    g.need(check.get('passed') is True and check.get('original_saved_native_guards_passed') is True and check.get('consumed_stats_unchanged') is True and done.get('passed') is True and done.get('samples')==SAMPLES and done.get('typed_arrays')==22,'Closed43-frame original native guards required')
    g.need(done.get('DynamicNoPenetrationPolicy')=='LegacyOperatorSplitReleaseOnly' and done.get('DynamicNoPenetrationActive') is True and done.get('DynamicNoPenetrationReactionClosed') is False,'Actual NoPen phase metadata differs')
    layout=g.table(paths[2]);g.need(len(layout)==22,'Original22 arrays required');names=['time'];formats=['<f8'];offsets=[0];extent=8
    for row,(name,kind,nc) in zip(layout,g.SCHEMA):
        dt=g.TYPES[kind];g.need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,dt.itemsize*nc),'Native typed22 layout differs')
        names.append(name);formats.append((dt,(6800,nc)) if nc>1 else (dt,(6800,)));offsets.append(extent);extent+=6800*nc*dt.itemsize
    with paths[3].open('rb') as f:g.need(struct.unpack('<III',f.read(12))==(6800,22,SAMPLES),'Original43-frame binary header differs')
    g.need(paths[3].stat().st_size==12+SAMPLES*extent,'Incomplete/extra typed records')
    raw=np.memmap(paths[3],mode='r',offset=12,shape=(SAMPLES,),dtype=np.dtype(dict(names=names,formats=formats,offsets=offsets,itemsize=extent)))
    clocks=g.table(paths[4]);g.need(len(clocks)==SAMPLES,'Actual clock coverage differs');b,normal,mk=g.normals_vtk(NORMALS)
    expected=np.r_[np.arange(1800),np.arange(2060,7060)].astype(np.uint32)
    for i,(f,c) in enumerate(zip(raw,clocks)):
        g.need(np.array_equal(f['Idp'],expected) and np.array_equal(f['Posd'][:1800],b[:1800]),'Original native IDs/fixed B changed')
        g.need(int(c['part'])==i and int(c['completed_step'])==4004000+4000*i and int(c['saved_step'])+1==int(c['completed_step']),'Actual saved global Step differs')
        g.need(struct.pack('<d',float(c['time_s']))==struct.pack('<d',float(f['time'])) and c['dterror_interval_empty']=='0' and float(c['signed_dterror_s'])<=1e-14,'Actual scalar/signed diagnostic differs')
        g.need(np.isfinite(f['Posd']).all() and np.isfinite(f['PoroVolumeRatio']).all() and np.all(f['PoroVolumeRatio']>g.SOLID0),'Invalid saved geometry/J')
    g.need(TARGET<1800 and mk[TARGET]==11 and normal[TARGET,0]==0 and normal[TARGET,2]>0,'823 must be the actual bottom sample')
    return raw,clocks,b[:1800,[0,2]],normal[:1800,[0,2]],mk[:1800],float(done['source_actual_time_s']),before,check

def membership(tree,soil,at,lower):
    ix=np.asarray(sorted(tree.query_ball_point(at,g.SEARCH)),dtype=int);d=at-soil[ix];rr=np.sum(d*d,axis=1);df=d.astype(np.float32)
    rc=rr.astype(np.float32);rf=np.float32(df[:,0]*df[:,0]+df[:,1]*df[:,1]);lo=g.LOWER if lower else 0.
    flags=[(v<=g.R2)&(v>=lo) for v in (rr,rc,rf)]
    return ix,flags,ix[flags[1]]

def geometry(tree,soil,js,ids,centre,gp):
    diag,near=g.support(tree,soil,js,ids,centre,gp);ix,flags,used=membership(tree,soil,centre,False)
    # Point-set rank is a binary64 geometric diagnostic, never an additional production gate.
    effective=np.array([k for k in used if g.cubic(float(np.dot(centre-soil[k],centre-soil[k])))[0]>0],dtype=int)
    points=soil[effective];design=np.column_stack((np.ones(len(points)),(points-centre)/float(g.H)))
    rank=int(np.linalg.matrix_rank(design)) if len(points) else 0
    span=np.linalg.svd(points-points.mean(axis=0),compute_uv=False) if len(points) else np.zeros(2);span=np.pad(span,(0,max(0,2-len(span))))
    diag.update(point_affine_rank=rank,point_span_smax_m=float(span[0]),point_span_smin_m=float(span[1]),
                nodes_double=int(flags[0].sum()),nodes_float_components=int(flags[2].sum()))
    return diag,near,used

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args()
    g.need(a.execution_authorized,'Author-only until root review authorizes execution');paths={q:Path(str(PREFIX)+q) for q in SUFFIXES}
    g.need(PREFIX.parent.is_dir() and not any(p.exists() for suffix,p in paths.items() if not suffix.endswith('.csv')),'Existing PNG/check protected; CSV reuse requires exact regenerated bytes')
    started=time.perf_counter();raw,clocks,b,normal,mk,release,before,nativecheck=load();base=b[TARGET]
    same=np.flatnonzero((b[:,1]==base[1])&(normal[:,0]==normal[TARGET,0])&(normal[:,1]==normal[TARGET,1])&(mk==mk[TARGET]))
    same=same[np.argsort(b[same,0])];where=int(np.flatnonzero(same==TARGET)[0]);walls=same[max(0,where-2):where+3]
    g.need(len(walls)==5 and TARGET in walls,'Five actual same-row bottom samples required')
    histories=[];contacts=[];wallrows=[];supportrows=[];stressrows=[];centrerows=[];plotframes={};max_affine_ratio=0.;max_decomp=0.;seen_bottom=set()
    bed=np.flatnonzero((mk==11)&(normal[:,0]==0)&(normal[:,1]>0));bedtree=cKDTree(b[bed]);A_requests=0;A_recovered=0
    selected=(SAMPLES-7,SAMPLES-4,SAMPLES-1)
    for part,(frame,clock) in enumerate(zip(raw,clocks)):
        xyz=np.asarray(frame['Posd'][1800:]);soil=xyz[:,[0,2]];ids=np.asarray(frame['Idp'][1800:]);js=np.asarray(frame['PoroVolumeRatio'][1800:]);p=np.asarray(frame['PorePress'][1800:],float);vel=np.asarray(frame['Vel'][1800:],float)
        sigma=s.stress(frame);eff=sigma[1800:];total=eff.copy();total[:,:3]-=p[:,None];speed=np.linalg.norm(vel,axis=1);kap=frame['Kplastic'][1800:];tree=cKDTree(soil);track=int(np.flatnonzero(ids==TRACK)[0])
        row=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,completed_step=int(clock['completed_step']),min_z_m=float(xyz[:,2].min()),min_x_m=float(xyz[:,0].min()),soil_z_lt0_count=int(np.count_nonzero(xyz[:,2]<0)),soil_x_lt0_count=int(np.count_nonzero(xyz[:,0]<0)),
                 p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),velocity_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),max_speed_m_s=float(speed.max()),kappa_max=float(kap.max()),kappa_nonzero_count=int(np.count_nonzero(kap)),min_J=float(js.min()),max_J=float(js.max()),
                 sigmaeff_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(eff[:,:3]**2,axis=1)+2*np.sum(eff[:,3:]**2,axis=1)))),totalstress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(total[:,:3]**2,axis=1)+2*np.sum(total[:,3:]**2,axis=1)))))
        for name,value in zip(('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s','p_Pa','kappa','J'),[*xyz[track],*vel[track],p[track],kap[track],js[track]]):row['id7010_'+name]=float(value)
        for c,name in enumerate(COMPONENTS):row['id7010_sigma_'+name+'_Pa']=float(eff[track,c])
        histories.append(row)
        for k in np.flatnonzero((xyz[:,2]<0)|(xyz[:,0]<0)):
            native_id=int(ids[k]);distance,j=bedtree.query(soil[k]);wall=int(bed[j]);B=b[wall];plane=B[1]+normal[wall,1]/2
            item=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,native_id=native_id,z_lt0=bool(xyz[k,2]<0),x_lt0=bool(xyz[k,0]<0),first_saved_z_lt0_for_ID=bool(xyz[k,2]<0 and native_id not in seen_bottom),
                      x_m=float(xyz[k,0]),z_m=float(xyz[k,2]),vx_m_s=float(vel[k,0]),vy_m_s=float(vel[k,1]),vz_m_s=float(vel[k,2]),p_Pa=float(p[k]),kappa=float(kap[k]),J=float(js[k]),
                      nearest_bed_id=wall,B_x_m=float(B[0]),B_z_m=float(B[1]),bed_plane_z_m=float(plane),x_minus_Bx_m=float(soil[k,0]-B[0]),z_minus_Bz_m=float(soil[k,1]-B[1]),z_minus_bed_plane_m=float(soil[k,1]-plane),distance_to_B_m=float(distance))
            previous=raw[part-1] if part else None;slot=1800+int(k)
            item.update(previous_saved_part=part-1 if part else None,previous_saved_time_s=float(previous['time']) if part else None,previous_saved_z_m=float(previous['Posd'][slot,2]) if part else None,previous_saved_vz_m_s=float(previous['Vel'][slot,2]) if part else None,
                        previous_saved_p_Pa=float(previous['PorePress'][slot]) if part else None,previous_saved_kappa=float(previous['Kplastic'][slot]) if part else None,previous_saved_J=float(previous['PoroVolumeRatio'][slot]) if part else None)
            for c,name in enumerate(COMPONENTS):item['sigma_'+name+'_Pa']=float(eff[k,c])
            contacts.append(item)
            if xyz[k,2]<0:seen_bottom.add(native_id)
        for wall in walls:
            B=b[wall];GP=B+normal[wall];_,bflags,_=membership(tree,soil,B,True);active=bool(np.any(np.logical_or.reduce(bflags)));first,near,used=geometry(tree,soil,js,ids,GP,GP)
            retry=bool(not first['geometry_gate'] and near is not None and np.any(GP-soil[near]!=0));centre=soil[near].copy() if retry else GP.copy()
            final,finalnear,finalused=geometry(tree,soil,js,ids,centre,GP) if retry else (first,near,used)
            shared=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=int(wall),B_x_m=float(B[0]),B_z_m=float(B[1]),GP_x_m=float(GP[0]),GP_z_m=float(GP[1]),B_active_union_proxy=active,B_double_nodes=int(bflags[0].sum()),B_cast_rr2_nodes=int(bflags[1].sum()),B_cast_component_nodes=int(bflags[2].sum()),retry_attempted=retry,retry_shift_m=float(np.linalg.norm(centre-GP)),final_geometry_gate=final['geometry_gate'],final_Jfit_saturated=final['Jfit_saturated'])
            for at,label in ((B,'B'),(GP,'GP')):
                distance,index=tree.query(at);shared[label+'_nearest_all_soil_id']=int(ids[index]);shared[label+'_nearest_all_distance_m']=float(distance)
            for prefix,diag in (('primary',first),('final',final)):
                shared.update({prefix+'_'+k:v for k,v in diag.items()})
            shared.update(saved_wall_p_Pa=float(frame['PorePress'][wall]),saved_wall_J=float(frame['PoroVolumeRatio'][wall]),saved_wall_vx_m_s=float(frame['Vel'][wall,0]),saved_wall_vy_m_s=float(frame['Vel'][wall,1]),saved_wall_vz_m_s=float(frame['Vel'][wall,2]))
            for c,name in enumerate(COMPONENTS):shared['saved_wall_sigma_'+name+'_Pa']=float(sigma[wall,c])
            wallrows.append(shared)
            phases=[('primary',GP,first,near,used)]+([('retry',centre,final,finalnear,finalused)] if retry else [])
            for phase,fitcentre,diag,nearest,indices in phases:
                f,_=s.fit(tree,soil,js,ids,eff,fitcentre,B)
                g.need(f['geometry_gate']==diag['geometry_gate'],'Reused fit geometry disagrees')
                for k in indices:
                    delta=fitcentre-soil[k];w0,_=g.cubic(float(np.dot(delta,delta)));v=vel[k]
                    item=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=int(wall),phase=phase,soil_id=int(ids[k]),x_m=float(soil[k,0]),z_m=float(soil[k,1]),distance_to_centre_m=float(np.linalg.norm(delta)),W=w0,V0J=g.VOL0*float(js[k]),J=float(js[k]),p_Pa=float(p[k]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),kappa=float(kap[k]))
                    for c,name in enumerate(COMPONENTS):item['sigma_'+name+'_Pa']=float(eff[k,c])
                    supportrows.append(item)
                for c,name in enumerate(COMPONENTS):
                    item=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=int(wall),phase=phase,B_active_union_proxy=active,geometry_gate=f['geometry_gate'],component=name,saved_sigma_B_Pa=float(sigma[wall,c]))
                    for key in ('q0','nearest_sigma','MLS_at_B','anchor_residual','gradient_distance','anchored_at_B','neighbor_min','neighbor_max','affine_mls_error','affine_anchor_error'):item[key+'_Pa']=float(f[key][c]) if f['geometry_gate'] else None
                    item.update(gradient_x_Pa_m=float(f['gradient'][0,c]) if f['geometry_gate'] else None,gradient_z_Pa_m=float(f['gradient'][1,c]) if f['geometry_gate'] else None,
                                gradient_distance_x_Pa=float((B[0]-soil[nearest,0])*f['gradient'][0,c]) if f['geometry_gate'] else None,gradient_distance_z_Pa=float((B[1]-soil[nearest,1])*f['gradient'][1,c]) if f['geometry_gate'] else None,
                                affine_budget_Pa=f.get('affine_budget'),decomposition_identity_error_Pa=f.get('decomposition_error'))
                    stressrows.append(item)
                if f['geometry_gate']:
                    max_affine_ratio=max(max_affine_ratio,float(max(f['affine_mls_error'].max(),f['affine_anchor_error'].max())/f['affine_budget']));max_decomp=max(max_decomp,f['decomposition_error'])
            # Counterfactual A: this fixed ORIGINAL-GP source list never expands through later stencils.
            shared.update(A_requested=False,A_attempts=0,A_found=False,A_min_shift_m=None,A_centre_owner_id=None,A_det=None,A_Jfit=None)
            if active and near is not None and not first['geometry_gate'] and not (final['geometry_gate'] and final['Jfit_saturated'] is True):
                shared['A_requested']=True;A_requests+=1
                ordered=sorted(used,key=lambda k:(float(np.linalg.norm(soil[k]-GP)),int(ids[k])))
                for attempt,k in enumerate(ordered,1):
                    candidate=soil[k];diag=final if k==near else geometry(tree,soil,js,ids,candidate,GP)[0]
                    sf=f if k==near else (s.fit(tree,soil,js,ids,eff,candidate,B)[0] if diag['geometry_gate'] else None)
                    eligible=bool(diag['geometry_gate'] and diag['Jfit_saturated'] is True and sf is not None and np.isfinite(sf['anchored_at_B']).all())
                    item=dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,wall_id=int(wall),attempt=attempt,centre_owner_id=int(ids[k]),centre_x_m=float(candidate[0]),centre_z_m=float(candidate[1]),distance_to_original_GP_m=float(np.linalg.norm(candidate-GP)),original_GP_sources=len(used),reused_retained_nearest=bool(k==near),
                              nodes=diag['nodes'],det=diag['det'],cond_hscaled_inf=diag['cond_hscaled_inf'],point_affine_rank=diag['point_affine_rank'],geometry_gate=diag['geometry_gate'],Jfit=diag['Jfit'],Jfit_saturated=diag['Jfit_saturated'],qualified_geometry_J_sigma=eligible)
                    for c,name in enumerate(COMPONENTS):item['anchored_sigma_'+name+'_Pa']=float(sf['anchored_at_B'][c]) if sf is not None and sf['geometry_gate'] else None
                    centrerows.append(item);shared['A_attempts']=attempt
                    if eligible:
                        shared.update(A_found=True,A_min_shift_m=item['distance_to_original_GP_m'],A_centre_owner_id=int(ids[k]),A_det=diag['det'],A_Jfit=diag['Jfit']);A_recovered+=1;break
            if wall==TARGET and part in selected:plotframes[part]=(first,final,GP.copy(),centre.copy(),used.copy(),soil.copy(),ids.copy())
    g.need(len(histories)==SAMPLES and len(wallrows)==SAMPLES*5,'Incomplete actual frame/wall coverage')
    for suffix,rows in (('_history.csv',histories),('_walls.csv',wallrows),('_support.csv',supportrows),('_stress.csv',stressrows)):write_csv(paths[suffix],rows)
    contact_fields=list(contacts[0]) if contacts else ['part','time_s','tau_s','native_id','z_lt0','x_lt0']
    write_csv(paths['_contacts.csv'],contacts,contact_fields);write_csv(paths['_centres.csv'],centrerows,list(CENTRE_FIELDS))
    first_crossing_part=min((r['part'] for r in contacts if r['z_lt0']),default=-1);first_crossing=[r for r in contacts if r['z_lt0'] and r['part']==first_crossing_part]
    tau=np.array([r['tau_s'] for r in histories]);val=lambda key:np.array([r[key] for r in histories]);fig,axs=plt.subplots(3,3,figsize=(14,10),constrained_layout=True)
    panels=[([('min_z_m','min z',1000),('min_x_m','min x',1000)],'Minimum soil coordinate [mm]'),([('soil_z_lt0_count','z<0',1),('soil_x_lt0_count','x<0',1)],'Soil IDs beyond plane'),([('p_min_Pa','min p',.001),('p_mean_Pa','mean p',.001),('p_max_Pa','max p',.001),('id7010_p_Pa','7010 p',.001)],'Absolute pore pressure [kPa]'),
            ([('velocity_RMS_m_s','RMS',1),('max_speed_m_s','max speed',1),('id7010_vz_m_s','7010 vz',1)],'Velocity [m/s]'),([('kappa_max','max kappa',1),('id7010_kappa','7010 kappa',1)],'Plastic history'),([('min_J','min J',1),('max_J','max J',1),('id7010_J','7010 J',1)],'Volume ratio J'),
            ([('sigmaeff_Frobenius_RMS_Pa','effective',.001),('totalstress_Frobenius_RMS_Pa','total',.001)],'Stress Frobenius RMS [kPa]'),([('id7010_z_m','7010 z',1000)],'Fixed material particle z [mm]')]
    for ax,(curves,ylabel) in zip(axs.flat,panels):
        for key,label,scale in curves:ax.plot(tau,val(key)*scale,label=label)
        ax.set(xlabel='Actual time since release [s]',ylabel=ylabel);ax.grid(alpha=.25);ax.legend(fontsize=7)
    for r in first_crossing[:5]:
        slot=int(np.flatnonzero(raw[0]['Idp']==r['native_id'])[0]);axs.flat[7].plot(tau,raw['Posd'][:,slot,2]*1000,label='first saved crossing ID'+str(r['native_id']))
    axs.flat[7].axhline(0,c='black',lw=.7);axs.flat[7].legend(fontsize=6)
    targetrows=[r for r in wallrows if r['wall_id']==TARGET];ax=axs.flat[8]
    for key,label in (('primary_det','primary'),('final_det','after allowed retry')):ax.plot(tau,[abs(r[key]) for r in targetrows],label=label)
    ax.axhline(.001,c='black',ls='--',label='original det gate');ax.set_yscale('symlog',linthresh=1e-6);ax.set(xlabel='Actual time since release [s]',ylabel='823 |det|');ax.grid(alpha=.25);ax.legend(fontsize=7)
    fig.suptitle('43 saved r4 NoPen/AS0 states; no failed-substage or reaction replay',fontsize=11)
    with paths['_history.png'].open('xb') as f:fig.savefig(f,format='png',dpi=170)
    plt.close(fig);localrows=[];lo=base[0]-.3;hi=base[0]+.3;pmax=1.;kmax=0.
    for part in selected:
        frame=raw[part];pos=frame['Posd'];roi=(pos[:,0]>=lo)&(pos[:,0]<=hi)&(pos[:,2]>=-.15)&(pos[:,2]<=.3)
        for k in np.flatnonzero(roi):
            localrows.append(dict(part=part,time_s=float(frame['time']),tau_s=float(frame['time'])-release,native_id=int(frame['Idp'][k]),fixed=bool(k<1800),x_m=float(pos[k,0]),z_m=float(pos[k,2]),p_Pa=float(frame['PorePress'][k]),kappa=float(frame['Kplastic'][k]),J=float(frame['PoroVolumeRatio'][k]),vx_m_s=float(frame['Vel'][k,0]),vz_m_s=float(frame['Vel'][k,2])))
        q=roi.copy();q[:1800]=False
        if np.any(q):pmax=max(pmax,float(np.abs(frame['PorePress'][q]).max()));kmax=max(kmax,float(frame['Kplastic'][q].max()))
    write_csv(paths['_local.csv'],localrows);fig,axs=plt.subplots(2,3,figsize=(14,7),constrained_layout=True)
    for col,part in enumerate(selected):
        first,final,GP,centre,indices,soil,ids=plotframes[part];frame=raw[part];roi=(soil[:,0]>=lo)&(soil[:,0]<=hi)&(soil[:,1]>=-.15)&(soil[:,1]<=.3)
        for row,(field,cmap,vmin,vmax,label) in enumerate(((frame['PorePress'][1800:]*.001,'coolwarm',-pmax*.001,pmax*.001,'p [kPa]'),(frame['Kplastic'][1800:],'viridis',0,max(kmax,1e-12),'kappa'))):
            ax=axs[row,col];image=ax.scatter(soil[roi,0],soil[roi,1],c=field[roi],s=16,cmap=cmap,vmin=vmin,vmax=vmax)
            ax.scatter(b[walls,0],b[walls,1],marker='s',c='.5',s=18);ax.scatter(*base,c='red',marker='x',s=45);ax.scatter(*GP,c='red',marker='+',s=45)
            if len(indices):ax.scatter(soil[indices,0],soil[indices,1],s=45,facecolors='none',edgecolors='orange')
            if not np.array_equal(GP,centre):ax.plot([GP[0],centre[0]],[GP[1],centre[1]],'k:');ax.scatter(*centre,c='black',marker='*',s=35)
            ax.axhline(0,c='black',lw=.7);ax.set(xlim=(lo,hi),ylim=(-.15,.3),aspect='equal',xlabel='x [m]',ylabel='z [m]',title=f"tau={float(frame['time'])-release:.6g}s; GP n={first['nodes']}, rank={first['point_affine_rank']}; final det={final['det']:.3g}")
            ax.grid(alpha=.2);fig.colorbar(image,ax=ax,label=label)
    fig.suptitle('Native soil and same-row bed near823; B red x / GP red + / primary support orange; saved-state proxy',fontsize=10)
    with paths['_local.png'].open('xb') as f:fig.savefig(f,format='png',dpi=170)
    plt.close(fig);g.need(all(g.stat(e['path'])==e for e in before),'Consumed sealed sources changed')
    result=dict(stage=TAG,passed=True,frames=SAMPLES,soil_IDs_per_frame=5000,wall_ids=walls.tolist(),native_check=g.stat(NATIVECHECK),consumed=before,outputs=[g.stat(p) for k,p in paths.items() if k!='.check.json'],elapsed_s=time.perf_counter()-started,
                source_actual_time_s=release,last_saved_time_s=float(raw[-1]['time']),last_saved_completed_step=int(clocks[-1]['completed_step']),all_saved_min_z_m=min(r['min_z_m'] for r in histories),all_saved_min_x_m=min(r['min_x_m'] for r in histories),max_saved_soil_z_lt0=max(r['soil_z_lt0_count'] for r in histories),max_saved_soil_x_lt0=max(r['soil_x_lt0_count'] for r in histories),
                first_saved_bottom_crossing=first_crossing,soil_time_z_lt0_rows=sum(r['z_lt0'] for r in contacts),distinct_saved_z_lt0_IDs=len(seen_bottom),
                target_summaries=targetrows,original_determinant_gate=.001,max_affine_error_over_retained_budget=max_affine_ratio,max_decomposition_identity_error_Pa=max_decomp,
                counterfactual_A_requests=A_requests,counterfactual_A_recovered=A_recovered,A_candidates_only_original_GP_same_radius_sources=True,A_order='distance_to_original_GP_then_native_ID',A_stops_at_first_qualified_centre=True,A_is_not_a_production_wall_choice_or_full_pressure_velocity_guard=True,
                point_affine_rank_is_unweighted_binary64_geometry=True,B_activation_is_three_predicate_proxy_not_wetness=True,negative_plane_counts_are_observations_not_NoPen_guarantee=True,
                reported_unsaved_failure=nativecheck['actual_runtime_diagnostic_line'],
                saved_state_not_failed_substage_replay=True,GPU_PosCell_cell_order_FMA_replayed=False,NoPen_per_step_scratch_or_reaction_exported=False,production_wall_law_modified=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0)
    with paths['.check.json'].open('x',encoding='utf-8') as f:json.dump(g.clean(result),f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(stage=TAG,passed=True,frames=SAMPLES,wall_ids=walls.tolist(),check=str(paths['.check.json'])),allow_nan=False))

if __name__=='__main__':main()
