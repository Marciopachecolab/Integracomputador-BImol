# 🗂️ Script de Organização de Documentação
# Move documentação de fases para estrutura organizada
#
# ATENÇÃO: Este script irá MOVER arquivos

param(
    [switch]$DryRun,  # Simula sem mover
    [switch]$Force    # Não pede confirmação
)

$ErrorActionPreference = "Continue"
$RootPath = (Resolve-Path "$PSScriptRoot/..").Path
$DocsPath = Join-Path $RootPath "docs"
$LegacyPath = Join-Path $DocsPath "legacy"

function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Danger { Write-Host $args -ForegroundColor Red }

Write-Host "`n🗂️  ORGANIZAÇÃO DE DOCUMENTAÇÃO" -ForegroundColor Magenta
Write-Host "=" * 60 -ForegroundColor Magenta

if ($DryRun) {
    Write-Warning "`n⚠️  MODO SIMULAÇÃO (DRY RUN) - Nenhum arquivo será movido"
}
else {
    Write-Danger "`n⚠️  ATENÇÃO: Este script irá MOVER arquivos!"
    if (-not $Force) {
        $confirm = Read-Host "`nDeseja continuar? (S/N)"
        if ($confirm -ne "S" -and $confirm -ne "s") {
            Write-Info "Operação cancelada pelo usuário."
            exit
        }
    }
}

# Criar estrutura de diretórios
$Directories = @(
    (Join-Path $LegacyPath "historico_fases"),
    (Join-Path $LegacyPath "relatorios_desenvolvimento"),
    (Join-Path $LegacyPath "planejamento"),
    (Join-Path $LegacyPath "scripts_migracao")
)

if (-not $DryRun) {
    foreach ($dir in $Directories) {
        if (-not (Test-Path $dir)) {
            New-Item -Path $dir -ItemType Directory -Force | Out-Null
            Write-Success "  ✅ Criado: $($dir.Replace($RootPath, ''))"
        }
    }
}

$TotalFiles = 0

# ========================================
# CATEGORIA 1: Documentação de Fases
# ========================================
Write-Host "`n📂 Movendo documentação de fases..." -ForegroundColor Yellow

$DestFases = Join-Path $LegacyPath "historico_fases"

$FaseDocs = @(
    "ETAPA1_PREPARACAO.md",
    "ETAPA2_COMPLETO.md",
    "ETAPA4_COMPLETO.md",
    "ETAPA4_PLANEJAMENTO.md",
    "ETAPA5_COMPLETO.md",
    "FASE1_3_EXTRACTORS_CONCLUIDA.md",
    "FASE4_DASHBOARD.md",
    "FASE5_ANALISE_FINAL.md",
    "FASE5_CONCLUSAO_FINAL.md",
    "FASE6_CONCLUSAO_COMPLETA.md",
    "FASE6_MIGRATION_LOG.txt",
    "FASE6_RESUMO_VISUAL.txt",
    "FASE6_VALIDATION_REPORT.txt",
    "FASE7_CONCLUSAO_COMPLETA.md",
    "FASE7_RESUMO_TESTES_E2E.md"
)

foreach ($file in $FaseDocs) {
    $source = Join-Path $RootPath $file
    if (Test-Path $source) {
        $dest = Join-Path $DestFases $file
        $TotalFiles++
        
        Write-Info "  📄 $file → legacy/historico_fases/"
        
        if (-not $DryRun) {
            Move-Item -Path $source -Destination $dest -Force
        }
    }
}

# ========================================
# CATEGORIA 2: Relatórios de Desenvolvimento
# ========================================
Write-Host "`n📂 Movendo relatórios de desenvolvimento..." -ForegroundColor Yellow

$DestRelatorios = Join-Path $LegacyPath "relatorios_desenvolvimento"

$RelatorioDocs = @(
    "ANALISE_CONSOLIDADA_FASES1-5.md",
    "ANALISE_ESTADO_ATUAL_VS_FLUXO_REVISADO.md",
    "ANALISE_MECANISMO_INCLUSAO_EXAMES.md",
    "ANALISE_USO_CONCOMITANTE_REDE_LOCAL.md",
    "AUDITORIA_CODIFICACAO.txt",
    "AUDITORIA_CODIFICACAO_FINAL.md",
    "AUDITORIA_RESUMO_VISUAL.txt",
    "CERTIFICADO_UTF8_FINAL.md",
    "COMPARACAO_ANTES_DEPOIS.md",
    "CONCLUSAO_VISUAL.txt",
    "CORRECOES_EQUIPMENT_DETECTOR.md",
    "RELATORIO_FASE4_INTEGRACAO.md",
    "RELATORIO_FASE5_ANALISE.md",
    "RELATORIO_FASES1-3_ANALISE.md",
    "RESUMO_ALTERACOES_CT.md",
    "RESUMO_FASE5.md",
    "RESUMO_SOLUCAO_CONCORRENCIA.md",
    "STATUS_CODIFICACAO_COMPLETO.md",
    "STATUS_PROGRESSO_ATUAL.md",
    "STATUS_PROJETO_FINAL.md",
    "SUMARIO_FINAL_FASE4.md",
    "relatorio_analise.txt",
    "RESULTADO_IMPLEMENTACAO.txt",
    "ARQUITETURA_CONCORRENCIA_VISUAL.md",
    "MAPA_VISUAL_FASE4.md",
    "MAPA_VISUAL_FASE5.md",
    "MATRIZ_VERIFICACAO_FASE4.md",
    "CORRECAO_CODIFICACAO.log"
)

foreach ($file in $RelatorioDocs) {
    $source = Join-Path $RootPath $file
    if (Test-Path $source) {
        $dest = Join-Path $DestRelatorios $file
        $TotalFiles++
        
        Write-Info "  📄 $file → legacy/relatorios_desenvolvimento/"
        
        if (-not $DryRun) {
            Move-Item -Path $source -Destination $dest -Force
        }
    }
}

# ========================================
# CATEGORIA 3: Planos de Implementação
# ========================================
Write-Host "`n📂 Movendo planos de implementação..." -ForegroundColor Yellow

$DestPlanos = Join-Path $LegacyPath "planejamento"

$PlanoDocs = @(
    "PLANO_FASE5_ETAPAS.md",
    "PLANO_FASE5_RESUMO.md",
    "PLANO_FASE6_MIGRACAO.md",
    "PLANO_FASE7_TESTES_E2E.md",
    "PLANO_IMPLANTACAO_5_FASES.md",
    "PLANO_IMPLANTACAO_FASE1.md",
    "RECOMENDACOES_TECNICAS_FASE4.md",
    "IMPLEMENTACAO_CONCLUIDA.md",
    "EXEMPLO_INTEGRACAO_CSV_LOCK.md",
    "EXPLICACAO_SISTEMA_HISTORICO.md",
    "FLUXO_DETALHADO_HISTORICO.md",
    "GUIA_IMPLEMENTACAO_RAPIDA.md",
    "GUIA_RAPIDO_IMPLEMENTACAO_HISTORICO.md",
    "ALTERNATIVAS_CSV_COMPARACAO.md"
)

foreach ($file in $PlanoDocs) {
    $source = Join-Path $RootPath $file
    if (Test-Path $source) {
        $dest = Join-Path $DestPlanos $file
        $TotalFiles++
        
        Write-Info "  📄 $file → legacy/planejamento/"
        
        if (-not $DryRun) {
            Move-Item -Path $source -Destination $dest -Force
        }
    }
}

# ========================================
# CATEGORIA 4: Scripts de Migração
# ========================================
Write-Host "`n📂 Movendo scripts de migração..." -ForegroundColor Yellow

$DestMigracao = Join-Path $LegacyPath "scripts_migracao"

$MigracaoScripts = @(
    "FASE6_migrate_exams_to_json.py",
    "FASE6_validate_registry.py",
    "GUIA_INTEGRACAO_REPORTER.py"
)

foreach ($file in $MigracaoScripts) {
    $source = Join-Path $RootPath $file
    if (Test-Path $source) {
        $dest = Join-Path $DestMigracao $file
        $TotalFiles++
        
        Write-Info "  📄 $file → legacy/scripts_migracao/"
        
        if (-not $DryRun) {
            Move-Item -Path $source -Destination $dest -Force
        }
    }
}

# ========================================
# CATEGORIA 5: Índices e Guias
# ========================================
Write-Host "`n📂 Movendo índices e guias antigos..." -ForegroundColor Yellow

$IndicesDocs = @(
    "INDICE_DOCUMENTACAO_COMPLETO.md",
    "INDICE_DOCUMENTACAO_FASE4.md"
)

foreach ($file in $IndicesDocs) {
    $source = Join-Path $RootPath $file
    if (Test-Path $source) {
        $dest = Join-Path $DestPlanos $file
        $TotalFiles++
        
        Write-Info "  📄 $file → legacy/planejamento/"
        
        if (-not $DryRun) {
            Move-Item -Path $source -Destination $dest -Force
        }
    }
}

# ========================================
# RESUMO FINAL
# ========================================
Write-Host "`n" + ("=" * 60) -ForegroundColor Magenta
Write-Host "📊 RESUMO DA ORGANIZAÇÃO" -ForegroundColor Magenta
Write-Host ("=" * 60) -ForegroundColor Magenta

Write-Info "`n  Total de arquivos movidos: $TotalFiles"
Write-Info "`n  Estrutura criada:"
Write-Info "    📁 docs/legacy/"
Write-Info "      ├── 📁 historico_fases/"
Write-Info "      ├── 📁 relatorios_desenvolvimento/"
Write-Info "      ├── 📁 planejamento/"
Write-Info "      └── 📁 scripts_migracao/"

if ($DryRun) {
    Write-Warning "`n⚠️  MODO SIMULAÇÃO - Nenhum arquivo foi movido"
    Write-Info "`n  Para executar a organização de verdade, execute:"
    Write-Host "  .\organizar_documentacao.ps1" -ForegroundColor Cyan
}
else {
    Write-Success "`n✅ Organização concluída com sucesso!"
}

Write-Host ""
