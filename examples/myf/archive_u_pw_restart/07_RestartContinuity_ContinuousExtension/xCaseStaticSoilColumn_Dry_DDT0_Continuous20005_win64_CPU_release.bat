@echo off
set CASE=CaseStaticSoilColumn_Dry_DDT0_Continuous20005
set OUT=%CASE%_out
..\..\..\bin\windows\GenCase_win64.exe %CASE%_Def %OUT%\%CASE% -save:all
if errorlevel 1 exit /b %errorlevel%
..\..\..\bin\windows\DualSPHysics5.2CPU_win64.exe -cpu -mdbc %OUT%\%CASE% %OUT% -dirdataout data -sv:csv,binx
exit /b %errorlevel%
