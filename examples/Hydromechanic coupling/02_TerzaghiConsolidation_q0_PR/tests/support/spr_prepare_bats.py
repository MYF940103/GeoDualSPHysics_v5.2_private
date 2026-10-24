"""Add clickable reproduction entries without touching retained XML or outputs."""
from pathlib import Path
import xml.etree.ElementTree as ET
from spr_planes_run import TESTS


def main():
    entries=[]
    for tag,binary in [('spr_planes_r3_rel','spr_planes_r3rel'),('spr_planes_r2_dbg','spr_planes_r3dbg'),
                       ('spr_planes_r4_rel','spr_planes_r3rel'),('spr_planes_r4_dbg','spr_planes_r3dbg'),
                       ('spr_pulse_r1','spr_pulse_r1rel'),('spr_pulse_nopen_r1','spr_pulse_nopen_r2rel')]:
        for definition in sorted((TESTS/'configs').glob(tag+'_*_Def.xml')):
            # Earlier r3_rel/r2_dbg wedge drafts failed and are not reproduction
            # entries for the accepted final wedge geometry.
            if tag in ('spr_planes_r3_rel','spr_planes_r2_dbg') and '_wedge2_' in definition.name:continue
            name=definition.stem.removesuffix('_Def');manual=name+'_manual_r1'
            exe='spr_pulse.exe' if tag.startswith('spr_pulse') else 'spr_planes.exe'
            assert (TESTS/'outputs'/binary/exe).is_file()
            extra=''
            if exe=='spr_pulse.exe':
                root=ET.parse(definition);dt=float(root.find("execution/parameters/parameter[@key='DtFixed']").get('value'))
                extra=str(round(.002/dt))+' '+str(round(.00001/dt))+' '
            path=TESTS/'configs'/('x'+name+'_win64_CPU.bat');assert not path.exists()
            lines=['@echo off','setlocal EnableDelayedExpansion','pushd "%~dp0\\..\\.."','',
                'rem Bounded companion reproduction, not a formal consolidation run.',
                'rem Writes native diagnostic CSV/JSON; combined comparison plots remain a separate offline step.',
                'set name='+manual,'set dirout=tests\\outputs\\%name%','set dirinput=tests\\outputs\\%name%_input',
                'set dirbin=../../../bin/windows','set gencase="%dirbin%/GenCase_win64.exe"',
                'set diagnostic="tests/outputs/'+binary+'/'+exe+'"',
                'if exist %dirout% goto fail','if exist %dirinput% goto fail',
                '%gencase% tests/configs/'+name+'_Def %dirinput%/%name% -save:all',
                'if not "%ERRORLEVEL%"=="0" goto fail',
                '%diagnostic% '+extra+'-cpu -ompthreads:1 %dirinput%/%name% %dirout% -dirdataout data -sv:none',
                'if not "%ERRORLEVEL%"=="0" goto fail','popd','exit /b 0',':fail',
                'echo Diagnostic refused or failed. Existing results were not removed.','popd','exit /b 1','']
            with path.open('x',encoding='utf8') as stream:stream.write('\n'.join(lines))
            entries.append(path.name)
    print('Prepared',len(entries),'XML companion BAT entries; no solver started')


if __name__=='__main__':main()
