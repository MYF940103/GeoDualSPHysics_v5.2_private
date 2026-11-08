"""Four saved-state raw fields for the sealed epsilon comparison; no dense peak claim."""
import argparse,json,struct
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize,TwoSlopeNorm
from matplotlib.lines import Line2D
import upl_c08_as05_compare_r1 as c

T=c.T;TAG='upl_c08_as05_fields_r1';PREFIX=T/'figures'/TAG;CHECK=T/'logs'/(TAG+'.check.json');PARTS=(22,65)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');a=ap.parse_args();c.need(a.execution_authorized,'Root full-read before four-state field plotting');c.need(not CHECK.exists() and not list(PREFIX.parent.glob(TAG+'*')),'Existing complete/partial fields protected')
    proof=c.read(c.CHECK);c.need(proof['passed'] and proof['analysis_completed'] and proof['actual_matched_samples']==66 and proof['clock_and_steps_exact'] and proof['soil_IDs_per_sample']==5000,'Passed actual parameter comparison required')
    groups=[c.load(spec) for spec in c.SPECS];c.need(groups[0]['done']['source_actual_time_s']==groups[1]['done']['source_actual_time_s'],'Actual source clock differs')
    before=[c.stat(__file__),c.stat(T/'notes'/(TAG+'.md')),c.stat(c.CHECK),c.bind(next(e for e in proof['consumed'] if Path(e['path']).samefile(c.__file__)))]+[e for g in groups for e in g['before']];selected={}
    for g in groups:
        with (g['native']/'typed22.bin').open('rb') as f:
            c.need(struct.unpack('<III',f.read(12))==(6805,22,66),'Literal full native header required')
            for part in PARTS:
                f.seek(12+part*g['dtype'].itemsize);raw=f.read(g['dtype'].itemsize);c.need(len(raw)==g['dtype'].itemsize,'Incomplete selected record');frame=np.frombuffer(raw,dtype=g['dtype'],count=1)[0];time,tau,step=c.inspect(frame,g,part)
                soil=frame['Idp'][:,0]>=2060;fixed=~soil;c.need(np.count_nonzero(soil)==5000 and np.count_nonzero(fixed)==1805,'Soil/fixed marker counts differ')
                selected[(part,g['label'])]=dict(group=g['label'],epsilon=g['epsilon'],part=part,time=time,tau=tau,step=step,soil_xz=frame['Posd'][soil][:,[0,2]].copy(),fixed_xz=frame['Posd'][fixed][:,[0,2]].copy(),pressure=frame['PorePress'][soil,0].astype(float),kappa=frame['Kplastic'][soil,0].astype(float),surface=np.isin(frame['FSType'][soil,0],(2,3)))
    columns=[selected[(part,g['label'])] for part in PARTS for g in groups]
    for part in PARTS:
        q,r=(selected[(part,g['label'])] for g in groups);c.need((q['time'],q['tau'],q['step'])==(r['time'],r['tau'],r['step']),'Selected states require exact actual clock/Step pairing')
    pressure=np.concatenate([q['pressure'] for q in columns]);kappa=np.concatenate([q['kappa'] for q in columns]);xy=np.concatenate([q['soil_xz'] for q in columns]);pnorm=TwoSlopeNorm(vmin=float(pressure.min()*.001),vcenter=0.,vmax=float(pressure.max()*.001));knorm=Normalize(vmin=float(kappa.min()),vmax=float(kappa.max()),clip=False)
    # The common view contains every soil center plus two dp of wall context;
    # all fixed points are drawn, but the long remote bed is outside this view.
    padding=2*.04;limits=(float(xy[:,0].min()-padding),float(xy[:,0].max()+padding),float(xy[:,1].min()-padding),float(xy[:,1].max()+padding));rows=[]
    plt.rcParams.update({'font.size':8,'figure.dpi':170});fig,axes=plt.subplots(2,4,figsize=(18,7.7),sharex=True,sharey=True,layout='constrained')
    for col,q in enumerate(columns):
        x=q['soil_xz'];fixed=q['fixed_xz'];surface=q['surface']
        for row,field,norm,cmap,scale in ((0,'pressure',pnorm,'RdBu_r',.001),(1,'kappa',knorm,'viridis',1.)):
            ax=axes[row,col];ax.scatter(fixed[:,0],fixed[:,1],s=4,c='.65',marker='s',linewidths=0,zorder=0)
            for mask,marker in ((~surface,'o'),(surface,'^')):
                ax.scatter(x[mask,0],x[mask,1],c=q[field][mask]*scale,s=7,norm=norm,cmap=cmap,marker=marker,linewidths=0,zorder=1)
            ax.set(xlim=limits[:2],ylim=limits[2:],xlabel='x [m]',ylabel='z [m]',title='epsilon=%g, actual tau=%.12g s\n%s'%(q['epsilon'],q['tau'],'Pore pressure' if row==0 else 'Kplastic history kappa'));ax.set_aspect('equal',adjustable='box');ax.grid(alpha=.15)
        rows.append(dict(group=q['group'],epsilon=q['epsilon'],part=q['part'],time_s=q['time'],tau_s=q['tau'],completed_step=q['step'],soil_IDs=5000,fixed_IDs=1805,soil_x_min_m=float(x[:,0].min()),soil_x_max_m=float(x[:,0].max()),soil_z_min_m=float(x[:,1].min()),soil_z_max_m=float(x[:,1].max()),p_min_Pa=float(q['pressure'].min()),p_max_Pa=float(q['pressure'].max()),negative_p_soil_count=int(np.count_nonzero(q['pressure']<0)),kappa_min=float(q['kappa'].min()),kappa_max=float(q['kappa'].max()),FS23_soil_count=int(surface.sum())))
    fig.colorbar(plt.cm.ScalarMappable(norm=pnorm,cmap='RdBu_r'),ax=axes[0,:].tolist(),label='Pore pressure [kPa]; shared full four-state soil range',shrink=.85)
    fig.colorbar(plt.cm.ScalarMappable(norm=knorm,cmap='viridis'),ax=axes[1,:].tolist(),label='Kplastic kappa; shared full four-state soil range',shrink=.85)
    handles=[Line2D([],[],marker='o',ls='',c='.25',label='Other soil'),Line2D([],[],marker='^',ls='',c='.25',label='Soil FS2/3'),Line2D([],[],marker='s',ls='',c='.65',label='Retained fixed markers')];axes[1,0].legend(handles=handles,fontsize=6,loc='lower left')
    fig.suptitle('Prescribed epsilon .2 versus .5: raw5000-soil saved states, no smoothing or theory/half gate\nPart22 and65 only; saved-state extrema are not dense-trace peaks; grey wall fields are not included in either color scale')
    png=Path(str(PREFIX)+'.png');csv=Path(str(PREFIX)+'.csv');fig.savefig(png);plt.close(fig);c.write(csv,rows);c.need(all(c.stat(e['path'])==e for e in before),'Sealed input/helper changed')
    result=dict(stage=TAG,passed=True,analysis_completed=True,selected_parts=list(PARTS),state_count=4,soil_IDs_per_state=5000,fixed_IDs_per_state=1805,selected_typed_records_read=4,whole66_frame_scan=False,all22_selected_fields_finite=True,exact_selected_clock_and_step_pairs=True,pressure_common_min_Pa=float(pressure.min()),pressure_common_max_Pa=float(pressure.max()),kappa_common_min=float(kappa.min()),kappa_common_max=float(kappa.max()),pressure_scale='zero-centered piecewise-linear full actual soil range in kPa; negative pressure retained',kappa_scale='linear full actual soil range',display_window_xz_m=list(limits),display_padding_m=padding,far_fixed_bed_can_be_outside_common_soil_view=True,all_soil_field_points_displayed=True,smoothing_clipping_fitting=False,FS23_triangles_are_native_saved_classification=True,dense_trace_read=False,saved_extrema_not_dense_peak=True,physical_acceptance=False,solver_invocations=0,decoder_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed=before,files=[c.stat(p) for p in (png,csv)])
    with CHECK.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    print('AS05_FIELDS_READY',CHECK,flush=True)

if __name__=='__main__':main()
