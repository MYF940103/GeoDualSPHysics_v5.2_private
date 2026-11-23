"""Compare two fresh eight-step M0 branches with common deformed soil material IDs."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from c08_m0_coupled_deformed_r1 import released

T = Path(__file__).resolve().parents[1]


def material(path, history):
    m, arrays, children = released(path, history)
    ix = np.argsort(arrays['Idp'])[1805:]
    assert np.array_equal(arrays['Idp'][ix], np.arange(2060, 7060))
    return m, {k: v[ix].astype(float) for k,v in arrays.items()}, children


def rms(a):
    return np.sqrt(np.mean(a*a))


def main():
    out = T/'outputs'
    m0, src, _ = material(out/'c08_h18_as03n255_full3_r1/data/Part_0038.bi4', False)
    paths = [sorted((out/('c08_m0_coupled_deformed_r1_'+tag)/'data').glob('Part_*.bi4')) for tag in ('b0','b004')]
    assert [len(x) for x in paths] == [8,8]
    old = [src,src]
    t = m0['TimeStep']
    rows=[]
    for k, pair in enumerate(zip(*paths),1):
        t+=5e-6
        cur=[]
        info = {'local_step':k,'actual_time_s':t,'elapsed_us':(t-m0['TimeStep'])*1e6}
        for b, path in enumerate(pair):
            m,a,ch=material(path,True)
            h,=ch
            assert m['TimeStep']==t and m['Step']==m0['Step']+k
            assert np.array_equal(h['arrays']['Idp'],a['Idp']) and h['values']['PreviousTime']==t-5e-6
            assert np.array_equal(h['arrays']['PorePressPrev'],old[b]['PorePress'])
            pre=('off_','on_')[b]
            p = a['PorePress']; active=old[b]['PorePress']<0
            info.update({pre+'active_old_p_count':active.sum(),pre+'min_Pa':p.min(),pre+'max_Pa':p.max(),pre+'negative_n':(p<0).sum(),
                         pre+'p_rms_from_finiteKw_Pa':rms(p-src['PorePress']),pre+'vmax_m_s':np.linalg.norm(a['Vel'],axis=1).max(),
                         pre+'p_nn0p01_quantile_Pa':np.quantile(p,.01),pre+'plastic_owners':(a['Kplastic']>0).sum()})
            cur.append(a)
        d=cur[1]['PorePress']-cur[0]['PorePress']
        info.update(p_diff_rms_Pa=rms(d),p_diff_max_abs_Pa=np.max(abs(d)), extremal_id=int(cur[0]['Idp'][np.argmax(abs(d))]),
                    p_diff_on_initial_negative_rms_Pa=rms(d[src['PorePress']<0]),p_diff_on_initial_nonnegative_rms_Pa=rms(d[src['PorePress']>=0]),
                    displacement_diff_max_mm=1000*np.linalg.norm(cur[1]['Posd']-cur[0]['Posd'],axis=1).max(),
                    velocity_diff_max_m_s=np.linalg.norm(cur[1]['Vel']-cur[0]['Vel'],axis=1).max())
        rows.append(info);old=cur
    figdir=T/'figures';stem='c08_m0_beta_compare_deformed8'
    with (figdir/(stem+'.csv')).open('x',encoding='utf8',newline='') as outcsv:
        w=csv.DictWriter(outcsv,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    x=[0]+[r['elapsed_us'] for r in rows]
    fig,axs=plt.subplots(2,2,figsize=(10,6),layout='constrained')
    for ax,field,scale,initial,label in [(axs[0,0],'min_Pa',.001,src['PorePress'].min(),'Minimum pore pressure (kPa)'),(axs[0,1],'max_Pa',.001,src['PorePress'].max(),'Maximum pore pressure (kPa)'),(axs[1,0],'negative_n',1,(src['PorePress']<0).sum(),'Negative-pressure soil particles')]:
        for tag,style,legend in [('off_','o-','β = 0'),('on_','s--','β = 0.04')]:ax.plot(x,np.array([initial]+[r[tag+field] for r in rows])*scale,style,ms=3,label=legend)
        ax.set_ylabel(label);ax.legend(fontsize=8)
    ax=axs[1,1]
    for field,legend in [('p_diff_rms_Pa','All soil'),('p_diff_on_initial_negative_rms_Pa','Initially negative'),('p_diff_on_initial_nonnegative_rms_Pa','Initially nonnegative')]:
        ax.plot(x,np.array([0]+[r[field] for r in rows])*.001,'.-',label=legend)
    ax.set_ylabel('Between-run pressure RMS (kPa)');ax.legend(fontsize=8)
    for ax in axs.flat:ax.grid(alpha=.2);ax.set_xlabel('Time after switch from finite Kw (µs)')
    fig.savefig(figdir/(stem+'.png'),dpi=180);plt.close(fig)


if __name__=='__main__':main()
