# Kopiuje moduly MDM z Testorbiteka/crm-engine do orbiteus (jednorazowo / po aktualizacji shipping).
# Usage: .\scripts\import-mdm-from-testorbiteka.ps1
# Po imporcie: recznie zarejestruj w backend/api.py + migracje + celery include.

$ErrorActionPreference = "Stop"
$Orbiteus = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Testorbiteka = "C:\Users\MARCINS\Documents\MIMMS_CORE\Testorbiteka\Testorbiteka\crm-engine\backend"

if (-not (Test-Path $Testorbiteka)) {
    Write-Host "Brak $Testorbiteka" -ForegroundColor Red
    exit 1
}

$Pairs = @(
    @{ Src = "modules\shipping"; Dst = "modules\shipping" },
    @{ Src = "orbiteus_core\ports"; Dst = "orbiteus_core\ports" },
    @{ Src = "tasks\shipping_tasks.py"; Dst = "tasks\shipping_tasks.py" },
    @{ Src = "tasks\outbox_tasks.py"; Dst = "tasks\outbox_tasks.py" },
    @{ Src = "orbiteus_core\integrations"; Dst = "orbiteus_core\integrations" }
)

foreach ($p in $Pairs) {
    $src = Join-Path $Testorbiteka $p.Src
    $dst = Join-Path (Join-Path $Orbiteus "backend") $p.Dst
    if (-not (Test-Path $src)) {
        Write-Host "SKIP (brak): $src" -ForegroundColor Yellow
        continue
    }
    $parent = Split-Path $dst -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    Copy-Item -Path $src -Destination $dst -Recurse -Force
    Write-Host "OK: $($p.Src) -> backend\$($p.Dst)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Nastepne kroki reczne:" -ForegroundColor Cyan
Write-Host "  1. backend/api.py: registry.register('shipping') [+ orders gdy bedzie]"
Write-Host "  2. celery_app.py include: tasks.shipping_tasks"
Write-Host "  3. Migracja l2f7* z Testorbiteka -> backend/migrations/versions/"
Write-Host "  4. docker-compose: worker+beat (jak testorbiteka local-ports)"
Write-Host "  5. .env: DPD_*, DSV_*, GEODIS_* (sync z mercato)"
