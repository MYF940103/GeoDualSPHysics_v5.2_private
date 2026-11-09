"""Frozen-state Cubic matched-LS residual force-rate shadow; no actual force or state update."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_cubic_residual_rate_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');JOB='upl_c08_causal_window_GPU_r1';N=6805;PARTS=(13,14);FOCUS=(7011,7012,6230,6231)
need,read,stat,bind=e.need,e.read,e.stat,e.bind
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def graph(x,V,h):
 support=2*h;cells=np.floor(x/support).astype(np.int64);bucket={}
 for k,cell in enumerate(cells):bucket.setdefault(tuple(cell),[]).append(k)
 ii=[];jj=[]
 for i,cell in enumerate(cells):
  for dx in (-1,0,1):
   for dz in (-1,0,1):
    for j in bucket.get((cell[0]+dx,cell[1]+dz),()):
     if j>i and np.dot(x[i]-x[j],x[i]-x[j])<support*support:ii.append(i);jj.append(j)
 i=np.asarray(ii);j=np.asarray(jj);need(len(i)>0,'Empty actual complete soil graph');d=x[i]-x[j];r=np.linalg.norm(d,axis=1);q=r/h
 # Positive analytic -W'(r)/r, including its finite r=0 limit; no trial cutoff.
 alpha=10/(7*np.pi*h*h);w=np.empty(len(q));inner=q<=1;w[inner]=alpha/(h*h)*(3-2.25*q[inner]);w[~inner]=alpha/(h*h)*.75*(2-q[~inner])**2/q[~inner]
 need(np.isfinite(w).all() and (w>0).all(),'Cubic derivative weights must be positive on the open support');M=np.zeros((len(x),2,2));dd=d[:,:,None]*d[:,None,:];np.add.at(M,i,V[j,None,None]*w[:,None,None]*dd);np.add.at(M,j,V[i,None,None]*w[:,None,None]*dd)
 U,s,Vt=np.linalg.svd(M);rank=np.sum(s>2*np.finfo(float).eps*s[:,0,None],axis=1);need(np.all(s[:,1]>0),'Exactly singular unregularized LS moment; native IDs='+str((2060+np.flatnonzero(s[:,1]<=0)).tolist())+'; no point is skipped or regularized')
 inverse=(Vt.transpose(0,2,1)*(1/s)[:,None,:])@U.transpose(0,2,1);degree=np.bincount(np.r_[i,j],minlength=len(x));return dict(i=i,j=j,d=d,w=w,M=M,inverse=inverse,s=s,rank=rank,condition=s[:,0]/s[:,1],degree=degree)
def shadow(x,v,V,rho,G,g):
 i,j,d,w=g['i'],g['j'],g['d'],g['w'];dv=v[i]-v[j];B=np.zeros_like(g['M']);outer=dv[:,:,None]*d[:,None,:];np.add.at(B,i,V[j,None,None]*w[:,None,None]*outer);np.add.at(B,j,V[i,None,None]*w[:,None,None]*outer);L=B@g['inverse'];li=np.einsum('nij,nj->ni',L[i],d);lj=np.einsum('nij,nj->ni',L[j],d);ri=dv-li;rj=dv-lj
 beta=G*V[i]*V[j]*w;pair=-.5*beta[:,None]*(ri+rj);force=np.zeros_like(v);np.add.at(force,i,pair);np.add.at(force,j,-pair);mass=rho*V;jerk=force/mass[:,None];form=float(.25*np.sum(beta*(np.sum(ri*ri,axis=1)+np.sum(rj*rj,axis=1))));power=float(np.sum(v*force));net=force.sum(axis=0);torque=float(np.sum(x[:,0]*force[:,1]-x[:,1]*force[:,0]));pairtorque=float(np.sum(d[:,0]*pair[:,1]-d[:,1]*pair[:,0]))
 normal=np.zeros_like(B);np.add.at(normal,i,V[j,None,None]*w[:,None,None]*(ri[:,:,None]*d[:,None,:]));np.add.at(normal,j,V[i,None,None]*w[:,None,None]*(rj[:,:,None]*d[:,None,:]));normal_power=float(G*np.sum(V[:,None,None]*L*normal));normal_torque=float(G*np.sum(V*(normal[:,1,0]-normal[:,0,1])))
 # Fixed operation-count envelope, before reading results; SVD error is exposed separately by its actual normal-equation defect.
 operations=64*(len(x)+len(i)+int(g['degree'].max())+1);eps=np.finfo(float).eps;gamma=operations*eps/(1-operations*eps)
 power_scale=float(np.sum((np.abs(v[i])+np.abs(v[j]))*np.abs(pair))+2*form+.5*np.sum(beta[:,None]*(np.abs(li*ri)+np.abs(lj*rj))));power_budget=gamma*power_scale;force_budget=gamma*np.sum(2*np.abs(pair),axis=0)
 torque_scale=float(np.sum((np.abs(x[i,0])+np.abs(x[j,0]))*np.abs(pair[:,1])+(np.abs(x[i,1])+np.abs(x[j,1]))*np.abs(pair[:,0])))+.5*G*float(np.sum(V*(np.abs(normal[:,1,0])+np.abs(normal[:,0,1]))));torque_budget=gamma*torque_scale
 need(np.isfinite(L).all() and np.isfinite(jerk).all() and np.isfinite(form+power+torque+normal_power+normal_torque),'Nonfinite shadow arithmetic')
 need(abs(power+2*form+.5*normal_power)<=power_budget and np.all(np.abs(net)<=force_budget) and abs(torque+.5*normal_torque)<=torque_budget,'Shadow algebra exceeds the declared accumulation envelope; preserve result, no tolerance change')
 betasum=np.zeros(len(x));np.add.at(betasum,i,beta);np.add.at(betasum,j,beta);lam=2*betasum/mass;normal_scale=np.linalg.norm(B,axis=(1,2))+np.linalg.norm(L@g['M'],axis=(1,2));relative=np.divide(np.linalg.norm(normal,axis=(1,2)),normal_scale,out=np.zeros(len(x)),where=normal_scale>0)
 summary=dict(pairs=len(i),numerical_rank_below2=int(np.sum(g['rank']<2)),max_LS_condition=float(g['condition'].max()),max_normal_equation_relative_defect=float(relative.max()),force_rate_power_J_per_m_s2=power,quadratic_form_J_per_m_s2=form,power_plus_2form_J_per_m_s2=power+2*form,LS_normal_power_defect_J_per_m_s2=normal_power,work_accumulation_budget_J_per_m_s2=power_budget,work_budget_including_LS_defect_J_per_m_s2=power_budget+.5*abs(normal_power),net_force_rate_x_N_per_m_s=float(net[0]),net_force_rate_z_N_per_m_s=float(net[1]),net_force_rate_budget_x_N_per_m_s=float(force_budget[0]),net_force_rate_budget_z_N_per_m_s=float(force_budget[1]),torque_rate_origin_N_m_per_m_s=torque,pair_torque_rate_N_m_per_m_s=pairtorque,LS_normal_torque_defect_N_m_per_m_s=normal_torque,torque_accumulation_budget_N_m_per_m_s=torque_budget,operation_count_envelope=operations,gamma_envelope=gamma,max_acceleration_rate_m_s3=float(np.linalg.norm(jerk,axis=1).max()),max_pair_one_sided_residual_m_s=float(max(np.linalg.norm(ri,axis=1).max(),np.linalg.norm(rj,axis=1).max())),lambda_bound_unit_xi_s_2=float(lam.max()),tau_unit_xi_s=float(1/np.sqrt(lam.max())),hypothetical_xi=.2,hypothetical_tau_xi02_s=float(1/np.sqrt(.2*lam.max())),hypothetical_dt_over_tau_xi02=float(2.5e-6*np.sqrt(.2*lam.max())))
 return dict(summary=summary,L=L,force=force,jerk=jerk,lambda_bound=lam,normal_relative=relative)
def run():
 paths={k:Path(str(PREFIX)+'_'+k+s) for k,s in [('summary','.csv'),('particles','.csv'),('pairs','.csv'),('manufactures','.csv'),('rates','.png')]};need(not CHECK.exists() and all(not p.exists() for p in paths.values()),'Existing complete/partial offline shadow protected');before=[]
 try:
  npth=T/'logs'/(JOB+'.native_r1.json');rp=T/'logs'/(JOB+'.run.json');gp=T/'logs/upl_c08_pair_gradient_cpu_r1.check.json';n,r,gr=read(npth),read(rp),read(gp);need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['source_run']==stat(rp) and r['passed'] and r['saved_frames']==90 and r['actual_steps']==4360000,'Actual passed causal90/native required');need(gr['passed'] and gr['source_native']==stat(npth) and gr['baseline_alignment']['mismatched_fields']==0,'Sealed actual baseline gradient/state provenance required')
  done=read(bind(n['completion'])['path']);native=Path(n['completion']['path']).parent;need(done['passed'] and done['samples']==90 and done['actual_native_IDs_per_frame']==N and done['typed_arrays']==22,'Original90/6805/22 profile required');bound={Path(q['path']).name:q for q in n['outputs']};before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(e.__file__),stat(npth),stat(rp),stat(gp),bind(n['completion']),bind(n['metadata']),bind(r['Run_out']),bind(r['input_xml']),bind(gr['source_prefix_proof'])]+[bind(bound[k]) for k in ('typed22.bin','typed22_layout.csv','clocks.csv')]
  logged=re.findall(r'^\s*Shear Modulus:\s*([0-9.eE+-]+)\s*$',Path(r['Run_out']['path']).read_text(encoding='utf-8',errors='replace'),re.M);need(len(logged)==1,'One actual frozen Run shear modulus required');G=float(logged[0]);need(G>0 and float(np.float32(G))==G,'Actual logged float shear modulus required');xml=ET.parse(r['input_xml']['path']).getroot();h=float(np.float32(float(xml.find('execution/constants/h').get('value'))));need(h==float(np.float32(.048)),'Only original Cubic h1.2 geometry is admitted');params={q.get('key'):q.get('value') for q in xml.findall('execution/parameters/parameter')};need(float(params['DtFixed'])==2.5e-6,'Hypothetical dt/tau must use the actual frozen2.5us input')
  layout=table(native/'typed22_layout.csv');need(len(layout)==22,'Original22 layout required');fields=[('time','<f8')]
  for q in layout:
   dt={'uint32':'<u4','float32':'<f4','float64':'<f8'}[q['type']];width=int(q['components']);need(np.dtype(dt).itemsize*width==int(q['bytes_per_particle']),'Typed layout byte width differs');fields.append((q['array'],dt,(N,width)))
  dtype=np.dtype(fields);raw=native/'typed22.bin';need(dtype.itemsize==8+N*212 and raw.stat().st_size==12+90*dtype.itemsize,'Actual normal90 payload extent differs');clocks=table(native/'clocks.csv');need(len(clocks)==90,'Actual90 clock rows required');expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('<u4');summaries=[];particles=[];pairrows=[];manufactures=[];panels=[]
  with raw.open('rb') as f:
   need(struct.unpack('<III',f.read(12))==(N,22,90),'Actual original90 header required')
   for part in PARTS:
    f.seek(12+part*dtype.itemsize);a=np.fromfile(f,dtype=dtype,count=1)[0];time=float(a['time']);tau=time-float(done['source_actual_time_s']);need(np.array_equal(a['Idp'][:,0],expected) and struct.pack('<d',time)==struct.pack('<d',float(clocks[part]['time_s'])) and int(clocks[part]['completed_step'])==4000000+4000*(part+1),'Actual selected ID/time/step differs')
    for q in layout:need(np.isfinite(a[q['array']]).all(),'Nonfinite selected native array')
    soil=a['Idp'][:,0]>=2060;ids=a['Idp'][soil,0];need(np.array_equal(ids,np.arange(2060,7060)) and np.all(a['Posd'][soil,1]==0) and np.all(a['Vel'][soil,1]==0),'Full5000 native2D soil set required');x=a['Posd'][soil][:,(0,2)];v=a['Vel'][soil][:,(0,2)].astype(float);V=a['PoroCurrentVolume'][soil,0];rho=a['PoroMixtureDensity'][soil,0];need(np.all(V>0) and np.all(rho>0),'Positive actual volume/density required');g=graph(x,V,h);out=shadow(x,v,V,rho,G,g);row=dict(part=part,time_s=time,tau_s=tau,completed_step=int(clocks[part]['completed_step']),native_soil_IDs=5000,xi=1,G_Pa=G,h_m=h,**out['summary']);summaries.append(row)
    for k,ident in enumerate(ids):
     L=out['L'][k];sk=a['SigmaState_kk'][soil][k];si=a['SigmaState_ij'][soil][k];particles.append(dict(part=part,time_s=time,tau_s=tau,native_id=int(ident),x_m=float(x[k,0]),z_m=float(x[k,1]),vx_m_s=float(v[k,0]),vz_m_s=float(v[k,1]),V_area_m2=float(V[k]),rho_kg_m3=float(rho[k]),mass_per_depth_kg_m=float(V[k]*rho[k]),neighbors=int(g['degree'][k]),LS_smax=float(g['s'][k,0]),LS_smin=float(g['s'][k,1]),LS_numerical_rank=int(g['rank'][k]),LS_condition=float(g['condition'][k]),LS_normal_relative_defect=float(out['normal_relative'][k]),Lxx_s_1=float(L[0,0]),Lxz_s_1=float(L[0,1]),Lzx_s_1=float(L[1,0]),Lzz_s_1=float(L[1,1]),Dxx_s_1=float(L[0,0]),Dxz_s_1=float(.5*(L[0,1]+L[1,0])),Dzz_s_1=float(L[1,1]),spin_xz_s_1=float(.5*(L[0,1]-L[1,0])),force_rate_x_N_per_m_s=float(out['force'][k,0]),force_rate_z_N_per_m_s=float(out['force'][k,1]),acceleration_rate_x_m_s3=float(out['jerk'][k,0]),acceleration_rate_z_m_s3=float(out['jerk'][k,1]),lambda_bound_unit_xi_s_2=float(out['lambda_bound'][k]),p_Pa=float(a['PorePress'][soil,0][k]),kappa=float(a['Kplastic'][soil,0][k]),J=float(a['PoroVolumeRatio'][soil,0][k]),n=float(a['PoroPorosity'][soil,0][k]),k_m_s=float(a['PoroHydraulicConductivity'][soil,0][k]),saved_FS=int(a['FSType'][soil,0][k]),saved_last_stage_theta_s_1=float(a['PoroThetaLastStage'][soil,0][k]),sigma_eff_xx_Pa=float(sk[0]),sigma_eff_yy_Pa=float(sk[1]),sigma_eff_zz_Pa=float(sk[2]),sigma_eff_xy_Pa=float(si[0]),sigma_eff_yz_Pa=float(si[1]),sigma_eff_xz_Pa=float(si[2])))
    for idi,idj in ((7011,7012),(6230,6231)):
     i,j=idi-2060,idj-2060;d=x[i]-x[j];distance=float(np.linalg.norm(d));normal=d/distance;relative=out['jerk'][i]-out['jerk'][j];pairrows.append(dict(part=part,time_s=time,tau_s=tau,id_i=idi,id_j=idj,r_m=distance,rdot_over_r_s_1=float((v[i]-v[j])@normal/distance),complete_graph_relative_jerk_normal_m_s3=float(relative@normal),relative_jerk_x_m_s3=float(relative[0]),relative_jerk_z_m_s3=float(relative[1]),hypothetical_xi02_relative_jerk_normal_m_s3=float(.2*relative@normal)))
     mid=.5*(x[i]+x[j]);mask=(np.linalg.norm(x-x[i],axis=1)<2*h)|(np.linalg.norm(x-x[j],axis=1)<2*h);wall=a['Posd'][~soil][:,(0,2)]-mid;wall=wall[np.linalg.norm(wall,axis=1)<3*h];panels.append(dict(part=part,tau=tau,pair=(idi,idj),x=x[mask]-mid,rate=out['jerk'][mask],p=a['PorePress'][soil,0][mask],centers=x[[i,j]]-mid,wall=wall))
    centered=x-x.mean(axis=0);cases=(('constant',np.broadcast_to(np.array([.2,-.1]),v.shape).copy()),('affine',centered@np.array([[.7,.2],[-.3,-.4]]).T+np.array([.11,-.07])),('rigid_rotation',centered@np.array([[0.,-1.],[1.,0.]]).T))
    for name,vtest in cases:manufactures.append(dict(part=part,time_s=time,tau_s=tau,manufacture=name,expected_exact_force_rate_zero=True,**shadow(x,vtest,V,rho,G,g)['summary']))
  for key,rows in [('summary',summaries),('particles',particles),('pairs',pairrows),('manufactures',manufactures)]:write(paths[key],rows)
  vmax=max(float(np.linalg.norm(q['rate'],axis=1).max()) for q in panels);scale=vmax/(.35*h) if vmax>0 else 1.;pressure=np.concatenate([q['p'] for q in panels]);norm=Normalize(vmin=float(pressure.min()),vmax=float(pressure.max()));fig,axes=plt.subplots(2,2,figsize=(11,9),layout='constrained')
  for ax,q in zip(axes.flat,panels):
   x=q['x'];rate=q['rate'];ax.scatter(q['wall'][:,0],q['wall'][:,1],s=12,c='.65',marker='s');im=ax.scatter(x[:,0],x[:,1],c=q['p'],norm=norm,cmap='coolwarm',s=25);quiv=ax.quiver(x[:,0],x[:,1],rate[:,0],rate[:,1],angles='xy',scale_units='xy',scale=scale,color='k',width=.004);ax.scatter(q['centers'][:,0],q['centers'][:,1],s=110,facecolors='none',edgecolors='limegreen',linewidths=1.5);ax.set_aspect('equal');ax.set(xlim=(-2.7*h,2.7*h),ylim=(-2.7*h,2.7*h),xlabel='x-pair_midpoint [m]',ylabel='z-pair_midpoint [m]',title=f"IDs{q['pair']} tau={q['tau']:.9f}s")
  if vmax>0:axes[1,0].quiverkey(quiv,.05,-.13,vmax,f'{vmax:.4g} m/s³; unit xi',coordinates='axes',labelpos='E')
  fig.colorbar(im,ax=axes,label='Actual saved pore pressure [Pa]');fig.suptitle('Complete soil graph Cubic matched-LS elastic force-RATE shadow\nCommon jerk-arrow scale; grey fixed positions are excluded; no acceleration/history is applied');fig.savefig(paths['rates'],dpi=170);plt.close(fig)
  need(len(summaries)==2 and len(particles)==10000 and len(pairrows)==4 and len(manufactures)==6 and all(stat(q['path'])==q for q in before),'Coverage or consumed source changed');e.save(CHECK,dict(stage=TAG,passed=True,source_native=stat(npth),source_gradient_check=stat(gp),actual_native_records_read=2,source_parts=list(PARTS),soil_IDs=5000,shadow_xi=1,hypothetical_xi=.2,G_from_actual_Run_Pa=G,complete_soil_pair_graph=True,regularization=False,plastic_gamma_used=False,force_rate_not_acceleration=True,force_history_integrated=False,torque_not_assumed_pairwise_central=True,physical_acceptance=False,solver_invocations=0,actual_force_evaluations=0,native_decodes=0,SHA_scans=0,consumed=before,consumed_stats_unchanged=True,outputs=[stat(p) for p in paths.values()]));print('CUBIC_RESIDUAL_RATE_SHADOW_PASSED',CHECK,flush=True)
 except Exception as error:
  if not CHECK.exists():e.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(error),partial_outputs_preserved=True,physical_acceptance=False,solver_invocations=0,actual_force_evaluations=0,native_decodes=0,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root reads this offline force-rate shadow');run()
