"""Sealed54 fixed-plane states versus sealed43 legacy states; descriptive operator comparison only."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json
from pathlib import Path
import numpy as np
import upl_c08_plane_window_review_r1 as w
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_plane_partial_review_r1';PREFIX=T/'figures'/TAG
NEW=T/'outputs/upl_c08_plane_partial_r1';OLD=T/'outputs/upl_c08_r4_partial_r1';NC=L/'upl_c08_plane_partial_r1.check.json';OC=L/'upl_c08_r4_partial_r1.check.json'
RUN=L/'upl_c08_plane_on_GPU_r1.run.json';CALL=L/'upl_c08_plane_on_GPU_r1.call.json';TOL=w.TOL
SAVES=(4040000,4080000,4120000,4172000,4216000);COMPONENTS=('xx','yy','zz','xy','yz','xz')
need,read,stat=w.need,w.read,w.stat

def csvout(leaf,rows):
    path=Path(str(PREFIX)+'_'+leaf+'.csv');need(rows,'Empty derived table')
    with path.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return path

def native_step_scales(n,rho,k,native_ids):
    n=np.asarray(n,dtype=np.float64).reshape(-1);rho=np.asarray(rho,dtype=np.float64).reshape(-1);k=np.asarray(k,dtype=np.float64).reshape(-1);ids=np.asarray(native_ids).reshape(-1)
    need(n.size==rho.size==k.size==ids.size and n.size and np.all(np.isfinite(n)) and np.all((n>0)&(n<1)) and np.all(np.isfinite(rho)) and np.all(rho>0) and np.all(np.isfinite(k)) and np.all(k>0),'Passed native soil ledger/domain required')
    h=float(np.float32(.048));safety=float(np.float32(.1));gamma=1000.*9.80665;M=19607844.+4.*7518796.5/3.
    D=(1e9/n)*k/gamma;cu2=(M+1e9/n)/rho;dm=float(np.max(D));cm=float(np.max(cu2))
    return dict(max_D_m2_s=dm,max_D_native_id=int(np.min(ids[D==dm])),max_cu2_m2_s2=cm,max_cu2_native_id=int(np.min(ids[cu2==cm])),dt_diffusion_only_s=safety*h*h/dm,quiescent_wave_upper_scale_s=float(.2*h/np.sqrt(cm)))

def sealed():
    nc,oc=read(NC),read(OC)
    for c in (nc,oc):need(c['passed'] and c['original_saved_native_guards_passed'] and c['consumed_stats_unchanged'] and not c['runtime_success_claimed'],'Both partial native checks must be sealed passed without runtime-success claim')
    r,c=read(RUN),read(CALL);need(not r['passed'] and r['actual_exit']==r['actual_Win32_exit']==1 and c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==1 and not c['ownership_errors'],'Actual unique failed runtime/owned exits differ')
    need(nc['actual_reported_failure_step']==4218523 and float(nc['actual_reported_current_dt_text'])==2.5e-6 and float(nc['actual_reported_bound_text'])==2.49899e-6,'Recorded necessary-bound first cause differs')
    before=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(w.__file__),NC,OC,RUN,CALL)]
    for native,receipt in ((NEW,nc),(OLD,oc)):
        need(Path(receipt['native_completion']['path']).samefile(native/'completion.json'),'Native completion binding differs')
        for entry in receipt['consumed']+receipt['files']+[receipt['native_completion'],receipt['reader_call']]:need(stat(Path(entry['path']))==entry,'Closed partial provenance changed: '+entry['path']);before.append(entry)
        actual=read(Path(receipt['reader_call']['path']));need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual owned partial reader exit differs')
    new=w.load(NEW,54,4216000);old=w.load(OLD,43,4172000);d=new[1]
    need(d['diagnostic_partial'] and not d['runtime_success_claimed'] and not d['completed_runtime_Run_csv_checked'] and not d['launch_plan_rewritten'] and d['original_launch_plan_samples']==60 and d['used_launch_plan_prefix_samples']==54,'Actual54 prefix must not be called the planned60 or normal completion')
    need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'New fixed-plane policy differs')
    for data,n in ((new,54),(old,43)):
        dd=data[1];counts=dict(ledger_checks=5000*n,fixed_marker_checks=1800*n,P0_bits_checks=6800*n,rho_cache_bits_checks=5000*n,kappa_nondecreasing_from_PRE_checks=5000*n,nonempty_signed_intervals=n)
        need(all(dd[k]==v for k,v in counts.items()) and dd['max_scalar_clock_error_s']<=1e-14 and dd['max_ledger_relative_error']<=5e-13 and dd['max_signed_dterror_s']<=1e-14,'Original partial safety/clock coverage differs')
    need(d['plane_gap_checks']==540000 and d['geometry_tolerance_m']==TOL and d['source_actual_time_s']==old[1]['source_actual_time_s'],'Original plane tolerance or shared actual PRE differs')
    return {'FixedPlane':new,'Legacy_r4':old},before,nc,oc

def summarize(model,bundle,planes):
    a,d,clocks,hist=bundle;ids=a[0]['Idp'][:,0];soil=ids>=2060;sid=ids[soil];rows=[];need(len(sid)==5000,'All5000 material IDs required')
    for part,x in enumerate(a):
        q=lambda field:x[field][soil,0].astype('float64');xyz=x['Posd'][soil];p=q('PorePress');vel=x['Vel'][soil].astype('float64');speed=np.linalg.norm(vel,axis=1);sk,si=w.total(x);eff=x['SigmaState_kk'][soil];off=x['SigmaState_ij'][soil]
        row=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-d['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),p_min_ID=int(sid[np.argmin(p)]),p_max_ID=int(sid[np.argmax(p)]),
                 effective_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(eff*eff,axis=1)+2*np.sum(off*off,axis=1)))),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(np.sum(sk[soil]*sk[soil],axis=1)+2*np.sum(si[soil]*si[soil],axis=1)))),speed_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),speed_max_m_s=float(speed.max()),speed_max_ID=int(sid[np.argmax(speed)]),
                 mean_downward_settlement_native_PRE_mm=-1000*float(hist[part]['mean_dz_from_PRE_m']),min_x_m=float(xyz[:,0].min()),min_z_m=float(xyz[:,2].min()),x_negative_raw_count=int(np.count_nonzero(xyz[:,0]<0)),z_negative_raw_count=int(np.count_nonzero(xyz[:,2]<0)),x_beyond_original_tol_count=int(np.count_nonzero(xyz[:,0]<-TOL)),z_beyond_original_tol_count=int(np.count_nonzero(xyz[:,2]<-TOL)),signed_dterror_s=float(clocks[part]['signed_dterror_s']))
        for key,field in (('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity'),('kappa','Kplastic'),('native_Rhop','native_Rhop')):
            v=q(field);row.update({key+'_min':float(v.min()),key+'_max':float(v.max()),key+'_mean':float(v.mean()),key+'_min_ID':int(sid[np.argmin(v)]),key+'_max_ID':int(sid[np.argmax(v)])})
        j=q('PoroVolumeRatio');row['J_min_tied_ID_count']=int(np.count_nonzero(j==j.min()));row['J_max_tied_ID_count']=int(np.count_nonzero(j==j.max()))
        effective6=np.column_stack((eff,off));total6=np.column_stack((sk[soil],si[soil]))
        for c,name in enumerate(COMPONENTS):
            e=effective6[:,c];t=total6[:,c]
            row.update({'sigmaeff_'+name+'_min_Pa':float(e.min()),'sigmaeff_'+name+'_max_Pa':float(e.max()),'total_sigma_'+name+'_min_Pa':float(t.min()),'total_sigma_'+name+'_max_Pa':float(t.max())})
        row.update(native_step_scales(q('PoroPorosity'),q('PoroMixtureDensity'),q('PoroHydraulicConductivity'),sid))
        if model=='FixedPlane':
            plane=planes[part];need(float(plane['time_s'])==row['time_s'] and int(plane['completed_step'])==row['completed_step'] and float(plane['geometry_tolerance_m'])==TOL and float(plane['min_soil_x_m'])==row['min_x_m'] and float(plane['min_soil_z_m'])==row['min_z_m'],'Native plane observations differ')
        rows.append(row)
    return rows

def selections(rows):
    result=[]
    for model in ('FixedPlane','Legacy_r4'):
        rr=[r for r in rows if r['model']==model]
        for key,direction,idkey in (('p_min_Pa',min,'p_min_ID'),('p_max_Pa',max,'p_max_ID'),('J_min',min,'J_min_ID'),('J_max',max,'J_max_ID'),('speed_max_m_s',max,'speed_max_ID'),('kappa_max',max,'kappa_max_ID')):
            for scope,r in (('final',rr[-1]),('window',direction(rr,key=lambda r:r[key]))):result.append(dict(model=model,scope=scope,criterion=key,part=r['part'],time_s=r['time_s'],tau_s=r['tau_s'],native_ID=r[idkey],value=r[key]))
    return result

def tracked(sets,chosen):
    roles={7010:['fixed7010'],7011:['fixed7011']}
    for r in chosen:roles.setdefault(r['native_ID'],[]).append(r['model']+':'+r['scope']+':'+r['criterion'])
    rows=[]
    for model,(data,d,clocks,hist) in sets.items():
        ids=data[0]['Idp'][:,0];slots={idp:int(np.searchsorted(ids,idp)) for idp in sorted(roles)}
        need(all(ids[slot]==idp for idp,slot in slots.items()),'Tracked material ID missing')
        for part,x in enumerate(data):
            sk,si=w.total(x)
            for idp,slot in slots.items():
                v=x['Vel'][slot].astype('float64');row=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-d['source_actual_time_s'],native_ID=idp,selection_roles=';'.join(roles[idp]),x_m=float(x['Posd'][slot,0]),y_m=float(x['Posd'][slot,1]),z_m=float(x['Posd'][slot,2]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)))
                for key,field in (('p_Pa','PorePress'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k_m_s','PoroHydraulicConductivity')):row[key]=float(x[field][slot,0])
                for c,name in enumerate(COMPONENTS):row['sigmaeff_'+name+'_Pa']=float(np.r_[x['SigmaState_kk'][slot],x['SigmaState_ij'][slot]][c]);row['total_sigma_'+name+'_Pa']=float(np.r_[sk[slot],si[slot]][c])
                rows.append(row)
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline analysis');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing partial/complete derived outputs protected')
    sets,before,nc,oc=sealed();planes=list(csv.DictReader((NEW/'plane_gaps.csv').open(encoding='utf-8')));need(len(planes)==54,'Exactly54 original plane observations required')
    rows=[r for model,bundle in sets.items() for r in summarize(model,bundle,planes)];chosen=selections(rows);points=tracked(sets,chosen);matched=[];new=sets['FixedPlane'];old=sets['Legacy_r4'];a,d,clocks,hist=new
    for j,x in enumerate(old[0]):
        hits=np.flatnonzero(np.abs(a['time']-x['time'])<=1e-14);need(len(hits)==1,'Old actual time lacks unique new match; no interpolation');i=int(hits[0]);need(int(clocks[i]['completed_step'])==int(old[2][j]['completed_step']) and np.array_equal(a[i]['Idp'],x['Idp']),'Matched material IDs/actual Steps differ')
        soil=x['Idp'][:,0]>=2060;p=a[i]['PorePress'][soil].astype('float64')-x['PorePress'][soil].astype('float64');dx=(a[i]['Posd'][soil]-x['Posd'][soil])*1000;ns,nt=w.total(a[i]);old_s,old_t=w.total(x);ds=ns[soil]-old_s[soil];dt=nt[soil]-old_t[soil]
        row=dict(old_part=j,new_part=i,old_time_s=float(x['time']),new_time_s=float(a[i]['time']),completed_step=int(clocks[i]['completed_step']),tau_s=float(a[i]['time'])-d['source_actual_time_s'],pressure_RMS_difference_Pa=float(np.sqrt(np.mean(p*p))),material_XYZmax_difference_mm=float(np.abs(dx).max()),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))))
        for key,field in (('velocity','Vel'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):row[key+'_max_abs_difference']=float(np.max(np.abs(a[i][field][soil].astype('float64')-x[field][soil].astype('float64'))))
        matched.append(row)
    need(len(matched)==43,'All43 actual common states required');files=[csvout('history',rows),csvout('selected_IDs',chosen),csvout('material_tracks',points),csvout('matched43',matched)]
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axs=plt.subplots(4,3,figsize=(16,13),layout='constrained')
    for ax,key,title,unit,scale in zip(axs.flat[:6],('p_RMS_Pa','p_min_Pa','total_stress_Frobenius_RMS_Pa','speed_RMS_m_s','kappa_max','mean_downward_settlement_native_PRE_mm'),('Pressure RMS','Minimum absolute pore pressure','Total stress Frobenius RMS','Speed RMS XYZ','Maximum plastic history','Mean material settlement'),('kPa','kPa','kPa','m/s','kappa','downward mm'),(.001,.001,.001,1,1,1)):w.series(ax,rows,key,title,unit,scale)
    for ax,key,unit in zip(axs.flat[6:10],('J','n','rho','k'),('J','porosity','kg/m3','m/s')):
        for model,color,style in (('FixedPlane','C0','-'),('Legacy_r4','.45','--')):
            rr=[r for r in rows if r['model']==model]
            for suffix in ('min','max'):ax.plot([r['tau_s'] for r in rr],[r[key+'_'+suffix] for r in rr],style,color=color,label=model+' '+suffix)
        ax.set(title=key+' full soil range',xlabel='Actual tau [s]',ylabel=unit)
    for model,color,style in (('FixedPlane','C0','-'),('Legacy_r4','.45','--')):
        rr=[r for r in rows if r['model']==model];tau=[r['tau_s'] for r in rr]
        for axis in ('x','z'):axs.flat[10].plot(tau,[r['min_'+axis+'_m']*1000 for r in rr],style,label=model+' min'+axis);axs.flat[11].plot(tau,[r[axis+'_beyond_original_tol_count'] for r in rr],style,label=model+' '+axis)
    axs.flat[10].axhline(-TOL*1000,c='red',lw=.7);axs.flat[10].set(title='Plane gaps; original40nm tolerance',ylabel='mm',xlabel='Actual tau [s]');axs.flat[11].set(title='Beyond tolerance, not contact telemetry',ylabel='soil IDs',xlabel='Actual tau [s]')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('Failed fixed-plane54 versus failed legacy43 saved states: descriptive, no5Pa/theory gate');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,key,title,scale in zip(axs.flat[:4],('z_m','vz_m_s','kappa','p_Pa'),('7010/7011 z [m]','7010/7011 vz [m/s]','7010/7011 kappa','7010/7011 pressure [kPa]'),(1,1,1,.001)):
        for model,style in (('FixedPlane','-'),('Legacy_r4','--')):
            for idp,color in ((7010,'C0'),(7011,'C1')):
                rr=[r for r in points if r['model']==model and r['native_ID']==idp];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,color=color,label=model+' '+str(idp))
        ax.set(title=title,xlabel='Actual tau [s]')
    for ax,key,criteria,title,scale in ((axs.flat[4],'p_Pa',('p_min_Pa',),'Selected final/window negative-peak IDs [kPa]',.001),(axs.flat[5],'J',('J_min','J_max'),'Selected final/window J-extreme IDs',1)):
        for model,style in (('FixedPlane','-'),('Legacy_r4','--')):
            ids=sorted({r['native_ID'] for r in chosen if r['model']==model and r['criterion'] in criteria})
            for idp in ids:
                rr=[r for r in points if r['model']==model and r['native_ID']==idp];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,label=model+' '+str(idp))
        ax.set(title=title,xlabel='Actual tau [s]')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=6)
    path=Path(str(PREFIX)+'_material.png');fig.savefig(path);plt.close(fig);files.append(path)
    for field,label,cmap,scale in (('PorePress','Native absolute pore pressure [kPa]','RdBu_r',.001),('Kplastic','Native plastic history','viridis',1)):
        lo=min(float(b[0][field][:,1800:,0].min()) for b in sets.values())*scale;hi=max(float(b[0][field][:,1800:,0].max()) for b in sets.values())*scale;fig,axs=plt.subplots(2,len(SAVES),figsize=(18,7),layout='constrained',sharex=True,sharey=True);scatter=[];mappable=None
        for rindex,(model,(data,done,clock,h)) in enumerate(sets.items()):
            for col,step in enumerate(SAVES):
                ax=axs[rindex,col];hits=[i for i,c in enumerate(clock) if int(c['completed_step'])==step];need(len(hits)<=1,'Duplicate saved Step')
                if not hits:ax.text(.5,.5,'No saved state\nNo interpolation',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
                i=hits[0];x=data[i];soil=x['Idp'][:,0]>=2060;pos=x['Posd'][soil];v=x[field][soil,0].astype('float64');tau=float(x['time'])-done['source_actual_time_s'];mappable=ax.scatter(pos[:,0],pos[:,2],c=v*scale,s=2,cmap=cmap,vmin=lo,vmax=hi,linewidths=0);ax.set(title=model+' tau='+format(tau,'.6f'),xlabel='x [m]',ylabel='z [m]',aspect='equal');ax.axhline(0,c='black',lw=.5);ax.axvline(0,c='black',lw=.5)
                scatter.extend(dict(model=model,part=i,time_s=float(x['time']),tau_s=tau,completed_step=step,native_ID=int(idp),x_m=float(p[0]),z_m=float(p[2]),**{field:float(vv)}) for idp,p,vv in zip(x['Idp'][soil,0],pos,v))
        fig.colorbar(mappable,ax=axs.ravel().tolist(),label=label,shrink=.7);fig.suptitle('All5000 native particles; same raw color range, no interpolation/smoothing/clipping');path=Path(str(PREFIX)+'_morph_'+field+'.png');fig.savefig(path);plt.close(fig);files.extend((path,csvout('morph_'+field,scatter)))
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed data changed')
    report=dict(stage=TAG,passed=True,analysis_completed=True,runtime_success_claimed=False,physical_acceptance=False,new_frames=54,old_partial_frames=43,actual_common_time_step_pairs=43,new_actual_end_s=float(a[-1]['time']),new_last_saved_completed_step=int(clocks[-1]['completed_step']),
                current_failure_step=nc['actual_reported_failure_step'],current_failure_line=nc['actual_failure_line'],old_MLS_failure_line=oc['actual_runtime_diagnostic_line'],actual_unsaved_failure_state_reconstructed=False,planned60_not_relabelled_completed=True,geometry_tolerance_m=TOL,
                NoPen_policy=d['DynamicNoPenetrationPolicy'],reaction_J_Darcy_closed=False,option_difference_not_error_against_theory_or_half=True,no_new_5Pa_gate=True,no_sigma_J_theory_gate=True,no_dt_change_recommendation=True,
                snapshot_scales_are_saved_full_stage_only=True,quiescent_wave_is_upper_scale_not_actual_guard=True,gradJ_C_ViscDt_force_VelMax_missing=True,selected_extreme_IDs=chosen,new_final=next(r for r in reversed(rows) if r['model']=='FixedPlane'),old_final=next(r for r in reversed(rows) if r['model']=='Legacy_r4'),
                solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(p) for p in files])
    path=Path(str(PREFIX)+'.check.json')
    with path.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print('PARTIAL_OFFLINE_REVIEW_READY',path,flush=True)

if __name__=='__main__':main()
