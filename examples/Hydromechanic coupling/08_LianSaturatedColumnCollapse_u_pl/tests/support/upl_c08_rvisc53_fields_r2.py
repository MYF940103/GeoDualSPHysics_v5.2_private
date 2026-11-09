"""Plot-only repair of colorbar ticks for four already validated saved records."""
import argparse,csv,struct
from pathlib import Path
import upl_c08_as05_compare_r1 as c
from matplotlib.colors import Normalize,TwoSlopeNorm
np,plt=c.np,c.plt
T=c.T;TAG='upl_c08_rvisc53_fields_r2';CHECK=T/'logs'/(TAG+'.check.json');PNG=T/'figures/upl_c08_rvisc90_partial_review_r1_fields_r2.png';ANALYSIS=T/'logs/upl_c08_rvisc90_partial_review_r1.check.json';PARTS=(49,52)
def run():
 c.need(not CHECK.exists() and not PNG.exists(),'Existing plot-only outputs protected');before=[]
 try:
  before=[c.stat(Path(__file__)),c.stat(T/'notes'/(TAG+'.md')),c.stat(Path(c.__file__)),c.stat(T/'support/upl_c08_fsmask_r1.py'),c.stat(ANALYSIS)];a=c.read(ANALYSIS);c.need(a['passed'] and a['partial'] and not a['runtime_success_claimed'] and a['actual_common_saved_frames']==53 and a['consumed_stats_unchanged'],'Closed failed53 analysis required');before.append(c.bind(next(q for q in a['files'] if Path(q['path']).name=='upl_c08_rvisc90_partial_review_r1_fields.png')));snap={};sources=[]
  for label,job,suffix,count,partial in (('OFF','upl_c08_causal_window_GPU_r1','.native_r1.json',90,False),('ON','upl_c08_rvisc90_GPU_r1','.partial_native_r1.json',53,True)):
   receipt=T/'logs'/(job+suffix);entry=c.stat(receipt);c.need(entry in a['consumed'],'Native receipt must be the one consumed by the completed analysis');n=c.read(receipt);c.need(n['passed'] and n['consumed_stats_unchanged'] and n['original_saved_native_guards_passed' if partial else 'original_native_guards_passed'],'Original native diagnosis required');c.need(not partial or (n['partial'] and not n['runtime_success_claimed']),'Preserve failed runtime');before += [entry]+[c.bind(n[k]) for k in ('source_run','completion','metadata')];d=c.read(n['completion']['path']);c.need(d['passed'] and d['samples']==count and d['actual_native_IDs_per_frame']==6805 and d['typed_arrays']==22,'Exact original native scope differs');root=Path(n['completion']['path']).parent
   for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):before.append(c.bind(next(q for q in n['outputs'] if Path(q['path']).samefile(root/leaf))))
   layout=c.table(root/'typed22_layout.csv');fields=[('time','<f8')];c.need(len(layout)==22,'Original22 layout required')
   for row,(name,kind,width) in zip(layout,c.SCHEMA):c.need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,c.TYPES[kind].itemsize*width),'Original typed schema differs');fields.append((name,c.TYPES[kind],(6805,width)))
   dtype=np.dtype(fields);raw=root/'typed22.bin'
   with raw.open('rb') as f:c.need(struct.unpack('<III',f.read(12))==(6805,22,count),'Original90/53 headers must remain intact')
   c.need(raw.stat().st_size==12+count*dtype.itemsize,'Payload extent differs');frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(count,));clock=c.table(root/'clocks.csv');c.need(len(clock)==count,'Original clock coverage differs');sources.append(dict(label=label,header=[6805,22,count],native=entry,source_actual_time_s=d['source_actual_time_s']))
   for part in PARTS:
    x=frames[part];ids=x['Idp'][:,0];c.need(np.array_equal(ids,c.EXPECTED),'Original sorted6805 IDs differ');soil=ids>=2060;pos=np.array(x['Posd']);p=np.array(x['PorePress'][soil,0],dtype=float);J=np.array(x['PoroVolumeRatio'][soil,0]);q=clock[part];c.need(np.count_nonzero(soil)==5000 and all(np.isfinite(v).all() for v in (pos,p,J)) and float(x['time'])==float(q['time_s']) and int(q['completed_step'])==4000000+(part+1)*4000 and float(q['signed_dterror_s'])<=1e-14,'Selected actual records/clock/finite guard differ');snap[label,part]=dict(pos=pos[soil],fixed=pos[~soil],p=p,J=J,time=float(x['time']),tau=float(q['tau_from_actual_release_s']),step=int(q['completed_step']))
  c.need(sources[0]['source_actual_time_s']==sources[1]['source_actual_time_s'] and all(snap['OFF',p]['time']==snap['ON',p]['time'] and snap['OFF',p]['step']==snap['ON',p]['step'] for p in PARTS),'Four records must have exact matched actual clocks')
  columns=[(label,part) for part in PARTS for label in ('OFF','ON')];xmin=min(snap[k]['pos'][:,0].min() for k in columns);xmax=max(snap[k]['pos'][:,0].max() for k in columns);zmin=min(snap[k]['pos'][:,2].min() for k in columns);zmax=max(snap[k]['pos'][:,2].max() for k in columns);roi=a['spatial_localization_roi_m'];color_ranges={};tick_records={};fig,axes=plt.subplots(4,4,figsize=(17,14),layout='constrained')
  for row,(field,title) in enumerate((('p','Full-domain p [kPa]'),('p','Localization p [kPa]'),('J','Full-domain J'),('J','Localization J'))):
   low=min(float(snap[k][field].min()) for k in columns);high=max(float(snap[k][field].max()) for k in columns);c.need([low,high]==a['color_full_actual_ranges'][field],'Same four-state full range must be preserved');color_ranges[field]=[low,high];norm=TwoSlopeNorm(vmin=low,vcenter=0.,vmax=high) if low<0<high else Normalize(vmin=low,vmax=high)
   if field=='p':ticks=sorted(set([low,high]+[v for v in (-2e6,-1e6,0.) if low<=v<=high]));labels=[('+' if v>0 else '')+format(v/1000.,'.3f').rstrip('0').rstrip('.') for v in ticks]
   else:ticks=list(np.linspace(low,high,5));labels=[format(v,'.5f') for v in ticks]
   for col,key in enumerate(columns):
    axis=axes[row,col];q=snap[key];axis.scatter(q['fixed'][:,0],q['fixed'][:,2],s=4,c='.7');image=axis.scatter(q['pos'][:,0],q['pos'][:,2],c=q[field],norm=norm,cmap='coolwarm' if field=='p' else 'viridis',s=6,rasterized=True);axis.set(xlim=(xmin-.04,xmax+.04),ylim=(zmin-.04,zmax+.04),xlabel='x [m]',ylabel='z [m]');axis.set_aspect('equal');axis.set_title(f"{key[0]} actual tau={q['tau']:.9f}s",fontsize=9)
    if row%2:axis.set(xlim=roi[:2],ylim=roi[2:])
   bar=fig.colorbar(image,ax=list(axes[row]),ticks=ticks,label=title);bar.set_ticks(ticks,labels=labels);bar.ax.set_ylim(low,high);tick_records[str(row)]=dict(field=field,ticks_in_original_units=[float(v) for v in ticks],display_labels=labels);c.need(all(low<=v<=high for v in ticks),'Display tick outside actual range')
  fig.suptitle('Same raw saved fields; full actual ranges, no clipping or smoothing\nPressure: zero-centered color halves use different negative/positive scales; explicit ticks in kPa',fontsize=13);fig.savefig(PNG,dpi=170);plt.close(fig);c.need(all(c.stat(q['path'])==q for q in before),'Consumed source changed')
  result=dict(stage=TAG,passed=True,plot_only=True,source_analysis=c.stat(ANALYSIS),original_analysis_unchanged=True,native_sources=sources,records_consumed=4,parts=list(PARTS),color_full_actual_ranges=color_ranges,colorbar_ticks=tick_records,pressure_positive_negative_color_halves_have_different_scales=True,old_plot_issue='Automatic display ticks extended beyond the actual positive pressure maximum; physical data and original analysis remain unchanged',physical_acceptance=False,visual_QA_pending=True,solver_invocations=0,decoder_invocations=0,NN_recomputations=0,consumed=before,consumed_stats_unchanged=True,files=[c.stat(PNG)])
  with CHECK.open('x',encoding='utf-8') as f:c.json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
  print('RVISC53_FIELDS_R2_PASSED',CHECK,flush=True)
 except Exception as error:
  if not CHECK.exists():
   with CHECK.open('x',encoding='utf-8') as f:c.json.dump(dict(stage=TAG,passed=False,first_failure=str(error),partial_outputs_preserved=True,physical_acceptance=False,consumed=before),f,indent=2);f.write('\n')
  raise
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();c.need(args.execution_authorized,'Author-only until root full-read');run()
