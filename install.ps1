$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "==> Installing root npm dependencies..."
Set-Location $Root; npm install

Write-Host "==> Installing frontend npm dependencies..."
Set-Location "$Root\frontend"; npm install

foreach ($dir in @("backend", "council_mcp_server", "generation_mcp_server", "review_mcp_server")) {
    if (Test-Path "$Root\$dir\pyproject.toml") {
        Write-Host "==> Running poetry install in $dir..."
        Set-Location "$Root\$dir"; poetry install
    }
}

Write-Host ""
Write-Host "All dependencies installed."
