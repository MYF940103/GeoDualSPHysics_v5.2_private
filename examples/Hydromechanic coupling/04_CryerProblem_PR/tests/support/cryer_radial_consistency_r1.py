"""Finite-storage radial Cryer fields on sealed native geometry; no solver or edits.

Only the current receiver-C pressure operators and raw momentum are evaluated.
Double offline sums with production scalar constants are NOT backend replay.
"""
import argparse
import hashlib
import json
import time
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import (TESTS, REPO, LIAN, R, Q, DP, READER, native,
    bound, write_json, batches, correction, add_pair)
from cryer_darcy_closed_r1 import constants

TAG = 'cryer_radial_consistency_r1'
PEAK = 'cryer_preload_peak_r1'
TAUS = [.005, .02, .0420518020252, .04638671875, .0625]


class Reference:
    """Quasistatic alpha=1 solution with finite Mf=Kw/n, not dynamic truth."""
    def __init__(self, modes=360):
        self.K = 2e6/(3*(1-2*.3)); self.G = 2e6/(2*(1+.3))
        self.H = self.K+4*self.G/3; self.Mf = 2e8/.3
        self.beta = 4*self.G/(3*self.K); self.A = 1+self.H/self.Mf
        self.B = self.Mf/(self.K+self.Mf); self.eta = self.H/(2*self.G*self.B)
        self.kappa = 1e-5/(1000*9.80665); self.cv = self.H*self.kappa/self.A
        f = lambda z: (1-self.eta*z*z/2)*np.sin(z)-z*np.cos(z)
        self.xi = np.array([brentq(f,j*np.pi+1e-6,(j+1)*np.pi-1e-6,
            xtol=5e-15,rtol=1e-15) for j in range(modes)])
        z = self.xi; self.sx = np.sinc(z/np.pi)
        c = self.B*self.eta*(np.sin(z)-z)/(self.eta*z*np.cos(z)/2+(self.eta-1)*np.sin(z))
        self.amplitude = c/(1-self.sx)
        self.mean = 3*(np.sin(z)-z*np.cos(z))/z**3-self.sx
        self.decay = z*z*self.cv/R**2

    def field(self, radius, tau):
        assert tau > 0, 'No differentiation of the incompatible opening corner'
        r = np.asarray(radius); w = self.amplitude*np.exp(-self.decay*tau)
        wt = -self.decay*w; wtt = self.decay**2*w
        mean_p = Q*np.dot(self.mean,w); mean_pt = Q*np.dot(self.mean,wt)
        out = {n: np.empty_like(r,dtype=float) for n in
            ['p','pt','lap','div','u_over_r','v_over_r','vt_over_r','sr','st','tr','tt']}
        for start in range(0,len(r),2048):
            sl = slice(start,start+2048); s = r[sl]/R; z = s[:,None]*self.xi
            sinc = np.sinc(z/np.pi); phi = np.empty_like(z); small = abs(z)<.02
            zz = z[small]**2
            phi[small] = 1/3-zz/30+zz**2/840-zz**3/45360+zz**4/3991680
            phi[~small] = (np.sin(z[~small])-z[~small]*np.cos(z[~small]))/z[~small]**3
            shape = sinc-self.sx
            p = Q*(shape@w); pt = Q*(shape@wt)
            radial_shape = phi+(self.beta*self.mean-self.sx)/3
            uor = -Q/(3*self.K)+Q/self.H*(radial_shape@w)
            epsv = (p-self.H*Q/self.K+self.beta*mean_p)/self.H
            st = 2*self.G*uor+(self.K-2*self.G/3)*epsv
            sr = 2*self.G*(epsv-2*uor)+(self.K-2*self.G/3)*epsv
            values = dict(p=p,pt=pt,lap=-Q/R**2*(sinc@(self.xi**2*w)),
                div=(pt+self.beta*mean_pt)/self.H,u_over_r=uor,
                v_over_r=Q/self.H*(radial_shape@wt),vt_over_r=Q/self.H*(radial_shape@wtt),
                sr=sr,st=st,tr=sr-p,tt=st-p)
            for name,value in values.items(): out[name][sl] = value
        out.update(mean_p=float(mean_p),mean_pt=float(mean_pt))
        return out


def selftest(ref):
    z=ref.xi; left=(1-ref.eta*z*z/2)*np.sin(z); right=z*np.cos(z)
    root_error=float(np.max(abs(left-right)/(1+abs(left)+abs(right))))
    assert root_error<1e-9
    assert np.allclose(ref.mean,ref.sx/(ref.beta/ref.A),rtol=1e-8,atol=1e-12)
    r=np.linspace(0,R,101); pde=0.; traction=0.; vdiff=0.; static=0.
    # Independent radial finite differences and modal/integral velocity identity.
    for tau in TAUS:
        a=ref.field(r,tau)
        pde=max(pde,float(abs(ref.Mf*(-a['div']+ref.kappa*a['lap'])-a['pt']).max()))
        traction=max(traction,abs(float(a['tr'][-1])+Q))
        assert abs(a['p'][-1])<1e-8 and abs(a['pt'][-1])<1e-7
        rc=np.linspace(.002,.048,25); dr=1e-7
        c=ref.field(rc,tau); lo=ref.field(rc-dr,tau); hi=ref.field(rc+dr,tau)
        divfd=((rc+dr)**3*hi['v_over_r']-(rc-dr)**3*lo['v_over_r'])/(2*dr*rc**2)
        vdiff=max(vdiff,float(abs(divfd-c['div']).max()))
        static=max(static,float(abs((hi['tr']-lo['tr'])/(2*dr)+2*(c['tr']-c['tt'])/rc).max()))
        w=ref.amplitude*np.exp(-ref.decay*tau); wt=-ref.decay*w
        s=rc/R; zz=s[:,None]*z
        j=(np.sin(zz)-zz*np.cos(zz))/z**3-ref.sx*s[:,None]**3/3
        integral_v=Q*R/ref.H*((j/s[:,None]**2+ref.beta*ref.mean*s[:,None]/3)@wt)
        assert np.max(abs(integral_v-rc*c['v_over_r']))<1e-13
    assert pde<1e-5 and traction<1e-7 and vdiff<1e-7 and static<.02
    return dict(passed=True,normalized_root_residual_max=root_error,
        pressure_PDE_residual_absmax_pa_s=pde,surface_traction_residual_absmax_pa=traction,
        radial_velocity_divergence_fd_error_absmax_s_inv=vdiff,
        quasistatic_radial_force_fd_error_absmax_pa_m=static,
        note='Arithmetic/continuum self-tests, not physical accuracy acceptance.')


def verify_peak():
    paths=[TESTS/'logs'/(PEAK+suffix) for suffix in
        ['.status.json','.run.json','.check.json','.completion.json','.prefix.json','.inputs.json']]
    status,run,check,completion,prefix,inputs=[json.loads(p.read_text()) for p in paths]
    assert status['status']=='preload_peak_safety_completed_pending_causal_review'
    assert run['owned_exited'] and run['exit_code']==0 and run['actual_last_saved_time_s']==.0703125
    assert completion['solver_finished'] and completion['owned_exited'] and completion['exit_code']==0
    assert inputs['program']==run['program']==completion['program']
    assert check['passed'] and check['checked_frames']==577 and check['prefix_samples']==69
    assert prefix['checked_samples']==69 and prefix['all35_columns0ulp_passed'] and not prefix['excluded_columns']
    assert len(prefix['samples'])==69
    for row in prefix['samples']:
        assert row['all_35_columns0ulp'] and len(row['compared_columns'])==35 and not row['differences']
    records=inputs['inputs']+completion['outputs']+[run['program'],run['prepared_inputs'],
        check['run_manifest'],check['sealed_completion'],check['prefix_receipt']]+run['artifacts']
    refpath=TESTS/'logs/cryer_finite_storage_r1.check.json'; ref=json.loads(refpath.read_text())
    assert ref['analysis_checks_passed'] and ref['reference_derivation_verified']
    records+=ref['inputs']
    unique={}
    for record in records:
        path=record['path']; expected=record['sha256']
        assert path not in unique or unique[path]['sha256']==expected, path
        unique[path]=record
    mismatches=[]
    for path,record in unique.items():
        if bound(path)['sha256']!=record['sha256']: mismatches.append(path)
    assert not mismatches, 'Frozen prerequisite hash mismatch: '+repr(mismatches)
    print('Verified %d sealed prerequisite/output hashes; no solver launched.'%len(unique),flush=True)
    hist=pd.read_csv(TESTS/'figures'/(PEAK+'_summary.csv'),float_precision='round_trip')
    assert len(hist)==577 and np.array_equal(hist.part,np.arange(577))
    assert np.array_equal(hist.time_s,np.arange(577)/8192)
    assert np.array_equal(hist.saved_step,np.r_[0,np.arange(1,577)*256-1])
    assert hist.true_surface_count.eq(5153).all() and hist.center_fixed_material_count.eq(18).all()
    assert hist.loc[hist.time_s>.0078125,'true_surface_pressure_absmax_pa'].eq(0).all()
    assert not bool(hist.loc[hist.part.eq(64),'drainage_active'].iloc[0])
    return run,dict(adopted_native_safety_frames=577,independently_rehashed_files=len(unique),
        native_frames_reread_this_audit=1,independently_checked_summary_rows=577,
        all35_columns_exact_prefix_samples=69,prefix_exclusions=[],
        sealed_outputs_bytes=sum(e.get('bytes',0) for e in completion['outputs']),
        input_manifest=bound(paths[-1]),completion=bound(paths[3]),prefix=bound(paths[4])),paths+[refpath]


def stats(values,mask,volume):
    a=np.asarray(values)[mask]; weights=volume[mask]
    return dict(count=int(mask.sum()),mean=float(np.average(a,weights=weights)),
        rms=float(np.sqrt(np.average(a*a,weights=weights))),absmax=float(abs(a).max()))


def evaluate(x,pairs,h,corr,volume,ctes,field,quantized=False):
    n=len(x); p=field['p']; velocity=x*field['v_over_r'][:,None]
    if quantized:
        p=p.astype(np.float32).astype(float); velocity=velocity.astype(np.float32).astype(float)
    div=np.zeros(n); lap=np.zeros(n); acc=np.zeros_like(x)
    er=x/np.linalg.norm(x,axis=1)[:,None]
    # T+qI: exact quasistatic stress plus current raw confinement contribution.
    tensor=(field['tt']+Q)[:,None,None]*np.eye(3)
    tensor+=(field['tr']-field['tt'])[:,None,None]*er[:,:,None]*er[:,None,:]
    for i,j,d,g in batches(x,pairs,h):
        g=g*ctes['helper_gradient_scale']; dv=velocity[j]-velocity[i]
        gi=np.einsum('nij,nj->ni',corr[i],g); gj=np.einsum('nij,nj->ni',corr[j],g)
        denom=np.sum(d*d,axis=1)+ctes['eta2_float_m2']; delta=p[i]-p[j]
        div+=np.bincount(i,weights=volume[j]*np.sum(dv*gi,axis=1),minlength=n)
        div+=np.bincount(j,weights=volume[i]*np.sum(dv*gj,axis=1),minlength=n)
        lap+=np.bincount(i,weights=2*volume[j]*delta*np.sum(d*gi,axis=1)/denom,minlength=n)
        lap+=np.bincount(j,weights=-2*volume[i]*delta*np.sum(d*gj,axis=1)/denom,minlength=n)
        if not quantized:
            tg=np.einsum('nij,nj->ni',tensor[i]+tensor[j],g)/2100.
            add_pair(acc,i,j,volume[j,None]*tg,-volume[i,None]*tg)
    return div,lap,acc


def main():
    target=TESTS/'logs'/(TAG+'.check.json'); data=TESTS/'figures'/(TAG+'.npz')
    plot=TESTS/'figures'/(TAG+'.png')
    table=TESTS/'figures'/(TAG+'_regions.csv'); bands=TESTS/'figures'/(TAG+'_radial.csv')
    assert not any(p.exists() for p in [target,data,plot,table,bands]), 'Never overwrite retained evidence'
    start=time.perf_counter(); result=dict(analysis_checks_passed=False,solver_executed=False,
        production_implemented=False,physical_acceptance=False,automatic_formal_run_admitted=False)
    try:
        run,receipt,prereqs=verify_peak(); result['peak_verification']=receipt
        result['inputs']=[bound(p) for p in prereqs+[Path(__file__),READER,LIAN/'lian_release_r1.py',
            Path(__file__).with_name('cryer_darcy_closed_r1.py'),
            Path(__file__).with_name('cryer_load_pair_r1.py'),
            REPO/'src/source/JSphCpu.cpp',REPO/'src/source/JSph.cpp',
            REPO/'src/source/FunSphKernel.h',REPO/'src/source/JSphGpu_ker.cu']]
        ref=Reference(); result['selftest']=selftest(ref)
        a=native(TESTS/'outputs'/PEAK,0)
        assert len(a)==37173 and a.id.nunique()==len(a) and a.position_double.eq(1).all()
        assert a.rho.eq(2100).all() and a.mass.eq(a.mass.iloc[0]).all() and a.nout.eq(0).all()
        x=a[['x','y','z']].to_numpy(); r=np.linalg.norm(x,axis=1); surface=a.fstype.isin([2,3]).to_numpy()
        center=a.id.isin(run['center_fixed_material_ids']).to_numpy()
        assert int(center.sum())==18 and np.array_equal(center,r<=DP+1e-12)
        assert surface.sum()==5153 and np.max(abs(r[surface]-R))<1e-14 and r.min()>0
        volume=(a.mass/a.rho).to_numpy(); volop=(a.mass.to_numpy(np.float32)/a.rho.to_numpy(np.float32)).astype(float)
        scale=float(volop[0]/volume[0]); assert np.all(volop/volume==scale)
        h=float(a.h.iloc[0]); ctes=constants(TESTS/'configs'/(PEAK+'_Def.xml'),h)
        xml=ET.parse(TESTS/'configs'/(PEAK+'_Def.xml')).getroot()
        hydro=xml.find('.//hydromechanics')
        get=lambda name,default: hydro.find(name).get('value') if hydro.find(name) is not None else default
        assert get('PoreCompressionSourceMode','PairDivergence') in ['PairDivergence','0']
        assert get('PoreCompressionGradCorr','true').lower() in ['true','1']
        assert float(xml.find('.//soils/ModulusE').get('value'))==2e6
        assert float(xml.find('.//soils/PRvs').get('value'))==.3
        text=(TESTS/'outputs'/PEAK/'Run.out').read_text(errors='replace')
        assert 'PoreCompressionSourceMode="PairDivergence"' in text
        assert 'PoreCompressionGradCorr="KernelGradient"' in text
        result['operator_path']=dict(compression='PairDivergence with receiver C',
            darcy='Receiver C regardless of compression/stress-gradient options',
            momentum='Raw gradient; same raw confinement contribution',
            xml_defaults_verified_by_run_out=True)
        pairs=cKDTree(x).query_pairs(2*h,output_type='ndarray')
        corr,affine=correction(x,a.mass.to_numpy(),a.rho.to_numpy(),h,pairs)
        corr=corr/(ctes['helper_gradient_scale']*scale)
        result.update(constants=ctes,correction=affine,pair_count=len(pairs),
            native_geometry=dict(soil_count=len(a),surface_count=int(surface.sum()),
                radius_min_m=float(r.min()),radius_max_m=float(r.max()),
                native_over_sphere_volume=float(volume.sum()/(4*np.pi*R**3/3)),
                mean_r2_over_R2=float(np.average(r*r,weights=volume)/R**2),
                ids_sha256=hashlib.sha256(a.id.to_numpy(dtype='<u4').tobytes()).hexdigest()))
        groups=dict(center18=center,full_support_core=r<R-2*h,
            near_surface_interior=(r>=R-2*h)&~surface,dirichlet_surface=surface,nondrained=~surface)
        result['rows']=[]; arrays=dict(id=a.id.to_numpy(),radius_m=r,surface=surface,tau_s=np.array(TAUS))
        radial=[]; edges=np.linspace(0,R,21); band_rows=[]
        for tindex,tau in enumerate(TAUS):
            print('Evaluating frozen radial field tau=%.12g s'%tau,flush=True)
            f=ref.field(r,tau)
            assert np.max(abs(f['p'][surface]))<1e-8
            f['p'][surface]=0. # Exact analytic Dirichlet data; no native data are edited.
            div,lap,acc=evaluate(x,pairs,h,corr,volop,ctes,f)
            divq,lapq,_=evaluate(x,pairs,h,corr,volop,ctes,f,quantized=True)
            for backend,scalar in ctes['backends'].items():
                mf=scalar['kwn_pa']; kap=ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*scalar['ghyd_m_s2'])
                comp=-mf*div; darcy=mf*kap*lap; net=comp+darcy
                model=mf*(-f['div']+kap*f['lap'])-f['pt']
                ce=-mf*(div-f['div']); de=mf*kap*(lap-f['lap']); error=net-f['pt']
                assert np.max(abs(error-(ce+de+model)))<1e-6
                quant=mf*(-divq+kap*lapq)-net
                for name,mask in groups.items():
                    row=dict(tau_s=tau,scalar_backend=backend,region=name,
                        raw_diagnostic_only=(name=='dirichlet_surface'))
                    for key,value in dict(exact_pt_pa_s=f['pt'],
                            reference_compression_pa_s=-ref.Mf*f['div'],
                            reference_darcy_pa_s=ref.Mf*ref.kappa*f['lap'],compression_pa_s=comp,darcy_pa_s=darcy,
                            net_pa_s=net,compression_error_pa_s=ce,darcy_error_pa_s=de,
                            scalar_model_error_pa_s=model,net_error_pa_s=error,
                            float_input_only_net_change_pa_s=quant,
                            raw_quasistatic_acc_norm_m_s2=np.linalg.norm(acc,axis=1),
                            reference_inertial_acc_norm_m_s2=abs(f['vt_over_r'])*r).items():
                        row[key]=stats(value,mask,volume)
                    result['rows'].append(row)
                if backend=='GPU':
                    arrays.update({f't{tindex}_{key}':value for key,value in dict(
                        p=f['p'],exact_pt=f['pt'],comp_error=ce,darcy_error=de,net_error=error,
                        float_input_change=quant,raw_acc_norm=np.linalg.norm(acc,axis=1)).items()})
                    band=[]
                    for j in range(len(edges)-1):
                        mask=(r>=edges[j])&(r<edges[j+1])&~surface
                        band.append([np.sqrt(np.average(v[mask]**2,weights=volume[mask])) if mask.any() else np.nan
                            for v in [ce,de,error,np.linalg.norm(acc,axis=1)]])
                        band_rows.append(dict(tau_s=tau,r_min_m=edges[j],r_max_m=edges[j+1],
                            count=int(mask.sum()),compression_error_rms_pa_s=band[-1][0],
                            darcy_error_rms_pa_s=band[-1][1],net_error_rms_pa_s=band[-1][2],
                            raw_quasistatic_force_rms_m_s2=band[-1][3]))
                    radial.append(band)
        arrays['radial_band_rms']=np.array(radial); arrays['radial_edges_m']=edges
        np.savez_compressed(data,**arrays)
        flat=[]
        for row in result['rows']:
            item={key:value for key,value in row.items() if not isinstance(value,dict)}
            for key,value in row.items():
                if isinstance(value,dict): item.update({key+'_'+k:v for k,v in value.items()})
            flat.append(item)
        pd.DataFrame(flat).to_csv(table,index=False,float_format='%.17g')
        pd.DataFrame(band_rows).to_csv(bands,index=False,float_format='%.17g')
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
        mid=(edges[:-1]+edges[1:])/2/R
        for ti,tau in enumerate(TAUS):
            for column,ax in enumerate(axes.ravel()):
                ax.semilogy(mid,np.array(radial)[ti,:,column],marker='.',label=f'{tau:.6g} s')
        for ax,title in zip(axes.ravel(),['Compression rate error RMS','Darcy rate error RMS',
                'Net pressure-rate error RMS','Raw quasistatic force residual RMS']):
            ax.set(xlabel='Initial radius r/R (non-Dirichlet receivers)',ylabel='Pa/s' if ax is not axes[1,1] else 'm/s²',title=title)
            ax.grid(True,alpha=.25); ax.legend(fontsize=8)
        fig.suptitle('Frozen finite-storage Cryer field / current operators / GPU scalar constants\n'
            'Offline double geometry and sums; no time integration or replacement operator')
        fig.savefig(plot,dpi=170); plt.close(fig)
        result['artifacts']=[bound(data),bound(plot),bound(table),bound(bands)]
        result['analysis_checks_passed']=True
    except Exception as exc:
        result.update(error=repr(exc),traceback=traceback.format_exc())
    result.update(wall_seconds=time.perf_counter()-start,limitations=[
        'Adopts the sealed 577-frame native safety check, freshly rehashes every frozen output; only Part0 is reread.',
        'Manufactured finite-storage quasistatic fields on fixed initial geometry, not actual coupled trajectories.',
        'Double pair distances/sums with float production scalar constants; not float cell-order or backend 0-ULP replay.',
        'Float-input contrast quantizes p and v only, not stress integration, all operators, or persistent-state feedback.',
        'Dirichlet nodes remain neighbours. Their raw rates are diagnostic only; production skips their rate and forces p=0.',
        'Raw momentum residual is relative to quasistatic balance; reference inertia is separately reported, not assumed zero dynamics.',
        'No mass/volume normalization, shifting, new boundary, gradient, damping, physical acceptance or formal run.'])
    write_json(target,result)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'],error=result.get('error'),
        wall_seconds=result['wall_seconds'])),flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true'); parser.add_argument('--selftest',action='store_true')
    args=parser.parse_args()
    if args.run: main()
    elif args.selftest: print(json.dumps(selftest(Reference()),indent=2))
    else: parser.print_help()
