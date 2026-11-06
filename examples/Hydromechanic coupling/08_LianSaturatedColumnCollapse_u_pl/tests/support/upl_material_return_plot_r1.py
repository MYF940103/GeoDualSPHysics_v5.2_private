"""Fresh plot from closed material CSV only. No program/solver or equation evaluation."""
from pathlib import Path
import csv,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
B=Path(__file__).resolve().parents[1]
raw=B/'outputs/upl_material_return_CPU_result_r1/points.csv'
png=B/'figures/upl_material_return_radial_r1.png'
output=B/'figures/upl_material_return_radial_r1.csv'
assert not png.exists() and not output.exists()
rows=list(csv.DictReader(raw.open(encoding='utf-8',newline='')))
branches=['linked_legacy','consistent_full_constant_psi','consistent_dev_constant_psi','consistent_dev_decay_psi']
labels=['Linked legacy','Consistent / full history','Consistent / dev history','Consistent / dev + psi decay']
angles=[0.,2.5,-5.];records=[]
for angle in angles:
 for branch in branches:
  group=[r for r in rows if r['branch']==branch and abs(float(r['psi0_deg'])-angle)<1e-6]
  ordinary=[r for r in group if r['path'] in ('first_yield_nonzero_shear','further_loading_nonzero_shear')]
  assert len(ordinary)==4 and all(r['return_available']=='1' for r in ordinary)
  preset=[r for r in group if r['path']=='preset_kappa_nonzero_shear'][0]
  records.append({'psi0_target_deg':angle,'branch':branch,'cp_Pa':float(group[0]['cp_Pa']),'ordinary_loading_rows':4,'ordinary_max_abs_saved_kappa_yield_residual_Pa':max(abs(float(r['f_return_saved_Pa']))for r in ordinary),'ordinary_max_abs_continuous_kappa_yield_residual_Pa':max(abs(float(r['f_return_continuous_Pa']))for r in ordinary),'separate_kappa_0p5_saved_residual_Pa':float(preset['f_return_saved_Pa']),'separate_preset_old_kappa':float(preset['kappa_old_float']),'separate_preset_end_kappa_continuous':float(preset['kappa_continuous']),'separate_preset_psi_at_old_deg':float(preset['psi_at_old_deg']),'separate_preset_psi_at_end_deg':float(preset['psi_at_continuous_deg'])})
with output.open('x',encoding='utf-8',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
fig,ax=plt.subplots(figsize=(12,6.3));x=np.arange(3);width=.19
for j,(branch,label)in enumerate(zip(branches,labels)):
 y=[next(r['ordinary_max_abs_saved_kappa_yield_residual_Pa']for r in records if r['branch']==branch and r['psi0_target_deg']==angle)for angle in angles]
 bars=ax.bar(x+(j-1.5)*width,y,width,label=label)
 for bar,value in zip(bars,y):ax.text(bar.get_x()+bar.get_width()/2,value*1.3,f'{value:.2e}',ha='center',va='bottom',fontsize=8.5,rotation=0)
ax.set_yscale('log');ax.set_ylim(1e-9,40);ax.set_xticks(x,[r'$\psi_0=0^\circ$  ($c_p=5$ kPa)',r'$\psi_0=+2.5^\circ$  ($c_p=5$ kPa)',r'$\psi_0=-5^\circ$  ($c_p=7.5$ kPa)']);ax.set_ylabel(r'Max $|f(\sigma_{new},\kappa_{saved,float})|$ [Pa]');ax.grid(axis='y',which='major',alpha=.3);ax.set_axisbelow(True)
fig.suptitle('Material-point radial return: yield residual after float history writeback',fontsize=14,y=.98)
ax.set_title('Four ordinary nonzero-shear loading points per group; algebraic residual, not spatial accuracy',fontsize=10,pad=12)
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.13),ncol=2,fontsize=10,frameon=False)
fig.text(.5,.045,'Apex diagnostics excluded: 18 candidate rows unsupported; 3 legacy hydrostatic rows nonfinite. No plastic release.',ha='center',fontsize=9)
fig.text(.5,.015,'Float material constants and saved kappa retained. Preset kappa=0.5 diagnostics are separate CSV columns.',ha='center',fontsize=9)
fig.subplots_adjust(left=.09,right=.985,top=.87,bottom=.27)
fig.savefig(png,dpi=180);plt.close(fig)
print(png);print(output)
