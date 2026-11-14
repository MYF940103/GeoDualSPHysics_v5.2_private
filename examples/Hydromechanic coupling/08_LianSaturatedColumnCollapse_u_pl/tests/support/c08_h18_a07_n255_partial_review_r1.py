"""Compare the genuine failed33 AS.7 prefix to retained AS.5/n2.55, offline only."""
import argparse
from pathlib import Path
import c08_h18_compare_r2 as core
from c08_h18_centroid_partial_review_r1 import mapped
from c08_h18_wend_receiver_review_r1 import add_total_settlement

T, np = core.T, core.np
TAG = 'c08_h18_a07_n255_partial_review_r1'
RUN = 'c08_h18_a07_n255_r1'
CONTROL = 'c08_h18_as05_n255_r1'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execution-authorized', action='store_true')
    assert p.parse_args().execution_authorized
    out = T/'figures'/TAG
    check = T/'logs'/(TAG+'.check.json')
    assert not check.exists() and not list(out.parent.glob(TAG+'*')), 'Existing derived review protected'
    root = T/'outputs'/RUN/'native_partial_r1'
    control = T/'outputs'/CONTROL/'native_r1'
    source = T/'outputs/c08_h18_wend_psi0_pre_r2/native_r1'
    native_check = T/'logs/c08_h18_a07_n255_partial_native_run_r1.check.json'
    old_history = T/'figures/c08_h18_n255_review_r1_history.csv'
    paths = [Path(__file__), Path(core.__file__), native_check, old_history,
             T/'logs'/(RUN+'.run.json'), T/'logs/c08_h18_n255_review_r1.check.json']
    paths += [q/leaf for q in (root, control, source)
              for leaf in ('completion.json', 'typed22.bin', 'typed22_layout.csv', 'clocks.csv')]
    paths.append(root/'bedkeep_metadata.json')
    before = [core.stat(q) for q in paths]
    r, receipt = core.read(T/'logs'/(RUN+'.run.json')), core.read(native_check)
    d, m, sd = (core.read(q) for q in (root/'completion.json', root/'bedkeep_metadata.json', source/'completion.json'))
    assert not r['passed'] and not r['solver_completed'] and r['actual_exit'] == r['actual_Win32_exit'] == 1
    assert receipt['saved_prefix_native_passed'] and receipt['consumed_stats_unchanged'] and not receipt['whole_run_passed']
    assert d['diagnostic_complete'] and d['saved_prefix_native_passed'] and d['samples'] == 33
    assert not d['passed'] and not d['whole_run_passed'] and not d['unsaved_state_reconstructed']
    assert m['AS_coefficient_float_reference'] == core.f32(.7) and m['AS_exponent_float_reference'] == core.f32(2.55)
    assert sd['passed'] and sd['samples'] == 1001 and sd['certified_PRE'] and not sd['partial']
    assert core.read(control/'completion.json')['passed']
    for q in (root, control, source):
        layout = core.table(q/'typed22_layout.csv')
        assert len(layout) == 22
        for row,(name,kind,width) in zip(layout,core.SCHEMA):
            assert (row['array'],row['type'],int(row['components']),int(row['bytes_per_particle'])) == (name,kind,width,core.TYPES[kind].itemsize*width)
    pre, frames, baseline = mapped(source,7060,1001), mapped(root,6805,33), mapped(control,6805,91)
    assert np.array_equal(pre[0]['Idp'][:,0],np.arange(7060)) and np.array_equal(pre[-1]['Idp'][:,0],np.arange(7060))
    retained = [q for q in core.table(old_history) if q['tag'] == CONTROL][:33]
    assert len(retained) == 33
    clocks = core.table(root/'clocks.csv')
    assert len(clocks) == 33
    reference = dict(initial_pos=np.array(pre[0]['Posd']),pos=np.array(pre[-1]['Posd']),
                     p0=np.array(pre[-1]['PorePress0'][:,0]),time=float(pre[-1]['time']),source=retained[0]['source'])
    expected = np.r_[np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)]
    bundle = dict(spec=dict(tag=RUN,source=reference['source'],group='psi0',actualAS=dict(coefficient=.7,exponent=2.55)),
        root=root,done=d,source=False,count=33,nodes=6805,expected=expected,frames=frames,clocks=clocks,
        kw=1e9,yield_rows={},runtime_observed=dict(passed=False,solver_completed=False,actual_exit=1,actual_Win32_exit=1))
    analysis = core.analyze_case(bundle,reference,[.1,.2,.32])
    add_total_settlement(analysis,reference)
    for i,(a,b) in enumerate(zip(analysis['history'],retained)):
        assert a['time_s'] == float(b['time_s']) == float(baseline[i]['time'])
        assert a['completed_step'] == int(b['completed_step']) and np.array_equal(baseline[i]['Idp'][:,0],expected)
    outputs = []
    for name in ('history','extrema','layers','tracks'):
        q = Path(str(out)+'_'+name+'.csv'); core.write_csv(q,analysis[name]); outputs.append(q)
    panels = [('p_min_Pa','Minimum absolute pressure [kPa]',.001),('p_RMS_Pa','Absolute pressure RMS [kPa]',.001),
              ('top_material_settlement_mm','Original top-material settlement [mm]',1),('front_x_m','Front x [m]',1),
              ('NN_min_over_dp','Minimum spacing / dp',1),('pairs_r_lt_0p7dp','Close pairs r < .7dp',1),
              ('total_stress_Frobenius_RMS_Pa','Total stress RMS [kPa]',.001),('max_kappa','Maximum plastic history',1),
              ('current_mixture_KE_J_per_m','Current mixture KE [J/m]',1)]
    fig,axes=core.plt.subplots(3,3,figsize=(13,10),layout='constrained')
    for ax,(key,title,scale) in zip(axes.flat,panels):
        for rows,label in ((retained,'Completed AS .5; first33 saves'),(analysis['history'],'Failed AS .7; all33 saves')):
            ax.plot([float(q['tau_s']) for q in rows],[float(q[key])*scale for q in rows],label=label)
        ax.set(title=title,xlabel='Actual tau [s]');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Original raw-FS, hdp1.8, exponent2.55: matched saved states only\n'
                 'AS .7 failed later at reported tau .32958 s; no unsaved state reconstructed')
    q=Path(str(out)+'_comparison.png');fig.savefig(q,dpi=170);core.plt.close(fig);outputs.append(q)
    fig,axes=core.plt.subplots(2,2,figsize=(12,8),layout='constrained')
    for col,(f,label) in enumerate(((baseline[32],'AS .5'),(frames[32],'AS .7 FAILED partial'))):
        soil=f['Idp'][:,0]>=2060;pos=f['Posd'][soil];pressure=f['PorePress'][soil,0]/1000
        lo=min(float(baseline[32]['PorePress'][baseline[32]['Idp'][:,0]>=2060,0].min())/1000,float(frames[32]['PorePress'][soil,0].min())/1000)
        hi=max(float(baseline[32]['PorePress'][baseline[32]['Idp'][:,0]>=2060,0].max())/1000,float(frames[32]['PorePress'][soil,0].max())/1000)
        im=axes[0,col].scatter(pos[:,0],pos[:,2],c=pressure,s=5,cmap='coolwarm',vmin=lo,vmax=hi)
        fig.colorbar(im,ax=axes[0,col],label='Absolute pressure [kPa]')
        axes[1,col].scatter(pos[:,0],pos[:,2],s=3,color='black')
        for ax in axes[:,col]:ax.set_aspect('equal');ax.set(xlabel='x [m]',ylabel='z [m]',title=label+'; tau .320005 s')
    fig.suptitle('All 5000 raw soil points; shared full pressure range, no smoothing/clipping')
    q=Path(str(out)+'_fields.png');fig.savefig(q,dpi=170);core.plt.close(fig);outputs.append(q)
    assert all(core.stat(q['path']) == q for q in before)
    check.write_text(core.json.dumps(dict(stage=TAG,analysis_complete=True,physical_acceptance=False,
        whole_run_passed=False,matched_saved_samples=33,original_launch_samples=91,consumed=before,
        consumed_stats_unchanged=True,outputs=[core.stat(q) for q in outputs],partial_summary=analysis['summary'],
        control_same_time_end=retained[-1],no_interpolation=True,unsaved_state_reconstructed=False),indent=2)+'\n')


if __name__ == '__main__':main()
