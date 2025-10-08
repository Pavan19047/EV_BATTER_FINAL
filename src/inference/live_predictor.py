# src/inference/live_predictor.py - Real-time EV Battery Prediction Service
"""
Live predictor service that:
- Loads trained models from local files or MLflow registry
- Queries latest telemetry from TimescaleDB
- Makes RUL and failure probability predictions
- Publishes predictions via MQTT
- Writes predictions back to database (optional)
- Exposes Prometheus metrics

Usage:
    python live_predictor.py --interval 5 --metrics-port 9100 --write-back
"""

import argparse
import json
import logging
import os
import time
from typing import Dict, Optional, Tuple
import sys

import joblib
import numpy as np
import psycopg2
from psycopg2 import pool
import paho.mqtt.client as mqtt
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
PREDICTIONS_COUNTER = Counter('predictions_emitted_total', 'Total number of predictions made')
RUL_GAUGE = Gauge('last_rul_value', 'Latest RUL prediction value')
FAILURE_PROB_GAUGE = Gauge('last_failure_probability', 'Latest failure probability prediction')
PREDICTION_LATENCY = Histogram('prediction_latency_seconds', 'Prediction latency in seconds',
                               buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0])
DB_ERRORS_COUNTER = Counter('db_query_errors_total', 'Total database query errors')
MQTT_ERRORS_COUNTER = Counter('mqtt_publish_errors_total', 'Total MQTT publish errors')


class ModelLoader:
    """Handles loading models from local filesystem or MLflow."""
    
    def __init__(self, models_dir: str = 'models'):
        self.models_dir = models_dir
        self.rul_model = None
        self.failure_model = None
        
    def load_models(self) -> Tuple[Optional[object], Optional[object]]:
        """Load RUL and failure prediction models."""
        
        # Try loading from MLflow first (if environment variables are set)
        mlflow_uri = os.getenv('MLFLOW_MODEL_URI')
        if mlflow_uri:
            logger.info(f"Attempting to load models from MLflow: {mlflow_uri}")
            try:
                import mlflow.pyfunc
                self.rul_model = mlflow.pyfunc.load_model(f"{mlflow_uri}/rul_model")
                self.failure_model = mlflow.pyfunc.load_model(f"{mlflow_uri}/failure_model")
                logger.info("Successfully loaded models from MLflow")
                return self.rul_model, self.failure_model
            except Exception as e:
                logger.warning(f"Failed to load from MLflow: {e}, falling back to local files")
        
        # Load from local filesystem
        rul_path = os.path.join(self.models_dir, 'rul_xgb_model.joblib')
        failure_path = os.path.join(self.models_dir, 'failure_xgb_model.joblib')
        
        try:
            if os.path.exists(rul_path):
                self.rul_model = joblib.load(rul_path)
                logger.info(f"Loaded RUL model from {rul_path}")
            else:
                logger.error(f"RUL model not found at {rul_path}")
                
            if os.path.exists(failure_path):
                self.failure_model = joblib.load(failure_path)
                logger.info(f"Loaded failure model from {failure_path}")
            else:
                logger.error(f"Failure model not found at {failure_path}")
                
        except Exception as e:
            logger.error(f"Error loading models: {e}", exc_info=True)
        
        return self.rul_model, self.failure_model


class TelemetryFetcher:
    """Fetches latest telemetry from TimescaleDB."""
    
    def __init__(self, pg_config: str):
        self.pg_config = pg_config
        self.db_pool = self._init_db()
        
    def _init_db(self) -> Optional[pool.SimpleConnectionPool]:
        """Initialize PostgreSQL connection pool with retry logic."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, self.pg_config)
                logger.info("Connected to PostgreSQL")
                return db_pool
            except psycopg2.Error as e:
                logger.warning(f"DB connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Failed to connect to database")
                    return None
    
    def fetch_latest(self) -> Optional[Dict]:
        """Fetch the most recent telemetry record."""
        if not self.db_pool:
            return None
            
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            query = """
                SELECT ts, soc, soh, battery_voltage, battery_current,
                       battery_temperature, motor_temperature, motor_vibration,
                       power_consumption, driving_speed, distance_traveled
                FROM telemetry
                ORDER BY ts DESC
                LIMIT 1;
            """
            
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                telemetry = {
                    'ts': row[0],
                    'soc': row[1],
                    'soh': row[2],
                    'battery_voltage': row[3],
                    'battery_current': row[4],
                    'battery_temperature': row[5],
                    'motor_temperature': row[6],
                    'motor_vibration': row[7],
                    'power_consumption': row[8],
                    'driving_speed': row[9],
                    'distance_traveled': row[10]
                }
                return telemetry
            else:
                logger.warning("No telemetry data found in database")
                return None
                
        except psycopg2.Error as e:
            logger.error(f"Database query error: {e}")
            DB_ERRORS_COUNTER.inc()
            return None
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def write_predictions(self, ts, rul: float, failure_prob: float) -> bool:
        """Write predictions back to the telemetry table."""
        if not self.db_pool:
            return False
            
        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()
            
            update_query = """
                UPDATE telemetry
                SET rul = %s, failure_probability = %s
                WHERE ts = %s;
            """
            
            cursor.execute(update_query, (rul, failure_prob, ts))
            conn.commit()
            cursor.close()
            logger.debug(f"Updated predictions for timestamp {ts}")
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Database update error: {e}")
            DB_ERRORS_COUNTER.inc()
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self.db_pool.putconn(conn)
    
    def close(self):
        """Close database connections."""
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("Database connections closed")


class PredictionPublisher:
    """Publishes predictions to MQTT."""
    
    def __init__(self, mqtt_host: str, mqtt_port: int):
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_client = self._init_mqtt()
        
    def _init_mqtt(self) -> Optional[mqtt.Client]:
        """Initialize MQTT client."""
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ev_predictor", protocol=mqtt.MQTTv311)
            logger.info(f"Connecting to MQTT at {self.mqtt_host}:{self.mqtt_port}")
            client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            client.loop_start()
            logger.info("Connected to MQTT broker")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return None
    
    def publish(self, predictions: Dict) -> bool:
        """Publish predictions to MQTT topic."""
        if not self.mqtt_client:
            return False
            
        try:
            result = self.mqtt_client.publish(
                'v1/devices/me/predictions',
                json.dumps(predictions),
                qos=1
            )
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug("Published predictions to MQTT")
                return True
            else:
                logger.error(f"MQTT publish failed with code {result.rc}")
                MQTT_ERRORS_COUNTER.inc()
                return False
        except Exception as e:
            logger.error(f"MQTT publish error: {e}")
            MQTT_ERRORS_COUNTER.inc()
            return False
    
    def close(self):
        """Close MQTT connection."""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")


def build_feature_vector(telemetry: Dict) -> np.ndarray:
    """
    Build feature vector from telemetry data for model inference.
    
    Args:
        telemetry: Dictionary containing telemetry fields
        
    Returns:
        numpy array with features in correct order
    """
    # Import shared utility if available
    try:
        from src.common.utils import extract_features
        return extract_features(telemetry)
    except ImportError:
        # Fallback implementation
        features = [
            telemetry.get('soc', 0),
            telemetry.get('soh', 0),
            telemetry.get('battery_voltage', 0),
            telemetry.get('battery_current', 0),
            telemetry.get('battery_temperature', 0),
            telemetry.get('motor_temperature', 0),
            telemetry.get('motor_vibration', 0),
            telemetry.get('power_consumption', 0),
            telemetry.get('driving_speed', 0),
            telemetry.get('distance_traveled', 0)
        ]
        return np.array([features])


class LivePredictor:
    """Main prediction service orchestrator."""
    
    def __init__(self, args):
        self.args = args
        
        # Load models
        logger.info("Loading models...")
        loader = ModelLoader(models_dir='models')
        self.rul_model, self.failure_model = loader.load_models()
        
        if not self.rul_model or not self.failure_model:
            logger.error("Failed to load models. Ensure models are trained and available.")
            sys.exit(1)
        
        # Initialize components
        self.fetcher = TelemetryFetcher(args.pg)
        self.publisher = PredictionPublisher(args.mqtt_host, args.mqtt_port)
        
        # Start Prometheus metrics server
        logger.info(f"Starting Prometheus metrics server on port {args.metrics_port}")
        start_http_server(args.metrics_port)
        
    def predict(self, telemetry: Dict) -> Tuple[float, float]:
        """
        Make predictions using loaded models.
        
        Args:
            telemetry: Telemetry data dictionary
            
        Returns:
            Tuple of (rul, failure_probability)
        """
        # Build feature vector
        features = build_feature_vector(telemetry)
        
        # Make predictions
        rul = float(self.rul_model.predict(features)[0])
        failure_prob = float(self.failure_model.predict(features)[0])
        
        # Ensure failure_prob is in [0, 1]
        failure_prob = max(0.0, min(1.0, failure_prob))
        
        return rul, failure_prob
    
    def run(self):
        """Main prediction loop."""
        logger.info("Starting live prediction service")
        logger.info(f"Prediction interval: {self.args.interval}s")
        logger.info(f"Write-back enabled: {self.args.write_back}")
        
        try:
            while True:
                start_time = time.time()
                
                # Fetch latest telemetry
                telemetry = self.fetcher.fetch_latest()
                
                if telemetry:
                    # Make predictions
                    rul, failure_prob = self.predict(telemetry)
                    
                    logger.info(f"Predictions - RUL: {rul:.1f} cycles, "
                              f"Failure Prob: {failure_prob:.3f}")
                    
                    # Update Prometheus metrics
                    PREDICTIONS_COUNTER.inc()
                    RUL_GAUGE.set(rul)
                    FAILURE_PROB_GAUGE.set(failure_prob)
                    
                    # Publish to MQTT
                    predictions = {
                        'ts': telemetry['ts'].isoformat() if hasattr(telemetry['ts'], 'isoformat') else str(telemetry['ts']),
                        'rul': rul,
                        'failure_probability': failure_prob
                    }
                    self.publisher.publish(predictions)
                    
                    # Write back to database if enabled
                    if self.args.write_back:
                        self.fetcher.write_predictions(telemetry['ts'], rul, failure_prob)
                    
                    # Record latency
                    latency = time.time() - start_time
                    PREDICTION_LATENCY.observe(latency)
                    logger.debug(f"Prediction latency: {latency:.3f}s")
                else:
                    logger.warning("No telemetry available for prediction")
                
                # Sleep until next interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.args.interval - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("Shutting down predictor...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
        finally:
            self.fetcher.close()
            self.publisher.close()
            logger.info("Predictor stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='EV Battery Live Prediction Service')
    parser.add_argument('--interval', type=float, default=5.0,
                        help='Prediction interval in seconds')
    parser.add_argument('--metrics-port', type=int, default=9100,
                        help='Port for Prometheus metrics endpoint')
    parser.add_argument('--write-back', action='store_true',
                        help='Write predictions back to database')
    parser.add_argument('--pg', default=None,
                        help='PostgreSQL connection string')
    parser.add_argument('--mqtt-host', default=None,
                        help='MQTT broker host')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                        help='MQTT broker port')
    parser.add_argument('--tb-host', default=None,
                        help='ThingsBoard host (optional, uses MQTT host if not set)')
    
    args = parser.parse_args()
    
    # Use environment variables if args not provided
    if not args.pg:
        args.pg = os.getenv('PG_CONN_STRING', 
                           'host=localhost port=5432 user=twin password=twin_pass dbname=twin_data')
    
    if not args.mqtt_host:
        args.mqtt_host = os.getenv('MQTT_HOST', 'localhost')
    
    # Create and run predictor
    predictor = LivePredictor(args)
    predictor.run()


if __name__ == '__main__':
    main()
