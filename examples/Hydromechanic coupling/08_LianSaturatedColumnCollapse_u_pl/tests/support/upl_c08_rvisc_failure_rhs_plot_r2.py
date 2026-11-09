"""Re-render existing RHS CSVs with short colorbar labels; no native or numerical rerun."""
import json
from pathlib import Path
import upl_c08_as05_compare_r1 as c
from matplotlib.colors import SymLogNorm,Normalize
np,plt=c.np,c.plt
T=c.T;tag='upl_c08_rvisc_failure_rhs_plot_r2';out=T/'figures/upl_c08_rvisc_failure_rhs_review_r1_fields_r2.png';check=T/'logs'/(tag+'.json')
c.need(not out.exists() and not check.exists(),'Existing plot protected')
receipt=T/'logs/upl_c08_rvisc_failure_rhs_review_r1.check.json';r=c.read(receipt);c.need(r['passed'],'Completed offline interpretation required')
component=c.read(r['source_component']['path']);source=next(c.bind(q) for q in component['files'] if Path(q['path']).name=='soil_force.csv');rows=c.table(source['path']);data=[]
for label in ('baseline_control','baseline52','rvisc52'):
    rr=sorted((q for q in rows if q['snapshot']==label and q['mode']=='ON'),key=lambda q:int(q['native_id']))
    c.need(len(rr)==5000,'All soil points required')
    data.append((label,np.array([[float(q['x_m']),float(q['z_m'])] for q in rr]),np.array([float(q['switch_minus_baseline_rate_Pa_s']) for q in rr]),np.array([sum(float(q['switch_minus_baseline_Ace_'+a+'_m_s2'])**2 for a in ('x','y','z'))**.5 for q in rr])))
peak=max(float(abs(q[2]).max()) for q in data);amax=max(float(q[3].max()) for q in data);norm=SymLogNorm(linthresh=1e6,vmin=-peak,vmax=peak);anorm=Normalize(0,amax)
fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
for i,(label,pos,dr,da) in enumerate(data):
    im=axes[0,i].scatter(pos[:,0],pos[:,1],c=dr,s=6,cmap='coolwarm',norm=norm,rasterized=True);ia=axes[1,i].scatter(pos[:,0],pos[:,1],c=da,s=6,cmap='viridis',norm=anorm,rasterized=True)
    for ax in axes[:,i]:ax.set_aspect('equal');ax.set(xlabel='x [m]',ylabel='z [m]',title=label)
fig.colorbar(im,ax=list(axes[0]),label='Delta pressure rate [Pa/s]')
fig.colorbar(ia,ax=list(axes[1]),label='Added acceleration [m/s2]')
fig.suptitle('Same-state residual-viscosity ON - OFF; zero time updates\nPressure-rate color uses symmetric log display; not the unsaved GPU failure state',fontsize=13)
fig.savefig(out,dpi=170,bbox_inches='tight');plt.close(fig)
with check.open('x',encoding='utf-8') as f:json.dump(dict(passed=True,plot_only=True,source_analysis=c.stat(receipt),source_CSV=source,script=c.stat(__file__),PNG=c.stat(out),original_plot_preserved=True,native_reads=0,new_force_calls=0,physical_steps=0,physical_acceptance=False),f,indent=2);f.write('\n')
