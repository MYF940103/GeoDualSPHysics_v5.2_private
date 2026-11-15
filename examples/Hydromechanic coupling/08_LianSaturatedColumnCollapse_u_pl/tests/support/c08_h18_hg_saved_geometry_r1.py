"""Offline six saved-state HG geometry/necessary-scale screen; never invokes a solver/reader."""
import argparse, csv, json, math, re, struct, zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1]; R=T.parents[3]; S=R/'src/source'
TAG='c08_h18_hg_saved_geometry_r1'; NOTE=T/'notes'/(TAG+'.md')
REVIEW=T/'logs/c08_h18_as03n255_full3_review_r1.check.json'
NATIVE=T/'logs/c08_h18_as03n255_full3_native_r1.check.json'
ROOT=T/'outputs/c08_h18_as03n255_full3_r1'; RAW=ROOT/'native_r1'
OUT=T/'outputs'/TAG; CHECK=T/'logs'/(TAG+'.check.json'); PNG=T/'figures'/(TAG+'.png')
PARTS=(0,38,60,83,87,300); XI=.1; REQUIRED_DT=5e-6
SCHEMA=(('Idp','uint32',1),('Posd','float64',3),('Vel','float32',3),('Sigma_kk','float32',3),('Sigma_ij','float32',3),('FSNormal','float32',3),('HydroMechLoadAce','float32',3),('native_Rhop','float32',1),('Kplastic','float32',1),('PorePress','float32',1),('PorePress0','float32',1),('ExcessPorePress','float32',1),('SigmaState_kk','float64',3),('SigmaState_ij','float64',3),('FSType','uint32',1),('PoroVolumeRatio','float64',1),('PoroPorosity','float64',1),('PoroThetaLastStage','float64',1),('PoroCurrentVolume','float64',1),('PoroMixtureDensity','float64',1),('PoroHydraulicConductivity','float64',1),('PosDiv','float32',1))
TYPES={'uint32':np.dtype('<u4'),'float32':np.dtype('<f4'),'float64':np.dtype('<f8')}
def need(ok,text):
    if not ok: raise RuntimeError(text)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve(); q=p.stat(); return dict(path=str(p),bytes=q.st_size,mtime_ns=q.st_mtime_ns)
def same(a,b): return str(Path(a).resolve()).casefold()==str(Path(b).resolve()).casefold()
def bind(q): need(stat(q['path'])==q,'Original sealed stat differs: '+q['path']); return q
def sealed(p,entries):
    found=[q for q in entries if same(p,q['path'])]
    need(found and all(q==found[0] for q in found),'Unique original seal absent/conflicting: '+str(p)); return bind(found[0])
def table(p):
    with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def dump(p,obj):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2,allow_nan=False)
def clean(v):
    if isinstance(v,(np.bool_,bool)):return bool(v)
    if isinstance(v,(np.integer,int)):return int(v)
    if isinstance(v,(np.floating,float)):return float(v) if math.isfinite(v) else None
    return v
def csvwrite(p,rows):
    need(rows,'Empty derived CSV')
    with Path(p).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:clean(v) for k,v in q.items()} for q in rows)
def f32(v):return float(np.float32(v))
def inputs(consumed):
    rev,native=read(REVIEW),read(NATIVE)
    need(rev['analysis_complete'] and rev['consumed_stats_unchanged'] and rev['actual_samples']==301
         and not rev['physical_acceptance'] and native['passed'] and native['consumed_stats_unchanged']
         and native['reader_invocations']==1 and native['solver_invocations']==0,'Actual sealed full301 review/native required')
    consumed.extend(stat(p) for p in (Path(__file__),NOTE,REVIEW,NATIVE))
    for key in ('native_completion','metadata','actual_call','reader_build'):consumed.append(bind(native[key]))
    done=read(native['native_completion']['path']); call=read(native['actual_call']['path'])
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,'Original successful owned native call required')
    need(done['passed'] and done['samples']==301 and done['completed_steps']==2600000
         and done['typed_arrays']==22 and done['typed_bytes_per_particle']==212
         and done['actual_native_IDs_per_frame']==6805 and done['soil_IDs']==5000
         and done['ledger_checks']==1505000 and done['source_handoff_schema']==2
         and done['source_material_law_version']==done['target_material_law_version']==2
         and done['declared_Kernel_XML_CSV']==2 and done['geometry_profile']=='bedroles'
         and not done['keep_bed_overlap'] and not done['native_rewritten']
         and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
         and done['max_ledger_relative_error']<=5e-13,'Original full301 native scope/budgets differ')
    consumed.extend(sealed(RAW/leaf,rev['consumed']) for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'))
    xmlpath=ROOT/'c08_h18_as03n255_full3_r1.xml'; runpath=ROOT/'Run.out'
    consumed.extend(sealed(p,rev['consumed']) for p in (xmlpath,runpath))
    archive=T/'outputs/c08_preload_schema2_source_r1/full_source.zip'
    consumed.append(sealed(archive,rev['consumed']))
    # Actual source anchors, not a newly invented kernel/elasticity convention.
    anchors={
      'JSphHourglassCpu.cpp':('const double mass=(Mass/RhopZero)*(RhopZero-WaterRho+WaterRho*j);','n.vol=(Mass/RhopZero)*n.j;','Pairs.push_back({i,j,dx,dz,-bwen/h*s*s*s});','add(a,b.vol*pair.w);add(b,a.vol*pair.w);','const double beta=Xi*Shear*a.vol*b.vol*pair.w;','2*n.betasum/(RhopZero? ParticleMass(n.j): Mass)','lo>0 && hi/lo<1e8'),
      'JSphCpuSingle.cpp':('CSP.kernelh,KernelSize,CSP.kwend.bwen,SoilCte.ModulusG,','(PorosityFeedback? RhopZero: 0),(PorosityFeedback? SoilCte.PoreWaterRho: 0)'),
      'FunSphKernel.h':('inline float GetKernelWendland_Factor(){ return(2.0f); }','kc.bwen=float(-2.7852/(h*h*h));'),
      'JSph.cpp':('SoilCte.ModulusG = float(SoilCte.ModulusE / (2.f*(1.f + SoilCte.PRvs)));',),
      'DualSphDef.h':('float ModulusE;','float PRvs;','float ModulusG;'),
      'JSph.h':('double SoilHourglassXi;','float KernelH;','float RhopZero;','float MassFluid;')}
    with zipfile.ZipFile(archive) as z:
        for leaf,patterns in anchors.items():
            current=(S/leaf).read_text(encoding='utf-8-sig'); frozen=z.read('src/source/'+leaf).decode('utf-8-sig')
            need(all(current.count(p)==frozen.count(p)==1 for p in patterns),'Actual/archive numerical anchor differs: '+leaf)
            consumed.append(stat(S/leaf))
    root=ET.parse(xmlpath).getroot(); pars={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')}
    c=root.find('execution/constants'); soil=root.find('execution/special/soils'); hydro=root.find('execution/special/hydromechanics')
    need(c is not None and soil is not None and hydro is not None,'Actual generated constants/material/hydromechanics required')
    H=f32(c.find('h').get('value')); support=f32(np.float32(2)*np.float32(H)); mass=f32(c.find('massfluid').get('value'))
    rho0=f32(c.find('rhop0').get('value')); rhow=f32(hydro.find('PoreWaterRho').get('value'))
    E=np.float32(soil.find('ModulusE').get('value')); nu=np.float32(soil.find('PRvs').get('value'))
    G=float(np.float32(E/np.float32(np.float32(2)*np.float32(np.float32(1)+nu))))
    bwen=f32(-2.7852/(H*H*H)); text=runpath.read_text(encoding='utf-8')
    match=re.search(r'Shear Modulus:\s*([+\-0-9.eE]+)',text)
    need(H==done['H'] and H>0 and support==2*H and mass>0 and rho0>0 and rhow>=0 and G>0
         and bwen<0 and pars['Kernel']=='2' and 'Kernel="Wendland"' in text
         and 'PeriodicActive="None"' in text and 'Simulate2DPosY=0' in text
         and match and float(match.group(1))==G,'Actual H/2D/kernel/G/volume-inertia binding differs')
    layout=table(RAW/'typed22_layout.csv');fields=[('time','<f8')]
    need(len(layout)==22,'Original22 layout required')
    for q,(name,kind,n) in zip(layout,SCHEMA):
        need((q['array'],q['type'],int(q['components']),int(q['bytes_per_particle']))==(name,kind,n,TYPES[kind].itemsize*n),'Original typed layout differs')
        fields.append((name,TYPES[kind],(6805,n)))
    dtype=np.dtype(fields)
    with (RAW/'typed22.bin').open('rb') as f:need(struct.unpack('<III',f.read(12))==(6805,22,301),'Original1/301 headers may not be rewritten')
    need((RAW/'typed22.bin').stat().st_size==12+301*dtype.itemsize,'Original payload extent differs')
    clocks=table(RAW/'clocks.csv');need(len(clocks)==301,'All original clock records required')
    frames=np.memmap(RAW/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(301,))
    return frames,clocks,dict(H_m=H,support_m=support,Bwen_float=bwen,G_float_Pa=G,E_float_Pa=float(E),nu_float=float(nu),MassFluid_float=mass,RhopZero_float=rho0,WaterRho_float=rhow,xi_double=XI,physical_kernel='Wendland',HG_kernel='Wendland',kernel_matches=True,source_anchors=anchors)

def analyze(frame,q,k):
    expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)))
    need(np.array_equal(frame['Idp'][:,0],expected) and all(np.isfinite(frame[name]).all() for name,_,_ in SCHEMA),'Selected original22 finite/ID gate failed')
    need(float(frame['time'])==float(q['time_s']) and float(q['dt_s'])==REQUIRED_DT and float(q['signed_dterror_s'])<=1e-14
         and int(q['native_IDs'])==6805 and int(q['dterror_interval_empty'])==0,'Selected actual clock/signed interval differs')
    at=frame['Idp'][:,0]>=2060; ids=frame['Idp'][at,0]; pos=np.array(frame['Posd'][at]); vel=np.array(frame['Vel'][at],dtype=float)
    need(len(ids)==5000 and np.all(pos[:,1]==0) and np.all(vel[:,1]==0),'Actual bounded2D5000-soil state required')
    J=np.array(frame['PoroVolumeRatio'][at,0]); vn=np.array(frame['PoroCurrentVolume'][at,0]); rn=np.array(frame['PoroMixtureDensity'][at,0])
    V=(k['MassFluid_float']/k['RhopZero_float'])*J
    m=(k['MassFluid_float']/k['RhopZero_float'])*(k['RhopZero_float']-k['WaterRho_float']+k['WaterRho_float']*J)
    rex=k['WaterRho_float']+(k['RhopZero_float']-k['WaterRho_float'])/J
    need(np.all(J>0)&np.all(V>0)&np.all(m>0)&np.all(np.isfinite(m)),'Original HG positive J/volume/inertia gate failed')
    vgap=np.abs(V-vn)/vn; rgap=np.abs(rex-rn)/rn
    need(vgap.max()<=5e-13 and rgap.max()<=5e-13,'Source-form/native ledger exceeds existing original budget')
    xz=pos[:,(0,2)]; v=vel[:,(0,2)]; radius=k['support_m']; eps=np.finfo(float).eps
    # Search padding only broadens candidate enumeration; strict source rr<support^2 below is unchanged.
    search_pad=32*eps*max(1.,float(np.max(np.abs(xz))))
    pair=cKDTree(xz).query_pairs(radius+search_pad,output_type='ndarray')
    pair=pair[np.lexsort((pair[:,1],pair[:,0]))] if len(pair) else pair
    d=xz[pair[:,0]]-xz[pair[:,1]]; rr=d[:,0]*d[:,0]+d[:,1]*d[:,1]
    margin=np.abs(rr-radius*radius); near=int(np.count_nonzero(margin<=64*eps*np.maximum(radius*radius,np.abs(rr))))
    keep=rr<radius*radius; pair,d,rr=pair[keep],d[keep],rr[keep]; i,j=pair[:,0],pair[:,1]
    r=np.sqrt(rr); s=np.maximum(0.,1-r/(2*k['H_m'])); w=((-k['Bwen_float']/k['H_m'])*s)*s*s
    positive=w>0; coincident=int(np.count_nonzero(rr<=0)); need(np.isfinite(w).all() and np.all(w>=0),'Nonfinite/negative source HG pair weight')
    beta=(((XI*k['G_float_Pa'])*V[i])*V[j])*w; degree=np.zeros(5000,dtype=int); positive_degree=degree.copy()
    mxx=np.zeros(5000);mxz=mxx.copy();mzz=mxx.copy();nxx=mxx.copy();nxz=mxx.copy();nzx=mxx.copy();nzz=mxx.copy();bs=mxx.copy();nearest=np.full(5000,np.inf)
    dv=v[i]-v[j];dx,dz=d[:,0],d[:,1]
    for receiver,weight in ((i,V[j]*w),(j,V[i]*w)):
        np.add.at(degree,receiver,1);np.add.at(positive_degree,receiver,positive.astype(int));np.minimum.at(nearest,receiver,r)
        for acc,value in ((mxx,weight*dx*dx),(mxz,weight*dx*dz),(mzz,weight*dz*dz),(nxx,weight*dv[:,0]*dx),(nxz,weight*dv[:,0]*dz),(nzx,weight*dv[:,1]*dx),(nzz,weight*dv[:,1]*dz)):
            np.add.at(acc,receiver,value)
        np.add.at(bs,receiver,beta)
    det=mxx*mzz-mxz*mxz; tr=mxx+mzz; hi=.5*(tr+np.hypot(mxx-mzz,2*mxz))
    with np.errstate(divide='ignore',invalid='ignore'):
        lo=det/hi;cond=hi/lo
    rank=np.isfinite(det)&(lo>0)&np.isfinite(cond)&(cond<1e8) # exact original numerical gate; no ridge/pinv/threshold change.
    L=np.full((5000,2,2),np.nan); a=rank
    L[a,0,0]=(nxx[a]*mzz[a]-nxz[a]*mxz[a])/det[a];L[a,0,1]=(nxz[a]*mxx[a]-nxx[a]*mxz[a])/det[a]
    L[a,1,0]=(nzx[a]*mzz[a]-nzz[a]*mxz[a])/det[a];L[a,1,1]=(nzz[a]*mxx[a]-nzx[a]*mxz[a])/det[a]
    ri=dv-np.einsum('nij,nj->ni',L[i],d);rj=dv-np.einsum('nij,nj->ni',L[j],d)
    p2=np.zeros(5000);pmax=p2.copy();count=np.zeros(5000,dtype=int)
    for receiver,residual in ((i,ri),(j,rj)):
        good=np.isfinite(residual).all(axis=1);length=np.hypot(residual[good,0],residual[good,1]);rec=receiver[good]
        np.add.at(p2,rec,length*length);np.maximum.at(pmax,rec,length);np.add.at(count,rec,1)
    prms=np.full(5000,np.nan);ok=rank&(count>0);prms[ok]=np.sqrt(p2[ok]/count[ok]);pmax[~ok]=np.nan
    lam=2*bs/m;dt=np.full(5000,np.nan);poslam=lam>0;dt[poslam]=.2/np.sqrt(lam[poslam])
    maxlam=float(lam.max()); limit=.2/math.sqrt(maxlam) if maxlam>0 else None
    positive_condition=cond[np.isfinite(cond)&(cond>0)]; valid_rows=int(count.sum());pvrms=math.sqrt(float(p2.sum())/valid_rows) if valid_rows else None
    geometry=bool(np.all(rank) and coincident==0 and np.all(degree>0))
    active_positive=bool(np.all(positive)) # new energy-state sqrt(D) domain, not an original HG/rank guard.
    gate=bool(geometry and limit is not None and limit>=REQUIRED_DT)
    context=dict(part=int(q['part']),time_s=q['time_s'],tau_s=q['tau_from_actual_release_s'],completed_step=int(q['completed_step']),saved_step=int(q['saved_step']),dt_s=q['dt_s'],signed_dterror_s=q['signed_dterror_s'])
    kappa=np.array(frame['Kplastic'][at,0],dtype=float);fs=frame['FSType'][at,0]
    rows=[]
    for z in range(5000):
        rows.append(dict(**context,native_id=int(ids[z]),x_m=pos[z,0],z_m=pos[z,2],vx_m_s=v[z,0],vz_m_s=v[z,1],J=J[z],native_V_m2=vn[z],HG_V_m2=V[z],native_rho_kg_m3=rn[z],HG_particle_mass_kg_m=m[z],native_Vrho_mass_kg_m=vn[z]*rn[z],HG_mass_vs_Vrho_relative_gap=abs(m[z]-vn[z]*rn[z])/m[z],neighbors=degree[z],positive_weight_neighbors=positive_degree[z],min_neighbor_r_m=nearest[z],Mxx=mxx[z],Mxz=mxz[z],Mzz=mzz[z],det_M=det[z],eigen_lo=lo[z],eigen_hi=hi[z],condition=cond[z],original_rank_gate_pass=rank[z],beta_sum=bs[z],lambda_receiver_per_s2=lam[z],old_receiver_scale_s=dt[z],Lxx_per_s=L[z,0,0],Lxz_per_s=L[z,0,1],Lzx_per_s=L[z,1,0],Lzz_per_s=L[z,1,1],Pv_RMS_m_s=prms[z],Pv_max_m_s=pmax[z],kappa_context_only=kappa[z],FS_type=int(fs[z])))
    atmax=int(lam.argmax()); minr=float(r.min()) if len(r) else None;minpositive=float(r[r>0].min()) if np.any(r>0) else None
    summary=dict(**context,soil_receivers=5000,undirected_pairs=len(pair),directed_rows=2*len(pair),min_r_m=minr,min_positive_r_m=minpositive,min_positive_r_over_dp=None if minpositive is None else minpositive/.04,coincident_pairs=coincident,zero_weight_pairs=int(np.count_nonzero(~positive)),support_roundoff_near_candidates=near,neighbors_min=int(degree.min()),neighbors_median=float(np.median(degree)),neighbors_max=int(degree.max()),rank_fail_receivers=int((~rank).sum()),condition_positive_max=float(positive_condition.max()) if len(positive_condition) else None,condition_positive_q95=float(np.quantile(positive_condition,.95)) if len(positive_condition) else None,lambda_formula_upper_per_s2=maxlam,lambda_max_native_ID=int(ids[atmax]),old_scale_limit_s=limit,five_us_over_scale=None if limit is None else REQUIRED_DT/limit,original_graph_rank_gate_pass=geometry,positive_active_weight_gate_pass=active_positive,necessary_geometry_dt_gate_pass=gate,new_energy_active_graph_gate_pass=bool(gate and active_positive),valid_directed_Pv_rows=valid_rows,Pv_RMS_m_s=pvrms,Pv_max_m_s=float(np.nanmax(pmax)) if np.any(ok) else None,instantaneous_skew_max_per_s=float(np.nanmax(.5*np.abs(L[:,0,1]-L[:,1,0]))) if np.any(rank) else None,native_volume_relative_gap_max=float(vgap.max()),native_rho_relative_gap_max=float(rgap.max()),HG_mass_vs_native_Vrho_relative_gap_max=float(np.max(np.abs(m-vn*rn)/m)),nonzero_kappa_context_count=int(np.count_nonzero(kappa)),original_elastic_state_gate_pass=bool(np.all(kappa==0)),old_implementation_admitted=False)
    return rows,summary

def plot(summary):
    fig,axes=plt.subplots(2,2,figsize=(11,8),layout='constrained');x=[float(q['tau_s']) for q in summary]
    axes[0,0].plot(x,[None if q['old_scale_limit_s'] is None else q['old_scale_limit_s']*1e6 for q in summary],'o-',label='old .2/sqrt(lambda formula)')
    axes[0,0].axhline(5,color='k',ls='--',label='requested5 us');axes[0,0].set(ylabel='Frozen HG scale [us]',yscale='log');axes[0,0].legend(fontsize=8)
    for key,label in (('condition_positive_max','max positive condition'),('condition_positive_q95','q95')):axes[0,1].plot(x,[q[key] for q in summary],'o-',label=label)
    axes[0,1].axhline(1e8,color='k',ls='--',label='original rank ceiling');axes[0,1].set(ylabel='LS moment condition',yscale='log');axes[0,1].legend(fontsize=8)
    axes[0,1].text(.03,.04,'Rank failures by part: '+', '.join(str(q['rank_fail_receivers']) for q in summary),transform=axes[0,1].transAxes,fontsize=8)
    for key,label in (('Pv_RMS_m_s','directed residual RMS'),('Pv_max_m_s','max')):axes[1,0].plot(x,[q[key] for q in summary],'o-',label=label)
    axes[1,0].set(ylabel='Saved velocity residual [m/s]');axes[1,0].legend(fontsize=8)
    axes[1,1].plot(x,[q['min_positive_r_over_dp'] for q in summary],'o-');axes[1,1].set(ylabel='Minimum positive pair r/dp')
    for ax in axes.flat:ax.set_xlabel('Actual saved tau [s]');ax.grid(alpha=.25)
    fig.suptitle('AS03 saved geometry only: xi=.1, worst gamma1\nNo HG trajectory, plastic producer or coupled stability qualification')
    fig.savefig(PNG,dpi=170);plt.close(fig)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true')
    need(p.parse_args().execution_authorized,'Independent root offline-analysis admission required')
    need(not OUT.exists() and not CHECK.exists() and not PNG.exists(),'Existing complete/partial derived outputs protected')
    consumed=[]
    try:
        frames,clocks,constants=inputs(consumed);OUT.mkdir();allrows=[];summary=[]
        for part in PARTS:
            q=clocks[part];need(int(q['part'])==part,'Actual selected part mismatch');rows,s=analyze(frames[part],q,constants);allrows.extend(rows);summary.append(s)
        need(len(allrows)==30000 and len(summary)==6,'All5000 receivers in all6 selected saves required')
        csvwrite(OUT/'receivers.csv',allrows);csvwrite(OUT/'summary.csv',summary);plot(summary)
        for q in consumed:bind(q)
        dump(CHECK,dict(stage=TAG,passed=True,analysis_complete=True,source_review=stat(REVIEW),source_native=stat(NATIVE),parts=list(PARTS),receiver_rows=30000,summary_rows=6,constants=constants,all_necessary_geometry_dt_gates_pass=all(q['necessary_geometry_dt_gate_pass'] for q in summary),new_energy_active_graph_all_pass=all(q['new_energy_active_graph_gate_pass'] for q in summary),rank_failure_total=sum(q['rank_fail_receivers'] for q in summary),summaries=[{k:clean(v) for k,v in q.items()} for q in summary],rank_threshold_unchanged=1e8,xi_prescribed_double=XI,gamma_worst=1,requested_dt_s=REQUIRED_DT,graph_scope='bounded5000soil-only2D',numerical_scope='source-form algebra; deterministic offline accumulation, not original CPU cell/GPU bits',lambda_scope='mathematical frozen Gamma<=1 stiffness upper formula; floating evaluation, not full coupled stability',original_elastic_plastic_guard_bypassed_in_solver=False,plastic_producer_qualified=False,spin_history_qualified=False,actual_Symplectic_qualified=False,Darcy_qualified=False,physical_acceptance=False,solver_invocations=0,reader_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,files=[stat(OUT/'receivers.csv'),stat(OUT/'summary.csv'),stat(PNG)],consumed=consumed,consumed_stats_unchanged=True))
    except Exception as error:
        if not CHECK.exists():dump(CHECK,dict(stage=TAG,passed=False,analysis_complete=False,first_failure=str(error),partial_outputs_preserved=True,consumed=consumed,solver_invocations=0,reader_invocations=0,SHA_scans=0,physical_acceptance=False))
        raise

if __name__=='__main__':main()
