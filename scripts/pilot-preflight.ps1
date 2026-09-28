# Daily Win V0.4.4 local parent-pilot preflight.
# Never prints secrets. Exit 0 only when blocking checks pass.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$RepoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $RepoRoot "apps\api"))) {
  $RepoRoot = (Get-Location).Path
}
$ApiDir = Join-Path $RepoRoot "apps\api"
$MobileDir = Join-Path $RepoRoot "apps\mobile"
$LocalApi = "http://127.0.0.1:8000"

$script:Failed = $false
$script:Warned = $false

function Write-Check {
  param(
    [string]$Name,
    [string]$Status,
    [string]$Detail = ""
  )
  $pad = $Name.PadRight(22, ".")
  if ($Detail) {
    Write-Host "$pad $Status  $Detail"
  } else {
    Write-Host "$pad $Status"
  }
}

function Fail([string]$Name, [string]$Detail = "") {
  $script:Failed = $true
  Write-Check -Name $Name -Status "FAIL" -Detail $Detail
}

function Pass([string]$Name, [string]$Detail = "") {
  Write-Check -Name $Name -Status "PASS" -Detail $Detail
}

function Warn([string]$Name, [string]$Detail = "") {
  $script:Warned = $true
  Write-Check -Name $Name -Status "WARNING" -Detail $Detail
}

function Read-EnvValue([string]$Path, [string]$Key) {
  if (-not (Test-Path $Path)) {
    return $null
  }
  foreach ($line in Get-Content -Path $Path) {
    $trim = $line.Trim()
    if ($trim.StartsWith("#") -or -not $trim.Contains("=")) {
      continue
    }
    $parts = $trim.Split("=", 2)
    if ($parts[0].Trim() -eq $Key) {
      return $parts[1].Trim().Trim([char]34).Trim([char]39)
    }
  }
  return $null
}

function Test-HttpOk([string]$Url) {
  try {
    $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
    return @{ Ok = ($response.StatusCode -eq 200); Status = $response.StatusCode; Body = [string]$response.Content }
  } catch {
    return @{ Ok = $false; Status = 0; Body = "" }
  }
}

Write-Host ""
Write-Host "Daily Win parent-pilot preflight"
Write-Host ""

$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $docker) {
  Fail "DOCKER" "docker not on PATH"
} else {
  Pass "DOCKER"
  $ps = docker ps --format "{{.Names}}" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Fail "DATABASE" "docker ps failed"
  } elseif ([string]$ps -match "daily-win|db") {
    Pass "DATABASE" "container running"
  } else {
    $pg = Test-NetConnection -ComputerName 127.0.0.1 -Port 5432 -WarningAction SilentlyContinue
    if ($pg.TcpTestSucceeded) {
      Warn "DATABASE" "port 5432 open; container name not matched"
    } else {
      Fail "DATABASE" "Postgres not reachable on 127.0.0.1:5432"
    }
  }
}

Push-Location $ApiDir
try {
  $current = uv run alembic current 2>&1 | Out-String
  $heads = uv run alembic heads 2>&1 | Out-String
  $currentRev = ([regex]::Matches($current, "[0-9a-f]{12,}") | ForEach-Object { $_.Value } | Select-Object -Last 1)
  $headRev = ([regex]::Matches($heads, "[0-9a-f]{12,}") | ForEach-Object { $_.Value } | Select-Object -First 1)
  if ($currentRev -and $headRev -and $currentRev -eq $headRev) {
    Pass "MIGRATIONS"
  } elseif ($current -match "head") {
    Pass "MIGRATIONS"
  } else {
    Fail "MIGRATIONS" "alembic is not at head"
  }
} catch {
  Fail "MIGRATIONS" "alembic current failed"
} finally {
  Pop-Location
}

$health = Test-HttpOk "$LocalApi/health"
if ($health.Ok) {
  Pass "API"
} else {
  Fail "API" "GET $LocalApi/health did not return 200"
}

$dbHealth = Test-HttpOk "$LocalApi/health/db"
if ($dbHealth.Ok) {
  Pass "API DB HEALTH"
} else {
  Fail "API DB HEALTH" "GET $LocalApi/health/db did not return 200"
}

$status = Test-HttpOk "$LocalApi/api/v1/demo/pilot/status"
if (-not $status.Ok) {
  Fail "OPENAI CONFIG" "pilot status unavailable"
  Fail "NEXT-WIN PREP" "pilot status unavailable"
} else {
  try {
    $payload = $status.Body | ConvertFrom-Json
  } catch {
    $payload = $null
  }
  if ($null -eq $payload) {
    Fail "OPENAI CONFIG" "could not parse pilot status"
  } else {
    $blob = ($status.Body).ToLowerInvariant()
    foreach ($secretWord in @("sk-", "api_key", "database_url", "postgresql+", "session_secret")) {
      if ($blob.Contains($secretWord)) {
        Fail "PILOT STATUS" "response contained a secret-shaped field"
        break
      }
    }
    if ($payload.generation_config -eq "configured") {
      Pass "OPENAI CONFIG"
    } else {
      Fail "OPENAI CONFIG" "generation_config is not configured"
    }
    Write-Check -Name "MODEL" -Status ($payload.model)
    Write-Check -Name "CURRICULUM" -Status ($payload.curriculum)
    Write-Check -Name "PLACEMENT" -Status ($payload.placement)
    Write-Check -Name "SCHEDULER" -Status ($payload.scheduler)
    Write-Check -Name "INSTRUCTION" -Status ($payload.instruction)
    Write-Check -Name "PROMPT" -Status ($payload.prompt)
    if ($payload.background_preparation -eq "available") {
      Pass "NEXT-WIN PREP"
    } else {
      Fail "NEXT-WIN PREP" "NextWinPreparation unavailable"
    }
    if ($payload.db -eq "ok") {
      Pass "PILOT DB"
    } else {
      Fail "PILOT DB" $payload.db
    }
  }
}

$envLocal = Join-Path $MobileDir ".env.local"
if (-not (Test-Path $envLocal)) {
  Fail "MOBILE ENV" "apps/mobile/.env.local missing"
} else {
  Pass "MOBILE ENV"
  $apiUrl = Read-EnvValue $envLocal "EXPO_PUBLIC_API_URL"
  if ([string]::IsNullOrWhiteSpace($apiUrl)) {
    Fail "MOBILE API URL" "EXPO_PUBLIC_API_URL missing"
  } elseif ($apiUrl.EndsWith("/")) {
    Fail "MOBILE API URL" "trailing slash - remove it"
  } elseif ($apiUrl -match "YOUR_COMPUTER_LAN_IP") {
    Fail "MOBILE API URL" "placeholder LAN IP still set"
  } else {
    $mobileHealth = Test-HttpOk "$apiUrl/health"
    if ($mobileHealth.Ok) {
      Pass "MOBILE API URL"
    } else {
      Fail "MOBILE API URL" "EXPO_PUBLIC_API_URL did not respond to /health"
    }
  }
}

$appEnv = Read-EnvValue (Join-Path $ApiDir ".env") "APP_ENV"
if ([string]::IsNullOrWhiteSpace($appEnv)) {
  $appEnv = "local"
}
if (@("local", "development", "dev", "test") -contains $appEnv.ToLowerInvariant()) {
  Pass "DEV ENVIRONMENT" $appEnv
} else {
  Warn "DEV ENVIRONMENT" $appEnv
}

Write-Host ''
if ($script:Failed) {
  Write-Host 'PILOT READY .......... NO'
  exit 1
}
Write-Host 'PILOT READY .......... YES'
exit 0
