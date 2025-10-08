# startup.ps1 - Windows PowerShell Startup Script for EV Digital Twin
# Run this script to check prerequisites and start the system

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "EV Digital Twin - Startup Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Function to check command exists
function Test-Command {
    param($Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# 1. Check Python
Write-Host "[1/7] Checking Python..." -ForegroundColor Yellow
if (Test-Command python) {
    $pythonVersion = python --version
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Python not found. Please install Python 3.12+" -ForegroundColor Red
    exit 1
}

# 2. Check Docker
Write-Host "[2/7] Checking Docker..." -ForegroundColor Yellow
if (Test-Command docker) {
    try {
        $dockerVersion = docker --version
        Write-Host "  ✓ $dockerVersion" -ForegroundColor Green
        
        # Test Docker is running
        docker ps 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Docker is running" -ForegroundColor Green
        }
        else {
            Write-Host "  ✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
            Write-Host "    Waiting for Docker to start..." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
        }
    }
    catch {
        Write-Host "  ✗ Docker error: $_" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "  ✗ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    exit 1
}

# 3. Check/Create Virtual Environment
Write-Host "[3/7] Checking Python virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "  ✓ Virtual environment exists" -ForegroundColor Green
}
else {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Virtual environment created" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# 4. Activate and Install Dependencies
Write-Host "[4/7] Installing Python dependencies..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
pip install -q -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# 5. Start Docker Containers
Write-Host "[5/7] Starting Docker containers..." -ForegroundColor Yellow
docker compose up -d
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Containers started" -ForegroundColor Green
}
else {
    Write-Host "  ✗ Failed to start containers" -ForegroundColor Red
    exit 1
}

# 6. Wait for Services to be Ready
Write-Host "[6/7] Waiting for services to be ready..." -ForegroundColor Yellow
Write-Host "  This may take 30-60 seconds..." -ForegroundColor Gray

$maxWait = 60
$waited = 0
$dbReady = $false

while ($waited -lt $maxWait -and -not $dbReady) {
    Start-Sleep -Seconds 5
    $waited += 5
    
    # Check database
    $dbStatus = docker exec timescaledb pg_isready -U twin 2>&1
    if ($dbStatus -match "accepting connections") {
        $dbReady = $true
        Write-Host "  ✓ Database is ready" -ForegroundColor Green
    }
    else {
        Write-Host "  Waiting... ($waited/$maxWait seconds)" -ForegroundColor Gray
    }
}

if (-not $dbReady) {
    Write-Host "  ⚠ Database took longer than expected. Check with: docker compose logs timescaledb" -ForegroundColor Yellow
}

# 7. Check if Models Exist
Write-Host "[7/7] Checking ML models..." -ForegroundColor Yellow
$rulModel = Test-Path "models\rul_xgb_model.joblib"
$failureModel = Test-Path "models\failure_xgb_model.joblib"

if ($rulModel -and $failureModel) {
    Write-Host "  ✓ Models exist" -ForegroundColor Green
}
else {
    Write-Host "  ! Models not found. Training models..." -ForegroundColor Yellow
    python src\models\train.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Models trained successfully" -ForegroundColor Green
    }
    else {
        Write-Host "  ✗ Failed to train models" -ForegroundColor Red
        Write-Host "    You can try manually: python src\models\train.py" -ForegroundColor Yellow
    }
}

# Summary
Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services are running at:" -ForegroundColor White
Write-Host "  • Grafana:     http://localhost:3000 (admin/admin)" -ForegroundColor Cyan
Write-Host "  • Prometheus:  http://localhost:9090" -ForegroundColor Cyan
Write-Host "  • MLflow:      http://localhost:5000" -ForegroundColor Cyan
Write-Host "  • ThingsBoard: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the application:" -ForegroundColor White
Write-Host "  1. Start simulator (Terminal 1):" -ForegroundColor Yellow
Write-Host "     python src\simulator\publisher.py --mode synth --interval 1" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start predictor (Terminal 2):" -ForegroundColor Yellow
Write-Host "     python src\inference\live_predictor.py --interval 5 --write-back" -ForegroundColor Gray
Write-Host ""
Write-Host "Check status:" -ForegroundColor White
Write-Host "  docker compose ps" -ForegroundColor Gray
Write-Host ""
Write-Host "View logs:" -ForegroundColor White
Write-Host "  docker compose logs -f" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop services:" -ForegroundColor White
Write-Host "  docker compose down" -ForegroundColor Gray
Write-Host ""
