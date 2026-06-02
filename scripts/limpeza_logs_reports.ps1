# Script de Limpeza de Logs e Reports Antigos
# Remove logs e reports com mais de 7 dias

param(
    [switch]$DryRun,
    [switch]$Force,
    [int]$DaysToKeep = 7
)

$ErrorActionPreference = "Continue"
$RootPath = (Resolve-Path "$PSScriptRoot/..").Path
$CutoffDate = (Get-Date).AddDays(-$DaysToKeep)

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Danger { Write-Host $args -ForegroundColor Red }

Write-Host "`nLIMPEZA DE LOGS E REPORTS ANTIGOS" -ForegroundColor Magenta
Write-Host ("=" * 60) -ForegroundColor Magenta
Write-Info "`n  Mantendo arquivos dos ultimos $DaysToKeep dias"
Write-Info "  Data de corte: $($CutoffDate.ToString('dd/MM/yyyy HH:mm'))"

if ($DryRun) {
    Write-Warning "`nMODO SIMULACAO (DRY RUN) - Nenhum arquivo sera excluido"
}
else {
    Write-Danger "`nATENCAO: Este script ira EXCLUIR arquivos permanentemente!"
    if (-not $Force) {
        $confirm = Read-Host "`nDeseja continuar? (S/N)"
        if ($confirm -ne "S" -and $confirm -ne "s") {
            Write-Info "Operacao cancelada pelo usuario."
            exit
        }
    }
}

$TotalSize = 0
$TotalFiles = 0

# LOGS TEMPORARIOS
Write-Host "`nLimpando logs temporarios..." -ForegroundColor Yellow

$LogsPath = Join-Path $RootPath "logs"

$LogFilesToDelete = @(
    "tmp_hist.csv",
    "test_historico.csv",
    "resultados_por_amostra.txt"
)

foreach ($file in $LogFilesToDelete) {
    $path = Join-Path $LogsPath $file
    if (Test-Path $path) {
        $item = Get-Item $path
        $size = $item.Length
        $TotalSize += $size
        $TotalFiles++
        
        $sizeKB = [math]::Round($size / 1KB, 2)
        Write-Info "  X $file ($sizeKB KB)"
        
        if (-not $DryRun) {
            Remove-Item $path -Force
        }
    }
}

# Relatorios de envio antigos
$relatorioEnvio = Get-ChildItem -Path $LogsPath -File -Filter "relatorio_envio_*.txt" | 
Where-Object { $_.LastWriteTime -lt $CutoffDate }

foreach ($file in $relatorioEnvio) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    $dateStr = $file.LastWriteTime.ToString('dd/MM/yyyy')
    Write-Info "  X $($file.Name) ($sizeKB KB) - $dateStr"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# Diretorio dataframe_reports completo
$dfReportsPath = Join-Path $LogsPath "dataframe_reports"
if (Test-Path $dfReportsPath) {
    $dfFiles = Get-ChildItem -Path $dfReportsPath -File
    
    foreach ($file in $dfFiles) {
        $size = $file.Length
        $TotalSize += $size
        $TotalFiles++
        
        $sizeKB = [math]::Round($size / 1KB, 2)
        Write-Info "  X dataframe_reports/$($file.Name) ($sizeKB KB)"
        
        if (-not $DryRun) {
            Remove-Item $file.FullName -Force
        }
    }
}

# REPORTS DE TESTE GAL
Write-Host "`nLimpando reports de teste GAL antigos..." -ForegroundColor Yellow

$ReportsPath = Join-Path $RootPath "reports"

# Reports GAL antigos
$galReports = Get-ChildItem -Path $ReportsPath -File -Filter "gal_*.csv" | 
Where-Object { 
    $_.Name -ne "gal_last_exame.csv" -and 
    $_.LastWriteTime -lt $CutoffDate 
}

foreach ($file in $galReports) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    $dateStr = $file.LastWriteTime.ToString('dd/MM/yyyy')
    Write-Info "  X $($file.Name) ($sizeKB KB) - $dateStr"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# Planilhas de placa antigas
$placaReports = Get-ChildItem -Path $ReportsPath -File -Filter "placa_*.xlsx" | 
Where-Object { $_.LastWriteTime -lt $CutoffDate }

foreach ($file in $placaReports) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    $dateStr = $file.LastWriteTime.ToString('dd/MM/yyyy')
    Write-Info "  X $($file.Name) ($sizeKB KB) - $dateStr"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# Imagens de placa antigas
$placaImages = Get-ChildItem -Path $ReportsPath -File -Filter "placa_*.png" | 
Where-Object { $_.LastWriteTime -lt $CutoffDate }

foreach ($file in $placaImages) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    $dateStr = $file.LastWriteTime.ToString('dd/MM/yyyy')
    Write-Info "  X $($file.Name) ($sizeKB KB) - $dateStr"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# Historicos antigos (exceto o principal)
$historicoReports = Get-ChildItem -Path $ReportsPath -File -Filter "historico_analises_*.csv" | 
Where-Object { $_.LastWriteTime -lt $CutoffDate }

foreach ($file in $historicoReports) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    $dateStr = $file.LastWriteTime.ToString('dd/MM/yyyy')
    Write-Info "  X $($file.Name) ($sizeKB KB) - $dateStr"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# RESUMO FINAL
Write-Host "`n" + ("=" * 60) -ForegroundColor Magenta
Write-Host "RESUMO DA LIMPEZA" -ForegroundColor Magenta
Write-Host ("=" * 60) -ForegroundColor Magenta

$sizeMB = [math]::Round($TotalSize / 1MB, 2)
Write-Info "`n  Total de arquivos: $TotalFiles"
Write-Info "  Espaco recuperado: $sizeMB MB"

if ($DryRun) {
    Write-Warning "`nMODO SIMULACAO - Nenhum arquivo foi excluido"
    Write-Info "`n  Para executar a limpeza de verdade, execute:"
    Write-Host "  .\limpeza_logs_reports.ps1" -ForegroundColor Cyan
    Write-Info "`n  Para alterar o periodo de retencao (padrao 7 dias):"
    Write-Host "  .\limpeza_logs_reports.ps1 -DaysToKeep 30" -ForegroundColor Cyan
}
else {
    Write-Success "`nLimpeza concluida com sucesso!"
}

Write-Host ""
