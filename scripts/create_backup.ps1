# Script de backup completo do sistema
# Cria backup timestamped excluindo .venv e arquivos temporários

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$sourceDir = Get-Location
$backupDir = Join-Path (Split-Path $sourceDir -Parent) "Integragal - Backup - $timestamp"

Write-Host ""
Write-Host "=== BACKUP DO SISTEMA ===" -ForegroundColor Cyan
Write-Host "Origem: $sourceDir" -ForegroundColor White
Write-Host "Destino: $backupDir" -ForegroundColor White
Write-Host ""

# Criar diretório de backup
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Exclusões
$excludeDirs = @('.venv', '__pycache__', '.git', 'reports')
$excludeFiles = @('*.pyc', '*.pyo', '*.log', 'encoding_report.csv', 'special_chars_report.csv')

Write-Host "Copiando arquivos..." -ForegroundColor Yellow

# Usar robocopy para backup eficiente
$robocopyArgs = @(
    $sourceDir,
    $backupDir,
    '/E',                    # Copiar subdiretórios incluindo vazios
    '/XD', ($excludeDirs -join ' '),  # Excluir diretórios
    '/XF', ($excludeFiles -join ' '), # Excluir arquivos
    '/NDL',                  # Não listar diretórios
    '/NJH',                  # Sem header
    '/NJS',                  # Sem summary
    '/NC',                   # Sem classe de arquivo
    '/NS',                   # Sem tamanho
    '/NP'                    # Sem progresso percentual
)

$result = robocopy @robocopyArgs

# Robocopy retorna códigos específicos
$exitCode = $LASTEXITCODE
if ($exitCode -le 7) {
    Write-Host ""
    Write-Host "SUCESSO: Backup criado!" -ForegroundColor Green
    Write-Host "Localizacao: $backupDir" -ForegroundColor Cyan
    
    # Contar arquivos copiados
    $fileCount = (Get-ChildItem -Path $backupDir -Recurse -File).Count
    Write-Host "Arquivos copiados: $fileCount" -ForegroundColor White
    
    # Salvar informação do backup
    $backupInfo = @{
        Timestamp = $timestamp
        SourceDir = $sourceDir.Path
        BackupDir = $backupDir
        FileCount = $fileCount
        ExitCode  = $exitCode
    }
    
    $backupInfo | ConvertTo-Json | Out-File -FilePath "backup_info.json" -Encoding UTF8
    Write-Host ""
    Write-Host "Informacoes salvas em: backup_info.json" -ForegroundColor Cyan
}
else {
    Write-Host ""
    Write-Host "ERRO: Backup falhou (Exit Code: $exitCode)" -ForegroundColor Red
    exit 1
}
