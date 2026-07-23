<#
.SYNOPSIS
    xiaopengPanel test runner script
.DESCRIPTION
    Runs backend pytest tests and frontend Vitest tests, summarizes results.
.PARAMETER BackendOnly
    Run backend tests only
.PARAMETER FrontendOnly
    Run frontend tests only
.PARAMETER Coverage
    Generate coverage reports
.EXAMPLE
    .\run_tests.ps1                  # Run all tests
    .\run_tests.ps1 -BackendOnly     # Backend only
    .\run_tests.ps1 -FrontendOnly    # Frontend only
    .\run_tests.ps1 -Coverage        # With coverage
#>
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$Coverage
)

$ErrorActionPreference = 'Continue'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot 'backend'
$frontendDir = Join-Path $projectRoot 'frontend-vue'

$results = @()

function Invoke-BackendTests {
    param([bool]$WithCoverage)
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  Backend Tests (pytest)' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan

    Push-Location $backendDir
    try {
        if ($WithCoverage) {
            $pyArgs = @('-m', 'pytest', 'tests/', '--tb=short', '-q', '--cov=modules', '--cov=api', '--cov-report=term-missing')
        } else {
            $pyArgs = @('-m', 'pytest', 'tests/', '--tb=short', '-q', '--no-cov')
        }
        & python @pyArgs 2>&1 | Out-Host
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($exitCode -eq 0) {
        Write-Host '[Backend] All tests passed' -ForegroundColor Green
        return @{ Name = 'Backend (pytest)'; Passed = $true; ExitCode = $exitCode }
    } else {
        Write-Host "[Backend] Failures or warnings (exit=$exitCode, coverage threshold also returns non-zero)" -ForegroundColor Yellow
        return @{ Name = 'Backend (pytest)'; Passed = $false; ExitCode = $exitCode }
    }
}

function Invoke-FrontendTests {
    param([bool]$WithCoverage)
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  Frontend Tests (Vitest)' -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan

    Push-Location $frontendDir
    try {
        if ($WithCoverage) {
            & npx vitest run --coverage 2>&1 | Out-Host
        } else {
            & npx vitest run 2>&1 | Out-Host
        }
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($exitCode -eq 0) {
        Write-Host '[Frontend] All tests passed' -ForegroundColor Green
        return @{ Name = 'Frontend (Vitest)'; Passed = $true; ExitCode = $exitCode }
    } else {
        Write-Host "[Frontend] Failures detected (exit=$exitCode)" -ForegroundColor Red
        return @{ Name = 'Frontend (Vitest)'; Passed = $false; ExitCode = $exitCode }
    }
}

# ==================== Run Tests ====================

$runBackend = -not $FrontendOnly
$runFrontend = -not $BackendOnly

if ($runBackend) {
    $results += (Invoke-BackendTests -WithCoverage $Coverage)
}
if ($runFrontend) {
    $results += (Invoke-FrontendTests -WithCoverage $Coverage)
}

# ==================== Summary ====================

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Test Summary' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

$allPassed = $true
foreach ($r in $results) {
    $status = if ($r.Passed) { 'PASS' } else { 'FAIL' }
    $color = if ($r.Passed) { 'Green' } else { 'Red' }
    Write-Host ("  {0,-20} {1}" -f $r.Name, $status) -ForegroundColor $color
    if (-not $r.Passed) { $allPassed = $false }
}

Write-Host ''
if ($allPassed) {
    Write-Host 'All test suites passed!' -ForegroundColor Green
    exit 0
} else {
    Write-Host 'Some tests failed. Please check the output above.' -ForegroundColor Red
    exit 1
}
