# Script de analise de encoding
$results = @()
$currentDir = (Get-Location).Path

Get-ChildItem -Path . -Filter *.py -Recurse | Where-Object { $_.FullName -notlike "*\.venv\*" } | ForEach-Object {
    $file = $_.FullName
    $bytes = [System.IO.File]::ReadAllBytes($file)
    
    $encoding = 'Unknown'
    $hasBOM = $false
    
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $encoding = 'UTF-8 with BOM'
        $hasBOM = $true
    }
    elseif ($bytes.Length -ge 2) {
        if ($bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
            $encoding = 'UTF-16 LE'
        }
        elseif ($bytes[0] -eq 0xFE -and $bytes[1] -eq 0xFF) {
            $encoding = 'UTF-16 BE'
        }
        else {
            $encoding = 'UTF-8 no BOM'
        }
    }
    
    $relativePath = $file.Replace($currentDir, '.').Replace('\', '/')
    $results += [PSCustomObject]@{
        File = $relativePath
        Encoding = $encoding
        HasBOM = $hasBOM
        SizeKB = [math]::Round($bytes.Length / 1024, 2)
    }
}

$results | Export-Csv -Path "encoding_report.csv" -NoTypeInformation -Encoding UTF8

Write-Host ""
Write-Host "=== RESUMO DE ENCODING ===" -ForegroundColor Cyan
$results | Group-Object Encoding | Select-Object Name, Count | Format-Table -AutoSize

$withBOM = $results | Where-Object { $_.HasBOM }
if ($withBOM.Count -gt 0) {
    Write-Host ""
    Write-Host "=== ARQUIVOS COM BOM (Precisam correcao) ===" -ForegroundColor Yellow
    $withBOM | Format-Table -AutoSize
}
else {
    Write-Host ""
    Write-Host "SUCESSO: Nenhum arquivo com BOM encontrado!" -ForegroundColor Green
}

Write-Host ""
Write-Host "Relatorio completo salvo em: encoding_report.csv" -ForegroundColor Cyan
Write-Host "Total de arquivos analisados: $($results.Count)" -ForegroundColor White
