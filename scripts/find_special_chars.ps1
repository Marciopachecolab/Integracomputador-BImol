# Script de busca de caracteres especiais
$specialChars = @()
$currentDir = (Get-Location).Path

Get-ChildItem -Path . -Filter *.py -Recurse | Where-Object { $_.FullName -notlike "*\.venv\*" } | ForEach-Object {
    $content = Get-Content $_.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    
    if ($content) {
        $pattern = '[àáâãäåèéêëìíîïòóôõöùúûüçñÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÇÑ]'
        if ($content -match $pattern) {
            $matches = ([regex]$pattern).Matches($content)
            
            $relativePath = $_.FullName.Replace($currentDir, '.').Replace('\', '/')
            $specialChars += [PSCustomObject]@{
                File = $relativePath
                CharCount = $matches.Count
                UniqueChars = ($matches.Value | Select-Object -Unique) -join ', '
            }
        }
    }
}

Write-Host ""
Write-Host "=== ARQUIVOS COM CARACTERES ESPECIAIS ===" -ForegroundColor Cyan
if ($specialChars.Count -gt 0) {
    $specialChars | Format-Table -AutoSize -Wrap
    Write-Host ""
    Write-Host "Total: $($specialChars.Count) arquivos com caracteres especiais" -ForegroundColor Yellow
    
    $specialChars | Export-Csv -Path "special_chars_report.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "Relatorio salvo em: special_chars_report.csv" -ForegroundColor Cyan
}
else {
    Write-Host "SUCESSO: Nenhum arquivo com caracteres especiais encontrado!" -ForegroundColor Green
}
