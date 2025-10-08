# Troubleshooting Guide - EV Digital Twin

## Common Issues and Solutions

### 1. Docker Desktop Not Running

**Error:**
```
unable to get image 'prom/prometheus:latest': error during connect: Get "http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/..."
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**Solution:**
1. **Start Docker Desktop:**
   - Open Docker Desktop application
   - Wait for it to fully start (icon in system tray should be green)
   - Verify with: `docker ps`

2. **If Docker Desktop is not installed:**
   - Download from: https://www.docker.com/products/docker-desktop/
   - Install and restart your computer
   - Enable WSL 2 if prompted

3. **Verify Docker is running:**
   ```powershell
   docker --version
   docker ps
   ```

### 2. Services Not Connecting (Kafka, MQTT, PostgreSQL)

**Error:**
```
NoBrokersAvailable
No connection could be made because the target machine actively refused it
Connection refused
```

**Root Cause:** Docker containers are not running yet.

**Solution:**
1. **Check Docker containers are running:**
   ```powershell
   docker compose ps
   ```

2. **If containers are not up, start them:**
   ```powershell
   docker compose up -d
   ```

3. **Wait for services to be healthy (30-60 seconds):**
   ```powershell
   # Check status every 5 seconds
   while ($true) { docker compose ps; Start-Sleep -Seconds 5 }
   ```

4. **Verify specific services:**
   ```powershell
   # PostgreSQL
   docker exec timescaledb pg_isready -U twin
   
   # Redpanda (Kafka)
   docker exec redpanda rpk cluster health
   
   # Check logs if issues persist
   docker compose logs timescaledb
   docker compose logs redpanda
   docker compose logs thingsboard
   ```

### 3. MLflow Path Error on Windows

**Error:**
```
FileNotFoundError: [WinError 2] The system cannot find the file specified: '\\\\.\\mlruns'
```

**Solution:**
This has been fixed in the code. The training script now uses absolute paths for Windows.

**Verify the fix:**
```powershell
# Ensure you're in the project directory
cd C:\Users\pavan\OneDrive\Desktop\EV_BATTER_FINAL

# Run training - should work now
python src/models/train.py
```

### 4. MQTT Callback API Deprecation Warning

**Warning:**
```
DeprecationWarning: Callback API version 1 is deprecated, update to latest version
```

**Solution:**
This has been fixed. The code now uses `mqtt.CallbackAPIVersion.VERSION2`.

### 5. Port Already in Use

**Error:**
```
Bind for 0.0.0.0:5432 failed: port is already allocated
```

**Solution:**
```powershell
# Find process using the port (example: 5432)
netstat -ano | findstr :5432

# Kill the process (replace <PID> with actual process ID)
taskkill /PID <PID> /F

# Or change the port in docker-compose.yml
# Change "5432:5432" to "5433:5432"
```

### 6. Cannot Train Models - Missing Dependencies

**Solution:**
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt

# If xgboost fails, you can still use RandomForest
# The code automatically falls back to RandomForest
```

## Step-by-Step Startup Guide (Windows)

### Prerequisites
1. ✅ Docker Desktop installed and running
2. ✅ Python 3.12+ installed
3. ✅ 8GB+ RAM available

### Complete Startup Sequence

```powershell
# 1. Navigate to project directory
cd C:\Users\pavan\OneDrive\Desktop\EV_BATTER_FINAL

# 2. Create and activate virtual environment (first time only)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies (first time only)
pip install -r requirements.txt

# 4. Start Docker Desktop
# (Wait for Docker Desktop to fully start - check system tray icon)

# 5. Start all infrastructure services
docker compose up -d

# 6. Wait for services to be ready (30-60 seconds)
# Check with:
docker compose ps

# All services should show "running (healthy)" or "running"
# If any show "starting", wait another 30 seconds

# 7. Verify database is ready
docker exec timescaledb pg_isready -U twin

# Should output: /var/run/postgresql:5432 - accepting connections

# 8. Train models (first time only, or when you want to retrain)
python src/models/train.py

# Should create:
# - models/rul_xgb_model.joblib
# - models/failure_xgb_model.joblib
# - models/rul_meta.json
# - models/failure_meta.json
# - mlruns/ directory

# 9. Verify models were created
dir models\*.joblib

# 10. Start simulator (in Terminal 1)
python src/simulator/publisher.py --mode synth --interval 1

# 11. Open NEW terminal, activate venv, start predictor (Terminal 2)
.\.venv\Scripts\Activate.ps1
python src/inference/live_predictor.py --interval 5 --write-back --metrics-port 9100

# 12. Access web interfaces
# - Grafana:     http://localhost:3000 (admin/admin)
# - Prometheus:  http://localhost:9090
# - MLflow:      http://localhost:5000
```

### Verification Commands

```powershell
# Check if telemetry is being generated
docker exec -it timescaledb psql -U twin -d twin_data -c "SELECT COUNT(*) FROM telemetry;"

# Check recent telemetry
docker exec -it timescaledb psql -U twin -d twin_data -c "SELECT * FROM telemetry ORDER BY ts DESC LIMIT 5;"

# Check Prometheus metrics
curl http://localhost:9100/metrics

# View Kafka topics
docker exec redpanda rpk topic list

# Consume Kafka messages
docker exec redpanda rpk topic consume telemetry --num 5
```

## Debugging Checklist

When something doesn't work, check these in order:

1. ☑ **Docker Desktop is running**
   ```powershell
   docker ps
   ```

2. ☑ **All containers are running**
   ```powershell
   docker compose ps
   # All should be "Up" or "running (healthy)"
   ```

3. ☑ **Virtual environment is activated**
   ```powershell
   # Prompt should show (.venv)
   ```

4. ☑ **Dependencies are installed**
   ```powershell
   pip list | Select-String "pandas|numpy|mlflow"
   ```

5. ☑ **Models are trained and exist**
   ```powershell
   dir models\*.joblib
   ```

6. ☑ **Database has data**
   ```powershell
   docker exec timescaledb psql -U twin -d twin_data -c "SELECT COUNT(*) FROM telemetry;"
   ```

7. ☑ **Services are accessible**
   ```powershell
   # Test each port
   Test-NetConnection localhost -Port 5432  # PostgreSQL
   Test-NetConnection localhost -Port 9092  # Kafka
   Test-NetConnection localhost -Port 1883  # MQTT
   Test-NetConnection localhost -Port 9090  # Prometheus
   Test-NetConnection localhost -Port 3000  # Grafana
   ```

## Quick Recovery Commands

### Reset Everything
```powershell
# Stop all services
docker compose down

# Remove all data (CAUTION: deletes everything)
docker compose down -v

# Remove models and MLflow data
Remove-Item -Recurse -Force models\*.joblib, models\*.json, mlruns\*

# Start fresh
docker compose up -d
python src/models/train.py
```

### Restart Individual Services
```powershell
# Restart database
docker compose restart timescaledb

# Restart Kafka
docker compose restart redpanda

# Restart MQTT/ThingsBoard
docker compose restart thingsboard

# View logs for specific service
docker compose logs -f timescaledb
```

### Clean Python Environment
```powershell
# Deactivate and remove venv
deactivate
Remove-Item -Recurse -Force .venv

# Recreate
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Performance Issues

### High CPU/Memory Usage
```powershell
# Check Docker resource usage
docker stats

# Reduce simulator frequency
python src/simulator/publisher.py --mode synth --interval 5

# Reduce predictor frequency
python src/inference/live_predictor.py --interval 10
```

### Slow Database Queries
```powershell
# Check database size
docker exec timescaledb psql -U twin -d twin_data -c "SELECT pg_size_pretty(pg_database_size('twin_data'));"

# Manually run retention policy
docker exec timescaledb psql -U twin -d twin_data -c "SELECT remove_retention_policy('telemetry', if_exists => true);"
docker exec timescaledb psql -U twin -d twin_data -c "SELECT add_retention_policy('telemetry', INTERVAL '7 days');"
```

## Getting Help

If issues persist:

1. **Check logs:**
   ```powershell
   docker compose logs --tail=50
   ```

2. **Check application logs:**
   - Simulator logs: stdout from publisher.py
   - Predictor logs: stdout from live_predictor.py
   - Training logs: stdout from train.py

3. **Verify environment:**
   ```powershell
   python --version
   docker --version
   docker compose version
   ```

4. **Test minimal setup:**
   ```powershell
   # Just database
   docker compose up -d timescaledb
   
   # Test connection
   docker exec timescaledb pg_isready -U twin
   ```
