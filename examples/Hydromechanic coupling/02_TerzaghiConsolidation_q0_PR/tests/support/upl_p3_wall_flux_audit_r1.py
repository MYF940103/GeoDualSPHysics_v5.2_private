import numpy as np, pathlib, csv, json, math, hashlib, sys, platform
# Offline diagnostic only. Never calls a solver or edits retained input/output.
# State fields are the failed r3 trajectory; all four closures are frozen-field
# counterfactuals, not separately integrated solutions. No posthoc physics gate.
def entry(p):
 p=pathlib.Path(p);b=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def require(ok,text):
 if not ok:raise RuntimeError(text)
base=pathlib.Path(__file__).resolve().parents[1]
check=base/'logs/upl_p3_wall_flux_audit_r1.check.json'
result_csv=base/'figures/upl_p3_wall_flux_audit_r1.csv'
require(not check.exists() and not result_csv.exists(),'Retained analysis protected; use a new reviewed revision')
freeze_path=base/'logs/upl_p3_wall_build_r2.json'
freeze=json.loads(freeze_path.read_text(encoding='utf-8-sig'))
run_path=base/'logs/upl_p3_wall_wave_ReleaseCPU_r3_k1_c.run.json'
run=json.loads(run_path.read_text(encoding='utf-8-sig'))
require(run['exit_code']==1 and run['owned_call_exited'],'Expected retired failed r3 owned exit1')
build_path=base/'logs/upl_p3_wall_wave_ReleaseCPU_r3.build.json'
build=json.loads(build_path.read_text(encoding='utf-8-sig'))
inputs=[pathlib.Path(__file__),freeze_path,run_path,build_path,pathlib.Path(run['program']['path']),pathlib.Path(run['log']['path'])]+[pathlib.Path(v['snapshot']['path']) for v in freeze['source']]
for v in freeze['source']:
 require(entry(v['snapshot']['path'])==v['snapshot'],'Frozen source snapshot changed')
require(entry(run['program']['path'])==run['program'],'Retained program hash changed')
require(entry(run['log']['path'])==run['log'],'Retained run log hash changed')
o=base/'outputs/upl_p3_wall_wave_ReleaseCPU_r3_k1_c'
inputs += [o/v for v in ['physical.bin','native_ids.csv','fixed_ids.csv','modes.csv','wall_audit.csv','endpoint_policy.csv','component.check.json','component.csv','Run.out']]
inputs += [pathlib.Path(v['path']) for v in build['snapshots']]
before=[entry(p) for p in sorted(set(inputs))]
for v in build['snapshots']:require(entry(v['path'])==v,'Archived recipe changed')
data=(o/'physical.bin').read_bytes(); header=np.frombuffer(data[:12],'<u4'); framebytes=8+1024*26*8
frames=(len(data)-12)//framebytes
require((len(data)-12)%framebytes==0 and header.tolist()==[1024,26,257] and frames==11,'Expected 11 complete frames of interrupted 257-frame plan')
require(not (o/'complete.json').exists(),'Failed trajectory was incorrectly marked complete')
native=list(csv.DictReader((o/'native_ids.csv').open()))
require([int(v['native_id']) for v in native]==list(range(256,1280)),'Native material row IDs changed')
recorded=list(csv.DictReader((o/'wall_audit.csv').open()))
recorded_by={(int(v['step']),float(v['plane_x'])):v for v in recorded}
require(len(recorded)==20 and max(int(v['step']) for v in recorded)==36,'Expected two recorded faces through step36 only')
raw=np.frombuffer(data[12:],'<f8').reshape(frames,1+1024*26)
wall=list(csv.DictReader((o/'fixed_ids.csv').open())); wx=np.array([[float(v['x0']),float(v['z0'])] for v in wall])
dp=1/512;W=L=1/16;f=np.float32;h=f(1.8*dp);ks2=float(f(f(2)*h)*f(f(2)*h));V0=dp*dp;aw=f(.557/float(h)**2);bw=f(-2.7852/float(h)**3);kh=float(f(.0001));gamma=1000*9.80665
target=wx.copy();target[:,0]=np.where(wx[:,0]<0,-wx[:,0],2*W-wx[:,0])
def kern(d,force=False):
 if force:d=d.astype('f4').astype(float);rr=(d[:,0].astype('f4')**2+d[:,1].astype('f4')**2).astype('f4')
 else:rr=np.sum(d*d,axis=1).astype('f4')
 rad=np.sqrt(rr).astype('f4');q=(rad/h).astype('f4');one=(f(1)-f(.5)*q).astype('f4');two=(one*one).astype('f4')
 wab=(((aw*((q+q).astype('f4')+f(1)))*two)*two).astype('f4')
 with np.errstate(invalid='ignore',divide='ignore'):fac=(((bw*q)*two)*one/rad).astype('f4')
 fac[rr==0]=0
 if force:g=(fac[:,None]*d.astype('f4')).astype('f4').astype(float)
 else:g=fac[:,None].astype(float)*d
 return rr,wab.astype(float),g
def clone(x,y):
 return np.concatenate([x+np.array([0,t]) for t in [-L,0,L]]),np.tile(y,(3,1))
def fit_targets(x,fields,V,anchor):
 xc,fc=clone(x,fields);vc=np.tile(V,3);out=[]
 for t in target:
  d=t-xc;rr,w,g=kern(d);mask=rr<=ks2;d=d[mask];w=w[mask]*vc[mask];g=g[mask]*vc[mask,None];ff=fc[mask]
  mat=np.array([[sum(w),sum(d[:,0]*w),sum(d[:,1]*w)],[sum(g[:,0]),sum(d[:,0]*g[:,0]),sum(d[:,1]*g[:,0])],[sum(g[:,1]),sum(d[:,0]*g[:,1]),sum(d[:,1]*g[:,1])]])
  rhs=np.vstack([w@ff,g[:,0]@ff,g[:,1]@ff]);sol=np.linalg.solve(mat,rhs)
  near=np.argmin(np.sum(d*d,axis=1));val=ff[near]-d[near,0]*sol[1]-d[near,1]*sol[2] if anchor else sol[0]
  out.append(val)
 return np.array(out)
def acceleration(x,r,ws):
 # State columns J,p,vx,vz,sxx,sxz,szz; reflection affects xz, not xx/zz.
 st=ws.copy();st[:,1]=st[:,1].astype('f4').astype(float);st[:,2]=(-st[:,2]).astype('f4').astype(float);st[:,3]=st[:,3].astype('f4').astype(float);st[:,5]*=-1
 xs=np.concatenate([x,wx]);stf=np.column_stack([r[:,8],r[:,6],r[:,3],r[:,5],r[:,10],r[:,12],r[:,15]])
 sf=np.concatenate([stf,st]);xx,ss=clone(xs,sf);acc=np.zeros((len(x),2),dtype='f4')
 for i,t in enumerate(x):
  d=t-xx;rr,w,g=kern(d,True);mask=(rr>=1e-18)&(rr<=ks2);p=ss[mask];gg=g[mask];rho=1000+1048/r[i,8]
  coeff=V0*p[:,0]/rho;pw=r[i,6]+p[:,1];sxx=float(f(r[i,10]))+p[:,4].astype('f4').astype(float)-pw
  sxz=float(f(r[i,12]))+p[:,5].astype('f4').astype(float);szz=float(f(r[i,15]))+p[:,6].astype('f4').astype(float)-pw
  terms=np.column_stack([coeff*(sxx*gg[:,0]+sxz*gg[:,1]),coeff*(szz*gg[:,1]+sxz*gg[:,0])]).astype('f4')
  acc[i]=np.sum(terms.astype(float),axis=0).astype('f4')
 return acc.astype(float),st
def face(x,r,st,ac,awall,side):
 xs=np.concatenate([x,wx]);ss=np.column_stack([np.r_[r[:,8],st[:,0]],np.r_[r[:,6],st[:,1]],np.r_[r[:,3],st[:,2]],np.r_[ac[:,0],awall[:,0]]]);xx,s=clone(xs,ss)
 pt=np.array([W if side else 0,L*.5]);d=xx-pt;rr,w,g=kern(d);mask=rr<=ks2;d=d[mask];s=s[mask];weights=V0*s[:,0]*w[mask];b=np.column_stack([np.ones(len(d)),d/h])
 mat=(b*weights[:,None]).T@b;sol=np.linalg.solve(mat,(b*weights[:,None]).T@s[:,1:]);gp=sol[1,0]/h;ap=sol[0,2];vn=sol[0,1]*( -1 if side else 1)
 alpha=weights*(np.linalg.inv(mat)[1]@b.T)/h
 beta=weights*(np.linalg.inv(mat)[0]@b.T)
 cu=math.sqrt((89478488+4*134217728/3+67108864/.25)/2048);A=1/512;k=2*math.pi/.125;ps=67108864/.25*A/cu
 am=max(A*cu*k,float(max(abs(s[:,3]))));pm=max(1,float(max(abs(s[:,1]))));gs=float(sum(abs(alpha*s[:,1])))
 condition=max(1,float(np.linalg.norm(mat,np.inf)*np.linalg.norm(np.linalg.inv(mat),np.inf)))
 qs=kh/gamma*(k*ps+1000*A*cu*k)
 bq=kh/gamma*(2*np.finfo('f4').eps*pm*sum(abs(alpha))+4*1000*np.finfo('f4').eps*am*sum(abs(beta))+4096*np.finfo('f8').eps*condition*(gs+1000*am))+1e-4*qs
 return dict(q=-kh/gamma*(gp+1000*ap)*(-1 if side else 1),gp=gp,ra=1000*ap,vn=vn,original_qn_budget=bq,q_over_original_budget=abs(kh/gamma*(gp+1000*ap))/bq)
results=[]
for idx in range(frames):
 t=raw[idx,0];r=raw[idx,1:].reshape(1024,26);x=r[:,[0,2]];fields=np.column_stack([r[:,8],r[:,6],r[:,3],r[:,5],r[:,10],r[:,12],r[:,15]])
 old=fit_targets(x,fields,V0*r[:,8],False);new=fit_targets(x,fields,V0*r[:,8],True);bias=old-new
 variants={}
 for stateanchor,aceanchor in [(False,False),(True,False),(False,True),(True,True)]:
  st0=new if stateanchor else old;ac,st=acceleration(x,r,st0);av=fit_targets(x,ac,V0*r[:,8],aceanchor);av[:,0]*=-1;av=av.astype('f4').astype(float)
  key=('anchor' if stateanchor else 'std')+'_state_'+('anchor' if aceanchor else 'std')+'_ace'
  variants[key]=[face(x,r,st,ac,av,s) for s in [0,1]]
 results.append(dict(saved_index=idx,step=idx*4,t=t,max_p_MLS_anchor_abs=float(max(abs(bias[:,1]))),max_vx_MLS_anchor_abs=float(max(abs(bias[:,2]))),max_sxx_MLS_anchor_abs=float(max(abs(bias[:,4]))),variants=variants))
rows=[];record_errors=[]
for r in results:
 for variant,faces in r['variants'].items():
  for side,vals in enumerate(faces):
   plane=W if side else 0;obs=recorded_by.get((r['step'],plane));residual=None
   if obs is not None and variant=='std_state_std_ace':
    residual=vals['q']-float(obs['face_qn']);record_errors.append(abs(residual))
   row=dict(step=r['step'],actual_time_s=r['t'],variant=variant,plane_x=plane,**vals,recorded_qn=None if obs is None else float(obs['face_qn']),reconstruction_minus_recorded_qn=residual,max_p_MLS_minus_anchor_abs_Pa=r['max_p_MLS_anchor_abs'],max_vx_MLS_minus_anchor_abs_mps=r['max_vx_MLS_anchor_abs'],max_sxx_MLS_minus_anchor_abs_Pa=r['max_sxx_MLS_anchor_abs'])
   require(all(math.isfinite(v) for v in row.values() if isinstance(v,(float,int))),'Nonfinite offline reconstruction');rows.append(row)
last=results[-1];face_std=last['variants']['std_state_std_ace'][0]
require(raw[-1,0]==40*2**-25 and len(rows)==88,'Wrong actual frame/counterfactual coverage')
with result_csv.open('x',newline='',encoding='utf-8') as outcsv:
 writer=csv.DictWriter(outcsv,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
after=[entry(p) for p in sorted(set(inputs))]
require(before==after,'Input changed during offline analysis')
report=dict(passed=True,scope='offline_frozen_fluid_state_wall_closure_attribution_only',solver_started=False,production_source_changed=False,physical_acceptance=False,coupled_candidate_acceptance=False,
 provenance=dict(python=sys.version,numpy=np.__version__,platform=platform.platform()),inputs=before,
 failed_original=dict(exit_code=run['exit_code'],owned_call_exited=run['owned_call_exited'],native_ids=1024,native_material_id_range=[256,1279],fixed_ids=256,planned_samples=257,complete_native_frames=frames,actual_saved_end_s=float(raw[-1,0]),actual_saved_step=40,wall_audit_last_passed_step=36,failed_check='Independent physical-plane Darcy flux bound',no_half_launched=True,complete_manifest_present=False),
 method=dict(fields='Original 26 native columns; construct z translations by +/-1/16 and two fixed native planes from retained ID tables',state_MLS='Same frozen generic 3x3 W/gradient matrix; W(0) retained with zero gradient; Vj=dp^2 J; scalars even and x velocity/xz stress odd',
 counterfactuals=['std state + std Ace','anchor state + std Ace','std state + anchor Ace','anchor state + anchor Ace'],
 anchor='Keep the same MLS negative-gradient coefficients; replace target intercept by nearest native sample minus qx*(target_x-nearest_x)-qz*(target_z-nearest_z). This reproduces affine fields and a coincident sample.',
 momentum='Same 2D raw kernel-gradient total-stress terms with per-pair float cast, double sum and final float cast. O(N^2) ID-ordered replay is not the real cell-list accumulation order.',
 face='Independent full-support physical-plane linear fit using all native fluid/fixed samples and z copies, same prior 1e-4 characteristic truncation budget and original float rounding formula',
 gate='Input hashes, failed-state schema/ID/time coverage, finite arithmetic only. Reconstruction-vs-native discrepancies and all counterfactual values are diagnostic, not new posthoc physical gates.'),
 metrics=dict(csv_rows=len(rows),native_recorded_face_comparisons=len(record_errors),max_reconstructed_std_qn_minus_native_abs_mps=max(record_errors),last_step_max_p_MLS_anchor_abs_Pa=last['max_p_MLS_anchor_abs'],last_step_max_vx_MLS_anchor_abs_mps=last['max_vx_MLS_anchor_abs'],last_step_max_sxx_MLS_anchor_abs_Pa=last['max_sxx_MLS_anchor_abs'],last_step_left_standard=face_std,last_step_left_anchor_state=last['variants']['anchor_state_std_ace'][0],last_step_left_anchor_Ace=last['variants']['std_state_anchor_ace'][0],last_step_left_both_anchor=last['variants']['anchor_state_anchor_ace'][0],last_step_pressure_gradient_fraction_abs=abs(face_std['gp'])/(abs(face_std['gp'])+abs(face_std['ra']))),
 limits=['No actual production helper invocation, force-call lifecycle or cell-list equality proof.','No new integrated trajectory: all variants reuse the same already-failed fluid fields; causal feedback over later times remains untested.','No budget relaxation, filtering, time interpolation, rewritten native data, full wave completion, independent half-step or physical wall acceptance.','The failed binary header still announces257 planned frames but contains only11 complete frames; the final step40 native state exists although its audit check rejected before writing either step40 face row.','Old source snapshots and archived recipes, not changing current production source, are the mathematical/source provenance for the failed standard-MLS run.'],
 conclusion='The frozen-field evidence attributes >99 percent of the step40 face gradient/acceleration residual to scalar ghost MLS smoothing that does not interpolate its coincident native sample. Only anchoring Ace changes little; anchoring state removes nearly all of the reconstructed defect. This justifies a bounded actual anchored-closure test, not admission of the candidate.',
 results=results,result_csv=entry(result_csv))
with check.open('x',encoding='utf-8') as outjson:json.dump(report,outjson,indent=2);outjson.write('\n')
print(json.dumps(dict(passed=True,check=entry(check),csv=entry(result_csv),metrics=report['metrics']),indent=2))

