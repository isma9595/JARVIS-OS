$ErrorActionPreference = "Continue"

$failedChecks = 0
$warningChecks = 0

function Write-CheckOk {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-CheckFail {
    param([string]$Message)
    $script:failedChecks++
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Write-CheckWarn {
    param([string]$Message)
    $script:warningChecks++
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Invoke-CheckedCommand {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    try {
        $output = & $Command @Arguments 2>&1
        return [PSCustomObject]@{
            ExitCode = $LASTEXITCODE
            Output = $output
            Error = $null
        }
    } catch {
        return [PSCustomObject]@{
            ExitCode = 1
            Output = @()
            Error = $_.Exception.Message
        }
    }
}

Write-Host "========================================"
Write-Host " JARVIS-OS Health Check"
Write-Host "========================================"
Write-Host ""

$projectRoot = Resolve-Path -Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
$pythonAvailable = $false
if ($null -eq $pythonCommand) {
    Write-CheckFail "Python is not available in PATH."
} else {
    $pythonVersionResult = Invoke-CheckedCommand -Command "python" -Arguments @("--version")
    if ($pythonVersionResult.ExitCode -eq 0) {
        $pythonAvailable = $true
        Write-CheckOk "Python is available."
        Write-Host "Python version: $($pythonVersionResult.Output)"
    } else {
        Write-CheckFail "Python command was found but could not run."
        if ($pythonVersionResult.Error) {
            Write-Host "Python error: $($pythonVersionResult.Error)"
        }
    }
}

if (Test-Path -Path "run.py" -PathType Leaf) {
    Write-CheckOk "run.py exists."
} else {
    Write-CheckFail "run.py is missing."
}

$keyFolders = @("core", "voice", "docs", "tests", ".ai")
foreach ($folder in $keyFolders) {
    if (Test-Path -Path $folder -PathType Container) {
        Write-CheckOk "Folder exists: $folder"
    } else {
        Write-CheckFail "Folder is missing: $folder"
    }
}

$pytestAvailable = $false
if ($pythonAvailable) {
    $pytestVersionResult = Invoke-CheckedCommand -Command "python" -Arguments @("-m", "pytest", "--version")
    if ($pytestVersionResult.ExitCode -eq 0) {
        $pytestAvailable = $true
        Write-CheckOk "pytest is available."
    } else {
        Write-CheckWarn "pytest is not available. Install it manually, then run: pytest"
    }
} else {
    Write-CheckWarn "pytest check skipped because Python is not available."
}

if ($pytestAvailable) {
    Write-Host ""
    Write-Host "Running pytest..."
    $pytestResult = Invoke-CheckedCommand -Command "python" -Arguments @("-m", "pytest")
    if ($pytestResult.Output) {
        $pytestResult.Output | ForEach-Object { Write-Host $_ }
    }

    if ($pytestResult.ExitCode -eq 0) {
        Write-CheckOk "pytest passed."
    } else {
        Write-CheckFail "pytest failed."
    }
}

Write-Host ""
Write-Host "========================================"
Write-Host " Health Check Summary"
Write-Host "========================================"
Write-Host "Failures: $failedChecks"
Write-Host "Warnings: $warningChecks"

if ($failedChecks -eq 0) {
    Write-Host "Result: SUCCESS" -ForegroundColor Green
    exit 0
}

Write-Host "Result: FAILURE" -ForegroundColor Red
exit 1
