# ScalpKit — Windows uchun bitta buyruqli o'rnatuvchi.
#
# PowerShell'da ishga tushirish:
#   irm https://raw.githubusercontent.com/rriskavan-crypto/scalp/claude/m5-scalping-strategy-5z9m9e/bootstrap.ps1 | iex
#
# Nima qiladi: repozitoriyni yuklab oladi, C:\scalp ga chiqaradi va
# install_windows.bat ni ishga tushiradi.

$ErrorActionPreference = "Stop"
$Repo   = "rriskavan-crypto/scalp"
$Branch = "claude/m5-scalping-strategy-5z9m9e"
$Dest   = if ($env:SCALPKIT_DIR) { $env:SCALPKIT_DIR } else { "C:\scalp" }

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "   SCALPKIT - YUKLAB OLISH VA O'RNATISH" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# --- 1. Eski nusxa bormi ---
if (Test-Path $Dest) {
    Write-Host "[!] $Dest allaqachon mavjud." -ForegroundColor Yellow
    $answer = Read-Host "    Ustiga yozilsinmi? (.venv va data saqlanadi)  [h/y]"
    if ($answer -notmatch '^[hHyY]') {
        Write-Host "    Bekor qilindi." -ForegroundColor Yellow
        return
    }
}

# --- 2. Yuklab olish ---
$zipUrl = "https://github.com/$Repo/archive/refs/heads/$Branch.zip"
$tmpZip = Join-Path $env:TEMP "scalpkit_$(Get-Random).zip"
$tmpDir = Join-Path $env:TEMP "scalpkit_x_$(Get-Random)"

Write-Host "[1/4] Yuklab olinmoqda..." -ForegroundColor Green
Write-Host "      $zipUrl"
try {
    # TLS 1.2 - eski Windows uchun
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
} catch {
    Write-Host ""
    Write-Host "   XATO: yuklab olinmadi." -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)"
    Write-Host ""
    Write-Host "   Yechim: brauzerda quyidagini oching va ZIP ni qo'lda chiqaring:"
    Write-Host "   $zipUrl"
    return
}
$sizeMb = [math]::Round((Get-Item $tmpZip).Length / 1MB, 2)
Write-Host "      tayyor ($sizeMb MB)"

# --- 3. Chiqarish ---
Write-Host "[2/4] Arxiv ochilmoqda..." -ForegroundColor Green
Expand-Archive -Path $tmpZip -DestinationPath $tmpDir -Force
# Arxiv ichida bitta papka bo'ladi: scalp-<branch-oxiri>
$inner = Get-ChildItem -Path $tmpDir -Directory | Select-Object -First 1
if (-not $inner) {
    Write-Host "   XATO: arxiv ichi bo'sh." -ForegroundColor Red
    return
}

Write-Host "[3/4] $Dest ga ko'chirilmoqda..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
# .venv va data saqlanadi: faqat fayllar ustiga yoziladi
Copy-Item -Path (Join-Path $inner.FullName "*") -Destination $Dest -Recurse -Force
Remove-Item $tmpZip, $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "      tayyor"

# --- 4. O'rnatuvchi ---
$installer = Join-Path $Dest "install_windows.bat"
if (-not (Test-Path $installer)) {
    Write-Host "   XATO: install_windows.bat topilmadi." -ForegroundColor Red
    return
}

Write-Host "[4/4] O'rnatuvchi ishga tushirilmoqda..." -ForegroundColor Green
Write-Host ""
Push-Location $Dest
try {
    & cmd /c $installer
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Loyiha papkasi: $Dest" -ForegroundColor Cyan
Write-Host "Shu papkada cmd ochib sinab ko'ring:  scalpkit profiles" -ForegroundColor Cyan
Write-Host ""
