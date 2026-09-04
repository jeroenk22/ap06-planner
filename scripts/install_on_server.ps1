# Installeert de AP06 Planner als Windows-taak op de interne server.
#
# Draai dit script EENMALIG op de server, in een PowerShell-venster "als administrator".
# Het script is idempotent: opnieuw draaien werkt de installatie bij in plaats van te
# dupliceren, dus het is ook bruikbaar om een update uit te rollen.
#
# De app draait daarna als geplande taak onder het SYSTEM-account: hij start automatisch
# bij het opstarten van de server, en herstart vanzelf als het proces vastloopt.

param(
    [string]$Projectroot = "C:\Apps\ap06-planner",
    [string]$Repo = "https://github.com/jeroenk22/ap06-planner.git",
    [string]$Branch = "develop",
    [int]$Port = 8501,
    [string]$TaskNaam = "AP06 Planner"
)

$ErrorActionPreference = "Stop"

function Stap($tekst) { Write-Host "`n=== $tekst ===" -ForegroundColor Cyan }
function Ok($tekst) { Write-Host "  [ok] $tekst" -ForegroundColor Green }
function Waarschuw($tekst) { Write-Host "  [let op] $tekst" -ForegroundColor Yellow }

# --- 1. Voorwaarden -----------------------------------------------------------------

Stap "Voorwaarden controleren"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    throw "Draai dit script in een PowerShell-venster dat als administrator is gestart."
}
Ok "administratorrechten"

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    throw "Python niet gevonden. Installeer Python 3.12 of hoger van python.org en vink 'Add to PATH' aan."
}
$versie = (& python --version 2>&1) -join ''
if ($versie -notmatch '3\.(1[2-9]|[2-9]\d)') {
    throw "$versie gevonden, maar 3.12 of hoger is nodig."
}
Ok "$versie op $python"

$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) {
    throw "Git niet gevonden. Installeer Git for Windows, of kopieer de projectmap handmatig naar $Projectroot en draai dit script opnieuw."
}
Ok "git op $git"

# --- 2. Code ophalen of bijwerken ----------------------------------------------------

Stap "Code ophalen"

if (Test-Path (Join-Path $Projectroot ".git")) {
    Set-Location $Projectroot
    & git fetch --quiet origin
    & git checkout --quiet $Branch
    & git pull --quiet --ff-only origin $Branch
    Ok "bijgewerkt naar laatste $Branch"
}
else {
    $ouder = Split-Path -Parent $Projectroot
    if (-not (Test-Path $ouder)) { New-Item -ItemType Directory -Path $ouder -Force | Out-Null }
    & git clone --quiet --branch $Branch $Repo $Projectroot
    Set-Location $Projectroot
    Ok "gekloond naar $Projectroot"
}

# --- 3. Virtual environment ----------------------------------------------------------

Stap "Virtual environment"

$venvPython = Join-Path $Projectroot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & python -m venv (Join-Path $Projectroot ".venv")
    Ok "venv aangemaakt"
}
else {
    Ok "venv bestaat al"
}

& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -e $Projectroot
Ok "dependencies geinstalleerd"

# --- 4. Configuratie en gegevens controleren -----------------------------------------

Stap "Configuratie en gegevens"

$envPad = Join-Path $Projectroot ".env"
$dbPad = Join-Path $Projectroot "data\ap06.db"
$ontbreekt = @()

if (-not (Test-Path $envPad)) {
    $ontbreekt += ".env  — kopieer .env.example naar .env en vul de sleutels in"
}
else { Ok ".env aanwezig" }

if (-not (Test-Path $dbPad)) {
    $ontbreekt += "data\ap06.db  — kopieer de monsternemer-database handmatig hierheen (staat niet in de repo)"
}
else { Ok "data\ap06.db aanwezig" }

if ($ontbreekt.Count -gt 0) {
    Waarschuw "Nog te plaatsen voordat de app bruikbaar is:"
    $ontbreekt | ForEach-Object { Write-Host "           - $_" -ForegroundColor Yellow }
}

# --- 5. Firewall ---------------------------------------------------------------------

Stap "Firewall"

$regelNaam = "AP06 Planner ($Port)"
$bestaand = Get-NetFirewallRule -DisplayName $regelNaam -ErrorAction SilentlyContinue
if ($bestaand) {
    Ok "firewallregel bestaat al"
}
else {
    New-NetFirewallRule -DisplayName $regelNaam -Direction Inbound -Protocol TCP `
        -LocalPort $Port -Action Allow -Profile Domain, Private | Out-Null
    Ok "poort $Port opengezet voor Domain en Private (niet Public)"
}

# --- 6. Geplande taak ----------------------------------------------------------------

Stap "Geplande taak"

$startScript = Join-Path $Projectroot "scripts\start_server.ps1"
if (-not (Test-Path $startScript)) { throw "Startscript niet gevonden: $startScript" }

$actie = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$startScript`" -Port $Port" `
    -WorkingDirectory $Projectroot

$trigger = New-ScheduledTaskTrigger -AtStartup

# ExecutionTimeLimit 0 = geen tijdslimiet; anders stopt Windows de app na drie dagen.
$instellingen = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

if (Get-ScheduledTask -TaskName $TaskNaam -ErrorAction SilentlyContinue) {
    Stop-ScheduledTask -TaskName $TaskNaam -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $TaskNaam -Confirm:$false
    Ok "bestaande taak verwijderd"
}

Register-ScheduledTask -TaskName $TaskNaam -Action $actie -Trigger $trigger `
    -Settings $instellingen -Principal $principal `
    -Description "AP06 Planner (Streamlit) op poort $Port" | Out-Null
Ok "taak '$TaskNaam' geregistreerd — start automatisch bij het opstarten van de server"

# --- 7. Starten en controleren -------------------------------------------------------

Stap "Starten"

Start-ScheduledTask -TaskName $TaskNaam

$gezond = $false
foreach ($poging in 1..30) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:$Port/_stcore/health" -TimeoutSec 3 -UseBasicParsing
        if ($r.StatusCode -eq 200) { $gezond = $true; break }
    }
    catch { }
}

if ($gezond) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
        Select-Object -First 1).IPAddress
    Ok "app draait"
    Write-Host "`nBereikbaar op: http://$ip`:$Port" -ForegroundColor Green
}
else {
    Waarschuw "De app reageerde niet binnen 60 seconden."
    Write-Host "  Controleer de taakstatus met: Get-ScheduledTaskInfo -TaskName '$TaskNaam'"
    Write-Host "  En het logboek in:            $Projectroot\logs"
}

Write-Host "`nBeheer:" -ForegroundColor Cyan
Write-Host "  stoppen : Stop-ScheduledTask  -TaskName '$TaskNaam'"
Write-Host "  starten : Start-ScheduledTask -TaskName '$TaskNaam'"
Write-Host "  status  : Get-ScheduledTaskInfo -TaskName '$TaskNaam'"
Write-Host "  updaten : draai dit script opnieuw"
