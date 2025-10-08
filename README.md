# EV Digital Twin - Complete End-to-End Demo

Production-grade repository demonstrating an Electric Vehicle battery digital twin with real-time telemetry simulation, ML-based predictive maintenance, and comprehensive observability.

## Architecture

- **Telemetry Simulator**: Generates synthetic EV data and publishes to Kafka, MQTT, and TimescaleDB
- **ML Training Pipeline**: Trains XGBoost models for RUL (Remaining Useful Life) and failure probability prediction
- **Live Predictor Service**: Real-time inference with Prometheus metrics exposure
- **Data Storage**: TimescaleDB for time-series data, MinIO for ML artifacts
- **Message Streaming**: Redpanda (Kafka-compatible) and MQTT via ThingsBoard
- **ML Tracking**: MLflow with S3-compatible storage
- **Observability**: Prometheus metrics + Grafana dashboards

## Quick Start

### Prerequisites
- Python 3.12+
- Docker and Docker Compose
- 8GB RAM minimum

### Step-by-Step Setup

1. **Clone and setup Python environment**
   ```bash
   cd EV_BATTER_FINAL
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/Mac:
   # source .venv/bin/activate
   
   pip install -r requirements.txt
   ```

2. **Start infrastructure services**
   ```bash
   docker compose up -d
   ```
   
   Wait ~30 seconds for all services to become healthy.

3. **Initialize database schema**
   ```bash
   # The schema is auto-applied via docker-entrypoint-initdb.d
   # If you need to reapply manually:
   docker exec -i timescaledb psql -U twin -d twin_data < infra/create_telemetry_table.sql
   ```

4. **Train ML models**
   ```bash
   python src/models/train.py
   ```
   
   This creates:
   - `models/rul_xgb_model.joblib`
   - `models/failure_xgb_model.joblib`
   - `models/rul_meta.json`
   - `models/failure_meta.json`
   - MLflow runs in `mlruns/`

5. **Start telemetry simulator**
   ```bash
   python src/simulator/publisher.py --mode synth --interval 1
   ```
   
   Generates telemetry every second and publishes to Kafka, MQTT, and TimescaleDB.

6. **Start live predictor (separate terminal)**
   ```bash
   python src/inference/live_predictor.py --interval 5 --write-back --metrics-port 9100
   ```
   
   Makes predictions every 5 seconds and exposes metrics on port 9100.

7. **Access dashboards**
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - MLflow: http://localhost:5000
   - ThingsBoard: http://localhost:8080 (tenant@thingsboard.org/tenant)
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| TimescaleDB | 5432 | PostgreSQL database |
| Redpanda Kafka | 9092 | Kafka broker |
| MinIO API | 9000 | S3-compatible storage |
| MinIO Console | 9001 | Web UI |
| MLflow | 5000 | ML tracking server |
| ThingsBoard HTTP | 8080 | IoT platform |
| ThingsBoard MQTT | 1883 | MQTT broker |
| Prometheus | 9090 | Metrics storage |
| Grafana | 3000 | Dashboards |
| Predictor Metrics | 9100 | Prometheus exporter |

## Project Structure

```
ev-digital-twin/
├── docker-compose.yml          # All infrastructure services
├── requirements.txt            # Python dependencies
├── pyproject.toml             # Project metadata
├── README.md                  # This file
├── src/
│   ├── simulator/
│   │   └── publisher.py       # Telemetry generator and publisher
│   ├── inference/
│   │   └── live_predictor.py  # Real-time prediction service
│   ├── models/
│   │   └── train.py           # ML training pipeline
│   └── common/
│       └── utils.py           # Shared utilities
├── infra/
│   ├── create_telemetry_table.sql  # Database schema
│   ├── prometheus/
│   │   └── prometheus.yml     # Prometheus configuration
│   └── grafana/
│       └── provisioning/      # Auto-provisioned dashboards
├── models/                    # Trained model artifacts
├── mlruns/                    # MLflow tracking data
└── tests/
    └── test_smoke.py          # Unit tests
```

## Usage Examples

### Simulator Options
```bash
# Synthetic mode with 1-second interval
python src/simulator/publisher.py --mode synth --interval 1

# Custom Kafka and MQTT endpoints
python src/simulator/publisher.py --mode synth --kafka localhost:9092 --mqtt-host localhost

# Custom database connection
python src/simulator/publisher.py --mode synth --pg "host=localhost port=5432 user=twin password=twin_pass dbname=twin_data"
```

### Predictor Options
```bash
# Run with default settings
python src/inference/live_predictor.py

# Custom prediction interval and metrics port
python src/inference/live_predictor.py --interval 10 --metrics-port 8000

# Without database write-back
python src/inference/live_predictor.py --interval 5

# With write-back enabled
python src/inference/live_predictor.py --interval 5 --write-back
```

### Training Options
```bash
# Train with default settings
python src/models/train.py

# MLflow UI to view experiments
mlflow ui --backend-store-uri file://./mlruns --port 5001
```

## Monitoring & Observability

### Prometheus Metrics
The live predictor exposes the following metrics on port 9100:

- `predictions_emitted_total`: Counter of total predictions made
- `last_rul_value`: Gauge with latest RUL prediction
- `last_failure_probability`: Gauge with latest failure probability
- `prediction_latency_seconds`: Histogram of prediction latencies
- `db_query_errors_total`: Counter of database errors
- `mqtt_publish_errors_total`: Counter of MQTT publish errors

### Grafana Dashboard
Pre-configured dashboard "EV Digital Twin" includes:
- RUL gauge visualization
- Failure probability trend
- Prediction rate and latency
- Error counters

## Running Tests

```bash
# Run unit tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## RUNBOOK - Operations Guide

### Starting the System

```bash
# 1. Start all infrastructure
docker compose up -d

# 2. Verify all services are healthy
docker compose ps

# 3. Check logs if any service is unhealthy
docker compose logs timescaledb
docker compose logs redpanda

# 4. Train models (first time only)
python src/models/train.py

# 5. Start simulator (terminal 1)
python src/simulator/publisher.py --mode synth --interval 1

# 6. Start predictor (terminal 2)
python src/inference/live_predictor.py --interval 5 --write-back
```

### Stopping the System

```bash
# Stop Python processes (Ctrl+C in each terminal)

# Stop containers but keep data
docker compose stop

# Stop and remove containers (keeps volumes)
docker compose down

# Remove everything including data
docker compose down -v
```

### Debugging Common Issues

#### Port Already in Use
```bash
# Find process using port (Windows PowerShell)
netstat -ano | findstr :5432
netstat -ano | findstr :9092

# Kill process by PID
taskkill /PID <pid> /F

# Or change port in docker-compose.yml
```

#### Prometheus Target Down
```bash
# Check predictor is running and exposing metrics
curl http://localhost:9100/metrics

# Check Prometheus targets
# Visit http://localhost:9090/targets

# Verify network connectivity
docker exec prometheus ping ev-live-predictor
```

#### Grafana Dashboard Not Showing Data
```bash
# 1. Verify Prometheus is scraping predictor
# Visit http://localhost:9090/targets
# Should show ev_predictor target as UP

# 2. Check if predictor is emitting metrics
curl http://localhost:9100/metrics | grep predictions_emitted_total

# 3. Run test query in Prometheus
# Query: predictions_emitted_total

# 4. Check Grafana datasource
# Visit http://localhost:3000/datasources
# Test connection to Prometheus

# 5. Reimport dashboard
# Settings > Dashboard > Import > Upload ev_digital_twin.json
```

#### Database Connection Errors
```bash
# Check TimescaleDB is running
docker exec timescaledb pg_isready -U twin

# Test connection manually
docker exec -it timescaledb psql -U twin -d twin_data -c "SELECT COUNT(*) FROM telemetry;"

# Check logs
docker logs timescaledb

# Verify credentials in connection string
# Default: host=localhost port=5432 user=twin password=twin_pass dbname=twin_data
```

#### Kafka/Redpanda Issues
```bash
# Check Redpanda status
docker exec redpanda rpk cluster health

# List topics
docker exec redpanda rpk topic list

# Consume from telemetry topic
docker exec redpanda rpk topic consume telemetry

# Create topic manually if needed
docker exec redpanda rpk topic create telemetry --partitions 1 --replicas 1
```

#### MQTT Connection Failures
```bash
# Check ThingsBoard is running
docker logs thingsboard | tail -20

# Test MQTT connection with mosquitto
docker run --rm --network ev_twin-net eclipse-mosquitto mosquitto_sub -h thingsboard -t v1/devices/me/telemetry -v

# Check if ThingsBoard MQTT port is accessible
telnet localhost 1883
```

#### Models Not Loading
```bash
# Check models directory
ls -la models/

# Should contain:
# - rul_xgb_model.joblib
# - failure_xgb_model.joblib
# - rul_meta.json
# - failure_meta.json

# Retrain if missing
python src/models/train.py

# Check model file permissions
chmod 644 models/*.joblib models/*.json
```

#### MLflow Issues
```bash
# Check MLflow server
curl http://localhost:5000/health

# View experiments
mlflow ui --backend-store-uri file://./mlruns

# Check MinIO is running (MLflow artifact store)
curl http://localhost:9000/minio/health/live

# Create bucket manually if needed
docker exec -it minio mc alias set local http://localhost:9000 minioadmin minioadmin
docker exec -it minio mc mb local/mlflow
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f timescaledb
docker compose logs -f ev-live-predictor

# Python application logs (if running locally)
# Logs are written to stdout with timestamps
```

### Database Queries

```bash
# Connect to database
docker exec -it timescaledb psql -U twin -d twin_data

# View recent telemetry
SELECT * FROM telemetry ORDER BY ts DESC LIMIT 10;

# Check telemetry count
SELECT COUNT(*) FROM telemetry;

# View predictions with RUL
SELECT ts, soc, soh, rul, failure_probability FROM telemetry WHERE rul IS NOT NULL ORDER BY ts DESC LIMIT 10;

# Calculate average RUL over last hour
SELECT AVG(rul) FROM telemetry WHERE ts > NOW() - INTERVAL '1 hour' AND rul IS NOT NULL;
```

### Performance Tuning

```bash
# Increase Docker resources in Docker Desktop
# Settings > Resources > Set RAM to 8GB+

# Reduce simulator interval to decrease load
python src/simulator/publisher.py --mode synth --interval 5

# Increase predictor interval
python src/inference/live_predictor.py --interval 10

# Monitor resource usage
docker stats
```

## Development

### Adding New Features
1. Add new metrics in `live_predictor.py` using `prometheus_client`
2. Update Grafana dashboard JSON to visualize new metrics
3. Add new telemetry fields in `create_telemetry_table.sql` and `publisher.py`

### Customizing Models
Edit `src/models/train.py` to:
- Use different algorithms (e.g., LightGBM, CatBoost)
- Add hyperparameter tuning
- Include more features
- Change training data source

## License
MIT License - Free for commercial and personal use

## Support
For issues and questions, check the logs and debugging section above.
