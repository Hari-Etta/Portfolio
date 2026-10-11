# Reads .env and loads each KEY=VALUE line into the current PowerShell session as an env var.
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}
Write-Host "Environment variables loaded from .env" -ForegroundColor Green