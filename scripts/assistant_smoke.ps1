$ErrorActionPreference = "Continue"

python -m pytest tests/smoke/test_assistant_smoke.py -q
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "JARVIS ASSISTANT SMOKE: SUCCESS"
} else {
    Write-Host "JARVIS ASSISTANT SMOKE: FAILED"
}

exit $exitCode
