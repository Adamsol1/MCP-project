# $ErrorActionPreference is intentionally left at default "Continue" so that
# native-command stderr (e.g. poetry deprecation warnings) does not turn into
# a terminating error when the script's output is piped/redirected. We check
# $LASTEXITCODE explicitly via Invoke-Step after every native call.

# VS Code's Python extension can set VIRTUAL_ENV to the system Python when it
# auto-activates the selected interpreter. Poetry honors VIRTUAL_ENV and skips
# venv creation, installing every project into the same system site-packages —
# which lets the projects overwrite each other's deps. Clear it for this run.
$env:VIRTUAL_ENV = $null

$Root = $PSScriptRoot

function Invoke-Step {
    param([string]$Description, [scriptblock]$Command)
    Write-Host "==> $Description"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED ($Description): exit $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Invoke-Step "Installing root npm dependencies..." { Set-Location $Root; npm install }
Invoke-Step "Installing frontend npm dependencies..." { Set-Location "$Root\frontend"; npm install }

foreach ($dir in @("backend", "council_mcp_server", "generation_mcp_server", "review_mcp_server")) {
    if (-not (Test-Path "$Root\$dir\pyproject.toml")) { continue }

    Set-Location "$Root\$dir"

    Write-Host "==> Checking poetry lock in $dir..."
    $lockOk = $false
    if (Test-Path "$Root\$dir\poetry.lock") {
        poetry check --lock
        if ($LASTEXITCODE -eq 0) { $lockOk = $true }
    }
    if (-not $lockOk) {
        Invoke-Step "Lock file missing or stale - running poetry lock in $dir..." { poetry lock }
    }

    Invoke-Step "Running poetry install in $dir..." { poetry install }

    if ($dir -eq "backend") {
        New-Item -ItemType Directory -Force -Path "$Root\backend\data\logs" | Out-Null
        Invoke-Step "Running sessions migration..." { poetry run alembic -c alembic_sessions.ini upgrade head }
        Invoke-Step "Running knowledge migration..." { poetry run alembic -c alembic_knowledge.ini upgrade head }
        Invoke-Step "Seeding knowledge database..." { poetry run python scripts/seed_knowledge.py }
        Invoke-Step "Seeding perspective documents..." { poetry run python scripts/seed_perspective_docs.py }
    }
}

Write-Host ""
Write-Host "All dependencies installed."
