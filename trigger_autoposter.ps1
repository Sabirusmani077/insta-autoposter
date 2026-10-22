# Daily Instagram Post Trigger & Verification Script
# Runs silently via Windows Task Scheduler to guarantee on-time daily publishing

$ErrorActionPreference = "SilentlyContinue"
$today = (Get-Date).ToString("yyyy-MM-dd")
$logPath = Join-Path $PSScriptRoot "trigger.log"

function Write-Log($msg) {
    $time = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    Add-Content -Path $logPath -Value "[$time] $msg"
}

# 1. Check if post is already published for today on GitHub
try {
    $historyUrl = "https://raw.githubusercontent.com/Sabirusmani077/insta-autoposter/main/history.json"
    $history = Invoke-RestMethod -Uri $historyUrl -TimeoutSec 15
    if ($history | Where-Object { $_.date -eq $today -and $_.status -eq "published" }) {
        Write-Log "Today ($today) already published. Skipping trigger."
        exit 0
    }
} catch {
    Write-Log "Could not read history.json from GitHub, proceeding with trigger..."
}

# 2. Retrieve GitHub token securely from Git Credential Manager
try {
    $inputCmd = "protocol=https`nhost=github.com`n`n"
    $res = $inputCmd | git credential fill
    $token = ($res -split "`n" | Where-Object { $_ -match "^password=" }) -replace "^password=", ""
    $token = $token.Trim()

    if (-not $token) {
        Write-Log "Git Credential Manager did not return a token."
        exit 1
    }

    $headers = @{
        "Authorization" = "Bearer $token"
        "Accept"        = "application/vnd.github+json"
        "User-Agent"    = "InstaAutoPoster-LocalTrigger"
    }
    $body = '{"ref":"main","inputs":{"publish":"true"}}'

    $dispatchUrl = "https://api.github.com/repos/Sabirusmani077/insta-autoposter/actions/workflows/daily.yml/dispatches"
    Invoke-RestMethod -Uri $dispatchUrl -Method Post -Headers $headers -Body $body -TimeoutSec 30
    Write-Log "Successfully triggered daily post workflow for $today via GitHub API."
} catch {
    Write-Log "Failed to trigger workflow: $_"
}
