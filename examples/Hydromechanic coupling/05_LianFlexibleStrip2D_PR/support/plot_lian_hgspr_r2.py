"""Merge the verified early save supplement with unchanged100s data and plot new r2 artifacts."""
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

CASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(CASE/'tests/scripts'))
from lian_release_r1 import bound,utc

TAG='lian_hgspr100_r2'; EARLY='lian_hgspr_early_r1'
OUT=CASE/'figures'; LOGS=CASE/'tests/logs'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(entries):
    for entry in entries:
        actual=bound(entry['path'])
        assert actual['sha256'].lower()==entry['sha256'].lower() and actual['bytes']==entry['bytes'],entry['path']


def main():
    receipt=LOGS/(TAG+'.plots.json')
    targets=[OUT/(TAG+'_'+s) for s in ['history.csv','paper_points.csv','history.png','fig11_compare.png','fig12_compare.png']]
    assert not receipt.exists() and not any(p.exists() for p in targets),'Fresh analysis tag only'
    ep=LOGS/(EARLY+'.check.json'); fp=LOGS/'lian_hgspr100_r1.check.json'
    early,formal=read(ep),read(fp)
    assert early['passed'] and early['native_safety_passed'] and early['prefix_passed'] and early['exact_shared_samples']==21
    assert formal['passed'] and formal['native_safety_passed'] and formal['frames']==2001
    verify(early['source_links']+early['artifacts']);verify(formal['artifacts'])
    newpath=CASE/'tests/figures'/(EARLY+'_history.csv');oldpath=OUT/'lian_hgspr100_r1_history.csv'
    e=pd.read_csv(newpath,float_precision='round_trip');old=pd.read_csv(oldpath,float_precision='round_trip')
    assert len(e)==101 and len(old)==2001 and set(e.columns)==set(old.columns)
    cut=int(e.saved_step.iloc[-1]);assert cut==int(old[old.part.eq(20)].saved_step.iloc[0])
    assert float(e.time_s.iloc[-1])==float(old[old.part.eq(20)].time_s.iloc[0])
    completion=read(LOGS/(EARLY+'.completion.json'))
    def native_map(entries):
        return {int(Path(v['path']).stem.split('_')[-1]):v['sha256'] for v in entries
                if Path(v['path']).name.startswith('Part_') and Path(v['path']).suffix=='.bi4'}
    emap=native_map(completion['outputs']);omap=native_map(formal['sources'])
    assert len(emap)==101 and len(omap)==2001
    chunks=[]
    for frame,tag,folder,mapping in [(e,EARLY,'tests/outputs/'+EARLY,emap),
            (old[old.saved_step.gt(cut)].copy(),'lian_hgspr100_r1','CaseLianFlexibleStrip2D_PR_release_HGSPR_out',omap)]:
        frame=frame.copy();frame['source_tag']=tag;frame['source_output_relative']=folder
        frame['source_part']=frame.part.astype(int)
        frame['source_native_sha256']=[mapping[int(p)] for p in frame.part]
        frame=frame.drop(columns='part');chunks.append(frame)
    h=pd.concat(chunks,ignore_index=True);h.insert(0,'merged_index',np.arange(len(h)))
    assert len(h)==2081 and h.time_s.is_monotonic_increasing and h.time_s.is_unique
    assert h.saved_step.is_unique and h.saved_step.is_monotonic_increasing
    for col in old.columns:
        if col=='part':continue
        a,b=h.iloc[-1][col],old.iloc[-1][col]
        assert (pd.isna(a) and pd.isna(b)) or a==b,('Final100s value changed',col)
    profilepath=OUT/'lian_hgspr100_r1_horizontal_profile.csv'
    profile=pd.read_csv(profilepath,float_precision='round_trip')
    refpath=LOGS/'lian_server_return_r1_reference_points.json';reference=read(refpath)
    verify(reference['sources']+reference['artifacts'])
    comparisons=[]
    for point in reference['points']:
        row=dict(point)
        if point['figure'] in ['11','12a']:
            target=point['raster_time_s'];col=point['paper_point']+('_pressure_pa' if point['figure']=='11' else '_settlement_mm')
            assert h.time_s.iloc[0]<=target<=h.time_s.iloc[-1]
            row['current_value']=float(np.interp(target,h.time_s,h[col].to_numpy()*.001))
            j=min(max(int(np.searchsorted(h.time_s,target)),1),len(h)-1)
            row.update(native_before_time_s=float(h.time_s.iloc[j-1]),native_after_time_s=float(h.time_s.iloc[j]),
                source_before=h.source_tag.iloc[j-1],source_after=h.source_tag.iloc[j],
                matching='Linear temporal interpolation of actual native observations only for raster-coordinate comparison; never a prefix gate.')
        else:
            row['current_value']=float(np.interp(point['elevation_m'],profile.z0_m,profile.ux_m))
            row['matching']='Unchanged100s signed initial-material x0=1.25m profile; linear initial-elevation interpolation.'
        row['current_minus_reference']=row['current_value']-point['value']
        row['relative_difference_percent']=100*row['current_minus_reference']/point['value']
        comparisons.append(row)
    comparison=pd.DataFrame(comparisons);artifacts=[]
    for path,frame in [(targets[0],h),(targets[1],comparison)]:
        frame.to_csv(path,index=False,float_format='%.17g');artifacts.append(bound(path))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.titlesize':11})
    def png(label,fig):
        path=OUT/(TAG+'_'+label+'.png');fig.savefig(path,dpi=180);plt.close(fig)
        with Image.open(path) as im:im.verify()
        artifacts.append(bound(path))
    def axis(ax,xlabel,ylabel,log=False):
        ax.set(xlabel=xlabel,ylabel=ylabel,xlim=(.01,100) if log else (0,100))
        if log:
            ax.set_xscale('log');ax.set_xticks([.01,.1,1,10,100],['0.01','0.1','1','10','100'])
        ax.grid(alpha=.2)
    caption='0–1 s: new 0.01 s saves on RTX 3050; later: unchanged A6000 data. Shared states: 34 columns, 0 ULP.'
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    positive=h.time_s.gt(0)
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        axes[0,0].plot(h.time_s[positive],h.loc[positive,point+'_pressure_pa']/1000,ls,color=color,label=point)
        axes[0,1].plot(h.time_s[positive],h.loc[positive,point+'_settlement_mm'],ls,color=color,label=point)
    axis(axes[0,0],'Actual saved time (s)','Material pore pressure (kPa)',True)
    axis(axes[0,1],'Actual saved time (s)','Downward material settlement (mm)',True)
    for ax in axes[0]:ax.legend()
    axes[1,0].plot(h.time_s,h.force_N_m/1000,color='#245d88');axis(axes[1,0],'Actual saved time (s)','Applied resultant (kN/m)')
    for col,ls,label in [('pressure_max_pa','-','Native maximum'),('pressure_mean_pa','--','Native mean'),
                        ('A_pressure_pa',':','Material A'),('B_pressure_pa','-.','Material B')]:
        tail=h.time_s.ge(3)
        axes[1,1].semilogy(h.time_s[tail],h.loc[tail,col].where(h.loc[tail,col].gt(0)),ls,label=label)
    axes[1,1].set(xlabel='Actual saved time (s)',ylabel='Late pore pressure (Pa)',xlim=(3,100));axes[1,1].grid(alpha=.2);axes[1,1].legend(fontsize=9)
    fig.suptitle('Lian HG + SPR: complete history with a verified early-save supplement\n'+caption,fontsize=12)
    png('history',fig)
    refs={key:CASE/'tests/figures'/('lian_server_return_r1_reference_'+key+'.png') for key in ['fig11','fig12']}
    fig,axes=plt.subplots(1,2,figsize=(14,5.5),layout='constrained')
    axes[0].imshow(Image.open(refs['fig11']));axes[0].axis('off');axes[0].set_title('Paper Fig11: SPH / ABAQUS FEM')
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        axes[1].plot(h.time_s[positive],h.loc[positive,point+'_pressure_pa']/1000,ls,color=color,label='Current '+point)
    for point,marker in [('A','D'),('B','o')]:
        r=comparison[comparison.figure.eq('11')&comparison.paper_point.eq(point)]
        axes[1].errorbar(r.raster_time_s,r.value,yerr=r.value_uncertainty,fmt=marker,mfc='none',color='#b53131',capsize=3,label='Paper SPH '+point+' (raster)')
    axis(axes[1],'Actual saved time (s)','Excess pore pressure (kPa)',True)
    axes[1].set_ylim(min(0.,float(h[['A_pressure_pa','B_pressure_pa']].min().min()/1000)),
                      max(5.,float(h[['A_pressure_pa','B_pressure_pa']].max().max()/1000)))
    axes[1].legend(fontsize=9);axes[1].set_title('Native observations: early 0.01 s cadence, later 0.05 s')
    fig.suptitle('Paper pressure-history comparison with measured early samples\n'+caption,fontsize=12)
    png('fig11_compare',fig)
    fig=plt.figure(figsize=(14,9),layout='constrained');grid=fig.add_gridspec(2,2,height_ratios=[.95,1])
    top=fig.add_subplot(grid[0,:]);top.imshow(Image.open(refs['fig12']));top.axis('off')
    top.set_title('Original paper Fig12: A/B settlement and signed horizontal displacement at 100 s')
    ax=fig.add_subplot(grid[1,0])
    for point,color,ls in [('A','#245d88','-'),('B','#b36a26','--')]:
        ax.plot(h.time_s[positive],h.loc[positive,point+'_settlement_mm']*10,ls,color=color,label='Current '+point)
    for point,marker in [('A','D'),('B','o')]:
        r=comparison[comparison.figure.eq('12a')&comparison.paper_point.eq(point)]
        ax.errorbar(r.raster_time_s,r.value*1e4,yerr=r.value_uncertainty*1e4,fmt=marker,mfc='none',color='#b53131',capsize=3,label='Paper SPH '+point+' (raster)')
    low=min(-5.,float(h[['A_settlement_mm','B_settlement_mm']].min().min()*10))
    high=max(20.,float(h[['A_settlement_mm','B_settlement_mm']].max().max()*10))
    axis(ax,'Actual saved time (s)',r'Downward settlement ($10^{-4}$ m)',True);ax.set_ylim(high,low);ax.legend(fontsize=9)
    ax=fig.add_subplot(grid[1,1]);ax.plot(profile.ux_m*1e4,profile.z0_m,color='#245d88',label='Unchanged current x0 = 1.25 m')
    for method,color,marker in [('FEM','#535353','D'),('SPH','#b53131','o')]:
        r=comparison[comparison.figure.eq('12b')&comparison.reference_method.eq(method)]
        ax.errorbar(r.value*1e4,r.elevation_m,xerr=r.value_uncertainty*1e4,fmt=marker,mfc='none',color=color,capsize=3,label='Paper '+method+' (raster)')
    ax.set(xlabel=r'Signed horizontal displacement ($10^{-4}$ m)',ylabel='Initial elevation (m)',ylim=(0,10));ax.grid(alpha=.2);ax.legend()
    fig.suptitle('Material settlement with early-save supplement; 100 s signed profile unchanged\n'+caption,fontsize=12)
    png('fig12_compare',fig)
    sourcepaths=[Path(__file__),ep,fp,newpath,oldpath,profilepath,refpath,LOGS/(EARLY+'.prefix.json'),
        LOGS/(EARLY+'.completion.json'),CASE/'tests/scripts/lian_release_r1.py',*refs.values()]
    result=dict(passed=True,utc=utc(),visual_review_passed=False,physical_accuracy_changed=False,
        full_cycle_half_step_tested=False,formal100_rerun=False,merged_rows=len(h),early_rows=101,late_original_rows=1980,
        source_boundary_time_s=float(e.time_s.iloc[-1]),source_boundary_saved_step=cut,
        exact_common_34column_samples=21,source_row_provenance_retained=True,final_observables_unchanged=True,
        paper_material_stencils=formal['paper_material_stencils'],sources=[bound(p) for p in sourcepaths],artifacts=artifacts,
        unchanged_formal_artifacts=[bound(OUT/name) for name in ['lian_hgspr100_r1_fig10_compare.png',
            'lian_hgspr100_r1_fig10_scales.csv','lian_hgspr100_r1_horizontal_profile.csv','lian_hgspr100_r1_stress_boundary.png']],
        limitations=['Composite observations from two fresh-start trajectories, verified at21 exact shared physical states; not an HG PART restart.',
            'Only output cadence/duration changed. This does not repair physics or create new half-step evidence.',
            'Original100s all-frame native safety and accepted late data are reused unchanged.',
            'Source-clock drainage remains; early1s supplement has no active drainage samples if source_t<1.',
            'Paper SPH/FEM raster points are numerical references with pixel uncertainty, not exact theory or original raw curves.',
            'Temporal interpolation is used only to report sparse raster-coordinate comparisons, never for native equivalence.',
            'Original13-node13000N/m resultant remains4percent above ideal12500N/m; not renormalized.',
            'Field Fig10, signed100s profile and original particle VTK series remain the unchanged r1 artifacts.'])
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(receipt,flush=True)


if __name__=='__main__':main()
