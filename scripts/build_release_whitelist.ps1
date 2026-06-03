<#
.SYNOPSIS
    Script de materializacao por whitelist do pacote de release IntegRAGal.

.DESCRIPTION
    Constroi a estrutura release/ copiando somente os itens explicitamente
    permitidos pelo manifest HIG-008 (docs/specs/higienizacao_implantacao.md §6).

    Por padrao opera em modo simulacao (WhatIf). Para materializar de fato,
    informe -Execute apos revisao humana em rodada propria autorizada.

    Este script NAO deve ser executado automaticamente por agentes de IA.
    Cada execucao real exige autorizacao humana explicita e rodada propria.

.PARAMETER SourceRoot
    Raiz do repositorio IntegRAGal. Padrao: diretorio atual de execucao.

.PARAMETER ReleaseRoot
    Destino do pacote de release. Padrao: ./release (relativo a SourceRoot).

.PARAMETER Execute
    Quando presente, realiza a copia real. Sem este parametro o script
    executa em modo simulacao (dry-run / WhatIf) e nao cria nenhum arquivo.

.PARAMETER Force
    Permite sobrescrever release/ existente. Exige confirmacao interativa
    adicional antes de prosseguir. Nao usar em automacao sem revisao.

.PARAMETER SkipValidation
    Pula a validacao pos-copia. Nao recomendado para uso normal.

.EXAMPLE
    # Modo simulacao (padrao seguro) - nao cria nada:
    .\build_release_whitelist.ps1

    # Modo simulacao com caminhos explicitos:
    .\build_release_whitelist.ps1 -SourceRoot "C:\Projetos\IntegRAGal" -ReleaseRoot "C:\Projetos\release"

    # Materializacao real - SOMENTE em rodada propria autorizada:
    .\build_release_whitelist.ps1 -Execute

    # Materializacao forcando sobrescrita de release/ existente:
    .\build_release_whitelist.ps1 -Execute -Force

.NOTES
    Criado em: 2026-05-17 como conclusao de REL-004.
    Manifest de referencia: docs/specs/higienizacao_implantacao.md §6.1-§6.6.
    Checklist pos-instalacao: docs/checklist_pos_instalacao.md
    Procedimento smoke-test: docs/procedimento_smoke_test_release.md
    Restricoes conhecidas: REL-001 (assets/icon.ico ausente - ressalva nao bloqueante).

    ATENCAO: execute somente em rodada propria autorizada, com baseline/backup
    disponivel e apos revisao humana deste script.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$SourceRoot  = (Get-Location).Path,
    [string]$ReleaseRoot = "",
    [switch]$Execute,
    [switch]$Force,
    [switch]$SkipValidation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Configuracao interna
# ---------------------------------------------------------------------------
$SCRIPT_VERSION   = "1.0"
$SCRIPT_DATE      = "2026-05-17"
$PROJECT_SENTINEL = "CLAUDE.md"   # arquivo que identifica a raiz do projeto

# ---------------------------------------------------------------------------
# Helpers de saida
# ---------------------------------------------------------------------------
function Write-Header {
    param([string]$Text)
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "--- $Text ---" -ForegroundColor Yellow
}

function Write-OK   { param([string]$Text); Write-Host "  [OK]  $Text" -ForegroundColor Green }
function Write-WARN { param([string]$Text); Write-Host "  [WARN] $Text" -ForegroundColor Yellow }
function Write-INFO { param([string]$Text); Write-Host "  [INFO] $Text" -ForegroundColor Cyan }
function Write-FAIL { param([string]$Text); Write-Host "  [FAIL] $Text" -ForegroundColor Red }
function Write-SIM  { param([string]$Text); Write-Host "  [SIM]  $Text" -ForegroundColor Magenta }

# ---------------------------------------------------------------------------
# Modo de operacao
# ---------------------------------------------------------------------------
$IsDryRun = -not $Execute.IsPresent

Write-Header "IntegRAGal - Script de Materializacao por Whitelist v$SCRIPT_VERSION ($SCRIPT_DATE)"

if ($IsDryRun) {
    Write-Host ""
    Write-Host "  MODO SIMULACAO (DRY-RUN)" -ForegroundColor Magenta
    Write-Host "  Nenhum arquivo sera criado, copiado ou modificado." -ForegroundColor Magenta
    Write-Host "  Para materializar de verdade, use: .\build_release_whitelist.ps1 -Execute" -ForegroundColor Magenta
} else {
    Write-Host ""
    Write-Host "  MODO EXECUCAO REAL" -ForegroundColor Red
    Write-Host "  Arquivos SERAO criados em: $ReleaseRoot" -ForegroundColor Red
}

# ---------------------------------------------------------------------------
# Resolucao de caminhos
# ---------------------------------------------------------------------------
$SourceRoot = (Resolve-Path $SourceRoot -ErrorAction Stop).Path

if ([string]::IsNullOrWhiteSpace($ReleaseRoot)) {
    $ReleaseRoot = Join-Path $SourceRoot "release"
} else {
    $ReleaseRoot = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($ReleaseRoot)
}

# ---------------------------------------------------------------------------
# Validacao 1: SourceRoot existe
# ---------------------------------------------------------------------------
Write-Section "Validacao de ambiente"

if (-not (Test-Path $SourceRoot -PathType Container)) {
    Write-FAIL "SourceRoot nao existe: $SourceRoot"
    exit 1
}
Write-OK "SourceRoot localizado: $SourceRoot"

# ---------------------------------------------------------------------------
# Validacao 2: sentinela de raiz do projeto
# ---------------------------------------------------------------------------
$SentinelPath = Join-Path $SourceRoot $PROJECT_SENTINEL
if (-not (Test-Path $SentinelPath)) {
    Write-FAIL "Arquivo sentinela '$PROJECT_SENTINEL' nao encontrado em $SourceRoot."
    Write-FAIL "Verifique se SourceRoot aponta para a raiz correta do projeto IntegRAGal."
    exit 1
}
Write-OK "Sentinela do projeto encontrado: $PROJECT_SENTINEL"

# ---------------------------------------------------------------------------
# Validacao 3: arquivos RUNTIME OBRIGATORIOS presentes na fonte
# ---------------------------------------------------------------------------
$RequiredSourceFiles = @(
    "main.py",
    "models.py",
    "requirements.txt",
    "README.md",
    "config.json"
)
foreach ($f in $RequiredSourceFiles) {
    $fp = Join-Path $SourceRoot $f
    if (-not (Test-Path $fp)) {
        Write-FAIL "Arquivo obrigatorio ausente na fonte: $f"
        exit 1
    }
    Write-OK "Fonte encontrada: $f"
}

$RequiredSourceDirs = @(
    "domain", "application", "services", "ui", "autenticacao",
    "exportacao", "browser", "utils", "db", "config"
)
foreach ($d in $RequiredSourceDirs) {
    $dp = Join-Path $SourceRoot $d
    if (-not (Test-Path $dp -PathType Container)) {
        Write-FAIL "Diretorio obrigatorio ausente na fonte: $d/"
        exit 1
    }
    Write-OK "Fonte encontrada: $d/"
}

Write-OK "Todos os itens obrigatorios localizados na fonte."

# ---------------------------------------------------------------------------
# Validacao 4: release/ nao deve existir (sem Force)
# ---------------------------------------------------------------------------
if (Test-Path $ReleaseRoot) {
    if ($Force.IsPresent) {
        Write-WARN "release/ ja existe: $ReleaseRoot"
        Write-WARN "Flag -Force detectado. Confirmacao obrigatoria para prosseguir."
        if (-not $IsDryRun) {
            $confirm = Read-Host "  ATENCAO: release/ sera removida e recriada. Digite CONFIRMAR para continuar"
            if ($confirm -ne "CONFIRMAR") {
                Write-FAIL "Operacao cancelada pelo usuario."
                exit 1
            }
            Write-WARN "Removendo release/ existente..."
            Remove-Item -Recurse -Force $ReleaseRoot
            Write-OK "release/ removida."
        } else {
            Write-SIM "  [SIM] release/ existente seria removida antes da recriacao (requer -Execute)."
        }
    } else {
        Write-FAIL "release/ ja existe: $ReleaseRoot"
        Write-FAIL "Para sobrescrever, use -Force com confirmacao explicita."
        Write-FAIL "Para apenas simular, omita -Execute."
        exit 1
    }
}

# ---------------------------------------------------------------------------
# Funcao auxiliar de copia controlada
# ---------------------------------------------------------------------------
function Invoke-SafeCopy {
    param(
        [string]$Source,
        [string]$Destination,
        [switch]$IsDir
    )
    if ($IsDryRun) {
        Write-SIM "  Copiaria: $Source -> $Destination"
    } else {
        if ($IsDir) {
            $null = New-Item -ItemType Directory -Path $Destination -Force
            Copy-Item -Path (Join-Path $Source "*") -Destination $Destination -Recurse -Force
        } else {
            $parentDir = Split-Path $Destination -Parent
            if (-not (Test-Path $parentDir)) {
                $null = New-Item -ItemType Directory -Path $parentDir -Force
            }
            Copy-Item -Path $Source -Destination $Destination -Force
        }
    }
}

function Invoke-MkDir {
    param([string]$Path, [string]$Label)
    if ($IsDryRun) {
        Write-SIM "  Criaria diretorio: $Path  [$Label]"
    } else {
        $null = New-Item -ItemType Directory -Path $Path -Force
        Write-OK "Diretorio criado: $Label"
    }
}

function Invoke-CopyBancoSeed {
    param(
        [string]$DestinationBancoDir,
        [string]$Label
    )

    Invoke-MkDir -Path $DestinationBancoDir -Label $Label

    foreach ($relative in $BancoSeedFiles) {
        $src = Join-Path (Join-Path $SourceRoot "banco") $relative
        $dst = Join-Path $DestinationBancoDir $relative
        if (-not (Test-Path $src -PathType Leaf)) {
            Write-FAIL "Seed obrigatorio ausente em banco/: $relative"
            exit 1
        }
        Invoke-SafeCopy -Source $src -Destination $dst
        Write-INFO "  $Label/$relative"
    }
}

# ---------------------------------------------------------------------------
# Funcao de remocao pos-copia de itens proibidos dentro de release/app/
# ---------------------------------------------------------------------------
function Remove-ProhibitedItems {
    param([string]$AppDir)

    # Lista de padroes a eliminar de dentro de release/app/ apos a copia recursiva
    $prohibited = @(
        "__pycache__",
        "debug",
        ".pytest_cache",
        ".mypy_cache",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        "*.db",
        "*.sqlite",
        "*.sqlite3"
    )

    foreach ($pattern in $prohibited) {
        $found = Get-ChildItem -Path $AppDir -Filter $pattern -Recurse -Force -ErrorAction SilentlyContinue
        foreach ($item in $found) {
            if ($IsDryRun) {
                Write-SIM "  Removeria (proibido em app/): $($item.FullName)"
            } else {
                Remove-Item -Recurse -Force $item.FullName -ErrorAction SilentlyContinue
                Write-WARN "Removido (proibido em app/): $($item.Name)"
            }
        }
    }
}

# ---------------------------------------------------------------------------
# Definicao da whitelist
# ---------------------------------------------------------------------------
Write-Section "Whitelist de materializacao (manifest HIG-008)"

$AppWhitelistFiles = @("main.py", "models.py", "requirements.txt", "config.json")
$AppWhitelistDirs  = @(
    "domain", "application", "services", "ui", "autenticacao",
    "exportacao", "browser", "utils", "db", "config"
)

$BancoSeedFiles = @(
    "credenciais.csv",
    "usuarios.csv",
    "configuracoes_sistema.csv",
    "equipamentos.csv",
    "equipamentos_metadata.csv",
    "exames_config.csv",
    "exames_metadata.csv",
    "placas.csv",
    "placas_metadata.csv",
    "regras.csv",
    "regras_analise_metadata.csv",
    "sas.csv",
    "sessoes.csv",
    "profiles\equipment_profiles.json",
    "protocols\analysis_protocols.json",
    "protocols\analysis_rules.json"
)

Write-INFO "release/app/ - arquivos: $($AppWhitelistFiles -join ', ')"
Write-INFO "release/app/ - diretorios: $($AppWhitelistDirs -join ', ')"
Write-INFO "release/config_template/ - config.json + config/contracts/"
Write-INFO "release/docs_operacionais/ - README.md, checklist, procedimento smoke-test"
Write-INFO "release/assets/ - diretorio vazio (icon.ico ausente - ressalva REL-001)"
Write-INFO "release/scripts_autorizados/ - diretorio vazio (aguarda auditoria H4)"
Write-INFO "release/runtime_empty/ - logs/, reports/, relatorios/, data/state/"
Write-INFO "release/runtime_private/banco/ - seed privado controlado de banco/ para migracao"
Write-INFO "release/app/banco/ - seed runtime esperado pelo BASE_DIR da aplicacao"
Write-WARN "OVERRIDE DE MIGRACAO: banco/credenciais.csv sera incluido por instrucao humana explicita."
Write-WARN "NOTA REL-001: assets/icon.ico ausente fisicamente; aceito formalmente como ressalva nao bloqueante para piloto."

# ---------------------------------------------------------------------------
# FASE 1: release/app/
# ---------------------------------------------------------------------------
Write-Section "FASE 1: release/app/"

$AppDest = Join-Path $ReleaseRoot "app"
Invoke-MkDir -Path $AppDest -Label "release/app/"

foreach ($f in $AppWhitelistFiles) {
    $src = Join-Path $SourceRoot $f
    $dst = Join-Path $AppDest $f
    Invoke-SafeCopy -Source $src -Destination $dst
    Write-INFO "  $f"
}

foreach ($d in $AppWhitelistDirs) {
    $src = Join-Path $SourceRoot $d
    $dst = Join-Path $AppDest $d
    Invoke-MkDir -Path $dst -Label "release/app/$d/"
    Invoke-SafeCopy -Source $src -Destination $dst -IsDir
    Write-INFO "  $d/"
}

# banco/ privado minimo esperado pelo runtime quando a aplicacao roda em release/app/
$AppBancoDest = Join-Path $AppDest "banco"
Invoke-CopyBancoSeed -DestinationBancoDir $AppBancoDest -Label "release/app/banco"

# Remover artefatos proibidos que possam ter sido copiados recursivamente
if (-not $IsDryRun) {
    Write-Section "Limpeza pos-copia: removendo artefatos proibidos de release/app/"
    Remove-ProhibitedItems -AppDir $AppDest
} else {
    Write-Section "Limpeza pos-copia (simulacao)"
    Remove-ProhibitedItems -AppDir (Join-Path $SourceRoot ".")   # apenas simula listagem
}

# ---------------------------------------------------------------------------
# FASE 2: release/config_template/
# ---------------------------------------------------------------------------
Write-Section "FASE 2: release/config_template/"

$ConfigTemplateDest = Join-Path $ReleaseRoot "config_template"
Invoke-MkDir -Path $ConfigTemplateDest -Label "release/config_template/"

# config.json (template/local runtime - campos de producao DEVEM estar vazios)
$srcConfigJson = Join-Path $SourceRoot "config.json"
$dstConfigJson = Join-Path $ConfigTemplateDest "config.json"
Invoke-SafeCopy -Source $srcConfigJson -Destination $dstConfigJson
Write-INFO "  config.json (template/local runtime)"
Write-WARN "  ATENCAO: config.json deve ter shared_storage.root, data_root e allowed_roots VAZIOS no release."
Write-WARN "  Verificar manualmente antes de distribuir."

# config/contracts/ (contratos canonicos de equipamentos)
$srcContracts = Join-Path $SourceRoot "config\contracts"
$dstContracts = Join-Path $ConfigTemplateDest "config\contracts"
if (Test-Path $srcContracts -PathType Container) {
    Invoke-MkDir -Path $dstContracts -Label "release/config_template/config/contracts/"
    Invoke-SafeCopy -Source $srcContracts -Destination $dstContracts -IsDir
    Write-INFO "  config/contracts/"
} else {
    Write-WARN "  config/contracts/ nao encontrado na fonte - verificar antes de distribuir."
}

# ---------------------------------------------------------------------------
# FASE 3: release/docs_operacionais/
# ---------------------------------------------------------------------------
Write-Section "FASE 3: release/docs_operacionais/"

$DocsDest = Join-Path $ReleaseRoot "docs_operacionais"
Invoke-MkDir -Path $DocsDest -Label "release/docs_operacionais/"

# README.md
$srcReadme = Join-Path $SourceRoot "README.md"
$dstReadme = Join-Path $DocsDest "README.md"
Invoke-SafeCopy -Source $srcReadme -Destination $dstReadme
Write-INFO "  README.md"

# checklist pos-instalacao
$srcChecklist = Join-Path $SourceRoot "docs\checklist_pos_instalacao.md"
$dstChecklist = Join-Path $DocsDest "checklist_pos_instalacao.md"
if (Test-Path $srcChecklist) {
    Invoke-SafeCopy -Source $srcChecklist -Destination $dstChecklist
    Write-INFO "  docs/checklist_pos_instalacao.md"
} else {
    Write-WARN "  docs/checklist_pos_instalacao.md nao encontrado - verificar."
}

# procedimento smoke-test
$srcSmokeTest = Join-Path $SourceRoot "docs\procedimento_smoke_test_release.md"
$dstSmokeTest = Join-Path $DocsDest "procedimento_smoke_test_release.md"
if (Test-Path $srcSmokeTest) {
    Invoke-SafeCopy -Source $srcSmokeTest -Destination $dstSmokeTest
    Write-INFO "  docs/procedimento_smoke_test_release.md"
} else {
    Write-WARN "  docs/procedimento_smoke_test_release.md nao encontrado - verificar."
}

# ---------------------------------------------------------------------------
# FASE 4: release/assets/ (diretorio vazio - ressalva REL-001)
# ---------------------------------------------------------------------------
Write-Section "FASE 4: release/assets/"

$AssetsDest = Join-Path $ReleaseRoot "assets"
Invoke-MkDir -Path $AssetsDest -Label "release/assets/"
Write-WARN "  assets/icon.ico NAO sera criado. Ausencia aceita formalmente (REL-001)."
Write-WARN "  Providenciar icone oficial antes de versao final/distribuicao ampla."

# ---------------------------------------------------------------------------
# FASE 5: release/scripts_autorizados/ (vazio - aguarda auditoria H4)
# ---------------------------------------------------------------------------
Write-Section "FASE 5: release/scripts_autorizados/"

$ScriptsDest = Join-Path $ReleaseRoot "scripts_autorizados"
Invoke-MkDir -Path $ScriptsDest -Label "release/scripts_autorizados/"
Write-WARN "  Nenhum script copiado. Aguarda auditoria H4 antes de incluir scripts administrativos."
Write-WARN "  scripts/limpeza_logs_reports.ps1 e scripts/limpeza_prioridade_alta.ps1 NAO incluidos."

# ---------------------------------------------------------------------------
# FASE 6: release/runtime_empty/
# ---------------------------------------------------------------------------
Write-Section "FASE 6: release/runtime_empty/"

$RuntimeEmptyDirs = @(
    (Join-Path $ReleaseRoot "runtime_empty\logs"),
    (Join-Path $ReleaseRoot "runtime_empty\reports"),
    (Join-Path $ReleaseRoot "runtime_empty\relatorios"),
    (Join-Path $ReleaseRoot "runtime_empty\data\state")
)

foreach ($d in $RuntimeEmptyDirs) {
    $label = $d.Replace($ReleaseRoot, "release")
    Invoke-MkDir -Path $d -Label $label
    Write-INFO "  $label (vazio - placeholder de runtime)"
}

Write-WARN "  data/state/window_state.json NAO deve ser incluido (arquivo gerado em uso)."

# ---------------------------------------------------------------------------
# FASE 7: release/runtime_private/
# ---------------------------------------------------------------------------
Write-Section "FASE 7: release/runtime_private/"

$RuntimePrivateBancoDest = Join-Path $ReleaseRoot "runtime_private\banco"
Invoke-CopyBancoSeed -DestinationBancoDir $RuntimePrivateBancoDest -Label "release/runtime_private/banco"
Write-WARN "  runtime_private/banco contem seed sensivel de migracao. Nao imprimir conteudo, nao versionar e distribuir apenas por canal controlado."

# ---------------------------------------------------------------------------
# FASE 8: Validacao pos-copia
# ---------------------------------------------------------------------------
if ($SkipValidation.IsPresent) {
    Write-WARN "Validacao pos-copia ignorada por -SkipValidation."
} else {
    Write-Section "FASE 8: Validacao pos-copia"

    if ($IsDryRun) {
        Write-SIM "  Validacao pos-copia sera executada somente em modo -Execute."
    Write-INFO "  Itens proibidos que serao verificados: banco/ fora da allowlist privada, .env*, logs/* (dados), reports/* (dados),"
        Write-INFO "  relatorios/* (dados), snapshots/, relatorio_final_corrida_*.json, *.db, *.sqlite,"
        Write-INFO "  window_state.json, analise/, extracao/, interface/, core/, debug/, sql/, Main.spec."
    } else {
        $validationErrors = @()

        # Banco seed permitido: somente os arquivos explicitamente listados,
        # em release/app/banco/ e release/runtime_private/banco/.
        $allowedBancoRelative = @{}
        foreach ($relative in $BancoSeedFiles) {
            $allowedBancoRelative[$relative.Replace("/", "\").ToLowerInvariant()] = $true
        }
        $allowedBancoDirs = @(
            (Join-Path $ReleaseRoot "app\banco"),
            (Join-Path $ReleaseRoot "runtime_private\banco")
        )

        foreach ($allowedDir in $allowedBancoDirs) {
            if (-not (Test-Path $allowedDir -PathType Container)) {
                $validationErrors += "BANCO SEED obrigatorio ausente: $allowedDir"
                Write-FAIL "AUSENTE: $allowedDir"
                continue
            }
            foreach ($relative in $BancoSeedFiles) {
                $expected = Join-Path $allowedDir $relative
                if (-not (Test-Path $expected -PathType Leaf)) {
                    $validationErrors += "BANCO SEED ausente: $expected"
                    Write-FAIL "BANCO SEED AUSENTE: $expected"
                }
            }
            $actualFiles = Get-ChildItem -Path $allowedDir -File -Recurse -Force -ErrorAction SilentlyContinue
            foreach ($file in $actualFiles) {
                $rel = $file.FullName.Substring($allowedDir.Length).TrimStart([char[]]@('\', '/')).Replace('/', '\').ToLowerInvariant()
                if (-not $allowedBancoRelative.ContainsKey($rel)) {
                    $validationErrors += "BANCO SEED inesperado: $($file.FullName)"
                    Write-FAIL "BANCO SEED INESPERADO: $($file.FullName)"
                }
            }
        }

        $allBancoDirs = Get-ChildItem -Path $ReleaseRoot -Directory -Recurse -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -eq "banco" }
        foreach ($dir in $allBancoDirs) {
            $full = $dir.FullName.TrimEnd([char[]]@('\', '/'))
            $isAllowed = $false
            foreach ($allowedDir in $allowedBancoDirs) {
                if ($full -ieq $allowedDir.TrimEnd([char[]]@('\', '/'))) {
                    $isAllowed = $true
                    break
                }
            }
            if (-not $isAllowed) {
                $validationErrors += "banco/ fora da allowlist encontrado: $full"
                Write-FAIL "BANCO FORA DA ALLOWLIST: $full"
            }
        }

        $forbiddenBancoNames = @("historico.db", "usuarios.db", "test_creds.csv")
        foreach ($name in $forbiddenBancoNames) {
            $found = Get-ChildItem -Path $ReleaseRoot -Filter $name -Recurse -Force -ErrorAction SilentlyContinue
            foreach ($item in $found) {
                $validationErrors += "ITEM BANCO PROIBIDO encontrado: $name -> $($item.FullName)"
                Write-FAIL "ITEM BANCO PROIBIDO: $name"
            }
        }

        # Padroes de itens proibidos que NAO devem existir em release/
        $prohibitedPatterns = @(
            @{ Pattern = ".env";                        Label = ".env" },
            @{ Pattern = ".env.txt";                    Label = ".env.txt" },
            @{ Pattern = "relatorio_final_corrida_*";   Label = "relatorio_final_corrida_*.json" },
            @{ Pattern = "snapshots";                   Label = "snapshots/" },
            @{ Pattern = "window_state.json";           Label = "data/state/window_state.json" },
            @{ Pattern = "analise";                     Label = "analise/ (legado)" },
            @{ Pattern = "extracao";                    Label = "extracao/ (legado)" },
            @{ Pattern = "interface";                   Label = "interface/ (fachada de testes)" },
            @{ Pattern = "core";                        Label = "core/ (legado DEC-003)" },
            @{ Pattern = "debug";                       Label = "debug/ (artefatos Selenium)" },
            @{ Pattern = "sql";                         Label = "sql/ (DDL PostgreSQL orphaned)" },
            @{ Pattern = "Main.spec";                   Label = "Main.spec (artefato PyInstaller)" },
            @{ Pattern = "images";                      Label = "images/ (sem refs confirmadas)" },
            @{ Pattern = "test_creds.csv";              Label = "test_creds.csv (sensivel)" }
        )

        foreach ($p in $prohibitedPatterns) {
            $found = Get-ChildItem -Path $ReleaseRoot -Filter $p.Pattern -Recurse -Force -ErrorAction SilentlyContinue
            if ($found) {
                $validationErrors += "ITEM PROIBIDO encontrado: $($p.Label) -> $($found[0].FullName)"
                Write-FAIL "ITEM PROIBIDO: $($p.Label)"
            }
        }

        # Verificar extensoes proibidas fora de runtime_empty
        $prohibitedExts = @("*.db", "*.sqlite", "*.sqlite3")
        foreach ($ext in $prohibitedExts) {
            $found = Get-ChildItem -Path (Join-Path $ReleaseRoot "app") -Filter $ext -Recurse -Force -ErrorAction SilentlyContinue
            if ($found) {
                foreach ($f in $found) {
                    $validationErrors += "BANCO DE DADOS proibido em app/: $($f.FullName)"
                    Write-FAIL "BANCO PROIBIDO em app/: $($f.Name)"
                }
            }
        }

        # Verificacoes positivas obrigatorias
        $requiredInRelease = @(
            @{ Path = "app\main.py";                         Label = "release/app/main.py" },
            @{ Path = "app\models.py";                       Label = "release/app/models.py (RUNTIME OBRIGATORIO)" },
            @{ Path = "app\config.json";                     Label = "release/app/config.json (template runtime)" },
            @{ Path = "app\banco\credenciais.csv";           Label = "release/app/banco/credenciais.csv (seed privado)" },
            @{ Path = "app\banco\usuarios.csv";              Label = "release/app/banco/usuarios.csv (seed privado)" },
            @{ Path = "config_template\config.json";         Label = "release/config_template/config.json" },
            @{ Path = "docs_operacionais\README.md";         Label = "release/docs_operacionais/README.md" },
            @{ Path = "docs_operacionais\checklist_pos_instalacao.md"; Label = "release/docs_operacionais/checklist_pos_instalacao.md" },
            @{ Path = "runtime_empty\data\state";            Label = "release/runtime_empty/data/state/ (vazio)" },
            @{ Path = "runtime_private\banco\credenciais.csv"; Label = "release/runtime_private/banco/credenciais.csv (seed privado)" },
            @{ Path = "runtime_private\banco\usuarios.csv";    Label = "release/runtime_private/banco/usuarios.csv (seed privado)" }
        )
        foreach ($r in $requiredInRelease) {
            $fp = Join-Path $ReleaseRoot $r.Path
            if (-not (Test-Path $fp)) {
                $validationErrors += "ITEM OBRIGATORIO ausente: $($r.Label)"
                Write-FAIL "AUSENTE: $($r.Label)"
            } else {
                Write-OK "Presente: $($r.Label)"
            }
        }

        # Verificacao negativa: window_state.json nao deve existir
        $wsJson = Join-Path $ReleaseRoot "runtime_empty\data\state\window_state.json"
        if (Test-Path $wsJson) {
            $validationErrors += "window_state.json NAO deve estar no release (arquivo gerado em uso)"
            Write-FAIL "ENCONTRADO (proibido): runtime_empty/data/state/window_state.json"
        } else {
            Write-OK "Ausente (correto): runtime_empty/data/state/window_state.json"
        }

        if ($validationErrors.Count -gt 0) {
            Write-Host ""
            Write-FAIL "=== VALIDACAO FALHOU: $($validationErrors.Count) erro(s) encontrado(s) ==="
            foreach ($e in $validationErrors) {
                Write-FAIL "  $e"
            }
            Write-FAIL "Corrija os erros antes de usar este pacote."
            exit 2
        } else {
            Write-OK "Validacao pos-copia passou sem erros."
        }
    }
}

# ---------------------------------------------------------------------------
# FASE 8: Geracao de MANIFEST.txt e checksums SHA-256 (opcional)
# ---------------------------------------------------------------------------
function Invoke-GenerateManifest {
    param([string]$ReleaseDir)

    Write-Section "Geracao de MANIFEST.txt + SHA-256"

    if ($IsDryRun) {
        Write-SIM "  Geraria MANIFEST.txt listando todos os arquivos de release/ com hash SHA-256."
        Write-SIM "  Nao executado em modo simulacao."
        return
    }

    $manifestPath = Join-Path $ReleaseDir "MANIFEST.txt"
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $lines  = @("# IntegRAGal Release Manifest", "# Gerado em: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "")

    Get-ChildItem -Path $ReleaseDir -File -Recurse | Sort-Object FullName | ForEach-Object {
        $relativePath = $_.FullName.Replace($ReleaseDir, "").TrimStart("\", "/")
        $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
        $hash  = [System.BitConverter]::ToString($sha256.ComputeHash($bytes)).Replace("-", "").ToLower()
        $lines += "$hash  $relativePath"
    }

    $sha256.Dispose()
    $lines | Set-Content -Path $manifestPath -Encoding UTF8
    Write-OK "MANIFEST.txt gerado: $manifestPath"
    Write-INFO "  Total de arquivos listados: $($lines.Count - 3)"
}

# Chamar geracao de manifest (so executa em modo real, se -Execute foi passado)
Invoke-GenerateManifest -ReleaseDir $ReleaseRoot

# ---------------------------------------------------------------------------
# Resumo final
# ---------------------------------------------------------------------------
Write-Header "Resumo final"

if ($IsDryRun) {
    Write-Host ""
    Write-Host "  MODO SIMULACAO CONCLUIDO." -ForegroundColor Magenta
    Write-Host "  Nenhum arquivo foi criado, copiado ou modificado." -ForegroundColor Magenta
    Write-Host ""
    Write-Host "  Para materializar de fato:" -ForegroundColor Cyan
    Write-Host "    1. Revise este script e o manifest HIG-008." -ForegroundColor Cyan
    Write-Host "    2. Confirme existencia de baseline: integragal_baseline_pre_higienizacao_2026-05-15.zip" -ForegroundColor Cyan
    Write-Host "    3. Execute em rodada propria autorizada:" -ForegroundColor Cyan
    Write-Host "       .\build_release_whitelist.ps1 -Execute" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Ressalvas conhecidas:" -ForegroundColor Yellow
    Write-Host "    - REL-001: assets/icon.ico ausente (ressalva nao bloqueante para piloto)." -ForegroundColor Yellow
    Write-Host "    - Apos materializacao: executar smoke-test conforme docs/procedimento_smoke_test_release.md" -ForegroundColor Yellow
    Write-Host "    - Apos smoke-test aprovado: executar checklist conforme docs/checklist_pos_instalacao.md" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "  MATERIALIZACAO CONCLUIDA." -ForegroundColor Green
    Write-Host "  release/ criada em: $ReleaseRoot" -ForegroundColor Green
    Write-Host ""
    Write-Host "  PROXIMAS ACOES OBRIGATORIAS:" -ForegroundColor Yellow
    Write-Host "    1. Verificar MANIFEST.txt gerado em release/MANIFEST.txt" -ForegroundColor Yellow
    Write-Host "    2. Executar smoke-test conforme docs/procedimento_smoke_test_release.md" -ForegroundColor Yellow
    Write-Host "    3. Aprovar smoke-test antes de qualquer instalacao em ambiente produtivo." -ForegroundColor Yellow
    Write-Host "    4. Executar checklist pos-instalacao: docs/checklist_pos_instalacao.md" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Ressalvas:" -ForegroundColor Yellow
    Write-Host "    - REL-001: assets/icon.ico ausente (ressalva nao bloqueante para piloto)." -ForegroundColor Yellow
    Write-Host "    - config.json: verificar manualmente que data_root e allowed_roots estao VAZIOS." -ForegroundColor Yellow
    Write-Host "    - Nao distribuir sem smoke-test aprovado." -ForegroundColor Yellow
}

Write-Host ""
