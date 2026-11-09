"""Offline six-call interpretation; no state updates or BI4 reader."""
import csv,json,struct
from pathlib import Path
import upl_c08_as05_compare_r1 as c
from matplotlib.colors import SymLogNorm,Normalize
np,plt=c.np,c.plt
T=c.T;TAG='upl_c08_rvisc_failure_rhs_review_r1';P=T/'figures'/TAG

def write(leaf,rows):
    path=Path(str(P)+'_'+leaf+'.csv')
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return path

def main():
    check=T/'logs'/(TAG+'.check.json')
    c.need(not check.exists() and not list(P.parent.glob(TAG+'_*')),'Existing analysis protected')
    receipt=T/'logs/upl_c08_rvisc_failure_rhs_r2.check.json';r=c.read(receipt)
    c.need(r['passed'] and r['force_evaluations']==r['Darcy_evaluations']==6 and r['actual_physical_steps']==0 and r['retained_part13_alignment']['mismatched_fields']==0,'Closed zero-time RHS component required')
    before=[c.stat(__file__),c.stat(receipt),c.stat(c.__file__),c.stat(T/'notes'/(TAG+'.md'))]+[c.bind(x) for x in r['files']]
    root=Path(r['component_completion']['path']).parent;rows=c.table(root/'soil_force.csv');meters=c.table(root/'damping.csv');calls=c.table(root/'calls.csv')
    c.need(len(rows)==30000 and len(meters)==len(calls)==6,'Actual six-call output required')
    arrays={};native_paths={}
    for label,key,count in [('baseline',r['source_native'],90),('candidate',r['candidate_partial_native'],53)]:
        before.append(c.bind(key));n=c.read(key['path']);folder=Path(c.bind(n['completion'])['path']).parent
        for leaf in ('typed22.bin','typed22_layout.csv'):
            before.append(c.bind(next(x for x in n['outputs'] if Path(x['path']).samefile(folder/leaf))))
        fields=[('time','<f8')]
        for name,kind,width in c.SCHEMA:fields.append((name,c.TYPES[kind],(6805,width)))
        dtype=np.dtype(fields);raw=folder/'typed22.bin'
        with raw.open('rb') as f:c.need(struct.unpack('<III',f.read(12))==(6805,22,count),'Original native header differs')
        c.need(raw.stat().st_size==12+count*dtype.itemsize,'Original payload extent differs')
        arrays[label]=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,));native_paths[label]=str(raw)
    summary=[];focus=[];spatial=[];specs=[('baseline_control','baseline',13),('baseline52','baseline',51),('rvisc52','candidate',51)]
    focus_ids=[7011,7012,6230,6231,5941,5897,5895,5294]
    for index,(label,source,part) in enumerate(specs):
        pair=[sorted([q for q in rows if q['snapshot']==label and q['mode']==mode],key=lambda q:int(q['native_id'])) for mode in ('OFF','ON')]
        c.need(all(len(q)==5000 and [int(x['native_id']) for x in q]==list(range(2060,7060)) for q in pair),'All material IDs required')
        old,new=pair;x=arrays[source][part];ids=x['Idp'][:,0];c.need(np.array_equal(ids,c.EXPECTED),'Actual IDs differ');soil=ids>=2060
        c.need(float(x['time'])==float(old[0]['time_s'])==float(new[0]['time_s']),'Actual clocks differ')
        def column(data,key):return np.array([float(q[key]) for q in data])
        p=x['PorePress'][soil,0].astype(float);n=x['PoroPorosity'][soil,0];volume=x['PoroCurrentVolume'][soil,0];rho=x['PoroMixtureDensity'][soil,0]
        velocity=x['Vel'][soil].astype(float);position=x['Posd'][soil];rate0=column(old,'rate_Pa_s');rate1=column(new,'rate_Pa_s');dr=rate1-rate0
        da=np.column_stack([column(new,'Ace_'+k+'_m_s2')-column(old,'Ace_'+k+'_m_s2') for k in ('x','y','z')]);dan=np.linalg.norm(da,axis=1)
        modulus=column(new,'capacity_Kw_over_n_Pa');compression=column(new,'compression_Pa_s');W=n*volume/1e9
        c.need(np.isfinite(dr).all() and np.isfinite(da).all() and np.array_equal(modulus,1e9/n),'Current source storage coefficient differs')
        at=int(np.argmax(abs(dr)));am=int(np.argmax(dan));meter=meters[2*index+1]
        summary.append(dict(snapshot=label,part=part,time_s=float(x['time']),tau_s=float(old[0]['tau_s']),max_abs_rate_OFF_Pa_s=float(abs(rate0).max()),max_abs_rate_ON_Pa_s=float(abs(rate1).max()),rate_RMS_OFF_Pa_s=float(np.sqrt(np.mean(rate0**2))),rate_RMS_ON_Pa_s=float(np.sqrt(np.mean(rate1**2))),delta_rate_RMS_Pa_s=float(np.sqrt(np.mean(dr**2))),max_abs_delta_rate_Pa_s=float(abs(dr[at])),max_delta_rate_ID=2060+at,max_added_accel_m_s2=float(dan[am]),max_added_accel_ID=2060+am,committed_mechanical_power_W_per_m=float(np.sum(rho*volume*np.sum(velocity*da,axis=1))),meter_committed_mechanical_power_W_per_m=float(meter['committed_work']),conditional_pressure_storage_power_change_W_per_m=float(np.sum(W*p*dr)),raw_compression_RMS_Pa_s=float(np.sqrt(np.mean(compression**2))),positive_p_times_delta_rate_soil_nodes=int(np.count_nonzero(p*dr>0)),max_dt_times_delta_rate_Pa=float(2.5e-6*abs(dr).max()),dt_times_rate_is_not_integrated_prediction=True))
        for ident in focus_ids:
            slot=ident-2060;q=old[slot]
            focus.append(dict(snapshot=label,part=part,time_s=float(x['time']),tau_s=float(q['tau_s']),native_id=ident,x_m=float(position[slot,0]),z_m=float(position[slot,2]),saved_p_Pa=float(p[slot]),saved_J=float(x['PoroVolumeRatio'][soil,0][slot]),recomputed_theta_s_1=float(q['theta_s_1']),raw_compression_Pa_s=float(compression[slot]),actual_rate_OFF_Pa_s=float(rate0[slot]),actual_rate_ON_Pa_s=float(rate1[slot]),delta_rate_Pa_s=float(dr[slot]),p_times_delta_rate_Pa2_s=float(p[slot]*dr[slot]),added_a_x_m_s2=float(da[slot,0]),added_a_z_m_s2=float(da[slot,2]),actual_FS=int(q['actual_FS'])))
        spatial.append(dict(label=label,pos=position.copy(),dr=dr.copy(),dan=dan.copy()))
    files=[write('summary',summary),write('focus',focus)]
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained');peak=max(float(abs(q['dr']).max()) for q in spatial);amax=max(float(q['dan'].max()) for q in spatial)
    norm=SymLogNorm(linthresh=1e6,vmin=-peak,vmax=peak);anorm=Normalize(0,amax)
    for j,q in enumerate(spatial):
        pos=q['pos'];im=axes[0,j].scatter(pos[:,0],pos[:,2],c=q['dr'],s=6,cmap='coolwarm',norm=norm,rasterized=True);ia=axes[1,j].scatter(pos[:,0],pos[:,2],c=q['dan'],s=6,cmap='viridis',norm=anorm,rasterized=True)
        for ax in axes[:,j]:ax.set_aspect('equal');ax.set(xlabel='x [m]',ylabel='z [m]',title=q['label'])
    fig.colorbar(im,ax=list(axes[0]),label='Same-state ON - OFF actual pressure rate [Pa/s]; symmetric log display')
    fig.colorbar(ia,ax=list(axes[1]),label='Same-state added acceleration magnitude [m/s2]')
    fig.suptitle('Six frozen CPU force/Darcy calls, zero integration; not the unsaved GPU failure state')
    image=Path(str(P)+'_fields.png');fig.savefig(image,dpi=170);plt.close(fig);files.append(image)
    c.need(all(c.stat(q['path'])==q for q in before),'Consumed source changed')
    result=dict(stage=TAG,passed=True,source_component=c.stat(receipt),actual_physical_steps=0,actual_component_calls_already_completed=6,new_component_calls=0,records_consumed=3,summary_rows=3,focus_rows=24,conditional_pressure_power_is_not_total_coupled_energy=True,raw_compression_is_not_full_projected_rate_budget=True,dt_times_delta_rate_is_not_symplectic_prediction=True,CPU_is_not_GPU_bit_replay=True,unsaved_failure_reconstructed=False,physical_acceptance=False,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in files],SHA_scans=0)
    with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
