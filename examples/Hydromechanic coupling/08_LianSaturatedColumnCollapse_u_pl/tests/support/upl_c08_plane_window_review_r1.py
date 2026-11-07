"""Once-off offline0.6s fixed-plane review versus sealed r4 partial43; no tools or automatic solver."""
import argparse,csv,json,re,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_plane_window_review_r1';PREFIX=T/'figures'/TAG
NEW=T/'outputs/upl_c08_plane_on_GPU_r1/native';OLD=T/'outputs/upl_c08_r4_partial_r1';NC=L/'upl_c08_plane_on_GPU_r1.native.json';OC=L/'upl_c08_r4_partial_r1.check.json'
SAVES=[(.1,4040000),(.2,4080000),(.3,4120000),(.43,4172000),(.5,4200000),(.6,4240000)];TOL=1e-6*.04

def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def stat(p):
    q=p.resolve();s=q.stat();return dict(path=str(q),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def csvout(leaf,rows):
    path=Path(str(PREFIX)+'_'+leaf+'.csv')
    with path.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return path

def load(folder,n,end):
    d=read(folder/'completion.json');need(d['passed'] and d['samples']==n and d['completed_steps']==end and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6800,'Closed native coverage differs')
    layout=list(csv.DictReader((folder/'typed22_layout.csv').open(encoding='utf8')));need(len(layout)==22,'Original22 layout required');fields=[('time','<f8')]
    for spec in layout:
        dt={'uint32':'<u4','float32':'<f4','float64':'<f8'}[spec['type']];width=int(spec['components']);need(np.dtype(dt).itemsize*width==int(spec['bytes_per_particle']),'Actual typed layout byte width differs');fields.append((spec['array'],dt,(6800,width)))
    dtype=np.dtype(fields);need(dtype.itemsize==8+6800*212,'Actual typed record stride differs')
    with (folder/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6800,22,n),'Original real header differs; no rewrite')
    need((folder/'typed22.bin').stat().st_size==12+n*dtype.itemsize,'Actual full payload length differs');a=np.memmap(folder/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(n,));clocks=list(csv.DictReader((folder/'clocks.csv').open(encoding='utf8')));history=list(csv.DictReader((folder/'history.csv').open(encoding='utf8')));need(len(clocks)==len(history)==n,'Original clocks/history counts differ');ids=a[0]['Idp'][:,0]
    need(np.array_equal(ids,np.r_[np.arange(1800),np.arange(2060,7060)]) and all(np.array_equal(x['Idp'][:,0],ids) for x in a),'Actual material IDs differ')
    for i,x in enumerate(a):need(float(clocks[i]['time_s'])==x['time'] and int(clocks[i]['completed_step'])==int(clocks[i]['saved_step'])+1 and np.isfinite(float(clocks[i]['signed_dterror_s'])) and float(clocks[i]['signed_dterror_s'])<=1e-14,'Actual saved clock/signed diagnostic differs')
    return a,d,clocks,history

def total(x):return x['SigmaState_kk']-x['PorePress'].astype('float64'),x['SigmaState_ij']
def series(ax,rows,key,title,unit,scale=1.):
    for model,color,style in [('FixedPlane','C0','-'),('Legacy_r4','0.45','--')]:
        r=[v for v in rows if v['model']==model];ax.plot([v['tau_s'] for v in r],[v[key]*scale for v in r],style,color=color,label=model,lw=1.6)
    ax.set(title=title,xlabel='Actual time since PRE [s]',ylabel=unit);ax.grid(alpha=.25);ax.legend(fontsize=7)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read before one offline review');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial review products protected')
    # Read no growing data: both immutable native receipts must be sealed before any payload is opened.
    nc,oc=read(NC),read(OC);need(nc['passed'] and nc['consumed_stats_unchanged'] and oc['passed'] and oc['original_saved_native_guards_passed'] and oc['consumed_stats_unchanged'],'Both native reviews must be sealed passed')
    run=L/'upl_c08_plane_on_GPU_r1.run.json';call=L/'upl_c08_plane_on_GPU_r1.call.json';r,c=read(run),read(call);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4240000 and r['saved_frames']==60 and r['consumed_stats_unchanged'] and c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and not c['ownership_errors'],'Completed unique0.6s runtime required')
    new=load(NEW,60,4240000);old=load(OLD,43,4172000);a,d,clock,history=new
    need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'] and not d['reaction_J_Darcy_closed'] and d['saved_steps_checked_against_launch_plan'] and d['completed_runtime_Run_csv_checked'],'New native fixed-plane scope differs')
    counts=dict(ledger_checks=300000,fixed_marker_checks=108000,P0_bits_checks=408000,rho_cache_bits_checks=300000,kappa_nondecreasing_from_PRE_checks=300000,nonempty_signed_intervals=60,plane_gap_checks=600000)
    need(all(d[k]==v for k,v in counts.items()) and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original60-frame safety/ledger/clock coverage not complete');need(old[1]['source_actual_time_s']==d['source_actual_time_s'],'Actual PRE clocks differ')
    need(Path(nc['completion']['path']).samefile(NEW/'completion.json') and Path(oc['native_completion']['path']).samefile(OLD/'completion.json'),'Native receipt bindings differ')
    readercall=read(nc['actual_call']['path']);need(readercall['actual_Popen_wait_exit']==readercall['actual_Win32_exit']==0 and readercall['ownership_failure'] is None,'Actual new reader exit differs')
    for folder,receipt,leaves in [(NEW,nc,['completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv']),(OLD,oc,['completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv'])]:
        entries=receipt.get('outputs',receipt.get('files',[]))
        for leaf in leaves:
            entry=next(e for e in entries if Path(e['path']).samefile(folder/leaf));need(stat(folder/leaf)==entry,'Closed native output binding changed: '+leaf)
    need(stat(Path(nc['actual_call']['path']))==nc['actual_call'],'Actual reader call binding changed')
    consumed=[stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),NC,OC,run,call,Path(nc['actual_call']['path']))]+[stat(folder/leaf) for folder in (NEW,OLD) for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv')]+[stat(NEW/'plane_gaps.csv')]
    for entry in (r['program'],r['source_build'],r['source_pre_file'],r['input_xml']):need(stat(Path(entry['path']))==entry,'Actual runtime provenance changed');consumed.append(entry)
    sets={'FixedPlane':new,'Legacy_r4':old};rows=[];points=[];matched=[];morph={'pressure':[],'kappa':[]};plane=list(csv.DictReader((NEW/'plane_gaps.csv').open(encoding='utf8')));need(len(plane)==60,'Original60 plane observations incomplete')
    for model,(data,done,clocks,hist) in sets.items():
        ids=data[0]['Idp'][:,0];soil=ids>=2060;need(int(soil.sum())==5000,'All5000 material soil IDs required')
        for part,x in enumerate(data):
            tau=float(x['time'])-done['source_actual_time_s'];xyz=x['Posd'][soil];vel=x['Vel'][soil].astype('float64');speed2=np.sum(vel*vel,axis=1);p=x['PorePress'][soil,0].astype('float64');sk,si=total(x);frob=np.sum(sk[soil]*sk[soil],axis=1)+2*np.sum(si[soil]*si[soil],axis=1)
            minx=float(xyz[:,0].min());minz=float(xyz[:,2].min());badx=int(np.count_nonzero(xyz[:,0]<-TOL));badz=int(np.count_nonzero(xyz[:,2]<-TOL));nearx=int(np.count_nonzero(np.abs(xyz[:,0])<=TOL));nearz=int(np.count_nonzero(np.abs(xyz[:,2])<=TOL))
            if model=='FixedPlane':need(float(plane[part]['min_soil_x_m'])==minx and float(plane[part]['min_soil_z_m'])==minz and int(plane[part]['completed_step'])==int(clocks[part]['completed_step']) and float(plane[part]['geometry_tolerance_m'])==TOL,'Saved plane observations do not match typed positions')
            rows.append(dict(model=model,part=part,time_s=float(x['time']),tau_s=tau,completed_step=int(clocks[part]['completed_step']),p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob))),speed_RMS_m_s=float(np.sqrt(np.mean(speed2))),speed_max_m_s=float(np.sqrt(speed2.max())),kappa_mean=float(x['Kplastic'][soil].mean()),kappa_max=float(x['Kplastic'][soil].max()),J_min=float(x['PoroVolumeRatio'][soil].min()),J_max=float(x['PoroVolumeRatio'][soil].max()),min_x_m=minx,min_z_m=minz,x_beyond_original_tol_count=badx,z_beyond_original_tol_count=badz,geometric_near_x_plane_count=nearx,geometric_near_z_plane_count=nearz,mean_downward_settlement_native_PRE_mm=-1000*float(hist[part]['mean_dz_from_PRE_m']),signed_dterror_s=float(clocks[part]['signed_dterror_s'])))
            for idp in (7010,7011):
                j=int(np.searchsorted(ids,idp));need(ids[j]==idp,'Fixed tracked material ID missing');v=x['Vel'][j].astype('float64');points.append(dict(model=model,part=part,time_s=float(x['time']),tau_s=tau,native_ID=idp,x_m=float(x['Posd'][j,0]),y_m=float(x['Posd'][j,1]),z_m=float(x['Posd'][j,2]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),speed_m_s=float(np.sqrt(np.sum(v*v))),kappa=float(x['Kplastic'][j,0]),p_Pa=float(x['PorePress'][j,0]),J=float(x['PoroVolumeRatio'][j,0]),porosity=float(x['PoroPorosity'][j,0]),conductivity_m_s=float(x['PoroHydraulicConductivity'][j,0]),total_zz_Pa=float(sk[j,2])))
    b=old[0]
    for j,x in enumerate(b):
        hits=np.flatnonzero(np.abs(a['time']-x['time'])<=1e-14);need(len(hits)==1,'Old actual saved time lacks a unique new match; no interpolation permitted');i=int(hits[0]);need(np.array_equal(a[i]['Idp'],x['Idp']) and int(clock[i]['completed_step'])==int(old[2][j]['completed_step']),'Matched original material IDs/global steps differ');soil=x['Idp'][:,0]>=2060;dp=a[i]['PorePress'][soil].astype('float64')-x['PorePress'][soil].astype('float64');du=(a[i]['Posd'][soil]-x['Posd'][soil])*1000.;nsk,nsi=total(a[i]);osk,osi=total(x);ds=nsk[soil]-osk[soil];dt=nsi[soil]-osi[soil]
        matched.append(dict(old_part=j,new_part=i,old_time_s=float(x['time']),new_time_s=float(a[i]['time']),actual_tau_s=float(a[i]['time'])-d['source_actual_time_s'],pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZmax_difference_mm=float(np.max(np.abs(du))),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))),max_kappa_difference=float(np.max(np.abs(a[i]['Kplastic'][soil].astype('float64')-x['Kplastic'][soil].astype('float64'))))))
    files=[csvout('history',rows),csvout('material7010_7011',points),csvout('matched43',matched)]
    plt.rcParams.update({'font.size':8,'figure.dpi':170});fig,axs=plt.subplots(4,3,figsize=(16,14),layout='constrained')
    for ax,key,title,unit,scale in zip(axs.ravel()[:6],['p_RMS_Pa','total_stress_Frobenius_RMS_Pa','speed_RMS_m_s','kappa_max','J_min','mean_downward_settlement_native_PRE_mm'],['All5000: absolute pressure RMS','All5000: total stress RMS','All5000: speed RMS (XYZ)','All5000: maximum plastic history','All5000: minimum volume ratio','All5000: mean material settlement'],['Pressure [kPa]','Stress [kPa]','Speed [m/s]','Accumulated plastic history','J','Downward displacement [mm]'],[.001,.001,1,1,1,1]):series(ax,rows,key,title,unit,scale)
    for model,color,style in [('FixedPlane','C0','-'),('Legacy_r4','0.45','--')]:
        rr=[x for x in rows if x['model']==model];t=[x['tau_s'] for x in rr]
        for key,label in [('min_x_m','x'),('min_z_m','z')]:axs[2,0].plot(t,[x[key]*1000 for x in rr],style,color=color,label=model+' min'+label)
        for key,label in [('x_beyond_original_tol_count','x outside tol'),('z_beyond_original_tol_count','z outside tol'),('geometric_near_z_plane_count','near bed')]:axs[2,1].plot(t,[x[key] for x in rr],style,label=model+' '+label)
    axs[2,0].axhline(-TOL*1000,color='r',lw=.8,label='Original geometry tolerance');axs[2,0].set(title='Ideal0-plane minimum gaps',ylabel='Gap [mm]',xlabel='Actual tau [s]');axs[2,1].set(title='Geometric counts, not force/contact telemetry',ylabel='Material IDs',xlabel='Actual tau [s]')
    for ax,key,title,unit in [(axs[2,2],'z_m','Fixed7010/7011: vertical trajectories','z [m]'),(axs[3,0],'vz_m_s','Fixed7010/7011: vertical velocity','vz [m/s]'),(axs[3,1],'kappa','Fixed7010/7011: plastic history','Accumulated plastic history'),(axs[3,2],'p_Pa','Fixed7010/7011: pore pressure','p [kPa]')]:
        for model,style in [('FixedPlane','-'),('Legacy_r4','--')]:
            for idp,color in [(7010,'C0'),(7011,'C1')]:
                rr=[x for x in points if x['model']==model and x['native_ID']==idp];ax.plot([x['tau_s'] for x in rr],[x[key]*(.001 if key=='p_Pa' else 1) for x in rr],style,color=color,label=model+' '+str(idp))
        ax.set(title=title,ylabel=unit,xlabel='Actual tau [s]')
    for ax in axs.ravel():ax.grid(alpha=.25);ax.legend(fontsize=6)
    fig.suptitle('C08 bounded fixed-plane candidate versus failed legacy r4 saved states; no theory/half/force-closure claim');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    selections={}
    for model,(data,done,clocks,_) in sets.items():
        selections[model]=[]
        for requested,step in SAVES:
            hit=[i for i,q in enumerate(clocks) if int(q['completed_step'])==step];need(len(hit)<=1,'Duplicate saved global step');selections[model].append(hit[0] if hit else None)
            if model=='FixedPlane':need(len(hit)==1,'Requested new native scatter state absent')
    for field,label,cmap,scale in [('pressure','Native pore pressure [kPa]','RdBu_r',.001),('kappa','Accumulated plastic history','viridis',1.)]:
        key='PorePress' if field=='pressure' else 'Kplastic';low=min(float(data[key][:,data[0]['Idp'][:,0]>=2060].min()) for data,_,_,_ in sets.values())*scale;high=max(float(data[key][:,data[0]['Idp'][:,0]>=2060].max()) for data,_,_,_ in sets.values())*scale;fig,axes=plt.subplots(2,6,figsize=(19,7),layout='constrained',sharex=True,sharey=True);mappable=None
        for row,model in enumerate(('FixedPlane','Legacy_r4')):
            data,done,clocks,_=sets[model];soil=data[0]['Idp'][:,0]>=2060
            for col,(requested,step) in enumerate(SAVES):
                ax=axes[row,col];i=selections[model][col]
                if i is None:ax.text(.5,.5,'No old saved state\nNo interpolation',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
                x=data[i];pos=x['Posd'][soil];values=x[key][soil,0].astype('float64');tau=float(x['time'])-done['source_actual_time_s'];mappable=ax.scatter(pos[:,0],pos[:,2],c=values*scale,s=2,cmap=cmap,vmin=low,vmax=high,linewidths=0);ax.set(title=model+' actual tau='+format(tau,'.6f'),xlabel='x [m]',ylabel='z [m]');ax.set_aspect('equal',adjustable='box');ax.axhline(0,color='k',lw=.4);ax.axvline(0,color='k',lw=.4)
                for idp,pp,value in zip(x['Idp'][soil,0],pos,values):morph[field].append(dict(model=model,requested_tau_s=requested,actual_time_s=float(x['time']),actual_tau_s=tau,completed_step=step,native_ID=int(idp),x_m=float(pp[0]),z_m=float(pp[2]),**{('PorePress_Pa' if field=='pressure' else 'Kplastic'):float(value)}))
        fig.colorbar(mappable,ax=axes.ravel().tolist(),label=label,shrink=.7);fig.suptitle('Native particle scatter: '+field+'; shared actual data range, no interpolation/smoothing/clipping');path=Path(str(PREFIX)+'_morph_'+field+'.png');fig.savefig(path);plt.close(fig);files += [path,csvout('morph_'+field,morph[field])]
    line=oc['actual_runtime_diagnostic_line'];m=re.search(r'\bstep_start=([^ ]+) step=(\d+) ',line);need(m is not None,'Old recorded source-stage failure clock missing');old_failure=float(m[1]);covered=float(a[-1]['time'])>=old_failure;need(all(stat(Path(e['path']))==e for e in consumed),'Consumed closed data changed')
    report=dict(stage=TAG,passed=True,bounded_native_review_completed=True,physical_acceptance=False,solver_invocations=0,reader_invocations=0,automatic_full_admission=False,SHA_scans=0,new_frames=60,old_partial_frames=43,matched_actual_times=43,new_actual_end_s=float(a[-1]['time']),actual_PRE_time_s=d['source_actual_time_s'],old_reported_force_stage_source_time_s=old_failure,old_reported_force_stage_step=int(m[2]),new_saved_window_covers_old_reported_source_clock=covered,new_saved_frames_after_old_reported_source_clock=int(np.count_nonzero(a['time']>old_failure)),old_unsaved_failure_state_reconstructed=False,NoPen_policy=d['DynamicNoPenetrationPolicy'],force_or_reaction_observed=False,reaction_J_Darcy_closed=False,option_comparison_not_half_or_theory_error=True,no_paper_matching_or_posthoc_threshold=True,Vel_components='Actual22 typed Vel float32 XYZ; converted to float64 only for norms/CSV.',geometry_counts_are_ideal0_with_original_tolerance_m=TOL,geometric_near_plane_counts_are_not_active_contact_or_force_telemetry=True,max_matched_pressure_RMS_difference_Pa=max(q['pressure_RMS_difference_Pa'] for q in matched),max_matched_material_XYZ_difference_mm=max(q['material_XYZmax_difference_mm'] for q in matched),new_final=next(x for x in reversed(rows) if x['model']=='FixedPlane'),old_final=next(x for x in reversed(rows) if x['model']=='Legacy_r4'),consumed=consumed,files=[stat(p) for p in files])
    path=Path(str(PREFIX)+'.check.json')
    with path.open('x',encoding='utf8') as f:json.dump(report,f,indent=2);f.write('\n')
    print('BOUNDED_OFFLINE_REVIEW_READY',path,flush=True)
if __name__=='__main__':main()
