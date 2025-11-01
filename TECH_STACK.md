# EV Battery Digital Twin - Tech Stack

## 📊 Project Overview
A production-grade Electric Vehicle Battery Digital Twin system with real-time telemetry simulation, predictive maintenance using machine learning, and comprehensive observability stack.

---

## 🐍 Core Programming Language
- **Python 3.12+**
  - Primary language for all services
  - Type hints for better code quality
  - Async/concurrent processing capabilities

---

## 🧠 Machine Learning & Data Science

### ML Framework
- **XGBoost 2.0+** 
  - Gradient boosting for RUL (Remaining Useful Life) prediction
  - Binary classification for failure probability
  - Tree-based model with excellent performance (R² = 0.9252)

### Data Processing
- **NumPy ≥1.24.0** - Numerical computing and array operations
- **Pandas ≥2.0.0** - Data manipulation, time-series handling
- **scikit-learn ≥1.3.0** - Feature scaling, model evaluation, preprocessing

### Model Management
- **Joblib ≥1.3.0** - Model serialization and persistence
- **MLflow ≥2.9.0** - Experiment tracking, model registry, artifact storage
- **MinIO (S3-compatible)** - ML artifacts and model versioning storage

---

## 🗄️ Databases & Storage

### Time-Series Database
- **TimescaleDB (PostgreSQL 15)** 
  - Hyper-tables for efficient time-series data storage
  - 829+ telemetry records with real-time inserts
  - Automatic retention policies and compression
  - Native PostgreSQL compatibility

### Object Storage
- **MinIO (latest)** 
  - S3-compatible object storage
  - ML model artifacts storage
  - MLflow backend store
  - Ports: 9000 (API), 9001 (Console)

---

## 📨 Message Streaming & IoT

### Message Broker (Kafka)
- **Redpanda v24.2.4** 
  - Kafka-compatible streaming platform
  - Higher performance, lower latency than Apache Kafka
  - Single-node deployment for development
  - Topic: `ev-telemetry`
  - Port: 9092 (external), 29092 (internal)

### MQTT Broker
- **Eclipse Mosquitto 2.0** 
  - Lightweight MQTT broker for IoT devices
  - Pub/Sub messaging for telemetry data
  - Topic: `ev/battery/telemetry`
  - Ports: 1883 (MQTT), 9002 (WebSocket)

---

## 📊 Monitoring & Observability

### Metrics Collection
- **Prometheus (latest)** 
  - Time-series metrics database
  - Scrapes metrics from predictor service
  - Query language: PromQL
  - Port: 9090

### Metrics Exposition
- **prometheus-client ≥0.18.0** 
  - Python client library
  - Exposes custom metrics from live predictor
  - Metrics types: Counter, Gauge, Histogram
  - Port: 9100 (predictor metrics endpoint)

### Visualization
- **Grafana (latest)** 
  - Real-time dashboards
  - PostgreSQL/TimescaleDB datasource
  - 8 panels with telemetry visualization
  - Auto-refresh every 5 seconds
  - Port: 3000
  - Credentials: admin/admin

---

## 🔧 Backend Services & APIs

### Database Connectivity
- **psycopg2-binary ≥2.9.0** 
  - PostgreSQL adapter for Python
  - Connection pooling for performance
  - Used by both simulator and predictor

### MQTT Client
- **paho-mqtt ≥1.6.0** 
  - MQTT protocol implementation
  - Publish/subscribe to IoT topics
  - QoS levels for reliability

### Kafka Client
- **kafka-python ≥2.0.0** 
  - Pure Python Kafka client
  - Producer for telemetry publishing
  - Consumer for stream processing

### Web Framework
- **Flask ≥3.0.0** 
  - Lightweight WSGI web framework
  - RESTful API endpoints (future expansion)
  - Health check endpoints

---

## ☁️ Cloud & Infrastructure

### Container Orchestration
- **Docker** 
  - Containerization platform
  - Multi-container application deployment

- **Docker Compose** 
  - YAML-based service orchestration
  - 7 services defined (timescaledb, redpanda, minio, mlflow, mosquitto, prometheus, grafana)
  - Shared network: `twin-net`
  - Persistent volumes for data

### Cloud SDK
- **boto3 ≥1.28.0** 
  - AWS SDK for Python
  - S3-compatible operations with MinIO
  - Artifact upload/download for MLflow

---

## 🛠️ Development & Utilities

### Configuration Management
- **PyYAML ≥6.0** 
  - YAML parsing for config files
  - Grafana datasource provisioning
  - Prometheus configuration

### Data Validation
- **Python Type Hints** - Static type checking with mypy
- **Logging** - Standard library logging throughout

---

## 📁 Project Architecture

### Component Structure
```
EV_BATTER_FINAL/
├── src/
│   ├── simulator/           # Telemetry data generation
│   │   └── publisher.py     # Kafka + MQTT + TimescaleDB publisher
│   ├── inference/           # ML prediction service
│   │   └── live_predictor.py # Real-time RUL & failure prediction
│   ├── models/              # Model training scripts
│   │   └── train.py         # XGBoost training pipeline
│   └── common/              # Shared utilities
│       └── utils.py         # Helper functions
├── models/                  # Trained model artifacts
│   ├── rul_xgb_model.joblib
│   ├── failure_xgb_model.joblib
│   ├── scaler.joblib
│   └── feature_names.joblib
├── notebooks/               # Jupyter notebooks
│   └── train_ev_models_fixed.ipynb  # Model training experiments
├── infra/                   # Infrastructure configs
│   ├── grafana/
│   │   └── provisioning/    # Datasources & dashboards
│   ├── prometheus/
│   │   └── prometheus.yml   # Metrics scraping config
│   └── create_telemetry_table.sql
├── datasets/                # Training data
│   └── EV_Predictive_Maintenance_Dataset_15min.csv
├── docker-compose.yml       # Service orchestration
└── requirements.txt         # Python dependencies
```

---

## 🔄 Data Flow Pipeline

```
EV Simulator (publisher.py)
    ↓
    ├─→ Kafka (Redpanda) → [Future: Stream Processing]
    ├─→ MQTT (Mosquitto) → [Future: IoT Dashboard]
    └─→ TimescaleDB → Live Predictor (live_predictor.py)
                           ↓
                           ├─→ XGBoost Models (RUL & Failure)
                           ├─→ Prometheus Metrics
                           └─→ TimescaleDB (predictions)
                                   ↓
                               Grafana Dashboards
```

---

## 📦 Service Ports Summary

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| TimescaleDB | 5432 | PostgreSQL | Time-series data storage |
| Redpanda | 9092 | Kafka | Message streaming |
| MinIO API | 9000 | HTTP/S3 | Object storage |
| MinIO Console | 9001 | HTTP | Admin UI |
| MLflow | 5000 | HTTP | ML tracking |
| Mosquitto | 1883 | MQTT | IoT messaging |
| Mosquitto WS | 9002 | WebSocket | MQTT over WS |
| Prometheus | 9090 | HTTP | Metrics database |
| Grafana | 3000 | HTTP | Dashboards |
| Predictor | 9100 | HTTP | Prometheus metrics |

---

## 🎯 Machine Learning Features

### Input Features (7)
1. **SoC** (State of Charge) - Battery charge level %
2. **SoH** (State of Health) - Battery health %
3. **Battery_Voltage** - Voltage in volts
4. **Battery_Current** - Current in amperes
5. **Battery_Temperature** - Temperature in °C
6. **Charge_Cycles** - Number of charge/discharge cycles
7. **Power_Consumption** - Power usage in watts

### Target Variables
- **RUL** (Remaining Useful Life) - Predicted cycles until maintenance
- **Failure_Probability** - Binary classification (0-1)

### Model Performance
- **RUL Model**: R² = 0.9252, MAE = 11.93 cycles
- **Failure Model**: R² = 0.2466 (binary classification)
- **Training Dataset**: 175,393 samples (100% retention)

---

## 🔐 Security & Configuration

### Default Credentials
- **Grafana**: admin/admin
- **TimescaleDB**: twin/twin_pass (database: twin_data)
- **MinIO**: minioadmin/minioadmin

### Environment Variables
```bash
# Database
PG_HOST=timescaledb
PG_PORT=5432
PG_USER=twin
PG_PASSWORD=twin_pass
PG_DATABASE=twin_data

# MQTT
MQTT_HOST=mosquitto
MQTT_PORT=1883

# MLflow
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

---

## 🚀 Deployment

### Development Mode
- Docker Compose for local deployment
- Python virtual environment (.venv)
- Manual service startup (simulator + predictor)

### Production Considerations
- Kubernetes deployment (future)
- Horizontal scaling for predictor
- High-availability database cluster
- Load balancing for Grafana
- SSL/TLS encryption
- Secrets management (Vault, K8s Secrets)

---

## 📈 Performance Characteristics

### Telemetry Generation
- **Frequency**: 2 seconds (configurable)
- **Throughput**: ~30 records/minute
- **Latency**: < 100ms (simulator to database)

### Prediction Service
- **Frequency**: 5 seconds (configurable)
- **Inference Time**: ~50ms per prediction
- **Model Loading**: ~2 seconds (startup)

### Data Storage
- **Current Records**: 829+ (growing continuously)
- **Database Size**: TimescaleDB auto-compression
- **Retention**: Configurable (default: unlimited)

---

## 🔄 CI/CD Readiness

### Testing
- Smoke tests in `tests/` directory
- Unit test structure ready
- Integration test capabilities

### Version Control
- Git repository structure
- Branch: main
- Owner: Pavan19047

### Docker
- Multi-stage builds possible
- Health checks configured
- Restart policies: unless-stopped

---

## 📚 Documentation Files

- **README.md** - Main documentation
- **QUICK_START.md** - Getting started guide
- **TROUBLESHOOTING.md** - Common issues and fixes
- **SERVICE_STATUS.md** - Service health tracking
- **FIXES_APPLIED.md** - Bug fixes and patches
- **GENERATION_SUMMARY.md** - Project generation notes
- **NOTEBOOK_FIXES.md** - Jupyter notebook corrections
- **TECH_STACK.md** - This document

---

## 🎓 Key Technologies Summary

**Languages**: Python 3.12+  
**ML Framework**: XGBoost, scikit-learn, NumPy, Pandas  
**Databases**: TimescaleDB (PostgreSQL 15), MinIO  
**Messaging**: Redpanda (Kafka), Eclipse Mosquitto (MQTT)  
**Monitoring**: Prometheus, Grafana  
**ML Ops**: MLflow, Joblib  
**Containers**: Docker, Docker Compose  
**Protocols**: HTTP/REST, MQTT, Kafka, PostgreSQL Wire Protocol  

---

**Last Updated**: October 20, 2025  
**Project**: EV Battery Digital Twin  
**Version**: 1.0
