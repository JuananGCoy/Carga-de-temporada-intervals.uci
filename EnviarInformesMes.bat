@echo off
chcp 65001 > nul
echo ============================================
echo   INFORME MENSUAL DE ENTRENAMIENTO
echo   Intervals.icu Coaching Suite
echo ============================================
echo.
echo Generando y enviando balances mensuales...
echo.
python send_reports.py --mode monthly --force
echo.
echo Proceso completado. Revisa el log: reports_sent.log
pause
