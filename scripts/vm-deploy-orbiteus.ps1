# Deploy msulich7-hub/orbiteus on VM 10.10.99.60
# Usage: .\scripts\vm-deploy-orbiteus.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $Root "scripts\vm-connection.env"

$cfg = @{
    Alias = "ubnt"
    Host = "10.10.99.60"
    User = "marcins"
    RemoteDir = "/home/marcins/apps/orbiteus"
}

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z_]+)=(.*)$') {
            switch ($Matches[1]) {
                "VM_SSH_ALIAS" { if ($Matches[2]) { $cfg.Alias = $Matches[2] } }
                "VM_SSH_HOST" { if ($Matches[2]) { $cfg.Host = $Matches[2] } }
                "VM_SSH_USER" { if ($Matches[2]) { $cfg.User = $Matches[2] } }
                "VM_ORBITEUS_REMOTE_DIR" { if ($Matches[2]) { $cfg.RemoteDir = $Matches[2] } }
            }
        }
    }
}

$sshTarget = if ($cfg.Alias) { $cfg.Alias } else { "$($cfg.User)@$($cfg.Host)" }
$remoteDir = $cfg.RemoteDir
$remoteCmd = @"
set -e
cd '$remoteDir'
git remote set-url origin https://github.com/msulich7-hub/orbiteus.git 2>/dev/null || true
git fetch origin
git stash push -m 'vm-pre-deploy' 2>/dev/null || true
git pull origin main
sed -i 's/\r$//' scripts/vm-orbiteus-deploy.sh 2>/dev/null || true
chmod +x scripts/vm-orbiteus-deploy.sh
./scripts/vm-orbiteus-deploy.sh
"@

Write-Host "=== Orbiteus VM deploy ===" -ForegroundColor Cyan
Write-Host "SSH: $sshTarget -> $remoteDir"
ssh $sshTarget $remoteCmd

Write-Host ""
Write-Host "Admin:  http://$($cfg.Host):3020" -ForegroundColor Green
Write-Host "API:    http://$($cfg.Host):8020" -ForegroundColor Green
Write-Host "Testorbiteka (MDM shipping): http://$($cfg.Host):3010 / :8010" -ForegroundColor Yellow
