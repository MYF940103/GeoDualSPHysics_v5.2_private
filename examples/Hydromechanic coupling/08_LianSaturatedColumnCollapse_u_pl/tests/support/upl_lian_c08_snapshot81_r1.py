"""One closed C08 snapshot,81 receivers: reconstructed-C geometry diagnostics only."""
import argparse,csv,importlib.util,json,math,struct,xml.etree.ElementTree as ET
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree
from upl_c08_fsmask_r1 import SCHEMA,TYPES,need
T=Path(__file__).resolve().parents[1];TAG='upl_lian_c08_snapshot81_r1';N,FIXED,PART=7060,2060,1000
D=T/'outputs/upl_prestress10_CPU_r1_native_r1'
SEED=T/'outputs/upl_gravity_release_preload10_r1_seed/CaseLianSaturatedColumnCollapse_prestress10_r1'
REF=T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_lian_eq23_reference_r1.py'
FIELDS=('constant','linear_x','linear_z','quadratic_x','quadratic_z','quadratic_xz','quadratic_tracezero','sine')
VARIANTS=('Ci_Eta0','Ci_Eta2','Cavg_Eta0','Cavg_Eta2')
def js(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def table(p):
 with Path(p).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write(p,rows):
 with p.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def bind(e):
 a=stat(e['path']);need(a==e,'Closed consumed stat changed: '+e['path']);return a
def load():
 receipt=T/'logs/upl_prestress10_CPU_r1_native_r1.check.json';r=js(receipt)
 need(r['passed'] and r['original_native_guards_passed'] and r['consumed_stats_unchanged'],'Closed original native receipt required')
 consumed=[stat(receipt),bind(r['source_run']),bind(r['native_completion']),stat(REF),stat(__file__)]
 run=js(r['source_run']['path']);done=js(D/'completion.json')
 need(run['passed'] and run['actual_exit']==run['actual_Win32_exit']==0 and run['consumed_stats_unchanged'] and str(SEED) in run['solver']['argv'],'Closed actual source/seed binding differs')
 need(done['passed'] and done['stage']=='upl_prestress10_native_r1' and done['samples']==1001 and done['completed_steps']==4000000 and done['actual_scalar_clock_verified'] and done['constant_conductivity_model']==0,'Only closed constant-k10s preload is admitted')
 need(done['total_native_IDs']==N and done['fixed_IDs']==FIXED and done['typed_arrays']==22 and done['all22_arrays_finite_and_ID_aligned'] and done['no_exclusions'],'Native scope differs')
 seedfiles=[Path(str(SEED)+s) for s in ('.xml','.bi4','_Normals.nbi4')]
 for p in seedfiles:
  e=next(e for e in run['consumed'] if Path(e['path'])==p);consumed.append(bind(e))
 files=[D/x for x in ('typed22_layout.csv','typed22.bin','native_ids.csv','clocks.csv')];consumed += [stat(p) for p in files]
 layout=table(files[0]);need(len(layout)==22,'Exactly22 layout records required');names=['time'];formats=['<f8'];offsets=[0];off=8
 for row,(name,kind,nc) in zip(layout,SCHEMA):
  need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,nc,TYPES[kind].itemsize*nc),'Typed layout differs')
  names.append(name);formats.append((TYPES[kind],(N,nc)) if nc>1 else (TYPES[kind],(N,)));offsets.append(off);off+=N*TYPES[kind].itemsize*nc
 with files[1].open('rb') as f:need(struct.unpack('<III',f.read(12))==(N,22,1001),'Typed header differs')
 need(files[1].stat().st_size==12+1001*off,'Typed file extent differs')
 frame=np.memmap(files[1],mode='r',offset=12+PART*off,shape=(1,),dtype=np.dtype(dict(names=names,formats=formats,offsets=offsets,itemsize=off)))[0]
 ids=table(files[2]);need(len(ids)==N and all(int(q['id'])==i and int(q['is_fixed'])==int(i<FIXED) for i,q in enumerate(ids)),'Complete native IDs required')
 x0=np.array([[float(q[k]) for k in ('x0','y0','z0')] for q in ids]);need(np.array_equal(frame['Idp'],np.arange(N)) and np.array_equal(frame['Posd'][:FIXED],x0[:FIXED]),'Native ID/fixed positions differ')
 clocks=table(files[3]);c=clocks[PART];time=float(frame['time']);need(len(clocks)==1001 and int(c['part'])==PART and int(c['completed_step'])==4000000 and int(c['saved_step'])==3999999 and struct.pack('<d',float(c['time_s']))==struct.pack('<d',time) and time==done['actual_end_s'],'Actual selected saved clock differs')
 xml=ET.parse(seedfiles[0]).getroot();ct=xml.find('execution/constants');dp=float(ct.find('dp').get('value'));h=np.float32(ct.find('h').get('value'));rho=float(np.float32(ct.find('rhop0').get('value')));mass=float(np.float32(ct.find('massfluid').get('value')))
 need(dp==.04 and float(xml.find('casedef/constantsdef/hdp').get('value'))==1.2 and xml.find('execution/parameters/parameter[@key="Kernel"]').get('value')=='1','Retained Cubic h/dp1.2 input required')
 variables={k:float(v) for e in xml.findall('casedef/geometry/predefinition/newvarcte') for k,v in e.attrib.items() if not k.startswith('_')}
 number=lambda s:variables[s[1:]] if s.startswith('#') else float(s)
 planes={}
 for p in xml.findall('execution/special/initialize/boundnormal_plane'):
  need(p.find('clear').get('v')=='true','Plane initialization must override its selected normals')
  normal=tuple(number(p.find('normal').get(a)) for a in ('x','z'));origin=tuple(number(p.find('point').get(a)) for a in ('x','z'));planes[normal]=origin
 need(set(planes)=={(1.,0.),(-1.,0.),(0.,1.)},'Only the actual three axis planes are handled')
 left,right,bed=planes[(1.,0.)][0],planes[(-1.,0.)][0],planes[(0.,1.)][1];need(left==0 and right==4 and bed==0,'Actual C08 plane locations differ')
 pos=frame['Posd'][FIXED:][:,[0,2]].copy();j=frame['PoroVolumeRatio'][FIXED:].copy();vol=frame['PoroCurrentVolume'][FIXED:].copy();fs=frame['FSType'][FIXED:].copy()
 need(np.isfinite(pos).all() and np.isfinite(j).all() and (j>0).all() and np.array_equal(vol,(mass/rho)*j),'Native J/current-volume ledger differs')
 need((pos[:,0]>left).all() and (pos[:,0]<right).all() and (pos[:,1]>bed).all(),'Analytic image oracle requires the actual soil strictly inside the three planes')
 grid=np.rint((x0[FIXED:][:,[0,2]]-.5*dp)/dp).astype(int);expected=.5*dp+dp*grid
 need(np.max(np.abs(expected-x0[FIXED:][:,[0,2]]))<=64*np.finfo(float).eps*4 and len({tuple(q) for q in grid})==5000,'Initial material grid mapping differs')
 bygrid={tuple(q):i for i,q in enumerate(grid)};selected=[bygrid[(x,z)] for z in (0,1,2,12,25,37,47,48,49) for x in (0,1,2,25,50,75,97,98,99)]
 need(len(selected)==len(set(selected))==81 and np.isin(fs,(2,3)).any(),'81 distinct receivers and saved free surface required')
 return frame,pos,j,vol,fs,selected,(left,right,bed),h,time,consumed
def cubic_fac(rr2,h):
 """Source float32 expression pattern: FunSphKernel.h::GetKernelCubic_Fac."""
 hh=float(h);aa=(10./(math.pi*7.))/(hh*hh*hh);c1=np.float32(-3.*aa);d1=np.float32(9.*aa/4.);c2=np.float32(-3.*aa/4.)
 rad=np.float32(np.sqrt(np.float32(rr2)));q=np.float32(rad/h)
 if rad>h:w=np.float32(np.float32(2.)-q);return float(np.float32(np.float32(c2*np.float32(w*w))/rad))
 q2=np.float32(q*q);return float(np.float32(np.float32(np.float32(c1*q)+np.float32(d1*q2))/rad))
class Cloud:
 def __init__(self,x,v,h,eq):
  self.x,self.v,self.h,self.eq=x,v,h,eq;self.tree=cKDTree(x);self.ec={};self.cc={};self.pairs=0
  size=np.float32(np.float32(2.)*h);self.r2=float(np.float32(size*size));self.eta=float(np.float32((float(h)*.1)*(float(h)*.1)));self.lower=float(np.float32(1e-18))
  # Broad-phase rounding envelope only; exact unchanged stage predicates decide membership below.
  self.search=math.nextafter(math.sqrt(float(np.nextafter(np.float32(self.r2),np.float32(np.inf)))),math.inf)
 def edges(self,i,moment=False):
  key=(i,moment)
  if key not in self.ec:
   out=[]
   for q in sorted(self.tree.query_ball_point(self.x[i],self.search,workers=1)):
    r=self.x[q]-self.x[i];rr=float(r[0]*r[0]+r[1]*r[1]);test=float(np.float32(rr)) if moment else rr
    if test>self.r2 or test<self.lower:continue
    fac=cubic_fac(rr,self.h);out.append(dict(j=q,r=tuple(r),d=tuple(-r),g=tuple(-fac*r),rr2=rr,v=float(self.v[q]),xj=tuple(self.x[q])))
   self.pairs+=len(out);self.ec[key]=out
  return self.ec[key]
 def correction(self,i):
  if i not in self.cc:
   edges=self.edges(i,True);m=[[math.fsum(e['v']*e['r'][a]*e['g'][b] for e in edges) for b in range(2)] for a in range(2)];c,det=self.eq.inverse2(m)
   cond=max(sum(abs(v) for v in row) for row in m)*max(sum(abs(v) for v in row) for row in c);need(math.isfinite(cond),'Nonfinite reconstructed-C condition')
   self.cc[i]=(c,det,cond)
  return self.cc[i]
def images(pos,vol,planes,radius):
 left,right,bed=planes;x=[pos];v=[vol]
 for side,plane in ((1,left),(-1,right)):
  pick=(pos[:,0]-plane if side==1 else plane-pos[:,0])<=2*radius;q=pos[pick].copy();q[:,0]=2*plane-q[:,0];x.append(q);v.append(vol[pick])
 pick=pos[:,1]-bed<=2*radius;q=pos[pick].copy();q[:,1]=2*bed-q[:,1];x.append(q);v.append(vol[pick])
 for side,plane in ((1,left),(-1,right)):
  pick=((pos[:,0]-plane if side==1 else plane-pos[:,0])<=2*radius)&(pos[:,1]-bed<=2*radius);q=pos[pick].copy();q[:,0]=2*plane-q[:,0];q[:,1]=2*bed-q[:,1];x.append(q);v.append(vol[pick])
 return np.concatenate(x),np.concatenate(v)
def field(eq,name,x):
 if name=='quadratic_tracezero':return x[0]*x[0]-x[1]*x[1],(2*x[0],-2*x[1]),[[2.,0.],[0.,-2.]]
 return eq.field(2,name,x)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-prefix',type=Path,required=True);a=p.parse_args();base=a.out_prefix;paths={k:Path(str(base)+s) for k,s in dict(fields='.fields.csv',receivers='.receivers.csv',check='.check.json',plot='.png').items()};need(base.parent.is_dir() and not any(q.exists() for q in paths.values()),'Fresh output files/existing parent required')
 try:
  frame,pos,j,vol,fs,selected,planes,h,time,consumed=load();spec=importlib.util.spec_from_file_location('retained_eq23_math',REF);eq=importlib.util.module_from_spec(spec);spec.loader.exec_module(eq)
  radius=float(np.float32(2.)*h);ghostx,ghostv=images(pos,vol,planes,radius);clouds=[('native_soil_support',Cloud(pos,vol,h,eq)),('analytic_wall_images',Cloud(ghostx,ghostv,h,eq))]
  surface=cKDTree(pos[np.isin(fs,(2,3))]);distance=surface.query(pos[selected],workers=1)[0];left,right,bed=planes;rows=[];receivers=[];checks=0
  for oracle,cloud in clouds:
   for q,i in enumerate(selected):
    x,z=pos[i];interior=min(x-left,right-x,z-bed)>2*radius and distance[q]>2*radius;ci,det,condition=cloud.correction(i);edges=[]
    for e in cloud.edges(i):
     cj,_,_=cloud.correction(e['j']);edges.append(dict(e,avg=tuple(tuple(.5*(ci[a][b]+cj[a][b]) for b in range(2)) for a in range(2))))
    need(edges and np.isfinite([v for row in ci for v in row]).all(),'Undefined sampled operator')
    receivers.append(dict(oracle=oracle,native_id=i+FIXED,x=x,z=z,J=float(j[i]),volume=float(vol[i]),saved_FSType=int(fs[i]),saved_FSNormal_x=float(frame['FSNormal'][i+FIXED,0]),saved_FSNormal_z=float(frame['FSNormal'][i+FIXED,2]),distance_to_saved_FS=float(distance[q]),interior_2R=interior,left_distance=x-left,right_distance=right-x,bed_distance=z-bed,rate_neighbors=len(edges),moment_neighbors=len(cloud.edges(i,True)),det=det,condition_inf=condition,Cxx=ci[0][0],Cxz=ci[0][1],Czx=ci[1][0],Czz=ci[1][1]))
    for variant in VARIANTS:
     local=[dict(e,avg=ci) for e in edges] if variant=='Ci_Eta2' else edges;vcall='Cavg_Eta2' if variant=='Ci_Eta2' else variant;op=eq.form_operator(2,local,ci,vcall,cloud.eta)
     for name in FIELDS:
      fi,gradient,truth=field(eq,name,cloud.x[i]);ideal=[field(eq,name,e['xj'])[0] for e in local]
      for precision in ('double','float_pressure'):
       f=float(np.float32(fi)) if precision=='float_pressure' else fi;fj=[float(np.float32(v)) for v in ideal] if precision=='float_pressure' else ideal;ev=eq.evaluate(2,local,ci,vcall,cloud.eta,op,f,fj)
       need(all(math.isfinite(v) for v in [*ev['H'],ev['trace'],ev['scalar'],ev['bound']]),'Nonfinite operator result');need(abs(ev['trace_delta'])<=ev['bound'] and ev['action_delta']<=ev['bound'],'Retained trace/action arithmetic budget failed');checks+=2
       if name=='constant':need(all(v==0 for v in [*ev['H'],*ev['grad'],ev['trace'],*ev['raw']]),'Constant exact null failed');checks+=1
       affine_bound=None
       if name.startswith('linear_') and precision=='double':
        affine_bound=ev['bound']+op['M_error']*sum(abs(v) for v in gradient)*max(sum(abs(v) for v in t) for t in op['t']);need(max(abs(v) for v in ev['H'])<=affine_bound,'Double-affine forward budget failed');checks+=1
       tx,tz,tc=truth[0][0],truth[1][1],truth[0][1];err=math.sqrt((ev['H'][0]-tx)**2+(ev['H'][1]-tz)**2+2*(ev['H'][2]-tc)**2);norm=math.sqrt(tx*tx+tz*tz+2*tc*tc)
       rows.append(dict(oracle=oracle,native_id=i+FIXED,interior_2R=interior,saved_FSType=int(fs[i]),field=name,pressure_storage=precision,variant=variant,Hxx=ev['H'][0],Hxz=ev['H'][2],Hzz=ev['H'][1],exact_Hxx=tx,exact_Hxz=tc,exact_Hzz=tz,trace=ev['trace'],exact_trace=tx+tz,scalar=ev['scalar'],tensor_Frobenius_error=err,tensor_relative_error=err/norm if norm else None,trace_abs_error=abs(ev['trace']-tx-tz),trace_identity_error=abs(ev['trace_delta']),arithmetic_bound=ev['bound'],affine_bound=affine_bound,moment_error=op['M_error'],condition_inf=condition,manufactured_pressure_rounding_max=max([abs(f-fi)]+[abs(a-b) for a,b in zip(fj,ideal)])))
  need(len(rows)==10368 and len(receivers)==162 and any(v['interior_2R'] for v in receivers),'Declared receiver/field/internal coverage differs');write(paths['fields'],rows);write(paths['receivers'],receivers)
  fig,ax=plt.subplots(1,2,figsize=(12,4.6));ax[0].scatter(pos[:,0],pos[:,1],s=1,c='.8');inside=np.array([r['interior_2R'] for r in receivers[:81]]);sp=pos[selected];ax[0].scatter(sp[~inside,0],sp[~inside,1],s=20,marker='s',label='wall/top band');ax[0].scatter(sp[inside,0],sp[inside,1],s=24,label='interior >2R');ax[0].set(xlabel='Current x [m]',ylabel='Current z [m]',title='81 fixed material IDs on saved geometry',aspect='equal');ax[0].legend(fontsize=8)
  for oracle,marker in ((clouds[0][0],'o'),(clouds[1][0],'x')):
   for variant,color in (('Ci_Eta0','tab:blue'),('Cavg_Eta2','tab:orange')):
    rr=[r for r in rows if r['oracle']==oracle and r['variant']==variant and r['field']=='quadratic_tracezero' and r['pressure_storage']=='double'];ax[1].scatter(range(81),[r['tensor_Frobenius_error'] for r in rr],s=14,marker=marker,c=color,label=oracle+' / '+variant)
  ax[1].set(xlabel='Declared receiver index',ylabel='Hessian Frobenius error [1/m²]',title='x²-z²: tensor error, no fitted correction');ax[1].grid(alpha=.25);ax[1].legend(fontsize=7);fig.suptitle('Cubic / saved10s geometry / reconstructed C; not a pressure-rate replay',fontsize=11);fig.tight_layout();fig.savefig(paths['plot'],dpi=180);plt.close(fig)
  need(all(stat(e['path'])==e for e in consumed),'Consumed snapshot/input/reference changed')
  summary=dict(stage=TAG,passed=True,part=PART,actual_time_s=time,receivers=81,receiver_rows=len(receivers),field_rows=len(rows),arithmetic_checks=checks,interior_receiver_count=int(sum(inside)),saved_FS_soil_count=int(np.isin(fs,(2,3)).sum()),J_range=[float(j.min()),float(j.max())],h_float=float(h),radius=radius,added_analytic_images=len(ghostx)-len(pos),C_reconstruction=[dict(oracle=n,sites=len(c.cc),cached_geometry_edges=c.pairs) for n,c in clouds],input_Normals_binary_decoded=False,plane_source='Actual run XML boundnormal_plane with clear=true; NBI4 is bound as an input artifact, not treated as exported per-ID native normals',native_fixed_samples_used_in_quadrature=False,native_C_or_total_Ace_available=False,production_operator_replay=False,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,SHA_scans=0,consumed=consumed,outputs=[stat(paths[k]) for k in ('fields','receivers','plot')])
  with paths['check'].open('x',encoding='utf-8') as f:json.dump(summary,f,indent=2);f.write('\n')
 except Exception as e:
  if not paths['check'].exists():
   with paths['check'].open('x',encoding='utf-8') as f:json.dump(dict(stage=TAG,passed=False,first_failure=str(e),production_operator_replay=False,physical_acceptance=False),f,indent=2)
  raise
if __name__=='__main__':main()
