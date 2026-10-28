"""Formal native plots and original-paper side-by-side comparisons; no solver."""
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from PIL import Image
import numpy as np
import pandas as pd

CASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE/'tests/scripts'))
from lian_release_r1 import bound,write_json,utc
from lian_fig10_first3_r1 import COLORS,CROPS
TAG='lian_hgspr100_r1'
OUT=CASE/'figures'
REF=CASE/'tests/figures'


def main():
    check=CASE/'tests/logs'/(TAG+'.check.json')
    audit=json.loads(check.read_text())
    assert audit['passed'] and audit['native_safety_passed'], 'Formal plots require the complete native safety review'
    receipt=CASE/'tests/logs'/(TAG+'.plots.json')
    assert not receipt.exists()
    for item in audit['artifacts']:
        assert bound(item['path'])['sha256']==item['sha256']
    h=pd.read_csv(OUT/(TAG+'_history.csv'),float_precision='round_trip')
    profile=pd.read_csv(OUT/(TAG+'_horizontal_profile.csv'),float_precision='round_trip')
    sources=[bound(p) for p in [__file__,check,OUT/(TAG+'_history.csv'),OUT/(TAG+'_horizontal_profile.csv')]]
    artifacts=[]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':11})
    particles=CASE/'CaseLianFlexibleStrip2D_PR_release_HGSPR_out/particles'
    particle_check=CASE/'tests/logs/lian_server_particles_r1.check.json'
    assert json.loads(particle_check.read_text())['passed']
    sources.append(bound(particle_check))
    for label in ['PartFluid','PartBound']:
        series=particles/(label+'.vtk.series');assert not series.exists()
        items=[dict(name=f'{label}_{int(row.part):04d}.vtk',time=float(row.time_s)) for row in h.itertuples()]
        assert len(items)==2001 and all((particles/e['name']).is_file() for e in items)
        write_json(series,{'file-series-version':'1.0','files':items})
        artifacts.append(bound(series))

    def png(label,fig):
        p=OUT/(TAG+'_'+label+'.png');assert not p.exists()
        fig.savefig(p,dpi=180);plt.close(fig);artifacts.append(bound(p))

    def axis_style(ax,xlabel,ylabel,log=False):
        ax.set(xlabel=xlabel,ylabel=ylabel,xlim=(.05,100) if log else (0,100))
        if log:
            ax.set_xscale('log');ax.set_xticks([.05,.1,1,10,100],['0.05','0.1','1','10','100'])
        ax.grid(alpha=.2)

    reference_path=CASE/'tests/logs/lian_server_return_r1_reference_points.json'
    reference=json.loads(reference_path.read_text())
    for item in reference['sources']+reference['artifacts']:
        assert bound(item['path'])['sha256']==item['sha256']
    sources.append(bound(reference_path))
    comparisons=[]
    for point in reference['points']:
        row=dict(point)
        if point['figure'] in ['11','12a']:
            target=point['raster_time_s']
            col=point['paper_point']+('_pressure_pa' if point['figure']=='11' else '_settlement_mm')
            values=h[col].to_numpy()*.001
            row['current_value']=float(np.interp(target,h.time_s,values))
            j=int(np.searchsorted(h.time_s,target));j=min(max(j,1),len(h)-1)
            row.update(native_before_time_s=float(h.time_s.iloc[j-1]),native_after_time_s=float(h.time_s.iloc[j]),
                matching='Linear temporal interpolation between actual native saves to the raster-time coordinate')
        else:
            row['current_value']=float(np.interp(point['elevation_m'],profile.z0_m,profile.ux_m))
            row['matching']='Linear initial-material elevation interpolation; fixed x0=1.25-m stencil at final actual time'
        row['current_minus_reference']=row['current_value']-point['value']
        row['relative_difference_percent']=100*row['current_minus_reference']/point['value']
        comparisons.append(row)
    comparison_path=OUT/(TAG+'_paper_points.csv');assert not comparison_path.exists()
    comparison=pd.DataFrame(comparisons);comparison.to_csv(comparison_path,index=False,float_format='%.17g')
    artifacts.append(bound(comparison_path))

    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        valid=h.time_s.gt(0)
        axes[0,0].plot(h.time_s[valid],h.loc[valid,point+'_pressure_pa']/1000,ls,color=color,label=point)
        axes[0,1].plot(h.time_s[valid],h.loc[valid,point+'_settlement_mm'],ls,color=color,label=point)
    axis_style(axes[0,0],'Actual saved time (s)','Material pore pressure (kPa)',True)
    axis_style(axes[0,1],'Actual saved time (s)','Downward material settlement (mm)',True)
    for ax in axes[0]:ax.legend()
    axes[1,0].plot(h.time_s,h.force_N_m/1000,color='#245d88')
    axis_style(axes[1,0],'Actual saved time (s)','Applied resultant (kN/m)')
    for col,ls,label in [('pressure_max_pa','-','Native maximum'),('pressure_mean_pa','--','Native mean'),
        ('A_pressure_pa',':','Material A'),('B_pressure_pa','-.','Material B')]:
        tail=h.time_s.ge(3)
        axes[1,1].semilogy(h.time_s[tail],h.loc[tail,col].where(h.loc[tail,col].gt(0)),ls,label=label)
    axes[1,1].set(xlabel='Actual saved time (s)',ylabel='Late pore pressure (Pa)',xlim=(3,100));axes[1,1].grid(alpha=.2);axes[1,1].legend(fontsize=9)
    fig.suptitle('Lian HG + SPR: returned 100-s server run\nA(0,10), B(1.25,8.75): fixed initial material IDs and bilinear weights',fontsize=13)
    png('history',fig)

    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    for ax,col,label,scale in zip(axes.flat,
        ['total_sigma_zz_rms_pa','vmax_m_s','left_normal_max_mm','right_normal_max_mm','bottom_normal_max_mm','bottom_tangent_max_mm'],
        ['Total vertical stress RMS (kPa)','Maximum speed (m/s)','Left-layer normal displacement (mm)',
         'Right-layer normal displacement (mm)','Bottom-layer normal displacement (mm)','Bottom-layer tangential displacement (mm)'],
        [.001,1,1,1,1,1]):
        ax.plot(h.time_s,h[col]*scale,color='#245d88');axis_style(ax,'Actual saved time (s)',label)
    fig.suptitle('Native total stress and adjacent soil-layer response\nSide walls FreeSlip; bottom NoSlip. Soil displacement is not wall motion.',fontsize=13)
    png('stress_boundary',fig)

    refs={name:REF/('lian_server_return_r1_reference_'+name+'.png') for name in ['fig10','fig11','fig12']}
    for p in refs.values():sources.append(bound(p))
    image=np.asarray(Image.open(refs['fig10']).convert('RGB'))
    crops={k:list(v) for k,v in CROPS.items()}
    # Fourth-row bounds are reviewed against the original embedded paper raster.
    crops['SPH'].append((31,1513,837,1921))
    crops['FEM'].append((938,1509,1751,1918))
    cmap=ListedColormap(COLORS);cmap.set_under('#b850b8');cmap.set_over(COLORS[-1])
    selected=[]
    fig=plt.figure(figsize=(16,12),layout='constrained')
    grid=fig.add_gridspec(4,4,width_ratios=[1,1,1,.045])
    for row,(part,target,maximum) in enumerate([(10,.5,5.),(20,1.,5.),(60,3.,1.75),(1000,50.,.06)]):
        p=OUT/(TAG+f'_field_{part:04d}.csv');a=pd.read_csv(p,float_precision='round_trip');sources.append(bound(p))
        entry=h[h.part.eq(part)].iloc[0]
        above=100*float(a.pressure_pa.gt(maximum*1000).mean());below=100*float(a.pressure_pa.lt(0).mean())
        selected.append(dict(part=part,target_time_s=target,actual_time_s=float(entry.time_s),paper_upper_kpa=maximum,
            native_max_kpa=float(a.pressure_pa.max()/1000),above_paper_scale_native_percent=above,below_zero_native_percent=below))
        for col,key in enumerate(['SPH','FEM','Current']):
            ax=fig.add_subplot(grid[row,col])
            if key!='Current':
                x0,y0,x1,y1=crops[key][row];ax.imshow(image[y0:y1,x0:x1],extent=[0,20,0,10],origin='upper')
                title=f'Paper {key}: {target:g} s'
            else:
                levels=np.linspace(0,maximum,13)
                artist=ax.tricontourf(a.x_m,a.z_m,a.pressure_pa/1000,levels=levels,norm=BoundaryNorm(levels,cmap.N),cmap=cmap,extend='both')
                title=f'Current: {entry.time_s:.6f} s\nmax {a.pressure_pa.max()/1000:.5g} kPa; >scale {above:.2f}%'
            ax.set(title=title,xlim=(0,20),ylim=(0,10),aspect='equal',xticks=[0,5,10,15,20],yticks=[0,5,10],xlabel='x (m)',ylabel='z (m)' if col==0 else '')
        fig.colorbar(artist,cax=fig.add_subplot(grid[row,3]),label='Pore pressure (kPa)')
    fig.suptitle('Lian 2023 Fig10: original paper SPH/FEM and returned HG+SPR run\nOriginal row limits and SPH palette; FEM retains its original colors. No smoothing or data clipping.',fontsize=13)
    png('fig10_compare',fig)
    p=OUT/(TAG+'_fig10_scales.csv');assert not p.exists();pd.DataFrame(selected).to_csv(p,index=False,float_format='%.17g');artifacts.append(bound(p))

    fig,axes=plt.subplots(1,2,figsize=(14,5.3),layout='constrained')
    axes[0].imshow(Image.open(refs['fig11']));axes[0].axis('off');axes[0].set_title('Paper Fig11: SPH / ABAQUS FEM')
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        valid=h.time_s.gt(0);axes[1].plot(h.time_s[valid],h.loc[valid,point+'_pressure_pa']/1000,ls,color=color,label='Current '+point)
    for point,marker in [('A','D'),('B','o')]:
        r=comparison[comparison.figure.eq('11')&comparison.paper_point.eq(point)]
        axes[1].errorbar(r.raster_time_s,r.value,yerr=r.value_uncertainty,fmt=marker,mfc='none',
            color='#b53131',capsize=3,label='Paper SPH '+point+' (raster)')
    axis_style(axes[1],'Actual saved time (s)','Excess pore pressure (kPa)',True)
    pressure_low=min(0.,float(h[['A_pressure_pa','B_pressure_pa']].min().min()/1000))
    pressure_high=max(5.,float(h[['A_pressure_pa','B_pressure_pa']].max().max()/1000))
    axes[1].set_ylim(pressure_low,pressure_high);axes[1].legend(fontsize=9);axes[1].set_title('Returned HG+SPR native material histories')
    fig.suptitle('Paper pressure-history comparison\nSaved data begin at 0.05 s; no reconstructed 0.01-0.05-s samples or imposed time shift.',fontsize=13)
    png('fig11_compare',fig)

    fig=plt.figure(figsize=(14,9),layout='constrained');grid=fig.add_gridspec(2,2,height_ratios=[.95,1])
    top=fig.add_subplot(grid[0,:]);top.imshow(Image.open(refs['fig12']));top.axis('off');top.set_title('Original paper Fig12: (a) A/B settlement, (b) signed horizontal displacement at 100 s')
    ax=fig.add_subplot(grid[1,0])
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        valid=h.time_s.gt(0);ax.plot(h.time_s[valid],h.loc[valid,point+'_settlement_mm']*10,ls,color=color,label='Current '+point)
    for point,marker in [('A','D'),('B','o')]:
        r=comparison[comparison.figure.eq('12a')&comparison.paper_point.eq(point)]
        ax.errorbar(r.raster_time_s,r.value*1e4,yerr=r.value_uncertainty*1e4,fmt=marker,mfc='none',
            color='#b53131',capsize=3,label='Paper SPH '+point+' (raster)')
    settlement_low=min(-5.,float(h[['A_settlement_mm','B_settlement_mm']].min().min()*10))
    settlement_high=max(20.,float(h[['A_settlement_mm','B_settlement_mm']].max().max()*10))
    axis_style(ax,'Actual saved time (s)',r'Downward settlement ($10^{-4}$ m)',True)
    ax.set_ylim(settlement_high,settlement_low);ax.legend(fontsize=9)
    ax=fig.add_subplot(grid[1,1]);ax.plot(profile.ux_m*1e4,profile.z0_m,color='#245d88',label='Current x0=1.25 m')
    for method,color,marker in [('FEM','#535353','D'),('SPH','#b53131','o')]:
        r=comparison[comparison.figure.eq('12b')&comparison.reference_method.eq(method)]
        ax.errorbar(r.value*1e4,r.elevation_m,xerr=r.value_uncertainty*1e4,fmt=marker,mfc='none',
            color=color,capsize=3,label='Paper '+method+' (raster)')
    ax.set(xlabel=r'Signed horizontal displacement ($10^{-4}$ m)',ylabel='Initial elevation (m)',ylim=(0,10));ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Native settlement and material-line displacement compared with the paper\nA/B: fixed material stencils. Signed profile uses initial x0=1.25 m, no absolute-value transformation.',fontsize=13)
    png('fig12_compare',fig)
    write_json(receipt,dict(passed=True,visual_review_passed=False,utc=utc(),native_safety_passed=audit['native_safety_passed'],
        paper_reference_accuracy_accepted=False,sources=sources,artifacts=artifacts,
        reference_type='Original numerical SPH/FEM paper raster, not analytical or original raw data',
        paraview_time_series_format='https://docs.paraview.org/en/latest/UsersGuide/dataIngestion.html',
        paraview_time_mapping='2001 actual saved times, independently JSON/file checked; GUI not exercised',
        probe_plot_ranges=dict(pressure_kpa=[pressure_low,pressure_high],settlement_1em4_m=[settlement_low,settlement_high],
            pressure_samples_outside_paper_range=int(((h[['A_pressure_pa','B_pressure_pa']]<0)|(h[['A_pressure_pa','B_pressure_pa']]>5000)).to_numpy().sum()),
            settlement_samples_outside_paper_range=int(((h[['A_settlement_mm','B_settlement_mm']]<-.5)|(h[['A_settlement_mm','B_settlement_mm']]>2)).to_numpy().sum())),
        plotting='Linear triangulation on actual saved coordinates; no smoothing, value clipping or time shifting',
        csv_data='Matching native history, selected fields and signed profile were sealed by the analysis receipt',
        limitations=['Native output cadence .05 s; paper starts at .01 s.',
            '25 manually reviewed sparse raster points with pixel uncertainty; not original raw SPH/FEM data or a full-curve error norm.',
            'FEM palette is preserved; native and SPH use the original SPH 12-band palette.']))
    print(receipt)


if __name__=='__main__':main()
