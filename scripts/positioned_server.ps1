param(
    [string]$WindowTitle = "Ollama Web Platform ECO",
    [string]$CommandLine = "python app.py",
    [int]$Cols = 68,
    [int]$Lines = 14,
    [int]$PollSeconds = 2,
    [string]$PositionFile = "E:\my_projects\py_misc\ollama_web_platform_console_window_position.json",
    [int]$InitialPositionDelaySeconds = 12
)

$ErrorActionPreference = "SilentlyContinue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..")

# A posição da janela precisa sobreviver a novas extrações/versões do projeto.
# Por isso o arquivo fica fora da pasta versionada, no diretório fixo abaixo.
$localDataDir = Join-Path $projectRoot "data"
if (-not (Test-Path $localDataDir)) { New-Item -ItemType Directory -Path $localDataDir | Out-Null }

$positionFile = $PositionFile
$positionDir = Split-Path -Parent $positionFile
try {
    if (-not (Test-Path $positionDir)) {
        New-Item -ItemType Directory -Path $positionDir -Force | Out-Null
    }
} catch {
    Write-Host "Nao consegui criar $positionDir. Usando arquivo local de fallback."
    $positionFile = Join-Path $localDataDir "console_window_position.json"
    $positionDir = Split-Path -Parent $positionFile
}

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32WindowTools {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@

function Get-WindowRectObject([IntPtr]$Handle) {
    $rect = New-Object Win32WindowTools+RECT
    $ok = [Win32WindowTools]::GetWindowRect($Handle, [ref]$rect)
    if (-not $ok) { return $null }
    return [pscustomobject]@{
        x = $rect.Left
        y = $rect.Top
        width = [Math]::Max(200, $rect.Right - $rect.Left)
        height = [Math]::Max(120, $rect.Bottom - $rect.Top)
        saved_at = (Get-Date).ToString("s")
    }
}

function Save-WindowRect([object]$Rect) {
    if ($null -eq $Rect) { return }
    $Rect | ConvertTo-Json | Set-Content -Path $positionFile -Encoding UTF8
}

function Test-SavedPosition([object]$Value) {
    if ($null -eq $Value) { return $false }
    $names = $Value.PSObject.Properties.Name
    return ($names -contains "x" -and $names -contains "y" -and $names -contains "width" -and $names -contains "height")
}

$saved = $null
if (Test-Path $positionFile) {
    try {
        $candidate = Get-Content $positionFile -Raw | ConvertFrom-Json
        if (Test-SavedPosition $candidate) { $saved = $candidate }
    } catch { $saved = $null }
}

Write-Host "Abrindo servidor em janela posicionada..."
Write-Host "Arquivo de posicao: $positionFile"
if ($saved) {
    Write-Host ("Usando ultima posicao: X={0} Y={1} W={2} H={3}" -f $saved.x, $saved.y, $saved.width, $saved.height)
} else {
    Write-Host "Nenhuma posicao salva ainda. Posicione a janela onde quiser; ela sera lembrada."
}

$cmdText = "mode con: cols=$Cols lines=$Lines & title $WindowTitle & $CommandLine"
$proc = Start-Process -FilePath $env:ComSpec -ArgumentList "/k", $cmdText -WorkingDirectory $projectRoot -PassThru
try { $proc.PriorityClass = "BelowNormal" } catch {}

$handle = [IntPtr]::Zero
for ($i = 0; $i -lt 80; $i++) {
    Start-Sleep -Milliseconds 250
    $proc.Refresh()
    if ($proc.MainWindowHandle -ne 0) {
        $handle = [IntPtr]$proc.MainWindowHandle
        break
    }
}

if ($handle -ne [IntPtr]::Zero -and $saved) {
    [void][Win32WindowTools]::MoveWindow($handle, [int]$saved.x, [int]$saved.y, [int]$saved.width, [int]$saved.height, $true)
}

$shouldAnnounceFirstSave = $false
if (-not $saved -and $handle -ne [IntPtr]::Zero) {
    $shouldAnnounceFirstSave = $true
    Write-Host ""
    Write-Host "Janela pronta. Voce ja pode mover o terminal para a posicao desejada."
    Write-Host "Dica: arraste para o segundo monitor/canto desejado agora."
    Write-Host "Aguardando $InitialPositionDelaySeconds segundos antes de criar/gravar o arquivo de posicao..."
    for ($sec = $InitialPositionDelaySeconds; $sec -gt 0; $sec--) {
        if ($proc.HasExited) { break }
        Write-Host ("Gravando posicao em {0}s..." -f $sec)
        Start-Sleep -Seconds 1
    }
}

$lastRect = $null
$firstSaveDone = $false
while (-not $proc.HasExited) {
    $proc.Refresh()
    if ($proc.MainWindowHandle -ne 0) {
        $handle = [IntPtr]$proc.MainWindowHandle
        $rect = Get-WindowRectObject $handle
        if ($rect) {
            $lastRect = $rect
            Save-WindowRect $rect
            if ($shouldAnnounceFirstSave -and -not $firstSaveDone) {
                $firstSaveDone = $true
                Write-Host ""
                Write-Host ("Arquivo de posicao criado/atualizado: {0}" -f $positionFile)
                Write-Host ("Posicao inicial gravada: X={0} Y={1} W={2} H={3}" -f $rect.x, $rect.y, $rect.width, $rect.height)
                Write-Host "A partir de agora, novas versoes devem abrir nessa mesma posicao."
            }
        }
    }
    Start-Sleep -Seconds $PollSeconds
}

if ($lastRect) {
    Save-WindowRect $lastRect
    Write-Host ("Posicao salva: X={0} Y={1} W={2} H={3}" -f $lastRect.x, $lastRect.y, $lastRect.width, $lastRect.height)
}
