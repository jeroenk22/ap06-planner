# Start de AP06 Planner op de interne server (192.168.4.105).
#
# Alle paden in de app (data/ap06.db, logs/) zijn relatief aan de working directory,
# daarom zet dit script die eerst expliciet op de projectroot. Draai dit script als
# Windows-service via NSSM of als taak in de Taakplanner.

param(
    # Standaard 8501; geef een andere poort mee om een testinstance naast de live app te draaien.
    [int]$Port = 8501
)

$ErrorActionPreference = "Stop"

$Projectroot = Split-Path -Parent $PSScriptRoot
Set-Location $Projectroot

& "$Projectroot\.venv\Scripts\python.exe" -m streamlit run "src\ap06_planner\main.py" `
    --server.address 0.0.0.0 `
    --server.port $Port `
    --server.headless true `
    --server.fileWatcherType none
