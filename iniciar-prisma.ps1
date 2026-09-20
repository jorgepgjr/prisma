[CmdletBinding()]
param(
    [switch]$Seed
)

$ErrorActionPreference = 'Stop'
$projectRoot = Join-Path $PSScriptRoot 'prisma'
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$composeFile = Join-Path $projectRoot 'docker-compose.yml'

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw 'O Docker Desktop não está pronto. Abra-o e aguarde o status "Running".'
}

docker compose -f $composeFile up -d
if ($LASTEXITCODE -ne 0) {
    throw 'Não foi possível iniciar o PostgreSQL.'
}

$databaseReady = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    docker compose -f $composeFile exec -T db pg_isready -U postgres -d prisma *> $null
    if ($LASTEXITCODE -eq 0) {
        $databaseReady = $true
        break
    }
    Start-Sleep -Seconds 2
}
if (-not $databaseReady) {
    throw 'O PostgreSQL não ficou pronto em até 40 segundos.'
}

if ($Seed) {
    Push-Location $backendRoot
    try {
        pipenv run python -m app.seed
        if ($LASTEXITCODE -ne 0) {
            throw 'A carga inicial do banco falhou.'
        }
    }
    finally {
        Pop-Location
    }
}

$shellCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
if (-not $shellCommand) {
    $shellCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue
}
if (-not $shellCommand) {
    throw 'Não encontrei um executável do PowerShell para abrir os serviços.'
}
$shellPath = $shellCommand.Source

Start-Process -FilePath $shellPath -WorkingDirectory $backendRoot -ArgumentList @(
    '-NoExit',
    '-Command',
    'pipenv run uvicorn app.main:app --reload'
)

Start-Process -FilePath $shellPath -WorkingDirectory $frontendRoot -ArgumentList @(
    '-NoExit',
    '-Command',
    'npm run dev'
)

Write-Host 'Prisma iniciado: portal http://localhost:3000 | API http://localhost:8000/docs'
