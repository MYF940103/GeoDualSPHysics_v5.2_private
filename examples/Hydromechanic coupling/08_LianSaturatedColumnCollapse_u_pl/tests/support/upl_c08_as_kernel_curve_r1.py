"""Pure kernel-ratio illustration; no solver, native data or existing owner invocation."""
import argparse,csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];TAG='upl_c08_as_kernel_curve_r1';PREFIX=T/'figures'/TAG
CURVES=(
    ('c08_baseline','Cubic',1.2,.2,2.55,'C08 Cubic a=1.2, eps=.2, n=2.55','C0','-'),
    ('c08_n3','Cubic',1.2,.2,3.,'C08 Cubic a=1.2, eps=.2, n=3','C1','--'),
    ('c08_n4_math_only','Cubic',1.2,.2,4.,'C08 Cubic a=1.2, eps=.2, n=4 (math only)','C2',':'),
    ('retro_preload_8m','Wendland',1.5,.2,4.,'Retro Wendland a=1.5, eps=.2, n=4','C3','-.'),
    ('retro_failure','Wendland',2.16,.3,5.,'Retro Wendland a=2.16, eps=.3, n=5','C4','-'),
    ('c08_as05_rejected','Cubic',1.2,.5,2.55,'C08 Cubic a=1.2, eps=.5, n=2.55 (rejected)','C5','--'))
ANCHORS=(.5,1.,1.5)

def shape(kernel,q):
    q=np.asarray(q,dtype=float)
    if kernel=='Cubic':return np.where((q>=0)&(q<=1),1.-1.5*q*q+.75*q*q*q,np.where((q>1)&(q<2),.25*(2.-q)**3,0.))
    if kernel=='Wendland':return np.where((q>=0)&(q<2),(1.-q/2.)**4*(2.*q+1.),0.)
    raise ValueError('Unknown fixed kernel')

def values(spec,s):
    identity,kernel,a,epsilon,n,*_=spec;s=np.asarray(s,dtype=float);q=s/a;den=float(shape(kernel,1./a));num=shape(kernel,q);ratio=num/den;F=epsilon*ratio**n
    if not(den>0 and np.isfinite(F).all() and (F>=0).all()):raise ValueError('Invalid mathematical kernel ratio')
    return q,num,den,ratio,F

def row(spec,s,is_anchor):
    identity,kernel,a,epsilon,n,*_=spec;q,num,den,ratio,F=values(spec,s)
    return dict(curve=identity,kernel=kernel,h_over_dp=a,epsilon=epsilon,exponent=n,s_r_over_dp=float(s),q_r_over_h=float(q),dimensionless_w_q=float(num),dimensionless_w_at_dp=den,kernel_ratio=float(ratio),distance_multiplier_F=float(F),support_end_s=2*a,strictly_inside_support=bool(s<2*a),requested_anchor=is_anchor)

def write(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for r in rows:w.writerow({k:format(v,'.17g') if isinstance(v,float) else v for k,v in r.items()})

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args()
    if not args.execution_authorized:raise RuntimeError('Root full-read before pure-math generation required')
    if list(PREFIX.parent.glob(TAG+'*')):raise RuntimeError('Existing complete/partial illustration preserved')
    # Integer division supplies the exact .5/1/1.5 anchors at indices100/200/300.
    grid=np.arange(901,dtype=float)/200.;rows=[];anchors=[]
    for spec in CURVES:
        if float(values(spec,1.)[-1])!=spec[3]:raise RuntimeError('F(dp) must equal epsilon exactly in this mathematical normalization')
        rows.extend(row(spec,s,bool(s in ANCHORS)) for s in grid)
        anchors.extend(row(spec,s,True) for s in ANCHORS)
    write(Path(str(PREFIX)+'_curves.csv'),rows);write(Path(str(PREFIX)+'_anchors.csv'),anchors)
    plt.rcParams.update({'font.size':9,'figure.dpi':170});fig,axes=plt.subplots(1,2,figsize=(14,6),layout='constrained')
    for spec in CURVES:
        *_,label,color,style=spec;y=values(spec,grid)[-1]
        axes[0].plot(grid,y,style,color=color,lw=1.5,label=label)
        axes[1].plot(grid,np.where(y>0,y,np.nan),style,color=color,lw=1.5,label=label)
        for s in ANCHORS:
            v=float(values(spec,s)[-1]);axes[0].plot(s,v,'o',color=color,ms=3);axes[1].plot(s,v,'o',color=color,ms=3)
    for ax in axes:
        ax.axvline(1.,color='.5',lw=.7);ax.grid(alpha=.25,which='both');ax.set(xlabel='s = r / dp',ylabel='F(s) = epsilon [w(s/a) / w(1/a)]^n')
    axes[0].set(xlim=(0,1.5),ylim=(0,None),title='Near field: distance multiplier, not pair force');axes[0].legend(fontsize=7)
    axes[1].set(xlim=(1,4.5),yscale='log',title='Tail: zero outside 2h; zeros omitted on log axis')
    for support in (2.4,3.,4.32):axes[1].axvline(support,color='.6',lw=.7,ls=':');axes[1].text(support,.98,str(support)+' dp',rotation=90,va='top',ha='right',fontsize=7,transform=axes[1].get_xaxis_transform())
    fig.suptitle('Artificial-stress locality: ideal real-valued kernel shapes, six fixed controls')
    fig.supxlabel('r=0: the multiplier is finite, but the radial kernel gradient tends to zero; no actual-force maximum is implied.',fontsize=8)
    png=Path(str(PREFIX)+'.png');fig.savefig(png);plt.close(fig)
    print('PURE_MATH_ILLUSTRATION_READY',png,'curve_rows',len(rows),'exact_anchor_rows',len(anchors),flush=True)

if __name__=='__main__':main()
