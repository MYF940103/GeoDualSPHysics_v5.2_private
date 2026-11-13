"""Offline summaries of the rejected centroid candidate's 35 sealed saves."""
import argparse,json,struct
from pathlib import Path
from scipy.spatial import cKDTree
import c08_h18_wend_receiver_review_r1 as previous

old=previous.old
np,T,stat,read=old.np,old.T,old.stat,old.read
TAG='c08_h18_centroid_partial_review_r1'
RUN='c08_h18_centroid_a07_GPU_r1'

def mapped(root,n,count):
    fields=[('time','<f8')]+[(name,old.TYPES[kind].newbyteorder('<'),(n,width)) for name,kind,width in old.SCHEMA]
    dtype=np.dtype(fields);raw=root/'typed22.bin'
    with raw.open('rb') as f:assert struct.unpack('<III',f.read(12))==(n,22,count)
    assert raw.stat().st_size==12+count*dtype.itemsize
    return np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true');a=parser.parse_args()
    assert a.execution_authorized
    root=T/'outputs'/RUN/'native_partial_r1';source=T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
    prefix=T/'figures'/TAG;check=T/'logs'/(TAG+'.check.json')
    assert not check.exists() and not list(prefix.parent.glob(TAG+'*'))
    paths=[Path(__file__),T/'logs'/(RUN+'.run.json'),T/'logs'/(RUN+'.native_r1.check.json'),T/'logs'/(RUN+'.prefix_r1.check.json')]
    paths += [p/name for p in (root,source) for name in ('completion.json','typed22.bin','typed22_layout.csv','clocks.csv')]
    consumed=[stat(p) for p in paths];result=dict(stage=TAG,analysis_complete=False,physical_acceptance=False,consumed=consumed)
    try:
        run=read(paths[1]);receipt=read(paths[2]);proof=read(paths[3]);done=read(root/'completion.json');src=read(source/'completion.json')
        assert not run['passed'] and not run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==1
        assert receipt['passed'] and proof['passed'] and proof['compared_original_records']==34
        assert done['saved_prefix_native_passed'] and done['diagnostic_complete'] and not done['passed'] and done['samples']==35
        assert src['passed'] and src['samples']==1001
        frames=mapped(root,6805,35);pre=mapped(source,7060,1001)
        assert np.array_equal(pre[-1]['Idp'][:,0],np.arange(7060,dtype=np.uint32))
        ppos=pre[-1]['Posd'][2060:];initial=pre[0]['Posd'][2060:];z0=initial[:,2];top=z0==z0.max();bottom=z0==z0.min()
        expected=np.r_[np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)]
        rows=[]
        for i,f in enumerate(frames):
            assert np.array_equal(f['Idp'][:,0],expected)
            soil=f['Idp'][:,0]>=2060;pos=f['Posd'][soil];p=f['PorePress'][soil,0].astype(float);q=f['ExcessPorePress'][soil,0].astype(float)
            sk=f['SigmaState_kk'][soil];si=f['SigmaState_ij'][soil];v=f['Vel'][soil].astype(float);speed=np.linalg.norm(v,axis=1)
            j=f['PoroVolumeRatio'][soil,0];kap=f['Kplastic'][soil,0];du=pos-ppos
            tree=cKDTree(pos[:,[0,2]]);nn=tree.query(pos[:,[0,2]],k=2)[0][:,1]/.04;pairs=tree.query_pairs(.7*.04,output_type='ndarray')
            row=dict(part=i,time_s=float(f['time']),tau_s=float(f['time'])-done['source_actual_time_s'],
                p_min_Pa=float(p.min()),p_max_Pa=float(p.max()),p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),negative_p_IDs=int((p<0).sum()),
                native_p_minus_fixed_P0_RMS_Pa=float(np.sqrt(np.mean(q*q))),J_min=float(j.min()),J_max=float(j.max()),kappa_max=float(kap.max()),
                effective_stress_Frob_RMS_Pa=float(np.sqrt(np.mean(np.sum(sk*sk,axis=1)+2*np.sum(si*si,axis=1)))),
                total_stress_Frob_RMS_Pa=float(np.sqrt(np.mean(np.sum((sk-p[:,None])**2,axis=1)+2*np.sum(si*si,axis=1)))),
                top_material_settlement_mm=float(-1000*du[top,2].mean()),bottom_material_settlement_mm=float(-1000*du[bottom,2].mean()),
                front_advance_from_PRE_m=float(pos[:,0].max()-ppos[:,0].max()),speed_RMS_m_s=float(np.sqrt(np.mean(speed*speed))),speed_max_m_s=float(speed.max()),
                mixture_KE_J_per_m=float(.5*np.sum(f['PoroMixtureDensity'][soil,0]*f['PoroCurrentVolume'][soil,0]*speed*speed)),
                NN_min_over_dp=float(nn.min()),NN_q05_over_dp=float(np.quantile(nn,.05)),NN_median_over_dp=float(np.median(nn)),pairs_below_0p7dp=int(len(pairs)))
            rows.append(row)
        csv=Path(str(prefix)+'_history.csv');old.write_csv(csv,rows)
        fig,axes=old.plt.subplots(4,2,figsize=(13,14),layout='constrained');tau=[r['tau_s'] for r in rows]
        panels=[(('p_min_Pa','p_mean_Pa','p_RMS_Pa'),1e-3,'Absolute pressure [kPa]'),
                (('effective_stress_Frob_RMS_Pa','total_stress_Frob_RMS_Pa'),1e-3,'Stress Frobenius RMS [kPa]'),
                (('J_min','J_max'),1,'Volume ratio J'),(('kappa_max',),1,'Maximum plastic history'),
                (('top_material_settlement_mm','bottom_material_settlement_mm'),1,'Fixed material settlement [mm]'),
                (('speed_RMS_m_s','speed_max_m_s'),1,'Speed [m/s]'),
                (('NN_min_over_dp','NN_q05_over_dp','NN_median_over_dp'),1,'Nearest spacing / dp'),
                (('pairs_below_0p7dp',),1,'Close pairs (descriptive count)')]
        for ax,(keys,scale,title) in zip(axes.flat,panels):
            for key in keys:ax.plot(tau,[r[key]*scale for r in rows],label=key)
            ax.set(title=title,xlabel='Actual saved tau [s]');ax.grid(alpha=.2);ax.legend(fontsize=7)
        fig.suptitle('Rejected centroid AS .7 candidate: all35 saved states\nLater wall808 failure; no .9s completion or physical acceptance',fontsize=12)
        png=Path(str(prefix)+'.png');fig.savefig(png,dpi=160);old.plt.close(fig)
        assert all(stat(p['path'])==p for p in consumed)
        result.update(analysis_complete=True,samples=35,first34_actual_prefix_exact=True,last_saved=rows[-1],
            extrema=dict(p_min_Pa=min(r['p_min_Pa'] for r in rows),p_RMS_max_Pa=max(r['p_RMS_Pa'] for r in rows),
                NN_min_over_dp=min(r['NN_min_over_dp'] for r in rows),close_pairs_max=max(r['pairs_below_0p7dp'] for r in rows)),
            native_fixed_P0_difference_is_not_paper_excess=True,mixture_KE_is_not_total_energy_balance=True,
            close_pairs_not_tensile_causation=True,whole_run_passed=False,unsaved_failure_state_reconstructed=False,
            no_new_physical_thresholds=True,decoder_invocations=0,solver_invocations=0,SHA_scans=0,
            consumed_stats_unchanged=True,visual_QA_pending=True,files=[stat(csv),stat(png)])
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')

if __name__=='__main__':main()
