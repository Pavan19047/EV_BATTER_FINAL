# src/simulator/publisher.py - EV Telemetry Simulator and Publisher
"""
Generates synthetic EV battery telemetry and publishes to multiple destinations:
- Kafka/Redpanda (topic: telemetry)
- MQTT (topic: v1/devices/me/telemetry)
- TimescaleDB (table: telemetry)

Usage:
    python publisher.py --mode synth --interval 1
    python publisher.py --mode synth --kafka localhost:9092 --mqtt-host localhost
"""

import argparse
import json
import logging
import time
import random
from datetime import datetime
from typing import Dict, Optional
import sys

import psycopg2
from psycopg2 import pool
import paho.mqtt.client as mqtt
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TelemetryGenerator:
    """Generates synthetic EV battery and vehicle telemetry."""
    
    def __init__(self):
        # Initialize state variables with realistic starting values
        self.soc = 85.0  # State of Charge (%)
        self.soh = 95.0  # State of Health (%)
        self.distance = 0.0  # Cumulative distance (km)
        self.cycles = 0  # Charge cycles
        
    def generate(self) -> Dict[str, float]:
        """Generate one telemetry data point with realistic EV metrics."""
        
        # Simulate gradual battery degradation
        self.soc = max(10.0, self.soc - random.uniform(0.01, 0.5))
        if self.soc < 20.0:  # Recharge when low
            self.soc = random.uniform(80.0, 100.0)
            self.cycles += 1
        
        # SOH degrades over charge cycles
        self.soh = max(70.0, 100.0 - (self.cycles * 0.01) - random.uniform(0, 0.05))
        
        # Battery metrics
        battery_voltage = 350.0 + (self.soc / 100.0) * 50.0 + random.uniform(-5, 5)
        battery_current = -20.0 + random.uniform(-30, 50) if self.soc > 20 else random.uniform(40, 80)
        battery_temp = 20.0 + random.uniform(0, 15) + (100 - self.soc) * 0.1
        
        # Motor metrics
        driving_speed = random.uniform(0, 120) if self.soc > 15 else random.uniform(0, 40)
        motor_temp = 40.0 + (driving_speed / 120.0) * 40.0 + random.uniform(-5, 10)
        motor_vibration = 0.3 + (driving_speed / 120.0) * 0.7 + random.uniform(-0.1, 0.1)
        
        # Power consumption based on speed and acceleration
        power_consumption = (driving_speed / 120.0) * 50.0 + random.uniform(5, 15)
        
        # Update distance
        self.distance += driving_speed / 3600.0  # km traveled per second
        
        telemetry = {
            'ts': datetime.utcnow().isoformat(),
            'soc': round(self.soc, 2),
            'soh': round(self.soh, 2),
            'battery_voltage': round(battery_voltage, 2),
            'battery_current': round(battery_current, 2),
            'battery_temperature': round(battery_temp, 2),
            'charge_cycles': self.cycles,  # Add charge cycles for model prediction
            'motor_temperature': round(motor_temp, 2),
            'motor_vibration': round(motor_vibration, 3),
            'power_consumption': round(power_consumption, 2),
            'driving_speed': round(driving_speed, 2),
            'distance_traveled': round(self.distance, 2)
        }
        
        return telemetry


class TelemetryPublisher:
    """Publishes telemetry to Kafka, MQTT, and PostgreSQL."""
    
    def __init__(self, kafka_bootstrap: str, mqtt_host: str, mqtt_port: int, pg_config: str):
        self.kafka_bootstrap = kafka_bootstrap
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.pg_config = pg_config
        
        # Initialize connections
        self.kafka_producer = self._init_kafka()
        self.mqtt_client = self._init_mqtt()
        self.db_pool = self._init_db()
        
    def _init_kafka(self) -> Optional[KafkaProducer]:
        """Initialize Kafka producer with retry logic."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=[self.kafka_bootstrap],
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1
                )
                logger.info(f"Connected to Kafka at {self.kafka_bootstrap}")
                return producer
            except KafkaError as e:
                logger.warning(f"Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Failed to connect to Kafka after all retries")
                    return None
    
    def _init_mqtt(self) -> Optional[mqtt.Client]:
        """Initialize MQTT client with connection."""
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ev_simulator", protocol=mqtt.MQTTv311)
            client.on_connect = self._on_mqtt_connect
            client.on_disconnect = self._on_mqtt_disconnect
            
            logger.info(f"Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
            client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            client.loop_start()
            return client
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            return None
    
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback."""
        if rc == 0:
            logger.info("Connected to MQTT broker successfully")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code {rc}), attempting reconnect...")
    
    def _init_db(self) -> Optional[pool.SimpleConnectionPool]:
        """Initialize PostgreSQL connection pool."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 10,
                    self.pg_config
                )
                logger.info("Connected to PostgreSQL")
                return db_pool
            except psycopg2.Error as e:
                logger.warning(f"DB connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error("Failed to connect to database after all retries")
                    return None
    
    def publish(self, telemetry: Dict) -> None:
        """Publish telemetry to all destinations."""
        
        # Publish to Kafka
        if self.kafka_producer:
            try:
                future = self.kafka_producer.send('telemetry', value=telemetry)
                future.get(timeout=10)  # Block until sent
                logger.debug("Published to Kafka successfully")
            except Exception as e:
                logger.error(f"Kafka publish error: {e}")
        
        # Publish to MQTT
        if self.mqtt_client:
            try:
                result = self.mqtt_client.publish(
                    'v1/devices/me/telemetry',
                    json.dumps(telemetry),
                    qos=1
                )
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.debug("Published to MQTT successfully")
                else:
                    logger.error(f"MQTT publish failed with code {result.rc}")
            except Exception as e:
                logger.error(f"MQTT publish error: {e}")
        
        # Insert into database
        if self.db_pool:
            conn = None
            try:
                conn = self.db_pool.getconn()
                cursor = conn.cursor()
                
                insert_query = """
                    INSERT INTO telemetry (
                        ts, soc, soh, battery_voltage, battery_current,
                        battery_temperature, charge_cycles, motor_temperature, motor_vibration,
                        power_consumption, driving_speed, distance_traveled
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (ts) DO UPDATE SET
                        soc = EXCLUDED.soc,
                        soh = EXCLUDED.soh,
                        battery_voltage = EXCLUDED.battery_voltage,
                        battery_current = EXCLUDED.battery_current,
                        battery_temperature = EXCLUDED.battery_temperature,
                        charge_cycles = EXCLUDED.charge_cycles,
                        motor_temperature = EXCLUDED.motor_temperature,
                        motor_vibration = EXCLUDED.motor_vibration,
                        power_consumption = EXCLUDED.power_consumption,
                        driving_speed = EXCLUDED.driving_speed,
                        distance_traveled = EXCLUDED.distance_traveled;
                """
                
                cursor.execute(insert_query, (
                    telemetry['ts'],
                    telemetry['soc'],
                    telemetry['soh'],
                    telemetry['battery_voltage'],
                    telemetry['battery_current'],
                    telemetry['battery_temperature'],
                    telemetry['charge_cycles'],
                    telemetry['motor_temperature'],
                    telemetry['motor_vibration'],
                    telemetry['power_consumption'],
                    telemetry['driving_speed'],
                    telemetry['distance_traveled']
                ))
                
                conn.commit()
                cursor.close()
                logger.debug("Inserted into database successfully")
                
            except psycopg2.Error as e:
                logger.error(f"Database insert error: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    self.db_pool.putconn(conn)
    
    def close(self):
        """Close all connections gracefully."""
        if self.kafka_producer:
            self.kafka_producer.close()
            logger.info("Kafka producer closed")
        
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            logger.info("MQTT client disconnected")
        
        if self.db_pool:
            self.db_pool.closeall()
            logger.info("Database connections closed")


def main():
    """Main entry point for the telemetry simulator."""
    parser = argparse.ArgumentParser(description='EV Telemetry Simulator and Publisher')
    parser.add_argument('--mode', choices=['synth', 'replay'], default='synth',
                        help='Generation mode: synth (synthetic) or replay')
    parser.add_argument('--interval', type=float, default=1.0,
                        help='Interval between telemetry generation (seconds)')
    parser.add_argument('--kafka', default='localhost:9092',
                        help='Kafka bootstrap server')
    parser.add_argument('--mqtt-host', default='localhost',
                        help='MQTT broker host')
    parser.add_argument('--mqtt-port', type=int, default=1883,
                        help='MQTT broker port')
    parser.add_argument('--pg', default='host=localhost port=5432 user=twin password=twin_pass dbname=twin_data',
                        help='PostgreSQL connection string')
    
    args = parser.parse_args()
    
    logger.info("Starting EV Telemetry Simulator")
    logger.info(f"Mode: {args.mode}, Interval: {args.interval}s")
    
    # Initialize components
    generator = TelemetryGenerator()
    publisher = TelemetryPublisher(
        kafka_bootstrap=args.kafka,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        pg_config=args.pg
    )
    
    try:
        while True:
            # Generate telemetry
            telemetry = generator.generate()
            
            # Log summary
            logger.info(f"Generated telemetry: SOC={telemetry['soc']}%, "
                       f"SOH={telemetry['soh']}%, Speed={telemetry['driving_speed']}km/h")
            
            # Publish to all destinations
            publisher.publish(telemetry)
            
            # Wait for next interval
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        logger.info("Shutting down simulator...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        publisher.close()
        logger.info("Simulator stopped")


if __name__ == '__main__':
    main()
