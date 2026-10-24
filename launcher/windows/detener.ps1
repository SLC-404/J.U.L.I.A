# Detiene el servidor de J.U.L.I.A. en Windows (equivalente de
# launcher/stop.sh). MySQL y Ollama se quedan encendidos: no estorban y asi
# la siguiente vez abre mas rapido.
#
#   powershell -ExecutionPolicy Bypass -File launcher\windows\detener.ps1

$App    = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Logs   = Join-Path (Split-Path $App -Parent) "logs"
$Puerto = if ($env:ASISTENTE_PORT) { $env:ASISTENTE_PORT } else { 8000 }

$pids = @()
$pidFile = Join-Path $Logs "servidor.pid"
if (Test-Path $pidFile) { $pids += [int](Get-Content $pidFile) }
$pids += Get-NetTCPConnection -LocalPort $Puerto -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess

foreach ($p in ($pids | Sort-Object -Unique)) {
    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
}
Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Host "J.U.L.I.A. detenida."
