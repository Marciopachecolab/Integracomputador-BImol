# 🧹 Script de Limpeza Automática - IntegRAGal
# PRIORIDADE ALTA - Arquivos Temporários e Debug
# 
# ATENÇÃO: Este script irá EXCLUIR arquivos permanentemente
# Certifique-se de ter um backup antes de executar

param(
    [switch]$DryRun,  # Simula sem excluir
    [switch]$Force    # Não pede confirmação
)

$ErrorActionPreference = "Continue"
$RootPath = (Resolve-Path "$PSScriptRoot/..").Path

# Cores para output
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Danger { Write-Host $args -ForegroundColor Red }

Write-Host "`nLIMPEZA AUTOMATICA - PRIORIDADE ALTA" -ForegroundColor Magenta
Write-Host ("=" * 60) -ForegroundColor Magenta

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

# ========================================
# CATEGORIA 1: Scripts Temporarios (Raiz)
# ========================================
Write-Host "`nCategoria 1: Scripts Temporarios..." -ForegroundColor Yellow

$TempScripts = @(
    "_tmp_patch.py",
    "tmp_fix.py",
    "tmp_plate_preview.py",
    "tmp_df_norm_excerpt.csv",
    "add_dtype_fix.py",
    "fix_encoding_safe.py"
)

foreach ($file in $TempScripts) {
    $path = Join-Path $RootPath $file
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

# ========================================
# CATEGORIA 2: Scripts de Analise (Raiz)
# ========================================
Write-Host "`nCategoria 2: Scripts de Analise Pontual..." -ForegroundColor Yellow

$AnaliseScripts = @(
    "analise_arquivos_imagem.py",
    "analise_cq_especifica.py",
    "analise_ct_parenteses.py",
    "analise_linhas.py",
    "analise_planilha_biomanguinhos.py",
    "analise_profunda_xls.py",
    "analise_subdiretorio_teste.py",
    "analise_xls_detalhada.py",
    "busca_cq_exaustiva.py",
    "analise_teste_subdir_resumo.txt"
)

foreach ($file in $AnaliseScripts) {
    $path = Join-Path $RootPath $file
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

# ========================================
# CATEGORIA 3: Scripts de Debug (Raiz)
# ========================================
Write-Host "`nCategoria 3: Scripts de Debug..." -ForegroundColor Yellow

$DebugScripts = @(
    "debug_cfx_detalhes.py",
    "debug_cfx_target.py",
    "debug_extractors.py",
    "debug_registry.py",
    "debug_registry2.py",
    "debug_slug.py",
    "df_debug.py",
    "df_report_full.py"
)

foreach ($file in $DebugScripts) {
    $path = Join-Path $RootPath $file
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

# ========================================
# CATEGORIA 4: Scripts de Verificacao (Raiz)
# ========================================
Write-Host "`nCategoria 4: Scripts de Verificacao..." -ForegroundColor Yellow

$VerificacaoScripts = @(
    "check_unicode.py",
    "check_utf8_simple.py",
    "verificacao_encoding_final.py",
    "verificacao_final_codificacao.py",
    "verifica_arquivo_principal.py",
    "auditoria_codificacao.py"
)

foreach ($file in $VerificacaoScripts) {
    $path = Join-Path $RootPath $file
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

# ========================================
# CATEGORIA 5: Testes na Raiz
# ========================================
Write-Host "`nCategoria 5: Arquivos de Teste na Raiz..." -ForegroundColor Yellow

$TestFiles = Get-ChildItem -Path $RootPath -File | Where-Object { 
    $_.Name -match "^test_.*\.py$" -or 
    $_.Name -match "^teste_.*\.py$" -or
    $_.Name -in @("mapavazio_teste.py", "mapa_vazio_teste_simplex.py", "validate_registry_interface.py")
}

foreach ($file in $TestFiles) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    Write-Info "  X $($file.Name) ($sizeKB KB)"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# ========================================
# CATEGORIA 6: Imagens Temporarias
# ========================================
Write-Host "`nCategoria 6: Imagens Temporarias..." -ForegroundColor Yellow

$ImageFiles = Get-ChildItem -Path $RootPath -File -Filter "Gemini_Generated_Image_*.png"

foreach ($file in $ImageFiles) {
    $size = $file.Length
    $TotalSize += $size
    $TotalFiles++
    
    $sizeKB = [math]::Round($size / 1KB, 2)
    Write-Info "  X $($file.Name) ($sizeKB KB)"
    
    if (-not $DryRun) {
        Remove-Item $file.FullName -Force
    }
}

# ========================================
# CATEGORIA 7: Cache e Coverage
# ========================================
Write-Host "`nCategoria 7: Arquivos de Cache..." -ForegroundColor Yellow

$CacheFiles = @(".coverage")
foreach ($file in $CacheFiles) {
    $path = Join-Path $RootPath $file
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

# Diretorio .ruff_cache
$ruffCache = Join-Path $RootPath ".ruff_cache"
if (Test-Path $ruffCache) {
    $cacheSize = (Get-ChildItem -Path $ruffCache -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $cacheCount = (Get-ChildItem -Path $ruffCache -Recurse -File).Count
    
    $TotalSize += $cacheSize
    $TotalFiles += $cacheCount
    
    $sizeKB = [math]::Round($cacheSize / 1KB, 2)
    Write-Info "  X .ruff_cache/ ($cacheCount arquivos, $sizeKB KB)"
    
    if (-not $DryRun) {
        Remove-Item $ruffCache -Recurse -Force
    }
}

# ========================================
# RESUMO FINAL
# ========================================
Write-Host "`n" + ("=" * 60) -ForegroundColor Magenta
Write-Host "RESUMO DA LIMPEZA" -ForegroundColor Magenta
Write-Host ("=" * 60) -ForegroundColor Magenta

$sizeMB = [math]::Round($TotalSize / 1MB, 2)
Write-Info "\n  Total de arquivos: $TotalFiles"
Write-Info "  Espaco recuperado: $sizeMB MB"

if ($DryRun) {
    Write-Warning "`nMODO SIMULACAO - Nenhum arquivo foi excluido"
    Write-Info "`n  Para executar a limpeza de verdade, execute:"
    Write-Host "  .\limpeza_prioridade_alta.ps1" -ForegroundColor Cyan
}
else {
    Write-Success "`nLimpeza concluida com sucesso!"
}

Write-Host ""
