"""Offline dtype repair of a completed preload probe; no solver or notifier."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cryer_start_r1 import TESTS,bound,native,utc
import cryer_preload_probe_r1 as probe

TAG='cryer_preload_offline_r1'
CSV=TESTS/'figures'/(TAG+'_summary.csv')
CHECK=TESTS/'logs'/(TAG+'.check.json')
HISTORY=TESTS/'figures'/(TAG+'_history.png')
DIAGNOSTICS=TESTS/'figures'/(TAG+'_diagnostics.png')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def floating_state(a):
    # An all-zero CSV column can be inferred as int64, although BI4 state is floating.
    # Explicit promotion changes no numeric value and does not change identity fields.
    b=a.copy()
    fields=probe.SIGMA+['pressure']
    b[fields]=b[fields].astype(np.float64)
    assert np.array_equal(b[fields].to_numpy(),a[fields].to_numpy())
    return b


def plots(table):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.18,'lines.linewidth':1.6})
    blue,orange,ink='#2166ac','#d17b0f','#333333'
    t=table.time_s.to_numpy()*1000
    full=(table.time_s>=probe.RAMP)&(table.time_s<=probe.DRAIN)
    def finish(fig,axes,path):
        for ax in axes.flat:
            ax.axvline(probe.RAMP*1000,color=ink,ls=':',lw=1)
            ax.axvline(probe.DRAIN*1000,color=ink,ls='--',lw=1)
            ax.set_xlim(t[0],t[-1]);ax.set_xlabel('Actual saved time (ms)')
            ax.legend(fontsize=8,loc='best')
        fig.suptitle('Cryer preload diagnostic: ramp / hold / drainage',fontsize=14)
        fig.text(.5,.01,'Dotted: ramp end; dashed: drainage source event (last closed save). No time shift or smoothing.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.035,1,.96));fig.savefig(path,dpi=160);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    ax=axes[0,0]
    ax.fill_between(t,table.pressure_min_pa/1000,table.pressure_max_pa/1000,color=blue,alpha=.12,label='Native min-max (not uncertainty)')
    ax.plot(t,table.pressure_mean_pa/1000,color=blue,label='Whole-material volume mean')
    ax.plot(t,table.center_pressure_mean_pa/1000,color=orange,label='Fixed 18-ID center mean')
    ax.plot(t[full],np.full(full.sum(),probe.P_TARGET/1000),color=ink,ls='--',label='Uniform undrained full-load reference')
    ax.set_title('Pressure');ax.set_ylabel('Pore pressure (kPa)')
    ax=axes[0,1]
    ax.plot(t,table.total_mean_compression_pa/1000,color=blue,label='Total mean compression')
    ax.plot(t,table.effective_mean_compression_pa/1000,color=orange,label='Effective mean compression')
    ax.plot(t[full],np.full(full.sum(),probe.Q/1000),color=ink,ls='--',label='Uniform total reference')
    ax.set_title('Stress');ax.set_ylabel('Compression-positive mean (kPa)')
    ax=axes[1,0]
    ax.plot(t,table.shell_inward_mean_mm,color=blue,label='Fixed outer-shell mean')
    ax.plot(t[full],table.shell_target_mean_mm[full],color=ink,ls='--',label='Reference at each native initial radius')
    ax.set_title('Material radial displacement');ax.set_ylabel('Inward displacement (mm)')
    ax=axes[1,1]
    ax.plot(t,table.speed_max_m_s,color=blue,label='Native maximum speed')
    ax.axhline(1e-5,color=ink,ls='--',label='Declared equilibrium speed criterion')
    ax.set_yscale('symlog',linthresh=1e-7);ax.set_title('Residual motion');ax.set_ylabel('Speed (m/s; symlog)')
    finish(fig,axes,HISTORY)
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    ax=axes[0,0]
    ax.plot(t,table.pressure_target_rms_pa,color=blue,label='Pressure target RMS')
    ax.plot(t,table.total_stress_target_six_rms_pa,color=orange,label='Total-stress six-component target RMS')
    ax.axhline(100,color=ink,ls='--',label='Declared closed-state criterion')
    ax.set_title('Uniform full-load target errors');ax.set_ylabel('Error (Pa)')
    ax=axes[0,1]
    ax.plot(t,table.isotropic_vector_residual_rms_mm,color=blue,label='Fixed-origin isotropic-fit vector RMS')
    ax.plot(t,table.shell_target_error_rms_mm,color=orange,label='Shell per-particle target-error RMS')
    ax.axhline(1e-5,color=ink,ls='--',label='Declared closed-state criterion')
    ax.set_yscale('symlog',linthresh=1e-7);ax.set_title('Geometric consistency');ax.set_ylabel('Error (mm; symlog)')
    ax=axes[1,0]
    ax.plot(t,table.fluid_content_from_stress_conditional,color=blue,label='Elastic-trace + pressure/storage modulus')
    ax.plot(t,table.fluid_content_from_isotropic_fit_conditional,color=orange,label='Isotropic geometric fit + pressure/storage')
    ax.set_title('Conditional small-strain content, not exact fluid mass');ax.set_ylabel('Dimensionless conditional observation')
    ax=axes[1,1]
    ax.plot(t,table.rho_mean_kg_m3-2100,color=blue,label='Native mean density minus initial density')
    ax.axhline(2100/(1-(-3*probe.STRAIN_TARGET))-2100,color=ink,ls='--',label='Uniform finite-storage small-strain reference')
    ax.set_title('Persistent float density observation');ax.set_ylabel('Density change (kg/m3)')
    finish(fig,axes,DIAGNOSTICS)


def main():
    assert not any(p.exists() for p in [CSV,CHECK,HISTORY,DIAGNOSTICS]),'Do not overwrite analysis evidence'
    oldrun=read(probe.RUN);oldcheck=read(probe.CHECK);state=read(probe.STATE)
    assert oldcheck['passed'] is False and oldrun['checked_frames']==0
    assert 'Cannot cast ufunc' in oldrun['traceback'] and 'residual[:,:3]+=Q' in oldrun['traceback']
    probe.verify([state['run_manifest'],oldrun['prepared_inputs'],oldrun['program'],oldrun['sealed_completion']])
    prep=read(oldrun['prepared_inputs']['path']);done=read(oldrun['sealed_completion']['path'])
    probe.verify(prep['inputs']+[prep['program']]);probe.verify(done['outputs'])
    assert done['solver_finished'] and done['owned_exited'] and done['exit_code']==0
    text=(probe.FOLDER/'Run.out').read_text(errors='replace')
    assert 'Finished execution (code=0)' in text
    assert int(re.search(r'Steps of simulation\.*:\s*(\d+)',text)[1])==probe.STEPS
    initial=floating_state(native(probe.FOLDER,0));reference=native(TESTS/'outputs/cryer_damp_peak_r1',0)
    fields=oldrun['initial_native_reference_fields0ulp']
    assert np.array_equal(initial[fields],reference[fields])
    rows=[]
    for part in range(probe.FRAMES):
        a=initial if part==0 else floating_state(native(probe.FOLDER,part))
        rows.append(probe.inspect(a,initial,part))
    table=pd.DataFrame(rows);eq=probe.equilibrium(rows)
    assert len(table)==69 and table.iloc[-1].time_s==probe.END
    with CSV.open('x',encoding='utf8',newline='') as stream:table.to_csv(stream,index=False,float_format='%.17g')
    plots(table)
    probe.verify(prep['inputs']+[prep['program']]);probe.verify(done['outputs'])
    result=dict(status='completed_solver_recovered_offline_pending_independent_review',utc=utc(),
        original_single_run_safety_passed=True,checked_frames=len(rows),actual_final_time_s=probe.END,
        physical_accepted=False,preload_equilibrium_accepted=False,half_accepted=False,full_cycle_accepted=False,
        solver_rerun=False,notifier_rearmed=False,production_changed=False,
        repair='Explicit numeric float64 parsing of SIGMA/pressure before unchanged frozen inspector; all numeric values unchanged.',
        old_terminal_status_preserved=oldrun['status'],equilibrium_diagnostics=eq,
        last_closed_state=rows[64],final_state=rows[-1],
        inputs=[bound(p) for p in [__file__,TESTS/'notes'/(TAG+'.md'),probe.RUN,probe.STATE,probe.CHECK,probe.COMPLETE,probe.PREP]],
        artifacts=[bound(p) for p in [CSV,HISTORY,DIAGNOSTICS]],
        limitations=['New equilibrium diagnostics are unchanged and distinct from original safety.',
            'Finite-Kw homogeneous references were not assigned; no drained theoretical curve is accepted.',
            'Part64 is pre-opening, Part65 is already tau=TimeOut, not tau=0.',
            'Conditional content is not exact fluid mass; float density is observed, not established as the cause.',
            'Old failed postprocessing receipts and all raw solver files remain byte-for-byte retained.'])
    with CHECK.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(status=result['status'],equilibrium_passed=eq['equilibrium_diagnostic_passed'],last_closed_state=rows[64])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:main()
    else:parser.print_help()
