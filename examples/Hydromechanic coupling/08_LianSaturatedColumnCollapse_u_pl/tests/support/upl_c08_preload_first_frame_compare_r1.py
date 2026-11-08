"""Compare actual PRE fluid VTK and the first completed collapse frame by native ID."""
import argparse,csv,json,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from upl_c08_fsmask_r1 import SCHEMA,TYPES

T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_preload_first_frame_compare_r1'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/particles/PartFluid_1000.vtk'
N=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r5_GPU_out/native'

def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)

def vtk(path):
 types={'float':'>f4','double':'>f8','unsigned_int':'>u4','int':'>i4','unsigned_short':'>u2','unsigned_char':'u1'}
 with path.open('rb') as f:
  def line():
   s=f.readline()
   while s in (b'\n',b'\r\n'):s=f.readline()
   return s.decode('ascii').strip().split()
  def array(kind,count):
   dtype=np.dtype(types[kind]);raw=f.read(count*dtype.itemsize);assert len(raw)==count*dtype.itemsize
   return np.frombuffer(raw,dtype=dtype).astype(dtype.newbyteorder('='))
  assert f.readline().startswith(b'# vtk DataFile Version');f.readline()
  assert line()==['BINARY'] and line()==['DATASET','POLYDATA']
  head=line();assert head[0]=='POINTS';count=int(head[1]);xyz=array(head[2],count*3).reshape(count,3)
  assert line()==['VERTICES',str(count),str(count*2)]
  vertices=array('int',count*2).reshape(count,2);assert np.all(vertices[:,0]==1) and np.array_equal(vertices[:,1],np.arange(count))
  assert line()==['POINT_DATA',str(count)] and line()==['SCALARS','Idp','unsigned_int'] and line()==['LOOKUP_TABLE','default']
  fields={'Idp':array('unsigned_int',count)};head=line();assert head[:2]==['FIELD','FieldData']
  for unused in range(int(head[2])):
   name,width,tuples,kind=line();assert int(tuples)==count and name not in fields
   fields[name]=array(kind,count*int(width)).reshape(count,int(width))
  assert not f.read().strip()
 return xyz,fields

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
 if not args.execution_authorized:raise RuntimeError('Root full-read required')
 prefix=T/'figures'/TAG
 if list(prefix.parent.glob(TAG+'*')):raise RuntimeError('Existing derived comparison preserved')
 completion=json.loads((N/'completion.json').read_text(encoding='utf-8'));assert completion['passed'] and completion['samples']==300 and completion['actual_native_IDs_per_frame']==6805
 proof=T/'logs/upl_preload_r2_GPU_particles_separate_r2.check.json';assert json.loads(proof.read_text(encoding='utf-8'))['passed']
 trace=T/'outputs/upl_c08_stage_trace_window_GPU_r1/C08StageTrace.csv'
 inputs=[PRE,N/'typed22.bin',N/'typed22_layout.csv',N/'clocks.csv',N/'completion.json',proof,trace,Path(__file__),T/'notes'/(TAG+'.md')];before=[stat(p) for p in inputs]
 xyz,fields=vtk(PRE);order=np.argsort(fields['Idp']);xyz=xyz[order];fields={k:v[order] for k,v in fields.items()};ids=fields['Idp'];assert np.array_equal(ids,np.arange(2060,7060))
 dtype=np.dtype([('time','<f8')]+[(name,TYPES[kind],(6805,width)) for name,kind,width in SCHEMA]);assert dtype.itemsize==8+6805*212
 with (N/'typed22.bin').open('rb') as f:assert struct.unpack('<III',f.read(12))==(6805,22,300)
 frames=np.memmap(N/'typed22.bin',dtype=dtype,offset=12,mode='r',shape=(300,));frame=frames[0];soil=np.flatnonzero(frame['Idp'][:,0]>=2060);assert np.array_equal(frame['Idp'][soil,0],ids)
 source=float(completion['source_actual_time_s']);actual=float(frame['time']);tau=actual-source
 with (N/'clocks.csv').open(encoding='utf-8') as f:clock=next(csv.DictReader(f))
 assert float(clock['time_s'])==actual and int(clock['completed_step'])==4004000
 summary=[]
 for name in ('PorePress','PorePress0','ExcessPorePress','PoroVolumeRatio','PoroPorosity','Kplastic'):
  old=fields[name].ravel();new=frame[name][soil].ravel();delta=new.astype(float)-old.astype(float)
  summary.append(dict(field=name,PRE_min=float(old.min()),PRE_max=float(old.max()),first_min=float(new.min()),first_max=float(new.max()),difference_RMS=float(np.sqrt(np.mean(delta**2))),difference_max_abs=float(np.max(np.abs(delta))),equal_value_IDs=int(np.count_nonzero(new==old)),compared_IDs=5000))
 p0_equal=np.array_equal(fields['PorePress0'].view(np.uint32),frame['PorePress0'][soil].view(np.uint32));assert p0_equal
 with trace.open(encoding='utf-8',newline='') as f:
  reader=csv.DictReader(f);initial=[next(reader) for unused in range(3)]
 initial_comparison=[]
 for r in initial:
  identity=int(r['native_id']);i=int(np.searchsorted(ids,identity));assert r['event']=='3' and r['nstep']=='4000000' and float(r['step_start_s'])==source
  old=float(fields['PorePress'][i,0]);before_p=float(r['p_before_Pa']);after_p=float(r['p_after_Pa'])
  initial_comparison.append(dict(native_ID=identity,PRE_p_Pa=old,initial_record_p_before_Pa=before_p,initial_record_p_after_Pa=after_p,equal=np.float32(old).tobytes()==np.float32(before_p).tobytes()==np.float32(after_p).tobytes()))
 assert all(r['equal'] for r in initial_comparison)
 files=[];path=Path(str(prefix)+'_summary.csv')
 with path.open('x',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
 files.append(path);path=Path(str(prefix)+'_material_points.csv');postx=frame['Posd'][soil]
 with path.open('x',encoding='utf-8',newline='') as f:
  w=csv.writer(f);w.writerow(['native_ID','PRE_x_float_m','PRE_z_float_m','first_x_double_m','first_z_double_m','PRE_p_Pa','first_p_Pa','delta_p_Pa','PRE_P0_Pa','first_P0_Pa','PRE_excess_Pa','first_excess_Pa','PRE_FS','first_FS'])
  for i,identity in enumerate(ids):
   w.writerow([int(identity),float(xyz[i,0]),float(xyz[i,2]),float(postx[i,0]),float(postx[i,2]),float(fields['PorePress'][i,0]),float(frame['PorePress'][soil[i],0]),float(frame['PorePress'][soil[i],0])-float(fields['PorePress'][i,0]),float(fields['PorePress0'][i,0]),float(frame['PorePress0'][soil[i],0]),float(fields['ExcessPorePress'][i,0]),float(frame['ExcessPorePress'][soil[i],0]),int(fields['FSType'][i,0]),int(frame['FSType'][soil[i],0])])
 files.append(path)
 pre=fields['PorePress'].ravel().astype(float)/1000;post=frame['PorePress'][soil,0].astype(float)/1000;delta=post-pre
 low=min(float(pre.min()),float(post.min()),0.);high=max(float(pre.max()),float(post.max()),0.);norm=TwoSlopeNorm(vmin=low,vcenter=0.,vmax=high);bound=float(np.max(np.abs(delta)))
 fig,axes=plt.subplots(1,3,figsize=(16,4.4),layout='constrained')
 for ax,points,values,title,use_norm in ((axes[0],xyz,pre,'PRE source: t=%.9f s'%source,norm),(axes[1],postx,post,'First collapse PART: tau=%.5f s'%tau,norm),(axes[2],xyz,delta,'Material delta p after 4000 new updates',TwoSlopeNorm(vmin=-bound,vcenter=0.,vmax=bound))):
  dots=ax.scatter(points[:,0],points[:,2],c=values,cmap='RdBu_r',norm=use_norm,s=8,marker='s',linewidths=0)
  ax.set(title=title,xlabel='x [m]',ylabel='z [m]',aspect='equal');fig.colorbar(dots,ax=ax,label='Total pore pressure [kPa]' if ax is not axes[2] else 'Delta total p [kPa]')
 fig.suptitle('Same 5000 native soil IDs; common pressure colour scale in first two panels. PRE is not a saved post-release t0.\nFixed material P0 is bit-identical for 5000/5000 IDs; VTK coordinates float, native first-frame coordinates double.',fontsize=10)
 path=Path(str(prefix)+'.png');fig.savefig(path,dpi=180);plt.close(fig);files.append(path)
 assert all(stat(e['path'])==e for e in before)
 result=dict(stage=TAG,passed=True,physical_acceptance=False,source_time_s=source,first_collapse_time_s=actual,elapsed_new_time_s=tau,new_updates=4000,common_material_IDs=5000,all5000_P0_float32_bits_equal=p0_equal,observed_initial_pressure_IDs=initial_comparison,initial_full5000_p_snapshot_available=False,comparison_is_PRE_to_evolved_10ms_not_import_copy_test=True,position_bit_identity_claimed=False,solver_invocations=0,BI4_decoder_invocations=0,SHA_scans=0,consumed=before,files=[stat(p) for p in files],visual_QA_pending=True)
 with Path(str(prefix)+'.check.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
 print(json.dumps(dict(passed=True,P0_equal_IDs=5000,initial_observed_equal_IDs=3,elapsed_s=tau,pressure_difference_RMS_Pa=summary[0]['difference_RMS'])))

if __name__=='__main__':main()
