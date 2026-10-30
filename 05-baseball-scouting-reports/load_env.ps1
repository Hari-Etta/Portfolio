# Loads .env into THIS PowerShell session so dbt can read the values. Run with:  . .\load_env.ps1
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#=][^=]*)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}
Write-Host "Loaded .env into this PowerShell session"
