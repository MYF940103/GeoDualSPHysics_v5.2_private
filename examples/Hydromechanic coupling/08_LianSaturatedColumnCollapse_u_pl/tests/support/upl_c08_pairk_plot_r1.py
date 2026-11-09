"""Display-only9-panel replot from passed derived pair-k summary CSVs."""
import argparse,csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator,ScalarFormatter
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];TAG='upl_c08_pairk_plot_r1';OLD='upl_c08_pairk_flux_review_r1';PARTS=(13,14,29)
GROUPS=('FS0_halo_free','FS0_halo_near','FS23','FS1_other');COLORS=('#2166ac','#67a9cf','#d95f02','#666666')
def table(p):
 with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def plot(summary,quant,path):
 fig,axes=plt.subplots(3,3,figsize=(16,11),layout='constrained');cases=(('constant_null','float64','C0'),('affine_hydraulic','float64','A64'),('affine_hydraulic','float32','A32'),('nonconstant_potential','float64','Q64'),('nonconstant_potential','float32','Q32'))
 for col,part in enumerate(PARTS):
  for row,method in enumerate(('current','pairFlux')):
   ax=axes[row,col]
   for group,color in zip(GROUPS,COLORS):
    points=[]
    for index,(field,storage,label) in enumerate(cases):
     q=[v for v in summary if v['part']==part and v['cohort']==group and v['field']==field and v['storage']==storage and v['method']==method]
     if q:points.append((index,q[0]['RMS_Pa_s']))
    if points:ax.plot([q[0] for q in points],[q[1] for q in points],'o-',ms=3,color=color,label=group)
   ax.set(xticks=range(5),xticklabels=[q[2] for q in cases],ylabel='Zero-reference RMS [Pa/s]',title=f'part{part}: {method}');ax.set_yscale('symlog',linthresh=1.);ax.grid(alpha=.2)
  ax=axes[2,col];qcases=(('affine_hydraulic','current','A current'),('affine_hydraulic','pairFlux','A pair'),('nonconstant_potential','current','Q current'),('nonconstant_potential','pairFlux','Q pair'))
  for group,color in zip(GROUPS,COLORS):
   points=[]
   for index,(field,method,label) in enumerate(qcases):
    q=[v for v in quant if v['part']==part and v['cohort']==group and v['field']==field and v['method']==method]
    if q:points.append((index,q[0]['RMS_rate32_minus_rate64_Pa_s']))
   if points:ax.plot([q[0] for q in points],[q[1] for q in points],'o-',ms=3,color=color,label=group)
  ax.set(xticks=range(4),xticklabels=[q[2] for q in qcases],ylabel='Storage effect RMS [Pa/s]',title='Float32 minus float64 rate');ax.set_yscale('linear');ax.yaxis.set_major_locator(MaxNLocator(nbins=5,min_n_ticks=3));formatter=ScalarFormatter(useOffset=False);formatter.set_scientific(False);ax.yaxis.set_major_formatter(formatter);ax.grid(alpha=.2)
 axes[0,0].legend(fontsize=7);fig.suptitle('Conditional analytic-field/ghost oracle on fixed actual C/J/FS\nC0=constant; A=uniform-A affine p; Q=nonconstant potential.\nTop two rows: symlog1Pa/s display only. Bottom: linear numeric ticks; data unchanged.');fig.savefig(path,dpi=160);plt.close(fig)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();e.need(a.execution_authorized,'Root review before one plot-only action');check=T/'logs'/(TAG+'.check.json');image=T/'figures'/(TAG+'_manufactured_readable.png');e.need(not check.exists() and not image.exists(),'Fresh display outputs required; preserve the original plot/check');before=[];result=dict(stage=TAG,passed=False,plot_only=True,analysis_rerun=False,raw_helper_CSVs_read=False,solver_invocations=0,force_invocations=0,decoder_invocations=0,build_invocations=0,SHA_scans=0,physical_acceptance=False)
 try:
  source=T/'logs'/(OLD+'.check.json');r=e.read(source);e.need(r['passed'] and r['consumed_stats_unchanged'] and r['actual_rows']==96 and r['manufactured_rows']==576,'Passed original derived review required');before=[e.stat(__file__),e.stat(T/'notes'/(TAG+'.md')),e.stat(source)];files={Path(q['path']).name:q for q in r['outputs']};loaded=[]
  for suffix in ('manufactured','quantization'):
   entry=e.bind(files[OLD+'_'+suffix+'.csv']);before.append(entry);rows=table(entry['path'])
   for q in rows:q['part']=int(q['part']);key='RMS_Pa_s' if suffix=='manufactured' else 'RMS_rate32_minus_rate64_Pa_s';q[key]=float(q[key])
   loaded.append(rows)
  plot(*loaded,image);e.need(all(e.stat(q['path'])==q for q in before),'Derived input changed during display-only replot');result.update(passed=True,source_review=e.stat(source),only_bottom_row_axis_and_caption_changed=True,top_zero_reference_symlog_unchanged=True,bottom_linear_autoscale_numeric_ticks=True,curve_values_and_cohorts_unchanged=True,consumed_stats_unchanged=True,output=e.stat(image))
 except Exception as error:result['first_failure']=str(error)
 result['consumed']=before;e.save(check,result);print(json.dumps(dict(passed=result['passed'],check=str(check),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
