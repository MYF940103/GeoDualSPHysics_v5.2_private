"""Offline91-frame Lstar/AS03 physical diagnostics only; never decode or solve."""
import argparse,csv,math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.ticker import MaxNLocator
import c08_h18_lstar_gpu_native_r1 as shared
import c08_h18_rv_window_review_r1 as previous
m,core,T,L=shared.m,shared.core,shared.T,shared.L
need,read,stat,bind,entry,owned,same,bits=shared.need,shared.read,shared.stat,shared.bind,shared.entry,shared.owned,shared.same,shared.bits
TAG='c08_h18_lstar_window_review_r1';SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md');CHECK=L/(TAG+'.check.json');FIG=T/'figures'
RUN=L/'c08_h18_lstar_window_GPU_r1.run.json';NATIVE=L/'c08_h18_lstar_window_GPU_r1.native_r1.check.json'
OLD_RUN=L/'c08_h18_as03_n255_r1.run.json';OLD_NATIVE=L/'c08_h18_as03_n255_native_r1.check.json'
CASES=('Original pair-C/Eta','Private receiver-C/bare');SELECTED=(30,60,90);CUTS=((.7,'0p7'),(.5,'0p5'),(.3,'0p3'));DP=.04;H=float(np.float32(.072));KW=1e9
COHORTS=('all','fixed_initial_top','fixed_initial_bottom','current_near_bed','current_FS23','current_nonFS_away_left_bed')
def write(path,rows):
    need(rows,'No empty output table')
    with path.open('x',encoding='utf-8',newline='')as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def seal(root,path,consumed):
    g=read(path);need(g['passed']and g['consumed_stats_unchanged'],'Existing native-export seal required');consumed.append(stat(path))
    for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
        rows=[q for q in g['consumed']if same(q['path'],root/leaf)];need(rows and all(q==rows[0]for q in rows),'Previously bound native export absent: '+leaf);consumed.append(bind(rows[0]))
def coverage(d):
    need(d['passed']and d['stage']=='c08_h18_wend_native_r1.receiver'and d['samples']==91 and d['completed_steps']==2180000 and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212,'Passed genuine91-frame native core required')
    for k,v in{'actual_native_IDs_per_frame':6805,'soil_IDs':5000,'actual_fixed_IDs':1805,'ledger_checks':455000,'P0_bits_checks':619255,'rho_cache_bits_checks':455000,'kappa_nondecreasing_from_PRE_checks':455000,'nonempty_signed_intervals':91}.items():need(d[k]==v,'Original native coverage differs: '+k)
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['FS23_pressure_checks']>0 and not d['native_rewritten'],'Original native gates differ')
def inputs(consumed):
    run,native,old,on=read(RUN),read(NATIVE),read(OLD_RUN),read(OLD_NATIVE)
    need(run['passed']and run['solver_completed']and run['consumed_stats_unchanged']and run['configuration']=='Release'and run['mode']=='on'and run['actual_steps']==2180000 and run['saved_frames']==91 and run['new_updates']==180000,'Completed new ReleaseON window required')
    need(native['passed']and native['consumed_stats_unchanged']and native['reader_invocations']==1 and entry(native,'source_run')==stat(RUN)and native['reader_build_reused']and not native['typed22_schema_changed'],'Actual unique new native receipt required')
    need(old['passed']and old['solver_completed']and old['consumed_stats_unchanged']and old['actual_steps']==2180000 and old['saved_frames']==91 and on['passed']and on['consumed_stats_unchanged']and on['reader_invocations']==1,'Retained AS03 control required')
    for q in(run,native,old,on):owned(read(entry(q,'actual_call')['path']));consumed.append(entry(q,'actual_call'))
    for q in(run,old):
        consumed.extend(entry(q,k)for k in('program','source_build','source_archive','source_pre_file','source_native','planned_steps','input_xml','native_profile','Run_out','Run_csv'))
    need(run['source_pre_file']==old['source_pre_file']and run['source_native']==old['source_native']and run['planned_steps']==old['planned_steps']and run['source_archive']==old['source_archive'],'Actual common PRE/archive/91plan required')
    for k in('input_xml','native_profile'):need(Path(run[k]['path']).read_bytes()==Path(old[k]['path']).read_bytes(),'Original input physics bytes differ: '+k)
    nd,od=read(entry(native,'native_completion')['path']),read(entry(on,'native_completion')['path']);coverage(nd);coverage(od)
    nr,orr=Path(native['native_completion']['path']).parent,Path(on['native_completion']['path']).parent
    need(same(nr.parent,run['output'])and same(orr.parent,Path(old['Run_out']['path']).parent),'Actual native/run roots differ')
    for leaf in('typed22.bin','typed22_layout.csv','clocks.csv'):
        refs=[q for q in native['files']if Path(q['path']).name==leaf];need(len(refs)==1,'One actual new export seal required');consumed.append(bind(refs[0]))
    seal(orr,L/'c08_h18_lstar_cpu_off_r1.build.json',consumed)
    new,oldb=core.typed(nr,6805,91,consumed),core.typed(orr,6805,91,consumed);need((nr/'typed22_layout.csv').read_bytes()==(orr/'typed22_layout.csv').read_bytes(),'Actual compared22 layouts differ')
    plan=core.table(run['planned_steps']['path']);need(len(plan)==91 and list(plan[0])==['part','completed_step','saved_step','time_s','dt_s'],'Original complete five-column91 plan required')
    for i,(a,b,p)in enumerate(zip(new['clocks'],oldb['clocks'],plan)):
        step=2180000 if i==90 else 2000001+2000*i
        need(int(a['part'])==int(b['part'])==int(p['part'])==i and int(a['completed_step'])==int(b['completed_step'])==int(p['completed_step'])==step and int(a['saved_step'])==int(b['saved_step'])==int(p['saved_step'])==step-1 and bits(a['time_s'])==bits(b['time_s'])==bits(p['time_s'])and bits(a['dt_s'])==bits(b['dt_s'])==bits(p['dt_s'])==bits(5e-6)and float(a['signed_dterror_s'])<=1e-14 and float(b['signed_dterror_s'])<=1e-14 and a['dterror_interval_empty']==b['dterror_interval_empty']=='0','Actual same-time/signed-clock91 join failed')
    sd=read(run['source_native']['path']);need(sd['passed']and sd['certified_PRE']and not sd['partial']and sd['samples']==1001 and sd['completed_steps']==2000000 and sd['native_IDs']==7060 and sd['typed_arrays']==22 and sd['same_material_plastic_PRE'],'Full actual schema2 source reference required');sr=Path(run['source_native']['path']).parent
    seal(sr,L/'c08_h18_rv_window_review_r1.check.json',consumed);sb=core.typed(sr,7060,1001,consumed);ref,cohorts=previous.source_reference(sb,sd)
    consumed.extend([stat(q)for q in(RUN,NATIVE,OLD_RUN,OLD_NATIVE)]+[entry(native,k)for k in('native_completion','metadata','reader_build')]+[entry(on,k)for k in('native_completion','metadata','reader_build')]);need(run['actual_source_time_s']==nd['source_actual_time_s']==od['source_actual_time_s']==sd['actual_end_s'],'Shared actual PRE clock differs')
    return run,old,new,oldb,ref,cohorts
def near(pos):
    tree=cKDTree(pos);_,idx=tree.query(pos,k=2,workers=1);length=np.linalg.norm(pos[idx]-pos[:,None,:],axis=-1);length=np.where(idx!=np.arange(5000)[:,None],length,np.inf);which=length.argmin(axis=1);nn=length[np.arange(5000),which];neighbor=idx[np.arange(5000),which];need(np.isfinite(nn).all()and(nn>=0).all(),'Every true3D nonself NN required')
    pairs=tree.query_pairs(.7*DP,output_type='ndarray');dist=np.linalg.norm(pos[pairs[:,0]]-pos[pairs[:,1]],axis=1)if len(pairs)else np.empty(0)
    for cut,_ in CUTS:need(np.count_nonzero(nn<cut*DP)==len(np.unique(pairs[dist<cut*DP])),'Independent global NN-node/unique-pair endpoints differ')
    return nn/DP,neighbor,pairs,dist
def frame_data(frame,ref,last):
    soil=frame['Idp'][:,0]>=2060;ids=frame['Idp'][soil,0];need(np.array_equal(ids,ref['ids'])and np.array_equal(frame['PorePress0'][:,0].view('<u4'),ref['p0all'].view('<u4')),'All material IDs/fixed P0 required')
    p32=np.array(frame['PorePress'][soil,0]);p=p32.astype(float);ex=np.array(frame['ExcessPorePress'][soil,0]);need(np.array_equal(ex.view('<u4'),np.asarray(frame['PorePress'][soil,0]-frame['PorePress0'][soil,0],dtype='<f4').view('<u4')),'Native fixed-reference float excess differs')
    pos=np.array(frame['Posd'][soil]);v=frame['Vel'][soil].astype(float);kap=frame['Kplastic'][soil,0].astype(float);need((kap>=ref['pre_kappa']).all()and(last is None or(kap>=last['kappa']).all()),'Actual accumulated kappa history decreased')
    J=np.array(frame['PoroVolumeRatio'][soil,0]);n=np.array(frame['PoroPorosity'][soil,0]);V=np.array(frame['PoroCurrentVolume'][soil,0]);rho=np.array(frame['PoroMixtureDensity'][soil,0]);k=np.array(frame['PoroHydraulicConductivity'][soil,0]);fs=frame['FSType'][soil,0];fs23=(fs==2)|(fs==3);kk=np.array(frame['SigmaState_kk'][soil]);ij=np.array(frame['SigmaState_ij'][soil]);total=kk-p[:,None];norm=np.sqrt(np.sum(total*total,axis=1)+2*np.sum(ij*ij,axis=1));effnorm=np.sqrt(np.sum(kk*kk,axis=1)+2*np.sum(ij*ij,axis=1));nn,neighbor,pairs,distance=near(pos);du=pos-ref['pos'];W=n*V/KW
    masks=dict(all=np.ones(5000,dtype=bool),fixed_initial_top=ref['top'],fixed_initial_bottom=ref['bottom'],current_near_bed=(pos[:,2]>=0)&(pos[:,2]<=2*H),current_FS23=fs23,current_nonFS_away_left_bed=(~fs23)&(pos[:,0]>2*H)&(pos[:,2]>2*H))
    return dict(ids=ids,p32=p32,p=p,ex=ex.astype(float),pos=pos,v=v,speed=np.linalg.norm(v,axis=1),kappa=kap,J=J,n=n,V=V,rho=rho,k=k,fs=fs,fs23=fs23,kk=kk,total=total,ij=ij,totalnorm=norm,effnorm=effnorm,du=du,W=W,nn=nn,neighbor=neighbor,pairs=pairs,distance=distance,masks=masks)
def aggregate(label,part,clock,d,ref,last):
    rows=[]
    for cohort in COHORTS:
        mask=d['masks'][cohort];count=int(mask.sum());r=dict(case=label,part=part,completed_step=int(clock['completed_step']),actual_time_s=float(clock['time_s']),tau_s=float(clock['time_s'])-ref['time'],signed_dterror_s=float(clock['signed_dterror_s']),cohort=cohort,count=count)
        for name,values in(('p_Pa',d['p']),('native_p_minus_fixedP0_Pa',d['ex']),('NN_over_dp',d['nn']),('J',d['J']),('n',d['n']),('rho_kg_m3',d['rho']),('k_m_s',d['k']),('kappa',d['kappa']),('speed_m_s',d['speed']),('effective_stress_Frobenius_Pa',d['effnorm']),('total_stress_Frobenius_Pa',d['totalnorm']),('effective_stress_trace_Pa',d['kk'].sum(axis=1)),('total_stress_trace_Pa',d['total'].sum(axis=1)),('settlement_from_PRE_mm',-1000*d['du'][:,2])):
            x=values[mask]
            for suffix,value in(('min',x.min()if count else None),('max',x.max()if count else None),('mean',x.mean()if count else None),('RMS',np.sqrt(np.mean(x*x))if count else None),('q05',np.quantile(x,.05)if count else None),('q50',np.quantile(x,.5)if count else None),('q95',np.quantile(x,.95)if count else None)):r[name+'_'+suffix]=float(value)if value is not None else None
        r.update(negative_p_nodes=int(np.count_nonzero(mask&(d['p']<0))),FS23_nodes=int(np.count_nonzero(mask&d['fs23'])),kappa_history_positive_nodes=int(np.count_nonzero(mask&(d['kappa']>0))),x_front_m=float(d['pos'][mask,0].max())if count else None,front_from_PRE_m=float(d['pos'][mask,0].max()-ref['pos'][mask,0].max())if count else None,material_displacement_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(d['du'][mask]**2,axis=1))))if count else None)
        for axis in range(3):r['material_mean_d'+'xyz'[axis]+'_from_PRE_mm']=float(1000*d['du'][mask,axis].mean())if count else None
        for cut,name in CUTS:
            close=d['pairs'][d['distance']<cut*DP];incident=np.any(mask[close],axis=1)if len(close)else np.empty(0,dtype=bool);both=np.all(mask[close],axis=1)if len(close)else np.empty(0,dtype=bool);r['NN_nodes_lt_'+name+'dp']=int(np.count_nonzero(mask&(d['nn']<cut)));r['unique_pairs_incident_lt_'+name+'dp']=int(incident.sum());r['unique_pairs_both_lt_'+name+'dp']=int(both.sum())
        nnidx=int(np.argmin(np.where(mask,d['nn'],np.inf)))if count else None;r.update(minNN_material_id=int(d['ids'][nnidx])if count else None,minNN_neighbor_id=int(d['ids'][d['neighbor'][nnidx]])if count else None)
        W,p=d['W'],d['p'];S=float(np.sum(W[mask]*p[mask]));r.update(storage_proxy_m2=S,storage_positive_m2=float(np.sum(W[mask]*np.maximum(p[mask],0))),storage_negative_m2=float(np.sum(W[mask]*np.minimum(p[mask],0))),pressure_storage_quadratic_J_per_m=float(.5*np.sum(W[mask]*p[mask]**2)),storage_weight_sum_m2_Pa=float(np.sum(W[mask])),mixture_kinetic_proxy_J_per_m=float(.5*np.sum(d['rho'][mask]*d['V'][mask]*d['speed'][mask]**2)))
        if last is None:change=pressure=weight=membership=residual=budget=None;switches=unchanged=kapinc=None
        else:
            oldmask=last['masks'][cohort];wp,pp=last['W'],last['p'];s0=float(np.sum(wp[oldmask]*pp[oldmask]));pressure=float(np.sum(.5*(W[mask]+wp[mask])*(p[mask]-pp[mask])));weight=float(np.sum(.5*(p[mask]+pp[mask])*(W[mask]-wp[mask])));membership=float(np.sum((mask.astype(int)-oldmask.astype(int))*wp*pp));change=S-s0;residual=change-pressure-weight-membership;budget=(64*5000+16)*np.finfo(float).eps/(1-(64*5000+16)*np.finfo(float).eps)*(abs(S)+abs(s0)+np.sum(np.abs(.5*(W[mask]+wp[mask])*(p[mask]-pp[mask])))+np.sum(np.abs(.5*(p[mask]+pp[mask])*(W[mask]-wp[mask])))+np.sum(np.abs((mask.astype(int)-oldmask.astype(int))*wp*pp)));need(abs(residual)<=budget,'Observed storage product arithmetic identity failed');switches=int(np.count_nonzero(mask&(d['fs']!=last['fs'])));unchanged=int(np.count_nonzero(mask&(~d['fs23'])&(d['p32'].view('<u4')==last['p32'].view('<u4'))));kapinc=int(np.count_nonzero(mask&(d['kappa']>last['kappa'])))
        r.update(storage_delta_m2=change,storage_pressure_change_m2=pressure,storage_weight_change_m2=weight,storage_membership_change_m2=membership,storage_product_residual_m2=residual,storage_product_roundoff_budget_m2=budget,FS_label_change_nodes=switches,nonFS_unchanged_pressure_bits_nodes=unchanged,kappa_history_increment_nodes=kapinc);need(all(math.isfinite(x)for x in r.values()if isinstance(x,float)),'No nonfinite scientific row may be deleted');rows.append(r)
    return rows
def physical(new,old,ref):
    history=[];matched=[];spatial=[];snapshots={};last={c:None for c in CASES}
    for part in range(91):
        data={}
        for label,bundle in zip(CASES,(old,new)):
            d=frame_data(core.core.read22(bundle,part),ref,last[label]);rows=aggregate(label,part,bundle['clocks'][part],d,ref,last[label]);history+=rows;data[label]=d;last[label]=d
            if part in SELECTED:
                snapshots[(label,part)]=d
                for i,nid in enumerate(d['ids']):
                    r=dict(case=label,part=part,completed_step=int(bundle['clocks'][part]['completed_step']),actual_time_s=float(bundle['clocks'][part]['time_s']),tau_s=float(bundle['clocks'][part]['time_s'])-ref['time'],native_id=int(nid),x_m=float(d['pos'][i,0]),y_m=float(d['pos'][i,1]),z_m=float(d['pos'][i,2]),p_Pa=float(d['p'][i]),native_p_minus_fixedP0_Pa=float(d['ex'][i]),NN_over_dp=float(d['nn'][i]),kappa=float(d['kappa'][i]),J=float(d['J'][i]),n=float(d['n'][i]),k_m_s=float(d['k'][i]),speed_m_s=float(d['speed'][i]),effective_stress_Frobenius_Pa=float(d['effnorm'][i]),total_stress_Frobenius_Pa=float(d['totalnorm'][i]),dx_from_PRE_mm=float(1000*d['du'][i,0]),dz_from_PRE_mm=float(1000*d['du'][i,2]),initial_material_layer=int(ref['layer'][i]))
                    for j,axis in enumerate(('xx','yy','zz')):r['effective_'+axis+'_Pa']=float(d['kk'][i,j]);r['total_'+axis+'_Pa']=float(d['total'][i,j])
                    for j,axis in enumerate(('xy','yz','xz')):r['effective_'+axis+'_Pa']=r['total_'+axis+'_Pa']=float(d['ij'][i,j])
                    spatial.append(r)
        a,b=data[CASES[0]],data[CASES[1]];dp=b['p']-a['p'];du=b['pos']-a['pos'];ds=b['total']-a['total'];di=b['ij']-a['ij'];matched.append(dict(part=part,completed_step=int(new['clocks'][part]['completed_step']),actual_time_s=float(new['clocks'][part]['time_s']),tau_s=float(new['clocks'][part]['time_s'])-ref['time'],delta_p_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),delta_p_absmax_Pa=float(np.abs(dp).max()),delta_XYZ_RMS_mm=float(1000*np.sqrt(np.mean(np.sum(du*du,axis=1)))),delta_XYZ_max_mm=float(1000*np.linalg.norm(du,axis=1).max()),delta_total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(di*di,axis=1))))))
    need(len(history)==1092 and len(matched)==91 and len(spatial)==30000,'Every actual91/5000 observation required');return history,matched,spatial,snapshots
def plots(history,snapshots):
    fig,axes=plt.subplots(4,3,figsize=(15,15),layout='constrained');panels=(('p_Pa_RMS','Pressure RMS [Pa]'),('p_Pa_mean','Signed mean pressure [Pa]'),('NN_over_dp_min','Minimum NN / dp'),('unique_pairs_incident_lt_0p5dp','Unique pairs <0.5dp'),('x_front_m','Front x [m]'),('speed_m_s_RMS','Velocity RMS [m/s]'),('storage_proxy_m2','Signed storage proxy [m²]'),('pressure_storage_quadratic_J_per_m','Pressure quadratic [J/m], not total energy'),('J_min','Minimum J'),('effective_stress_Frobenius_Pa_RMS','Effective stress Frobenius RMS [Pa]'),('total_stress_Frobenius_Pa_RMS','Total stress Frobenius RMS [Pa]'),('settlement_from_PRE_mm_mean','Fixed initial top settlement [mm]'))
    for ax,(key,title)in zip(axes.flat,panels):
        for case in CASES:
            rows=[r for r in history if r['case']==case and r['cohort']==('fixed_initial_top'if key=='settlement_from_PRE_mm_mean'else'all')];ax.plot([r['tau_s']for r in rows],[r[key]for r in rows],label=case)
        ax.set_title(title);ax.set_xlabel('Actual time after release [s]');ax.grid(True,alpha=.25);ax.xaxis.set_major_locator(MaxNLocator(nbins=6));ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    axes[0,0].legend(fontsize=9);fig.suptitle('Bounded .90s spatial-operator comparison: all91actual frames / all5000 material IDs\nStorage and pressure quadratic are proxies; no physics or conservation acceptance')
    path=FIG/(TAG+'_history.png');fig.savefig(path,dpi=165);plt.close(fig);paths=[path]
    for field,cmap,title,unit in(('p','coolwarm','Native signed pressure','Pa'),('nn','viridis','True3D nearest-neighbor spacing','dp')):
        values=np.concatenate([d[field]for d in snapshots.values()]);positions=np.concatenate([d['pos']for d in snapshots.values()]);vmin,vmax=float(values.min()),float(values.max());norm=Normalize(vmin=vmin,vmax=vmax);fig,axes=plt.subplots(2,3,figsize=(16,8),layout='constrained')
        for row,case in enumerate(CASES):
            for col,part in enumerate(SELECTED):
                d=snapshots[(case,part)];ax=axes[row,col];sc=ax.scatter(d['pos'][:,0],d['pos'][:,2],c=d[field],s=3,cmap=cmap,norm=norm,rasterized=True);ax.axhline(0,color='.2',lw=.6);ax.axvline(0,color='.2',lw=.6);ax.set_aspect('equal');ax.set_xlim(min(0,float(positions[:,0].min()))-DP,float(positions[:,0].max())+DP);ax.set_ylim(min(0,float(positions[:,2].min()))-DP,float(positions[:,2].max())+DP);clock=next(r for r in history if r['case']==case and r['part']==part and r['cohort']=='all');ax.set_title(case+'\nP'+str(part)+' actual τ='+format(clock['tau_s'],'.9g')+' s');ax.set_xlabel('x [m]');ax.set_ylabel('z [m]');ax.xaxis.set_major_locator(MaxNLocator(nbins=6));ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
        fig.colorbar(sc,ax=axes.ravel().tolist(),label=title+' ['+unit+']',shrink=.85);fig.suptitle(title+': shared colorbar over every selected point; no clipping/smoothing/interpolation');path=FIG/(TAG+'_'+field+'.png');fig.savefig(path,dpi=165);plt.close(fig);paths.append(path)
    return paths
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');need(p.parse_args().execution_authorized,'Separate offline root admission required');outputs=[FIG/(TAG+s)for s in('_history.csv','_matched.csv','_spatial.csv','_cohorts.csv','_timing.csv','_history.png','_p.png','_nn.png')];need(not CHECK.exists()and all(not q.exists()for q in outputs),'Existing complete/partial analysis protected');consumed=[stat(q)for q in(SCRIPT,NOTE,Path(shared.__file__),Path(core.__file__),Path(core.core.__file__),Path(previous.__file__),T/'notes/c08_h18_lstar_conservation_audit_r1.md')]
    try:
        run,original,new,old,ref,cohorts=inputs(consumed);history,matched,spatial,snapshots=physical(new,old,ref);timing=[]
        for case,r in zip(CASES,(original,run)):
            s=r['summary'];loop=float(s['TSimul']);need(math.isfinite(loop)and loop>0,'Actual positive finite loop time required');timing.append(dict(case=case,new_updates=180000,TSimul_s=loop,TTotal_s=float(s['TTotal']),Hardware=s['Hardware'],observed_new_updates_per_s=180000/loop,controlled_benchmark=False))
        shared.frozen(consumed)
        for path,rows in zip(outputs[:5],(history,matched,spatial,cohorts,timing)):write(path,rows)
        pictures=plots(history,snapshots);shared.frozen(consumed);m.save(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,physical_acceptance=False,frames_per_case=91,soil_IDs_each=5000,history_rows=len(history),matched_rows=91,spatial_rows=30000,source_cohort_rows=5000,source_reference_initial_and_PRE_only=True,cohort_names=COHORTS,selected_parts=SELECTED,all_frames_in_statistics=True,all_signed_points_retained=True,storage_is_fluid_mass=False,pressure_quadratic_is_total_energy=False,operator_spectrum_proven=False,actual_pressure_flux_budget_proven=False,old_reference_seals_are_original_decoder_exit=False,observed_timing_not_controlled_benchmark=True,new_solver_invocations=0,new_API_calls=0,new_native_invocations=0,old_analysis_reexecuted=False,SHA_scans=0,visual_QA_pending=True,consumed=consumed,consumed_stats_unchanged=True,files=[stat(q)for q in(*outputs[:5],*pictures)]))
    except Exception as e:
        if not CHECK.exists():m.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),consumed=consumed,partial_outputs_preserved=True,new_solver_invocations=0,new_API_calls=0,new_native_invocations=0,physical_acceptance=False))
        raise
if __name__=='__main__':main()
