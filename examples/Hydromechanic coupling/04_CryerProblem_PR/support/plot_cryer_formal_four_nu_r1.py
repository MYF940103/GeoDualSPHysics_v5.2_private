"""Four returned Cryer formal runs: read-only native reduction and log-Tv figures.

Uses actual saved times and fixed initial center18 IDs. Never starts a solver.
"""
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[_key]='1'
import argparse
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.optimize import brentq, minimize_scalar

CASE=Path(__file__).resolve().parents[1]; TESTS=CASE/'tests'; DEST=CASE/'figures/formal_validation'
TAG='cryer_formal_four_nu_r1'; TD=2.**-7; DT=2.**-20; R=.05; Q=10000.
GROUPS=[('010',.1,'CaseCryerProblem_PR_release_nu010_r1',1265435),('020',.2,'CaseCryerProblem_PR_release_nu020_r1',1165427),('030',.3,'CaseCryerProblem_PR_symc_nu030',963370),('045',.45,'CaseCryerProblem_PR_release_nu045_r1',347180)]

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def bound(p):
    p=Path(p).resolve()
    with p.open('rb') as f:d=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(path=str(p),bytes=p.stat().st_size,sha256=d)
def verify(r):
    a=bound(r['path']);assert a['bytes']==r['bytes'] and a['sha256']==r['sha256'].lower(),r['path']
def seal(p,value):
    with Path(p).open('x',encoding='utf8') as f:json.dump(value,f,indent=2,allow_nan=False)
def table_path(tag,kind):return DEST/(TAG+'_nu'+tag+'_'+kind+'.csv')

def parameters(folder,stem,nu):
    path=folder/(stem+'.xml');root=ET.parse(path).getroot()
    def value(k):
        a=root.find('.//'+k)
        if a is None:a=root.find('.//parameter[@key="'+k+'"]')
        assert a is not None,k
        return float(a.get('value'))
    assert value('PRvs')==nu and value('ModulusE')==2e6 and value('Porosity')==.3 and value('PoreWaterBulkModulus')==2e8
    assert value('HydraulicConductivity')==1e-5 and value('PoreWaterRho')==1000 and value('HydroMechTopLoadQ0')==Q
    assert value('HydroMechTopLoadRampTime')==2.**-8 and value('HydroMechDrainageStartTime')==TD and value('HydroMechDrainageFixedGrid')==1
    assert value('DtFixed')==DT and value('SavePosDouble')==1 and value('SoilStressRateGradCorr')==1 and value('PoreDarcySymmetricCorr')==1
    assert value('SoilBoundaryDerivativeSPR')==value('SoilHourglassXi')==value('Shifting')==0 and value('SoilDampingCoef')==.00004
    h=root.find('./execution/special/hydromechanics');assert h is not None
    return dict(nu=nu,E=value('ModulusE'),n=value('Porosity'),Kw=value('PoreWaterBulkModulus'),k=value('HydraulicConductivity'),rhow=value('PoreWaterRho'),dt=value('DtFixed'),end=value('TimeMax'),tout=value('TimeOut'),runtime=bound(path))

class Reference:
    """Finite-Kw alpha=1 quasistatic sphere, matching retained nu=.30 reference."""
    def __init__(self,nu,modes=360,finite=True):
        self.nu=nu;self.K=2e6/(3*(1-2*nu));self.G=2e6/(2*(1+nu));self.H=self.K+4*self.G/3
        self.Mf=2e8/.3;self.B=self.Mf/(self.K+self.Mf) if finite else 1.;self.A=1+self.H/self.Mf if finite else 1.
        self.beta=4*self.G/(3*self.K);self.eta=self.H/(2*self.G*self.B);self.kappa=1e-5/(1000*9.80665);self.cv=self.H*self.kappa/self.A
        self.legacy_cv=self.H*1e-5/(1000*9.81)
        if not finite:self.cv=self.legacy_cv # Explicitly reproduce paper's legacy incompressible reference.
        f=lambda z:(1-self.eta*z*z/2)*np.sin(z)-z*np.cos(z)
        self.xi=np.array([brentq(f,j*np.pi+1e-6,(j+1)*np.pi-1e-6,xtol=5e-15,rtol=1e-15) for j in range(modes)])
        z=self.xi;self.sx=np.sinc(z/np.pi)
        c=self.B*self.eta*(np.sin(z)-z)/(self.eta*z*np.cos(z)/2+(self.eta-1)*np.sin(z))
        self.amplitude=c/(1-self.sx);self.mean=3*(np.sin(z)-z*np.cos(z))/z**3-self.sx;self.decay=z*z*self.cv/R**2
    def pressure(self,tau,radius=.0025):
        tau=np.atleast_1d(tau).astype(float);out=np.full(tau.shape,np.nan);positive=tau>0
        shape=np.sinc(self.xi*radius/R/np.pi)-self.sx
        out[positive]=Q*(shape*self.amplitude)@np.exp(-self.decay[:,None]*tau[positive]);out[tau==0]=self.B*Q
        return out
    def mean_and_shell(self,tau,radius,weight,h):
        shell=radius>=R-2*h;sw=weight[shell]/weight[shell].sum();mean_shape=np.zeros(len(self.xi));shell_u=mean_shape.copy()
        for start in range(0,len(radius),2048):
            sl=slice(start,start+2048);rr=radius[sl];z=rr[:,None]*self.xi/R;sinc=np.sinc(z/np.pi);small=abs(z)<.02;phi=np.empty_like(z);zz=z[small]**2
            phi[small]=1/3-zz/30+zz**2/840-zz**3/45360+zz**4/3991680;phi[~small]=(np.sin(z[~small])-z[~small]*np.cos(z[~small]))/z[~small]**3
            mean_shape+=weight[sl]@(sinc-self.sx);mask=shell[sl];shell_u+=(weight[sl][mask]*rr[mask]/weight[shell].sum())@(phi[mask]+(self.beta*self.mean-self.sx)/3)
        tau=np.asarray(tau);valid=tau>=0;w=self.amplitude[:,None]*np.exp(-self.decay[:,None]*tau[valid]);mean=np.full(len(tau),np.nan);settle=mean.copy();stress=mean.copy()
        mean[valid]=Q*(mean_shape@w);settle[valid]=1000*Q/(3*self.K)*(sw@radius[shell])-1000*Q/self.H*(shell_u@w)
        stress[valid]=Q+(1-self.K/self.H)*mean[valid]-self.K/self.H*self.beta*Q*(self.mean@w)
        zero=tau==0;mean[zero]=self.B*Q;settle[zero]=1000*Q/(3*(self.K+self.Mf))*(sw@radius[shell]);stress[zero]=Q
        return mean,settle,stress

def selftest():
    sys.path.insert(0,str(TESTS/'support'));import cryer_radial_consistency_r1 as old
    rows=[]
    for _,nu,_,_ in GROUPS:
        r=Reference(nu)
        # Reuse the already derived radial-field method,with ALL local coefficients replaced.
        proxy=old.Reference.__new__(old.Reference);proxy.__dict__.update(r.__dict__);test=old.selftest(proxy)
        hi=Reference(nu,720);tau=np.geomspace(.0005,1.2,90)*R**2/r.legacy_cv
        err=float(abs(r.pressure(tau)-hi.pressure(tau)).max());assert err<1e-7
        rows.append(dict(nu=nu,B=r.B,A=r.A,eta=r.eta,legacy_cv=r.legacy_cv,finite_cv=r.cv,modes360_720_absmax_pa=err,radial_selftest=test))
    current=Reference(.3);prior=old.Reference();tau=np.geomspace(.0001,1.,100)
    assert np.max(abs(current.pressure(tau)-np.array([prior.field(np.array([.0025]),float(t))['p'][0] for t in tau])))<1e-8
    return rows

def extract(tag):
    group=next(g for g in GROUPS if g[0]==tag);_,nu,stem,steps=group;folder=CASE/(stem+'_out');p=parameters(folder,stem,nu)
    check=TESTS/'logs'/(TAG+'_nu'+tag+'.native.check.json');manifest=check.with_name(check.stem+'.inputs.json');summary=table_path(tag,'summary');center=table_path(tag,'center18')
    assert not any(x.exists() for x in [check,manifest,summary,center]),'Fresh extraction only; preserve earlier data'
    buildpath=TESTS/'logs/cryer_nu_native_r2.build.json';build=read(buildpath);assert build['built'] and build['exit_code']==0 and build['typed_LASTEXITCODE_captured_immediately'];verify(build['program'])
    for r in build['inputs']:verify(r)
    peerpath=TESTS/'logs/cryer_four_nu_identity_peer_r1.check.json';peer=read(peerpath)
    assert peer['passed'] and peer['initial_sample_identity']['all_four_initial_decoded_35_column_numeric_tables_bit_equal'] and peer['initial_sample_identity']['initial_comparison_soil_rows_per_group']==37173
    inputs=[bound(__file__),bound(buildpath),build['program'],p['runtime'],bound(folder/'Run.out'),bound(peerpath)];raw=sorted((folder/'data').glob('Part_*.bi4'));assert [x.name for x in raw]==[f'Part_{i:04d}.bi4' for i in range(1065)]
    started=time.perf_counter();stamps={};files=[]
    for i,path in enumerate(raw+[folder/'data/Part_Head.ibi4']):
        stat=path.stat();files.append(bound(path));stamps[str(path)]=(stat.st_size,stat.st_mtime_ns)
        if i%250==0:print(f'nu={nu}: hash {i}/{len(raw)}',flush=True)
    for name in ['execution_receipt_nu_r1.json','execution_receipt_r2.json','Run.csv']:
        if (folder/name).exists():inputs.append(bound(folder/name))
    text=(folder/'Run.out').read_text(errors='replace');assert 'Finished execution (code=0)' in text and int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==steps and 'NVIDIA RTX A6000' in text
    seal(manifest,dict(inputs=inputs,native_files=files,parameters=p,actual_expected_steps=steps,raw_SHA_passes=1,solver_started=False))
    argv=[build['program']['path'],str(folder/'data'),'1065',str(summary),str(center)];log=TESTS/'logs'/(TAG+'_nu'+tag+'.native.log')
    with log.open('xb') as f:result=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),check=False)
    assert result.returncode==0,('Read-only reducer failed,retain partial products',tag,result.returncode)
    a=pd.read_csv(summary,float_precision='round_trip');c=pd.read_csv(center,float_precision='round_trip');ref=Reference(nu)
    assert len(a)==1065 and len(c)==18*1065 and np.array_equal(a.part,np.arange(1065)) and a.center_count.eq(18).all() and a.native_soil_count.eq(37173).all()
    assert a.time_s.iloc[-1]==steps*DT==p['end'] and a.saved_step.iloc[-1]==steps-1 and a.symplectic_dt_s.eq(DT).all()
    delta=Fraction(str(p['tout']));grid=[]
    for part in range(1065):
        nominal=Fraction(part,8192) if part<=64 else Fraction(1,128)+(part-64)*delta;q=nominal/Fraction.from_float(DT);grid.append(min(steps,(q.numerator+q.denominator-1)//q.denominator))
    assert np.array_equal(a.time_s,np.array(grid)*DT) and np.array_equal(a.saved_step,np.r_[0,np.array(grid[1:])-1]),'Actual saved clock differs from declared output schedule'
    assert np.array_equal(a.time_s.iloc[:65],np.arange(65)/8192) and a.true_surface_count.eq(5153).all() and a.loc[a.time_s>TD,'true_surface_p_absmax_pa'].eq(0).all()
    pore=float(np.float32(.1))*float(np.float32(1000))*9.80665*float(np.float32(.3))/float(np.float32(2e8))*a.h_m.iloc[0]**2/float(np.float32(1e-5));assert DT<=pore
    assert len(c.id.unique())==18 and c.groupby('part').size().eq(18).all() and np.max(abs(c.r0_m-.0025))<1e-15
    for r in inputs:verify(r)
    assert all((path.stat().st_size,path.stat().st_mtime_ns)==stamps[str(path)] for path in raw+[folder/'data/Part_Head.ibi4'])
    verify(build['program']);seal(check,dict(passed=True,nu=nu,actual_saved_frames=1065,all_native_soil_states=1065*37173,source_manifest=bound(manifest),artifacts=[bound(summary),bound(center)],command=argv,owned_read_only_exit_code=result.returncode,log=bound(log),end_s=float(a.time_s.iloc[-1]),actual_steps=steps,source_statistics_unchanged_after_read=True,raw_SHA_passes=1,raw_second_pass='Size/mtime checked; full SHA recorded once before read',pore_dt_s=pore,elapsed_s=time.perf_counter()-started,full_half_validation=False,physical_acceptance=False,solver_started=False))
    print(f'nu={nu}: native complete, {time.perf_counter()-started:.1f}s',flush=True)

def plot():
    paths={k:DEST/(TAG+'_'+k+e) for k,e in [('log','.png'),('paper_limit_log','.png'),('state','.png'),('native','.csv'),('theory','.csv'),('metrics','.csv'),('summary','.json')]};check=TESTS/'logs'/(TAG+'.check.json')
    assert not check.exists() and not any(p.exists() for p in paths.values()),'New formal figure label only; never overwrite historical figures'
    tests=selftest();inputs=[bound(__file__)];history=[];curves=[];metrics=[];models=[]
    peerpath=TESTS/'logs/cryer_four_nu_identity_peer_r1.check.json';peer=read(peerpath);assert peer['passed'] and peer['initial_sample_identity']['all_four_initial_decoded_35_column_numeric_tables_bit_equal'];inputs.append(bound(peerpath))
    cloudpath=TESTS/'figures/cryer_full_native_r1_initial_cloud.csv';oldcheckpath=TESTS/'logs/cryer_full_native_r1.check.json';oldcheck=read(oldcheckpath);assert oldcheck['passed']
    cloudrecord=next(r for r in oldcheck['artifacts'] if Path(r['path']).name==cloudpath.name);verify(cloudrecord);verify(oldcheck['inputs_manifest'])
    oldmanifest=read(oldcheck['inputs_manifest']['path']);raw0=next(r for r in oldmanifest['inputs'] if r['path'].lower()==str((CASE/'CaseCryerProblem_PR_symc_nu030_out/data/Part_0000.bi4').resolve()).lower());verify(raw0)
    inputs += [bound(oldcheckpath),oldcheck['inputs_manifest'],cloudrecord,raw0]
    cloud=pd.read_csv(cloudpath,float_precision='round_trip');radius=cloud.r0_m.to_numpy();weight=cloud.weight0.to_numpy();assert len(radius)==37173 and abs(weight.sum()-1)<1e-12
    for tag,nu,stem,steps in GROUPS:
        receipt=TESTS/'logs'/(TAG+'_nu'+tag+'.native.check.json');record=read(receipt);assert record['passed'];verify(record['source_manifest']);inputs.append(bound(receipt));inputs.append(record['source_manifest'])
        for r in record['artifacts']:verify(r);inputs.append(r)
        a=pd.read_csv(table_path(tag,'summary'),float_precision='round_trip');c=pd.read_csv(table_path(tag,'center18'),float_precision='round_trip');ref=Reference(nu);paper=Reference(nu,finite=False);tau=a.time_s.to_numpy()-TD;tv=ref.legacy_cv*tau/R**2
        a['nu']=nu;a['tau_s']=tau;a['legacy_Tv']=tv;a['finite_storage_theta']=ref.cv*tau/R**2;a['sim_p_over_q0']=a.center_pressure_pa/Q;a['finite_Kw_fixed18_p_pa']=ref.pressure(tau);a['finite_Kw_fixed18_p_over_q0']=a.finite_Kw_fixed18_p_pa/Q;a['paper_incompressible_r0_p_over_q0']=paper.pressure(tau,0)/Q;a['error_pa']=a.center_pressure_pa-a.finite_Kw_fixed18_p_pa;a['shown_on_log_axis']=tv>0
        assert a.shown_on_log_axis.sum()==1000;assert set(c.loc[c.part.eq(0),'id'].astype(int))==set(cloud.loc[cloud.center18.astype(bool),'id'].astype(int));assert np.max(abs(c.loc[c.part.eq(0),['x0','y0','z0']].to_numpy()-cloud.loc[cloud.center18.astype(bool),['x0','y0','z0']].to_numpy()))==0
        mean,settlement,stress=ref.mean_and_shell(tau,radius,weight,float(a.h_m.iloc[0]));a['theory_pressure_mean_pa']=mean;a['theory_shell_inward_mm']=settlement;a['theory_total_mean_compression_pa']=stress
        grid=np.geomspace(.0005,1.2,1400);gt=grid*R**2/ref.legacy_cv;dense=pd.DataFrame(dict(nu=nu,legacy_Tv=grid,tau_s=gt,finite_storage_theta=ref.cv*gt/R**2,finite_Kw_fixed18_p_over_q0=ref.pressure(gt)/Q,paper_incompressible_r0_p_over_q0=paper.pressure(gt,0)/Q));curves.append(dense)
        domain=a.legacy_Tv.ge(.005);peak=a.loc[domain].center_pressure_pa.idxmax();j=int(peak);assert 64<j<1064
        scan=np.geomspace(.005,.5,400);v=ref.pressure(scan*R**2/ref.legacy_cv);k=int(v.argmax());assert 0<k<len(scan)-1
        opt=minimize_scalar(lambda z:-float(ref.pressure([z])[0]),bounds=(scan[k-1]*R**2/ref.legacy_cv,scan[k+1]*R**2/ref.legacy_cv),method='bounded',options={'xatol':1e-14});assert opt.success
        pt=float(opt.x);pp=float(-opt.fun);r=a.iloc[j];errors=a.loc[domain,'error_pa'].to_numpy()
        metrics.append(dict(nu=nu,saved_frames=1065,positive_time_frames=1000,dp_m=.0025,dt_s=DT,actual_end_s=float(a.time_s.iloc[-1]),drainage_relative_final_Tv=float(tv[-1]),sim_sampled_peak_p_pa=float(r.center_pressure_pa),theory_continuous_peak_p_pa=pp,peak_amplitude_error_percent=100*(r.center_pressure_pa/pp-1),sim_sampled_peak_tau_s=float(r.tau_s),theory_continuous_peak_tau_s=pt,peak_time_error_percent=100*(r.tau_s/pt-1),sim_sampled_peak_Tv=float(r.legacy_Tv),theory_continuous_peak_Tv=ref.legacy_cv*pt/R**2,left_save_tau_s=float(a.tau_s.iloc[j-1]),right_save_tau_s=float(a.tau_s.iloc[j+1]),mandel_window_RMS_error_pa=float(np.sqrt(np.mean(errors**2))),mandel_window_RMS_error_over_q0_percent=float(np.sqrt(np.mean(errors**2)))/Q*100,final_sim_center_pa=float(a.center_pressure_pa.iloc[-1]),final_theory_center_pa=float(a.finite_Kw_fixed18_p_pa.iloc[-1]),final_shell_sim_mm=float(a.shell_inward_mm.iloc[-1]),final_shell_theory_mm=float(settlement[-1]),initial_closed_pressure_target_pa=ref.B*Q,finite_B=ref.B,legacy_cv_m2_s=ref.legacy_cv,finite_cv_m2_s=ref.cv))
        history.append(a);models.append((nu,a,dense));print(f'nu={nu}: peak error {metrics[-1]["peak_amplitude_error_percent"]:.4f}%, time {metrics[-1]["peak_time_error_percent"]:.4f}%',flush=True)
    combined=pd.concat(history,ignore_index=True);dense=pd.concat(curves,ignore_index=True);m=pd.DataFrame(metrics)
    for key,data in [('native',combined),('theory',dense),('metrics',m)]:
        with paths[key].open('x',encoding='utf8',newline='') as f:data.to_csv(f,index=False,float_format='%.17g')
    # Cross-check the already accepted nu=.30 history without assigning its missing historical EXE hash.
    priorpath=DEST/'cryer_server_symc_full_r1_log_native.csv';prior=pd.read_csv(priorpath,float_precision='round_trip');current=history[2];assert np.array_equal(prior.time_s,current.time_s) and np.max(abs(prior.center_pressure_mean_pa-current.center_pressure_pa))<1e-8;inputs.append(bound(priorpath))
    import matplotlib
    matplotlib.use('Agg');import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'],'font.size':12,'mathtext.fontset':'stix'})
    colors=['#0072B2','#D55E00','#009E73','#CC79A7'];markers=['o','s','^','D']
    for key,theorycol,description in [('log','finite_Kw_fixed18_p_over_q0','Finite water bulk modulus; fixed initial center18, $r_0/a=0.05$'),('paper_limit_log','paper_incompressible_r0_p_over_q0','Paper reference limit: incompressible water, exact center $r=0$')]:
        fig,ax=plt.subplots(figsize=(11,7.5),constrained_layout=True)
        for (nu,a,d),color,marker in zip(models,colors,markers):
            shown=a[a.shown_on_log_axis];ax.plot(d.legacy_Tv,d[theorycol],color=color,ls=(0,(6,3)),lw=1.9,label=fr'Theory, $\nu={nu:g}$')
            ax.plot(shown.legacy_Tv,shown.sim_p_over_q0,color=color,lw=.8,marker=marker,markevery=12,ms=4,mfc='none',mew=.85,label=fr'SPH, $\nu={nu:g}$')
        ax.set(xscale='log',xlim=(5e-4,1.2),ylim=(0,1.6),xlabel=r'Drainage-relative $T_v=c_v(t-t_D)/a^2$',ylabel=r'Normalized pore pressure, $p^w/p_0$')
        ax.grid(True,which='major',color='.84',lw=.7);ax.grid(True,which='minor',color='.9',ls=':',lw=.6);ax.legend(loc='lower left',ncol=2,fontsize=11,frameon=True,fancybox=False,edgecolor='.45')
        ax.set_title('Cryer: four Poisson ratios, returned formal GPU runs\n'+description,fontsize=14)
        fig.supxlabel(r'$d_p=0.0025$ m, $k=10^{-5}$ m/s, $p_0=10$ kPa; $t_D=2^{-7}$ s. Legacy $c_v$ uses $g=9.81$.'+'\nAll native records retained in CSV; only positive drainage-relative times appear on the log axis. No fitted shift or scale.',fontsize=9)
        fig.savefig(paths[key],dpi=240);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    for (nu,a,d),color,marker in zip(models,colors,markers):
        shown=a[a.shown_on_log_axis];label=fr'$\nu={nu:g}$'
        axes[0,0].plot(shown.legacy_Tv,shown.error_pa/Q*100,color=color,label=label)
        axes[0,1].plot(shown.legacy_Tv,shown.shell_inward_mm,color=color,label=label);axes[0,1].plot(shown.legacy_Tv,shown.theory_shell_inward_mm,'--',color=color)
        axes[1,0].plot(shown.legacy_Tv,shown.total_mean_compression_pa/Q,color=color,label=label);axes[1,0].plot(shown.legacy_Tv,shown.theory_total_mean_compression_pa/Q,'--',color=color)
        axes[1,1].plot(shown.legacy_Tv,shown.center_pressure_std_pa,color=color,label=label)
    for ax,title,ylabel in zip(axes.flat,['Pressure error: fixed18 finite-Kw reference','Tracked shell inward displacement','Native-volume-weighted total compression','Center18 spatial spread (not uncertainty)'],['$(p_{SPH}-p_{theory})/p_0$ [%]','Inward displacement [mm]','Mean total compression / $p_0$','Center18 pressure standard deviation [Pa]']):
        ax.set(xscale='log',xlim=(5e-4,1.2),xlabel='$T_v$',ylabel=ylabel,title=title);ax.grid(True,which='both',alpha=.25);ax.legend(fontsize=10)
    fig.suptitle('Cryer four-ratio state comparison; solid=SPH, dashed=finite-Kw theory\nTheory uses fixed original native-volume/shell weights, not a fitted effective radius.',fontsize=13);fig.savefig(paths['state'],dpi=220);plt.close(fig)
    summary=dict(analysis_checks_passed=True,groups=metrics,reference_selftests=tests,sampling='Same18 initial native material IDs at r0/a=.05; all1065 actual saved times per group; no interpolation or smoothing',time='tau=t-2^-7; every nu has its own legacy_cv; finite_storage_theta retained separately',theory='Finite-Kw alpha1 small-strain quasistatic sphere conditional on equilibrated closed ramp/hold; paper incompressible point-center separately plotted',native_safety='All saved soil IDs, finite double positions/stress,elasticity/no exclusion,active true-surface drainage,natural/pore bounds checked by batch reducer and Python; not full-half convergence',limitations=['No new full-cycle half-step validation.','Nu=.30 historical actual EXE/DLL identity remains unknown; later package cannot repair it.','Finite-Kw theory omits inertia,damping and particle surface/quadrature effects.','Sampled peak timing is output-resolution limited; adjacent saves are not a confidence interval.'],physical_acceptance=False,solver_started=False)
    seal(paths['summary'],summary)
    for r in inputs:verify(r)
    seal(check,dict(passed=True,inputs=inputs,artifacts=[bound(p) for p in paths.values()],native_rows=len(combined),theory_rows=len(dense),actual_frames_per_nu=1065,nu030_matches_prior_center_history=True,reference_selftests=tests,solver_started=False,production_modified=False,old_figures_overwritten=False,physical_acceptance=False))
    print(str(paths['log']),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group();mode.add_argument('--extract',choices=[x[0] for x in GROUPS]);mode.add_argument('--plot',action='store_true');mode.add_argument('--selftest',action='store_true');args=parser.parse_args()
    if args.extract:extract(args.extract)
    elif args.plot:plot()
    elif args.selftest:print(json.dumps(selftest(),indent=2))
    else:parser.print_help()
