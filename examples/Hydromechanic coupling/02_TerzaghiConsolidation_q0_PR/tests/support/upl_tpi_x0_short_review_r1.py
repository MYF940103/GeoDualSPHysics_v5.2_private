"""Offline-only review of the closed 151-save CPU X0 window; never invoke a program."""
import argparse
import csv
import json
import math
import struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
L = T/'logs'
PREFIX = 'upl_tpi_x0_short_r2'
COUNT, SOIL, FIXED, COLS = 151, 1000, 40, 26
SCHEMA = ('original','off','on')


def need(value, message):
    if not value:
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bind(entry):
    need(stat(entry['path']) == entry, 'Consumed stat changed: '+entry['path'])
    return entry


def save(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write('\n')


def csvout(path, rows):
    need(rows, 'Empty CSV result')
    with path.open('x', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def mem(path, header, stride, dtype):
    with path.open('rb') as f:
        got = struct.unpack('<'+'I'*len(header), f.read(4*len(header)))
    need(got == header and path.stat().st_size == 4*len(header)+COUNT*stride,
         'Binary header/length differs: '+str(path))
    return np.memmap(path, mode='r', offset=4*len(header), dtype=dtype, shape=(COUNT,))


def samebits(a, b):
    return a.shape == b.shape and np.array_equal(np.asarray(a).view('<u8'), np.asarray(b).view('<u8'))


def load(which):
    need(which in SCHEMA, 'Undeclared CPU variant')
    check = L/(PREFIX+'_'+which+'.native.check.json'); native = read(check)
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1,
         'A successful uniquely owned native read is required')
    completion = bind(native['completion']); done = read(completion['path'])
    need(done['passed'] and done['stage']=='upl_tpi_x0_short_r1_native' and done['window']=='x0_short15'
         and done['dt_s']==5e-6 and done['planned_completed_steps']==30000
         and done['samples']==COUNT and done['total_native_count']==1040
         and done['native_total_arrays']==22 and done['noninitial_signed_dterror_intervals']==150
         and done['post_open_frames']==141 and done['post_open_drained_particle_checks']==1410
         and done['typed22_exported'], 'Original closed native gates/schema failed')
    files = {Path(q['path']).name:bind(q) for q in native['files']}
    need(len(files)==len(native['files']), 'Repeated native output name')
    root = Path(completion['path']).parent
    for leaf,header,stride in (('typed22.bin',(1040,22,COUNT),220488),
                               ('original15.bin',(1040,15,COUNT),166408)):
        with (root/leaf).open('rb') as f:
            need(struct.unpack('<III',f.read(12))==header and
                 (root/leaf).stat().st_size==12+COUNT*stride,
                 'Original typed export header/length differs: '+leaf)
    q = mem(root/'physical.bin', (SOIL,COLS,COUNT), 208008,
            np.dtype([('t','<f8'),('q','<f8',(SOIL,COLS))]))
    clocks = mem(root/'clock.bin', (COUNT,28), 28,
                 np.dtype([('t','<f8'),('step','<u4'),('dt','<f8'),('signed','<f8')]))
    jt = mem(root/'common_j_theta.bin', (1040,2,COUNT), 16648,
             np.dtype([('t','<f8'),('a','<f8',(1040,2))]))
    n = mem(root/'soil_n.bin', (SOIL,1,COUNT), 8008,
            np.dtype([('t','<f8'),('n','<f8',(SOIL,))]))
    need(samebits(q['t'], clocks['t']) and samebits(q['t'], jt['t']) and samebits(q['t'], n['t']),
         'Original binary actual clocks differ')
    need(np.all(clocks['dt']==5e-6) and np.all(clocks['signed'][1:]<=1e-14)
         and np.all(clocks['signed'][1:]!=-np.finfo('f8').max), 'Original signed interval guard failed')
    need(samebits(jt['a'][:,FIXED:,0], q['q'][:,:,8])
         and samebits(jt['a'][:,FIXED:,1], q['q'][:,:,9]), 'Original J/theta exports disagree')
    with (root/'native_ids.csv').open(encoding='utf-8-sig', newline='') as f:
        ids = list(csv.DictReader(f))
    need(len(ids)==SOIL and [int(v['id']) for v in ids]==list(range(40,1040)), 'Native soil IDs differ')
    x0 = np.array([[float(v[k]) for k in ('x0','y0','z0')] for v in ids])
    need(samebits(q['q'][0,:,:3],x0), 'Native initial positions differ')
    layer = np.rint(x0[:,2]/.01-.5).astype(int)
    column = np.rint(x0[:,0]/.01-.5).astype(int)
    order = np.argsort(10*layer+column)
    need(np.array_equal((10*layer+column)[order],np.arange(SOIL)), 'Original 100x10 material lattice differs')
    rho = np.empty((COUNT,SOIL)); volume = np.empty_like(rho); kval = np.empty_like(rho)
    rows = 0
    with (root/'ledger.csv').open(encoding='utf-8-sig', newline='') as f:
        for v in csv.DictReader(f):
            i, j = divmod(rows,SOIL)
            need(i<COUNT and int(v['part'])==i and int(v['id'])==40+j
                 and float(v['time_s'])==q['t'][i] and float(v['J'])==q['q'][i,j,8]
                 and float(v['n_native'])==n['n'][i,j], 'Native ledger row order/time/J/n differs')
            rho[i,j]=float(v['rho_native_kg_m3']); volume[i,j]=float(v['V_native_m2']); kval[i,j]=float(v['k_native_m_s']); rows+=1
    need(rows==COUNT*SOIL and np.all(np.isfinite(q['q'])) and np.all(np.isfinite(rho))
         and np.all(np.isfinite(volume)) and np.all(np.isfinite(kval)), 'Incomplete/nonfinite native exports')
    consumed=[stat(Path(__file__)),stat(T/'notes/upl_tpi_x0_short_review_r1.md'),stat(check),completion,*files.values()]
    return dict(which=which,root=root,q=q,clocks=clocks,n=n,rho=rho,volume=volume,k=kval,
                x0=x0,layer=layer,column=column,order=order,consumed=consumed)


def fields(d):
    q=d['q']['q']; order=d['order']; time=d['q']['t']
    uz=1000*(q[:,:,2]-d['x0'][None,:,2]); settlement=-uz
    dx=q[:,:,0]-d['x0'][None,:,0]; dx-=.1*np.rint(dx/.1)
    pressure=q[:,:,6]; compression=pressure-q[:,:,15]
    p=pressure[:,order].reshape(COUNT,100,10)
    stress=compression[:,order].reshape(COUNT,100,10)
    u=uz[:,order].reshape(COUNT,100,10)
    sign=np.where(np.arange(10)%2, -1.,1.)
    pmean=p.mean(2); smean=stress.mean(2); umean=u.mean(2)
    qsecond=smean[:,2:]-2*smean[:,1:-1]+smean[:,:-2]
    return dict(time=time,uz=uz,settlement=settlement,dx=dx,pressure=pressure,compression=compression,
                pmean=pmean,smean=smean,umean=umean,Q=qsecond,
                altUz=np.mean(u*sign,2),altStress=np.mean(stress*sign,2),
                layer_error=np.max(np.abs(smean-10000),axis=1),topgap=np.abs(smean[:,99]-smean[:,98]))


def figures(path, d, a):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,2,figsize=(11.5,7.5),layout='constrained')
    ax[0,0].plot(a['time'],a['pressure'].mean(1)/1000,label='soil mean')
    ax[0,0].plot(a['time'],a['pmean'][:,0]/1000,label='bottom material layer')
    ax[0,0].set(ylabel='Pore pressure [kPa]');ax[0,0].legend()
    ax[0,1].plot(a['time'],-a['umean'][:,99],label='top material layer')
    ax[0,1].plot(a['time'],-a['umean'][:,0],label='bottom material layer')
    ax[0,1].set(ylabel='Material settlement [mm]');ax[0,1].legend()
    ax[1,0].plot(a['time'],a['layer_error'],label='max layer total-stress error')
    ax[1,0].plot(a['time'],a['topgap'],label='top two-layer gap')
    ax[1,0].axhline(100,color='k',ls='--',lw=.8,label='post-.1 s limit')
    ax[1,0].set_yscale('symlog',linthresh=100)
    ax[1,0].set(ylabel='Total compression diagnostic [Pa]');ax[1,0].legend()
    ax[1,1].plot(a['time'],np.max(np.abs(a['altUz']),axis=1))
    ax[1,1].set(ylabel='Max layer alternating-X Uz [mm]')
    for x in ax.flat:x.set_xlabel('Actual native time [s]');x.grid(alpha=.25)
    fig.suptitle(d['which']+' CPU 5 us; saved native fields; no theory acceptance')
    fig.savefig(path/'history.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6.5,6),layout='constrained')
    for target in (0.,.01,.025,.05,.1,.15):
        i=int(np.argmin(np.abs(a['time']-target)))
        ax.plot(a['pmean'][i]/1000,(np.arange(100)+.5)*.01,label=f't={a["time"][i]:.6f} s')
    ax.set(xlabel='Material-layer mean pore pressure [kPa]',ylabel='Initial material z [m]')
    ax.grid(alpha=.25);ax.legend();fig.savefig(path/'pressure_profiles.png',dpi=170);plt.close(fig)


def single(which):
    check=L/(PREFIX+'_'+which+'.review.check.json')
    out=T/'figures'/(PREFIX+'_'+which+'_review')
    need(not check.exists() and not out.exists(), 'Existing/partial single review protected')
    d=load(which);a=fields(d);q=d['q']['q'];post=a['time']>=.1-1e-7
    histories=[];layers=[]
    for i,t in enumerate(a['time']):
        loadproxy=np.sum((d['rho'][i]*d['volume'][i])[:,None]*q[i,:,22:25],axis=0)
        histories.append(dict(part=i,time_s=float(t),saved_step=int(d['clocks']['step'][i]),
            completed_step=0 if i==0 else int(d['clocks']['step'][i])+1,
            signed_dterror_s=float(d['clocks']['signed'][i]),pressure_mean_Pa=float(a['pressure'][i].mean()),
            pressure_RMS_Pa=float(np.sqrt(np.mean(a['pressure'][i]**2))),
            top_material_settlement_mm=float(-a['umean'][i,99]),bottom_material_settlement_mm=float(-a['umean'][i,0]),
            total_layer_error_max_Pa=float(a['layer_error'][i]),top_two_layer_gap_Pa=float(a['topgap'][i]),
            Q_layer_second_difference_RMS_Pa=float(np.sqrt(np.mean(a['Q'][i]**2))),
            alternating_X_Uz_layer_abs_max_mm=float(np.max(np.abs(a['altUz'][i]))),
            alternating_X_total_compression_layer_abs_max_Pa=float(np.max(np.abs(a['altStress'][i]))),
            minimum_soil_z_m=float(q[i,:,2].min()),max_periodic_lateral_drift_mm=float(1000*np.abs(a['dx'][i]).max()),
            min_J=float(q[i,:,8].min()),max_J=float(q[i,:,8].max()),min_native_n=float(d['n']['n'][i].min()),
            max_native_n=float(d['n']['n'][i].max()),min_native_rho=float(d['rho'][i].min()),max_native_rho=float(d['rho'][i].max()),
            J_mass_LoadAce_x_proxy_N_m=float(loadproxy[0]),J_mass_LoadAce_y_proxy_N_m=float(loadproxy[1]),
            J_mass_LoadAce_z_proxy_N_m=float(loadproxy[2])))
        for z in range(100):
            select=d['layer']==z
            layers.append(dict(part=i,time_s=float(t),initial_layer=z,initial_z_m=(z+.5)*.01,
                pressure_mean_Pa=float(a['pmean'][i,z]),total_compression_mean_Pa=float(a['smean'][i,z]),
                Uz_mean_mm=float(a['umean'][i,z]),alternating_X_Uz_mm=float(a['altUz'][i,z]),
                alternating_X_total_compression_Pa=float(a['altStress'][i,z]),
                total_compression_second_difference_Pa=float(a['Q'][i,z-1]) if 0<z<99 else '',
                J_mean=float(q[i,select,8].mean()),native_n_mean=float(d['n']['n'][i,select].mean()),
                native_rho_mean=float(d['rho'][i,select].mean()),native_k_mean=float(d['k'][i,select].mean())))
    gates=dict(post_0p1_layer_total_error_le_100Pa=bool(np.all(a['layer_error'][post]<=100)),
               post_0p1_top_two_layer_gap_le_100Pa=bool(np.all(a['topgap'][post]<=100)),
               no_soil_bottom_crossing=bool(np.all(q[:,:,2]>0)),
               periodic_lateral_drift_lt_0p5mm=bool(np.max(np.abs(a['dx']))<.0005))
    error=np.abs(a['smean']-10000)
    bad=np.argwhere(post[:,None] & (error>100))
    first=None
    if len(bad):
        i,z=map(int,bad[0]);first=dict(part=i,time_s=float(a['time'][i]),initial_layer=z,
             total_compression_mean_Pa=float(a['smean'][i,z]),absolute_error_Pa=float(error[i,z]),limit_Pa=100.)
    masked=np.where(post[:,None],error,-1.)
    ip,zp=map(int,np.unravel_index(np.argmax(masked),masked.shape))
    peak=dict(part=ip,time_s=float(a['time'][ip]),initial_layer=zp,
              total_compression_mean_Pa=float(a['smean'][ip,zp]),absolute_error_Pa=float(error[ip,zp]),limit_Pa=100.)
    gapbad=np.flatnonzero(post & (a['topgap']>100))
    firstgap=None if not len(gapbad) else dict(part=int(gapbad[0]),time_s=float(a['time'][gapbad[0]]),
                top_two_layer_gap_Pa=float(a['topgap'][gapbad[0]]),limit_Pa=100.)
    out.mkdir();csvout(out/'history.csv',histories);csvout(out/'layers.csv',layers);figures(out,d,a)
    for entry in d['consumed']:bind(entry)
    save(check,dict(stage=PREFIX+'_'+which+'.review',passed=True,analysis_complete=True,which=which,
        samples=COUNT,material_layers=100,layer_rows=len(layers),gates=gates,
        physical_pass=all(gates.values()),physical_gates_passed=all(gates.values()),
        first_post_0p1_layer_total_error_failure=first,peak_post_0p1_layer_total_error=peak,
        all_failing_post_0p1_layer_samples=int(len(bad)),first_post_0p1_top_gap_failure=firstgap,
        max_post_0p1_layer_total_error_Pa=float(np.max(a['layer_error'][post])),
        max_post_0p1_top_two_layer_gap_Pa=float(np.max(a['topgap'][post])),final_history=histories[-1],
        consumed=d['consumed'],consumed_stats_unchanged=True,files=[stat(p) for p in sorted(out.iterdir())],
        load_proxy_is_not_force_stage_guard=True,force_stage_guard_independently_observed=False,
        ON_theta_and_LoadAce_are_endpoint_not_half_stage=which=='on',
        Q_is_unthresholded_layer_second_difference=True,no_theory_accuracy_claim=True,
        ON_OFF_half_or_5Pa_equivalence_claimed=False,physical_acceptance=False,SHA_scans=0,
        solver_invocations=0,reader_invocations=0))


def bytes_equal(a,b):
    if a.stat().st_size!=b.stat().st_size:return False
    with a.open('rb') as fa,b.open('rb') as fb:
        while True:
            x,y=fa.read(1<<20),fb.read(1<<20)
            if x!=y:return False
            if not x:return True


def pair_off():
    check=L/(PREFIX+'_off_pair.check.json');need(not check.exists(),'Existing OFF pair review protected')
    a,b=load('original'),load('off');results={}
    for leaf in ('typed22.bin','clock.bin','physical.bin','original15.bin','common_j_theta.bin','soil_n.bin','typed22_layout.csv'):
        results[leaf]=bytes_equal(a['root']/leaf,b['root']/leaf)
    for e in a['consumed']+b['consumed']:bind(e)
    save(check,dict(stage=PREFIX+'_off_pair',passed=all(results.values()),analysis_complete=True,samples=COUNT,
        all22_payload_bytes_equal=results['typed22.bin'],all22_headers_included=True,
        all_signed_clock_bytes_equal=results['clock.bin'],all_headers_and_all151_records_preserved=True,
        exact_files=results,consumed=a['consumed']+b['consumed'],consumed_stats_unchanged=True,
        SHA_scans=0,solver_invocations=0,reader_invocations=0,physical_acceptance=False))


def compare():
    check=L/(PREFIX+'_on_compare.check.json');out=T/'figures'/(PREFIX+'_on_compare')
    need(not check.exists() and not out.exists(),'Existing/partial ON comparison protected')
    a,b=load('original'),load('on');fa,fb=fields(a),fields(b)
    need(samebits(fa['time'],fb['time']) and np.array_equal(a['clocks']['step'],b['clocks']['step']),
         'Actual saved times/steps differ; no interpolation admitted')
    rows=[]
    for i,t in enumerate(fa['time']):
        dp=fb['pressure'][i]-fa['pressure'][i];du=fb['uz'][i]-fa['uz'][i]
        rows.append(dict(part=i,time_s=float(t),pressure_difference_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),
            material_Uz_difference_max_mm=float(np.max(np.abs(du))),
            original_top_settlement_mm=float(-fa['umean'][i,99]),ON_top_settlement_mm=float(-fb['umean'][i,99]),
            original_bottom_settlement_mm=float(-fa['umean'][i,0]),ON_bottom_settlement_mm=float(-fb['umean'][i,0]),
            original_pressure_RMS_Pa=float(np.sqrt(np.mean(fa['pressure'][i]**2))),ON_pressure_RMS_Pa=float(np.sqrt(np.mean(fb['pressure'][i]**2))),
            original_max_alternating_Uz_mm=float(np.max(np.abs(fa['altUz'][i]))),ON_max_alternating_Uz_mm=float(np.max(np.abs(fb['altUz'][i])))))
    out.mkdir();csvout(out/'comparison.csv',rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(2,2,figsize=(11,7.5),layout='constrained')
    for label,f in (('finite-Kw original',fa),('X0 beta=0',fb)):
        ax[0,0].plot(f['time'],f['pressure'].mean(1)/1000,label=label)
        ax[0,1].plot(f['time'],-f['umean'][:,99],label=label)
        ax[1,0].plot(f['time'],f['layer_error'],label=label)
        ax[1,1].plot(f['time'],np.max(np.abs(f['altUz']),axis=1),label=label)
    for x,title in zip(ax.flat,('Mean pore pressure [kPa]','Top material settlement [mm]',
                              'Max material-layer total-stress error [Pa]','Max alternating-X Uz [mm]')):
        x.set(xlabel='Actual saved time [s]',ylabel=title);x.grid(alpha=.25);x.legend()
    ax[1,0].set_yscale('symlog',linthresh=100)
    ax[1,0].axhline(100,color='k',ls='--',lw=.8)
    fig.suptitle('Different pressure models; actual matched times; no half/theory accuracy claim')
    fig.savefig(out/'comparison.png',dpi=170);plt.close(fig)
    for e in a['consumed']+b['consumed']:bind(e)
    save(check,dict(stage=PREFIX+'_on_compare',passed=True,analysis_complete=True,samples=COUNT,
        actual_times_and_steps_exact=True,interpolation=False,pressure_difference_RMS_max_Pa=max(r['pressure_difference_RMS_Pa'] for r in rows),
        material_Uz_difference_max_mm=max(r['material_Uz_difference_max_mm'] for r in rows),
        final_comparison=rows[-1],consumed=a['consumed']+b['consumed'],consumed_stats_unchanged=True,
        files=[stat(p)for p in sorted(out.iterdir())],ON_theta_and_LoadAce_are_endpoint_not_half_stage=True,
        finite_Kw_vs_incompressible_limit_not_same_equations=True,ON_OFF_5Pa_equivalence_claimed=False,
        accuracy_improvement_claimed=False,physical_acceptance=False,SHA_scans=0,solver_invocations=0,reader_invocations=0))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=('single','pair_off','compare'),required=True)
    p.add_argument('--which',choices=SCHEMA);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Independent offline review admission required')
    need((a.phase=='single')==(a.which is not None),'Use --which only with single')
    check=L/(PREFIX+'_'+a.which+'.review.check.json') if a.phase=='single' else L/(
          PREFIX+('_off_pair.check.json' if a.phase=='pair_off' else '_on_compare.check.json'))
    try:
        if a.phase=='single':single(a.which)
        elif a.phase=='pair_off':pair_off()
        else:compare()
    except Exception as error:
        if not check.exists():
            save(check,dict(stage=PREFIX+'.review_failure',passed=False,analysis_complete=False,
                 phase=a.phase,which=a.which,first_failure=str(error),partial_derived_outputs_preserved=True,
                 original_native_and_solver_outputs_untouched=True,automatic_retry=False,SHA_scans=0,
                 solver_invocations=0,reader_invocations=0,physical_acceptance=False))
        raise


if __name__=='__main__':main()
