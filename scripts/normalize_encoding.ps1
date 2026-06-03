# Script de normalizacao de encoding
# Garante que todos os arquivos estao em UTF-8 sem BOM

param(
    [switch]$DryRun = $false
)

$processed = 0
$converted = 0
$errors = @()

Write-Host ""
Write-Host "=== NORMALIZACAO DE ENCODING ===" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "MODO: DRY RUN (simulacao)" -ForegroundColor Yellow
}
Write-Host ""

Get-ChildItem -Path . -Filter *.py -Recurse | Where-Object { $_.FullName -notlike "*\.venv\*" } | ForEach-Object {
    $file = $_.FullName
    $processed++
    
    try {
        # Ler conteudo
        $content = Get-Content $file -Raw -Encoding UTF8
        
        if (-not $DryRun) {
            # Salvar em UTF-8 sem BOM
            $utf8NoBOM = New-Object System.Text.UTF8Encoding $false
            [System.IO.File]::WriteAllText($file, $content, $utf8NoBOM)
            $converted++
            
            if ($processed % 20 -eq 0) {
                Write-Host "Processados: $processed / Convertidos: $converted" -ForegroundColor Cyan
            }
        }
        else {
            if ($processed % 20 -eq 0) {
                Write-Host "[DRY RUN] Processados: $processed" -ForegroundColor Yellow
            }
        }
    }
    catch {
        $relativePath = $file.Replace((Get-Location).Path, '.')
        $errors += [PSCustomObject]@{
            File  = $relativePath
            Error = $_.Exception.Message
        }
        Write-Host "ERRO: $relativePath" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== CONCLUSAO ===" -ForegroundColor Cyan
Write-Host "Arquivos processados: $processed" -ForegroundColor White
if (-not $DryRun) {
    Write-Host "Arquivos convertidos: $converted" -ForegroundColor Green
}
Write-Host "Erros: $($errors.Count)" -ForegroundColor $(if ($errors.Count -eq 0) { "Green" } else { "Red" })

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "=== ERROS ENCONTRADOS ===" -ForegroundColor Red
    $errors | Format-Table -AutoSize
}
else {
    Write-Host ""
    Write-Host "SUCESSO: Todos os arquivos normalizados!" -ForegroundColor Green
}
