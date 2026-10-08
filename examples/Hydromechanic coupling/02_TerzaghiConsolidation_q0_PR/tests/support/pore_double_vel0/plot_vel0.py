"""Create the two reviewed static Vel0 comparison figures from analysis CSVs."""
import csv
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CASE = Path(__file__).resolve().parents[3]
LOG = CASE / 'tests/logs/pore_double_vel0'
FIG = CASE / 'figures'
BLUE, ORANGE, INK = '#3274A1', '#E1812C', '#262626'
REPLACE = False


def read(name):
    with (LOG / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def values(rows, key):
    a = np.array([float(r[key]) for r in rows])
    assert np.isfinite(a).all()
    return a


def frame(title, subtitle):
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 8.4))
    fig.subplots_adjust(left=.085, right=.975, top=.785, bottom=.185, wspace=.23, hspace=.30)
    fig.suptitle(title, x=.085, y=.973, ha='left', fontsize=16)
    fig.text(.085, .925, subtitle, fontsize=10.5)
    for col in range(2):
        axes[0, col].set_title('Full short run' if col == 0 else 'Load / drainage transition', loc='left', fontsize=11)
        for ax in axes[:, col]:
            ax.set_xlim(0, .2 if col == 0 else .03)
            ax.set_xlabel('Time (s)')
            ax.axvline(.01, color='#737373', ls=':', lw=.9)
    return fig, axes


def save(fig, stem):
    assert stem in ('pore_double_vel0_history','pore_double_vel0_differences','pore_double_vel0_event')
    for ext in ('png', 'pdf'):
        path = FIG / (stem + '.' + ext)
        assert REPLACE or not path.exists(), f'Refusing to replace {path}'
        fig.savefig(path, dpi=180, facecolor='white')
        print(path)
    plt.close(fig)


def plot_event():
    history, diffs = read('event_history.csv'), read('event_differences.csv')
    meta = json.loads((LOG / 'event_analysis.json').read_text(encoding='utf-8'))
    assert meta['common_frames'] == 61 and meta['excluded_from_timestep_comparison'] == 0
    fig, axes = frame('CPU Vel0 consolidation: the 0--30 ms event window',
        'Same physics and integrator | output-only sampling diagnostic | 61 measured common-time frames; no interpolation')
    for ax in axes.ravel():
        ax.set_xlim(0,.03)
    axes[0,0].set_title('Pressure / settlement histories',loc='left',fontsize=11)
    axes[0,1].set_title('Migration / step-halving differences',loc='left',fontsize=11)
    for run in meta['runs']:
        rows = [r for r in history if r['run']==run['name']]
        rows.sort(key=lambda r:float(r['time_s']))
        assert len(rows)==61
        old,coarse=run['build']=='baseline',run['dt_s']==1e-5
        style=dict(color=BLUE if old else ORANGE,ls='-' if coarse else '--',lw=1.4,
            label=('High/low' if old else 'Double state')+(' / 10 us' if coarse else ' / 5 us'),
            marker='o' if old else '^',markevery=11,markersize=3,markerfacecolor='none')
        axes[0,0].plot(values(rows,'time_s'),values(rows,'mean_pressure_pa')/1000,**style)
        axes[1,0].plot(values(rows,'time_s'),values(rows,'fixed_top_settlement_mm'),**style)
    for name,color,ls,label in (
        ('migration_10us',BLUE,'-','Migration / 10 us'),('migration_5us',BLUE,'--','Migration / 5 us'),
        ('step_baseline',ORANGE,'-','Step halving / high-low'),('step_current',ORANGE,'--','Step halving / double')):
        rows=[r for r in diffs if r['comparison']==name]
        rows.sort(key=lambda r:float(r['time_s']))
        for ax,key,factor in ((axes[0,1],'rms_pressure_difference_pa',1.),(axes[1,1],'settlement_difference_mm',1000.)):
            y=np.abs(values(rows,key))*factor
            ax.plot(values(rows,'time_s'),np.where(y>0,y,np.nan),color=color,ls=ls,lw=1.4,label=label,
                marker='o' if ls=='-' else '^',markevery=11,markersize=3,markerfacecolor='none')
            ax.set_yscale('log')
    axes[0,0].set_ylabel('Mean soil pressure (kPa)')
    axes[1,0].set_ylabel('Top-layer settlement (mm)')
    axes[0,1].set_ylabel('Soil pressure RMS difference (Pa)')
    axes[1,1].set_ylabel('Absolute settlement difference (um)')
    for col,anchor in ((0,.075),(1,.535)):
        handles,labels=axes[0,col].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(anchor,.895),ncol=2,fontsize=8.8)
    fig.text(.085,.11,'Vertical guide: prescribed 0.01 s event. Actual boundary activation is step-quantized; step difference is not true error.',fontsize=9)
    fig.text(.085,.077,'Right panels use log scales; exact-zero differences are omitted, including coincident migration settlement trajectories.',fontsize=9)
    fig.text(.085,.043,'Source: tests/logs/pore_double_vel0/event_history.csv and event_differences.csv. This supplements the original four runs.',fontsize=9)
    save(fig,'pore_double_vel0_event')


def main():
    global REPLACE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event',action='store_true',help='Render only the separate 0--30 ms figure.')
    parser.add_argument('--replace',action='store_true',help='Replace only the explicitly named figures from this test group for visual QA.')
    args=parser.parse_args()
    REPLACE=args.replace
    history, diffs = read('history.csv'), read('differences.csv')
    meta = json.loads((LOG / 'analysis.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'text.color':INK,
        'axes.labelcolor':INK, 'axes.spines.top':False, 'axes.spines.right':False,
        'axes.grid':True, 'grid.color':'#E4E4E4', 'grid.linewidth':.6,
        'legend.frameon':False, 'axes.formatter.useoffset':False})
    if args.event:
        plot_event()
        return
    fig, axes = frame('CPU Vel0 consolidation: pressure and settlement histories',
        'k = 1e-4 m/s | 1,000 soil particles | fixed initial top layer: 10 IDs | 201 frames per run')
    for run in meta['runs']:
        rows = [r for r in history if r['run'] == run['name']]
        assert len(rows) == 201
        rows.sort(key=lambda r: float(r['time_s']))
        t = values(rows, 'time_s')
        old, coarse = run['build'] == 'baseline', run['dt_s'] == 1e-5
        label = ('High/low' if old else 'Double state') + (' / 10 us' if coarse else ' / 5 us')
        style = dict(color=BLUE if old else ORANGE, ls='-' if coarse else '--',
                     marker='o' if old else '^', markevery=23 if coarse else 27,
                     markersize=3, markerfacecolor='none', lw=1.4, label=label)
        for col in range(2):
            axes[0,col].plot(t, values(rows,'mean_pressure_pa')/1000, **style)
            axes[1,col].plot(t, values(rows,'fixed_top_settlement_mm'), **style)
    for col in range(2):
        axes[0,col].set_ylabel('Mean soil pressure (kPa)')
        axes[1,col].set_ylabel('Top-layer settlement (mm)')
        axes[0,col].set_ylim(bottom=0)
        axes[1,col].set_ylim(bottom=0)
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper left', bbox_to_anchor=(.075,.889), ncol=4, fontsize=9.5)
    fig.text(.085,.11,'Vertical guide: prescribed 0.01 s load end / drainage start; actual activation occurs at a time-step boundary.',fontsize=9)
    fig.text(.085,.077,'Saved Part0 float position is a shared origin; subsequent positions and reconstructed pressure are read natively.',fontsize=9)
    fig.text(.085,.043,'Source: tests/logs/pore_double_vel0/history.csv. Overlapping curves do not establish full 2Tv accuracy.',fontsize=9)
    save(fig, 'pore_double_vel0_history')

    fig, axes = frame('CPU Vel0 consolidation: migration and time-step differences',
        f"Native BI4 pressure / position | migration: 201 frames | time-step comparison: {meta['common_frames']} common-time frames")
    for label, color, line, legend in (
        ('migration_10us',BLUE,'-','Migration / 10 us'),
        ('migration_5us',BLUE,'--','Migration / 5 us'),
        ('step_baseline',ORANGE,'-','Step halving / high-low'),
        ('step_current',ORANGE,'--','Step halving / double')):
        rows = [r for r in diffs if r['comparison'] == label]
        rows.sort(key=lambda r: float(r['time_s']))
        assert len(rows) >= 8
        t = values(rows, 'time_s')
        pressure = values(rows, 'rms_pressure_difference_pa')
        settlement = np.abs(values(rows, 'settlement_difference_mm')) * 1000
        for col in range(2):
            for ax,y in ((axes[0,col],pressure),(axes[1,col],settlement)):
                # Logarithmic display intentionally leaves exact zero differences blank.
                gaps=np.flatnonzero(np.diff(t)>.0015)+1
                tx=np.insert(t,gaps,np.nan)
                yy=np.insert(np.where(y>0,y,np.nan),gaps,np.nan)
                ax.plot(tx,yy,color=color,ls=line,lw=1.4,label=legend,
                        marker='o' if line=='-' else '^',markevery=23,markersize=2.5,markerfacecolor='none')
                ax.set_yscale('log')
                ax.grid(True, which='major')
    for col in range(2):
        axes[0,col].set_ylabel('Soil pressure RMS difference (Pa)')
        axes[1,col].set_ylabel('Absolute settlement difference (um)')
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.075,.889),ncol=4,fontsize=9.2)
    axes[0,1].text(.02,.84,'No matched step samples at 10-30 ms; see the event-window figure.',
        transform=axes[0,1].transAxes,va='top',fontsize=8.2,color='#525252')
    fig.text(.085,.11,'Log scales; exact zeros are not drawn. Missing common-time samples break the lines; no interpolation is used.',fontsize=9)
    fig.text(.085,.077,f"Step comparison excludes {meta['excluded_from_timestep_comparison']} misaligned frames (time tolerance 1e-11 s). Step sensitivity is not true error.",fontsize=9)
    fig.text(.085,.043,'Source: tests/logs/pore_double_vel0/differences.csv. Migration = double minus high/low; step = 5 us minus 10 us.',fontsize=9)
    save(fig,'pore_double_vel0_differences')


if __name__ == '__main__':
    main()
