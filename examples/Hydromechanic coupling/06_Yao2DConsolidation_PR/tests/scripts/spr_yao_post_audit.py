"""Offline post-ramp fields/regions and an independent CSV/manifest audit."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS,bound
from spr_yao_review import native
from spr_yao_gpu_post_review import load_state


def main():
    tag='spr_yao_gpu_post03_r1';receipt=TESTS/'logs'/(tag+'.audit_r1.json');assert not receipt.exists()
    run=load_state(tag);review=TESTS/'logs'/(tag+'.review.json');check=json.loads(review.read_text());assert check['passed']
    for item in check['evidence']+check['outputs']:assert bound(item['path'])['sha256']==item['sha256']
    h=pd.read_csv(TESTS/'figures'/(tag+'_history.csv'),float_precision='round_trip')
    comparisons=pd.read_csv(TESTS/'figures'/(tag+'_comparison.csv'),float_precision='round_trip')
    variants=('faces_off','faces_on','faces_half');assert h.groupby('variant').size().eq(301).all()
    half=comparisons[comparisons.kind.eq('GPU_half')];assert len(half)==301
    assert half.pressure_rms_pa.le(5).all() and half.max_material_displacement_mm.le(.005).all()
    assert check['matching_native_samples_0ulp']==dict.fromkeys(variants,101)
    assert comparisons[comparisons.kind.eq('CPU_GPU')].time_s.max()<.1000001
    initial=native(TESTS/'outputs'/(tag+'_faces_on'),0);assert len(initial)==20301 and initial.id.is_unique
    top=np.isclose(initial.z,10,atol=1e-8);strip=abs(initial.x)<3-1e-8
    regions=dict(all=np.ones(len(initial),dtype=bool),near_fixed_wall=(initial.z<.200001)|(abs(initial.x)>9.799999),
        bottom_corner=(initial.z<.5)&(abs(initial.x)>9.5))
    selected=[];evidence=[bound(__file__),bound(review),bound(TESTS/'logs'/(tag+'.status.json'))];finals={}
    for part in (0,100,150,200,250,300):
        frames={v:native(TESTS/'outputs'/(tag+'_'+v),part) for v in variants}
        for a in frames.values():assert np.array_equal(a.id,initial.id) and abs(a.time_s.iloc[0]-part*.001)<1e-10
        on,off=frames['faces_on'],frames['faces_off']
        dp=on.pressure.to_numpy()-off.pressure.to_numpy()
        ds=(on.pressure-on.sigma_zz).to_numpy()-(off.pressure-off.sigma_zz).to_numpy()
        du=(off.z.to_numpy()-on.z.to_numpy())*1000
        movement=np.linalg.norm(on[['x','z']].to_numpy()-off[['x','z']].to_numpy(),axis=1)*1000
        for region,mask in regions.items():
            selected.append(dict(time_s=float(on.time_s.iloc[0]),part=part,region=region,native_count=int(mask.sum()),
                pressure_on_off_rms_pa=float(np.sqrt(np.mean(dp[mask]**2))),pressure_on_off_abs_max_pa=float(abs(dp[mask]).max()),
                compression_total_stress_on_off_rms_pa=float(np.sqrt(np.mean(ds[mask]**2))),
                settlement_on_off_abs_max_mm=float(abs(du[mask]).max()),movement_on_off_max_mm=float(movement[mask].max())))
        if part==300:finals=frames
    regions_csv=TESTS/'figures'/(tag+'_regions_r1.csv');pd.DataFrame(selected).to_csv(regions_csv,index=False,mode='x')
    on,off,fine=[finals[v] for v in ('faces_on','faces_off','faces_half')]
    field=pd.DataFrame(dict(id=initial.id,x0_m=initial.x,z0_m=initial.z,
        pressure_pa=on.pressure,pressure_on_off_pa=on.pressure-off.pressure,pressure_on_half_pa=on.pressure-fine.pressure,
        settlement_mm=(initial.z-on.z)*1000,settlement_on_off_mm=(off.z-on.z)*1000,settlement_on_half_mm=(fine.z-on.z)*1000,
        total_compression_pa=on.pressure-on.sigma_zz,
        total_compression_on_off_pa=(on.pressure-on.sigma_zz)-(off.pressure-off.sigma_zz),
        total_compression_on_half_pa=(on.pressure-on.sigma_zz)-(fine.pressure-fine.sigma_zz)))
    fields_csv=TESTS/'figures'/(tag+'_fields_r1.csv');field.to_csv(fields_csv,index=False,mode='x')
    fig,axes=plt.subplots(3,3,figsize=(15,11));columns=['SPR on','SPR on minus off','SPR on minus half dt']
    keys=[['pressure_pa','pressure_on_off_pa','pressure_on_half_pa'],['settlement_mm','settlement_on_off_mm','settlement_on_half_mm'],
        ['total_compression_pa','total_compression_on_off_pa','total_compression_on_half_pa']]
    labels=['Pore pressure (kPa)','Material settlement (mm)','Vertical total compression (kPa)']
    for row in range(3):
        for col in range(3):
            ax=axes[row,col];v=field[keys[row][col]]/(1 if row==1 else 1000);kwargs=dict(cmap='viridis')
            if col:
                limit=max(float(abs(v).max()),1e-14);kwargs=dict(cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit))
            dots=ax.scatter(field.x0_m,field.z0_m,c=v,s=3,marker='s',linewidths=0,rasterized=True,**kwargs)
            ax.set(xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal')
            ax.set_title(columns[col]+'\n'+labels[row],fontsize=10);fig.colorbar(dots,ax=ax,pad=.04,shrink=.82)
    fig.suptitle('Yao GPU native material fields at actual t = 0.3 s',fontsize=15)
    fig.tight_layout(rect=(0,.045,1,.96));fig.text(.5,.012,'Independent colorbar ranges; same 20301 IDs; HG/NoPen off. On/off differences are not theory error. CPU comparison ends at 0.1 s.',ha='center',fontsize=9)
    fields_png=TESTS/'figures'/(tag+'_fields_r1.png');assert not fields_png.exists();fig.savefig(fields_png,dpi=150);plt.close(fig)
    colors={'faces_off':'#696969','faces_on':'#2166a5','faces_half':'#b18b2b'}
    fig,axes=plt.subplots(3,2,figsize=(12,10))
    for variant,g in h.groupby('variant'):
        for ax,key,scale in zip(axes[:2].flat,['max_pressure_pa','strip_settlement_mm','max_total_stress_pa','corner_pressure_rms_pa'],[1000,1,1000,1000]):
            ax.plot(g.time_s,g[key]/scale,color=colors[variant],ls='--' if variant=='faces_half' else '-',label=variant)
    for ax,key in zip(axes[2],['pressure_rms_pa','max_material_displacement_mm']):ax.plot(half.time_s,half[key],color='#2166a5',label='GPU coarse vs half')
    for ax,title in zip(axes.flat,['Maximum pore pressure (kPa)','59 original top materials: mean settlement (mm)',
        'Maximum absolute vertical total stress (kPa)','Bottom-corner pore-pressure RMS (kPa)',
        'GPU half pressure RMS (Pa); original limit = 5','GPU half material movement (mm); limit = 0.005']):
        ax.set(title=title,xlabel='Actual saved time (s)',xlim=(0,.3));ax.set_xticks(np.arange(0,.3001,.05));ax.axvline(.1,color='.65',ls=':',lw=1);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Yao GPU 0.3-s post-ramp numerical review',fontsize=15);fig.tight_layout(rect=(0,.05,1,.96))
    fig.text(.5,.015,'Dotted line: ramp end at 0.1 s. Error panels are zoomed; limits enforced over all 301 samples. Not full 2-D theory acceptance.',ha='center',fontsize=9)
    history_png=TESTS/'figures'/(tag+'_mechanics_r1.png');assert not history_png.exists();fig.savefig(history_png,dpi=150);plt.close(fig)
    force={v:h[h.variant.eq(v)].force_N_m.to_numpy() for v in variants};force_diff=float(abs(force['faces_on']-force['faces_off']).max())
    assert force_diff==0
    post=h[h.time_s.gt(.1000001)];assert post.loaded_count.eq(61).all()
    actual_force=float(abs(post.force_N_m).iloc[-1]);ideal=5000*6
    metadata={}
    for variant in variants:
        path=TESTS/'figures'/(tag+'_'+variant+'_metadata.csv');a=pd.read_csv(path,float_precision='round_trip');active=a[a.part.gt(0)]
        assert len(a)==301 and a.nout.eq(0).all() and a.native_count.eq(21945).all() and active.has_dterror.eq(1).all() and active.dterror_s.lt(0).all()
        dt=1e-5 if variant=='faces_half' else 2e-5;assert active.dt_min_s.eq(dt).all() and active.dt_max_s.eq(dt).all()
        metadata[variant]=dict(mechanical_limit_min_s=float(dt-active.dterror_s.max()),pore_limit_s=check['metadata'][variant]['pore_limit_s'])
        assert dt<=metadata[variant]['pore_limit_s'];evidence.append(bound(path))
    after=half[half.time_s.gt(.1000001)]
    result=dict(passed=True,physical_acceptance=False,actual_final_times_s=check['actual_final_times_s'],all_half_samples=301,
        full_half_max=dict(pressure_rms_pa=float(half.pressure_rms_pa.max()),material_mm=float(half.max_material_displacement_mm.max())),
        post_ramp_half_max=dict(pressure_rms_pa=float(after.pressure_rms_pa.max()),material_mm=float(after.max_material_displacement_mm.max())),
        cpu_comparison_end_s=.1,off_on_saved_force_max_difference_N_m=force_diff,post_ramp_force_abs_N_m=actual_force,ideal_force_N_m=ideal,
        post_ramp_force_bias_percent=100*(actual_force/ideal-1),selected_region_times_only=[0,.1,.15,.2,.25,.3],
        final_histories=h.groupby('variant').tail(1).to_dict('records'),metadata=metadata,
        limitations=['Original nodal 59/61 load quadrature retained','No CPU control after .1 s','Completion dt-error reset sentinel not used as physical limit','No theory/long-cycle/plastic/rotating-wall acceptance'],
        evidence=evidence,outputs=[bound(x) for x in (regions_csv,fields_csv,fields_png,history_png)],visual_inspected=False)
    with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence','outputs','final_histories')},indent=2))


if __name__=='__main__':main()
