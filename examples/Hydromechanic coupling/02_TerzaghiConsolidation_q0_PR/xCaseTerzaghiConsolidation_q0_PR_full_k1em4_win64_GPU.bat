@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

set case=CaseTerzaghiConsolidation_q0_PR_full_k1em4
set dirout=%case%_release_GPU_out
set diroutdata=%dirout%\data
set nsteps=7288429

set dirbin=../../../bin/windows
set gencase="%dirbin%/GenCase_win64.exe"
set dualsphysics="%dirbin%/DualSPHysics5.2_GEO_win64.exe"
set partvtk="%dirbin%/PartVTK_win64.exe"
set python=python
if exist "D:\Anaconda3\python.exe" set python=D:\Anaconda3\python.exe
set vars=+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress

if /i "%~1"=="-postprocess" goto postprocess
if exist "%dirout%" (
  echo Protected output "%dirout%" already exists. No files were deleted.
  echo Use -postprocess to review a completed run, or choose a new explicit output name.
  goto abort
)

rem Formal elastic u-pw PR consolidation: 1e-4 m/s, 2Tv, HG/SPR/band enabled.
%gencase% %case%_Def %dirout%/%case% -save:all
if not "%ERRORLEVEL%" == "0" goto fail

%dualsphysics% -gpu:0 -ompthreads:1 -stable -mdbc %dirout%/%case% %dirout% -dirdataout data -svres -svextraparts:1 -nsteps:%nsteps%
if not "%ERRORLEVEL%" == "0" goto fail

:postprocess
set vtkdir=%dirout%\particles
%partvtk% -dirin %diroutdata% -savevtk %vtkdir%/PartFluid -onlytype:-bound -vars:%vars%
if not "%ERRORLEVEL%" == "0" goto fail

"%python%" -B support/release_case.py --output "%dirout%" --label full_validation_release_k1em4_GPU
if not "%ERRORLEVEL%" == "0" goto fail

:success
echo q0 Terzaghi consolidation 1e-4 formal calculation and plots done.
popd
exit /b 0

:abort
echo Existing results preserved; no solver was launched.
popd
exit /b 0

:fail
echo q0 Terzaghi consolidation 1e-4 stopped. Existing data are preserved.
popd
exit /b 1
