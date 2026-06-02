# Run baseline test suite (Phase 0)
# Usage: .\scripts\run_baseline_tests.ps1

param(
    [string]$PythonExe = "python"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     BASELINE TEST SUITE (PHASE 0)      " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& $PythonExe -m pytest -q
exit $LASTEXITCODE
