"""Eight soil-only instantaneous affine velocity fits from two sealed native records; no tools."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,csv,json,struct,xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_pair_localfit_r1';P=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json')
JOB='upl_c08_causal_window_GPU_r1';FOCUS=(7011,7012,6230,6231);PARTS=(13,14);N=6805
need,read,stat,bind=e.need,e.read,e.stat,e.bind
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def fit(x,v,volume,center,h):
 dx=x-x[center];r=np.linalg.norm(dx,axis=1);select=np.flatnonzero(r<2*h);q=r[select]/h
 # The positive Cubic normalization cancels from every weighted fit/normalized metric.
 w=np.where(q<=1,1-1.5*q*q+.75*q*q*q,.25*(2-q)**3)*volume[select]
 design=np.column_stack((np.ones(len(select)),dx[select]/h));A=design*np.sqrt(w[:,None]);Y=v[select]*np.sqrt(w[:,None])
 rcond=np.finfo(float).eps*max(A.shape);coef,_,rank,singular=np.linalg.lstsq(A,Y,rcond=rcond)
 predicted=design@coef;residual=v[select]-predicted;L=coef[1:].T/h;energy=w*np.sum(residual*residual,axis=1);total=float(energy.sum());center_local=int(np.flatnonzero(select==center)[0])
 distance=np.linalg.norm(x[select,None]-x[None,select],axis=2);np.fill_diagonal(distance,np.inf);nn=np.argmin(distance,axis=1);edges=sorted({tuple(sorted((i,int(j)))) for i,j in enumerate(nn)})
 dot=np.array([residual[i]@residual[j] for i,j in edges]);ew=np.array([np.sqrt(w[i]*w[j]) for i,j in edges]);den=float(sum(ew[k]*np.linalg.norm(residual[i])*np.linalg.norm(residual[j]) for k,(i,j) in enumerate(edges)))
 metric=dict(neighbors_including_self=len(select),svd_rank=int(rank),affine_solution_unique=bool(rank==3),svd_rcond=rcond,svd_s0=float(singular[0]),svd_s1=float(singular[1]),svd_s2=float(singular[2]),condition_scaled_design=float(singular[0]/singular[-1]) if singular[-1]>0 else None,effective_weighted_count=float(w.sum()**2/(w@w)),weighted_residual_RMS_m_s=float(np.sqrt(total/w.sum())),max_residual_m_s=float(np.linalg.norm(residual,axis=1).max()),center_residual_m_s=float(np.linalg.norm(residual[center_local])),center_weighted_SSE_fraction=float(energy[center_local]/total) if total>0 else None,max_single_weighted_SSE_fraction=float(energy.max()/total) if total>0 else None,nearest_edges=len(edges),nearest_edge_negative_dot_fraction=float(np.mean(dot<0)),nearest_edge_residual_alignment=float(ew@dot/den) if den>0 else None)
 return dict(select=select,weight=w,residual=residual,predicted=predicted,L=L,intercept=coef[0],metric=metric,center_local=center_local,edges=edges)
def run():
 paths={k:Path(str(P)+'_'+k+s) for k,s in [('fits','.csv'),('neighbors','.csv'),('pairs','.csv'),('residuals','.png')]};need(not CHECK.exists() and all(not p.exists() for p in paths.values()),'Existing complete/partial analysis protected');before=[]
 try:
  npth=T/'logs'/(JOB+'.native_r1.json');gp=T/'logs/upl_c08_pair_gradient_cpu_r1.check.json';n,g=read(npth),read(gp);rp=Path(n['source_run']['path']);r=read(rp)
  need(n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1 and n['source_run']==stat(rp) and r['passed'] and r['actual_steps']==4360000 and r['saved_frames']==90,'Closed actual causal90 run/native required')
  need(g['passed'] and g['consumed_stats_unchanged'] and g['source_native']==stat(npth) and g['force_evaluations']==2 and g['actual_physical_steps']==0 and g['full_velocity_gradient_observed'] and g['gradient_observed_IDs']==list(FOCUS) and g['baseline_alignment']['mismatched_fields']==0,'Passed actual CPU gradient source/alignment required')
  done=read(bind(n['completion'])['path']);native=Path(n['completion']['path']).parent;need(done['passed'] and done['stage']=='upl_c08_causal_native_r1' and done['samples']==90 and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==N,'Original normal90/22/6805 profile required')
  before=[stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(e.__file__),stat(npth),stat(gp),bind(n['source_run']),bind(n['completion']),bind(n['metadata']),bind(g['component_completion']),bind(g['source_prefix_proof']),bind(r['input_xml'])]
  bound={Path(q['path']).name:q for q in n['outputs']};before += [bind(bound[k]) for k in ('typed22.bin','typed22_layout.csv','clocks.csv')];focusentry=next(q for q in g['files'] if Path(q['path']).name=='focus.csv');before.append(bind(focusentry));sph={(int(q['part']),int(q['native_id'])):q for q in table(focusentry['path'])};need(len(sph)==8,'Exactly eight observed SPH gradients required')
  xml=ET.parse(r['input_xml']['path']).getroot();hnode=xml.find('execution/constants/h');need(hnode is not None,'Actual generated kernel h missing');h=float(np.float32(float(hnode.get('value'))));need(h==float(np.float32(.048)),'Only the original Cubic h1.2 profile is admitted');radius=2*h
  layout=table(native/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Original22 layout required')
  for q in layout:
   dt={'uint32':'<u4','float32':'<f4','float64':'<f8'}[q['type']];width=int(q['components']);need(np.dtype(dt).itemsize*width==int(q['bytes_per_particle']),'Bound native layout byte width differs');fields.append((q['array'],dt,(N,width)))
  dtype=np.dtype(fields);raw=native/'typed22.bin';need(dtype.itemsize==8+N*212 and raw.stat().st_size==12+90*dtype.itemsize,'Original90 typed extent differs');clocks=table(native/'clocks.csv');need(len(clocks)==90,'Original90 clock rows required');source_time=float(done['source_actual_time_s'])
  expected=np.sort(np.r_[np.arange(1800),(1800,1852,1904,1956,2008),np.arange(2060,7060)]).astype('<u4');fits=[];neighbors=[];pairrows=[];panels=[]
  with raw.open('rb') as f:
   need(struct.unpack('<III',f.read(12))==(N,22,90),'Preserve the actual90 header')
   for part in PARTS:
    f.seek(12+part*dtype.itemsize);a=np.fromfile(f,dtype=dtype,count=1)[0];time=float(a['time']);clock=clocks[part];need(np.array_equal(a['Idp'][:,0],expected) and int(clock['completed_step'])==4000000+4000*(part+1) and struct.pack('<d',time)==struct.pack('<d',float(clock['time_s'])),'Actual ID/time/step alignment differs')
    for q in layout:need(np.isfinite(a[q['array']]).all(),'Nonfinite selected native field')
    soil=a['Idp'][:,0]>=2060;ids=a['Idp'][soil,0];need(np.array_equal(ids,np.arange(2060,7060)),'Exactly5000 material soil IDs required');x=a['Posd'][soil][:,(0,2)];v=a['Vel'][soil][:,(0,2)].astype(float);V=a['PoroCurrentVolume'][soil,0];need((V>0).all(),'Positive actual quadrature volumes required');results={}
    for ident in FOCUS:
     center=int(ident-2060);z=fit(x,v,V,center,h);results[ident]=z;obs=sph[part,ident];need(float(obs['time_s'])==time and float(obs['x_m'])==x[center,0] and float(obs['z_m'])==x[center,1] and float(obs['vx_m_s'])==v[center,0] and float(obs['vz_m_s'])==v[center,1],'Native and observed SPH center state differs')
     Ls=np.array([[float(obs['L_sum_'+i+j]) for j in ('x','z')] for i in ('x','z')]);row=dict(part=part,time_s=time,tau_s=time-source_time,completed_step=int(clock['completed_step']),native_id=ident,fit_scope='soil_only',h_m=h,**z['metric'])
     row.update(fitted_v0x_m_s=float(z['intercept'][0]),fitted_v0z_m_s=float(z['intercept'][1]),center_p_Pa=float(a['PorePress'][soil,0][center]),center_kappa=float(a['Kplastic'][soil,0][center]),center_J=float(a['PoroVolumeRatio'][soil,0][center]),center_k_m_s=float(a['PoroHydraulicConductivity'][soil,0][center]),center_saved_FS=int(a['FSType'][soil,0][center]),center_actual_SPH_FS=int(obs['actual_FS']),SPH_theta_s_1=float(obs['theta_s_1']))
     for i,axis in enumerate(('x','z')):
      for j,direction in enumerate(('x','z')):row['fit_L'+axis+direction+'_s_1']=float(z['L'][i,j]);row['SPH_mixed_L'+axis+direction+'_s_1']=float(Ls[i,j])
     fits.append(row);context={name:a[name][soil] for name in ('PorePress','PoroVolumeRatio','PoroHydraulicConductivity','Kplastic','FSType','SigmaState_kk','SigmaState_ij')}
     for k,j in enumerate(z['select']):
      sk=context['SigmaState_kk'][j];si=context['SigmaState_ij'][j];er=z['residual'][k];neighbors.append(dict(part=part,time_s=time,tau_s=time-source_time,focus_id=ident,native_id=int(ids[j]),x_m=float(x[j,0]),z_m=float(x[j,1]),dx_m=float(x[j,0]-x[center,0]),dz_m=float(x[j,1]-x[center,1]),weight_Wshape_times_actualV=float(z['weight'][k]),vx_m_s=float(v[j,0]),vz_m_s=float(v[j,1]),fitted_vx_m_s=float(z['predicted'][k,0]),fitted_vz_m_s=float(z['predicted'][k,1]),residual_vx_m_s=float(er[0]),residual_vz_m_s=float(er[1]),p_Pa=float(context['PorePress'][j,0]),kappa=float(context['Kplastic'][j,0]),J=float(context['PoroVolumeRatio'][j,0]),k_m_s=float(context['PoroHydraulicConductivity'][j,0]),saved_FS=int(context['FSType'][j,0]),sigma_eff_xx_Pa=float(sk[0]),sigma_eff_yy_Pa=float(sk[1]),sigma_eff_zz_Pa=float(sk[2]),sigma_eff_xy_Pa=float(si[0]),sigma_eff_yz_Pa=float(si[1]),sigma_eff_xz_Pa=float(si[2]),total_trace_Pa=float(sk.sum()-3*context['PorePress'][j,0])))
     wall=a['Posd'][~soil][:,(0,2)]-x[center];wall=wall[np.linalg.norm(wall,axis=1)<radius];panels.append(dict(row=row,xy=x[z['select']]-x[center],residual=z['residual'],p=context['PorePress'][z['select'],0],wall=wall,center_local=z['center_local']))
    for idi,idj in ((7011,7012),(6230,6231)):
     i,j=idi-2060,idj-2060;dx=x[i]-x[j];dv=v[i]-v[j];distance=float(np.linalg.norm(dx));normal=dx/distance;Li,Lj=results[idi]['L'],results[idj]['L'];Ls=[]
     for ident in (idi,idj):obs=sph[part,ident];Ls.append(np.array([[float(obs['L_sum_'+u+w]) for w in ('x','z')] for u in ('x','z')]))
     residual=dv-.5*(Li+Lj)@dx;pairrow=dict(part=part,time_s=time,tau_s=time-source_time,id_i=idi,id_j=idj,r_m=distance,rdot_over_r_s_1=float(dv@normal/distance),soil_fit_mean_direction_s_1=float(normal@(.5*(Li+Lj))@normal),SPH_mixed_mean_direction_s_1=float(normal@(.5*(Ls[0]+Ls[1]))@normal),soil_fit_pair_residual_x_m_s=float(residual[0]),soil_fit_pair_residual_z_m_s=float(residual[1]),soil_fit_pair_residual_norm_m_s=float(np.linalg.norm(residual)))
     for focus,partner,label in ((idi,idj,'i_fit'),(idj,idi,'j_fit')):
      z=results[focus];ki=int(np.flatnonzero(z['select']==focus-2060)[0]);kj=int(np.flatnonzero(z['select']==partner-2060)[0]);pairrow[label+'_center_residual_m_s']=float(np.linalg.norm(z['residual'][ki]));pairrow[label+'_partner_residual_m_s']=float(np.linalg.norm(z['residual'][kj]));pairrow[label+'_center_partner_residual_dot_m2_s2']=float(z['residual'][ki]@z['residual'][kj])
     pairrows.append(pairrow)
  for key,rows in [('fits',fits),('neighbors',neighbors),('pairs',pairrows)]:write(paths[key],rows)
  vmax=max(float(np.linalg.norm(q['residual'],axis=1).max()) for q in panels);pressure=np.concatenate([q['p'] for q in panels]);norm=Normalize(vmin=float(pressure.min()),vmax=float(pressure.max()));scale=vmax/(.3*radius) if vmax>0 else 1.;fig,axes=plt.subplots(2,4,figsize=(15,8),layout='constrained')
  for ax,q in zip(axes.flat,panels):
   xy=q['xy'];rr=q['residual'];ax.scatter(q['wall'][:,0],q['wall'][:,1],s=12,c='.65',marker='s');im=ax.scatter(xy[:,0],xy[:,1],c=q['p'],norm=norm,cmap='coolwarm',s=26);quiver=ax.quiver(xy[:,0],xy[:,1],rr[:,0],rr[:,1],angles='xy',scale_units='xy',scale=scale,color='k',width=.004);ax.scatter([0],[0],s=110,facecolors='none',edgecolors='limegreen',linewidths=1.5);ax.set(xlim=(-radius,radius),ylim=(-radius,radius),xlabel='x-x_focus [m]',ylabel='z-z_focus [m]');ax.set_aspect('equal');row=q['row'];ax.set_title(f"ID{row['native_id']} tau={row['tau_s']:.9f}s\np={row['center_p_Pa']:.0f} Pa; kappa={row['center_kappa']:.3g}; J={row['center_J']:.6g}; FS={row['center_saved_FS']}",fontsize=9)
  if vmax>0:axes[1,0].quiverkey(quiver,.1,-.13,vmax,f'{vmax:.4g} m/s',coordinates='axes',labelpos='E')
  fig.colorbar(im,ax=axes,label='Actual saved pore pressure [Pa]');fig.suptitle('Soil-only Cubic W*actual V affine-fit residual velocities; common arrow scale\nGrey fixed positions are excluded from the fit; no wall derivative velocities invented');fig.savefig(paths['residuals'],dpi=170);plt.close(fig)
  need(len(fits)==8 and len(pairrows)==4 and all(stat(q['path'])==q for q in before),'Coverage or consumed input changed');e.save(CHECK,dict(stage=TAG,passed=True,source_native=stat(npth),source_gradient_check=stat(gp),selected_parts=list(PARTS),focus_IDs=list(FOCUS),actual_native_records_read=2,fit_count=8,fit_scope='soil_only',wall_derivative_velocities_available=False,rank_deficient_fits=sum(not q['affine_solution_unique'] for q in fits),support_radius_m=radius,arrow_scale_m_s_per_m=scale,max_residual_arrow_m_s=vmax,physical_acceptance=False,hourglass_cause_claimed=False,solver_invocations=0,native_decodes=0,force_evaluations=0,SHA_scans=0,consumed=before,consumed_stats_unchanged=True,outputs=[stat(p) for p in paths.values()]));print('PAIR_LOCALFIT_PASSED',CHECK,flush=True)
 except Exception as error:
  if not CHECK.exists():e.save(CHECK,dict(stage=TAG,passed=False,first_failure=str(error),partial_outputs_preserved=True,physical_acceptance=False,solver_invocations=0,native_decodes=0,force_evaluations=0,consumed=before,SHA_scans=0))
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root full-read and one offline invocation');run()
