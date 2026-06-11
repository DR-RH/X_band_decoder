@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if not exist "data\raw_data_unprocessed" mkdir "data\raw_data_unprocessed"
if not exist "data\raw_data_processed" mkdir "data\raw_data_processed"
if not exist "data\loss_packet_group" mkdir "data\loss_packet_group"
if not exist "output\X_band_decoded" mkdir "output\X_band_decoded"
if not exist "output\report" mkdir "output\report"

python -m app.main

pause
