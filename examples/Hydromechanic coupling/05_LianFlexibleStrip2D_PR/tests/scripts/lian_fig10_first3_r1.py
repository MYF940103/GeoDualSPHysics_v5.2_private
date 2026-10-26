"""Paper Fig10 first-three-time comparison, original native pressure and scales."""
import json
from pathlib import Path
import fitz
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import numpy as np
import pandas as pd
from lian_release_r1 import CASE, TESTS, REPO, READER, native, bound, utc, write_json
from lian_mirror_review_r1 import sample

TAG='lian_fig10_first3_r1'
PDF=REPO/'src/papers/PDF/Lian 2023 u-pl.pdf'
RUNS={'strict_c':'lian_late15_r1','mirror_c':'lian_mirror15_r1_c','mirror_h':'lian_mirror15_r1_h'}
TIMES=[(.5,10,5.),(1.,20,5.),(3.,60,1.75)]
# Native pixels in the PDF's 1751x1949 embedded Fig10 image (xref63).
# Original FEM legends are retained; their Pa values correspond to row kPa limits.
CROPS={'SPH':[(22,52,840,468),(32,542,844,955),(32,1030,844,1437)],
       'FEM':[(940,60,1750,468),(940,546,1744,953),(937,1029,1744,1435)]}
# Twelve bands read from the original SPH colorbar, rounded to its RGB85 steps.
COLORS=np.array([[0,0,170],[0,0,255],[0,85,255],[0,170,255],[0,255,255],
    [85,255,170],[170,255,85],[255,255,0],[255,170,0],[255,85,0],[255,0,0],[170,0,0]])/255


def main():
    receipt=TESTS/'logs'/(TAG+'.check.json')
    assert not receipt.exists(), 'Retained comparison is never overwritten'
    ref_dir=TESTS/'outputs/lian_fig10_ref_r1'
    ref_dir.mkdir(exist_ok=True)
    image_path=ref_dir/'figure10.png'
    doc=fitz.open(PDF)
    image_ref=doc[16].get_images()[0]
    assert image_ref[0]==63 and image_ref[2:4]==(1751,1949)
    pix=fitz.Pixmap(doc,image_ref[0])
    if not image_path.exists():
        pix.save(str(image_path))
    source_image=np.asarray(Image.open(image_path).convert('RGB'))
    assert np.array_equal(source_image,np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,pix.n))
    sources=[bound(p) for p in [__file__,PDF,image_path,READER,
        TESTS/'scripts/lian_release_r1.py',TESTS/'scripts/lian_mirror_review_r1.py']]
    arrays,rows,outputs,pairs={},{},[],[]
    summary=[]
    for key,name in RUNS.items():
        folder=TESTS/'outputs'/name
        manifest_path=TESTS/'logs'/(name+'.run.json')
        manifest=json.loads(manifest_path.read_text())
        exit_code=manifest.get('exit_code',manifest.get('solver_exit_code'))
        assert exit_code==0 and manifest['owned_exited']
        assert abs(manifest['actual_final_time_s']-15)<2e-5
        expected={str(Path(e['path']).resolve()).lower():e['sha256'].lower() for e in manifest['outputs']}
        sources.append(bound(manifest_path))
        initial=native(folder,0)
        assert initial.pressure.eq(0).all(), 'PorePress must equal excess pressure in this zero-initial-pressure case'
        for path in [folder/'data/Part_0000.bi4',folder/'data/Part_Head.ibi4']:
            item=bound(path)
            assert item['sha256'].lower()==expected[item['path'].lower()]
            sources.append(item)
        for target,part,maximum in TIMES:
            path=folder/'data'/f'Part_{part:04d}.bi4'
            item=bound(path)
            assert item['sha256'].lower()==expected[item['path'].lower()]
            sources.append(item)
            a=native(folder,part)
            dt=5e-6 if key=='mirror_h' else 1e-5
            row=sample(a,initial,dt,key!='strict_c')
            assert abs(row['time_s']-target)<=1.01e-5
            assert len(a)==20301 and np.array_equal(a.id,initial.id)
            row.update(run=key,output_name=name,target_time_s=target,part=part,dt_s=dt,
                paper_colorbar_max_kpa=maximum,pressure_max_kpa=float(a.pressure.max()/1000),
                pressure_min_kpa=float(a.pressure.min()/1000),pressure_mean_kpa=float(a.pressure.mean()/1000),
                above_colorbar_nodes=int(a.pressure.gt(maximum*1000).sum()),
                above_colorbar_native_fraction_pct=float(100*a.pressure.gt(maximum*1000).mean()))
            peak=a.loc[a.pressure.idxmax()]
            row.update(peak_id=int(peak.id),peak_x_m=float(peak.x),peak_z_m=float(peak.z))
            summary.append(row)
            arrays[key,part]=a
            csv=TESTS/'figures'/f'{TAG}_{key}_part{part:04d}.csv'
            assert not csv.exists()
            pd.DataFrame(dict(id=a.id,x_m=a.x,z_m=a.z,pressure_pa=a.pressure,pressure_kpa=a.pressure/1000)).to_csv(
                csv,index=False,float_format='%.17g')
            outputs.append(bound(csv))
        print('Read original native frames:',name,flush=True)
    for target,part,maximum in TIMES:
        c,h,o=[arrays[k,part] for k in ['mirror_c','mirror_h','strict_c']]
        assert np.array_equal(c.id,h.id) and np.array_equal(c.id,o.id)
        assert float(c.time_s.iloc[0])==float(o.time_s.iloc[0])
        pairs.append(dict(target_time_s=target,part=part,coarse_time_s=float(c.time_s.iloc[0]),
            half_time_s=float(h.time_s.iloc[0]),
            half_pressure_rms_pa=float(np.sqrt(np.mean((c.pressure-h.pressure)**2))),
            half_pressure_max_abs_pa=float(abs(c.pressure-h.pressure).max()),
            mirror_strict_pressure_rms_pa=float(np.sqrt(np.mean((c.pressure-o.pressure)**2)))))
    summary=pd.DataFrame(summary)
    paired=pd.DataFrame(pairs)
    for label,frame in [('summary',summary),('pairs',paired)]:
        path=TESTS/'figures'/(TAG+'_'+label+'.csv')
        assert not path.exists()
        frame.to_csv(path,index=False,float_format='%.17g')
        outputs.append(bound(path))
    plt.rcParams.update({'font.size':10,'axes.titlesize':11})
    cmap=ListedColormap(COLORS)
    cmap.set_over(COLORS[-1])
    cmap.set_under('#b850b8')
    fig=plt.figure(figsize=(18,10),layout='constrained')
    grid=fig.add_gridspec(3,5,width_ratios=[1,1,1,1,.045])
    for r,(target,part,maximum) in enumerate(TIMES):
        levels=np.linspace(0,maximum,13)
        norm=BoundaryNorm(levels,cmap.N)
        for col,label in enumerate(['Paper SPH','Paper FEM','Current strict, 10 us','Mirror, 10 us']):
            ax=fig.add_subplot(grid[r,col])
            if col<2:
                x0,y0,x1,y1=CROPS[['SPH','FEM'][col]][r]
                ax.imshow(source_image[y0:y1,x0:x1],extent=[0,20,0,10],origin='upper')
                title=label+f' | t={target:g} s'
            else:
                key='strict_c' if col==2 else 'mirror_c'
                a=arrays[key,part]
                artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=levels,norm=norm,cmap=cmap,extend='both')
                record=summary[summary.run.eq(key)&summary.part.eq(part)].iloc[0]
                title=label+f' | actual {record.time_s:.6f} s\nmax {record.pressure_max_kpa:.4f} kPa; >bar {record.above_colorbar_native_fraction_pct:.2f}% nodes'
            ax.set(title=title,xlim=(0,20),ylim=(0,10),aspect='equal',xticks=[0,5,10,15,20],yticks=[0,5,10],
                xlabel='x (m)',ylabel='z (m)' if col==0 else '')
        cax=fig.add_subplot(grid[r,4])
        colorbar=fig.colorbar(artist,cax=cax,ticks=[0,1,2,3,4,5] if maximum==5 else [0,.5,1,1.5,1.75])
        colorbar.set_label('Excess pore pressure (kPa)')
    fig.suptitle('Lian2023 Fig10: first three times, original paper crops and actual native results\n'
        'Row scales: 0-5 / 0-5 / 0-1.75 kPa. New plots use the original SPH 12-band palette; FEM retains its own palette.\n'
        'No smoothing, zero-clipping or field rescaling. Over-range values remain in CSVs and are flagged; paper raster is not raw FEM data.',fontsize=13)
    path=TESTS/'figures'/(TAG+'_comparison.png')
    assert not path.exists()
    fig.savefig(path,dpi=180)
    plt.close(fig)
    outputs.append(bound(path))
    fig=plt.figure(figsize=(13,10),layout='constrained')
    grid=fig.add_gridspec(3,5,width_ratios=[1,1,.04,1,.04])
    for r,(target,part,maximum) in enumerate(TIMES):
        levels=np.linspace(0,maximum,13)
        for col,key in enumerate(['mirror_c','mirror_h']):
            a=arrays[key,part]
            ax=fig.add_subplot(grid[r,col])
            artist=ax.tricontourf(a.x,a.z,a.pressure/1000,levels=levels,cmap=cmap,extend='both')
            ax.set(title=f'Mirror {"10" if col==0 else "5"} us | actual {a.time_s.iloc[0]:.6f} s',
                xlabel='x (m)',ylabel='z (m)',xlim=(0,20),ylim=(0,10),aspect='equal')
        fig.colorbar(artist,cax=fig.add_subplot(grid[r,2]),label='kPa')
        c,h=arrays['mirror_c',part],arrays['mirror_h',part]
        delta=c.pressure-h.pressure
        limit=max(float(abs(delta).max()),1e-9)
        ax=fig.add_subplot(grid[r,3])
        artist=ax.tricontourf(c.x,c.z,delta,levels=np.linspace(-limit,limit,21),cmap='RdBu_r',extend='both')
        ax.set(title=f'Coarse minus half (native IDs)\nRMS={np.sqrt(np.mean(delta**2)):.4g} Pa',
            xlabel='x (m)',ylabel='z (m)',xlim=(0,20),ylim=(0,10),aspect='equal')
        fig.colorbar(artist,cax=fig.add_subplot(grid[r,4]),label='Difference (Pa)')
    fig.suptitle('Mirror 15-s pair: first-three-time native half-step comparison\nPressure scales match paper Fig10; differences use separately labeled Pa scales',fontsize=13)
    path=TESTS/'figures'/(TAG+'_half.png')
    assert not path.exists()
    fig.savefig(path,dpi=180)
    plt.close(fig)
    outputs.append(bound(path))
    write_json(receipt,dict(passed=True,visual_review_passed=False,paper_accuracy_accepted=False,utc=utc(),
        sources=sources,artifacts=outputs,paper_image_page=17,paper_image_xref=image_ref[0],
        paper_crops_pixels=CROPS,palette_rgb_85_steps=(COLORS*255).astype(int).tolist(),
        paper_times_and_limits=[dict(time_s=t,lower_kpa=0,upper_kpa=m) for t,_,m in TIMES],
        pairs=paired.to_dict('records'),limits=[
            'Paper SPH/FEM are original raster crops with no raw pressure fields; no whole-field RMSE or exact peak error against the paper is claimed.',
            'The paper colorbar upper bound is not automatically its actual maximum pressure.',
            'FEM inset legends remain present; raster colors are not used as quantitative FEM samples.',
            'Exceedance is a native-node fraction, not an integrated continuum area.',
            'Current physical load remains the original13-node +4% quadrature; no new solver or parameter change.']))
    print(summary[['run','target_time_s','time_s','pressure_max_kpa','above_colorbar_native_fraction_pct']].to_string(index=False),flush=True)
    print(paired.to_string(index=False),flush=True)


if __name__=='__main__':
    main()
