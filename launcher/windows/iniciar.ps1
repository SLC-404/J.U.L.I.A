# Arranca J.U.L.I.A. en Windows y abre el navegador. Lo corre el icono del
# escritorio (ver instalar.ps1), sin ventana. Es el equivalente de
# launcher/start.sh en la Mac.
#
# Si algo ya esta corriendo (MySQL, Ollama, el servidor), no lo vuelve a
# arrancar: abrir el icono dos veces solo abre otra pestana.
#
# Al abrir, si hay internet, se actualiza solo desde GitHub (git pull) y,
# si cambiaron las librerias, las instala. Sin internet sigue con lo que hay.

$ErrorActionPreference = "Continue"
$App     = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Raiz    = Split-Path $App -Parent
$Backend = Join-Path $App "backend"
$Python  = Join-Path $Backend ".venv\Scripts\python.exe"
$Logs    = Join-Path $Raiz "logs"
$Puerto  = if ($env:ASISTENTE_PORT) { $env:ASISTENTE_PORT } else { 8000 }
$Url     = "http://127.0.0.1:$Puerto"
New-Item -ItemType Directory -Force -Path $Logs | Out-Null
# Caches y modelos junto a J.U.L.I.A. (puede ser D:), igual que en instalar.ps1
$env:UV_CACHE_DIR  = Join-Path $Raiz "cache\uv"
$env:HF_HOME       = Join-Path $Raiz "cache\huggingface"
if (Test-Path (Join-Path $Raiz "ollama-modelos")) { $env:OLLAMA_MODELS = Join-Path $Raiz "ollama-modelos" }
$env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
            (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links") + ";" +
            (Join-Path $env:LOCALAPPDATA "Programs\Ollama")

Add-Type -AssemblyName System.Windows.Forms
function Avisar($mensaje) {
    # Ventana de aviso (no hay consola) y termina.
    [System.Windows.Forms.MessageBox]::Show($mensaje, "J.U.L.I.A.", "OK", "Warning") | Out-Null
    exit 1
}
function Log($texto) { Add-Content -Path (Join-Path $Logs "iniciar.log") -Value "$(Get-Date -Format s) $texto" }

function Puerto-Abierto($p) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $p); $c.Close(); return $true } catch { return $false }
}
function Esperar-Puerto($p, $segundos) {
    for ($i = 0; $i -lt $segundos; $i++) { if (Puerto-Abierto $p) { return $true }; Start-Sleep 1 }
    return $false
}

# Si ya esta corriendo, solo abre el navegador.
if (Puerto-Abierto $Puerto) { Start-Process $Url; exit 0 }

# 1. MySQL (servicio de Windows; normalmente ya arranco con la computadora)
if (-not (Puerto-Abierto 3306)) {
    Start-Service "JULIA-MySQL" -ErrorAction SilentlyContinue
    if (-not (Esperar-Puerto 3306 20)) {
        Avisar "La base de datos (MySQL) no está encendida.`n`nReinicia la computadora y vuelve a abrir J.U.L.I.A. Si sigue igual, avísale a César."
    }
}

# 2. Ollama (el modelo de IA)
if (-not (Puerto-Abierto 11434)) {
    $ollamaApp = Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama app.exe"
    if (Test-Path $ollamaApp) { Start-Process $ollamaApp }
    else { Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve" }
    if (-not (Esperar-Puerto 11434 30)) { Avisar "No se pudo encender Ollama (el modelo de IA). Avísale a César." }
}

# 3. Actualizacion desde GitHub (rapida; sin internet se salta)
if (Get-Command git -ErrorAction SilentlyContinue) {
    $antes = git -C $App rev-parse HEAD 2>$null
    $job = Start-Job { param($a) git -C $a fetch --quiet origin main 2>&1 } -ArgumentList $App
    if (Wait-Job $job -Timeout 20) {
        Receive-Job $job | Out-Null
        $remoto = git -C $App rev-parse origin/main 2>$null
        if ($remoto -and $remoto -ne $antes) {
            Log "actualizando $antes -> $remoto"
            git -C $App pull --ff-only --quiet 2>&1 | ForEach-Object { Log $_ }
            $cambios = git -C $App diff --name-only $antes HEAD 2>$null
            if ($cambios -contains "backend/requirements.txt" -or $cambios -contains "backend/overrides.txt") {
                Log "cambiaron las librerias; instalando"
                & uv pip install --python $Python -r (Join-Path $Backend "requirements.txt") --overrides (Join-Path $Backend "overrides.txt") 2>&1 | ForEach-Object { Log $_ }
            }
        }
    } else {
        Log "sin internet o GitHub lento; no se actualiza"
    }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
}

# 4. Respaldo del dia (si todavia no hay), en segundo plano
Start-Process -WindowStyle Hidden -FilePath $Python -ArgumentList "-m", "app.respaldo", "--si-falta" `
    -WorkingDirectory $Backend `
    -RedirectStandardOutput (Join-Path $Logs "respaldo.log") -RedirectStandardError (Join-Path $Logs "respaldo-error.log")

# 5. Servidor (FastAPI): sirve la API y la pantalla en el mismo puerto
$srv = Start-Process -WindowStyle Hidden -PassThru -FilePath $Python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Puerto" `
    -WorkingDirectory $Backend `
    -RedirectStandardOutput (Join-Path $Logs "servidor.log") -RedirectStandardError (Join-Path $Logs "servidor-error.log")
Set-Content -Path (Join-Path $Logs "servidor.pid") -Value $srv.Id

$listo = $false
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest "$Url/api/health" -UseBasicParsing -TimeoutSec 2 | Out-Null; $listo = $true; break } catch { Start-Sleep 1 }
}
if (-not $listo) { Avisar "El servidor no arrancó. Avísale a César (ver $Logs\servidor-error.log)." }

# 6. Abrir en el navegador de siempre
Start-Process $Url
