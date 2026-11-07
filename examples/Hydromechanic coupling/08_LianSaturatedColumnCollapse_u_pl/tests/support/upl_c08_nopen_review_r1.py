"""Offline saved-state NoPen diagnostic versus the retained ASoff prefix; no native tool calls."""
import argparse,csv,json,os,struct
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from upl_c08_as_effect_r1 import vtk_positions,need,read,stat
from upl_c08_fsmask_r1 import SCHEMA,TYPES
T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_nopen_review_r1';PREFIX=T/'figures'/TAG
SOURCES={'OFF':T/'outputs/upl_c08_as_short_r1_off_native','NoPen':T/'outputs/upl_c08_nopen_native_r1'}
CHECKS={'OFF':T/'logs/upl_c08_as_short_r1_off.native.check.json','NoPen':T/'logs/upl_c08_nopen_native_r1.check.json'}
PREVTK=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/particles'
ROI=(3.5,4.5,-.16,.24);SELECTED=(8,10,14) # Actual saved tau about .09/.11/.15; no interpolation.

def load(folder,samples,steps):
    done=read(folder/'completion.json');need(done['passed'] and done['samples']==samples and done['typed_arrays']==22 and done['completed_steps']==steps,'Closed matching native completion required')
    with (folder/'typed22_layout.csv').open(encoding='utf-8',newline='') as f:layout=list(csv.DictReader(f))
    need(len(layout)==22,'All22 typed arrays required');fields=[]
    for row,(name,kind,nc) in zip(layout,SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,TYPES[kind].itemsize*nc),'Original typed layout differs');fields.append((name,TYPES[kind],(6800,nc)))
    dtype=np.dtype([('time','<f8'),*fields]);need(dtype.itemsize==8+6800*212,'Native record stride differs')
    with (folder/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6800,22,samples),'Original actual native header differs')
    need((folder/'typed22.bin').stat().st_size==12+samples*dtype.itemsize,'Native file truncated or extra records present');raw=np.memmap(folder/'typed22.bin',mode='r',dtype=dtype,offset=12,shape=(samples,))
    with (folder/'clocks.csv').open(encoding='utf-8',newline='') as f:clocks=list(csv.DictReader(f))
    with (folder/'history.csv').open(encoding='utf-8',newline='') as f:history=list(csv.DictReader(f))
    need(len(clocks)==len(history)==samples,'Full original clock/history coverage required');ids=np.r_[np.arange(1800),np.arange(2060,7060)]
    for part,(frame,clock,hist) in enumerate(zip(raw,clocks,history)):
        need(np.array_equal(frame['Idp'][:,0],ids),'Material ID registry/order differs')
        need(int(clock['part'])==int(hist['part'])==part and int(clock['completed_step'])==4004000+4000*part and int(clock['saved_step'])+1==int(clock['completed_step']),'Actual global saved Step differs')
        need(float(clock['time_s'])==float(hist['time_s'])==frame['time'] and clock['dterror_interval_empty']=='0' and float(clock['signed_dterror_s'])<=1e-14,'Actual saved time/signed necessary-step diagnostic differs')
    return raw,done,clocks,history

def csvout(leaf,rows):
    p=Path(str(PREFIX)+'_'+leaf+'.csv')
    with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return p

def draw(ax,rows,key,label,title,scale=1):
    for mode,style,color in (('OFF','--','C0'),('NoPen','-','C1')):
        rr=[r for r in rows if r['mode']==mode];ax.plot([r['tau_s'] for r in rr],[r[key]*scale for r in rr],style,color=color,marker='o',ms=3,lw=1.6,label=mode)
    ax.set(xlabel='Actual time since release [s]',ylabel=label,title=title);ax.grid(alpha=.25);ax.legend(fontsize=8)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full review before one offline execution');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial derived outputs protected')
    consumed=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md')),stat(T/'support/upl_c08_as_effect_r1.py'),stat(T/'support/upl_c08_fsmask_r1.py')]
    initialids,initial,itype=vtk_positions(PREVTK/'PartFluid_0000.vtk');preids,pre,ptype=vtk_positions(PREVTK/'PartFluid_1000.vtk');need(np.array_equal(initialids,preids),'Initial/PRE VTK material IDs differ')
    top=initialids[initial[:,2]==initial[:,2].max()];bottom=initialids[initial[:,2]==initial[:,2].min()];need(len(top)>0 and len(bottom)>0,'Fixed initial material layers must be nonempty')
    consumed += [stat(PREVTK/'PartFluid_0000.vtk'),stat(PREVTK/'PartFluid_1000.vtk')];materials=[]
    for layer,ids in (('top',top),('bottom',bottom)):
        for nativeid in ids:
            i=int(np.searchsorted(preids,nativeid));materials.append(dict(layer=layer,native_ID=int(nativeid),initial_z_VTK_m=float(initial[i,2]),PRE_z_VTK_m=float(pre[i,2]),initial_storage=itype,PRE_storage=ptype))
    datasets={};overview=[];point=[];local=[];panels={}
    for mode,folder in SOURCES.items():
        check=read(CHECKS[mode]);need(check['passed'],'Actual native check did not pass')
        if mode=='NoPen':need(check['original_native_guards_passed'] and check['consumed_stats_unchanged'],'Original NoPen native guards/bindings did not pass')
        n=11 if mode=='OFF' else 15;raw,done,clocks,history=load(folder,n,4044000 if mode=='OFF' else 4060000);datasets[mode]=(raw,done,clocks)
        consumed += [stat(CHECKS[mode]),*[stat(folder/leaf) for leaf in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv')]]
        ids=raw[0]['Idp'][:,0];soil=ids>=2060;topidx=np.searchsorted(ids,top);bottomidx=np.searchsorted(ids,bottom);i7010=int(np.searchsorted(ids,7010));need(ids[i7010]==7010,'Tracked material7010 missing');pretop=pre[np.searchsorted(preids,top),2];prebottom=pre[np.searchsorted(preids,bottom),2]
        for part,frame in enumerate(raw):
            tau=float(frame['time'])-done['source_actual_time_s'];pos=frame['Posd'];vel=frame['Vel'].astype(float);pressure=frame['PorePress'][:,0].astype(float);j=frame['PoroVolumeRatio'][:,0];kappa=frame['Kplastic'][:,0];speed2=np.sum(vel*vel,axis=1);sk=frame['SigmaState_kk'];si=frame['SigmaState_ij'];total=sk-pressure[:,None];total2=np.sum(total*total,axis=1)+2*np.sum(si*si,axis=1)
            common=dict(mode=mode,part=part,time_s=float(frame['time']),tau_s=tau,completed_step=int(clocks[part]['completed_step']))
            overview.append(dict(**common,soil_IDs=int(soil.sum()),soil_min_z_m=float(pos[soil,2].min()),soil_z_below_zero_count=int((pos[soil,2]<0).sum()),soil_min_x_m=float(pos[soil,0].min()),soil_left_x_below_zero_count=int((pos[soil,0]<0).sum()),p_mean_Pa=float(pressure[soil].mean()),p_RMS_Pa=float(np.sqrt(np.mean(pressure[soil]**2))),p_min_Pa=float(pressure[soil].min()),p_max_Pa=float(pressure[soil].max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(total2[soil].mean())),speed_RMS_m_s=float(np.sqrt(speed2[soil].mean())),max_speed_m_s=float(np.sqrt(speed2[soil].max())),kappa_max=float(kappa[soil].max()),kappa_nonzero_IDs=int((kappa[soil]>0).sum()),J_min=float(j[soil].min()),J_max=float(j[soil].max()),top_downward_settlement_PRE_VTK_mm=1000*float(np.mean(pretop-pos[topidx,2])),bottom_downward_settlement_PRE_VTK_mm=1000*float(np.mean(prebottom-pos[bottomidx,2])),all_soil_mean_downward_settlement_native_PRE_mm=-1000*float(history[part]['mean_dz_from_PRE_m']),signed_dterror_s=float(clocks[part]['signed_dterror_s'])))
            point.append(dict(**common,native_ID=7010,x_m=float(pos[i7010,0]),y_m=float(pos[i7010,1]),z_m=float(pos[i7010,2]),vx_m_s=float(vel[i7010,0]),vy_m_s=float(vel[i7010,1]),vz_m_s=float(vel[i7010,2]),speed_m_s=float(np.sqrt(speed2[i7010])),kappa=float(kappa[i7010]),p_Pa=float(pressure[i7010]),J=float(j[i7010]),total_sigma_zz_Pa=float(total[i7010,2])))
            if part in SELECTED:
                roi=(pos[:,0]>=ROI[0])&(pos[:,0]<=ROI[1])&(pos[:,2]>=ROI[2])&(pos[:,2]<=ROI[3]);selected=np.flatnonzero(roi);panels[mode,part]=(pos[selected].copy(),ids[selected].copy(),kappa[selected].copy(),tau,pos[i7010].copy());keep=sorted(set(selected.tolist())|{i7010})
                for q in keep:local.append(dict(**common,native_ID=int(ids[q]),is_fixed=bool(ids[q]<2060),selected_by_ROI=bool(roi[q]),x_m=float(pos[q,0]),y_m=float(pos[q,1]),z_m=float(pos[q,2]),vx_m_s=float(vel[q,0]),vy_m_s=float(vel[q,1]),vz_m_s=float(vel[q,2]),p_Pa=float(pressure[q]),total_sigma_zz_Pa=float(total[q,2]),kappa=float(kappa[q]),J=float(j[q]),FSType=int(frame['FSType'][q,0])))
    off,do,oc=datasets['OFF'];nop,dn,nc=datasets['NoPen'];need(do['source_actual_time_s']==dn['source_actual_time_s'] and np.max(np.abs(off['time']-nop['time'][:11]))<=1e-14,'Actual matched prefix clocks/PRE differ')
    prefix=[]
    for i in range(11):prefix.append(dict(part=i,OFF_time_s=float(off[i]['time']),NoPen_time_s=float(nop[i]['time']),raw_time_plus22_record_byte_equal=off[i].tobytes()==nop[i].tobytes(),array_payload_byte_equal_count=sum(off[i][name].tobytes()==nop[i][name].tobytes() for name,kind,width in SCHEMA),array_payload_count=22,signed_dterror_original_text_equal=oc[i]['signed_dterror_s']==nc[i]['signed_dterror_s']))
    need(len(overview)==len(point)==26 and len(panels)==5,'Incomplete actual history/selected snapshot coverage');files=[csvout('history',overview),csvout('particle7010',point),csvout('material_layers',materials),csvout('local_bed',local),csvout('prefix_comparison',prefix)]
    plt.rcParams.update({'font.size':10,'figure.dpi':160});fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,key,label,title,scale in zip(axes.flat,('z_m','vz_m_s','kappa','p_Pa','J','speed_m_s'),('z [m]','vz [m/s]','Accumulated history','Pore pressure [kPa]','J','Speed [m/s]'),('Material7010: vertical position','Material7010: vertical velocity','Material7010: plastic history','Material7010: absolute pressure','Material7010: volume ratio','Material7010: speed'),(1,1,1,.001,1,1)):draw(ax,point,key,label,title,scale)
    axes[0,0].axhline(0,color='k',lw=.7);fig.suptitle('C08 legacy NoPen diagnostic: fixed material7010; projection scratch not exported');p=Path(str(PREFIX)+'_particle7010.png');fig.savefig(p);plt.close(fig);files.append(p)
    fig,axes=plt.subplots(3,3,figsize=(15,11),layout='constrained')
    for ax,key,label,title,scale in zip(list(axes.flat)[:8],('soil_min_z_m','soil_z_below_zero_count','soil_left_x_below_zero_count','p_RMS_Pa','total_stress_Frobenius_RMS_Pa','speed_RMS_m_s','kappa_max','J_min'),('z [m]','Soil IDs','Soil IDs','Pressure RMS [kPa]','Total stress RMS [kPa]','Speed RMS [m/s]','Maximum history','Minimum J'),('Minimum soil z','Saved z < 0: geometric count','Saved x < 0: geometric count','All5000: absolute pore pressure','All5000: sigma_eff - p I','All5000: speed','All5000: kappa','All5000: current J'),(1,1,1,.001,.001,1,1,1)):draw(ax,overview,key,label,title,scale)
    for mode,style in (('OFF','--'),('NoPen','-')):
        rr=[r for r in overview if r['mode']==mode]
        for layer,color in (('top','C0'),('bottom','C1')):axes[2,2].plot([r['tau_s'] for r in rr],[r[layer+'_downward_settlement_PRE_VTK_mm'] for r in rr],style,color=color,label=mode+' '+layer)
    axes[2,2].set(xlabel='Actual time since release [s]',ylabel='Downward settlement [mm]',title='Fixed initial layers: PRE VTK float baseline');axes[2,2].grid(alpha=.25);axes[2,2].legend(fontsize=8);fig.suptitle('C08 NoPen saved-state observation; OFF stops at tau .11, no extension or acceptance gate');p=Path(str(PREFIX)+'_history.png');fig.savefig(p);plt.close(fig);files.append(p)
    vmax=max(1e-12,max(float(v[2][v[1]>=2060].max()) if np.any(v[1]>=2060) else 0. for v in panels.values()));norm=Normalize(0,vmax);fig,axes=plt.subplots(2,3,figsize=(15,6.8),layout='constrained');artist=None
    for row,mode in enumerate(('OFF','NoPen')):
        for col,part in enumerate(SELECTED):
            ax=axes[row,col];ax.set(xlim=ROI[:2],ylim=ROI[2:],xlabel='Native x [m]',ylabel='Native z [m]',aspect='equal');ax.axhline(0,color='k',lw=.8);ax.grid(alpha=.15)
            if (mode,part) not in panels:ax.text(.5,.5,'No OFF state at tau .15\n(no extrapolation)',transform=ax.transAxes,ha='center');ax.set_title(mode+' / unavailable');continue
            pos,ids,kap,tau,tracked=panels[mode,part];wall=ids<2060;ax.scatter(pos[wall,0],pos[wall,2],s=12,c='.6',marker='s',label='Fixed quadrature')
            artist=ax.scatter(pos[~wall,0],pos[~wall,2],s=16,c=kap[~wall],norm=norm,cmap='viridis',label='Soil');inside=ROI[0]<=tracked[0]<=ROI[1] and ROI[2]<=tracked[2]<=ROI[3]
            if inside:ax.scatter([tracked[0]],[tracked[2]],s=55,facecolors='none',edgecolors='red',marker='D',linewidths=1.2,label='ID7010')
            else:ax.text(.02,.02,'ID7010 outside fixed window',transform=ax.transAxes,fontsize=8)
            ax.set_title(mode+' / actual tau %.9f s'%tau)
    if artist is not None:fig.colorbar(artist,ax=axes.ravel().tolist(),label='Native scalar Kplastic (not plastic-strain tensor)',shrink=.8)
    axes[0,0].legend(fontsize=7);fig.suptitle('Saved local bottom region: native double positions; separate soil/fixed IDs');p=Path(str(PREFIX)+'_local_bed.png');fig.savefig(p);plt.close(fig);files.append(p)
    need(all(stat(Path(e['path']))==e for e in consumed),'Consumed native/reference data changed');check=dict(stage=TAG,passed=True,offline_only=True,frames={'OFF':11,'NoPen':15},actual_matched_prefix=11,prefix_comparison_is_descriptive_not_gate=True,prefix_comparison=prefix,actual_native_headers_preserved_11_and15=True,soil_IDs=5000,tracked_native_ID=7010,top_initial_material_IDs=top.tolist(),bottom_initial_material_IDs=bottom.tolist(),initial_VTK_storage=itype,PRE_VTK_storage=ptype,layer_baseline='PartFluid0000 selects fixed IDs; PartFluid1000 gives PRE float coordinates, with rounding; post positions are native double.',all_soil_mean_settlement_baseline='Original native reader history uses double PRE coordinates.',AS_off_qualified_by_original_run_native_checks_not_inferred_from_arrays=True,arithmetic_soil_statistics_not_volume_weighted=True,NoPen_scratch_or_trigger_counts_exported=False,reaction_J_Darcy_closure_claimed=False,geometric_zero_plane_counts_are_not_acceptance_gates=True,local_ROI=list(ROI),local_selected_parts=list(SELECTED),OFF_tau15_unavailable=True,no_interpolation_or_smoothing=True,no_5Pa_or_half_gate=True,automatic_full_or_solver_started=False,physical_acceptance=False,solver_invocations=0,reader_invocations=0,build_invocations=0,SHA_scans=0,consumed=consumed,files=[stat(p) for p in files])
    with Path(str(PREFIX)+'.check.json').open('x',encoding='utf-8') as f:json.dump(check,f,indent=2);f.write('\n')
    print('OFFLINE_NOPEN_REVIEW_READY',str(PREFIX)+'.check.json',flush=True)

if __name__=='__main__':main()
