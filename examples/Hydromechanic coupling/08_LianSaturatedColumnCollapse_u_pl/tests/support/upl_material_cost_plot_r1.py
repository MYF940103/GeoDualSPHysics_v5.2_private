"""Plot the completed same-model material comparison; no new calculation."""
import csv,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1];src=T/'outputs/upl_material_cost_r1/result';fig=T/'figures/upl_material_cost_accuracy_r1.png'
assert json.loads((T/'logs/upl_material_cost_r1.check.json').read_text())['passed']
paths=list(csv.DictReader((src/'accuracy_by_path.csv').open()));timings=list(csv.DictReader((src/'cost_summary.csv').open()))
error=[]
for method in ('linearized_dev','endpoint'):
    for n in (8,16,32,64):
        rows=[r for r in paths if r['method']==method and int(r['N'])==n]
        assert len(rows)==21
        error.append(dict(method=method,increments_per_segment=n,material_paths=len(rows),max_stress_component_error_Pa=max(float(r['max_stress_component_error_Pa']) for r in rows)))
outputs=[fig,T/'figures/upl_material_cost_accuracy_r1_error.csv',T/'figures/upl_material_cost_accuracy_r1_timing.csv'];assert not any(p.exists() for p in outputs)
for p,rows in zip(outputs[1:],(error,timings)):
    with p.open('x',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
plt.rcParams.update({'font.size':11,'axes.grid':True,'grid.alpha':.22})
f,axes=plt.subplots(1,2,figsize=(11.5,4.5),constrained_layout=True);colors={'linearized_dev':'#d17b16','endpoint':'#2466a5'};labels={'linearized_dev':'Taylor, dev kappa','endpoint':'Endpoint, dev kappa'}
for method in colors:
    rows=[r for r in error if r['method']==method]
    axes[0].plot([r['increments_per_segment'] for r in rows],[r['max_stress_component_error_Pa'] for r in rows],'-o',label=labels[method],color=colors[method])
axes[0].set(xscale='log',yscale='log',xlabel='Material increments per load segment',ylabel='Worst stress component path error [Pa]',title='Same model: 21 smooth/elastic paths');axes[0].set_xticks([8,16,32,64],['8','16','32','64']);axes[0].xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter());axes[0].legend()
for i,phase in enumerate(('fixed_common_incoming','independent_paths')):
    for j,method in enumerate(colors):
        r=next(r for r in timings if r['phase']==phase and r['method']==method);value=float(r['median_ns_per_return']);x=i+(j-.5)*.34
        axes[1].bar(x,value,.32,color=colors[method],label=labels[method] if i==0 else None);axes[1].text(x,value+4,f'{value:.1f}',ha='center',fontsize=10)
axes[1].set(xticks=[0,1],xticklabels=['Common incoming states','Independent paths'],ylabel='Median material entry + driver cost [ns/return]',title='Serial CPU /O2, seven batches');axes[1].set_ylim(0,355);axes[1].legend(loc='upper left',fontsize=8);axes[1].grid(axis='x',visible=False)
f.suptitle('Material return accuracy and local cost — not a whole-SPH benchmark',fontsize=13)
f.savefig(fig,dpi=180);plt.close(f);print(fig)
