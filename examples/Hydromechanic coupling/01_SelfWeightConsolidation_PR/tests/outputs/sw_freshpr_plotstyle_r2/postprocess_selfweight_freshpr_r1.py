"""Standalone native fresh-PR self-weight plots/CSVs; diagnostics never grant physical acceptance."""
import argparse
import ast
import hashlib
import io
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

COLUMNS='time_s saved_step id x y z vx vy vz rho pressure sigma_xx sigma_yy sigma_zz sigma_xy sigma_yz sigma_xz kplastic load_ax load_ay load_az fstype normal_x normal_y normal_z load_available position_double stress_double mass dp h native_count nout has_dterror dterror_s is_boundary porepress0 excess_native'.split()
TARGETS=[.005,.05,.1,.25,.4,.5,.7,1.,1.5,2.]
SIGMA=['sigma_xx','sigma_yy','sigma_zz','sigma_xy','sigma_yz','sigma_xz']


def bound(path):
    path=Path(path).resolve(); digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return dict(path=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest())


def clean(value):
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    if isinstance(value,np.generic):return clean(value.item())
    return None if isinstance(value,float) and not math.isfinite(value) else value


def parameters(path):
    root=ET.parse(path).getroot(); f=np.float32
    def value(name,default=None):
        node=root.find('.//'+name)
        if node is None:node=root.find('.//parameter[@key="'+name+'"]')
        return float(node.get('value')) if node is not None else default
    e,nu=f(value('ModulusE')),f(value('PRvs')); K=f(e/(f(3)*(f(1)-f(2)*nu))); G=f(e/(f(2)*(f(1)+nu)))
    gravity=[float(f(root.find('.//gravity').get(k))) for k in ['x','y','z']]
    return dict(K=float(K),G=float(G),M=float(K)+4*float(G)/3,Mf=float(f(value('PoreWaterBulkModulus')))/float(f(value('Porosity'))),
        nu=float(nu),rho=float(f(value('rhop0'))),rho_w=float(f(value('PoreWaterRho'))),g=math.sqrt(sum(x*x for x in gravity)),gravity=gravity,
        k=float(f(value('HydraulicConductivity'))),safety=float(f(value('PoreDtSafety'))),H=float(root.find('.//newvarcte[@sizefz]').get('sizefz')),
        dp=float(root.find('.//newvarcte[@Dp]').get('Dp')),dt=value('DtFixed'),end=value('TimeMax'),init_mode=value('HydroMechInitMode'),
        shepard=value('PoreShepardRegularization'),G1=value('SoilStressRateGradCorr',0),SPR=value('SoilBoundaryDerivativeSPR',0),HG=value('SoilHourglassXi',0),
        damping=value('SoilDampingCoef'),slip=value('SlipMode'),save_double=value('SavePosDouble'))


def reference(z,t,p,height=None,finite=True):
    """Batched1024-term small-strain quasi-static reference, not exact dynamic startup truth."""
    z,t=np.asarray(z),np.asarray(t); H=p['H'] if height is None else height; B=p['Mf']/(p['M']+p['Mf']); cv=p['k']*p['M']/(p['rho_w']*p['g']); D=(B if finite else 1)*cv
    lam=(2*np.arange(1024)+1)*np.pi/(2*H); C=np.cos(z[:,None]*lam); S=np.sin(z[:,None]*lam); gamma=(p['rho']-p['rho_w'])*p['g']
    weights=2*B*gamma/(H*lam[:,None]**2)*np.exp(-D*lam[:,None]**2*t); q=(C@weights).T; integral=((S/lam)@weights).T
    rate=(S@(D*lam[:,None]*weights)).T/p['M']*1000; rate[t==0]=np.nan; q[t==0]=B*gamma*(H-z)
    settlement=(B*gamma*(H*z-z*z/2)-integral)/p['M']*1000; settlement[t==0]=0.; depth=np.maximum(H-z,0.)
    return dict(q_pa=q,p_pa=q+p['rho_w']*p['g']*depth,settlement_increment_mm=settlement,vertical_velocity_m_s=-rate/1000,
        sigma_zz_pa=q-gamma*depth,total_sigma_zz_pa=np.broadcast_to(-p['rho']*p['g']*depth,q.shape),legacy_Tv=cv*t/H**2,finite_Kw_Tv=B*cv*t/H**2)


def native(reader,directory,part):
    raw=subprocess.check_output([str(reader),str(directory),str(part)],timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    a=pd.read_csv(io.BytesIO(raw),dtype='<f8',float_precision='round_trip')
    assert list(a)==COLUMNS and len(a)==1040 and np.array_equal(a.id,np.arange(1040)),'Unexpected all-ID38-column native schema'
    return a


def initial_formula(a,p):
    s=a.iloc[40:]; z=s.z.to_numpy(); drained=(s.id.to_numpy().astype(int)-40)%100==99; depth=np.maximum(p['H']-z,0.); B=p['Mf']/(p['M']+p['Mf'])
    hydro=p['rho_w']*p['g']*depth; excess=B*max(0.,p['rho']-p['rho_w'])*p['g']*depth
    pressure=np.asarray(hydro+excess,dtype='<f4'); p0=np.asarray(hydro,dtype='<f4'); pressure[drained]=0.; p0[drained]=0.
    zz=np.asarray(-p['M']/(p['M']+p['Mf'])*max(0.,p['rho']-p['rho_w'])*p['g']*depth,dtype='<f4'); k0=np.float32(np.float32(p['nu'])/(np.float32(1)-np.float32(p['nu'])))
    want=dict(pressure=pressure,porepress0=p0,sigma_zz=zz,sigma_xx=k0*zz,sigma_yy=k0*zz,**{k:np.zeros(1000) for k in ['sigma_xy','sigma_yz','sigma_xz']})
    fields=[dict(field=k,different_bits=int(np.count_nonzero(s[k].to_numpy(dtype='<f8').view('<u8')!=np.asarray(v,dtype='<f8').view('<u8'))),max_abs_difference=float(abs(s[k].to_numpy()-v).max())) for k,v in want.items()]
    rho_match=bool(s.rho.eq(p['rho']).all())
    return dict(passed=rho_match and all(x['different_bits']==0 for x in fields),initial_soil_rho_matches_rhop0=rho_match,bulk_only_not_wall=True,fields=fields,drained_top_sigma_zz_pa=s.loc[drained,'sigma_zz'].tolist(),wall_formula_applied=False)


def hg_runtime(text):
    def one(pattern):
        found=re.findall(pattern,text); assert len(found)==1,('Missing/duplicate runtime record',pattern); return found[0]
    n=int(one(r'Steps of simulation\.*:\s*(\d+)')); xi,backend=one(r'SoilHourglassXi:\s*(\S+) \((CPU|GPU) elastic GNOG, endpoint-trapezoidal history\)')
    d=dict(steps=n,xi=float(xi),backend=backend,**dict(zip(['forcecalls','predictorupdates','correctorupdates','ratecalls'],map(int,one(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)')))))
    d.update(zip(['ratecalculations','endpoint_rate_reuses'],map(int,one(r'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)'))))
    d.update(zip(['max_net_history_force','max_net_actual_added_force','max_dt_tau','spinbound'],map(float,one(r'SoilHourglass: max\|sum\(m\*H\)\|=(\S+) max\|sum\(m\*deltaAce\)\|=(\S+) max\(dt/tau\)=(\S+) spinbound=(\S+)'))))
    d['passed']=bool(d['xi']==.1 and d['forcecalls']==d['ratecalls']==2*n and d['predictorupdates']==d['correctorupdates']==n and d['ratecalculations']+d['endpoint_rate_reuses']==2*n and 0<=d['endpoint_rate_reuses']<=2*n and all(np.isfinite(d[k]) and d[k]>=0 for k in ['max_net_history_force','max_net_actual_added_force','max_dt_tau','spinbound']) and d['max_dt_tau']<=.2 and d['spinbound']<.01)
    return d


def read_case(reader,folder,p,label,expected,strict=True):
    folder=Path(folder).resolve(); directory=folder if folder.name.lower()=='data' else folder/'data'; out=directory.parent; logfile=out/'Run.out'
    text=logfile.read_text(errors='replace'); assert 'Finished execution (code=0)' in text,'Completed Run.out required; never process a live or incomplete solver'
    parts=sorted(int(x.stem.split('_')[-1]) for x in directory.glob('Part_*.bi4')); assert parts==list(range(expected)),('Incomplete native catalog',len(parts),expected)
    inputs=[bound(logfile)]+[bound(x) for x in sorted(directory.iterdir()) if x.is_file() and (x.suffix.lower() in ['.bi4','.ibi4'])]
    first=None; profiles=[]; history=[]; ends=[]; errors=[]; vz=[]; clock=0.; clock_step=0; initial={}; hg=hg_runtime(text) if strict else dict(not_retroactively_required=True)
    if strict:
        assert hg['passed'] and all(x in text for x in ['HydroMechInitMode="AnalyticalSelfWeight1D"','mode=gravity-on self-weight','SoilBoundaryDerivativeSPR="MirroredWallDerivatives"','SoilStressRateGradCorr="KernelGradient"','PoreCompressionGradCorr="KernelGradient"','PoreShepardRegularization="Disabled"','SlipMode="DBC vel=0"','No Penetration=False'])
    for part in parts:
        a=native(reader,directory,part)
        if first is None:first=a.copy(); origin=float(a.time_s.iloc[0]); initial=initial_formula(a,p) if strict else dict(not_the_mode3_initial_state=True,own_initial_material_baseline=True)
        s,s0=a.iloc[40:],first.iloc[40:]; t=float(a.time_s.iloc[0]); saved=int(a.saved_step.iloc[0]); step=saved+1 if part else 0; fail=[]
        def guard(ok,name):
            if not bool(ok):fail.append(name)
        guard(np.isfinite(a.to_numpy()).all(),'finite38'); guard(a.rho.gt(0).all() and a.kplastic.eq(0).all() and a.nout.eq(0).all(),'rho_elastic_no_exclusion')
        guard(a.native_count.eq(1040).all() and np.array_equal(a.is_boundary,np.r_[np.ones(40),np.zeros(1000)]),'native_ID_partition'); guard(a.time_s.eq(t).all() and a.saved_step.eq(saved).all(),'uniform_native_metadata')
        guard(np.array_equal(a.porepress0.to_numpy().view('<u8'),first.porepress0.to_numpy().view('<u8')),'p0_fixed_bits'); guard(np.array_equal(a.excess_native.to_numpy(dtype='<f4').view('<u4'),(a.pressure.to_numpy(dtype='<f4')-a.porepress0.to_numpy(dtype='<f4')).view('<u4')),'native_float32_excess')
        guard(np.array_equal(a[['mass','dp','h']],first[['mass','dp','h']]),'fixed_mass_dp_h'); du=s[['x','y','z']].to_numpy()-s0[['x','y','z']].to_numpy(); dx=(du[:,0]+.05)%.1-.05
        surface=s.fstype.isin([2,3]); guard(set(s.id[surface])==set(first.id.iloc[139::100]) and s.pressure[surface].eq(0).all(),'true_top10_drainage')
        pore_limit=p['safety']*(p['rho_w']*p['g']/p['Mf'])*float(a.h.iloc[0])**2/p['k']; recurrence=None
        if strict:
            guard(origin==0. and a.position_double.eq(1).all() and a.stress_double.eq(1).all(),'fresh_zero_time_double_state'); guard(initial['passed'],'initial_bulk_formula')
            guard(s.z.gt(0).all() and abs(dx).max()*1000<.5 and np.ptp(s.z.to_numpy().reshape(10,100),axis=0).max()*1000<.5,'original_geometry')
            guard(step>=clock_step,'monotone_natural_step')
            while clock_step<step:clock+=p['dt']; clock_step+=1
            recurrence=t-clock; guard(abs(recurrence)<=1e-14,'sequential_binary64_clock'); guard(p['dt']<=pore_limit,'configured_native_h_pore_limit')
            if part:guard(a.has_dterror.eq(1).all() and a.dterror_s.max()<=1e-14,'original_signed_dterror')
        row=dict(dataset=label,part=part,time_s=t,elapsed_since_own_initial_s=t-origin,saved_step=saved,natural_step=step if strict else None,native_safety_passed=not fail,
            clock_recurrence_error_s=recurrence,dterror_s=float(a.dterror_s.max()),native_h_m=float(a.h.iloc[0]),pore_limit_s=pore_limit,configured_dt_over_pore_limit=p['dt']/pore_limit,
            rho_min=float(a.rho.min()),rho_max=float(a.rho.max()),speed_max_m_s=float(np.linalg.norm(s[['vx','vy','vz']],axis=1).max()),stress_double=int(a.stress_double.min()),position_double=int(a.position_double.min()))
        r=s.excess_native.to_numpy()+p['Mf']*(s.sigma_xx+s.sigma_yy+s.sigma_zz).to_numpy()/(3*p['K']); r=r[(s.id.to_numpy().astype(int)-40)%100!=99]
        row.update(r_990_rms_pa=float(np.sqrt(np.mean(r*r))),r_990_mean_pa=float(r.mean()),r_990_absmax_pa=float(abs(r).max())); history.append(row); vz.append(s.vz.to_numpy())
        if fail:errors.append(dict(part=part,time_s=t,guards=fail))
        top=float(s.iloc[99::100].z.mean())
        for layer in range(100):
            b,b0=s.iloc[layer::100],s0.iloc[layer::100]; u=dx[layer::100]; x=b0.x.to_numpy(); denom=float(np.sum((x-x.mean())**2)); epsx=float(np.sum((x-x.mean())*(u-u.mean()))/denom) if denom else np.nan
            rec=dict(dataset=label,part=part,time_s=t,elapsed_since_own_initial_s=t-origin,saved_step=saved,layer=layer,z0_m=float(b0.z.mean()),z_m=float(b.z.mean()),pressure_pa=float(b.pressure.mean()),porepress0_pa=float(b.porepress0.mean()),excess_native_pa=float(b.excess_native.mean()),
                q_fixed_double_pa=float((b.pressure-b.porepress0).mean()),q_current_pa=float((b.pressure-p['rho_w']*p['g']*np.maximum(top-b.z,0)).mean()),hydro_current_pa=float((p['rho_w']*p['g']*np.maximum(top-b.z,0)).mean()),
                settlement_increment_mm=float((b0.z.to_numpy()-b.z.to_numpy()).mean()*1000),rho_kg_m3=float(b.rho.mean()),eps_xx_material_regression=epsx,total_sigma_zz_pa=float((b.sigma_zz-b.pressure).mean()),speed_max_m_s=float(np.linalg.norm(b[['vx','vy','vz']],axis=1).max()),
                **{k:float(b[k].mean()) for k in SIGMA+['vx','vy','vz']})
            rec.update(hydro_current_minus_fixed_p0_pa=rec['hydro_current_pa']-rec['porepress0_pa'],native_excess_roundoff_pa=rec['excess_native_pa']-rec['q_fixed_double_pa'],r_layer_mean_pa=rec['excess_native_pa']+p['Mf']*(rec['sigma_xx']+rec['sigma_yy']+rec['sigma_zz'])/(3*p['K'])); profiles.append(rec)
        selected=s[((s.id.astype(int)-40)%100).isin([0,99])].copy(); selected['dataset']=label; selected['part']=part; selected['material_layer']=(selected.id.astype(int)-40)%100
        selected['settlement_increment_mm']=(s0.set_index('id').loc[selected.id,'z'].to_numpy()-selected.z.to_numpy())*1000; selected['q_fixed_double_pa']=selected.pressure-selected.porepress0; selected['q_current_pa']=selected.pressure-p['rho_w']*p['g']*np.maximum(top-selected.z,0.); ends+=selected.to_dict('records')
    if strict and (step!=hg['steps'] or step!=math.ceil(p['end']/p['dt'])):errors.append(dict(guard='final_natural_step_not_configured_completed_end'))
    return dict(profiles=pd.DataFrame(profiles),history=pd.DataFrame(history),endpoints=pd.DataFrame(ends),inputs=inputs,errors=errors,initial=initial,hg=hg,origin=origin,raw_vz=np.asarray(vz),legacy=not strict)


def enrich(case,p):
    a,h=case['profiles'],case['history']; n=len(h); get=lambda k:a[k].to_numpy().reshape(n,100); z=get('z0_m')[0]; t=h.elapsed_since_own_initial_s.to_numpy(); hd=float(z[-1]); B=p['Mf']/(p['M']+p['Mf']); cv=p['k']*p['M']/(p['rho_w']*p['g'])
    h['legacy_Tv']=cv*t/p['H']**2; h['finite_Kw_Tv']=B*h.legacy_Tv; a['legacy_Tv']=np.repeat(h.legacy_Tv.to_numpy(),100); a['finite_Kw_Tv']=np.repeat(h.finite_Kw_Tv.to_numpy(),100)
    phi=np.cos(np.pi*z/(2*p['H'])); factor=float(phi.sum()/np.sum(phi*phi)); extra={}; references={}
    for key in ['pressure_pa','porepress0_pa','excess_native_pa','q_fixed_double_pa','q_current_pa','hydro_current_minus_fixed_p0_pa','settlement_increment_mm','sigma_zz','total_sigma_zz_pa','vz','eps_xx_material_regression']:
        x=get(key); extra['bottom_'+key]=x[:,0]; extra['top_'+key]=x[:,-1]; extra['mean_'+key]=x.mean(axis=1)
    extra['top_minus_bottom_settlement_mm']=get('settlement_increment_mm')[:,-1]-get('settlement_increment_mm')[:,0]
    for key in ['q_current_pa','q_fixed_double_pa']:extra['first_mode_'+key]=(get(key)@phi)/np.sum(phi*phi)
    for observed,key,unit in [('settlement_increment_mm','settlement','mm'),('sigma_zz','effective_sigma_zz','pa'),('pressure_pa','pressure','pa')]:
        x=get(observed); d=x[:,1:-1]-(x[:,:-2]+x[:,2:])/2; a[key+'_half_second_difference_'+unit]=np.c_[np.full(n,np.nan),d,np.full(n,np.nan)].reshape(-1)
        extra[key+'_stagger_interior_rms_'+unit]=np.sqrt(np.mean(d*d,axis=1)); extra[key+'_stagger_bulk10_to89_rms_'+unit]=np.sqrt(np.mean(d[:,9:89]**2,axis=1))
    extra['lateral_strain_x_absmax']=np.max(abs(get('eps_xx_material_regression')),axis=1)
    if not case['legacy']:
        assert abs(hd-(p['H']-p['dp']/2))<=1e-12
        for prefix,height,finite in [('H1_finite_',p['H'],True),('H1_legacy_',p['H'],False),('HD_finite_',hd,True)]:
            r=reference(z,t,p,height,finite); references[prefix]=r
            for key,value in r.items():a[prefix+key]=np.repeat(value,100) if value.ndim==1 else value.reshape(-1)
            for observed,want,name in [('pressure_pa','p_pa','pressure_rms_pa'),('settlement_increment_mm','settlement_increment_mm','settlement_rms_mm'),('sigma_zz','sigma_zz_pa','effective_sigma_zz_rms_pa')]:extra[prefix+name]=np.sqrt(np.mean((get(observed)-r[want])**2,axis=1))
            for key in ['p_pa','q_pa','settlement_increment_mm','vertical_velocity_m_s']:extra[prefix+'bottom_'+key]=r[key][:,0]; extra[prefix+'top_'+key]=r[key][:,-1]
        r=references['H1_finite_']; residual=get('q_current_pa')-r['q_pa']; perror=get('pressure_pa')-r['p_pa']
        for name,x in [('current_q_minus_H1_intrinsic_q_pa',residual),('absolute_p_minus_H1_total_p_pa',perror)]:
            a[name]=x.reshape(-1); extra['bottom_'+name]=x[:,0]; extra['mean_'+name]=x.mean(axis=1); extra['first_mode_'+name]=(x@phi)/np.sum(phi*phi)
        assert np.array_equal(get('z0_m'),np.broadcast_to(z,(n,100)))
        ref_vz=np.tile(r['vertical_velocity_m_s'],(1,10)); dv=case['raw_vz']-ref_vz
        extra.update(native1000_vz_H1_residual_rms_m_s=np.sqrt(np.mean(dv*dv,axis=1)),native1000_vz_H1_residual_absmax_m_s=np.max(abs(dv),axis=1),H1_reference_absmax_vz_m_s=np.max(abs(ref_vz),axis=1))
    case['history']=pd.concat([h,pd.DataFrame(extra)],axis=1); case.update(references=references,phi=phi,constant_projection_factor=factor,HD=hd); return case


def floor_estimates(h,factor,label):
    late=h[h.finite_Kw_Tv>=1]; assert len(late)>=2,'No late Tv>=1 observations; full-tail review pending'
    i=int(np.argmin(abs(h.finite_Kw_Tv.to_numpy()-1.5))); covered=bool(h.finite_Kw_Tv.iloc[-1]>=2); j=int(np.argmin(abs(h.finite_Kw_Tv.to_numpy()-2))) if covered else len(h)-1
    assert h.finite_Kw_Tv.iloc[i]>=1 and j>i; tau1,tau2=float(h.finite_Kw_Tv.iloc[i]),float(h.finite_Kw_Tv.iloc[j]); ratio=math.exp(-np.pi**2*(tau2-tau1)/4); result=[]
    fields=[('raw_current_q','q_current_pa',True),('current_q_minus_H1_intrinsic_q','current_q_minus_H1_intrinsic_q_pa',True),('absolute_p_error_not_floor_budget','absolute_p_minus_H1_total_p_pa',False)]
    for definition,suffix,budget in fields:
        for location in ['bottom','mean','first_mode']:
            key=location+'_'+suffix
            if key not in h:continue
            q1,q2=float(h[key].iloc[i]),float(h[key].iloc[j]); C=(q2-ratio*q1)/(1-ratio); equivalent=C/factor if location=='first_mode' else C
            result.append(dict(dataset=label,definition=definition,location=location,part1=int(h.part.iloc[i]),part2=int(h.part.iloc[j]),time1_s=float(h.time_s.iloc[i]),time2_s=float(h.time_s.iloc[j]),actual_finite_Tv1=tau1,actual_finite_Tv2=tau2,
                requested_Tv1=1.5,requested_Tv2=2.,Tv1_error=tau1-1.5,Tv2_error=tau2-2.,finite_Tv2_covered=covered,actual_delta_Tv=tau2-tau1,first_mode_decay_ratio=ratio,denominator=1-ratio,value1_pa=q1,value2_pa=q2,
                estimated_C_coefficient_pa=C,constant_projection_factor=factor if location=='first_mode' else 1.,estimated_uniform_floor_equivalent_pa=equivalent,
                residual_floor_budget_pa=5.,budget_applied=bool(budget and covered),budget_met=bool(abs(equivalent)<=5) if budget and covered else None,physical_acceptance=False))
    return pd.DataFrame(result),late


def selections(case,clock):
    h=case['history']; column='legacy_Tv' if clock=='legacy' else 'finite_Kw_Tv'; choices=[(str(target),target,int(np.argmin(abs(h[column].to_numpy()-target)))) for target in TARGETS]
    choices.append(('final_actual_finite_Tv',float(h.finite_Kw_Tv.iloc[-1]),len(h)-1)); result=[]
    for name,target,part in choices:
        b=case['profiles'][case['profiles'].part==part].copy(); b['selection_label']=name; b['selection_clock']='finite' if name.startswith('final') else clock; b['selection_requested_Tv']=target
        b['selection_actual_Tv']=float(h.finite_Kw_Tv.iloc[part] if name.startswith('final') else h[column].iloc[part]); b['selection_time_s']=float(h.time_s.iloc[part]); result.append(b)
    return pd.concat(result,ignore_index=True)


def plots(cases,selected,paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator, ScalarFormatter
    plt.rcParams.update({'font.size':9,'axes.grid':True,'grid.alpha':.25}); main=cases['fresh']; h=main['history']; t=h.legacy_Tv
    def save(fig,axes,path):
        for ax in axes.flat:
            ax.xaxis.set_major_locator(MaxNLocator(6)); fmt=ScalarFormatter(useOffset=False); fmt.set_scientific(False); ax.xaxis.set_major_formatter(fmt); ax.legend(fontsize=6)
        with path.open('xb') as stream:fig.savefig(stream,format='png',dpi=180)
        plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(16,10),constrained_layout=True)
    groups=list(selected[selected.dataset=='fresh'].groupby('selection_label',sort=False)); colors=plt.get_cmap('turbo')(np.linspace(.05,.95,len(groups)))
    for (name,b),color in zip(groups,colors):
        b=b.sort_values('layer'); label=name+' '+b.selection_clock.iloc[0]+' (actual '+format(b.selection_actual_Tv.iloc[0],'.5g')+')'
        for ax,key,scale in zip(axes.flat,['pressure_pa','q_current_pa','settlement_increment_mm','sigma_zz','total_sigma_zz_pa','eps_xx_material_regression'],[1000,1000,1,1000,1000,1]):ax.plot(b[key]/scale,b.z0_m,color=color,label=label)
        for i,key,scale in [(0,'p_pa',1000),(2,'settlement_increment_mm',1),(3,'sigma_zz_pa',1000),(4,'total_sigma_zz_pa',1000)]:axes.flat[i].plot(b['H1_finite_'+key]/scale,b.z0_m,'--',color=color,linewidth=.7)
    for ax,title in zip(axes.flat,['Total p [kPa]; dashed H1 finite-Kw','Current drained-plane hydro excess [kPa]','Own-initial settlement increment [mm]','Effective sigma zz [kPa]','Total sigma zz [kPa]','Lateral material regression strain']):ax.set(title=title,ylabel='Initial material z [m]')
    fig.suptitle('Fresh mode3 actual nearest saves; no interpolation; H1 quasi-static curves are not exact startup truth'); save(fig,axes,paths['profiles_png'])
    fig,axes=plt.subplots(3,3,figsize=(16,12),constrained_layout=True)
    specs=[[(0,'bottom_pressure_pa',1000),(0,'H1_finite_bottom_p_pa',1000)],[(1,'bottom_q_current_pa',1),(1,'bottom_excess_native_pa',1),(1,'H1_finite_bottom_q_pa',1)],[(2,'top_settlement_increment_mm',1),(2,'bottom_settlement_increment_mm',1),(2,'H1_finite_top_settlement_increment_mm',1)],
        [(3,'bottom_sigma_zz',1000),(3,'bottom_total_sigma_zz_pa',1000)],[(4,'speed_max_m_s',1),(4,'H1_reference_absmax_vz_m_s',1),(4,'native1000_vz_H1_residual_rms_m_s',1)],[(5,'r_990_rms_pa',1)],
        [(6,'H1_finite_pressure_rms_pa',1),(6,'H1_legacy_pressure_rms_pa',1),(6,'HD_finite_pressure_rms_pa',1)],[(7,'bottom_hydro_current_minus_fixed_p0_pa',1),(7,'bottom_current_q_minus_H1_intrinsic_q_pa',1),(7,'bottom_absolute_p_minus_H1_total_p_pa',1)],[(8,'lateral_strain_x_absmax',1)]]
    for group in specs:
        for i,key,scale in group:axes.flat[i].plot(t,h[key]/scale,label=key)
    for ax,title in zip(axes.flat,['Bottom p [kPa]','Bottom current / native fixed q [Pa]','Material increment [mm]','Bottom effective / total stress [kPa]','Raw speed / reference / signed-vz residual [m/s]','Direct non-top990 R RMS [Pa]','All-layer total p reference RMS [Pa]','Hydro baseline / q residual / p error [Pa]','Lateral-strain absmax']):ax.set(title=title,xlabel='Actual legacy Tv (finite-Kw Tv=B*legacy Tv)')
    fig.suptitle('All actual native saves; finite-Kw references quasi-static; no automatic physical acceptance'); save(fig,axes,paths['history_png'])
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    for label,case in cases.items():
        hh=case['history']; b=case['profiles'][case['profiles'].part==hh.part.iloc[-1]].sort_values('layer')
        axes[0,0].plot(b.settlement_increment_mm,b.z0_m,label=label+' own increment'); axes[0,1].plot(b.settlement_half_second_difference_mm,b.z0_m,label=label+' half second diff')
        axes[1,0].plot(hh.legacy_Tv,hh.settlement_stagger_interior_rms_mm,label=label+' interior1..98'); axes[1,0].plot(hh.legacy_Tv,hh.settlement_stagger_bulk10_to89_rms_mm,'--',label=label+' bulk10..89')
        axes[1,1].plot(hh.legacy_Tv,hh.effective_sigma_zz_stagger_interior_rms_pa,label=label+' effective stress')
    for ax,title in zip(axes.flat,['Final material settlement [mm]','Final alternating-layer indicator [mm]','Settlement half-second-difference RMS [mm]','Effective-stress half-second-difference RMS [Pa]']):ax.set_title(title)
    axes[0,0].set_ylabel('Initial material z [m]'); axes[0,1].set_ylabel('Initial material z [m]'); axes[1,0].set_xlabel('Actual own-baseline legacy Tv'); axes[1,1].set_xlabel('Actual own-baseline legacy Tv')
    fig.suptitle('Staggering diagnostics; legacy, if present, is a combined-improvements historical control'); save(fig,axes,paths['staggering_png'])
    if 'legacy' in cases:
        fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
        for label,case in cases.items():
            hh=case['history']; b=case['profiles'][case['profiles'].part==hh.part.iloc[-1]].sort_values('layer'); title=label+' actual finite Tv '+format(float(hh.finite_Kw_Tv.iloc[-1]),'.6g')
            axes[0,0].plot(b.q_current_pa,b.z0_m,label=title); axes[0,1].plot(b.settlement_increment_mm,b.z0_m,label=title+' own initial')
            axes[1,0].plot(hh.finite_Kw_Tv,hh.bottom_q_current_pa,label=label); axes[1,1].plot(hh.finite_Kw_Tv,hh.top_settlement_increment_mm,label=label)
        for ax,title in zip(axes.flat,['Final current-hydro q [Pa]; not equal final times','Final own-initial increment [mm]','Bottom current q [Pa]','Top own-initial increment [mm]']):ax.set_title(title)
        axes[1,0].set_xlabel('Actual own-baseline finite-Kw Tv'); axes[1,1].set_xlabel('Actual own-baseline finite-Kw Tv')
        fig.suptitle('Historical combined improvements, not isolated stress-precision A/B; no resampled metadata'); save(fig,axes,paths['legacy_png'])


def process(args):
    config=Path(args.config).resolve(); reader=Path(args.reader).resolve(); figures=Path(args.figures_dir).resolve(); assert reader.is_file(); figures.mkdir(parents=True,exist_ok=True)
    assert args.label and Path(args.label).name==args.label and re.fullmatch(r'[A-Za-z0-9_-]+',args.label); assert not list(figures.glob(args.label+'_nativepr_*')),'Fresh figure label required; never overwrite'
    stem=args.label+'_nativepr_'; paths={k:figures/(stem+s) for k,s in [('manifest','manifest.json'),('profiles_png','profiles.png'),('history_png','history.png'),('staggering_png','staggering.png'),('legacy_png','legacy_comparison.png')]+[(k,k+'.csv') for k in ['profiles','history','native_endpoints','selected_profiles','late_history','floor_estimates']]}
    p=parameters(config); assert p['init_mode']==3 and p['k']>0 and p['g']>0 and p['H']==1 and p['dp']==.01 and p['dt']>0 and p['shepard']==0 and p['G1']==p['SPR']==p['slip']==p['save_double']==1 and p['HG']==.1 and p['damping']==.02
    cases=dict(fresh=enrich(read_case(reader,args.data_dir,p,'fresh',args.expected_frames),p)); records=[bound(__file__),bound(config),bound(reader),bound(sys.executable)]+cases['fresh']['inputs']; legacy_status=dict(status='not_requested_or_not_present',comparison_complete=False)
    if args.legacy_dir:
        try:
            lp=parameters(args.legacy_config) if args.legacy_config else p
            if args.legacy_config:records.append(bound(args.legacy_config))
            cases['legacy']=enrich(read_case(reader,args.legacy_dir,lp,'legacy',401,False),lp); records+=cases['legacy']['inputs']
            legacy_status=dict(status='decoded401_native_frames',comparison_complete=True,combined_improvements_not_isolated_precision=True,constants_from_legacy_config=bool(args.legacy_config),own_initial_time_s=cases['legacy']['origin'])
        except Exception as failure:legacy_status=dict(status='pending_missing_incomplete_or_reader_unsupported',comparison_complete=False,error=repr(failure))
    selected=pd.concat([selections(case,args.profile_clock) for case in cases.values()],ignore_index=True); floors=[]; late=[]
    for label,case in cases.items():
        f,l=floor_estimates(case['history'],case['constant_projection_factor'],label); floors.append(f); late.append(l)
    data=dict(profiles=pd.concat([x['profiles'] for x in cases.values()],ignore_index=True),history=pd.concat([x['history'] for x in cases.values()],ignore_index=True),native_endpoints=pd.concat([x['endpoints'] for x in cases.values()],ignore_index=True),selected_profiles=selected,late_history=pd.concat(late,ignore_index=True),floor_estimates=pd.concat(floors,ignore_index=True))
    for key,a in data.items():
        with paths[key].open('x',encoding='utf8',newline='') as stream:a.to_csv(stream,index=False,float_format='%.17g')
    plots(cases,selected,paths); unique={r['path']:r for r in records}
    for record in unique.values():assert bound(record['path'])==record,'Input changed during offline review'
    mainfloors=data['floor_estimates'].query('dataset=="fresh" and budget_applied==True'); met=bool(len(mainfloors)==6 and mainfloors.budget_met.all())
    passed=not cases['fresh']['errors']
    manifest=dict(passed=passed,analysis_checks_passed=passed,postprocessing_completed=True,native_safety_passed=passed,parameters=p,inputs=list(unique.values()),versions=dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__),legacy=legacy_status,
        datasets={k:dict(frames=len(v['history']),initial_native_time_s=v['origin'],initial_reference=v['initial'],hg=v['hg'],native_errors=v['errors'],final=v['history'].iloc[-1].to_dict()) for k,v in cases.items()},
        reference_scope='H1 finite-Kw B*Cv quasi-static actual-mode3-bulk diagnostic,not exact dynamic startup/paper zero-p loading. HD is initial-native-top-plane different-domain sensitivity,not fitted. Settlement is own-initial material increment.',
        floor_scope='C assumes first-mode exponential plus constant,using actual finite deltaTv. Raw current-hydro q and q_current-H1 intrinsic excess are reported. Absolute total-p error retains hydro geometry offset and is explicitly NOT the5Pa numerical-floor budget. First-mode coefficient divided by discrete sum(phi)/sum(phi^2) is uniform-floor-equivalent,not a point value. No extrapolated finiteTv2 or automatically accepted physics.',
        residual_floor_budget_pa=5.,residual_floor_budget_diagnostic_met=met,physical_acceptance=False,automatic_full_acceptance=False,restart_acceptance=False,formal_acceptance=False,solver_started=False,
        native_reader_invocations_retained_datasets=sum(len(x['history']) for x in cases.values()),reader_scope='Automatic Pos/Posd and Sigma/SigmaState storage support; native PorePress0/Excess required; no reconstructed substitute. mass export is fluid mass even for walls. Optional failed legacy attempts are recorded pending,not counted as complete decoded datasets.',
        storage_scope='Native SigmaState is binary64 for fresh audits. PartVTK Sigma_kk/ij display arrays remain float and are NOT double-precision evidence. svextraparts saves normal metadata,not HG history or restart admission.',
        figures_require_visual_inspection=True,artifacts=[bound(path) for key,path in paths.items() if key!='manifest' and path.exists()])
    with paths['manifest'].open('x',encoding='utf8') as stream:json.dump(clean(manifest),stream,indent=2,allow_nan=False)
    return dict(manifest=str(paths['manifest']),passed=passed,native_safety_passed=passed,residual_floor_budget_diagnostic_met=met,physical_acceptance=False)


def selftest():
    ast.parse(Path(__file__).read_text(encoding='utf8')); assert len(COLUMNS)==38
    p=dict(M=2e6,Mf=2e8,k=.001,rho=2100.,rho_w=1000.,g=9.81,H=1.); z=np.array([0.,.005,.995,1.]); t=np.array([0.,.1,100.]); r=reference(z,t,p); B=p['Mf']/(p['M']+p['Mf'])
    np.testing.assert_allclose(r['q_pa'][0],B*(p['rho']-p['rho_w'])*p['g']*(1-z)); assert np.all(r['settlement_increment_mm'][0]==0) and np.isnan(r['vertical_velocity_m_s'][0]).all()
    np.testing.assert_allclose(r['finite_Kw_Tv'],B*r['legacy_Tv']); assert abs(r['settlement_increment_mm'][-1,-1]-B*(p['rho']-p['rho_w'])*p['g']/(2*p['M'])*1000)<1e-9
    dt=1e-6; rr=reference(z,np.array([.1-dt,.1+dt]),p); np.testing.assert_allclose(-r['vertical_velocity_m_s'][1]*1000,(rr['settlement_increment_mm'][1]-rr['settlement_increment_mm'][0])/(2*dt),rtol=1e-7,atol=1e-8)
    h=pd.DataFrame(dict(part=[0,1,2],time_s=[0.,1.49,2.00001],finite_Kw_Tv=[0.,1.49,2.00001])); factor=1.27
    for location in ['bottom','mean','first_mode']:h[location+'_q_current_pa']=(42*np.exp(-np.pi**2*h.finite_Kw_Tv/4)+3)*(factor if location=='first_mode' else 1)
    f,_=floor_estimates(h,factor,'synthetic'); np.testing.assert_allclose(f.estimated_uniform_floor_equivalent_pa,3.,atol=1e-12); assert f.budget_met.all()
    h.loc[2,'finite_Kw_Tv']=1.99; f,_=floor_estimates(h,factor,'synthetic'); assert not f.finite_Tv2_covered.any() and not f.budget_applied.any()
    repeated=pd.DataFrame(index=np.arange(300)); repeated['Tv']=np.repeat(h.finite_Kw_Tv.to_numpy(),100); assert repeated.Tv.iloc[100]==1.49
    return dict(passed=True,files_written=False,native_process_started=False,real_data_read=False,solver_started=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--selftest',action='store_true'); parser.add_argument('--config'); parser.add_argument('--data-dir'); parser.add_argument('--figures-dir',default='figures'); parser.add_argument('--label')
    parser.add_argument('--reader',default=str(Path(__file__).resolve().parent/'bin/ReadSelfWeightNative.exe')); parser.add_argument('--expected-frames',type=int,default=403); parser.add_argument('--profile-clock',choices=['legacy','finite'],default='legacy'); parser.add_argument('--legacy-dir'); parser.add_argument('--legacy-config'); args=parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif not all([args.config,args.data_dir,args.label]):parser.print_help()
    else:
        result=process(args); print(json.dumps(result)); raise SystemExit(0 if result['passed'] else 1)
