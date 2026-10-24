# Instalador de J.U.L.I.A. para Windows 10/11 (64 bits).
#
# Se corre UNA vez, en PowerShell abierto "como administrador":
#
#   irm https://raw.githubusercontent.com/SLC-404/J.U.L.I.A/main/launcher/windows/instalar.ps1 | iex
#
# Se puede volver a correr cuantas veces sea: lo que ya esta instalado se
# salta y lo que falta se instala (sirve tambien para "reparar").
#
# Que hace:
#   1. Instala con winget lo que falte: Git, uv (Python), Ollama, MySQL y
#      el runtime de Visual C++.
#   2. Baja el proyecto de GitHub a %LOCALAPPDATA%\JULIA\app (o lo actualiza).
#   3. Prepara MySQL como servicio de Windows ("JULIA-MySQL", solo escucha
#      en 127.0.0.1) y crea la base dev002.
#   4. Crea el entorno de Python e instala las librerias.
#   5. Baja los modelos: Ollama (qwen + nomic-embed-text), Whisper, Piper y
#      Chatterbox (~12 GB, una sola vez).
#   6. Importa el paquete de datos de la Mac (si se lo das) o indexa las leyes.
#   7. Crea el icono "J.U.L.I.A." en el escritorio y en el menu Inicio.
#
# Todo queda en la computadora; despues de instalar, J.U.L.I.A. funciona sin
# internet (solo lo usa para actualizarse).
#
# (Sin acentos a proposito: con "irm | iex" PowerShell 5.1 a veces los lee mal.)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # las barras de progreso hacen MUY lento Invoke-WebRequest

$Repo     = "https://github.com/SLC-404/J.U.L.I.A.git"
$Raiz     = if ($env:JULIA_DIR) { $env:JULIA_DIR } else { Join-Path $env:LOCALAPPDATA "JULIA" }
$App      = Join-Path $Raiz "app"
$Backend  = Join-Path $App "backend"
$Python   = Join-Path $Backend ".venv\Scripts\python.exe"
$Logs     = Join-Path $Raiz "logs"
# Los datos de MySQL van en C:\ProgramData (ruta sin acentos ni espacios: con
# un usuario "Juana Perez" con acento, MySQL falla en %LOCALAPPDATA%).
$MysqlDir = Join-Path $env:ProgramData "JULIA\mysql"
$Servicio = "JULIA-MySQL"

function Paso($texto)  { Write-Host ""; Write-Host "==> $texto" -ForegroundColor Cyan }
function Ok($texto)    { Write-Host "    $texto" -ForegroundColor Green }
function Aviso($texto) { Write-Host "    $texto" -ForegroundColor Yellow }
function Falla($texto) { Write-Host ""; Write-Host "ERROR: $texto" -ForegroundColor Red; Write-Host "Revisa el log: $Logs\instalacion.log"; throw $texto }

function Refrescar-Path {
    # winget agrega cosas al PATH, pero esta ventana no se entera sola
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links") + ";" +
                (Join-Path $env:LOCALAPPDATA "Programs\Ollama") + ";" +
                (Join-Path $env:USERPROFILE ".local\bin")
}

function Tiene($comando) { [bool](Get-Command $comando -ErrorAction SilentlyContinue) }

function Instalar-Winget($id, $nombre, $comando) {
    if ($comando -and (Tiene $comando)) { Ok "$nombre ya esta instalado"; return }
    Write-Host "    Instalando $nombre..."
    Nativo { winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements --disable-interactivity }
    # 0 = listo; -1978335189 = ya estaba instalado y no hay version nueva
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne -1978335189) { Falla "No se pudo instalar $nombre (winget $LASTEXITCODE)" }
    Refrescar-Path
    Ok "$nombre instalado"
}

function Puerto-Abierto($puerto) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $puerto); $c.Close(); return $true } catch { return $false }
}

function Esperar-Puerto($puerto, $segundos) {
    for ($i = 0; $i -lt $segundos; $i++) { if (Puerto-Abierto $puerto) { return $true }; Start-Sleep 1 }
    return $false
}

function Nativo([scriptblock]$Comando) {
    # Programas como mysqld, git u ollama escriben mensajes NORMALES por el
    # canal de errores; con $ErrorActionPreference = "Stop", PowerShell 5.1
    # los toma como falla y corta el instalador. Aqui se corren sin eso y se
    # juzgan por su codigo de salida ($LASTEXITCODE).
    $antes = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try { & $Comando 2>&1 | ForEach-Object { Write-Host "    $_" } }
    finally { $ErrorActionPreference = $antes }
}

function Py {
    $argumentos = $args   # dentro del bloque, $args seria otro
    Nativo { & $Python @argumentos }
    if ($LASTEXITCODE -ne 0) { Falla "Fallo: python $($argumentos -join ' ')" }
}

# --- 0. Revisiones ------------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $Raiz, $Logs | Out-Null
Start-Transcript -Path (Join-Path $Logs "instalacion.log") -Append | Out-Null

Write-Host ""
Write-Host "  J.U.L.I.A. - Jurisprudencia Unificada, Leyes e Inteligencia Aplicada" -ForegroundColor Magenta
Write-Host "  Instalador para Windows. Carpeta: $Raiz"

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { Falla "Abre PowerShell como administrador (clic derecho > Ejecutar como administrador) y vuelve a correr el comando." }
if (-not [Environment]::Is64BitOperatingSystem) { Falla "J.U.L.I.A. necesita Windows de 64 bits." }
if ($env:PROCESSOR_ARCHITECTURE -eq "ARM64") { Aviso "Esta computadora es ARM (Snapdragon): algunas partes pueden ir lentas o no funcionar." }
$libre = [math]::Round((Get-PSDrive ($Raiz.Substring(0, 1))).Free / 1GB)
if ($libre -lt 25) { Falla "Se necesitan unos 25 GB libres en el disco y hay $libre GB." }
Ok "Administrador, 64 bits, $libre GB libres"
if (-not (Tiene "winget")) { Falla "Falta winget (App Installer). Instalalo desde la Microsoft Store y vuelve a intentar." }
Refrescar-Path

# --- 1. Programas -------------------------------------------------------------------
Paso "1/7 Programas necesarios"
Instalar-Winget "Microsoft.VCRedist.2015+.x64" "Visual C++ (runtime)" $null
Instalar-Winget "Git.Git" "Git" "git"
Instalar-Winget "astral-sh.uv" "uv (Python)" "uv"
Instalar-Winget "Ollama.Ollama" "Ollama" "ollama"
$mysqld = Get-ChildItem "C:\Program Files\MySQL\MySQL Server*\bin\mysqld.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
if (-not $mysqld) {
    Instalar-Winget "Oracle.MySQL" "MySQL" $null
    $mysqld = Get-ChildItem "C:\Program Files\MySQL\MySQL Server*\bin\mysqld.exe" -ErrorAction SilentlyContinue | Sort-Object FullName | Select-Object -Last 1
    if (-not $mysqld) { Falla "Se instalo MySQL pero no encuentro mysqld.exe en C:\Program Files\MySQL" }
} else { Ok "MySQL ya esta instalado" }
$mysqlBin = $mysqld.DirectoryName

# --- 2. El proyecto -----------------------------------------------------------------
Paso "2/7 Proyecto J.U.L.I.A."
if (Test-Path (Join-Path $App ".git")) {
    Nativo { git -C $App pull --ff-only }
    if ($LASTEXITCODE -ne 0) { Aviso "No se pudo actualizar (sin internet o con cambios locales); sigo con lo que hay." } else { Ok "Actualizado" }
} else {
    Nativo { git clone $Repo $App }
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo bajar el proyecto de GitHub" }
    Ok "Descargado en $App"
}

# --- 3. MySQL -----------------------------------------------------------------------
Paso "3/7 Base de datos (MySQL)"
if (-not (Get-Service $Servicio -ErrorAction SilentlyContinue)) {
    if (Puerto-Abierto 3306) { Falla "Ya hay otro MySQL usando el puerto 3306. Detenlo o desinstalalo y vuelve a intentar." }
    $datos = Join-Path $MysqlDir "datos"
    $ini   = Join-Path $MysqlDir "my.ini"
    New-Item -ItemType Directory -Force -Path $MysqlDir | Out-Null
    # MySQL quiere diagonales normales en my.ini
    @"
[mysqld]
basedir=$((Split-Path $mysqlBin -Parent) -replace '\\','/')
datadir=$($datos -replace '\\','/')
port=3306
bind-address=127.0.0.1
character-set-server=utf8mb4
"@ | Set-Content -Path $ini -Encoding ASCII   # todo ASCII: ProgramData y Program Files
    $marca = Join-Path $MysqlDir "inicializado.txt"
    if ((Test-Path $datos) -and -not (Test-Path $marca)) {
        # Quedo a medias en un intento anterior (todavia sin servicio ni datos
        # de nadie): se borra y se vuelve a preparar.
        Aviso "La carpeta de MySQL quedo incompleta en un intento anterior; se rehace."
        Remove-Item -Recurse -Force $datos
    }
    if (-not (Test-Path $datos)) {
        # root sin contrasena: solo se puede entrar desde esta computadora (127.0.0.1)
        $mysqldExe = Join-Path $mysqlBin "mysqld.exe"
        Nativo { & $mysqldExe --defaults-file="$ini" --initialize-insecure --console }
        if ($LASTEXITCODE -ne 0) { Falla "No se pudo preparar la carpeta de datos de MySQL" }
        Set-Content -Path $marca -Value (Get-Date -Format s)
    }
    $mysqldExe = Join-Path $mysqlBin "mysqld.exe"
    Nativo { & $mysqldExe --install $Servicio --defaults-file="$ini" }
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo registrar el servicio $Servicio" }
    Ok "Servicio $Servicio creado (arranca solo con Windows)"
}
if ((Get-Service $Servicio).Status -ne "Running") { Start-Service $Servicio }
if (-not (Esperar-Puerto 3306 30)) { Falla "MySQL no arranco (revisa $MysqlDir\datos\*.err)" }
$mysqlExe = Join-Path $mysqlBin "mysql.exe"
Nativo { & $mysqlExe -h 127.0.0.1 -u root -e "CREATE DATABASE IF NOT EXISTS dev002 CHARACTER SET utf8mb4" }
if ($LASTEXITCODE -ne 0) { Falla "No se pudo crear la base dev002" }
Ok "MySQL listo, base dev002"

$envFile = Join-Path $Backend ".env"
if (-not (Test-Path $envFile)) { Copy-Item (Join-Path $Backend ".env.example") $envFile; Ok "Configuracion (.env) creada" }

# --- 4. Python ----------------------------------------------------------------------
Paso "4/7 Python y librerias (tarda varios minutos la primera vez)"
if (-not (Test-Path $Python)) {
    # uv baja su propio Python 3.14 (el mismo que en la Mac; no hace falta
    # instalar Python aparte)
    Nativo { uv venv --python 3.14 (Join-Path $Backend ".venv") }
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo crear el entorno de Python" }
}
Nativo { uv pip install --python $Python -r (Join-Path $Backend "requirements.txt") --overrides (Join-Path $Backend "overrides.txt") }
if ($LASTEXITCODE -ne 0) { Falla "No se pudieron instalar las librerias de Python" }
Ok "Librerias instaladas"

# --- 5. Modelos ---------------------------------------------------------------------
Paso "5/7 Modelos de IA (~12 GB la primera vez; si se corta, vuelve a correr el instalador)"
if (-not (Puerto-Abierto 11434)) {
    Start-Process -WindowStyle Hidden -FilePath "ollama" -ArgumentList "serve"
    if (-not (Esperar-Puerto 11434 30)) { Falla "Ollama no arranco" }
}
$modelo = "qwen3.5:9b"
$linea = Select-String -Path $envFile -Pattern '^OLLAMA_MODEL=(.+)$' | Select-Object -First 1
if ($linea) { $modelo = $linea.Matches[0].Groups[1].Value.Trim() }
foreach ($m in @($modelo, "nomic-embed-text")) {
    Write-Host "    Ollama: $m"
    Nativo { ollama pull $m }
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo bajar el modelo $m" }
}
Push-Location $Backend
Write-Host "    Voz: Whisper, Piper y Chatterbox"
Py -c "from app import voz; voz._modelo_whisper(); voz._voz_piper(); m = voz._modelo_chatterbox(); print('Chatterbox:', 'listo' if m else voz._chatterbox_error)"
Pop-Location
Ok "Modelos listos"

# --- 6. Datos -----------------------------------------------------------------------
Paso "6/7 Datos del despacho"
Push-Location $Backend
Py -c "from app.database import init_db; init_db()"
$hayClientes = 0
$ErrorActionPreference = "Continue"
$hayClientes = (& $mysqlExe -h 127.0.0.1 -u root -N -e "SELECT COUNT(*) FROM dev002.clients" 2>$null) -as [int]
$ErrorActionPreference = "Stop"
if ($hayClientes -gt 0) {
    Ok "Ya hay $hayClientes clientes; no se importa nada"
} else {
    $paquete = if ($env:JULIA_PAQUETE) { $env:JULIA_PAQUETE } else {
        Read-Host "    Si tienes el paquete de datos de la Mac (.zip), arrastralo aqui y da Enter (o solo Enter para empezar sin datos)"
    }
    $paquete = $paquete.Trim().Trim('"')
    if ($paquete) {
        if (-not (Test-Path $paquete)) { Falla "No encuentro el paquete: $paquete" }
        Py -m app.paquete importar "$paquete"
        Aviso "El paquete trae datos de clientes: borralo de la USB cuando confirmes que todo esta bien."
    } elseif (-not (Test-Path (Join-Path $Backend "chroma_db"))) {
        Write-Host "    Indexando las leyes (unos minutos)..."
        Py scripts\ingest_legal_corpus.py
    }
}
Pop-Location

# --- 7. Icono -----------------------------------------------------------------------
Paso "7/7 Icono en el escritorio"
$iniciar = Join-Path $App "launcher\windows\iniciar.ps1"
$icono   = Join-Path $App "launcher\windows\julia.ico"
$shell   = New-Object -ComObject WScript.Shell
$destinos = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "J.U.L.I.A..lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "J.U.L.I.A..lnk")
)
foreach ($lnk in $destinos) {
    $s = $shell.CreateShortcut($lnk)
    $s.TargetPath = "powershell.exe"
    $s.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$iniciar`""
    $s.WorkingDirectory = $App
    $s.IconLocation = $icono
    $s.Description = "J.U.L.I.A. - asistente legal"
    $s.Save()
}
Ok "Icono creado"

Stop-Transcript | Out-Null
Write-Host ""
Write-Host "  Listo. Abre J.U.L.I.A. con el icono del escritorio." -ForegroundColor Green
Write-Host "  (La primera vez el navegador pide permiso para el microfono: dale Permitir.)"
Write-Host ""
