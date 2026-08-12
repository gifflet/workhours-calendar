# Workhours Calendar installer (Windows) — pulls the prebuilt images and
# starts MongoDB + the API with Docker. Safe to re-run: it updates the
# containers and keeps the data (stored in the workhours_mongo volume).
#
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/gifflet/workhours-calendar/main/install.ps1 | iex
#
# Options (environment variables):
#   WORKHOURS_PORT  Host port for the API (default: 8001)
#   MONGO_URL       Use an external MongoDB instead of starting a container

$ErrorActionPreference = "Stop"

$ApiImage = "ghcr.io/gifflet/workhours-calendar-api:latest"
$MongoImage = "mongo:7"
$Network = "workhours"
$ApiPort = if ($env:WORKHOURS_PORT) { $env:WORKHOURS_PORT } else { "8001" }

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker is required. Install Docker Desktop from https://docs.docker.com/get-docker/ and re-run."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker is installed but not running. Start Docker Desktop and re-run."
}

# Fail early if the port is served by something we don't manage.
$portBusy = $false
try {
    Invoke-WebRequest "http://localhost:$ApiPort/health" -TimeoutSec 2 -UseBasicParsing | Out-Null
    $portBusy = $true
} catch {}
if ($portBusy -and -not ((docker ps --format '{{.Names}}') -contains 'workhours-api')) {
    Write-Error "Port $ApiPort is already in use by something else. Set WORKHOURS_PORT to a free port and re-run."
}

Write-Host "Setting up Workhours Calendar (API on port $ApiPort)..."
docker network inspect $Network *> $null
if ($LASTEXITCODE -ne 0) { docker network create $Network | Out-Null }

$MongoUrl = $env:MONGO_URL
if (-not $MongoUrl) {
    $MongoUrl = "mongodb://workhours-mongo:27017"
    docker pull $MongoImage
    # Stop gracefully (SIGTERM) so mongod flushes to disk; data lives in the
    # workhours_mongo volume and survives container replacement.
    docker stop workhours-mongo *> $null
    docker rm workhours-mongo *> $null
    docker run -d --name workhours-mongo --network $Network `
        --restart unless-stopped -v workhours_mongo:/data/db $MongoImage | Out-Null
}

docker pull $ApiImage
docker rm -f workhours-api *> $null
docker run -d --name workhours-api --network $Network `
    --restart unless-stopped -p "${ApiPort}:8000" `
    -e "MONGO_URL=$MongoUrl" $ApiImage | Out-Null

Write-Host "Waiting for the API to become healthy..."
$healthy = $false
foreach ($i in 1..30) {
    try {
        $health = Invoke-RestMethod "http://localhost:$ApiPort/health" -TimeoutSec 2
        if ($health.mongodb -eq "up") { $healthy = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
}
if (-not $healthy) {
    Write-Error "API did not become healthy in 30s. Check: docker logs workhours-api"
}

Write-Host ""
Write-Host "Workhours Calendar is up:"
Write-Host "  API:        http://localhost:$ApiPort"
Write-Host "  Swagger UI: http://localhost:$ApiPort/docs"
Write-Host ""
Write-Host "Containers restart with Docker on boot. Re-run this script to update."
Write-Host "Uninstall: docker rm -f workhours-api workhours-mongo; docker volume rm workhours_mongo"
