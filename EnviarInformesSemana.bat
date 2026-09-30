@echo off
chcp 65001 > nul
echo ========================================================
echo   Enviando Resumen Semanal a todos los deportistas...
echo ========================================================
python send_reports.py --mode weekly --force
pause
