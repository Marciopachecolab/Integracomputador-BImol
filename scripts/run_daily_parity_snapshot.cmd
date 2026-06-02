@echo off
pushd "%~dp0.."
set "ProjectRoot=%CD%"
popd
"%ProjectRoot%\.venv\Scripts\python.exe" "%ProjectRoot%\scripts\generate_daily_parity_snapshot.py" --logs-dir "%ProjectRoot%\logs" --db-path "%ProjectRoot%\banco\historico.db" --output-dir "%ProjectRoot%\snapshots" --offset-days 1 --reconciliation-alert-threshold 0.02 --reconciliation-block-threshold 0.05 --exame-slug "vr1e2_biomanguinhos" --fail-on-reconciliation-block
exit /b %ERRORLEVEL%
