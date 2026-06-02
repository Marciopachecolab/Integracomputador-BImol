# Run Phase 0 gates (baseline + smoke contracts)
# Usage: .\scripts\run_phase0_gates.ps1

param(
    [string]$PythonExe = "python",
    [switch]$SkipBaselineCheck,
    [switch]$StrictEncodingScan
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       PHASE 0 GATES (MINIMAL)         " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipBaselineCheck) {
    & $PythonExe scripts/generate_phase0_baseline.py --check
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & $PythonExe scripts/baseline_refresh_governance.py check
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

# Scanner de conformidade CSV (encoding/BOM/mojibake).
$scanArgs = @(
    "scripts/scan_csv_encoding_conformance.py",
    "--root", "logs",
    "--root", "reports",
    "--root", "banco",
    "--report", "snapshots/encoding_conformance_report.json",
    "--strict-bom",
    "--strict-invalid-utf8",
    "--strict-mojibake"
)
# Compatibilidade: switch legado mantido, mas scanner estrito virou regra fixa.

& $PythonExe @scanArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $PythonExe -m pytest -q `
    tests/test_u0_service_ui_boundary.py `
    tests/test_phase_u5_error_handler_backend.py `
    tests/test_phase_u5_ui_notification_backend.py `
    tests/test_phase_u6_boundary_guards.py `
    tests/test_csv_encoding_conformance_scanner.py `
    tests/test_mojibake_scan.py `
    tests/test_ui_mojibake_literals_guard.py `
    tests/test_phase0_mojibake_gate_policy.py `
    tests/test_sanitize_historico_mojibake.py `
    tests/test_phase0_runtime_flags.py `
    tests/test_phase0_analysis_routing.py `
    tests/test_phase0_main_panel_flag.py `
    tests/test_gal_formatter_layout.py `
    tests/test_history_report_csv.py `
    tests/integration/test_pipeline_smoke.py
exit $LASTEXITCODE
