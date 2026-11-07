"""Author-only once-off offline plots of two eleven-frame AS option trajectories; no native tools."""
import argparse,csv,json,re,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_as_effect_r1';PREFIX=T/'figures'/TAG
SOURCES={'OFF':T/'outputs/upl_c08_as_short_r1_off_native','ON':T/'outputs/upl_c08_as_on_partial_r1'}
CHECKS={'OFF':T/'logs/upl_c08_as_short_r1_off.native.check.json','ON':T/'logs/upl_c08_as_on_partial_r1.check.json'}
PREVTK=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/particles'

def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def stat(p):
    q=p.resolve();s=q.stat();return dict(path=str(q),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def csvout(leaf,rows):
    p=Path(str(PREFIX)+'_'+leaf+'.csv')
    with p.open('x',encoding='utf8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return p

def vtk_positions(p):
    # Only read existing legacy binary Idp/POINTS, not reconstructing PRE from a post frame.
    b=p.read_bytes();m=re.search(rb'(?m)^POINTS (\d+) (float|double)\r?\n',b);need(m is not None and b'\nBINARY\n' in b[:100],'Actual binary legacy VTK POINTS required');n=int(m[1]);dtype='>f4' if m[2]==b'float' else '>f8';x=np.frombuffer(b,dtype=dtype,count=n*3,offset=m.end()).reshape(n,3).astype('float64')
    ids=re.search(rb'(?m)^SCALARS Idp unsigned_int(?: 1)?\r?\nLOOKUP_TABLE default\r?\n',b);need(ids is not None,'Actual VTK Idp field required');idp=np.frombuffer(b,dtype='>u4',count=n,offset=ids.end()).astype('uint32');order=np.argsort(idp);need(n==5000 and np.array_equal(idp[order],np.arange(2060,7060)),'Actual VTK soil material IDs differ');return idp[order],x[order],m[2].decode()

def load(folder):
    d=read(folder/'completion.json');need(d['passed'] and d['samples']==11 and d['typed_arrays']==22 and d['completed_steps']==4044000,'Closed eleven-state native completion required')
    specs=list(csv.DictReader((folder/'typed22_layout.csv').open(encoding='utf8')));need(len(specs)==22,'Original22 typed layout required');dtype=[]
    for v in specs:
        base={'uint32':'<u4','float32':'<f4','float64':'<f8'}[v['type']];width=int(v['components']);need(np.dtype(base).itemsize*width==int(v['bytes_per_particle']),'Typed layout byte width differs');dtype.append((v['array'],base,(6800,width)))
    record=np.dtype([('time','<f8'),*dtype]);need(record.itemsize==8+6800*212,'Native record stride differs')
    with (folder/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6800,22,11),'Actual header differs; no rewrite')
    need((folder/'typed22.bin').stat().st_size==12+11*record.itemsize,'Actual native file length differs');a=np.memmap(folder/'typed22.bin',dtype=record,offset=12,mode='r',shape=(11,));clocks=list(csv.DictReader((folder/'clocks.csv').open(encoding='utf8')));history=list(csv.DictReader((folder/'history.csv').open(encoding='utf8')));need(len(clocks)==len(history)==11,'Actual native history/clock coverage differs')
    ids=a[0]['Idp'][:,0];need(np.array_equal(ids,np.r_[np.arange(1800),np.arange(2060,7060)]) and all(np.array_equal(q['Idp'][:,0],ids) for q in a),'Actual per-frame material IDs differ')
    for i,q in enumerate(a):need(float(clocks[i]['time_s'])==q['time'] and int(clocks[i]['completed_step'])==int(clocks[i]['saved_step'])+1 and float(clocks[i]['signed_dterror_s'])<=1e-14,'Original actual clock/signed metadata differs')
    return a,d,clocks,history

def draw(axes,rows,key,label,title,scales=None):
    for mode,style in [('OFF','-'),('ON','--')]:
        r=[x for x in rows if x['AS']==mode];axes.plot([x['tau_s'] for x in r],[x[key]*(scales or 1) for x in r],style,label=mode,lw=1.8,marker='o',ms=3)
    axes.set(title=title,xlabel='Actual time since PRE release [s]',ylabel=label);axes.grid(alpha=.25);axes.legend(fontsize=8)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full review before one offline plot execution');need(not list(PREFIX.parent.glob(TAG+'*')),'Existing partial/complete plot products protected; no overwrite')
    consumed=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md'))];data={};overview=[];point=[];walls=[];materials=[]
    initialids,initial,itype=vtk_positions(PREVTK/'PartFluid_0000.vtk');preids,pre,ptype=vtk_positions(PREVTK/'PartFluid_1000.vtk');need(np.array_equal(initialids,preids),'Initial/PRE actual ID identity differs');bottom=initialids[initial[:,2]==initial[:,2].min()];top=initialids[initial[:,2]==initial[:,2].max()];need(len(bottom)>0 and len(top)>0,'Fixed initial material layers empty')
    consumed += [stat(PREVTK/'PartFluid_0000.vtk'),stat(PREVTK/'PartFluid_1000.vtk')]
    for layer,ids in [('bottom',bottom),('top',top)]:
        for idp in ids:
            j=int(np.searchsorted(preids,idp));materials.append(dict(layer=layer,native_ID=int(idp),initial_z_from_VTK_m=initial[j,2],PRE_z_from_VTK_m=pre[j,2],initial_VTK_storage=itype,PRE_VTK_storage=ptype))
    for mode,folder in SOURCES.items():
        ck=read(CHECKS[mode]);need(ck['passed'],'Native check did not pass: '+mode);q,d,clocks,history=load(folder);data[mode]=(q,d);consumed += [stat(CHECKS[mode]),*[stat(folder/x) for x in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv','history.csv')]]
        idlist=q[0]['Idp'][:,0];soil=idlist>=2060;topidx=np.searchsorted(idlist,top);botidx=np.searchsorted(idlist,bottom);pretop=pre[np.searchsorted(preids,top),2];prebot=pre[np.searchsorted(preids,bottom),2];i7010=int(np.searchsorted(idlist,7010));need(idlist[i7010]==7010,'Tracked material7010 missing')
        for part,x in enumerate(q):
            tau=float(x['time'])-d['source_actual_time_s'];pos=x['Posd'];v=x['Vel'].astype('float64');p=x['PorePress'][:,0].astype('float64');sk=x['SigmaState_kk'];si=x['SigmaState_ij'];speed=np.sqrt(np.sum(v*v,axis=1));total=sk-p[:,None];frob=np.sum(total*total,axis=1)+2*np.sum(si*si,axis=1)
            overview.append(dict(AS=mode,part=part,time_s=float(x['time']),tau_s=tau,completed_step=int(clocks[part]['completed_step']),soil_z_below_zero_count=int(np.count_nonzero(pos[soil,2]<0)),soil_min_z_m=float(pos[soil,2].min()),p_RMS_Pa=float(np.sqrt(np.mean(p[soil]*p[soil]))),p_mean_Pa=float(p[soil].mean()),p_min_Pa=float(p[soil].min()),p_max_Pa=float(p[soil].max()),top_downward_settlement_PRE_VTK_mm=float(np.mean(pretop-pos[topidx,2])*1000),bottom_downward_settlement_PRE_VTK_mm=float(np.mean(prebot-pos[botidx,2])*1000),all_soil_mean_downward_settlement_native_PRE_mm=-1000*float(history[part]['mean_dz_from_PRE_m']),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob[soil]))),speed_RMS_m_s=float(np.sqrt(np.mean(speed[soil]*speed[soil]))),speed_max_m_s=float(speed[soil].max()),J_min=float(x['PoroVolumeRatio'][soil].min()),J_max=float(x['PoroVolumeRatio'][soil].max()),kappa_max=float(x['Kplastic'][soil].max()),signed_dterror_s=float(clocks[part]['signed_dterror_s'])))
            point.append(dict(AS=mode,part=part,time_s=float(x['time']),tau_s=tau,native_ID=7010,z_m=float(pos[i7010,2]),vx_m_s=v[i7010,0],vy_m_s=v[i7010,1],vz_m_s=v[i7010,2],speed_m_s=speed[i7010],kappa=float(x['Kplastic'][i7010,0]),p_Pa=p[i7010],J=float(x['PoroVolumeRatio'][i7010,0])))
            for idp in (783,787,791):
                k=int(np.searchsorted(idlist,idp));need(idlist[k]==idp,'Tracked wall material missing');walls.append(dict(AS=mode,part=part,time_s=float(x['time']),tau_s=tau,native_ID=idp,z_m=float(pos[k,2]),p_Pa=p[k],effective_zz_Pa=float(sk[k,2]),total_zz_Pa=float(sk[k,2]-p[k])))
    qa,da=data['OFF'];qb,db=data['ON'];need(da['source_actual_time_s']==db['source_actual_time_s'],'Different actual PRE clocks');need(np.max(np.abs(qa['time']-qb['time']))<=1e-14,'Actual option times differ')
    files=[csvout('history',overview),csvout('particle7010',point),csvout('walls',walls),csvout('material_layers',materials)]
    plt.rcParams.update({'font.size':10,'figure.dpi':160})
    fig,ax=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for a,key,label,title,scale in zip(ax.ravel(),['z_m','vz_m_s','speed_m_s','kappa','p_Pa','J'],['z [m]','vz [m/s]','Speed [m/s]','Accumulated plastic history','Pore pressure [kPa]','J'],['Material7010: vertical position','Material7010: vertical velocity','Material7010: speed','Material7010: plastic history','Material7010: pressure','Material7010: volume ratio'],[1,1,1,1,.001,1]):draw(a,point,key,label,title,scale)
    fig.suptitle('C08 AS OFF/ON: fixed material7010, actual saved states only');p=Path(str(PREFIX)+'_particle7010.png');fig.savefig(p);plt.close(fig);files.append(p)
    fig,ax=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    draw(ax[0,0],overview,'soil_z_below_zero_count','Number of soil IDs','Geometric count z < 0 (not a new guard)');draw(ax[0,1],overview,'p_RMS_Pa','Pressure RMS [kPa]','All5000 soil: native absolute pressure',.001)
    for mode,style in [('OFF','-'),('ON','--')]:
        rr=[x for x in overview if x['AS']==mode]
        for name,color in [('top','C0'),('bottom','C1')]:ax[0,2].plot([x['tau_s'] for x in rr],[x[name+'_downward_settlement_PRE_VTK_mm'] for x in rr],style,color=color,label=mode+' '+name)
    ax[0,2].set(title='Fixed initial material layers (PRE VTK float reference)',xlabel='Actual time since PRE release [s]',ylabel='Downward settlement [mm]');ax[0,2].grid(alpha=.25);ax[0,2].legend(fontsize=8)
    draw(ax[1,0],overview,'total_stress_Frobenius_RMS_Pa','Total stress RMS [kPa]','All5000 soil: sigma_eff - p I',.001);draw(ax[1,1],overview,'speed_RMS_m_s','Speed RMS [m/s]','All5000 soil: velocity');draw(ax[1,2],overview,'J_min','Minimum J','All5000 soil: saturation-domain response')
    fig.suptitle('C08 AS option effects:11 saved states; OFF bounded exit0 / ON later failed');p=Path(str(PREFIX)+'_history.png');fig.savefig(p);plt.close(fig);files.append(p)
    fig,ax=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for j,idp in enumerate((783,787,791)):
        rr=[x for x in walls if x['native_ID']==idp];draw(ax[0,j],rr,'total_zz_Pa','Total zz stress [kPa]','Fixed wall'+str(idp)+': sigma_eff,zz - p',.001);draw(ax[1,j],rr,'p_Pa','Native pore pressure [kPa]','Fixed wall'+str(idp)+': original p field',.001)
    fig.suptitle('C08 wall state: real saved fields, not unsaved failure-stage reconstructions');p=Path(str(PREFIX)+'_walls.png');fig.savefig(p);plt.close(fig);files.append(p)
    need(all(stat(Path(e['path']))==e for e in consumed),'Consumed native/reference files changed')
    check=dict(stage=TAG,passed=True,offline_only=True,solver_invocations=0,reader_invocations=0,actual_pairs=11,soil_IDs=5000,top_material_IDs=[int(i) for i in top],bottom_material_IDs=[int(i) for i in bottom],initial_layer_definition='Source PartFluid0000 VTK extreme z; fixed IDs tracked thereafter.',layer_settlement_reference='Actual source PartFluid1000 VTK coordinates; float storage introduces baseline rounding.',initial_VTK_storage=itype,PRE_VTK_storage=ptype,all_soil_mean_settlement_reference='Reader history uses actual double PRE coordinates.',total_stress_definition='SigmaState_kk - native absolute PorePress I',z_below_zero_is_geometric_description_not_a_gate=True,option_comparison_is_not_half_or_theory_error=True,ON_solver_failure_not_relabelled_success=True,OFF_is_bounded_completed_not_full_acceptance=True,no_interpolation_or_filtering=True,physical_acceptance=False,consumed=consumed,files=[stat(p) for p in files])
    out=Path(str(PREFIX)+'.check.json')
    with out.open('x',encoding='utf8') as f:json.dump(check,f,indent=2);f.write('\n')
    print('OFFLINE_AS_EFFECT_PLOTS_READY',out,flush=True)
if __name__=='__main__':main()
