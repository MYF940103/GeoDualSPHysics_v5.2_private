"""Repair only draft field-figure typography, retaining all numerical data."""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from spr_yao_short import TESTS,bound


def main():
    tag='spr_yao_gpu_load_grid10_r2';receipt=TESTS/'logs'/(tag+'.fields_r2.check.json');assert not receipt.exists()
    source=TESTS/'figures'/(tag+'_fields.csv');a=pd.read_csv(source,float_precision='round_trip');assert len(a)==20301 and np.isfinite(a.to_numpy()).all()
    fig,axes=plt.subplots(2,3,figsize=(14,8.1))
    keys=[['gpu_pressure_pa','cpu_gpu_pressure_pa','spr_on_off_pressure_pa'],['gpu_settlement_mm','cpu_gpu_settlement_mm','spr_on_off_settlement_mm']]
    titles=[['GPU SPR on\nPore pressure (Pa)','GPU minus CPU, SPR on\nPore pressure difference (Pa)','GPU SPR on minus off\nPore pressure difference (Pa)'],
        ['GPU SPR on\nMaterial settlement (mm)','GPU minus CPU, SPR on\nSettlement difference (mm)','GPU SPR on minus off\nSettlement difference (mm)']]
    for row in range(2):
        for col in range(3):
            ax=axes[row,col];v=a[keys[row][col]];kwargs=dict(cmap='viridis')
            if col:
                limit=max(float(abs(v).max()),1e-14);kwargs=dict(norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),cmap='RdBu_r')
            dots=ax.scatter(a.x0_m,a.z0_m,c=v,s=4,marker='s',linewidths=0,rasterized=True,**kwargs)
            ax.set(xlabel='Initial material x (m)',ylabel='Initial material z (m)',xlim=(-10.1,10.1),ylim=(-.1,10.1),aspect='equal');ax.set_title(titles[row][col],fontsize=11)
            fig.colorbar(dots,ax=ax,shrink=.78,pad=.03)
    fig.suptitle('Yao native material fields at actual t = 0.1 s',fontsize=15)
    fig.tight_layout(rect=(0,.065,1,.94));fig.text(.5,.02,'HG/NoPen off; 20301 same IDs. On/off differences are not theory errors. Original 59/61-node load quadrature retained.',ha='center',fontsize=9)
    png=TESTS/'figures'/(tag+'_fields_r2.png');assert not png.exists();fig.savefig(png,dpi=160);plt.close(fig)
    with receipt.open('x',encoding='utf8') as stream:json.dump(dict(passed=True,numerical_data_unchanged=True,old_figure_retained_as_draft=True,
        evidence=[bound(__file__),bound(source),bound(TESTS/'logs'/(tag+'.fields.json'))],outputs=[bound(png)],visual_inspected=False),stream,indent=2)


if __name__=='__main__':main()
