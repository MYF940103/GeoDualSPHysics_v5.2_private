"""Offline actual-step Ck2 CPU/GPU composition review; no solver or decoder."""
import json,struct,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];L=T/'logs';P=T/'figures/upl_ck2_release_short_r1'
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
    with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
    with Path(p).open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def frob(v):return np.sqrt(np.sum(v[:,:3]**2,axis=1)+2*np.sum(v[:,3:]**2,axis=1))
def load(backend):
    tag='upl_ck2_release_short_'+backend+'_r1';d=T/'outputs'/(tag+'_native_r1');check=L/(tag+'_native_r1.check.json');c=read(check);runpath=L/(tag+'.run.json');run=read(runpath)
    need(c['passed'] and c['original_native_guards_passed'] and c['consumed_stats_unchanged'] and run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0,'Closed run/native checks required')
    for e in [c['native_completion'],*c['files']]:need(stat(e['path'])==e,'Closed native output changed')
    done=read(d/'completion.json');need(done['HydroMechConductivityModel']==1 and done['HydroMechConductivityCk']==2 and done['completed_steps']==800,'Wrong Ck2 native profile')
    layout=table(d/'typed22_layout.csv');need(len(layout)==22 and sum(int(r['bytes_per_particle']) for r in layout)==212,'Original22 layout differs')
    dtype={'uint32':'<u4','float32':'<f4','float64':'<f8'};clocks=table(d/'clocks.csv');need(len(clocks)==done['samples'],'Incomplete clocks')
    original=table(d/'native_ids.csv');need(len(original)==7060 and all(int(r['id'])==i for i,r in enumerate(original)),'Original ID ledger differs');x0=np.array([[float(r[k]) for k in ('x0','y0','z0')] for r in original])
    data={};counts=done['phase_saved_frames']
    for phase,count in enumerate(counts):
        blob=(d/('phase%d_typed22.bin'%phase)).read_bytes();n=7060 if phase==0 else 6800;size=8+n*212
        need(struct.unpack('<III',blob[:12])==(n,22,count) and len(blob)==12+count*size,'Actual phase binary header/size differs');records=[]
        for local in range(count):
            off=12+local*size;time=struct.unpack_from('<d',blob,off)[0];off+=8;a={}
            for r in layout:
                nc=int(r['components']);dt=np.dtype(dtype[r['type']]);v=np.frombuffer(blob,dt,count=n*nc,offset=off);off+=n*nc*dt.itemsize;need(np.isfinite(v).all(),'Nonfinite actual array');a[r['array']]=v.reshape(n,nc) if nc>1 else v
            wanted=np.arange(7060) if phase==0 else np.r_[np.arange(1800),np.arange(2060,7060)];need(np.array_equal(a['Idp'],wanted),'Actual original ID membership differs');records.append((time,a))
        data[phase]=records
    frames=[];previous=0;scalar=0.;used=[0,0]
    for part,c in enumerate(clocks):
        phase=int(c['phase']);local=int(c['phase_local_index']);need(local==used[phase] and int(c['part'])==part,'Actual phase order differs');used[phase]+=1;time,a=data[phase][local];completed=int(c['completed_step'])
        for _ in range(previous,completed):scalar+=2.5e-6
        previous=completed;need(abs(time-scalar)<=1e-14 and time==float(c['time_s']),'Actual scalar clock differs')
        if part:need(int(c['dterror_interval_empty'])==0 and float(c['signed_dterror_s'])<=1e-14,'Original signed interval failed')
        soil=np.flatnonzero(a['Idp']>=2060);ids=a['Idp'][soil];need(np.array_equal(ids,np.arange(2060,7060)),'All5000 soil IDs required');j=a['PoroVolumeRatio'][soil];k=a['PoroHydraulicConductivity'][soil];pn=float(np.float32(.35));k0=float(np.float32(.0002));reference=k0*np.exp((j-1)/((1-pn)*2))
        need(np.all(np.abs(k-reference)<=5e-13*np.abs(reference)),'Independent same-J conductivity law mismatch')
        u=(a['Posd'][soil]-x0[ids])*1000;p=a['PorePress'][soil].astype(float);total=np.c_[a['SigmaState_kk'][soil]-p[:,None],a['SigmaState_ij'][soil]];z=x0[ids,2];top=z>=z.max()-2*float(np.float32(.048));bottom=z<=z.min()+2*float(np.float32(.048))
        row=dict(backend=backend,part=part,completed_step=completed,actual_time_s=time,phase=phase,native_IDs=len(a['Idp']),soil_IDs=5000,p_mean_Pa=float(p.mean()),p_RMS_Pa=float(np.sqrt(np.mean(p*p))),top_material_settlement_mm=float(-u[top,2].mean()),bottom_material_settlement_mm=float(-u[bottom,2].mean()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(total)**2))),J_min=float(j.min()),J_max=float(j.max()),k_min_m_s=float(k.min()),k_max_m_s=float(k.max()),kappa_max=float(a['Kplastic'][soil].max()),FS23_soil=int(np.isin(a['FSType'][soil],(2,3)).sum()))
        frames.append(dict(row=row,p=p,u=u,total=total,k=k,j=j))
    need(used==counts and previous==800,'Incomplete phase/frame coverage')
    return frames,c,run
check=L/'upl_ck2_release_short_r1.check.json';paths=[check,Path(str(P)+'.png'),Path(str(P)+'_history.csv'),Path(str(P)+'_pairs.csv')];need(not any(p.exists() for p in paths),'Existing review protected')
cpu,cc,cr=load('CPU');gpu,gc,gr=load('GPU');need(gr['memcheck_zero_errors_and_leaks'],'GPU memcheck not passed');need(len(cpu)==len(gpu),'Backend frame counts differ');pairs=[]
for a,b in zip(cpu,gpu):
    x,y=a['row'],b['row'];need(x['completed_step']==y['completed_step'] and x['phase']==y['phase'] and x['native_IDs']==y['native_IDs'],'Actual matched-step phase/IDs differ');dp=b['p']-a['p'];du=b['u']-a['u']
    pairs.append(dict(completed_step=x['completed_step'],actual_time_s=x['actual_time_s'],phase=x['phase'],time_difference_s=abs(x['actual_time_s']-y['actual_time_s']),pressure_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),material_XYZ_max_mm=float(np.linalg.norm(du,axis=1).max()),total_stress_Frobenius_RMS_Pa=float(np.sqrt(np.mean(frob(b['total']-a['total'])**2))),J_max_difference=float(np.abs(b['j']-a['j']).max()),k_max_difference_m_s=float(np.abs(b['k']-a['k']).max())))
write(paths[2],[r['row'] for group in (cpu,gpu) for r in group]);write(paths[3],pairs)
fig,axes=plt.subplots(2,3,figsize=(13,7.4));fields=[('p_RMS_Pa','Pressure RMS (Pa)'),('top_material_settlement_mm','Top material settlement (mm)'),('total_stress_Frobenius_RMS_Pa','Total stress Frobenius RMS (Pa)'),('J_min','Minimum J'),('k_min_m_s','Minimum k (m/s)'),('phase','Saved phase')]
for backend,group,color in (('CPU8',cpu,'#1866a0'),('GPU',gpu,'#d17a12')):
    x=[r['row']['actual_time_s']*1000 for r in group]
    for ax,(field,label) in zip(axes.flat,fields):ax.plot(x,[r['row'][field] for r in group],label=backend,color=color,ls='-' if backend=='CPU8' else 'none',marker=None if backend=='CPU8' else 'o',mfc='none',ms=4);ax.set(xlabel='Actual time (ms)',ylabel=label);ax.grid(alpha=.25);ax.axvline(.95,color='gray',ls=':',lw=1)
axes[0,0].legend();axes[1,2].set_yticks((0,1));fig.suptitle('C08 Ck=2 combined startup/release compatibility; not preload equilibrium or full collapse');fig.tight_layout(rect=(0,0,1,.95));fig.savefig(paths[1],dpi=160);plt.close(fig)
pressure=max(r['pressure_RMS_Pa'] for r in pairs);disp=max(r['material_XYZ_max_mm'] for r in pairs);time_error=max(r['time_difference_s'] for r in pairs);passed=pressure<=5 and disp<=.005 and time_error<=1e-14
result=dict(stage='upl_ck2_release_short_r1.review',passed=passed,backend_checks={b:stat(L/('upl_ck2_release_short_'+b+'_r1_native_r1.check.json')) for b in ('CPU','GPU')},run_checks={b:stat(L/('upl_ck2_release_short_'+b+'_r1.run.json')) for b in ('CPU','GPU')},source_builds=dict(CPU=cr['source_build'],GPU=gr['source_build']),programs=dict(CPU=cr['program'],GPU=gr['program']),memcheck_zero_errors_and_leaks=True,actual_matched_pairs=len(pairs),phase_frame_counts=cc['actual_completion']['phase_saved_frames'],pressure_RMS_max_Pa=pressure,material_XYZ_max_mm=disp,time_error_max_s=time_error,total_stress_Frobenius_RMS_max_Pa=max(r['total_stress_Frobenius_RMS_Pa'] for r in pairs),kappa_max_by_backend={b:max(r['row']['kappa_max'] for r in group) for b,group in (('CPU',cpu),('GPU',gpu))},outputs=[stat(p) for p in paths[1:]],physical_acceptance=False,full13s_or_paper_validation=False,no_half_or_old_control_rerun=True,SHA_scans=0)
save(check,result);print(json.dumps(result,indent=2));need(passed,'Original backend comparison failed; retain evidence, no relaxed gate')
