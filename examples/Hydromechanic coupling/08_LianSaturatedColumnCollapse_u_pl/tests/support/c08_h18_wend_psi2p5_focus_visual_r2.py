"""Replot the sealed psi2p5 source history CSV; no numerical/native analysis."""
import argparse, csv, json
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_wend_psi2p5_focus_visual_r2'
BASE = 'c08_h18_wend_psi2p5_source_review_r1'
SOURCE = T / 'logs' / (BASE + '.check.json')
HISTORY = T / 'figures' / (BASE + '_history.csv')
CHECK = T / 'logs' / (TAG + '.check.json')
NOTE = T / 'notes' / (TAG + '.md')
WINDOWS = (('full',None),('last1s',1.),('last0p5s',.5))
CHARTS = (
    ('Pressure RMS','Pressure [kPa]',(('p_RMS_Pa','Absolute p',.001,0.),('native_p_minus_fixedP0_RMS_Pa','Native p - fixed P0',.001,0.))),
    ('Speed','Speed [m/s]',(('velocity_RMS_m_s','RMS',1.,0.),('max_speed_m_s','Maximum',1.,0.))),
    ('Stress RMS','Frobenius RMS [kPa]',(('effective_stress_Frobenius_RMS_Pa','Effective',.001,0.),('total_stress_Frobenius_RMS_Pa','Total',.001,0.))),
    ('Kinetic energy','Mixture KE [J/m]',(('current_mixture_KE_J_per_m','KE',1.,0.),)),
    ('Material settlement','Settlement [mm]',(('mean_settlement_reference_mm','All mean',1.,0.),('top_material_settlement_mm','Initial top layer',1.,0.),('bottom_material_settlement_mm','Initial bottom layer',1.,0.))),
    ('Volume and history','Dimensionless',(('max_kappa','Maximum kappa',1.,0.),('min_J','Minimum J - 1',1.,1.),('max_J','Maximum J - 1',1.,1.))),
)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized',action='store_true')
    assert parser.parse_args().execution_authorized, 'Root full read and explicit plotting authorization required'
    destinations = [T / 'figures' / (TAG + '_' + name + '.png') for name,_ in WINDOWS]
    assert not CHECK.exists() and not any(p.exists() for p in destinations), 'Protect existing complete/partial plots'
    check = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
    assert check['passed'] and check['analysis_complete'] and check['actual_samples'] == 1001
    assert check['group'] == 'psi2p5' and check['source_native_qualified'] and check['consumed_stats_unchanged']
    bound = next(q for q in check['files'] if Path(q['path']).resolve() == HISTORY.resolve())
    assert stat(HISTORY) == bound, 'Original sealed history CSV changed'
    original = [stat(SOURCE),bound]
    with HISTORY.open(encoding='utf-8-sig',newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1001 and all(int(r['part']) == i and r['group'] == 'psi2p5' for i,r in enumerate(rows))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    end = float(rows[-1]['time_s']); outputs = []
    for (name,duration),dest in zip(WINDOWS,destinations):
        selected = [r for r in rows if duration is None or float(r['time_s']) >= end-duration]
        x = [float(r['time_s']) for r in selected]
        fig,axes = plt.subplots(2,3,figsize=(15,8.5),layout='constrained')
        for ax,(title,unit,series) in zip(axes.flat,CHARTS):
            for column,label,scale,offset in series:
                ax.plot(x,[(float(r[column])-offset)*scale for r in selected],label=label,lw=1.25)
            ax.set(title=title,xlabel='Actual source time t [s]',ylabel=unit)
            ax.grid(alpha=.25); ax.legend(fontsize=8)
        fig.suptitle('Wendland psi = +2.5 deg preload: actual '+format(x[0],'.6f')+' to '+format(x[-1],'.6f')+' s\nSaved native histories; completion/certificate are not equilibrium acceptance',fontsize=13)
        fig.savefig(dest,dpi=170); plt.close(fig)
        outputs.append(dict(window=name,requested_duration_s=duration,first_actual_time_s=x[0],
                            last_actual_time_s=x[-1],rows=len(selected),figure=stat(dest)))
    assert all(stat(q['path']) == q for q in original), 'Original check/history CSV changed'
    result = dict(stage=TAG,passed=True,CSV_only_plot=True,source_check=original[0],source_history=bound,
        original_inputs_unchanged=True,original_figure_or_check_modified=False,actual_samples=1001,
        original_windows_and_series_preserved=True,charts=CHARTS,windows=outputs,
        numerical_analysis_recalculated=False,only_original_plot_unit_scales_and_J_minus1=True,
        visual_QA_pending=True,author_files=[stat(Path(__file__)),stat(NOTE)],physical_acceptance=False,
        solver_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0)
    with CHECK.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')


if __name__ == '__main__':
    main()
