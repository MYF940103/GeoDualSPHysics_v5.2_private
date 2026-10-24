"""Offline .1-s native-ID field comparison after the numerical review passes."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS,bound
from spr_yao_review import native


def main():
    tag='spr_yao_gpu_load_grid10_r2';receipt=TESTS/'logs'/(tag+'.fields.json');assert not receipt.exists()
    review=TESTS/'logs'/(tag+'.review.json');r=json.loads(review.read_text());assert r['passed'] and r['frames_per_variant']==101
    stem=TESTS/'figures'/tag;paths=[str(stem)+'_'+k+'_final.csv' for k in ('faces_off','faces_on','faces_half')]
    off,on,half=[pd.read_csv(x,float_precision='round_trip') for x in paths]
    cpu_path=TESTS/'figures/spr_yao_grid10_r1_review_r2_faces_on_final.csv'
    cpu=pd.read_csv(cpu_path,float_precision='round_trip');initial=native(TESTS/'outputs'/(tag+'_faces_on'),0)
    for a in (off,half,cpu,initial):assert np.array_equal(a.id,on.id)
    t=float(on.time_s.iloc[0]);assert abs(t-.1)<1e-10 and abs(float(cpu.time_s.iloc[0])-t)<1e-10
    field=pd.DataFrame(dict(id=on.id,x0_m=initial.x,z0_m=initial.z,gpu_pressure_pa=on.pressure,
        gpu_settlement_mm=(initial.z-on.z)*1000,cpu_gpu_pressure_pa=on.pressure-cpu.pressure,
        cpu_gpu_settlement_mm=(cpu.z-on.z)*1000,spr_on_off_pressure_pa=on.pressure-off.pressure,
        spr_on_off_settlement_mm=(off.z-on.z)*1000))
    assert np.isfinite(field.to_numpy()).all()
    csv=TESTS/'figures'/(tag+'_fields.csv');field.to_csv(csv,index=False,mode='x')
    fig,axes=plt.subplots(2,3,figsize=(14,8.1));keys=[['gpu_pressure_pa','cpu_gpu_pressure_pa','spr_on_off_pressure_pa'],
        ['gpu_settlement_mm','cpu_gpu_settlement_mm','spr_on_off_settlement_mm']]
    titles=[['GPU SPR on: pore pressure (Pa)','GPU minus CPU, SPR on (Pa)','GPU SPR on minus off (Pa)'],
        ['GPU SPR on: material settlement (mm)','GPU minus CPU settlement (mm)','GPU SPR on minus off settlement (mm)']]
    for row in range(2):
        for col in range(3):
            ax=axes[row,col];v=field[keys[row][col]];kwargs={}
            if col:
                limit=max(float(abs(v).max()),1e-14);kwargs=dict(norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),cmap='RdBu_r')
            else:kwargs=dict(cmap='viridis')
            artist=ax.scatter(field.x0_m,field.z0_m,c=v,s=4,marker='s',linewidths=0,rasterized=True,**kwargs)
            ax.set(title=titles[row][col],xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal')
            fig.colorbar(artist,ax=ax,shrink=.8,pad=.03)
    fig.suptitle('Yao native material fields at actual t=%.12f s'%t)
    fig.tight_layout(rect=(0,.065,1,.95));fig.text(.5,.02,'HG/NoPen off; same 20301 IDs. On/off differences are not theory errors. Existing 59/61-node strip quadrature retained.',ha='center',fontsize=9)
    png=TESTS/'figures'/(tag+'_fields.png');assert not png.exists();fig.savefig(png,dpi=160);plt.close(fig)
    maxima={key:float(abs(field[key]).max()) for row in keys for key in row}
    with receipt.open('x',encoding='utf8') as stream:json.dump(dict(passed=True,actual_time_s=t,native_soil_count=len(field),max_abs=maxima,
        evidence=[bound(__file__),bound(review),bound(cpu_path)]+[bound(x) for x in paths],outputs=[bound(csv),bound(png)],visual_inspected=False,physical_acceptance=False),stream,indent=2)
    print(json.dumps(maxima,indent=2))


if __name__=='__main__':main()
