"""Plot the sealed eight-block pressure-operator comparison; no physical solver."""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1]
TAG='upl_c08_pressure_pairing_plot_r1'
F=T/'figures'
source=F/'upl_c08_pressure_pairing_ab_r1_summary.csv'
receipt=T/'logs/upl_c08_pressure_pairing_ab_r1.check.json'

def main():
    outputs=[F/(TAG+s) for s in ('.png','.check.json')]
    if any(p.exists() for p in outputs):raise RuntimeError('Existing plot/evidence preserved')
    check=json.loads(receipt.read_text(encoding='utf-8-sig'))
    if not check['passed'] or check['evaluated_saved_state_blocks']!=8:raise RuntimeError('Completed eight-block review required')
    rows=list(csv.DictReader(source.open(encoding='utf-8-sig',newline='')))
    variants=['A0_current_same_AS','A1_Cweighted_same_AS','A_pair_no_AS','A_pair_same_AS']
    labels=['Current + same AS','C-weighted force only + same AS','Matched D/G, no AS (control)','Matched D/G + same AS (control)']
    blocks=[(p,q) for p in (60,61,62,63) for q in ('5809','4956_4959')]
    fig,axes=plt.subplots(2,1,figsize=(13,8),sharex=True,layout='constrained')
    for ax,view,title in zip(axes,['all_patch_variables','FS0_principal'],['All local pressure variables; outside perturbations held zero','Interior FS0 principal block; outside perturbations held zero']):
        for j,(variant,label) in enumerate(zip(variants,labels)):
            values=[]
            for part,patch in blocks:
                hits=[r for r in rows if int(r['part'])==part and r['patch']==patch and r['variant']==variant and r['variable_view']==view]
                if len(hits)!=1:raise RuntimeError('Unique sealed matrix result required')
                values.append(float(hits[0]['max_real_eigenvalue_per_s']))
            ax.plot(np.arange(8),np.array(values)/1000,marker='o',markersize=5,label=label)
        ax.axhline(0,color='black',lw=1)
        ax.set_title(title,fontsize=11)
        ax.set_ylabel('Largest real eigenvalue [1000 / s]')
        ax.grid(alpha=.25)
    axes[0].legend(loc='upper left',fontsize=9)
    axes[-1].set_xticks(range(8),[f'tau={.01*(part+1):.2f} s\nIDs {patch.replace("_", "/")}' for part,patch in blocks])
    fig.suptitle('Frozen local pressure-only comparison: conditional growth, not full coupled stability',fontsize=14)
    fig.savefig(outputs[0],dpi=180)
    plt.close(fig)
    def stat(p):
        s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
    outputs[1].write_text(json.dumps(dict(stage=TAG,passed=True,physical_acceptance=False,inputs=[stat(source),stat(receipt)],plot=stat(outputs[0]),matrix_results_recomputed=False,solver_invocations=0,decoder_invocations=0,visual_QA_pending=True),indent=2)+'\n',encoding='utf-8')
    print('PAIRING_PLOT_READY',outputs[0],flush=True)

if __name__=='__main__':main()
