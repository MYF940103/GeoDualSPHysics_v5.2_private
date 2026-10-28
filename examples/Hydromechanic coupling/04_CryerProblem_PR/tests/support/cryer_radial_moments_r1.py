"""Local Taylor moments of the current Darcy stencil; no replacement or solver."""
import argparse
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_radial_consistency_r1 import Reference,TAUS
from cryer_load_pair_r1 import TESTS,R,Q,DP,native,bound,write_json,batches,correction,add_pair

TAG='cryer_radial_moments_r1'


def main():
    target=TESTS/'logs'/(TAG+'.check.json'); csv=TESTS/'figures'/(TAG+'_regions.csv')
    bins=TESTS/'figures'/(TAG+'_radial.csv'); image=TESTS/'figures'/(TAG+'.png')
    assert not any(p.exists() for p in [target,csv,bins,image])
    source=TESTS/'logs/cryer_radial_consistency_r1.check.json'
    actual=TESTS/'logs/cryer_radial_force_r2.check.json'
    prior=json.loads(source.read_text()); real=json.loads(actual.read_text())
    assert prior['analysis_checks_passed'] and real['analysis_checks_passed'] and real['integrated_steps']==0
    for entry in prior['inputs']+prior['artifacts']+real['inputs']+real['artifacts']:
        assert bound(entry['path'])['sha256']==entry['sha256'],entry['path']
    a=native(TESTS/'outputs/cryer_preload_peak_r1',0);x=a[['x','y','z']].to_numpy();r=np.linalg.norm(x,axis=1)
    volume=(a.mass/a.rho).to_numpy();volop=(a.mass.to_numpy(np.float32)/a.rho.to_numpy(np.float32)).astype(float)
    ctes=prior['constants'];h=float(a.h.iloc[0]);scale=float(volop[0]/volume[0])
    assert np.all(volop/volume==scale)
    pairs=cKDTree(x).query_pairs(2*h,output_type='ndarray')
    corr,_=correction(x,a.mass.to_numpy(),a.rho.to_numpy(),h,pairs)
    corr/=ctes['helper_gradient_scale']*scale
    ell=np.zeros_like(x);moment=np.zeros((len(x),3,3));poly=np.zeros(len(x))
    gpoly=np.array([1.,-2.,.5]);hpoly=np.array([[2.,.3,-.4],[.3,-.7,.2],[-.4,.2,1.4]])
    ppoly=x@gpoly+.5*np.einsum('ni,ij,nj->n',x,hpoly,x)
    for i,j,d,g in batches(x,pairs,h):
        g*=ctes['helper_gradient_scale'];denom=np.sum(d*d,axis=1)+ctes['eta2_float_m2']
        hi=np.einsum('ni,nij,nj->n',d,corr[i],g)/denom
        hj=np.einsum('ni,nij,nj->n',d,corr[j],g)/denom
        add_pair(ell,i,j,2*volop[j,None]*hi[:,None]*d,-2*volop[i,None]*hj[:,None]*d)
        dd=d[:,:,None]*d[:,None,:]
        for u in range(3):
            for v in range(3):
                moment[:,u,v]+=np.bincount(i,weights=-volop[j]*hi*dd[:,u,v],minlength=len(x))
                moment[:,u,v]+=np.bincount(j,weights=-volop[i]*hj*dd[:,u,v],minlength=len(x))
        delta=ppoly[i]-ppoly[j]
        poly+=np.bincount(i,weights=2*volop[j]*hi*delta,minlength=len(x))
        poly+=np.bincount(j,weights=-2*volop[i]*hj*delta,minlength=len(x))
    predicted=np.sum(ell*(gpoly+x@hpoly.T),axis=1)+np.einsum('nij,ij->n',moment,hpoly)
    polynomial_error=float(abs(poly-predicted).max());assert polynomial_error<1e-8
    ref=Reference();tau=TAUS[2];f=ref.field(r,tau);w=ref.amplitude*np.exp(-ref.decay*tau)
    z=r[:,None]/R*ref.xi;phi=(np.sin(z)-z*np.cos(z))/z**3
    ptangent=-Q/R**2*(phi@(ref.xi**2*w));pradial=f['lap']-2*ptangent
    er=x/r[:,None];gradient=ptangent[:,None]*x
    hessian=ptangent[:,None,None]*np.eye(3)+(pradial-ptangent)[:,None,None]*er[:,:,None]*er[:,None,:]
    assert np.max(abs(np.trace(hessian,axis1=1,axis2=2)-f['lap']))<1e-7
    gpu=ctes['backends']['GPU'];factor=.5*gpu['diffusion_factor_m2_s']
    linear=factor*np.sum(ell*gradient,axis=1)
    quadratic=factor*(np.einsum('nij,nij->n',moment,hessian)-f['lap'])
    saved=np.load(TESTS/'figures/cryer_radial_consistency_r1.npz')
    assert np.array_equal(a.id,saved['id'])
    error=saved['t2_darcy_error'];higher=error-linear-quadratic
    surface=a.fstype.isin([2,3]).to_numpy();groups=dict(center18=r<=DP+1e-12,
        full_support_core=r<R-2*h,near_surface_interior=(r>=R-2*h)&~surface,nondrained=~surface)
    arrays=dict(linear_moment_error_pa_s=linear,quadratic_moment_error_pa_s=quadratic,
        higher_remainder_pa_s=higher,total_darcy_error_pa_s=error,
        linear_moment_norm_m_inv=np.linalg.norm(ell,axis=1),
        quadratic_moment_minus_I_norm=np.linalg.norm(moment-np.eye(3),axis=(1,2)))
    rows=[];radial=[];edges=np.linspace(0,R,21)
    for name,mask in groups.items():
        row=dict(region=name,count=int(mask.sum()),tau_s=tau)
        for key,value in arrays.items():
            row[key+'_mean']=float(np.average(value[mask],weights=volume[mask]))
            row[key+'_rms']=float(np.sqrt(np.average(value[mask]**2,weights=volume[mask])))
        rows.append(row)
    for j in range(20):
        mask=(r>=edges[j])&(r<edges[j+1])&~surface
        row=dict(r_min_m=edges[j],r_max_m=edges[j+1],count=int(mask.sum()),tau_s=tau)
        for key,value in arrays.items():
            row[key+'_rms']=float(np.sqrt(np.average(value[mask]**2,weights=volume[mask]))) if mask.any() else np.nan
        radial.append(row)
    pd.DataFrame(rows).to_csv(csv,index=False,float_format='%.17g');pd.DataFrame(radial).to_csv(bins,index=False,float_format='%.17g')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained');mid=(edges[:-1]+edges[1:])/2/R
    for key,label in [('total_darcy_error_pa_s','Total Darcy error'),('linear_moment_error_pa_s','First-moment contribution'),
            ('quadratic_moment_error_pa_s','Second-moment contribution'),('higher_remainder_pa_s','Higher-order remainder')]:
        ax.semilogy(mid,[row[key+'_rms'] for row in radial],'.-',label=label)
    ax.set(xlabel='Initial radius r/R (non-Dirichlet receivers)',ylabel='Contribution RMS (Pa/s)',
        title='Current Darcy stencil at the finite-storage theoretical peak\nFrozen native geometry; Taylor identity, not a corrected operator')
    ax.legend();ax.grid(True,alpha=.25);fig.savefig(image,dpi=170);plt.close(fig)
    write_json(target,dict(analysis_checks_passed=True,production_implemented=False,solver_executed=False,
        physical_acceptance=False,tau_s=tau,polynomial_identity_absmax_pa_m2=polynomial_error,
        definitions=dict(stencil='Lh p=2 sum Vj Hij (pi-pj)',Hij='dij dot Ci gradWij / (rij²+Eta2)',
            ell='2 sum Vj Hij dij',moment='-sum Vj Hij dij tensor dij',
            decomposition='Lh p-lap p = ell dot grad p + (moment:Hessian p-lap p) + remainder'),
        inputs=[bound(__file__),bound(source),bound(actual)],artifacts=[bound(csv),bound(bins),bound(image)],rows=rows,
        limitations=['Double offline moments with current production scalar constants, not another actual CPU kernel run.',
            'Signed contributions add pointwise; their separate RMS values do not add algebraically.',
            'No surface receiver rate is included; actual production forces their pressure/rate to zero.',
            'The nonzero first moment explains local linear inconsistency, not a complete coupled peak-error attribution.',
            'No replacement stencil, gradient subtraction, volume renormalization or new physical run.']))
    print(json.dumps(dict(analysis_checks_passed=True,center=rows[0],near_surface=rows[2])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true')
    if p.parse_args().run:main()
    else:p.print_help()
