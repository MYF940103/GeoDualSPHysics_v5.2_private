"""Author-only AS1 window versus sealed AS0 fixed-plane54; derived observations, no automatic tools."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import upl_c08_plane_window_review_r1 as w
import upl_c08_plane_partial_review_r1 as prior
from upl_c08_as_effect_r1 import vtk_positions
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_asplane_window_review_r1';PREFIX=T/'figures'/TAG
NEW=T/'outputs/upl_c08_asplane_window_GPU_r1/native';OLD=T/'outputs/upl_c08_plane_partial_r1'
NC=L/'upl_c08_asplane_window_GPU_r1.native.json';OC=L/'upl_c08_plane_partial_r1.check.json'
PREVTK=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/particles'
TRACK=(4808,4859,5809,5556,7010,7011);STEPS=(4040000,4120000,4196000,4216000,4240000)
need,read,stat=w.need,w.read,w.stat

def bind(entry):
    need(stat(Path(entry['path']))==entry,'Closed file identity changed: '+entry['path']);return entry
def csvout(name,rows):
    path=Path(str(PREFIX)+'_'+name+'.csv');need(rows,'Empty derived table')
    with path.open('x',encoding='utf-8',newline='') as f:q=csv.DictWriter(f,fieldnames=list(rows[0]));q.writeheader();q.writerows(rows)
    return path

def sealed():
    nc,oc=read(NC),read(OC)
    need(nc['passed'] and nc['expected_AS'] is True and nc['original_native_guards_passed'] and nc['consumed_stats_unchanged'],'Closed AS1 native review required')
    need(oc['passed'] and oc['original_saved_native_guards_passed'] and oc['consumed_stats_unchanged'] and not oc['runtime_success_claimed'],'Closed original AS0 partial54 required')
    before=[stat(q) for q in (Path(__file__),T/'notes'/(TAG+'.md'),Path(w.__file__),Path(prior.__file__),T/'support/upl_c08_as_effect_r1.py',NC,OC)]
    run=read(Path(bind(nc['source_run'])['path']));before.append(nc['source_run'])
    need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['actual_steps']==4240000 and run['saved_frames']==60 and run['consumed_stats_unchanged'] and run['ArtificialStress'] is True and run['target_backend']=='GPU','Actual normal AS1 window is not closed60')
    call=read(Path(bind(run['actual_call'])['path']));before.append(run['actual_call'])
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['actual_solver_Win32_exit']==0 and not call['ownership_errors'],'Actual unique solver/tool exits differ')
    for key in ('program','source_build','source_pre_file','input_xml'):before.append(bind(run[key]))
    build=read(Path(run['source_build']['path']));need(build['passed'] and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and run['program']==build['program'],'Executed AS1 program/build identity differs')
    for folder,receipt,entries,completion,reader in ((NEW,nc,nc['outputs'],nc['completion'],nc['actual_call']),(OLD,oc,oc['files'],oc['native_completion'],oc['reader_call'])):
        need(Path(bind(completion)['path']).samefile(folder/'completion.json'),'Native completion path differs');before.append(completion)
        actual=read(Path(bind(reader)['path']));before.append(reader);need(actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0 and actual['ownership_failure'] is None,'Actual original reader exit differs')
        for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv','plane_gaps.csv'):
            before.append(bind(next(e for e in entries if Path(e['path']).samefile(folder/leaf))))
    before.append(bind(nc['AS_metadata']));need(Path(nc['AS_metadata']['path']).samefile(NEW/'AS_metadata.json'),'AS metadata binding differs');m=read(NEW/'AS_metadata.json')
    need(m['passed'] and m['stage']=='upl_c08_as_plane_native_r2' and m['expected_AS'] is True and m['NoPenOn_required'] and m['samples']==60 and m['completed_steps']==4240000 and m['AS_active_true_headers']==m['AS_policy_present_headers']==m['metadata_header_scans']==60 and m['AS_policy_when_enabled']=='ReleaseOnly' and m['AS_coefficient_float_reference']==float(np.float32(.2)) and m['AS_exponent_float_reference']==float(np.float32(2.55)) and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_numerical_guards_modified'] and not m['PRE_arrays_reloaded_by_adapter'],'Original AS metadata/header coverage differs')
    sets={'AS0':w.load(OLD,54,4216000),'AS1':w.load(NEW,60,4240000)}
    for model,(data,d,clocks,hist) in sets.items():
        n=len(data);counts=dict(ledger_checks=5000*n,fixed_marker_checks=1800*n,P0_bits_checks=6800*n,rho_cache_bits_checks=5000*n,kappa_nondecreasing_from_PRE_checks=5000*n,nonempty_signed_intervals=n,plane_gap_checks=10000*n)
        need(all(d[k]==v for k,v in counts.items()) and d['FS23_pressure_checks']>0 and d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14,'Original per-frame22/ID/ledger/P0/FS/clock/plane guards differ')
        need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'Fixed-plane scope differs')
    need(sets['AS1'][1]['completed_runtime_Run_csv_checked'] and not sets['AS0'][1]['runtime_success_claimed'] and sets['AS0'][1]['diagnostic_partial'] and sets['AS0'][1]['original_launch_plan_samples']==60 and sets['AS0'][1]['used_launch_plan_prefix_samples']==54,'Actual normal60/failed-prefix54 distinction lost')
    need(sets['AS0'][1]['source_actual_time_s']==sets['AS1'][1]['source_actual_time_s'],'Actual certified PRE clocks differ')
    before.append(bind(next(e for e in oc['consumed'] if Path(e['path']).samefile(run['source_pre_file']['path']))))
    oldout=T/'outputs/upl_c08_plane_on_GPU_r1/Run.out';oldentry=next(e for e in oc['consumed'] if Path(e['path']).samefile(oldout));before.append(bind(oldentry));need('ArtificialStress="None"' in oldout.read_text(encoding='utf-8-sig'),'Original AS0 executed policy differs')
    return sets,before

def layers(before):
    a,initial,itype=vtk_positions(PREVTK/'PartFluid_0000.vtk');b,pre,ptype=vtk_positions(PREVTK/'PartFluid_1000.vtk');need(np.array_equal(a,b),'Actual initial/PRE material IDs differ')
    before.extend(stat(PREVTK/leaf) for leaf in ('PartFluid_0000.vtk','PartFluid_1000.vtk'));cohort={'top':a[initial[:,2]==initial[:,2].max()],'bottom':a[initial[:,2]==initial[:,2].min()]};rows=[]
    for name,ids in cohort.items():
        need(len(ids)>0,'Empty original material cohort')
        for identity in ids:
            k=int(np.searchsorted(b,identity));rows.append(dict(layer=name,native_ID=int(identity),initial_z_VTK_m=float(initial[k,2]),PRE_z_VTK_m=float(pre[k,2]),initial_storage=itype,PRE_storage=ptype))
    return cohort,b,pre,rows,itype,ptype

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read before one derived review');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial products protected')
    sets,before=sealed();cohort,preids,pre,material,itype,ptype=layers(before);history=[];tracks=[];matched=[]
    for model,bundle in sets.items():
        data,d,clocks,hist=bundle;rows=prior.summarize(model,bundle,[]);ids=data[0]['Idp'][:,0];slots={name:np.searchsorted(ids,v) for name,v in cohort.items()};ref={name:pre[np.searchsorted(preids,v),2] for name,v in cohort.items()}
        gaps=list(csv.DictReader(((NEW if model=='AS1' else OLD)/'plane_gaps.csv').open(encoding='utf-8')));need(len(gaps)==len(data),'Original gap coverage differs')
        for part,x in enumerate(data):
            for name in cohort:need(np.array_equal(ids[slots[name]],cohort[name]),'Material cohort IDs missing');rows[part][name+'_settlement_PRE_VTK_mm']=float(np.mean(ref[name]-x['Posd'][slots[name],2])*1000)
            gap=gaps[part];need(float(gap['time_s'])==rows[part]['time_s'] and int(gap['completed_step'])==rows[part]['completed_step'] and float(gap['min_soil_x_m'])==rows[part]['min_x_m'] and float(gap['min_soil_z_m'])==rows[part]['min_z_m'] and float(gap['geometry_tolerance_m'])==w.TOL,'Actual gap observations differ')
            sk,si=w.total(x)
            for identity in TRACK:
                k=int(np.searchsorted(ids,identity));need(ids[k]==identity,'Tracked native material ID absent');v=x['Vel'][k].astype(float);s=x['SigmaState_kk'][k];off=x['SigmaState_ij'][k]
                row=dict(model=model,part=part,time_s=float(x['time']),tau_s=float(x['time'])-d['source_actual_time_s'],completed_step=int(clocks[part]['completed_step']),native_ID=identity,x_m=float(x['Posd'][k,0]),z_m=float(x['Posd'][k,2]),vx_m_s=float(v[0]),vy_m_s=float(v[1]),vz_m_s=float(v[2]),speed_m_s=float(np.linalg.norm(v)),FSType=int(x['FSType'][k,0]))
                for key,field in (('p_Pa','PorePress'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k_m_s','PoroHydraulicConductivity')):row[key]=float(x[field][k,0])
                for c,name in enumerate(prior.COMPONENTS):row['sigmaeff_'+name+'_Pa']=float(np.r_[s,off][c]);row['total_sigma_'+name+'_Pa']=float(np.r_[sk[k],si[k]][c])
                tracks.append(row)
        history.extend(rows)
    new,old=sets['AS1'],sets['AS0'];by_step={int(q['completed_step']):i for i,q in enumerate(new[2])};need(len(by_step)==len(new[0]),'Duplicate actual AS1 saved Step')
    for j,y in enumerate(old[0]):
        step=int(old[2][j]['completed_step']);need(step in by_step,'Original common saved Step absent');i=by_step[step];x=new[0][i];need(abs(float(x['time'])-float(y['time']))<=1e-14 and np.array_equal(x['Idp'],y['Idp']),'Actual paired time/IDs differ; no interpolation')
        soil=x['Idp'][:,0]>=2060;dp=x['PorePress'][soil].astype(float)-y['PorePress'][soil].astype(float);du=(x['Posd'][soil]-y['Posd'][soil])*1000;xs,xt=w.total(x);ys,yt=w.total(y);ds=xs[soil]-ys[soil];dt=xt[soil]-yt[soil]
        row=dict(completed_step=step,old_part=j,new_part=i,old_time_s=float(y['time']),new_time_s=float(x['time']),tau_s=float(x['time'])-new[1]['source_actual_time_s'],pressure_RMS_difference_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZmax_difference_mm=float(np.abs(du).max()),total_stress_Frobenius_RMS_difference_Pa=float(np.sqrt(np.mean(np.sum(ds*ds,axis=1)+2*np.sum(dt*dt,axis=1)))))
        for key,field in (('velocity','Vel'),('kappa','Kplastic'),('J','PoroVolumeRatio'),('n','PoroPorosity'),('rho','PoroMixtureDensity'),('k','PoroHydraulicConductivity')):row[key+'_max_abs_difference']=float(np.max(np.abs(x[field][soil].astype(float)-y[field][soil].astype(float))))
        matched.append(row)
    need(len(matched)==54,'All54 actual common states required');files=[csvout('history',history),csvout('material_tracks',tracks),csvout('matched54',matched),csvout('material_layers',material)]
    plt.rcParams.update({'font.size':8,'figure.dpi':160});fig,axs=plt.subplots(4,3,figsize=(16,13),layout='constrained')
    specs=[('p_RMS_Pa','Absolute pressure RMS [kPa]',.001),('p_min_Pa','Minimum absolute pressure [kPa]',.001),('p_max_Pa','Maximum absolute pressure [kPa]',.001),('top_settlement_PRE_VTK_mm','Fixed initial top settlement [mm]',1),('bottom_settlement_PRE_VTK_mm','Fixed initial bottom settlement [mm]',1),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS [kPa]',.001),('speed_RMS_m_s','Speed RMS [m/s]',1),('speed_max_m_s','Maximum speed [m/s]',1),('kappa_max','Maximum plastic history',1)]
    for ax,(key,title,scale) in zip(axs.flat,specs):
        for model,style,color in (('AS0','--','.45'),('AS1','-','C0')):
            rr=[r for r in history if r['model']==model];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,c=color,label=model)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for ax,key,title in zip(axs.flat[9:],('J','n','k'),('Native J range','Native porosity range','Native conductivity range [m/s]')):
        for model,style in (('AS0','--'),('AS1','-')):
            rr=[r for r in history if r['model']==model]
            for suffix,color in (('min','C0'),('max','C1')):ax.plot([r['tau_s'] for r in rr],[r[key+'_'+suffix] for r in rr],style,c=color,label=model+' '+suffix)
        ax.set(title=title,xlabel='Actual time since PRE [s]')
    for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=7)
    fig.suptitle('AS1 normal bounded60 versus AS0 failed-prefix54; PRE VTK float layer references, no theory/half gate');path=Path(str(PREFIX)+'_history.png');fig.savefig(path);plt.close(fig);files.append(path)
    fig,axs=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,identity in zip(axs.flat,TRACK):
        for model,style,color in (('AS0','--','.45'),('AS1','-','C0')):
            rr=[r for r in tracks if r['model']==model and r['native_ID']==identity];ax.plot([r['tau_s'] for r in rr],[r['p_Pa']*.001 for r in rr],style,c=color,label=model)
        ax.set(title='Fixed material'+str(identity),xlabel='Actual time since PRE [s]',ylabel='Native absolute p [kPa]');ax.grid(alpha=.25);ax.legend()
    path=Path(str(PREFIX)+'_material_pressure.png');fig.savefig(path);plt.close(fig);files.append(path)
    for field,label,cmap,scale in (('PorePress','Native absolute p [kPa]','RdBu_r',.001),('Kplastic','Native plastic history','viridis',1)):
        low=min(float(b[0][field][:,1800:,0].min()) for b in sets.values())*scale;high=max(float(b[0][field][:,1800:,0].max()) for b in sets.values())*scale;fig,axs=plt.subplots(2,len(STEPS),figsize=(18,7),layout='constrained',sharex=True,sharey=True);points=[];mappable=None
        for rindex,(model,(data,done,clock,h)) in enumerate(sets.items()):
            for col,step in enumerate(STEPS):
                ax=axs[rindex,col];hits=[i for i,q in enumerate(clock) if int(q['completed_step'])==step];need(len(hits)<=1,'Duplicate actual scatter Step')
                if not hits:ax.text(.5,.5,'No saved AS0 state\nNo interpolation',ha='center',va='center',transform=ax.transAxes);ax.set_axis_off();continue
                part=hits[0];x=data[part];soil=x['Idp'][:,0]>=2060;pos=x['Posd'][soil];value=x[field][soil,0].astype(float);tau=float(x['time'])-done['source_actual_time_s'];mappable=ax.scatter(pos[:,0],pos[:,2],c=value*scale,s=2,cmap=cmap,vmin=low,vmax=high,linewidths=0);ax.set(title=model+' tau='+format(tau,'.6f'),xlabel='x [m]',ylabel='z [m]',aspect='equal');ax.axhline(0,c='black',lw=.5);ax.axvline(0,c='black',lw=.5)
                points.extend(dict(model=model,part=part,time_s=float(x['time']),tau_s=tau,completed_step=step,native_ID=int(identity),x_m=float(q[0]),z_m=float(q[2]),**{field:float(v)}) for identity,q,v in zip(x['Idp'][soil,0],pos,value))
        fig.colorbar(mappable,ax=axs.ravel().tolist(),label=label,shrink=.7);fig.suptitle('All5000 raw points; one complete shared field range, no smoothing/clipping/interpolation');path=Path(str(PREFIX)+'_morph_'+field+'.png');fig.savefig(path);plt.close(fig);files.extend((path,csvout('morph_'+field,points)))
    need(all(stat(Path(e['path']))==e for e in before),'Consumed sealed native/reference changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,AS1_frames=60,AS0_saved_prefix_frames=54,actual_common_pairs=54,AS0_runtime_success_claimed=False,AS1_bounded_runtime_closed_not_physical_acceptance=True,NoPen_policy='FixedPlaneStageProjectionReleaseOnly',AS1_policy='ReleaseOnly',reaction_J_Darcy_closed=False,fixed_initial_top_IDs=cohort['top'].tolist(),fixed_initial_bottom_IDs=cohort['bottom'].tolist(),initial_VTK_storage=itype,PRE_VTK_storage=ptype,layer_baseline='Actual source PartFluid0000 fixed IDs; PartFluid1000 PRE coordinates retain their float rounding; post positions double',whole_soil_mean_settlement_baseline='Original native history double PRE',no_interpolation_smoothing_clipping_fitting=True,no_new_5Pa_or_half_or_theory_gate=True,option_difference_is_descriptive=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,consumed=before,files=[stat(q) for q in files])
    with Path(str(PREFIX)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('AS_WINDOW_OFFLINE_REVIEW_COMPLETED',str(PREFIX)+'.check.json',flush=True)

if __name__=='__main__':main()
