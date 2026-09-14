@echo off
REM ============================================================
REM  IZBORNA NOC 2026 - jedan dvoklik i sve radi.
REM  1) dopuni strukturu sa RIK-a (opstine, mesta, liste)
REM  2) vrti agregatni collector u krug na 60s (<1 min po krugu)
REM  Prekid: Ctrl+C. Ponovno pokretanje nastavlja gde je stalo.
REM ============================================================
cd /d "%~dp0"

echo [1/2] Bootstrap strukture 2026...
python collector\bootstrap.py --election-type 2 --election-round 680072
if errorlevel 1 (
  echo BOOTSTRAP NIJE USPEO - proveri internet / RIK.
  pause
  exit /b 1
)

echo [2/2] Collector u krugu (60s). Prekid: Ctrl+C
python collector\aggregates.py --election-slug parlamentarni-2026 --interval 60
pause
