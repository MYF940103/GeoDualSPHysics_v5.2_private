"""Plots only independently audited HG x SPR native results; no solver launch."""
import json
from pathlib import Path
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import pandas as pd
from lian_release_r1 import TESTS, READER, native, bound, utc, write_json
from lian_opt3_review_r1 import verify_bindings
from lian_fig10_first3_r1 import COLORS, CROPS, TIMES

TAG='lian_hg3_figures_r1'
RUNS={'H0S0':'lian_spr_mix_r1_off_3s','H0S1':'lian_spr_mix_r1_on_3s',
      'H1S0':'lian_hg3_r2_spr0_3s','H1S1':'lian_hg3_r2_spr1_3s'}
STYLE={'H0S0':('#353535',':','HG OFF / SPR OFF'),'H0S1':('#28618e','--','HG OFF / SPR ON'),
       'H1S0':('#ae692c','-.','HG .1 / SPR OFF'),'H1S1':('#9b4b76','-','HG .1 / SPR ON')}


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json');assert not receipt.exists()
    check_path=TESTS/'logs/lian_hg3_review_r1.check.json';check=json.loads(check_path.read_text())
    assert check['passed']
    verify_bindings(check['sources']+check['artifacts'])
    history_path=TESTS/'figures/lian_hg3_review_r1_history.csv'
    history=pd.read_csv(history_path,float_precision='round_trip')
    image_path=TESTS/'outputs/lian_fig10_ref_r1/figure10.png'
    paper_check=TESTS/'logs/lian_fig10_first3_r1.check.json'
    old=json.loads(paper_check.read_text())
    old_image=next(e for e in old['sources'] if Path(e['path']).name=='figure10.png')
    verify_bindings([old_image])
    sources=[bound(p) for p in [__file__,check_path,history_path,READER,image_path,paper_check,
        TESTS/'scripts/lian_fig10_first3_r1.py']]
    artifacts=[]
    def png(label,fig):
        path=TESTS/'figures'/(TAG+'_'+label+'.png');assert not path.exists()
        fig.savefig(path,dpi=180);plt.close(fig);artifacts.append(bound(path))
    def csv(label,frame):
        path=TESTS/'figures'/(TAG+'_'+label+'.csv');assert not path.exists()
        frame.to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
    assert set(history.run)==set(RUNS)
    def data(key):
        h=history[history.run.eq(key)].sort_values('time_s');assert len(h)==61
        return h
    plt.rcParams.update({'font.size':11,'axes.titlesize':11})
    panels=[('paper_A_pressure_pa','A material pressure (kPa)',.001),('paper_B_pressure_pa','B material pressure (kPa)',.001),
        ('pressure_max_pa','Native maximum pressure (kPa)',.001),('paper_A_settlement_mm','A material settlement (mm)',1),
        ('paper_B_settlement_mm','B material settlement (mm)',1),('total_sigma_zz_rms_pa','Total vertical stress RMS (kPa)',.001)]
    for label,selected in [('history',panels),('boundary',[
        ('left_normal_max_mm','Left soil-layer normal displacement (mm)',1),
        ('right_normal_max_mm','Right soil-layer normal displacement (mm)',1),
        ('bottom_normal_max_mm','Bottom soil-layer normal displacement (mm)',1),
        ('bottom_tangent_max_mm','Bottom soil-layer tangent displacement (mm)',1),
        ('vmax_m_s','Native maximum speed (m/s)',1),('pressure_min_pa','Native minimum pressure (Pa)',1)])]:
        fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
        for key,(color,line,title) in STYLE.items():
            h=data(key)
            for ax,(field,ylabel,scale) in zip(axes.flat,selected):
                ax.plot(h.time_s,h[field]*scale,color=color,ls=line,label=title)
                ax.set(xlim=(0,3),xlabel='Actual saved time (s)',ylabel=ylabel);ax.grid(alpha=.2)
        axes[0,0].legend(fontsize=9)
        fig.suptitle('Lian HG x SPR | same dt=10 us, eta=.04, corrected stress gradient, original mixed slip/load\n'
            'Native material histories; option differences are not half-step or theory errors. Boundary panels track soil, not wall motion.',fontsize=12)
        png(label,fig)
    image=np.asarray(Image.open(image_path).convert('RGB'))
    cmap=ListedColormap(COLORS);cmap.set_over(COLORS[-1]);cmap.set_under('#b850b8')
    snapshots={};summary=[]
    for key,name in RUNS.items():
        manifest_path=TESTS/'logs'/(name+'.run.json');manifest=json.loads(manifest_path.read_text())
        sources.append(bound(manifest_path));expected={str(Path(e['path']).resolve()).lower():e for e in manifest['outputs']}
        for target,part,maximum in TIMES:
            path=TESTS/'outputs'/name/'data'/f'Part_{part:04d}.bi4';verify_bindings([expected[str(path.resolve()).lower()]])
            sources.append(bound(path));a=native(TESTS/'outputs'/name,part)
            assert len(a)==20301 and abs(float(a.time_s.iloc[0])-target)<=1.01e-5
            snapshots[key,part]=a
            summary.append(dict(run=key,output_name=name,target_time_s=target,actual_time_s=float(a.time_s.iloc[0]),
                saved_step=int(a.saved_step.iloc[0]),pressure_max_kpa=float(a.pressure.max()/1000),
                pressure_min_pa=float(a.pressure.min()),paper_max_kpa=maximum,
                above_bar_native_pct=100*float(a.pressure.gt(maximum*1000).mean()),
                below_zero_native_pct=100*float(a.pressure.lt(0).mean())))
            csv(f'{key}_part{part:04d}',pd.DataFrame(dict(id=a.id,x_m=a.x,z_m=a.z,pressure_pa=a.pressure)))
    selected=pd.DataFrame(summary);csv('selected',selected)
    for spr in [0,1]:
        keys=['H0S'+str(spr),'H1S'+str(spr)]
        fig=plt.figure(figsize=(18,10),layout='constrained');grid=fig.add_gridspec(3,5,width_ratios=[1,1,1,1,.045])
        for row,(target,part,maximum) in enumerate(TIMES):
            levels=np.linspace(0,maximum,13)
            for col,key in enumerate(['SPH','FEM']+keys):
                ax=fig.add_subplot(grid[row,col])
                if key in CROPS:
                    x0,y0,x1,y1=CROPS[key][row];ax.imshow(image[y0:y1,x0:x1],extent=[0,20,0,10],origin='upper')
                    title=f'Paper {key} | {target:g} s'
                else:
                    a=snapshots[key,part];m=selected[selected.run.eq(key)&selected.target_time_s.eq(target)].iloc[0]
                    artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=levels,norm=BoundaryNorm(levels,cmap.N),cmap=cmap,extend='both')
                    title=STYLE[key][2]+f'\n{m.actual_time_s:.6f} s | max {m.pressure_max_kpa:.4f} kPa\n>bar {m.above_bar_native_pct:.2f}% nodes'
                ax.set(title=title,xlim=(0,20),ylim=(0,10),aspect='equal',xticks=[0,5,10,15,20],yticks=[0,5,10],
                    xlabel='x (m)',ylabel='z (m)' if col==0 else '')
            fig.colorbar(artist,cax=fig.add_subplot(grid[row,4]),label='Excess pressure (kPa)',
                ticks=[0,1,2,3,4,5] if maximum==5 else [0,.5,1,1.5,1.75])
        fig.suptitle(f'Lian Fig10 comparison | SPR {"ON" if spr else "OFF"}, HG OFF versus .1\n'
            'Original SPH palette and row limits 0-5 / 0-5 / 0-1.75 kPa; FEM retains its original legend.\n'
            'Linear triangulated display; no field smoothing, zero-clipping or rescaling. Paper raster is not raw FEM/SPH data.',fontsize=12)
        png('fields_spr'+str(spr),fig)
    fig=plt.figure(figsize=(18,8),layout='constrained');grid=fig.add_gridspec(2,5,width_ratios=[1,1,1,1,.045])
    endpoint={key:snapshots[key,60] for key in RUNS}
    compression={key:-(a.sigma_zz-a.pressure)/1000 for key,a in endpoint.items()}
    speed={key:np.linalg.norm(a[['vx','vy','vz']],axis=1) for key,a in endpoint.items()}
    lo=min(0,min(float(v.min()) for v in compression.values()));hi=max(float(v.max()) for v in compression.values())
    vmax=max(float(v.max()) for v in speed.values())
    for col,key in enumerate(RUNS):
        a=endpoint[key]
        csv(key+'_endpoint_nodes',pd.DataFrame(dict(id=a.id,x_m=a.x,z_m=a.z,
            total_vertical_compression_kpa=compression[key],speed_m_s=speed[key])))
        for row,(values,vmin,vmaxrow,label) in enumerate([(compression[key],lo,hi,'Total vertical compression (kPa)'),
            (speed[key],0,vmax,'Speed (m/s)')]):
            ax=fig.add_subplot(grid[row,col]);artist=ax.scatter(a.x,a.z,c=values,s=2,cmap='cividis',vmin=vmin,vmax=vmaxrow,linewidths=0)
            ax.set(title=STYLE[key][2],xlim=(0,20),ylim=(0,10),aspect='equal',xlabel='x (m)',ylabel='z (m)' if col==0 else '')
            if col==3:fig.colorbar(artist,cax=fig.add_subplot(grid[row,4]),label=label)
    fig.suptitle('Native nodes at actual3.000000s | total compression=-(effective sigma_zz-p), common scale per row\n'
        'No spatial averaging. Smaller stress amplitude/speed is not by itself a theory-accuracy improvement.',fontsize=12)
    png('endpoint_nodes',fig)
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),sources=sources,artifacts=artifacts,
        native_runs=RUNS,paper_times_and_limits=[dict(time_s=t,lower_kpa=0,upper_kpa=m) for t,_,m in TIMES],
        selected=summary,physical_3s_half_accepted=False,formal100_admitted=False,
        limitations=['No quantitative paper field RMSE: references are original raster crops, not raw simulation data.',
            'Colorbar upper bound is not automatically an exact paper pressure maximum.',
            'Node exceedance percentages are not continuum area fractions.',
            'No candidate selection from colors alone; no full3s half/100s/theory/general-contact acceptance.']))
    print(selected.to_string(index=False),flush=True)


if __name__=='__main__':main()
